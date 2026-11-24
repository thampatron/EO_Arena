"""Preview: dataset score with a between-lab term, per dataset, on the points scale. Aggregates only."""
import os as _o
V5DIR = _o.environ.get('V5DIR', '/home/claude/v5out'); WB5 = _o.environ.get('WB5CSV', '/home/claude/wb5')

import numpy as np, pandas as pd
from scipy import stats
rng = np.random.default_rng(0); pd.set_option('display.width', 200)
L = pd.read_pickle(f'{V5DIR}/long_v5.pkl')
PTS = {'miou','acc','f1','acc_top1','r2','iou','map','micro_f1','oa','segm_map','mijacc'}
L = L[L.metric_s.isin(PTS) & (L.evaluation_protocol != 'kmeans_clustering')].copy()
L['yc'] = L.y - L.groupby('task').y.transform('mean')
# tau^2 per setting: between-family variance within one paper's table
tau = L.groupby('task').agg(t2=('y', 'var'), n=('y', 'size'), ds=('canonical_dataset', 'first'), lvl=('y', 'mean'), bid=('benchmark_id', 'first'))
tau = tau[tau.n >= 4]
# lab variance per family x dataset cell: between-paper variance of the paper's (setting-centred) mean
c = L.groupby(['canonical_dataset', 'family', 'paper_key']).yc.mean().reset_index()
cells = c.groupby(['canonical_dataset', 'family']).yc.agg(['var', 'count']).reset_index()
cells = cells[cells['count'] >= 2]
D = cells.groupby('canonical_dataset').agg(lab_mean=('var', 'mean'), lab_med=('var', 'median'), cells=('var', 'size'))
D = D.join(tau.groupby('ds').agg(tau2=('t2', 'median'), level=('lvl', 'median'), settings=('t2', 'size'), versions=('bid', 'nunique')))
D['papers'] = L.groupby('canonical_dataset').paper_key.nunique()
D = D.dropna()
D['score_seed'] = D.tau2 / (D.tau2 + 0.64)
D['score_lab'] = D.tau2 / (D.tau2 + 0.64 + D.lab_mean)
D['score_lab_robust'] = D.tau2 / (D.tau2 + 0.64 + D.lab_med)
print(D.sort_values('score_lab', ascending=False).round(2).to_string())
print('\ndatasets:', len(D), '| median score seed-only %.2f, with lab (mean) %.2f, with lab (median) %.2f' % (D.score_seed.median(), D.score_lab.median(), D.score_lab_robust.median()))
print('IQR of score_lab: %.2f-%.2f' % tuple(D.score_lab.quantile([.25, .75])))
# is lab variance heterogeneous across datasets beyond sampling noise? permute cells across datasets (keeping per-dataset cell counts)
def spread(v, lab):
    m = pd.Series(v).groupby(lab).mean(); m = m[m > 0]; return np.log(m).var()
cc = cells[cells.canonical_dataset.isin(D.index)]
obs = spread(cc['var'].values, cc.canonical_dataset.values)
null = [spread(rng.permutation(cc['var'].values), cc.canonical_dataset.values) for _ in range(2000)]
print('heterogeneity of log lab variance across datasets: observed %.2f, permutation null median %.2f, p = %.3f' % (obs, np.median(null), np.mean(np.array(null) >= obs)))
obs_r = spread(np.log1p(cc['var'].values), cc.canonical_dataset.values); null_r = [spread(rng.permutation(np.log1p(cc['var'].values)), cc.canonical_dataset.values) for _ in range(2000)]
print('same on log1p(cell var) (robust to heavy tails): observed %.3f, null median %.3f, p = %.3f' % (obs_r, np.median(null_r), np.mean(np.array(null_r) >= obs_r)))
# what predicts it?
for col in ['level', 'tau2', 'versions', 'papers', 'cells']:
    r = stats.spearmanr(D[col], np.log(D.lab_mean)); r2 = stats.spearmanr(D[col], D.score_lab)
    print(f'spearman with log lab var: {col:9s} {r.statistic:+.2f} (p {r.pvalue:.2f}) | with score_lab {r2.statistic:+.2f} (p {r2.pvalue:.2f})')
# rank agreement between seed-only and lab-adjusted ordering of datasets
print('rank corr score_seed vs score_lab: %.2f' % stats.spearmanr(D.score_seed, D.score_lab).statistic)
