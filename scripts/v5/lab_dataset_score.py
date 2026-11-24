"""Dataset score (note Eq. 4-6) with a between-lab noise term, per dataset, with reporter adjustment and empirical-Bayes shrinkage.

score_d = 1 - sigma2_d / tau2_obs,d   (the note's implementation: tau2_obs = observed between-family variance on the dataset's
settings, points scale), sigma2_d = sigma2_seed + lab_d.
lab_d (moment): mean over the dataset's family x dataset cells with >= 2 papers of the between-paper variance of the papers'
setting-centred means, minus the within-paper term e * mean(1/n_settings) (e from the points REML).
Reporter adjustment: lab_d / mean lab multiplier m_pf of the papers and families in those cells (lab_effects.py), so a dataset
is not penalised for being reported by error-prone labs or for fragile models.
Shrinkage: log(lab_d / tau2_obs,d) ~ N(mu, omega^2 + s_d^2), s_d^2 = 2 / cells_d (DerSimonian-Laird); heterogeneity Q test.
D-study: implementations to average for 0.8 on the dataset ordering, n = 4 sigma2_d / (tau2_obs,d - sigma2_d).
Eligibility for display (agreed with the site review): >= 3 independent papers, >= 4 replicated cells, >= 4 families.
Usage: python3 -I lab_dataset_score.py <long.pkl> <w_lab.pkl> <vc.json> <out_local.json> <out_public.json> [seed_sd]
"""
import sys, json, numpy as np, pandas as pd
from scipy import stats
L = pd.read_pickle(sys.argv[1]); w = pd.read_pickle(sys.argv[2]); vc = json.load(open(sys.argv[3]))
SEED2 = float(sys.argv[6]) ** 2 if len(sys.argv) > 6 else 0.8 ** 2
e_pts = vc['points']['e'] * float(__import__('os').environ.get('LAB_E_SCALE', '1'))   # sensitivity: 0 = no within-paper correction (pessimistic bound)
L = L[(L.pclass != 'other') & L.pts & ~L.shifted].copy(); L['m'] = w.reindex(L.index).fillna(1.0).values
L['yc'] = L.y - L.groupby('task').y.transform('mean')
tau = L.groupby('task').agg(t2=('y', 'var'), n=('y', 'size'), ds=('canonical_dataset', 'first')); tau = tau[tau.n >= 4]
pm = L.groupby(['canonical_dataset', 'family', 'paper_key']).agg(c=('yc', 'mean'), ns=('yc', 'size'), m=('m', 'mean')).reset_index()
cel = pm.groupby(['canonical_dataset', 'family']).agg(v=('c', 'var'), k=('c', 'size'), inv_ns=('ns', lambda s: (1 / s).mean()), m=('m', 'mean')).reset_index()
# within-paper variance across a paper's settings for one family on one dataset: per dataset where estimable (>= 5 groups with
# >= 2 settings), shrunk toward the pooled REML e by its degrees of freedom; pooled e elsewhere (LAB_E_MODE=pooled restores v1)
wg = L.groupby(['canonical_dataset', 'family', 'paper_key']).yc.agg(['var', 'size']).dropna(); wg = wg[wg['size'] >= 2]
wd = wg.assign(ss=wg['var'] * (wg['size'] - 1), df=wg['size'] - 1).groupby(level=0).agg(ss=('ss', 'sum'), df=('df', 'sum'), g=('ss', 'size'))
PRIOR_DF = 10.0
e_d = ((wd.ss + PRIOR_DF * e_pts) / (wd.df + PRIOR_DF)).where(wd.g >= 5)
if __import__('os').environ.get('LAB_E_MODE', 'dataset') == 'pooled': e_d = e_d * np.nan
cel = cel[cel.k >= 2]; cel['e_d'] = cel.canonical_dataset.map(e_d).fillna(e_pts); cel['lab'] = cel.v - cel.e_d * cel.inv_ns
def per_dataset(cel):
    g = cel.groupby('canonical_dataset')
    return pd.DataFrame({'lab_raw': g.lab.mean(), 'cells': g.size(), 'm_bar': g.m.mean()})
