"""Held-out test of a signed self-report offset in the note's latent-factor model (Eq. 9).

y[m,t] = mu_t + u_m . theta_t + delta * sd_t * S[m,t] + e,   S = 1 when the paper of task t introduced GeoFM family m.
delta (in units of the task's training spread) is estimated inside each training fold by alternating: fit the pipeline's model on
y - delta*sd*S, then move delta by the mean training residual of self-reported minus third-party cells (3 rounds). Held-out
predictions add delta*sd*S back. Same folds, seeds and pairwise-accuracy metric as the pipeline (db.heldout_cell_cv), plus the
accuracy on held-out pairs that do not involve a self-report (the less biased target).
Usage: EOARENA_WORKBOOK_DIR=<xlsx dir> python3 -I heldout_selfrep.py <out.json>
"""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'robustness')); sys.path.insert(0, os.path.join(HERE, '..'))
ARGS = list(sys.argv)
import robust_lib as R, dataset_benchmarking as db
D = R.load(); Y, mask, S = D['Y'], D['mask'], D['selfrep'] & D['mask']
KW = dict(ridge_u=R.RID, ridge_theta=R.RID, ridge_g={k: R.RID for k in D['G']}, n_restarts=2, n_iter=200, tol=1e-6, prior_group=D['FAM'])
def acc(df):
    ok = tot = 0
    for _, g in df.groupby('t'):
        if len(g) < 2: continue
        dy = np.sign(g.y.values[:, None] - g.y.values[None, :]); dp = np.sign(g.p.values[:, None] - g.p.values[None, :]); iu = np.triu_indices(len(g), 1)
        k = dy[iu] != 0
        if 'third' in g: k &= (g.third.values[:, None] & g.third.values[None, :])[iu]
        ok += float(np.where(dp[iu][k] == 0, 0.5, dy[iu][k] == dp[iu][k]).sum()); tot += int(k.sum())
    return ok / tot if tot else np.nan
def run(K, seed, rounds, folds=5, min_keep=4):
    rng = np.random.default_rng(seed); cells = np.argwhere(mask); per = mask.sum(0); cand = cells[per[cells[:, 1]] > min_keep]; rng.shuffle(cand); fid = np.arange(len(cand)) % folds
    out = {'all': [], 'third_party_pairs': [], 'delta': []}
    for f in range(folds):
        held = cand[fid == f]; m2 = mask.copy(); m2[held[:, 0], held[:, 1]] = False; bad = m2.sum(0) < min_keep
        if bad.any(): back = bad[held[:, 1]]; m2[held[back, 0], held[back, 1]] = True; held = held[~back]
        sd = np.maximum(np.array([Y[m2[:, t], t].std(ddof=1) if m2[:, t].sum() > 1 else np.nan for t in range(Y.shape[1])]), 0.5)
        delta = 0.0; SD = np.nan_to_num(sd)[None, :] * S
        for it in range(max(rounds, 1)):
            Yc = np.where(mask, Y - delta * SD, Y); fit, psi = db.fit_heteroskedastic(Yc, m2, K, D['G'], seed=seed + f, **KW); P = fit.predict()
            if rounds == 0: break
            r = ((Yc - P) / sd[None, :]); tr = m2 & np.isfinite(r)
            delta += float(r[tr & S].mean() - r[tr & ~S].mean())
        Pf = P + delta * SD
        df = pd.DataFrame({'t': held[:, 1], 'y': Y[held[:, 0], held[:, 1]], 'p': Pf[held[:, 0], held[:, 1]]})
        out['all'].append(acc(df)); out['third_party_pairs'].append(acc(df.assign(third=~S[held[:, 0], held[:, 1]]))); out['delta'].append(delta)
    return {k: float(np.nanmean(v)) for k, v in out.items()}
res = {'selfrep_cells': int(S.sum()), 'cells': int(mask.sum())}
for K in (1, 2):
    for rounds, nm in ((0, 'base'), (3, 'selfrep_offset')):
        rs = [run(K, s, rounds) for s in (0, 1, 2)]
        res[f'{nm}_K{K}'] = {k: float(np.mean([r[k] for r in rs])) for k in rs[0]} | {'by_seed_all': [r['all'] for r in rs]}
        print(nm, K, res[f'{nm}_K{K}'], flush=True)
json.dump(res, open(ARGS[1], 'w'), indent=1)
