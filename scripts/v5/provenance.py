"""Provenance and deduplication: how much of the literature is copied numbers, and what copying does to agreement and to the
variance components (rewrite of the 2026-11-23 Analysis 3, extended for v5).

1. Copy detector on raw workbook rows: two rows printed by different papers are a copy pair if they share the model id (or the
   GeoFM family unit, or the canonical dataset instead of benchmark_id), benchmark_id and metric, and their values are equal after
   rounding both to the coarser printed precision (parsed from raw_cell, moved to normalised units); "near" = within 0.05.
   The copy is the row the workbook labels re_citation when exactly one row of the pair carries the label, else the later release
   (the build's D6 order: release month, then arXiv number). The label wins over release order because revised arXiv versions
   reprint later papers.
2. Chance coincidence: exact-match rate of different-family pairs within 1 point, by printed precision; expected false calls.
3. Agreement with the workbook label (kappa); copy shares by paper; copy matrix (copy <- origin).
4. Three analysed matrices: repo as committed; dedup (repo minus residual calls); copies kept (labels ignored, D6 off).
   Agreement between papers (cross_paper definitions) with cluster bootstraps over paper pairs and over papers, and the exact
   REML variance components on the within-setting z scale for each matrix.
Usage: EOARENA_WORKBOOK_DIR=<xlsx dir> python3 -I provenance.py <repo root> <results_long.csv> <sources.csv> <out.json> [--no-varcomp]
Writes aggregate statistics only; paper names appear with counts.
"""
import os, sys, json, re, types, contextlib, io, itertools, numpy as np, pandas as pd
ARGS = list(sys.argv); ROOT, RAWF, SRCF, OUTP = ARGS[1:5]; NOVC = '--no-varcomp' in ARGS
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'robustness')); sys.path.insert(0, os.path.join(ROOT, 'scripts')); sys.path.insert(0, os.path.join(ROOT, 'scripts', 'v5'))
import robust_lib as R, prefix
from scipy.stats import spearmanr
rng = np.random.default_rng(0); OUT = {}
# raw printed values (copy matching), so r2 printed in percent is comparable here; analysis scales use protocol.PTS
PTS = {'miou', 'acc', 'f1', 'acc_top1', 'r2', 'iou', 'map', 'micro_f1', 'oa', 'segm_map', 'mijacc', 'bal_acc', 'weighted_f1', 'acc_avg', 'macro_f1'}

# ----------------------------------------------------------------------------------------------------------- 1. raw rows
raw = pd.read_csv(RAWF, low_memory=False); src = pd.read_csv(SRCF, low_memory=False).drop_duplicates('paper_key').set_index('paper_key')
raw['v'] = pd.to_numeric(raw.result_normalized, errors='coerce'); raw = raw[raw.v.notna()].copy()
# printed precision = decimals of the first number in raw_cell; for per-seed lists ("seeds 0: 71.23, 1: ...") the first number is
# a seed label, so read the first value after it instead
_rc = raw.raw_cell.astype(str); _seedv = _rc.str.extract(r'seeds?\s+\d+:\s*(-?\d+(?:\.\d+)?)')[0]; _rc = _seedv.where(_seedv.notna(), _rc)
num = _rc.str.extract(r'(-?\d+(?:\.(\d+))?)')
raw['dec'] = num[1].fillna('').str.len(); first = pd.to_numeric(num[0], errors='coerce')
scale = (raw.v / first).where((first.abs() > 0) & first.notna(), 1.0).abs()
scale = scale.where(np.isclose(scale, 1) | np.isclose(scale, 100, rtol=1e-3) | np.isclose(scale, 0.01, rtol=1e-3), 1.0)
raw['prec'] = 10.0 ** (-raw.dec) * scale
arx = src.identifier.astype(str).str.extract(r'(\d{4}\.\d{4,5})')[0].fillna('9999.99999')
raw['release'] = raw.paper_key.map((src.release_year_month.astype(str) + '|' + arx).to_dict()).fillna('9999') + '|' + raw.paper_key.astype(str)
raw['lab'] = raw.agreement_vs_recitation.eq('re_citation'); raw['unit'] = raw.model_id.astype(str).map(R.unit_of)
bmap = pd.read_csv(os.path.join(ROOT, 'data', 'benchmark_map.csv'), dtype=str).fillna('').set_index('benchmark_id')
raw['cds'] = raw.benchmark_id.map(bmap.canonical_dataset).fillna(''); raw['metric'] = raw.metric.astype(str)
raw['pts'] = raw.metric.isin(PTS) & raw.scale_basis.isin(['percent_printed', 'fraction_printed'])
OUT['raw_rows'] = {'rows': int(len(raw)), 'labelled_re_citation': int(raw.lab.sum()), 'self_reported': int((raw.is_self_reported == True).sum()),
                   'labelled_by_paper_top': raw[raw.lab].paper_key.value_counts().head(15).to_dict(), 'papers': int(raw.paper_key.nunique())}
