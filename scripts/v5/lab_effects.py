"""Heteroscedastic lab-effects model: paper error-proneness and model fragility in the between-lab variance.

Dispersion model of a double hierarchical GLM (Lee & Nelder 2006; the location-scale meta-analysis model of Viechtbauer &
Lopez-Lopez 2022 with random scale effects): for paper p reporting family f on dataset d, the squared deviation of its
setting-centred score from the other papers' mean for that family and dataset,
    q_pfd = (zbar_pfd - zbar_(-p)fd)^2,   E[q_pfd] = sigma2_lab * exp(a_p + b_f) * (1 + 1/k_(-p)) (+ within-paper term),
is fitted by a gamma GLM with log link and Gaussian (ridge) penalties on a_p and b_f, i.e. random effects in the dispersion.
Penalties are chosen by held-out deviance over dataset halves. Validation: traits estimated on half the datasets predict
squared deviations on the other half (Spearman, against label permutations).
Outputs only aggregates (spread of a_p and b_f, by paper type), never per-paper values; per-score multipliers stay local.
Usage: python3 -I lab_effects.py <long.pkl> <out.json> <weights_out.pkl>
"""
import sys, json, numpy as np, pandas as pd
from scipy import optimize, stats
rng = np.random.default_rng(0)

def cells(L, col='z'):
    x = L.copy(); x['c'] = x[col] - x.groupby('task')[col].transform('mean')
    c = x.groupby(['family', 'canonical_dataset', 'paper_key']).agg(c=('c', 'mean'), n=('c', 'size'), sr=('selfrep', 'max'), shifted=('shifted', 'max')).reset_index()
    g = c.groupby(['family', 'canonical_dataset'])
    c['k'] = g.paper_key.transform('size'); c['sum'] = g.c.transform('sum')
    c = c[c.k >= 2].copy(); c['loo'] = (c['sum'] - c.c) / (c.k - 1); c['q'] = (c.c - c.loo) ** 2; c['k_other'] = c.k - 1
    return c

def fit_dispersion(c, lam_p, lam_f):
    P = pd.factorize(c.paper_key)[0]; F = pd.factorize(c.family)[0]; nP, nF = P.max() + 1, F.max() + 1
    off = np.log1p(1.0 / c.k_other.values); q = np.maximum(c.q.values, 1e-8)
    def nll(th):
        a0, a, b = th[0], th[1:1 + nP], th[1 + nP:]
        eta = a0 + a[P] + b[F] + off; mu = np.exp(eta)
        dev = (q / mu + eta).sum()                                   # gamma (shape fixed) negative log-lik up to constants
        g = np.zeros_like(th); r = 1 - q / mu
        g[0] = r.sum(); g[1:1 + nP] = np.bincount(P, r, nP) + 2 * lam_p * a; g[1 + nP:] = np.bincount(F, r, nF) + 2 * lam_f * b
        return dev + lam_p * (a ** 2).sum() + lam_f * (b ** 2).sum(), g
    th0 = np.zeros(1 + nP + nF); th0[0] = np.log(q.mean())
    th = optimize.minimize(nll, th0, jac=True, method='L-BFGS-B').x
    a = pd.Series(th[1:1 + nP], index=pd.factorize(c.paper_key)[1]); b = pd.Series(th[1 + nP:], index=pd.factorize(c.family)[1])
    return th[0], a, b

def predict(c, a0, a, b):
    return np.exp(a0 + c.paper_key.map(a).fillna(0).values + c.family.map(b).fillna(0).values + np.log1p(1.0 / c.k_other.values))

def gamma_dev(q, mu): q = np.maximum(q, 1e-8); return float((q / mu - np.log(q / mu) - 1).mean())

