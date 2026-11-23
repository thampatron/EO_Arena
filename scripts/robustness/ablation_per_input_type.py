"""The analysis repeated separately for each input type, with ONE MODEL PER FAMILY.

    python ablation_per_input_type.py [SHARD NSHARDS]   ->  <EOARENA_OUT>/per_input_type_<shard>.jsonl

EXPLORATORY. This is not the frozen unit of analysis (D19, variants averaged per family). Here:
  - the unmerged model matrix is loaded (R.load(flags=()));
  - families are widened so that version lines count once (BRAND below; all SSL4EO baselines are one family);
  - within an input type, each family is represented by a single checkpoint, the one with the most scores in that
    input type (ties: larger size tier). No averaging over variants.
For each input type: R.findings (label tests, protocol ratio), held-out K = 1, 2, 3 and a leaderboard, cross-paper
rank agreement, and mean rank percentile by pretraining imagery.
"""
import collections, numpy as np, pandas as pd
from scipy.stats import spearmanr
import ablation_lib as A
from ablation_lib import R
ATT = R.ATT; D0 = R.load(flags=()); models = D0['models']; ts = A.sensor_of_tasks(D0)
BRAND = {'skysense_v2': 'skysense', 'prithvi_v1': 'prithvi', 'prithvi_v2': 'prithvi', 'dofa_plus': 'dofa', 'tessera_v2_l': 'tessera', 'satlas_aerial': 'satlas', 'satlas_s1': 'satlas', 'satlas_s2': 'satlas', 'satmae_pp': 'satmae'}
def brand(m):
    f = ATT.get(m, {}).get('family', m); return 'ssl4eo' if 'ssl4eo' in f else BRAND.get(f, f)
br = np.array([brand(m) for m in models]); pre = lambda m: ATT.get(m, {}).get('pretraining') or ''

def build(sen):
    cols = ts == sen; n = D0['mask'][:, cols].sum(1); keep = np.zeros(len(models), bool); chosen = {}
    for b in sorted(set(br)):
        idx = np.where(br == b)[0]; idx = idx[n[idx] > 0]
        if len(idx) == 0: continue
        best = max(idx, key=lambda i: (n[i], ATT.get(models[i], {}).get('size_tier') or 0)); keep[best] = True
        chosen[b] = {'model': models[best], 'scores': int(n[best]), 'family_scores': int(n[idx].sum()), 'variants': len(idx)}
    return R.sub(D0, cols=cols, rows=keep), chosen, int(D0['mask'][:, cols].sum())

def cross_paper(D, min_shared=4):
    """Median Spearman between two sources reporting the same dataset under the same protocol."""
    Y, M, td, tp, pf = D['Y'], D['mask'], D['td'], D['tp'], D['pf']; rs = []
    for n in set(td):
        ix = np.where(td == n)[0]
        for a in range(len(ix)):
            for b in range(a + 1, len(ix)):
                i, j = ix[a], ix[b]
                if tp[i] == tp[j] or pf[i] != pf[j]: continue
                o = M[:, i] & M[:, j]
                if o.sum() >= min_shared: rs.append(spearmanr(Y[o, i], Y[o, j])[0])
    rs = [r for r in rs if r == r]; return (float(np.median(rs)), len(rs)) if rs else (None, 0)

def pretraining_ranks(D):
    acc = collections.defaultdict(list); pg = np.array([pre(m) for m in D['models']])
    for t in range(D['mask'].shape[1]):
        o = D['mask'][:, t]
        if o.sum() < 4: continue
        rk = (pd.Series(D['Y'][o, t]).rank().values - 1) / (o.sum() - 1) * 100
        for g in set(pg[o]):
            if g: acc[g].append(rk[pg[o] == g].mean())
    return {g: {'mean_rank': float(np.mean(v)), 'settings': len(v), 'models': int((pg == g).sum())} for g, v in acc.items()}

def job(s):
    D, chosen, raw = build(s['key'])
    o = {'scores_all_variants': raw, 'models': len(D['models']), 'tasks': len(D['tasks']), 'scores': int(D['mask'].sum()), 'datasets': len(set(D['td'])), 'sources': len(set(D['tp'])), 'chosen': chosen}
    o['cross_paper_rho'], o['cross_paper_pairs'] = cross_paper(D); o['pretraining_ranks'] = pretraining_ranks(D)
    try: o['findings'] = {k: v for k, v in R.findings(D, cv=False, nperm=1000).items() if not k.startswith('_')}
    except Exception as e: o['findings_error'] = repr(e)
    try: o.update(A.held_out(D, seeds=(0, 1), Ks=(1, 2, 3)))
    except Exception as e: o['cv_error'] = repr(e)
    return o

if __name__ == '__main__':
    S = [{'name': sen, 'key': sen} for sen in ('multispectral', 'SAR + optical', 'high-resolution optical', 'SAR')]
    A.run_jobs(S, job, 'per_input_type', *A.shard_args())
