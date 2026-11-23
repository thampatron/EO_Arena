"""Shared helpers for the ablation scripts (ablation_*.py). Uses the pipeline in robust_lib unchanged.

Workbook location: EOARENA_WORKBOOK_DIR (not in this repo). Outputs: EOARENA_OUT, default data/robustness.
Outputs are aggregate statistics only; no workbook scores are written.
"""
import os, sys, json, time, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ARGV = list(sys.argv)                                    # robust_lib rewrites sys.argv while loading; keep ours
import robust_lib as R
OUTD = R.OUTD

def shard_args(argv=None):
    """`script.py [SHARD NSHARDS]` -> (shard, nshards); default one shard."""
    a = [x for x in (ARGV[1:] if argv is None else argv) if x.isdigit()]
    return (int(a[0]), int(a[1])) if len(a) >= 2 else (0, 1)

def lb_cv(D, seed=0, folds=5, min_keep=4):
    """Held-out pairwise ranking accuracy of a plain leaderboard, on the same fold scheme as R.cvK.
    Leaderboard = a GeoFM's mean within-setting z-score over its training cells."""
    Y, mask = D['Y'], D['mask']; rng = np.random.default_rng(seed); cells = np.argwhere(mask); per = mask.sum(0)
    cand = cells[per[cells[:, 1]] > min_keep]; rng.shuffle(cand); fid = np.arange(len(cand)) % folds; acc = []
    for f in range(folds):
        held = cand[fid == f]; m2 = mask.copy(); m2[held[:, 0], held[:, 1]] = False; bad = m2.sum(0) < min_keep
        if bad.any(): back = bad[held[:, 1]]; m2[held[back, 0], held[back, 1]] = True; held = held[~back]
        Z = np.full(Y.shape, np.nan)
        for t in range(Y.shape[1]):
            o = m2[:, t]; sd = Y[o, t].std(ddof=1) if o.sum() > 1 else 0
            if sd > 0: Z[o, t] = (Y[o, t] - Y[o, t].mean()) / sd
        with np.errstate(all='ignore'): lb = np.nanmean(Z, axis=1)
        lb = np.where(np.isnan(lb), 0.0, lb)
        df = pd.DataFrame({'t': held[:, 1], 'y': Y[held[:, 0], held[:, 1]], 'p': lb[held[:, 0]]}); ok = tot = 0
        for _, g in df.groupby('t'):
            if len(g) < 2: continue
            dy = np.sign(g.y.values[:, None] - g.y.values[None, :]); dp = np.sign(g.p.values[:, None] - g.p.values[None, :]); iu = np.triu_indices(len(g), 1); k = dy[iu] != 0
            ok += float(np.where(dp[iu][k] == 0, 0.5, (dy[iu][k] == dp[iu][k])).sum()); tot += int(k.sum())
        acc.append(ok / tot if tot else np.nan)
    return float(np.nanmean(acc))

def held_out(D, seeds=(0,), Ks=(1, 2)):
    """Held-out accuracy of the fitted model at each K and of the leaderboard, averaged over fold seeds."""
    c = R.cvK(D, Ks=Ks, seeds=seeds); o = {f'acc_K{k}': c[k] for k in Ks}; o.update({f'se_K{k}': c[f'se{k}'] for k in Ks})
    o['acc_LB'] = float(np.mean([lb_cv(D, seed=s) for s in seeds])); return o

def run_jobs(specs, job, out_name, shard=0, nshards=1):
    """Run job(spec) for this shard's specs, appending one JSON line each; resumable by spec['name']."""
    out = os.path.join(OUTD, f'{out_name}_{shard}.jsonl'); t0 = time.time()
    done = {json.loads(l)['name'] for l in open(out)} if os.path.exists(out) else set()
    todo = [s for i, s in enumerate(specs) if i % nshards == shard and s['name'] not in done]; print('jobs', len(todo), '->', out, flush=True)
    with open(out, 'a') as fh:
        for s in todo:
            try: r = {**s, **job(s)}
            except Exception as e: r = {**s, 'error': repr(e)}
            fh.write(json.dumps(r, default=float) + '\n'); fh.flush(); print(f'[{time.time()-t0:5.0f}s]', s['name'], r.get('error') or '', flush=True)
    print('DONE', flush=True)

def read_jobs(out_name):
    import glob
    return [json.loads(l) for f in sorted(glob.glob(os.path.join(OUTD, f'{out_name}_*.jsonl'))) for l in open(f)]

def sensor_of_tasks(D): return np.array([R.NA.get(n, {}).get('sensor') or '' for n in D['td']])
