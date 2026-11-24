"""Exact REML variance components for published GeoFM scores (rewrite of the 2026-11-23 analysis for v5).

score[f,s] = setting (fixed) + F + FxD + FxP + FxDxP + FxC + e     (D dataset, P paper, C protocol class)
Every random term contains the family, so V is block-diagonal by family; REML is evaluated exactly from the blocks.
Lab variance = FxP + FxDxP. Reliability of one published score for a family x dataset effect = FD / (FD + FP + FDP + e);
independent papers per cell for 0.8 = 4 (FP + FDP + e) / FD. Intervals: delete-a-group jackknife over papers (Kott 2001).
Also used with per-score lab weights (heteroscedastic lab model, lab_effects.py) via `w_lab`.
Usage: python3 -I variance_components.py <long.pkl> <out.json>     (writes aggregate statistics only)
"""
import sys, json, numpy as np, pandas as pd
from scipy import optimize, linalg
COMP = ['F', 'FD', 'FP', 'FDP', 'FC', 'e']

def prepare(L, col):
    L = L.reset_index(drop=True)
    L = L[L.groupby('task')[col].transform('size') >= 2].reset_index(drop=True)
    s_codes, s_idx = np.unique(L.task.values, return_inverse=True)
    blocks = []
    for f, g in L.groupby('family'):
        ix = g.index.values; y = g[col].values.astype(float)
        Zs = {}
        for name, key in (('FD', g.canonical_dataset), ('FP', g.paper_key), ('FDP', g.canonical_dataset + '|' + g.paper_key), ('FC', g.pclass)):
            k = pd.factorize(key)[0]; Zs[name] = (k[:, None] == k[None, :]).astype(float)
        Zs['F'] = np.ones((len(ix), len(ix)))
        blocks.append((ix, y, Zs, s_idx[ix], g.get('w_lab', pd.Series(1.0, index=g.index)).values.astype(float)))
    return L, blocks, len(s_codes)

def neg_reml(logv, blocks, S, hetero=False):
    v = dict(zip(COMP, np.exp(logv)))
    XtVX = np.zeros((S, S)); XtVy = np.zeros(S); yVy = 0.0; logdet = 0.0
    for ix, y, Z, s, w in blocks:
        n = len(y)
        V = v['F'] * Z['F'] + v['FD'] * Z['FD'] + v['FC'] * Z['FC'] + v['e'] * np.eye(n)
        if hetero:   # lab terms scaled per score: Cov = sqrt(w_i w_j) * sigma^2 * Z
            sw = np.sqrt(w); W = np.outer(sw, sw); V = V + W * (v['FP'] * Z['FP'] + v['FDP'] * Z['FDP'])
        else: V = V + v['FP'] * Z['FP'] + v['FDP'] * Z['FDP']
        try: c = linalg.cho_factor(V, lower=True)
        except linalg.LinAlgError: return 1e12
        logdet += 2 * np.log(np.diag(c[0])).sum()
        Vy = linalg.cho_solve(c, y); yVy += y @ Vy
        X = np.zeros((n, S)); X[np.arange(n), s] = 1.0; us = np.unique(s); Xs = X[:, us]
        VX = linalg.cho_solve(c, Xs)
        XtVX[np.ix_(us, us)] += Xs.T @ VX; XtVy[us] += Xs.T @ Vy
    keep = np.diag(XtVX) > 0; A = XtVX[np.ix_(keep, keep)]; b = XtVy[keep]
    try: ca = linalg.cho_factor(A, lower=True)
    except linalg.LinAlgError: return 1e12
    return 0.5 * (logdet + 2 * np.log(np.diag(ca[0])).sum() + yVy - b @ linalg.cho_solve(ca, b))

def fit(L, col, x0=None, hetero=False):
    L2, blocks, S = prepare(L, col)
    x0 = np.log(np.full(6, L2[col].var() / 6)) if x0 is None else x0
    res = optimize.minimize(neg_reml, x0, args=(blocks, S, hetero), method='L-BFGS-B', bounds=[(-12, 12)] * 6, options={'maxiter': 200})
    v = dict(zip(COMP, np.exp(res.x))); return v, res.x, len(L2)

def summary(v):
    lab = v['FP'] + v['FDP']
    return {**{k: float(x) for k, x in v.items()}, 'lab': float(lab), 'rel_one_score': float(v['FD'] / (v['FD'] + lab + v['e'])),
            'papers_for_08': float(4 * (lab + v['e']) / max(v['FD'], 1e-12)), 'lab_over_signal': float(lab / max(v['FD'], 1e-12))}

def jackknife(L, col, x0, groups=10, seed=0):
    papers = np.array(sorted(L.paper_key.unique())); rng = np.random.default_rng(seed); g = rng.permutation(len(papers)) % groups
    est = []
    for k in range(groups):
        v, _, _ = fit(L[~L.paper_key.isin(papers[g == k])], col, x0); est.append(summary(v))
    E = pd.DataFrame(est); full = None
    return E

if __name__ == '__main__':
    L = pd.read_pickle(sys.argv[1]); out = {}
    L = L[L.pclass != 'other']
    specs = [('points', L[L.pts], 'y'), ('z', L, 'z'), ('rank', L, 'rank')]
    for it in ('multispectral', 'SAR + optical', 'high-resolution optical'):
        specs += [(f'{it} | z', L[L.itype == it], 'z')]
    for name, d, col in specs:
        v, x, n = fit(d, col); s = summary(v)
        rec = {'n_scores': n, 'families': int(d.family.nunique()), 'papers': int(d.paper_key.nunique()), **s}
        cells = d.groupby(['family', 'canonical_dataset']).paper_key.nunique(); rec['replicated_cells'] = int((cells >= 2).sum()); rec['cells_3plus'] = int((cells >= 3).sum())
        if name in ('points', 'z') or name.endswith('| z'):
            E = jackknife(d, col, x, groups=10); G = len(E)
            for k in ('rel_one_score', 'papers_for_08', 'lab_over_signal', 'FD', 'lab', 'e'):
                m = E[k].mean(); se = np.sqrt((G - 1) / G * ((E[k] - m) ** 2).sum()); rec[k + '_jk90'] = [float(s[k] - 1.645 * se), float(s[k] + 1.645 * se)]
        out[name] = rec; print(name, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in rec.items()}, flush=True)
    json.dump(out, open(sys.argv[2], 'w'), indent=1)
