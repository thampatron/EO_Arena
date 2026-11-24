"""Where the outliers are, whether removing them could fix cross-paper agreement, and a paper-level held-out test."""
import os as _o
V5DIR = _o.environ.get('V5DIR', '/home/claude/v5out'); WB5 = _o.environ.get('WB5CSV', '/home/claude/wb5')

import numpy as np, pandas as pd
from scipy import stats
rng = np.random.default_rng(1); pd.set_option('display.width', 220)
L = pd.read_pickle(f'{V5DIR}/long_res_pts.pkl'); d = L[L.res.notna()].copy()
SHIFT = {'no_overlap', 'superset', 'ood_test'}
d['shifted'] = d.variant.isin(SHIFT); d['direct'] = pd.cut(d.n_direct, [-1, 0, 1, 99], labels=['0 other papers', '1 other paper', '>=2 other papers'])
f = lambda h: pd.Series(dict(scores=len(h), share_t3=(h.t.abs() > 3).mean(), mix_share=h.p_out.mean()))
print(d.groupby('direct', observed=True).apply(f).round(3)); print(d.groupby('shifted').apply(f).round(3)); print(d.groupby('pclass').apply(f).round(3))
clean = d[(~d.shifted) & (d.n_direct >= 1)]
print('\nclean subset (in-distribution, family x dataset reported elsewhere):', len(clean), 'share |t|>3', round((clean.t.abs() > 3).mean(), 4), 'mixture share', round(clean.p_out.mean(), 3))
pr = (clean.t.abs() > 3).mean()
g = clean.groupby('paper_key').agg(scores=('t', 'size'), n3=('t', lambda x: (x.abs() > 3).sum()), mix=('p_out', 'mean'))
g['p'] = [stats.binom.sf(k - 1, n, pr) for k, n in zip(g.n3, g.scores)]; g['q_holm'] = np.minimum(1, np.sort(g.p.values) * (len(g) - np.arange(len(g))))[np.argsort(np.argsort(g.p.values))]
print(g.sort_values('p').round(4).head(10))
chi = ((g.n3 - g.scores * pr) ** 2 / (g.scores * pr)).sum(); print('overdispersion chi2', round(chi, 1), 'df', len(g) - 1, 'p', stats.chi2.sf(chi, len(g) - 1))

# ---- ICC of a single paper's (setting-centred z) value for a family x dataset cell ----
def icc(df):
    x = df.copy(); x['zc'] = x.z - x.groupby('task').z.transform('mean')
    c = x.groupby(['family', 'canonical_dataset', 'paper_key']).zc.mean().reset_index()
    c = c[c.groupby(['family', 'canonical_dataset']).paper_key.transform('size') >= 2]
    grp = c.groupby(['family', 'canonical_dataset']).zc; k = grp.size(); gm = c.zc.mean()
    ssb = (k * (grp.mean() - gm) ** 2).sum(); ssw = ((c.zc - c.groupby(['family', 'canonical_dataset']).zc.transform('mean')) ** 2).sum()
    a = len(k); N = len(c); msb, msw = ssb / (a - 1), ssw / (N - a); k0 = (N - (k ** 2).sum() / N) / (a - 1)
    return (msb - msw) / (msb + (k0 - 1) * msw), a
base, a0 = icc(d); print(f'\nICC single paper, all scored rows: {base:.3f} over {a0} replicated cells')
out = {}
for name, mask in [('drop |t|>3', d.t.abs() > 3), ('drop p_out>0.5', d.p_out > 0.5), ('drop shifted settings', d.shifted)]:
    v, a = icc(d[~mask]); rr = [icc(d.drop(rng.choice(d.index, mask.sum(), replace=False)))[0] for _ in range(50)]
    print(f'{name:28s} removes {mask.sum():4d}: ICC {v:.3f} ({a} cells); random removal of same count {np.mean(rr):.3f} [{np.percentile(rr,5):.3f},{np.percentile(rr,95):.3f}]')
for k in (1, 2, 3, 4):
    top = list(g.sort_values('p').index[:k]); v, a = icc(d[~d.paper_key.isin(top)])
    rr = [icc(d[~d.paper_key.isin(rng.choice(g.index, k, replace=False))])[0] for _ in range(60)]
    print(f'drop {k} most outlier-heavy papers {top}: ICC {v:.3f} ({a} cells); random {k} papers {np.nanmean(rr):.3f} [{np.nanpercentile(rr,5):.3f},{np.nanpercentile(rr,95):.3f}]')

# ---- paper-level held-out test: rank papers by outlier share on half the datasets, drop the worst 2, measure ICC on the other half ----
ds = d.canonical_dataset.unique(); res = []
for rep in range(60):
    A = set(rng.choice(ds, len(ds) // 2, replace=False)); dA, dB = d[d.canonical_dataset.isin(A)], d[~d.canonical_dataset.isin(A)]
    sh = dA.groupby('paper_key').p_out.mean()[dA.groupby('paper_key').size() >= 20]
    papersB = set(dB.paper_key)
    worst = [p for p in sh.sort_values(ascending=False).index if p in papersB][:2]
    if len(worst) < 2: continue
    b0 = icc(dB)[0]; bw = icc(dB[~dB.paper_key.isin(worst)])[0]
    cand = sorted(papersB & set(sh.index)); br = np.nanmean([icc(dB[~dB.paper_key.isin(rng.choice(cand, 2, replace=False))])[0] for _ in range(20)])
    res.append((b0, bw, br, worst))
r = pd.DataFrame(res, columns=['base', 'drop_worst2', 'drop_random2', 'worst'])
print('\nheld-out paper test (60 splits):', r[['base', 'drop_worst2', 'drop_random2']].mean().round(3).to_dict(), '| worst beats random in', round((r.drop_worst2 > r.drop_random2).mean(), 2), 'of splits')
print('papers chosen as worst on half A:', pd.Series([p for w in r.worst for p in w]).value_counts().to_dict())
clean.to_pickle(f'{V5DIR}/clean_pts.pkl')
