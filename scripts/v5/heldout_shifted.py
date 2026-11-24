import os as _o
V5DIR = _o.environ.get('V5DIR', '/home/claude/v5out'); WB5 = _o.environ.get('WB5CSV', '/home/claude/wb5')
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/repo/scripts/robustness'); sys.path.insert(0, '/home/claude/repo/scripts')
import robust_lib as R, ablation_lib as A
D = R.load(); L = pd.read_pickle(f'{V5DIR}/long_v5.pkl')
shifted_j = set(L[L.variant.isin({'no_overlap', 'superset', 'ood_test'})].j)
cols = np.array([j not in shifted_j for j in range(len(D['tasks']))]); out = open(f'{V5DIR}/heldout_shifted.jsonl', 'a')
for name, rows in [('no_shifted', None), ('no_shifted_no_terrafm', np.array([not m.startswith('terrafm') for m in D['models']]))]:
    DD = R.sub(D, cols=cols, rows=rows); o = A.held_out(DD, seeds=(0, 1, 2)); o.update(name=name, scores=int(DD['mask'].sum()), families=len(DD['models']))
    out.write(json.dumps(o, default=float) + '\n'); out.flush(); print(o, flush=True)