def split_half(c, lam_p, lam_f, reps=100, which='both'):
    ds = c.canonical_dataset.unique(); out = []
    for _ in range(reps):
        A = set(rng.choice(ds, len(ds) // 2, replace=False)); ca, cb = c[c.canonical_dataset.isin(A)], c[~c.canonical_dataset.isin(A)]
        a0, a, b = fit_dispersion(ca, lam_p if which != 'family' else 1e6, lam_f if which != 'paper' else 1e6)
        mu = predict(cb, a0, a, b); mu0 = np.exp(np.log(ca.q.mean())) * (1 + 1 / cb.k_other.values) / (1 + 1 / ca.k_other.values).mean()
        ap = cb.paper_key.map(a).fillna(0); perm = dict(zip(a.index, rng.permutation(a.values))); bp = dict(zip(b.index, rng.permutation(b.values)))
        mup = np.exp(a0 + cb.paper_key.map(perm).fillna(0).values + cb.family.map(bp).fillna(0).values + np.log1p(1 / cb.k_other.values))
        out.append({'rho': stats.spearmanr(mu, cb.q).statistic, 'rho_perm': stats.spearmanr(mup, cb.q).statistic,
                    'dev': gamma_dev(cb.q.values, mu), 'dev_null': gamma_dev(cb.q.values, mu0)})
    return pd.DataFrame(out)

if __name__ == '__main__':
    L = pd.read_pickle(sys.argv[1]); L = L[L.pclass != 'other']
    res = {}
    for scale, d, col in (('z', L, 'z'), ('points', L[L.pts], 'y')):
        c = cells(d, col); c = c[~c.shifted]
        # penalty by held-out deviance over dataset halves
        grid = [(lp, lf) for lp in (0.5, 2, 8, 32) for lf in (0.5, 2, 8, 32)]
        score = {g: split_half(c, *g, reps=20).dev.mean() for g in grid}; lp, lf = min(score, key=score.get)
        V = split_half(c, lp, lf, reps=100); Vp = split_half(c, lp, lf, reps=60, which='paper'); Vf = split_half(c, lp, lf, reps=60, which='family')
        a0, a, b = fit_dispersion(c, lp, lf)
        np_ = c.groupby('paper_key').size(); nf = c.groupby('family').size()
        ptype = c.drop_duplicates('paper_key').set_index('paper_key')
        rec = {'cells': int(len(c)), 'papers': int(c.paper_key.nunique()), 'families': int(c.family.nunique()), 'penalty_paper': lp, 'penalty_family': lf,
               'sd_a_paper': float(a[np_[a.index] >= 5].std()), 'sd_b_family': float(b[nf[b.index] >= 5].std()),
               'ratio_p90_p10_paper': float(np.exp(a[np_[a.index] >= 5].quantile(.9) - a[np_[a.index] >= 5].quantile(.1))),
               'ratio_p90_p10_family': float(np.exp(b[nf[b.index] >= 5].quantile(.9) - b[nf[b.index] >= 5].quantile(.1))),
               'heldout': {k: {'rho_mean': float(x.rho.mean()), 'rho_5_95': [float(x.rho.quantile(.05)), float(x.rho.quantile(.95))],
                               'beats_permutation': float((x.rho > x.rho_perm).mean()), 'deviance_gain': float((x.dev_null - x.dev).mean()),
                               'deviance_better_share': float((x.dev < x.dev_null).mean())} for k, x in (('paper+family', V), ('paper only', Vp), ('family only', Vf))}}
        res[scale] = rec; print(scale, json.dumps(rec, indent=0)[:1500], flush=True)
        if scale == 'z':
            # per-score lab multiplier (normalised to mean 1 over cells) for the heteroscedastic REML and precision weights; local only
            m = np.exp(L.paper_key.map(a).fillna(0).values + L.family.map(b).fillna(0).values)
            m = m / np.exp(a.reindex(c.paper_key).fillna(0).values + b.reindex(c.family).fillna(0).values).mean()
            pd.Series(m, index=L.index, name='w_lab').to_pickle(sys.argv[3])
            # aggregate by evaluator type (allowed on the site: >= 5 papers per group)
            c2 = c.assign(m=predict(c, a0, a, b) / (1 + 1 / c.k_other))
            res['by_type'] = {'self_reported_vs_third_party_mean_multiplier': c2.groupby('sr').m.mean().rename(lambda s: 'self' if s else 'third_party').to_dict()}
    json.dump(res, open(sys.argv[2], 'w'), indent=1, default=float)