print(OUT['raw_rows'], flush=True)

def pairs_on(keys, near=False):
    """Cross-paper row pairs sharing `keys`; returns DataFrame (i, j, exact, near, absdiff) with i, j raw indices."""
    out = []
    for _, h in raw.groupby(keys, sort=False):
        if len(h) < 2 or h.paper_key.nunique() < 2: continue
        ix = h.index.values; v = h.v.values; p = h.prec.values; pk = h.paper_key.values
        a, b = np.triu_indices(len(h), 1); m = pk[a] != pk[b]; a, b = a[m], b[m]
        pp = np.maximum(p[a], p[b]); ex = np.isclose(np.round(v[a] / pp), np.round(v[b] / pp)) & (np.abs(v[a] - v[b]) <= pp)
        out.append(pd.DataFrame({'i': ix[a], 'j': ix[b], 'exact': ex, 'near': np.abs(v[a] - v[b]) <= 0.05, 'absdiff': np.abs(v[a] - v[b]), 'dec': np.minimum(h.dec.values[a], h.dec.values[b])}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=['i', 'j', 'exact', 'near', 'absdiff', 'dec'])

def direct(P):
    """Orient pairs: copy, origin (label wins when exactly one row is labelled, else the later release is the copy)."""
    li, lj = raw.lab.reindex(P.i).values, raw.lab.reindex(P.j).values; ri, rj = raw.release.reindex(P.i).values, raw.release.reindex(P.j).values
    i_copy = np.where(li != lj, li, ri > rj)
    P = P.assign(cp=np.where(i_copy, P.i, P.j), origin=np.where(i_copy, P.j, P.i), label_vs_date=(li != lj) & (li != (ri > rj)))
    return P

Pm = direct(pairs_on(['model_id', 'benchmark_id', 'metric']))
Pf = direct(pairs_on(['unit', 'benchmark_id', 'metric']))
Pc = direct(pairs_on(['model_id', 'cds', 'metric']).pipe(lambda d: d[raw.cds.reindex(d.i).values != '']))
det = {'model_exact': set(Pm[Pm.exact].cp), 'family_exact': set(Pf[Pf.exact].cp), 'dataset_exact': set(Pc[Pc.exact].cp), 'model_near': set(Pm[Pm.near].cp)}
called = set().union(*det.values()); raw['called'] = raw.index.isin(called); raw['is_copy'] = raw.called | raw.lab
OUT['detector'] = {'model_pairs': int(len(Pm)), 'model_exact_pairs': int(Pm.exact.sum()), 'model_near_not_exact': int((Pm.near & ~Pm.exact).sum()),
                   'family_pairs': int(len(Pf)), 'family_exact_pairs': int(Pf.exact.sum()), 'label_contradicts_release_order': int(Pm[Pm.exact].label_vs_date.sum()),
                   'rows_called': {k: len(v) for k, v in det.items()}, 'rows_called_any': int(len(called))}
print(OUT['detector'], flush=True)

# ----------------------------------------------------------------------------------------------------------- 2. chance coincidence
def chance_pairs():
    out = []
    for _, h in raw[raw.pts].groupby(['benchmark_id', 'metric'], sort=False):
        if h.unit.nunique() < 2: continue
        h = h.sort_values('v'); v = h.v.values; p = h.prec.values; u = h.unit.values; pk = h.paper_key.values; d = h.dec.values
        for k in range(1, len(h)):
            a = np.arange(len(h) - k); b = a + k; m = (v[b] - v[a] <= 1.0)
            if not m.any(): break
            a, b = a[m], b[m]; m = (u[a] != u[b]) & (pk[a] != pk[b]); a, b = a[m], b[m]
            pp = np.maximum(p[a], p[b]); out.append(pd.DataFrame({'dec': np.minimum(d[a], d[b]), 'exact': np.isclose(np.round(v[a] / pp), np.round(v[b] / pp)) & (v[b] - v[a] <= pp), 'half': v[b] - v[a] <= 0.5}))
    return pd.concat(out, ignore_index=True)
C = chance_pairs(); rate = C.groupby(C.dec.clip(upper=4)).exact.mean()
fam1 = Pf[raw.pts.reindex(Pf.i).values & (Pf.absdiff <= 1.0)]
exp_false = fam1.dec.clip(upper=4).map(rate).fillna(1.0)
OUT['chance'] = {'cross_family_pairs_within_1pt': int(len(C)), 'exact_rate_by_decimals': {int(k): float(x) for k, x in rate.items()},
                 'exact_rate_1dec_within_half_point': float(C[(C.dec == 1) & C.half].exact.mean()) if ((C.dec == 1) & C.half).any() else None,
                 'same_family_pairs_within_1pt': int(len(fam1)), 'same_family_exact_within_1pt': int(fam1.exact.sum()), 'expected_chance_among_them': float(exp_false.sum()),
                 'by_decimals': {int(k): {'pairs': int(len(g)), 'observed_exact': int(g.exact.sum()), 'expected_chance': float(exp_false[g.index].sum())} for k, g in fam1.groupby(fam1.dec.clip(upper=4))}}
OUT['chance']['upper_bound_false_share'] = OUT['chance']['expected_chance_among_them'] / max(OUT['chance']['same_family_exact_within_1pt'], 1)
print(OUT['chance'], flush=True)

# ----------------------------------------------------------------------------------------------------------- 3. label agreement, shares
mex = det['model_exact'] | det['family_exact'] | det['dataset_exact']; lab = raw.lab.values; cal = raw.index.isin(mex)
po = (lab == cal).mean(); pe = lab.mean() * cal.mean() + (1 - lab.mean()) * (1 - cal.mean())
has_origin = raw.set_index(['model_id', 'benchmark_id', 'metric']).index
grp = raw.groupby(['model_id', 'benchmark_id', 'metric']).paper_key.transform('nunique') >= 2
lnc = raw[raw.lab & ~cal]
OUT['label_agreement'] = {'both': int((lab & cal).sum()), 'labelled_not_called': int((lab & ~cal).sum()),
                          'labelled_not_called_no_origin_row': int((~grp[lnc.index]).sum()), 'labelled_not_called_origin_differs': int(grp[lnc.index].sum()),
                          'called_not_labelled': int((~lab & cal).sum()), 'called_not_labelled_by_paper': raw[~raw.lab & cal].paper_key.value_counts().head(10).to_dict(),
                          'called_not_labelled_1dec_or_less': int(((~lab & cal) & (raw.dec.values <= 1)).sum()), 'kappa': float((po - pe) / (1 - pe))}
sh = raw.groupby('paper_key').agg(rows=('v', 'size'), copies=('is_copy', 'sum')); sh['share'] = sh.copies / sh.rows
allp = pd.concat([Pm[Pm.exact], Pf[Pf.exact], Pc[Pc.exact]]).drop_duplicates(['cp', 'origin'])
cm = pd.DataFrame({'copy': raw.paper_key.reindex(allp.cp).values, 'origin': raw.paper_key.reindex(allp.origin).values, 'row': allp.cp.values}).drop_duplicates(['copy', 'origin', 'row'])
cmx = cm.groupby(['copy', 'origin']).row.nunique().sort_values(ascending=False)
OUT['copy_shares'] = {'copy_rows': int(raw.is_copy.sum()), 'share': float(raw.is_copy.mean()), 'papers': int(len(sh)), 'papers_without_copies': int((sh.copies == 0).sum()),
                      'papers_under_5pct': int((sh.share < 0.05).sum()), 'papers_over_25pct': sh[sh.share > 0.25].share.round(2).sort_values(ascending=False).to_dict(),
                      'copy_matrix_top': {f'{a} <- {b}': int(n) for (a, b), n in cmx.head(25).items()},
                      'origins_most_copied': cm.groupby('origin').row.nunique().sort_values(ascending=False).head(10).to_dict()}
print(OUT['label_agreement'], {k: v for k, v in OUT['copy_shares'].items() if k != 'copy_matrix_top'}, flush=True)

# ----------------------------------------------------------------------------------------------------------- 4. matrices
_ev_path = os.path.join(ROOT, 'scripts', 'evidence_rows.py'); _ev_src = open(_ev_path).read(); _A = '(r.agreement_vs_recitation == "original")'; assert _A in _ev_src
_D6 = 'keep(~recited, "recitation of an earlier paper\'s value")'; _MARK = '# ============================================================================= 2. model-free tests'
LAST = {}
def ev_module(keep_lab):
    m = types.ModuleType('evidence_rows'); m.__file__ = _ev_path
    exec(compile(_ev_src.replace(_A, '(r.agreement_vs_recitation.isin(["original", "re_citation"]))') if keep_lab else _ev_src, _ev_path, 'exec'), m.__dict__); return m
def make_build(keep_copies=False, extra_drop=()):
    def build(flags=()):
        sys.argv = ['x', prefix.WB, *flags]; s = open(os.path.join(ROOT, 'scripts', 'build_dataset_analysis.py')).read(); s = s[:s.index(_MARK)]; assert _D6 in s
        if keep_copies: s = s.replace('assert (cell.n_rows == 1).all(), "a (task, model) cell still averages several rows"', 'pass  # copies kept: a recited and an original row may share a cell')
        s = s.replace(_D6, 'PRE_D6 = r.copy()\n' + ('keep(np.ones(len(r), bool), "D6 off")' if keep_copies else _D6) + '\nPOST_D6 = r.copy()\nkeep(~r.index.isin(EXTRA_DROP), "residual copies (provenance detector)")')
        sys.modules['evidence_rows'] = ev_module(keep_copies)
        g = {'__file__': os.path.join(ROOT, 'scripts', 'build_dataset_analysis.py'), '__name__': 'x', 'EXTRA_DROP': set(extra_drop)}
        with contextlib.redirect_stdout(io.StringIO()): exec(compile(s, 'b', 'exec'), g)
        sys.modules['evidence_rows'] = ev_module(False); LAST['g'] = g; return g
    return build
def load(keep_copies=False, extra_drop=()):
    prefix.build = make_build(keep_copies, extra_drop); D = R.load(); g = LAST['g']; r = g['r']
    assert (raw.paper_key.reindex(r.index).values == r.paper_key.values).all() and (raw.model_id.reindex(r.index).values == r.model_id.values).all()
    cp = r.index.isin(raw.index[raw.is_copy]); cpc = r.assign(fam=r.model_id.map(R.unit_of), c=cp).groupby(['task', 'fam']).c.any()
    ti = {t: k for k, t in enumerate(D['tasks'])}; mi = {m: k for k, m in enumerate(D['models'])}; CP = np.zeros(D['mask'].shape, bool)
    for (t, f), c in cpc.items():
        if c and t in ti and f in mi: CP[mi[f], ti[t]] = True
    D['copy'] = CP & D['mask']; D['pre_d6'] = g['PRE_D6']; D['post_d6'] = g['POST_D6']; D['r'] = r; return D

def agreement(D):
    Y, M, td, tp, pf, met, tf = D['Y'], D['mask'], D['td'], D['tp'], D['pf'], D['metric'], D['tf']; T = Y.shape[1]; rows = []
    for a, b in itertools.combinations(range(T), 2):
        if td[a] != td[b] or tp[a] == tp[b]: continue
        c = M[:, a] & M[:, b]
        if c.sum() < 4: continue
        pa, pb = sorted([tp[a], tp[b]]); same = pf[a] == pf[b]; setup = same and met[a] == met[b] and tf[a] == tf[b]
        rows.append(dict(dataset=td[a], pa=pa, pb=pb, rho=spearmanr(Y[c, a], Y[c, b]).correlation, same_protocol=bool(same), same_setup=bool(setup),
                         pts=met[a] in PTS, absdiff=float(np.median(np.abs(Y[c, a] - Y[c, b]))) if setup else np.nan))
    df = pd.DataFrame(rows)
    def wmed(x, w):
        o = np.argsort(x); x, w = x[o], w[o]; c = np.cumsum(w); return float(x[np.searchsorted(c, c[-1] / 2)])
    def summ(d, col='rho', B=1000):
        u = d.groupby(['dataset', 'pa', 'pb'])[col].agg('mean' if col == 'rho' else 'median').dropna().reset_index()
        if not len(u): return None
        u['pp'] = u.pa + '~' + u.pb; med = float(u[col].median()); res = {'median': med, 'units': int(len(u)), 'paper_pairs': int(u.pp.nunique()), 'datasets': int(u.dataset.nunique()),
                                                                             'papers': int(len(set(u.pa) | set(u.pb)))}
        if u.pp.nunique() >= 3:
            pps = u.pp.unique(); idx = {p: np.where(u.pp.values == p)[0] for p in pps}
            bs = [np.median(u[col].values[np.concatenate([idx[p] for p in rng.choice(pps, len(pps))])]) for _ in range(B)]; res['ci90_pp'] = [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))]
            papers = np.array(sorted(set(u.pa) | set(u.pb))); bs = []
            for _ in range(B):
                cnt = pd.Series(rng.choice(papers, len(papers))).value_counts(); w = u.pa.map(cnt).fillna(0).values * u.pb.map(cnt).fillna(0).values
                if w.sum() > 0: bs.append(wmed(u[col].values, w))
            res['ci90_p'] = [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))]
        return res
    ref = []; idx = rng.choice(T, (40000, 2))
    for a, b in idx:
        if td[a] == td[b] or tp[a] == tp[b]: continue
        c = M[:, a] & M[:, b]
        if c.sum() >= 4: ref.append(spearmanr(Y[c, a], Y[c, b]).correlation)
    return {'identical_setup_rho': summ(df[df.same_setup]), 'identical_setup_absdiff': summ(df[df.same_setup], 'absdiff'),
            'identical_setup_absdiff_points_only': summ(df[df.same_setup & df.pts], 'absdiff'), 'same_protocol_rho': summ(df[df.same_protocol]),
            'all_pairs_rho': summ(df), 'different_datasets_rho': float(np.nanmedian(ref))}

