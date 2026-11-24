"""Why is one published score less reliable in v5 than in v4? Exact REML variance components (within-setting z) on subsets of the
v5 analysed matrix: papers already in v4 vs papers new in v5, input types, without shifted / transfer settings, without the two
benchmark papers that carry most consensus outliers, third-party scores only. Each subset is refitted from scratch.
Usage: python3 -I varcomp_decompose.py <long.pkl> <v4 sources.csv> <out.json>   (aggregate statistics only)
"""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import variance_components as VC
L = pd.read_pickle(sys.argv[1]); L = L[L.pclass != 'other']; v4 = set(pd.read_csv(sys.argv[2]).paper_key); OUTP = sys.argv[3]
L['v4paper'] = L.paper_key.isin(v4); BENCH2 = {'geocross-bench', 'earthshift'}
subsets = [('all', L), ('v4 papers', L[L.v4paper]), ('new v5 papers', L[~L.v4paper]),
           ('no shifted settings', L[~L.shifted]), ('no geocross-bench / earthshift', L[~L.paper_key.isin(BENCH2)]),
           ('no shifted, no geocross/earthshift', L[~L.shifted & ~L.paper_key.isin(BENCH2)]), ('third-party scores only', L[~L.selfrep]),
           ('no high-resolution optical', L[L.itype != 'high-resolution optical'])]
for it in ('multispectral', 'SAR + optical', 'high-resolution optical'):
    subsets += [(f'{it}', L[L.itype == it]), (f'{it} | v4 papers', L[(L.itype == it) & L.v4paper]), (f'{it} | new papers', L[(L.itype == it) & ~L.v4paper])]
out = {}
for name, d in subsets:
    cells = d.groupby(['family', 'canonical_dataset']).paper_key.nunique()
    if (cells >= 2).sum() < 15: out[name] = {'skipped': 'fewer than 15 replicated cells', 'replicated_cells': int((cells >= 2).sum())}; continue
    v, x, n = VC.fit(d, 'z'); s = VC.summary(v)
    # how much each piece moves reliability: the share of the (lab + e) denominator
    rep = d[d.set_index(['family', 'canonical_dataset']).index.isin(cells[cells >= 2].index)]
    out[name] = {'n_scores': n, 'papers': int(d.paper_key.nunique()), 'families': int(d.family.nunique()), 'datasets': int(d.canonical_dataset.nunique()),
                 'replicated_cells': int((cells >= 2).sum()), 'papers_in_replicated_cells': int(rep.paper_key.nunique()),
                 'median_families_per_setting': float(d.groupby('task').size().median()), **{k: float(s[k]) for k in ('F', 'FD', 'FP', 'FDP', 'FC', 'e', 'lab', 'rel_one_score', 'papers_for_08', 'lab_over_signal')}}
    print(name, {k: (round(v_, 3) if isinstance(v_, float) else v_) for k, v_ in out[name].items()}, flush=True)
json.dump(out, open(OUTP, 'w'), indent=1)
