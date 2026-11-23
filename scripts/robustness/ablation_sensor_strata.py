"""Held-out test within each task sensor and on sensor-matched scores only, plus fold-seed stability of the K = 2 gain.

    python ablation_sensor_strata.py [SHARD NSHARDS]   ->  <EOARENA_OUT>/sensor_strata_<shard>.jsonl

Family-level unit (the pipeline's merged families). "Matched" keeps a score only where the family's pretraining
imagery matches the task sensor: multispectral tasks x (multispectral optical, multi-sensor) families; SAR + optical
tasks x multi-sensor families; high-resolution tasks x high-resolution-RGB families.
"""
import numpy as np
import ablation_lib as A
from ablation_lib import R
D0 = R.load(); pg = np.array([R.pre_of(m) for m in D0['models']]); ts = A.sensor_of_tasks(D0)
MATCH = {'multispectral': ('multispectral optical', 'multi-sensor (SAR + optical)'), 'SAR + optical': ('multi-sensor (SAR + optical)',), 'high-resolution optical': ('high-resolution RGB',)}
def build(s):
    k = s['kind']
    if k == 'base': return D0
    if k == 'no_family': return R.sub(D0, rows=np.array([m != s['key'] for m in D0['models']]))
    if k == 'sensor': return R.sub(D0, cols=ts == s['key'])
    if k == 'sensor_matched': return R.sub(D0, cols=ts == s['key'], rows=np.isin(pg, MATCH[s['key']]))
    if k == 'pooled_3sensors': return R.sub(D0, cols=np.isin(ts, list(MATCH)))
    if k == 'pooled_matched':
        m = D0['mask'].copy()
        for sen, grp in MATCH.items(): m[np.ix_(~np.isin(pg, grp), ts == sen)] = False
        return R.sub(D0, mask=m, cols=np.isin(ts, list(MATCH)))
    raise ValueError(k)
def job(s):
    D = build(s); seeds = tuple(s.get('seeds', (0, 1))); o = {'families': len(D['models']), 'tasks': len(D['tasks']), 'scores': int(D['mask'].sum()), 'datasets': len(set(D['td']))}
    o.update(A.held_out(D, seeds=seeds))
    if s.get('per_seed'): o['K2_by_seed'] = [R.cvK(D, Ks=(2,), seeds=(x,))[2] for x in seeds]
    return o
if __name__ == '__main__':
    S = [{'name': 'base_3seeds', 'kind': 'base', 'seeds': (0, 1, 2), 'per_seed': True}, {'name': 'no_terrafm_3seeds', 'kind': 'no_family', 'key': 'terrafm', 'seeds': (0, 1, 2), 'per_seed': True}]
    S += [{'name': f'{k}:{sen}', 'kind': k, 'key': sen} for sen in MATCH for k in ('sensor', 'sensor_matched')]
    S += [{'name': 'pooled_3sensors', 'kind': 'pooled_3sensors'}, {'name': 'pooled_matched', 'kind': 'pooled_matched'}]
    A.run_jobs(S, job, 'sensor_strata', *A.shard_args())
