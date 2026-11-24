"""Does the comparator set a paper chose bias a task's tau^2? (note Eq. 3, population check for the per-task score)

Eq. 3 defines tau_t^2 = Var_m(lambda_t' theta_m + gamma_mt) over the evaluated GeoFM population, the same population for every
task. The per-task multilevel score (ml_task_score.py) estimates the variance over the families actually evaluated on t, which
papers choose. Using the note's latent fit (Eq. 9 with Eq. 11 blocks) extended with paper x family offsets c_mp (implementation
effects removed from theta), compare for each task the shared-capability variance over ALL families,
    Var_all(lambda_t' theta_m),
with the same quantity over the families evaluated on t. Ratio ~ 1: comparator choice does not bias tau^2 (shared part).
Psi_tt is not identifiable from single scores (note p. 3), so only the shared part is compared.
Usage: EOARENA_WORKBOOK_DIR=<xlsx dir> python3 -I latent_tau.py <long.pkl> <ml_local.json> <out.json> [K]
"""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'robustness')); sys.path.insert(0, os.path.join(HERE, '..'))
ARGS = list(sys.argv)
import robust_lib as R, dataset_benchmarking as db
L = pd.read_pickle(ARGS[1]); ML = json.load(open(ARGS[2]))['tasks']; K = int(ARGS[4]) if len(ARGS) > 4 else 4
D = R.load(); tp = np.asarray(D['tp']); pidx = pd.factorize(tp)[0]
KW = dict(ridge_u=R.RID, ridge_theta=R.RID, ridge_g={k: R.RID for k in D['G']}, n_restarts=2, n_iter=300, tol=1e-6)
fit = db.fit_structured(D['Y'], D['mask'], K, D['G'], paper=pidx, **KW)
lam = fit.lam(); th = fit.theta; S = th @ lam.T          # (M, T) shared-capability component, implementation offsets removed
t2x = L.drop_duplicates('task').set_index('task').xtask
rows = []
for j, t in enumerate(D['tasks']):
    x = t2x.get(t)
    if x is None or x not in ML: continue
    ev = D['mask'][:, j]
    rows.append(dict(xtask=x, var_all=float(S[:, j].var(ddof=1)), var_eval=float(S[ev, j].var(ddof=1)), n_eval=int(ev.sum())))
df = pd.DataFrame(rows); g = df.groupby('xtask')[['var_all', 'var_eval']].median(); g['ratio'] = g.var_all / g.var_eval
from scipy.stats import spearmanr
sc = pd.Series({x: ML[x]['score'] for x in g.index})
out = {'K': K, 'tasks': int(len(g)), 'ratio_all_over_evaluated_median': float(g.ratio.median()), 'ratio_iqr': [float(g.ratio.quantile(.25)), float(g.ratio.quantile(.75))],
       'share_ratio_outside_0.67_1.5': float(((g.ratio < 2 / 3) | (g.ratio > 1.5)).mean()),
       'spearman_ratio_vs_ml_score': float(spearmanr(g.ratio, sc).statistic)}
json.dump(out, open(ARGS[3], 'w'), indent=1); print(json.dumps(out, indent=1))
