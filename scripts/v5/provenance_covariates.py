import os as _o
V5DIR = _o.environ.get('V5DIR', '/home/claude/v5out'); WB5 = _o.environ.get('WB5CSV', '/home/claude/wb5')
import sys, os, numpy as np, pandas as pd, re
from scipy import stats
sys.path.insert(0, '/home/claude/repo/scripts/robustness'); sys.path.insert(0, '/home/claude/repo/scripts'); os.environ.setdefault('EOARENA_WORKBOOK_DIR', '/home/claude/wb5x')
import robust_lib as R
L = pd.read_pickle(f'{V5DIR}/long_res_pts.pkl'); L = L[L.t.notna() & ~L.selfrep & ~L.variant.isin({'no_overlap', 'superset', 'ood_test'})]
r5 = pd.read_csv(f'{WB5}/results_long.csv', low_memory=False)
r5 = r5[r5.paper_key.isin(L.paper_key.unique()) & (r5.agreement_vs_recitation == 'original')].copy()
r5['family'] = r5.model_id.map(R.unit_of)
n = r5.note.fillna('').astype(str)
r5['official'] = n.str.contains(r'official (repositor|code|implementation|weights|checkpoint|release)|weights were downloaded|released (weights|checkpoint)|publicly (available|released) (weights|checkpoint)', case=False)
r5['retrained'] = n.str.contains(r're-?implement|re-?train|trained (it|them|all|each)? ?(ourselves|from scratch)|our (own )?implementation', case=False)
r5['inferred'] = (r5.model_id_inferred == 1) | n.str.contains('MODEL SIZE INFERRED|checkpoint release not named', case=False)
r5['modality_stated'] = r5.input_modality_basis.isin(['stated', 'config_variant', 'value_match'])
k = ['paper_key', 'family', 'benchmark_id']
cov = r5.groupby(k)[['official', 'retrained', 'inferred', 'modality_stated']].mean().reset_index()
X = L.merge(cov, on=k, how='left')
print('scores matched to v5 rows:', X.official.notna().sum(), 'of', len(X))
X = X[X.official.notna()]; X['a'] = X.t.abs(); X['gross'] = X.a > 3
for c in ['official', 'retrained', 'inferred', 'modality_stated']:
    g = X.groupby(X[c] > 0.5).agg(n=('a', 'size'), papers=('paper_key', 'nunique'), mean_sq=('t', lambda s: (s**2).mean()), gross=('gross', 'mean'))
    print('\n', c); print(g.round(3).to_string())
# cluster-robust check: paper-level means (avoid one paper dominating)
for c in ['official', 'inferred']:
    X['flag'] = (X[c] > 0.5).astype(int); pm = X.groupby(['paper_key', 'flag']).t.apply(lambda s: (s**2).mean()).unstack()
    both = pm.dropna() if pm.shape[1] == 2 else pm.iloc[0:0]
    if len(both): d = both[1] - both[0]; print(f'{c}: {len(both)} papers have both; within-paper difference in mean sq dev: median {d.median():+.2f}, positive in {(d>0).sum()} of {len(d)}')
    else: print(c, 'no paper has both')
