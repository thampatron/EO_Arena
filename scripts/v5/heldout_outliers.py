import os as _o
V5DIR = _o.environ.get('V5DIR', '/home/claude/v5out'); WB5 = _o.environ.get('WB5CSV', '/home/claude/wb5')
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/repo/scripts/robustness'); sys.path.insert(0, '/home/claude/repo/scripts')
import robust_lib as R, ablation_lib as A
D = R.load(); L = pd.read_pickle(f'{V5DIR}/long_res_pts.pkl'); mi = {m: i for i, m in enumerate(D['models'])}
def masked(sel):
    M = D['mask'].copy()
    for f, j in zip(sel.family, sel.j): M[mi[f], j] = False
    return R.sub(D, mask=M)
rng = np.random.default_rng(3); d = L[L.res.notna()]
specs = [('all', None), ('drop_t3', d[d.t.abs() > 3]), ('drop_pout', d[d.p_out > 0.5])]
for k in range(2): specs.append((f'random_{k}', d.loc[rng.choice(d.index, (d.t.abs() > 3).sum(), replace=False)]))
specs.append(('no_terrafm', None))
out = open(f'{V5DIR}/heldout_outliers.jsonl', 'a')
for name, sel in specs:
    if name == 'no_terrafm': DD = R.sub(D, rows=np.array([not m.startswith('terrafm') for m in D['models']]))
    else: DD = D if sel is None else masked(sel)
    o = A.held_out(DD, seeds=(0, 1, 2)); o.update(name=name, scores=int(DD['mask'].sum())); out.write(json.dumps(o, default=float) + '\n'); out.flush(); print(o, flush=True)
