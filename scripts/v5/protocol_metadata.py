"""Does recorded protocol metadata explain cross-paper disagreement? (rewrite of the 2026-11-23 Analysis 2, extended for v5)

Pairs: checkpoint-level scores (pipeline inclusion rules, reprints removed, probe / decoder / fine-tune / PE classes) of the same
GeoFM family on the same canonical dataset, printed by two different papers. Response |difference| in points (points metrics).
Mismatch knobs: exact protocol, protocol class, metric, train fraction, checkpoint within family, benchmark_id, setting label;
plus self-reported involvement, leaderboard, model id inferred, appendix table, score level; v5 adds input modality and
temporal steps where both rows state them. OLS, each paper-pair x dataset cell weighted to 1, errors clustered by paper pair.
Also: lab SD / between-family SD by matching tier. Usage: python3 -I protocol_metadata.py <repo root> <workbook csv dir> <out.json>
"""
import os, sys, json, itertools, numpy as np, pandas as pd
ROOT = sys.argv[1]; sys.path.insert(0, os.path.join(ROOT, 'scripts', 'robustness')); sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import robust_lib as R, prefix
CSV = sys.argv[2]; OUTP = sys.argv[3]; rng = np.random.default_rng(0)
PTS = {'miou', 'acc', 'f1', 'acc_top1', 'r2', 'iou', 'map', 'micro_f1', 'oa', 'segm_map', 'mijacc', 'bal_acc', 'weighted_f1', 'acc_avg', 'macro_f1'}
def pclass(p): return 'ft' if p in ('FT', 'PFT') else 'dec' if p == 'frozen_dec' else 'pe' if p == 'PE' else 'other' if p == 'kmeans_clustering' else 'probe'
g = prefix.build(['--offset', 'none', '--skip-sim']); TI = g['TI']; lc = g['lc'].copy()
lc = lc.join(TI, on='task'); lc['family_unit'] = lc.model_id.map(R.unit_of); lc['pclass'] = lc.evaluation_protocol.map(pclass)
lc = lc[(lc.pclass != 'other') & lc.metric_s.isin(PTS) & (lc.canonical_dataset != '')].copy()
# raw-row attributes (model id inferred; v5 input modality / temporal steps) by (paper, model, benchmark, protocol, metric, fraction)
fn = [f for f in os.listdir(CSV) if f.endswith('results_long.csv')][0]
raw = pd.read_csv(os.path.join(CSV, fn), low_memory=False)
k = ['paper_key', 'model_id', 'benchmark_id', 'evaluation_protocol', 'metric', 'train_fraction_norm']
agg = {'model_id_inferred': ('model_id_inferred', lambda s: bool((s == 1).any() or (s.astype(str) == 'True').any()))}
if 'input_modality_norm' in raw: agg['modality'] = ('input_modality_norm', lambda s: s.dropna().astype(str).mode().iat[0] if s.notna().any() else '')
if 'input_temporal_steps' in raw: agg['tsteps'] = ('input_temporal_steps', lambda s: s.dropna().astype(str).mode().iat[0] if s.notna().any() else '')
ra = raw.groupby(k).agg(**agg).reset_index().rename(columns={'metric': 'metric_s'})
lc = lc.merge(ra, on=['paper_key', 'model_id', 'benchmark_id', 'evaluation_protocol', 'metric_s', 'train_fraction_norm'], how='left')
lc['row'] = np.arange(len(lc))
pairs = []
for (fam, ds), h in lc.groupby(['family_unit', 'canonical_dataset']):
    if h.paper_key.nunique() < 2: continue
    H = h.to_dict('records')
    for a, b in itertools.combinations(H, 2):
        if a['paper_key'] == b['paper_key']: continue
        if a['paper_key'] > b['paper_key']: a, b = b, a
        d = {'family': fam, 'dataset': ds, 'pp': a['paper_key'] + '~' + b['paper_key'], 'absdiff': abs(a['y'] - b['y']),
             'm_protocol': a['evaluation_protocol'] != b['evaluation_protocol'], 'm_class': a['pclass'] != b['pclass'], 'm_metric': a['metric_s'] != b['metric_s'],
             'm_fraction': str(a['train_fraction_norm']) != str(b['train_fraction_norm']), 'm_checkpoint': a['model_id'] != b['model_id'],
             'm_benchmark': a['benchmark_id'] != b['benchmark_id'], 'm_setting': str(a['variant']) != str(b['variant']),
             'any_self': bool(a['selfrep'] or b['selfrep']), 'leaderboard': bool(a['is_leaderboard'] or b['is_leaderboard']),
             'inferred': bool(a.get('model_id_inferred') is True or b.get('model_id_inferred') is True),
             'appendix': a['location'] == 'appendix' or b['location'] == 'appendix', 'level': 100 - (a['y'] + b['y']) / 2}
        if 'modality' in a:
            ma, mb = str(a.get('modality') or ''), str(b.get('modality') or ''); d['modality_known'] = bool(ma and mb and ma != 'nan' and mb != 'nan'); d['m_modality'] = d['modality_known'] and ma != mb
            ta, tb = str(a.get('tsteps') or ''), str(b.get('tsteps') or ''); d['tsteps_known'] = bool(ta and tb and ta != 'nan' and tb != 'nan'); d['m_tsteps'] = d['tsteps_known'] and ta != tb
        pairs.append(d)
