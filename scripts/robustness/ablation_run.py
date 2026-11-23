"""Ablations of the family-level fit: remove each dataset, each GeoFM family, and random halves / quarters.

    python ablation_run.py [SHARD NSHARDS] [--cv-all]

Every run recomputes R.findings (label tests, coverage, protocol ratio, sensor match, similarity-map agreement).
The held-out test (K = 1, 2 and a leaderboard) is run for the base fit, every single-family removal, the ten
most-reported single-dataset removals and five random halves of each kind; --cv-all adds every dataset removal.
Output: <EOARENA_OUT>/ablation_<shard>.jsonl. Summarise with ablation_summary.py.
"""
import collections, numpy as np
import ablation_lib as A
from ablation_lib import R
D0 = R.load(); f0, _ = R.fit(D0); names0, Ld0, *_ = R.dataset_loadings(D0, f0); REF = (names0, Ld0.tolist())

def build(s):
    rng = np.random.default_rng(s.get('seed', 0)); g = s['group']
    if g == 'base': return D0
    if g == 'leave_one_dataset_out': return R.sub(D0, cols=D0['td'] != s['key'])
    if g == 'leave_one_family_out': return R.sub(D0, rows=np.array([m != s['key'] for m in D0['models']]))
    if g == 'sub_datasets':
        ds = sorted(set(D0['td'])); keep = set(rng.choice(ds, int(len(ds) * s['frac']), replace=False)); return R.sub(D0, cols=np.array([d in keep for d in D0['td']]))
    if g == 'sub_families':
        ms = list(D0['models']); keep = set(rng.choice(ms, int(len(ms) * s['frac']), replace=False)); return R.sub(D0, rows=np.array([m in keep for m in ms]))
    raise ValueError(g)

def job(s):
    D = build(s); o = {k: v for k, v in R.findings(D, cv=False, ref=REF, nperm=500).items() if not k.startswith('_')}
    if s.get('cv'): o.update(A.held_out(D, seeds=tuple(s.get('seeds', (0,)))))
    return o

if __name__ == '__main__':
    cv_all = '--cv-all' in A.ARGV; ntask = collections.Counter(D0['td']); topd = {d for d, _ in ntask.most_common(10)}
    S = [{'name': 'base', 'group': 'base', 'cv': True, 'seeds': (0, 1, 2)}]
    S += [{'name': f'lofo:{m}', 'group': 'leave_one_family_out', 'key': m, 'cv': True} for m in D0['models']]
    S += [{'name': f'lodo:{d}', 'group': 'leave_one_dataset_out', 'key': d, 'cv': cv_all or d in topd} for d in sorted(ntask)]
    S += [{'name': f'{g}_50_cv#{i}', 'group': g, 'frac': 0.5, 'seed': 100 + i, 'cv': True} for g in ('sub_datasets', 'sub_families') for i in range(5)]
    S += [{'name': f'{g}_{int(fr*100)}#{i}', 'group': g, 'frac': fr, 'seed': i} for g in ('sub_datasets', 'sub_families') for fr in (0.5, 0.75) for i in range(20)]
    A.run_jobs(S, job, 'ablation', *A.shard_args())
