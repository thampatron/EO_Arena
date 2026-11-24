import os as _o
V5DIR = _o.environ.get('V5DIR', '/home/claude/v5out'); WB5 = _o.environ.get('WB5CSV', '/home/claude/wb5')
import numpy as np, pandas as pd
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
exec(open('triangulate.py').read().split("key = [")[0])   # same filters and loading
r = r[r.train_fraction_norm.astype(str).isin(['100%', 'unspecified', 'nan'])].copy()
r['pclass'] = r.evaluation_protocol.map(lambda q: 'ft' if q in ('FT', 'PFT') else 'dec' if q == 'frozen_dec' else 'probe')
key = ['model_id', 'benchmark_id', 'metric', 'pclass']
p = r.groupby(key + ['paper_key']).agg(v=('v', 'median'), rel=('rel', 'first'), sr=('is_self_reported', 'max'), proto=('evaluation_protocol', 'first')).reset_index()
p = p.sort_values('rel'); p['vr'] = p.v.round(1); p = p.drop_duplicates(key + ['vr'], keep='first')
n = p.groupby(key).paper_key.transform('nunique')
sp = p[n >= 2].groupby(key).v.agg(lambda x: x.max() - x.min())
print('loose key (model, benchmark, metric, protocol class; full or unspecified fraction):', len(sp), 'tuples with >=2 papers;', (n >= 3).groupby([p[k] for k in key]).any().sum(), 'with >=3')
print('spread median %.1f p75 %.1f p90 %.1f | >=10: %d (%.0f%%)' % (sp.median(), sp.quantile(.75), sp.quantile(.9), (sp >= 10).sum(), 100 * (sp >= 10).mean()))
rows = []
for k, g in p[n >= 3].groupby(key):
    for i, row in g.iterrows():
        o = g.drop(i).v; rows.append(dict(zip(key, k), paper=row.paper_key, proto=row.proto, self=bool(row.sr), dev=row.v - o.median(), others_spread=o.max() - o.min(), n_others=len(o)))
T = pd.DataFrame(rows); ntup = T.groupby(key).ngroups
for gap, agree in [(10, 3), (5, 2)]:
    f = T[(T.dev.abs() >= gap) & (T.others_spread <= agree)]
    print(f'\nlone dissenters |dev|>={gap}, others within {agree}: {len(f)} values / {ntup} tuples; by paper (tested = values of that paper in >=3-paper tuples):')
    print(f.groupby('paper').agg(n=('dev', 'size'), mean_dev=('dev', 'mean')).join(T.groupby('paper').size().rename('tested')).sort_values('n', ascending=False).round(1).to_string())
print(T[(T.dev.abs() >= 10) & (T.others_spread <= 3)].sort_values('dev')[['model_id', 'benchmark_id', 'metric', 'pclass', 'proto', 'paper', 'self', 'dev', 'others_spread', 'n_others']].round(1).to_string())
# no-consensus tuples: >=3 papers but others disagree too
amb = T.groupby(key).apply(lambda g: (g.others_spread > 5).all()); print(f'\n>=3-paper tuples where no paper is a clear lone dissenter (every leave-one-out spread > 5): {amb.sum()} of {ntup}')
T.to_pickle(f'{V5DIR}/triangulation_relaxed.pkl')