P = pd.DataFrame(pairs); P['cell'] = P.pp + '|' + P.dataset
P['w'] = 1.0 / P.groupby('cell').absdiff.transform('size')
knobs = ['m_setting', 'm_fraction', 'm_benchmark', 'm_metric', 'm_protocol', 'm_class', 'm_checkpoint']
def boot_median(x, cl, B=1000):
    u = cl.unique(); idx = {c: np.where(cl.values == c)[0] for c in u}; out = []
    for _ in range(B):
        s = rng.choice(u, len(u)); out.append(np.median(np.concatenate([x.values[idx[c]] for c in s])))
    return [float(np.percentile(out, 5)), float(np.percentile(out, 95))]
res = {'pairs': int(len(P)), 'paper_pairs': int(P.pp.nunique()), 'cells': int(P.groupby(['family', 'dataset']).ngroups), 'datasets': int(P.dataset.nunique()),
       'families': int(P.family.nunique()), 'papers': int(len(set(P.pp.str.split('~').str[0]) | set(P.pp.str.split('~').str[1])))}
res['share_mismatched'] = {k_: float(P[k_].mean()) for k_ in knobs}
full = ~P[knobs].any(axis=1)
tiers = {'all': P.index == P.index, 'same protocol, metric, fraction': ~P[['m_protocol', 'm_metric', 'm_fraction']].any(axis=1), 'fully matched on recorded knobs': full}
if 'm_modality' in P:
    tiers['fully matched + same stated input'] = full & P.modality_known & ~P.m_modality
res['median_absdiff'] = {}
for nm, m in tiers.items():
    x = P[m]
    res['median_absdiff'][nm] = {'median': float(x.absdiff.median()) if len(x) else None, 'ci90': boot_median(x.absdiff, x.pp) if x.pp.nunique() >= 3 else None, 'pairs': int(len(x)), 'paper_pairs': int(x.pp.nunique())}
res['marginal'] = {k_: {'matched': float(P[~P[k_]].absdiff.median()), 'mismatched': float(P[P[k_]].absdiff.median())} for k_ in knobs + ([c for c in ('m_modality', 'm_tsteps') if c in P])}
# weighted OLS with paper-pair clustered SEs
def ols(P, cols):
    X = np.column_stack([np.ones(len(P))] + [P[c].astype(float).values for c in cols]); y = P.absdiff.values; w = P.w.values
    XtW = X.T * w; A = np.linalg.inv(XtW @ X); b = A @ (XtW @ y); e = y - X @ b
    meat = np.zeros((X.shape[1], X.shape[1]))
    for c, ix in P.groupby('pp').indices.items():
        s = (X[ix] * (w[ix] * e[ix])[:, None]).sum(0); meat += np.outer(s, s)
    G = P.pp.nunique(); V = A @ meat @ A * G / (G - 1); se = np.sqrt(np.diag(V))
    r2 = 1 - (w * e ** 2).sum() / (w * (y - np.average(y, weights=w)) ** 2).sum()
    return {c: [float(b[i + 1]), float(b[i + 1] - 1.645 * se[i + 1]), float(b[i + 1] + 1.645 * se[i + 1])] for i, c in enumerate(cols)}, float(r2)
cols = knobs + ['any_self', 'leaderboard', 'inferred', 'appendix', 'level']
res['ols'], res['ols_r2'] = ols(P, cols)
if 'm_modality' in P:
    Q = P[P.modality_known]
    if Q.pp.nunique() >= 10: res['ols_modality_subset'], res['ols_modality_subset_r2'] = ols(Q, cols + ['m_modality']); res['modality_subset'] = {'pairs': int(len(Q)), 'paper_pairs': int(Q.pp.nunique()), 'mismatch_share': float(Q.m_modality.mean())}
    Q = P[P.tsteps_known]
    if Q.pp.nunique() >= 10: res['ols_tsteps_subset'], _ = ols(Q, cols + ['m_tsteps']); res['tsteps_subset'] = {'pairs': int(len(Q)), 'paper_pairs': int(Q.pp.nunique())}
# lab SD / between-family SD by tier (per family x dataset x paper-pair cell)
bf = lc.groupby('task').y.std(); lc['bfsd'] = lc.task.map(bf)
bsd = lc.groupby(['family_unit', 'canonical_dataset']).bfsd.median()
for nm, m in tiers.items():
    x = P[m]; c = x.groupby(['family', 'dataset', 'pp']).absdiff.apply(lambda s: np.sqrt((s ** 2).mean()) / np.sqrt(2)).reset_index()
    c['ratio'] = c.absdiff / c.set_index(['family', 'dataset']).index.map(bsd).values
    res['median_absdiff'][nm]['labsd_over_betweenfamilysd'] = float(c.ratio.median()) if len(c) else None
json.dump(res, open(OUTP, "w"), indent=1, default=float); print(json.dumps(res, indent=1, default=float)[:4000])