D = per_dataset(cel).join(tau.groupby('ds').agg(tau2=('t2', 'median'), settings=('t2', 'size')), how='inner')
D['papers'] = pm[pm.set_index(['canonical_dataset', 'family']).index.isin(cel.set_index(['canonical_dataset', 'family']).index)].groupby('canonical_dataset').paper_key.nunique()
D['families'] = L.groupby('canonical_dataset').family.nunique()
D['lab_adj'] = D.lab_raw / D.m_bar
def eb(D, col):
    x = np.log(np.maximum(D[col], 0.05) / D.tau2); s2 = 2.0 / D.cells
    wv = 1 / s2; mu_fe = (wv * x).sum() / wv.sum(); Q = (wv * (x - mu_fe) ** 2).sum(); k = len(x)
    om2 = max(0.0, (Q - (k - 1)) / (wv.sum() - (wv ** 2).sum() / wv.sum())); wr = 1 / (s2 + om2); mu = (wr * x).sum() / wr.sum()
    B = s2 / (s2 + om2); post = B * mu + (1 - B) * x; pv = (1 - B) * s2 + B ** 2 / wr.sum()
    return post, pv, {'mu': float(mu), 'omega2': float(om2), 'Q': float(Q), 'df': int(k - 1), 'p_het': float(stats.chi2.sf(Q, k - 1)), 'I2': float(max(0, (Q - (k - 1)) / Q)) if Q > 0 else 0.0}
res = {'seed_sd': float(np.sqrt(SEED2)), 'e_points': e_pts, 'datasets': {}}
for name, col in (('unadjusted', 'lab_raw'), ('reporter_adjusted', 'lab_adj')):
    post, pv, het = eb(D, col); res[name] = het
    lab_hat = np.exp(post) * D.tau2; lo = np.exp(post - 1.645 * np.sqrt(pv)) * D.tau2; hi = np.exp(post + 1.645 * np.sqrt(pv)) * D.tau2
    for d in D.index:
        s2 = SEED2 + lab_hat[d]; t2 = D.tau2[d]
        sc = max(0.0, 1 - s2 / t2); sc_lo = max(0.0, 1 - (SEED2 + hi[d]) / t2); sc_hi = max(0.0, 1 - (SEED2 + lo[d]) / t2)
        tt = t2 - s2; nimp = 4 * s2 / tt if tt > 0 else float('inf')
        r = res['datasets'].setdefault(d, {'cells': int(D.cells[d]), 'papers': int(D.papers[d]), 'families': int(D.families[d]), 'settings': int(D.settings[d]),
                                           'eligible': bool(D.papers[d] >= 3 and D.cells[d] >= 4 and D.families[d] >= 4), 'score_seed_only': float(max(0, 1 - SEED2 / t2))})
        r[name] = {'score': sc, 'score90': [sc_lo, sc_hi], 'n_impl_08': nimp, 'lab_over_tau2': float(lab_hat[d] / t2)}
E = pd.DataFrame({d: {'seed': v['score_seed_only'], 'u': v['unadjusted']['score'], 'a': v['reporter_adjusted']['score'], 'el': v['eligible']} for d, v in res['datasets'].items()}).T.astype({'seed': float, 'u': float, 'a': float})
for k_ in ('u', 'a'):
    res[f'summary_{k_}'] = {'median_all': float(E[k_].median()), 'iqr_all': [float(E[k_].quantile(.25)), float(E[k_].quantile(.75))], 'median_eligible': float(E[E.el.astype(bool)][k_].median()),
                            'rank_corr_with_seed_only': float(stats.spearmanr(E.seed, E[k_]).statistic), 'n_eligible': int(E.el.astype(bool).sum()), 'n_datasets': int(len(E))}
res['rank_corr_unadj_vs_adj'] = float(stats.spearmanr(E.u, E.a).statistic)
res['median_abs_change_from_adjustment'] = float((E.a - E.u).abs().median()); res['n_moved_05'] = int(((E.a - E.u).abs() > 0.05).sum())
json.dump(res, open(sys.argv[4], 'w'), indent=1, default=float)
pub = {k: v for k, v in res.items() if k != 'datasets'}
pub['datasets'] = {d: {k: v[k] for k in ('cells', 'papers', 'families', 'eligible', 'score_seed_only', 'unadjusted')} for d, v in res['datasets'].items()}
json.dump(pub, open(sys.argv[5], 'w'), indent=1, default=float)
print(json.dumps({k: v for k, v in res.items() if k != 'datasets'}, indent=1, default=float))
