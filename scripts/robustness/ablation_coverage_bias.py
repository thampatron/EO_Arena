"""Is the portfolio coverage score (note Eq. 7-8, as computed in R.findings) biased towards rarely reported datasets?

    python ablation_coverage_bias.py   ->  prints the checks, writes <EOARENA_OUT>/coverage_bias.json

Checks, on datasets with two or more sources: loading norm against how often a dataset is reported; the most-used
five against random fives drawn from popular datasets only; coverage with loadings scaled to unit length; cosine
similarity among the most-used five. Also prints which GeoFM families carry the pretraining-sensor contrast.
"""
import os, json, collections, numpy as np, pandas as pd
from scipy.stats import spearmanr
import ablation_lib as A
from ablation_lib import R
D = R.load(); f, _ = R.fit(D); names, Ld, L, w, sh = R.dataset_loadings(D, f); td = D['td']; K = Ld.shape[1]
nsrc = pd.Series(D['tp']).groupby(td).nunique().reindex(names).values; nset = pd.Series(td).value_counts().reindex(names).values; nsc = np.array([D['mask'][:, td == n].sum() for n in names])
ms = np.where(nsrc >= 2)[0]; Lm = Ld[ms]; I = np.eye(K); V = lambda X: np.linalg.slogdet(I + X.T @ X)[1]; norm = np.linalg.norm(Lm, axis=1); rr = np.random.default_rng(2); allp = np.arange(len(ms))
def greedy(X):
    ch = []
    for _ in range(5): ch.append(max((i for i in range(len(X)) if i not in ch), key=lambda i: V(X[ch + [i]])))
    return ch
rand = lambda X, pool, n=2000: float(np.mean([V(X[rr.choice(pool, 5, replace=False)]) for _ in range(n)]))
mu = [i for i, j in enumerate(ms) if names[j] in R.MOST_USED]; VA = V(Lm); g = greedy(Lm); U = Lm / np.maximum(norm[:, None], 1e-9) * np.median(norm); VU = V(U); gu = greedy(U)
pop = np.where(nsrc[ms] >= np.median(nsrc[ms]))[0]; top10 = np.argsort(-nsrc[ms])[:10]
cos = lambda X: (X @ X.T) / np.outer(np.linalg.norm(X, axis=1), np.linalg.norm(X, axis=1))
o = {'n_multi_source': len(ms),
     'spearman_norm_vs_sources': float(spearmanr(norm, nsrc[ms])[0]), 'spearman_norm_vs_settings': float(spearmanr(norm, nset[ms])[0]), 'spearman_norm_vs_scores': float(spearmanr(norm, nsc[ms])[0]),
     'by_norm': [{'dataset': names[ms[i]], 'norm': float(norm[i]), 'sources': int(nsrc[ms[i]]), 'settings': int(nset[ms[i]]), 'most_used': names[ms[i]] in R.MOST_USED} for i in np.argsort(-norm)],
     'cov_most_used': V(Lm[mu]) / VA, 'cov_random_any': rand(Lm, allp) / VA, 'cov_random_popular_half': rand(Lm, pop) / VA, 'cov_random_top10': rand(Lm, top10) / VA, 'cov_greedy': V(Lm[g]) / VA, 'greedy': [names[ms[i]] for i in g],
     'share_random_below_most_used': float(np.mean([V(Lm[rr.choice(allp, 5, replace=False)]) < V(Lm[mu]) for _ in range(3000)])),
     'unit_norm': {'cov_most_used': V(U[mu]) / VU, 'cov_random_any': rand(U, allp) / VU, 'cov_greedy': V(U[gu]) / VU, 'greedy': [names[ms[i]] for i in gu]},
     'cosine_most_used': float(cos(Lm[mu])[np.triu_indices(len(mu), 1)].mean()), 'cosine_all_pairs': float(cos(Lm)[np.triu_indices(len(ms), 1)].mean())}
# which families carry the pretraining-sensor contrast
pg = np.array([R.pre_of(m) for m in D['models']]); ts = A.sensor_of_tasks(D); fam = []
for i in np.where(np.isin(pg, ['high-resolution RGB', 'multispectral optical']))[0]:
    row = {'family': D['models'][i], 'pretraining': pg[i]}
    for lab, sel in (('hr', ts == 'high-resolution optical'), ('ms', ts == 'multispectral')):
        v = []
        for t in np.where(sel)[0]:
            ob = D['mask'][:, t]
            if D['mask'][i, t] and ob.sum() >= 4: rk = (pd.Series(D['Y'][ob, t]).rank().values - 1) / (ob.sum() - 1) * 100; v.append(rk[np.where(ob)[0] == i][0])
        row[f'n_{lab}'] = int(D['mask'][i, sel].sum()); row[f'mean_rank_{lab}'] = float(np.mean(v)) if v else None
    fam.append(row)
o['sensor_contrast_families'] = fam; o['settings_by_sensor'] = dict(collections.Counter(ts))
for k, v in o.items():
    if not isinstance(v, (list, dict)) or k in ('greedy', 'unit_norm'): print(k, v)
json.dump(o, open(os.path.join(A.OUTD, 'coverage_bias.json'), 'w'), indent=1, default=float)
