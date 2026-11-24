"""Leave-one-paper-out test of the paper x family offset (the 'implementation effect') in the note's Eq. 9.

The held-out cell test rewards a model that learns how each paper sees each family, because held-out cells share their paper's
offset with training cells. The question that matters for capability estimates is different: does absorbing lab offsets into
c_{m,p} give latent capabilities that better predict how an UNSEEN paper orders families on a known dataset? Here every task of
one paper is dropped, the model is refitted with and without paper offsets (the held-out paper has no offset: c = 0), and the
dropped tasks' orderings are predicted from their dataset/protocol/sensor blocks (db.leave_one_paper_out, the pipeline's own
LOPO; 'struct' = structured prediction, 'board' = plain leaderboard of training z-scores, 'global' = mean predicted score).
Usage: EOARENA_WORKBOOK_DIR=<xlsx dir> python3 -I heldout_lopo_lab.py <v4 sources.csv> <out.json> [K]
"""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'robustness')); sys.path.insert(0, os.path.join(HERE, '..'))
ARGS = list(sys.argv)
import robust_lib as R, dataset_benchmarking as db
D = R.load(); v4 = set(pd.read_csv(ARGS[1]).paper_key); K = int(ARGS[3]) if len(ARGS) > 3 else 2
tp = np.asarray(D['tp']); pidx = pd.factorize(tp)[0]
KW = dict(ridge_u=R.RID, ridge_theta=R.RID, ridge_g={k: R.RID for k in D['G']}, n_restarts=2, n_iter=200, tol=1e-6, prior_group=D['FAM'])
out = {}
def summ(df):
    w = df.n_pairs.clip(lower=1)
    r = {'tasks': int(len(df)), 'papers': int(df.paper.nunique())}
    for c in ('acc_struct', 'acc_board', 'acc_global', 'rho_struct', 'rho_board', 'rho_anch', 'rho_half_board'):
        x = df[c]; ok = x.notna(); r[c] = float(np.average(x[ok], weights=w[ok])) if ok.any() else None
    pm = df.groupby('paper')[['acc_struct', 'acc_board']].mean().dropna(); r['paper_level_struct_minus_board'] = float((pm.acc_struct - pm.acc_board).mean())
    return r
rows = {}
for nm, extra in (('base', {}), ('paper_offset', {'paper': pidx})):
    df = db.leave_one_paper_out(D['Y'], D['mask'], tp, K, D['G'], **KW, **extra); df['v4'] = df.paper.isin(v4); rows[nm] = df
    out[nm] = {'all': summ(df), 'v4 papers': summ(df[df.v4]), 'new papers': summ(df[~df.v4])}; print(nm, out[nm], flush=True)
    json.dump(out, open(ARGS[2], 'w'), indent=1)
a, b = rows['base'].set_index(['paper', 'task']), rows['paper_offset'].set_index(['paper', 'task']); j = a.join(b, rsuffix='_off', how='inner')
pm = j.groupby(level=0)[['acc_struct', 'acc_struct_off']].mean().dropna(); d = pm.acc_struct_off - pm.acc_struct
rng = np.random.default_rng(0); bs = [d.sample(len(d), replace=True, random_state=int(s)).mean() for s in rng.integers(0, 1 << 30, 2000)]
out['offset_minus_base_paper_level'] = {'mean': float(d.mean()), 'ci90': [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))], 'papers': int(len(d)), 'share_better': float((d > 0).mean())}
print(out['offset_minus_base_paper_level']); json.dump(out, open(ARGS[2], 'w'), indent=1)
