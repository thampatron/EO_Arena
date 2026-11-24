import os as _o
V5DIR = _o.environ.get('V5DIR', '/home/claude/v5out'); WB5 = _o.environ.get('WB5CSV', '/home/claude/wb5')
import numpy as np, pandas as pd
rng = np.random.default_rng(2)
L = pd.read_pickle(f'{V5DIR}/long_res_pts.pkl'); d = L[L.res.notna()].copy(); d['shifted'] = d.variant.isin({'no_overlap','superset','ood_test'})
def icc(df, col='y'):
    x = df.copy(); x['c'] = x[col] - x.groupby('task')[col].transform('mean')
    c = x.groupby(['family','canonical_dataset','paper_key']).c.mean().reset_index()
    c = c[c.groupby(['family','canonical_dataset']).paper_key.transform('size') >= 2]
    G = c.groupby(['family','canonical_dataset']).c; k = G.size(); gm = c.c.mean()
    ssb = (k*(G.mean()-gm)**2).sum(); ssw = ((c.c - G.transform('mean'))**2).sum(); a, N = len(k), len(c)
    msb, msw = ssb/(a-1), ssw/(N-a); k0 = (N-(k**2).sum()/N)/(a-1); return (msb-msw)/(msb+(k0-1)*msw)
for col in ['y', 'rank']:
    b = icc(d, col); print(f'\n[{col}] ICC all {b:.3f}')
    for name, m in [('drop |t|>3', d.t.abs()>3), ('drop p_out>0.5', d.p_out>0.5), ('drop shifted', d.shifted)]:
        rr = [icc(d.drop(rng.choice(d.index, m.sum(), replace=False)), col) for _ in range(50)]
        print(f'  {name:16s} n={m.sum():4d}: {icc(d[~m], col):.3f}  random {np.mean(rr):.3f} [{np.percentile(rr,5):.3f},{np.percentile(rr,95):.3f}]')
    # winsorise residual-defined outliers instead of dropping: pull y back to pred + 3*s_d
    if col == 'y':
        w = d.copy(); lim = 3*w.s_d; adj = np.clip(w.res, -lim, lim) - w.res; w['y'] = w.y + adj
        print(f'  winsorise at 3 SD: {icc(w, col):.3f}')