def matrix_stats(D):
    M = D['mask']; td, tp = D['td'], D['tp']; st = {'families': int((M.sum(1) > 0).sum()), 'settings': int(M.shape[1]), 'scores': int(M.sum()), 'scores_with_copied_row': int(D['copy'].sum())}
    pap = pd.DataFrame({'d': td, 'p': tp}); st['datasets_in_2plus_papers'] = int((pap.groupby('d').p.nunique() >= 2).sum())
    indep = pd.DataFrame({'d': np.repeat(td[None], M.shape[0], 0)[M], 'p': np.repeat(tp[None], M.shape[0], 0)[M], 'c': D['copy'][M]})
    st['datasets_in_2plus_independent_papers'] = int((indep[~indep.c].groupby('d').p.nunique() >= 2).sum()); return st

Ds = {}
Ds['repo'] = load()
pre = Ds['repo']['pre_d6']; post = Ds['repo']['post_d6']; r_repo = Ds['repo']['r']
residual = sorted(set(r_repo.index) & set(raw.index[raw.called]))
OUT['d6_vs_detector'] = {'pre_d6_rows': int(len(pre)), 'd6_drops': int(len(set(pre.index) - set(post.index))), 'detector_calls_in_pre_d6': int(pre.index.isin(raw.index[raw.called]).sum()),
                         'residual_calls_after_d6': len(residual), 'residual_by_copy_paper': raw.loc[residual].paper_key.value_counts().head(10).to_dict(),
                         'residual_decimals': raw.loc[residual].dec.value_counts().to_dict()}
