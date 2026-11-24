"""Row-level checks on the workbook: lone dissenters among >= 3 independent papers, unresolvable pairs, self-report vs later
third-party values, and within-paper fine-tune vs frozen inversions. Points metrics only. Aggregates printed; flagged rows listed by identifiers."""
import os as _o
V5DIR = _o.environ.get('V5DIR', '/home/claude/v5out'); WB5 = _o.environ.get('WB5CSV', '/home/claude/wb5')

import numpy as np, pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 45); pd.set_option('display.max_rows', 200)
r = pd.read_csv(f'{WB5}/results_long.csv', low_memory=False)
src = pd.read_csv(f'{WB5}/sources.csv').set_index('paper_key')
r = r[(r.exclude_from_analysis != 1) & (r.agreement_vs_recitation == 'original') & (~r.model_id.astype(str).str.contains('_abl'))
      & (r.is_non_foundation_baseline != 1) & (r.evaluation_protocol != 'scratch')].copy()
r['v'] = pd.to_numeric(r.result_normalized, errors='coerce'); r = r[r.v.notna() & r.scale_basis.isin(['percent_printed', 'fraction_printed'])]
r['cfg'] = r.config_variant.fillna('').astype(str) + '|' + r.variant_axis.fillna('').astype(str) + '|' + r.input_modality_norm.fillna('').astype(str)
r['rel'] = r.paper_key.map(src.release_year_month).astype(str)
key = ['model_id', 'benchmark_id', 'metric', 'evaluation_protocol', 'train_fraction_norm', 'cfg']
# one value per paper per tuple (median if a paper prints several, e.g. two tables)
p = r.groupby(key + ['paper_key']).agg(v=('v', 'median'), rel=('rel', 'first'), sr=('is_self_reported', 'max')).reset_index()
# collapse unlabelled copies: same tuple, value equal to 0.05 points, keep earliest release
p = p.sort_values('rel'); p['vr'] = p.v.round(1)
p = p.drop_duplicates(key + ['vr'], keep='first')
n = p.groupby(key).paper_key.transform('nunique'); p['n_papers'] = n
print('tuples with >=2 papers', p[n >= 2].groupby(key).ngroups, '; >=3 papers', p[n >= 3].groupby(key).ngroups)
spread = p[n >= 2].groupby(key).v.agg(lambda x: x.max() - x.min())
print('spread (points) over tuples with >=2 independent papers: median %.1f, p75 %.1f, p90 %.1f; >=5: %d, >=10: %d, >=20: %d of %d' %
      (spread.median(), spread.quantile(.75), spread.quantile(.9), (spread >= 5).sum(), (spread >= 10).sum(), (spread >= 20).sum(), len(spread)))
# lone dissenters
rows = []
for k, g in p[n >= 3].groupby(key):
    for i, row in g.iterrows():
        o = g.drop(i).v
        rows.append(dict(zip(key, k), paper=row.paper_key, self=bool(row.sr), dev=row.v - o.median(), others_spread=o.max() - o.min(), n_others=len(o)))
T = pd.DataFrame(rows)
for gap, agree in [(10, 3), (5, 2)]:
    f = T[(T.dev.abs() >= gap) & (T.others_spread <= agree)]
    print(f'\nlone dissenters: |deviation| >= {gap} pts while the other >= 2 papers agree within {agree}: {len(f)} values in {f.groupby(key).ngroups} tuples (of {T.groupby(key).ngroups})')
    print(f.groupby('paper').agg(n=('dev', 'size'), mean_dev=('dev', 'mean')).join(T.groupby('paper').size().rename('tested')).sort_values('n', ascending=False).round(1).to_string())
F10 = T[(T.dev.abs() >= 10) & (T.others_spread <= 3)].sort_values('dev')
print(F10[['model_id', 'benchmark_id', 'metric', 'evaluation_protocol', 'train_fraction_norm', 'paper', 'self', 'dev', 'others_spread', 'n_others']].round(1).to_string())
# pairs that cannot be resolved (only 2 papers, gap >= 10)
pairs = p[n == 2].groupby(key).agg(gap=('v', lambda x: x.max() - x.min()), papers=('paper_key', lambda x: ' vs '.join(sorted(x))))
print(f'\nunresolvable two-paper tuples with gap >= 10: {(pairs.gap >= 10).sum()} of {len(pairs)}; most frequent paper pairs:')
print(pairs[pairs.gap >= 10].papers.value_counts().head(10).to_string())
# self-report vs later third-party median
sr = []
for k, g in p[n >= 2].groupby(key):
    s = g[g.sr == True]; t = g[g.sr != True]
    if len(s) == 1 and len(t) >= 1: sr.append(dict(zip(key, k), paper=s.paper_key.iloc[0], gap=s.v.iloc[0] - t.v.median(), n_third=len(t)))
S = pd.DataFrame(sr)
print(f'\nself-reported vs third-party median: {len(S)} tuples; median gap {S.gap.median():+.2f} pts; self higher by >=5: {(S.gap >= 5).sum()}, lower by >=5: {(S.gap <= -5).sum()}')
print(S.groupby('paper').gap.agg(['size', 'median', lambda x: (x >= 5).sum()]).round(1).sort_values('median', ascending=False).to_string())
# within-paper inversions: fine-tuned below a frozen protocol by >= 10 points, same paper/model/benchmark/metric/fraction
w = r.groupby(['paper_key', 'model_id', 'benchmark_id', 'metric', 'train_fraction_norm', 'cfg', 'evaluation_protocol']).v.median().unstack()
fro = [c for c in ['LP', 'kNN', 'frozen_dec', 'frozen', 'MLP'] if c in w]
if 'FT' in w:
    ww = w[w.FT.notna()]; best_frozen = ww[fro].max(axis=1); inv = ww[(best_frozen - ww.FT) >= 10]
    print(f'\nwithin-paper fine-tune below best frozen protocol by >= 10 pts: {len(inv)} of {best_frozen.notna().sum()} comparable cells')
    print(inv.reset_index().groupby('paper_key').size().sort_values(ascending=False).to_string())
T.to_pickle(f'{V5DIR}/triangulation.pkl'); S.to_pickle(f'{V5DIR}/selfrep_gap.pkl')
