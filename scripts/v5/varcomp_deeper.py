"""Follow-up to varcomp_decompose: where does the paper-level family variance (F x P) come from, and what does it imply for an
overall ranking (the family main effect F) as opposed to dataset-specific capability (F x D)?

1. Checkpoint level: refit with checkpoints as units (no family merge). If F x P is mostly a paper's choice of size / version
   within a family, it moves into F (checkpoint) and F x P shrinks.
2. Families reported by >= 3 papers, all scores and third-party scores only: F is then separable from F x P.
3. Reliability of one paper's overall verdict on a family (mean over k datasets) for an overall ranking:
   F / (F + FP + (FD + FDP + e) / k); papers needed for 0.8: 4 (FP + (FD + FDP + e)/k) / F.
Usage: EOARENA_WORKBOOK_DIR=<xlsx dir> python3 -I varcomp_deeper.py <long.pkl> <v4 sources.csv> <out.json>
"""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'robustness')); sys.path.insert(0, os.path.join(HERE, '..'))
ARGS = list(sys.argv)
import variance_components as VC, robust_lib as R, prefix
L = pd.read_pickle(ARGS[1]); L = L[L.pclass != 'other']; v4 = set(pd.read_csv(ARGS[2]).paper_key); L['v4paper'] = L.paper_key.isin(v4)
out = {}
def overall(s, k=5):
    noise = s['FP'] + (s['FD'] + s['FDP'] + s['e']) / k
    return {'rel_overall_one_paper_k5': s['F'] / (s['F'] + noise), 'papers_for_08_overall_k5': 4 * noise / max(s['F'], 1e-12)}
def fit(name, d, unit='family'):
    d = d.rename(columns={unit: 'family'}) if unit != 'family' else d
    cells = d.groupby(['family', 'canonical_dataset']).paper_key.nunique(); npap = d.groupby('family').paper_key.nunique()
    v, x, n = VC.fit(d, 'z'); s = VC.summary(v)
    out[name] = {'n_scores': n, 'units': int(d.family.nunique()), 'units_in_3plus_papers': int((npap >= 3).sum()), 'papers': int(d.paper_key.nunique()),
                 'replicated_cells': int((cells >= 2).sum()), **{k_: float(s[k_]) for k_ in ('F', 'FD', 'FP', 'FDP', 'FC', 'e', 'rel_one_score', 'papers_for_08')}, **overall(s)}
    print(name, {k_: (round(v_, 3) if isinstance(v_, float) else v_) for k_, v_ in out[name].items()}, flush=True)
# 2. families in >= 3 papers
for lab, d in (('all', L), ('v4 papers', L[L.v4paper]), ('new papers', L[~L.v4paper]), ('high-resolution optical', L[L.itype == 'high-resolution optical']),
               ('multispectral', L[L.itype == 'multispectral']), ('SAR + optical', L[L.itype == 'SAR + optical'])):
    for tp, dd in (('all scores', d), ('third-party only', d[~d.selfrep])):
        npap = dd.groupby('family').paper_key.nunique(); dd = dd[dd.family.isin(npap[npap >= 3].index)]
        dd = dd[dd.groupby('task').z.transform('size') >= 2]
        if dd.family.nunique() >= 8: fit(f'{lab} | {tp} | families in 3+ papers', dd)
json.dump(out, open(ARGS[3], 'w'), indent=1)
# 1. checkpoint level (no family merge): long table rebuilt from the pipeline without --merge-families
g = prefix.build(['--offset', 'none', '--skip-sim']); TI = g['TI'].reset_index(drop=True); Y, M = g['Y'], g['mask']; mods = list(g['models']); tasks = list(g['tasks'])
lc = g['lc']; sr = set(zip(lc.task[lc.selfrep.astype(bool)], lc.model_id[lc.selfrep.astype(bool)]))
rows = []
for j in range(len(tasks)):
    idx = np.where(M[:, j])[0]; y = Y[idx, j]; sd = y.std(ddof=1); z = (y - y.mean()) / sd if sd > 0 else np.zeros_like(y)
    for k_, i in enumerate(idx): rows.append((mods[i], R.unit_of(mods[i]), tasks[j], z[k_], (tasks[j], mods[i]) in sr))
C = pd.DataFrame(rows, columns=['ckpt', 'fam', 'task', 'z', 'selfrep'])
meta = L.drop_duplicates('task').set_index('task')[['paper_key', 'canonical_dataset', 'pclass', 'itype', 'shifted', 'v4paper']]
C = C[C.task.isin(meta.index)].join(meta, on='task')          # same settings as the family-level analysis
C = C[C.groupby('task').z.transform('size') >= 2]
for lab, d in (('all', C), ('v4 papers', C[C.v4paper]), ('new papers', C[~C.v4paper]), ('high-resolution optical', C[C.itype == 'high-resolution optical']),
               ('high-resolution optical | new papers', C[(C.itype == 'high-resolution optical') & ~C.v4paper]), ('multispectral', C[C.itype == 'multispectral'])):
    fit(f'checkpoint level | {lab}', d, unit='ckpt')
    dd = d.groupby(['fam', 'task'], as_index=False).agg(z=('z', 'mean'), selfrep=('selfrep', 'max')).join(meta, on='task')
    fit(f'family level, same settings | {lab}', dd[dd.groupby('task').z.transform('size') >= 2], unit='fam')
json.dump(out, open(ARGS[3], 'w'), indent=1); print('done')