d6drop = set(pre.index) - set(post.index); calls = set(pre.index[pre.index.isin(raw.index[raw.called])])
OUT['d6_vs_detector'].update({'both': len(d6drop & calls), 'd6_only': len(d6drop - calls), 'detector_only': len(calls - d6drop)})
print(OUT['d6_vs_detector'], flush=True)
Ds['dedup'] = load(extra_drop=residual)
Ds['copies_kept'] = load(keep_copies=True)
OUT['matrices'] = {}
for k, D in Ds.items():
    OUT['matrices'][k] = {**matrix_stats(D), 'agreement': agreement(D)}; print(k, json.dumps(OUT['matrices'][k], default=float)[:1500], flush=True)
json.dump(OUT, open(OUTP, 'w'), indent=1, default=float)

# ----------------------------------------------------------------------------------------------------------- 5. variance components
if not NOVC:
    import v5_long, variance_components as VC
    OUT['varcomp_z'] = {}
    for k, kw in (('repo', {}), ('dedup', {'extra_drop': residual}), ('copies_kept', {'keep_copies': True})):
        prefix.build = make_build(**kw); tmp = OUTP + f'.{k}.long.pkl'; L = v5_long.build(tmp); os.remove(tmp); L = L[L.pclass != 'other']
        res = {}
        for nm, d in (('pooled', L), ('multispectral', L[L.itype == 'multispectral']), ('SAR + optical', L[L.itype == 'SAR + optical'])):
            v, x, n = VC.fit(d, 'z'); s = VC.summary(v); cells = d.groupby(['family', 'canonical_dataset']).paper_key.nunique()
            res[nm] = {'n_scores': n, 'replicated_cells': int((cells >= 2).sum()), **{q: s[q] for q in ('FD', 'FP', 'FDP', 'e', 'lab', 'rel_one_score', 'papers_for_08', 'lab_over_signal')}}
        OUT['varcomp_z'][k] = res; print(k, res, flush=True)
json.dump(OUT, open(OUTP, 'w'), indent=1, default=float); print('done')
