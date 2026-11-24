"""Stage-1 outputs at the note's unit, the task (dataset x protocol; cross-paper key `xtask`, protocol.py).

For every task:
  * Eq. 10 reported separation: tau2_obs = Var_m(y_mt) within each paper's setting, summarised over the task's settings.
    Interpreted only as "reported GeoFM separation under the available evidence" (note p. 3-4), not as quality.
  * Eq. 6 within one implementation, where the note's own sigma^2 exists: settings with printed seed SDs for >= 3 GeoFMs
    (and >= 6 GeoFMs in the comparison), computed by build_dataset_analysis.py section 6 (REL_T). sigma^2 there is replicate
    noise in that paper's pipeline, so the score is conditional on one implementation and its models.
Writes a local JSON (per task, may include single-paper values; never committed) and a public JSON (aggregates only).
Usage: python3 -I task_outputs.py <long.pkl> <out_local.json> <out_public.json>   (EOARENA_WORKBOOK_DIR set)
"""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'robustness')); sys.path.insert(0, os.path.join(HERE, '..'))
import prefix
ARGV = list(sys.argv)   # prefix.build overwrites sys.argv
L = pd.read_pickle(ARGV[1]); L = L[(L.pclass != 'other') & ~L.shifted]
t2x = L.drop_duplicates('task').set_index('task').xtask
g = prefix.build(['--offset', 'none', '--skip-sim', '--merge-families'])
# prefix.build stops before the analyses; run build_dataset_analysis section 6 (seed-noise Eq. 6) verbatim on the same state
_src = open(os.path.join(HERE, '..', 'build_dataset_analysis.py')).read()
_a = _src.index('# ============================================================================= 6. seed-noise'); _b = _src.index('REL_T = pd.DataFrame(rel_rows)') + len('REL_T = pd.DataFrame(rel_rows)')
exec(compile(_src[_a:_b], 'section6', 'exec'), g)
REL = g['REL_T'].copy(); REL['xtask'] = REL.task.map(t2x); REL = REL[REL.xtask.notna()]

# Eq. 10 per setting, then per task
st = L.groupby('task').agg(xtask=('xtask', 'first'), paper=('paper_key', 'first'), n=('y', 'size'), t2=('y', lambda s: s.var(ddof=1)), pts=('pts', 'first'))
st = st[st.n >= 4]
rows = {}
for x, gg in st.groupby('xtask'):
    fams = L[L.xtask == x].family.nunique()
    r = {'dataset': x.split('|')[0], 'settings': int(len(gg)), 'papers': int(gg.paper.nunique()), 'families': int(fams), 'scale': 'points' if gg.pts.all() else 'log_error_or_mixed',
         'eq10_sd_median': float(np.sqrt(gg.t2.median())), 'eq10_sd_range': [float(np.sqrt(gg.t2.min())), float(np.sqrt(gg.t2.max()))]}
    s = REL[REL.xtask == x]
    if len(s):
        r['eq6_within_implementation'] = {'comparisons': int(len(s)), 'sources': int(s.source.nunique()), 'median': float(s.score.median()),
                                          'lo5_min': float(s.score_lo.min()), 'hi95_max': float(s.score_hi.max()), 'seed_sd_median': float(s.sigma.median()),
                                          'n_reps_assumed_share': float((~s.n_reps_known.astype(bool)).mean())}
    rows[x] = r
D = pd.DataFrame(rows).T
out = {'tasks': rows}
pub = {'n_tasks_with_eq10': int(len(D)), 'n_datasets': int(D.dataset.nunique()),
       'tasks_multi_paper': int((D.papers >= 2).sum()),
       'eq10_sd_median_points_tasks': float(D[D.scale == 'points'].eq10_sd_median.astype(float).median()),
       'n_tasks_with_eq6_within_impl': int(D.get('eq6_within_implementation', pd.Series(dtype=object)).notna().sum()) if 'eq6_within_implementation' in D else 0}
if 'eq6_within_implementation' in D:
    e6 = pd.DataFrame([v for v in D.eq6_within_implementation.dropna()])
    pub['eq6_within_impl_median_of_task_medians'] = float(e6['median'].median()); pub['eq6_within_impl_share_ge_0_8'] = float((e6['median'] >= 0.8).mean())
    pub['eq6_within_impl_datasets'] = int(D[D.eq6_within_implementation.notna()].dataset.nunique())
json.dump(out, open(ARGV[2], 'w'), indent=1, default=float); json.dump(pub, open(ARGV[3], 'w'), indent=1, default=float)
print(json.dumps(pub, indent=1))
