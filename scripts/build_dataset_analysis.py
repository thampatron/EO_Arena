#!/usr/bin/env python3
"""Dataset-level benchmarking analysis (v2): what each benchmark dataset measures, how much it overlaps with others,
how reproducibly independent groups agree on the model differences it shows, and — where seed noise is reported — how
reliably it separates GeoFMs (note Eq. 6).  Statistics in scripts/dataset_benchmarking.py; base rows from
scripts/evidence_rows.py.  Follows "GeoFM Benchmark Scoring" (S. Wang, Oct 2026).  Every analysis decision and its
justification is in docs/analysis-decisions.md; each revised decision has a switch for sensitivity runs.

Usage: python3 scripts/build_dataset_analysis.py <dir with metaanalysis_benchmark_table_v4.xlsx> [options]
  --main-text-only     drop appendix / supplementary tables (v1 rule)
  --no-leaderboard     drop the GEO-Bench-2 leaderboard source (v1 rule)
  --no-regression      drop regression tasks (v1 rule)
  --offset S           paper x model offset for: select (default: chosen by leave-one-paper-out among all /
                       multi_domain / none) | all | multi_domain | none
  --skip-sim           skip the simulation studies (sensitivity runs)
  --out PATH           output JSON (default data/dataset_analysis.json)
Writes summary statistics only; no individual scores leave the workbook.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1"); os.environ.setdefault("MKL_NUM_THREADS", "1")
import json, sys, time, multiprocessing as mp
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dataset_benchmarking as db
from evidence_rows import load

A = sys.argv
SRC = Path(A[1]); QUICK = "--quick" in A
MAIN_ONLY = "--main-text-only" in A; WITH_LB = "--no-leaderboard" not in A; WITH_REG = "--no-regression" not in A
OFFSET = A[A.index("--offset") + 1] if "--offset" in A else "select"; SKIP_SIM = "--skip-sim" in A
OUT = Path(A[A.index("--out") + 1]) if "--out" in A else ROOT / "data" / "dataset_analysis.json"
SEED = 0; KS_LOPO = (1, 2, 3, 4); FOLDS = 5; RIDGE = 3.0; RIDGE_PM = 3.0; MIN_MODELS = 4
NPROC = max(1, min(2, os.cpu_count() or 1))
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:6.0f}s]", *a, flush=True)

r, _TINFO, _make_cells, breg, _mreg, srcs = load(SRC)
mreg_all = pd.read_excel(SRC / "metaanalysis_benchmark_table_v4.xlsx", "model_registry")

# ============================================================================= 1. inclusion (docs/analysis-decisions.md, D1-D7)
LOC = json.loads((ROOT / "data" / "table_locations.json").read_text())
loc = pd.DataFrame(LOC["tables"]).set_index(["paper", "file", "table_id"])
r["file"] = r.locator.astype(str).str.replace(r":(\d+|p\d+)$", "", regex=True); r["table_id"] = r.table_id.astype(str)
key = list(zip(r.paper_key, r.file, r.table_id))
r["location"] = [loc.location.get(x, "unclear") for x in key]
_line = pd.to_numeric(r.locator.astype(str).str.extract(r":(\d+)$")[0], errors="coerce")
for o in LOC.get("line_overrides", []):
    r.loc[(r.paper_key == o["paper"]) & (r.file == o["file"]) & (_line >= o["appendix_from_line"]), "location"] = "appendix"
r["is_leaderboard"] = r.source_kind.astype(str).eq("leaderboard")
_abl = [loc.ablation.get(x, None) for x in key]
r["table_ablation_unknown"] = [a is None or (isinstance(a, float) and np.isnan(a)) for a in _abl]
r["table_ablation"] = [bool(a) if not u else False for a, u in zip(_abl, r.table_ablation_unknown)]
role = mreg_all.groupby("model_id").row_role.agg(lambda s: "ablation" if (s == "ablation").any() else "")
r["model_ablation"] = r.model_id.map(role).eq("ablation") | r.model_id.astype(str).str.contains("_abl")
AX = set(LOC["ablation_axes"]); HEAD = LOC.get("headline_variants", {})
r["variant_ablation"] = np.array([a in AX and str(v) != HEAD.get(a) for a, v in zip(r.variant_axis.astype(str), r.config_variant.astype(str))], bool)
SCOPE = json.loads((ROOT / "data" / "model_scope.json").read_text())
GFM_CATS = set(SCOPE["geofm_categories"]); GFM_EXTRA = set(SCOPE["geofm_uncategorised"]) | set(SCOPE.get("geofm_from_baseline_pretrained", {}))
cat = mreg_all.dropna(subset=["category"]).groupby("model_id").category.agg(lambda s: s.mode().iat[0])
r["category"] = r.model_id.map(cat).fillna("")
r["is_geofm"] = r.category.isin(GFM_CATS) | r.model_id.isin(GFM_EXTRA)
r["metric_s"] = r.metric.astype(str)

# D11: a printed SD is rounded; floor it at half its last printed digit (e.g. "± 0.1" -> >= 0.05), in result units
import re as _re
def _sd_decimals(cell):
    c = str(cell)
    m = _re.search(r"seeds?\s+((?:\d+:\s*-?\d+(?:\.\d+)?,?\s*)+)", c)
    if m:
        vals = _re.findall(r"\d+:\s*-?\d+(?:\.(\d+))?", m.group(1)); return max(len(v) for v in vals) if vals else 0
    m = _re.search(r"(?:±|\\pm|\+/-|\$\\pm\$)\s*\d+(?:\.(\d+))?", c) or _re.search(r"-?\d+(?:\.\d+)?\s*\(\s*\d+(?:\.(\d+))?\s*\)", c)
    if m:
        g_ = [x for x in m.groups() if x is not None]; return len(g_[0]) if g_ else 0
    return None
_dec = r.raw_cell.map(_sd_decimals)
_ratio = (r.v / r.pm_mean).where(r.pm_mean.abs() > 0).fillna(1.0).abs()
_floor = (0.5 * 10.0 ** (-_dec.astype(float))) * _ratio
r["sd_floored"] = r.sd.notna() & (r.sd < _floor)
r.loc[r.sd_floored, "sd"] = _floor[r.sd_floored]

steps, n0 = [], len(r)
def keep(m, why):
    global r
    m = np.asarray(m, bool); steps.append({"rule": why, "dropped": int((~m).sum())}); r = r[m].copy()
keep(~r.location.eq("unclear") | r.is_leaderboard, "table placement unclear")
if MAIN_ONLY: keep(r.location.eq("main") | r.is_leaderboard, "appendix / supplementary table (--main-text-only)")
if not WITH_LB: keep(~r.is_leaderboard, "GEO-Bench-2 leaderboard (--no-leaderboard)")
keep(~r.table_ablation_unknown | r.is_leaderboard, "ablation status of table not checked")
keep(~r.table_ablation, "ablation-study table")
keep(~r.model_ablation, "registry ablation model")
keep(~r.variant_ablation, "ablation variant axis (non-headline setting)")
keep(r.is_geofm, "not a GeoFM (baseline / task architecture / uncategorised)")
_piv = {(p_, m_) for p_, ms_ in SCOPE.get("paper_internal_variants", {}).items() if p_ != "about" for m_ in ms_}
keep(~np.array([(p_, m_) in _piv for p_, m_ in zip(r.paper_key, r.model_id)]), "paper-internal variant of the introducing paper's own method (D7)")
_sub_t = {(x_["paper"], x_["table_id"]) for x_ in LOC.get("subscore_tables", [])}
_sub_b = {(p_, b_) for p_, bs_ in LOC.get("subscore_benchmarks", {}).items() if p_ != "evidence" for b_ in bs_}
keep(~np.array([(p_, t_) in _sub_t or (p_, b_) in _sub_b for p_, t_, b_ in zip(r.paper_key, r.table_id, r.benchmark_id)]), "per-class sub-score of a headline result (D5)")

# D4: metric scales. Bounded classification/segmentation metrics stay in points. Regression metrics go on a log-error
# scale, y = -100 ln(err) with err = RMSE (or sqrt(MSE), MAE, L1, nMAE as reported) and, for R^2, err^2 = 1 - R^2
# (so -100 ln sqrt(1-R^2) = -100 ln RMSE + const within a task: R^2 and RMSE of the same runs agree up to the task mean).
REG = {"r2", "rmse", "mse", "mae", "l1", "nmae"}
r["family"] = np.where(r.metric_s.isin(REG), "logerr", np.where(r.pts.astype(bool), "points", "other"))
if WITH_REG:
    reg = r.family.eq("logerr")
    v = r.v.astype(float)
    R2 = np.where((r.scale_basis == "percent_printed") & (v.abs() > 1.5), v / 100.0, v)
    sdv = r.sd.astype(float)
    sdR2 = np.where((r.scale_basis == "percent_printed") & (v.abs() > 1.5), sdv / 100.0, sdv)
    err = np.select([r.metric_s.eq("r2"), r.metric_s.eq("mse")], [np.sqrt(np.clip(1 - R2, 1e-12, None)), np.sqrt(np.clip(v, 1e-12, None))], v)
    sd_err = np.select([r.metric_s.eq("r2"), r.metric_s.eq("mse")], [sdR2 / (2 * np.sqrt(np.clip(1 - R2, 1e-12, None))), sdv / (2 * np.sqrt(np.clip(v, 1e-12, None)))], sdv)
    ok_reg = reg & (((r.metric_s == "r2") & (R2 < 1)) | ((r.metric_s != "r2") & (v > 0)))
    r.loc[reg, "y"] = np.where(ok_reg[reg], -100 * np.log(np.where(ok_reg, err, 1.0)[reg]), np.nan)
    r.loc[reg, "sd"] = 100 * sd_err[reg] / np.where(ok_reg, err, 1.0)[reg]                  # delta method on -100 ln(err)
    keep(~reg | ok_reg, "regression value outside the metric's domain")
    keep(r.family.isin(["points", "logerr"]), "metric not on a bounded-points or log-error scale (skill scores etc.)")
else:
    keep(r.family.eq("points"), "regression or other unbounded metric (--no-regression)")

# D5: within-paper duplicates — (a) an appendix table repeating a main-text value (same model, benchmark, protocol,
# fraction, metric, value; the setting label is ignored because appendices name the headline setting that main tables
# leave blank, e.g. PANGAEA 'joint') is one measurement: the appendix copy is dropped; (b) the leaderboard's 'best of'
# setting repeats its s2_main value: kept once. Identical values in different settings within one location are NOT
# collapsed (they are separate experiments that happen to coincide).
r["variant"] = r.config_variant.astype(str).where(r.variant_axis.notna(), "")
dk = ["paper_key", "model_id", "benchmark_id", "evaluation_protocol", "train_fraction_norm", "metric_s"]
r["_yr"] = r.y.round(1)
_g = r.groupby(dk + ["_yr"]).location
_drop_app = (r.location == "appendix") & _g.transform(lambda x_: (x_ == "main").any()).values
_lbk = r.is_leaderboard.values
_order = r.assign(_pri=(r.variant != "s2_main").astype(int)).sort_values(["_pri", "table_id"])
_lb_dup = _order[_order.is_leaderboard].duplicated(dk + ["_yr", "table_id"], keep="first")
_drop_lb = r.index.isin(_lb_dup[_lb_dup].index)
keep(~(_drop_app | _drop_lb), "within-paper duplicate (appendix repeats main text; leaderboard 'best of' repeats s2_main)")

# D6: reprints across papers — kept only in the earliest source (month, then arXiv number)
_arx = srcs.identifier.astype(str).str.extract(r"(\d{4}\.\d{4,5})")[0].fillna("9999.99999")
REL = (srcs.release_year_month.astype(str) + "|" + _arx).to_dict()
r["release"] = r.paper_key.map(REL).fillna("9999")
r["vkey"] = list(zip(r.model_id, r.benchmark_id, r.metric_s, r._yr))
first = r.sort_values(["release", "paper_key"]).drop_duplicates("vkey").set_index("vkey").paper_key
recited = r.paper_key.values != r.vkey.map(first).values
r["vkey2"] = list(zip(r.model_id, r.canonical_dataset, r.metric_s, r._yr))
first2 = r.sort_values(["release", "paper_key"]).drop_duplicates("vkey2").set_index("vkey2").paper_key
recited |= (r.paper_key.values != r.vkey2.map(first2).values) & (r.canonical_dataset.values != "")
r["skey"] = list(zip(r.model_id, r.benchmark_id, r.metric_s))
reprint_pairs = []
pk = r.paper_key.unique()
for pa in pk:
    for pb in pk:
        if pa >= pb: continue
        Av = r[r.paper_key == pa].groupby("skey")._yr.first(); Bv = r[r.paper_key == pb].groupby("skey")._yr.first()
        sh = Av.index.intersection(Bv.index)
        if len(sh) >= 3 and (Av[sh] == Bv[sh]).mean() >= 0.5:
            later = pb if (REL.get(pb, ""), pb) > (REL.get(pa, ""), pa) else pa
            reprint_pairs.append({"earlier": pa if later == pb else pb, "later": later, "shared_cells": int(len(sh)), "identical_share": round(float((Av[sh] == Bv[sh]).mean()), 2)})
            recited |= (r.paper_key.values == later) & r.skey.isin(set(sh)).values
recited_by = r[recited].groupby("paper_key").size().to_dict()
keep(~recited, "recitation of an earlier paper's value")

# comparisons and one canonical metric each
r["comparison"] = (r.paper_key.astype(str) + "|" + r.table_id + "|" + r.benchmark_id.astype(str) + "|" + r.evaluation_protocol.astype(str)
                   + "|" + r.train_fraction_norm.astype(str) + "|" + r.variant)
# metric twins: different metrics of the same runs, also when a paper prints each metric in its own table (Infra-Bench):
# one canonical metric per core = paper | benchmark | protocol | fraction | setting (most GeoFMs, then priority)
r["core"] = (r.paper_key.astype(str) + "|" + r.benchmark_id.astype(str) + "|" + r.evaluation_protocol.astype(str) + "|" + r.train_fraction_norm.astype(str) + "|" + r.variant)
PRIORITY = ["miou", "iou", "f1", "map", "acc", "acc_top1", "oa", "bal_acc", "micro_f1", "weighted_f1", "acc_avg", "r2", "rmse", "mae", "l1", "mse", "nmae"]
nm = r.groupby(["core", "metric_s"]).model_id.nunique().reset_index(name="n")
nm["prio"] = nm.metric_s.map({m: i for i, m in enumerate(PRIORITY)}).fillna(len(PRIORITY))
canon = nm.sort_values(["core", "n", "prio", "metric_s"], ascending=[True, False, True, True]).drop_duplicates("core").set_index("core").metric_s
keep(r.metric_s.values == r.core.map(canon).values, "metric twin (one metric per paper x benchmark x protocol x fraction x setting)")
r["task"] = r.comparison + "|" + r.metric_s
log(f"rows {n0} -> {len(r)}"); [log(f"   dropped {s['dropped']:5d}  {s['rule']}") for s in steps]
log(f"   recitations by citing paper: {recited_by}; reprint pairs: {reprint_pairs}")

TINFO = r.drop_duplicates("task").set_index("task")[["paper_key", "benchmark_id", "evaluation_protocol", "pf", "metric_s", "family", "train_fraction_norm", "variant",
                                                    "canonical_dataset", "eoarena_id", "domain", "subdomain", "input_kind", "location", "is_leaderboard"]]
TINFO["task_type"] = TINFO.benchmark_id.map(breg.task_type).fillna(""); TINFO["sensor"] = TINFO.benchmark_id.map(breg.sensor).fillna("")
cell = r.groupby(["task", "model_id"]).agg(y=("y", "mean"), n_rows=("y", "size"), sd=("sd", "mean"), n_reps=("n_reps", "max"),
                                            n_known=("n_reps_known", "max"), selfrep=("self", "max")).reset_index()
nmod = cell.groupby("task").model_id.nunique(); cell = cell[cell.task.isin(nmod[nmod >= MIN_MODELS].index)]
assert (cell.n_rows == 1).all(), "a (task, model) cell still averages several rows"

IMG = TINFO[(TINFO.input_kind == "eo_imagery") & (~TINFO.domain.isin(["composite", "outside_taxonomy"])) & (TINFO.canonical_dataset != "")].index
lc = cell[cell.task.isin(IMG)]
models = sorted(lc.model_id.unique()); tasks = sorted(lc.task.unique())
mi = {m: i for i, m in enumerate(models)}; ti = {t: i for i, t in enumerate(tasks)}
Y = np.zeros((len(models), len(tasks))); mask = np.zeros_like(Y, bool)
Y[lc.model_id.map(mi), lc.task.map(ti)] = lc.y; mask[lc.model_id.map(mi), lc.task.map(ti)] = True
TI = TINFO.loc[tasks]; td = TI.canonical_dataset.values; tp = TI.paper_key.values
FAM = (TI.family.values == "logerr").astype(int)
PIDX = np.asarray(pd.factorize(tp)[0])
def lev(col):
    v_ = pd.Series(TI[col].values).astype(str).replace({"": np.nan, "nan": np.nan}); return np.asarray(pd.factorize(v_)[0], int)
G_ALL = {"dataset": lev("canonical_dataset"), "protocol": lev("pf"), "sensor": lev("sensor")}
ppm = pd.DataFrame({"m": np.nonzero(mask)[0], "p": tp[np.nonzero(mask)[1]]}).groupby("m").p.nunique()
dpp = TI.groupby("canonical_dataset").paper_key.nunique()
dom_per_paper = TI.groupby("paper_key").domain.nunique()
overlap = {"models": len(models), "tasks": len(tasks), "datasets": int(len(set(td))), "sources": int(len(set(tp))), "density": round(float(mask.mean()), 4),
           "models_in_1_source": int((ppm == 1).sum()), "models_in_3plus_sources": int((ppm >= 3).sum()), "datasets_in_2plus_sources": int((dpp >= 2).sum()),
           "models_per_task_median": float(np.median(mask.sum(0))), "tasks_logerr": int(FAM.sum()), "tasks_from_appendix": int((TI.location == "appendix").sum()),
           "tasks_from_leaderboard": int(TI.is_leaderboard.sum()), "single_domain_sources": int((dom_per_paper == 1).sum())}
log("matrix", overlap)

# D8: paper x model offset — for every source, only for sources spanning >= 2 domains, or none
MULTI_DOM = set(dom_per_paper[dom_per_paper >= 2].index)
OFFSETS = {"all": PIDX, "multi_domain": np.where(np.isin(tp, list(MULTI_DOM)), PIDX, -1), "none": None}
def kw(offset, groups=("dataset", "protocol", "sensor")):
    k = dict(groups={g: G_ALL[g] for g in groups}, ridge_u=RIDGE, ridge_g={g: RIDGE for g in groups}, ridge_theta=RIDGE,
             n_restarts=1, n_iter=200, tol=1e-6, prior_group=FAM)
    if OFFSETS[offset] is not None: k.update(paper=OFFSETS[offset], ridge_pm=RIDGE_PM)
    return k

def paired_boot(a, b, papers, B=2000):
    d = pd.DataFrame({"d": np.asarray(a, float) - np.asarray(b, float), "p": papers}).dropna(); groups = [g_.d.values for _, g_ in d.groupby("p")]
    rng = np.random.default_rng(SEED); bs = np.array([np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))]).mean() for _ in range(B)])
    return {"mean": round(float(d.d.mean()), 4), "ci90": [round(float(np.percentile(bs, 5)), 4), round(float(np.percentile(bs, 95)), 4)],
            "p_le_0": round(float((bs <= 0).mean()), 4), "n_tasks": int(len(d)), "n_papers": len(groups)}

def _lopo_job(args):
    Yx, offset, K = args
    k = kw(offset); g = k.pop("groups")
    return (offset, K), db.leave_one_paper_out(Yx, mask, tp, K, g, **k)
def run_parallel(jobs):
    if NPROC > 1:
        with mp.get_context("fork").Pool(NPROC) as pool: return dict(pool.map(_lopo_job, jobs))
    return dict(map(_lopo_job, jobs))

def choose_K(rows):
    means = {K_: float(v_.rho_struct.mean()) for K_, v_ in rows.items()}; bk = max(means, key=means.get); tests = {}
    for K_, v_ in rows.items():
        if K_ == bk: continue
        Aa = v_.set_index("task"); Bb = rows[bk].set_index("task"); j = Aa.index.intersection(Bb.index)
        tests[K_] = paired_boot(Aa.loc[j, "rho_struct"], Bb.loc[j, "rho_struct"], Aa.loc[j, "paper"])
    return min([bk] + [k_ for k_, t_ in tests.items() if t_["ci90"][1] >= 0]), bk, tests, means

# ============================================================================= 2. model-free tests from pairwise Kendall tau (primary, D15)
P_tau = db.tau_pairs(Y, mask, min_shared=4)
_keys = [f"{td[t]}|{TI.pf.values[t]}|{TI.train_fraction_norm.astype(str).values[t]}" for t in range(len(tasks))]
CODEBASE = db.shared_codebase_pairs(Y, mask, tp, _keys)
TAU = db.tau_contrasts(P_tau, tp, td, TI.pf.values, exclude_source_pairs=[(a_, b_) for a_, b_, _, _ in CODEBASE], B=2000, seed=SEED)
TAU["robustness"] = db.tau_robustness(P_tau, tp, td, B=1000, seed=SEED)
TAU["flagged_source_pairs_detail"] = [{"a": a_, "b": b_, "matched_cells": n_, "median_abs_diff": m_} for a_, b_, n_, m_ in CODEBASE]
log("tau cells", TAU["cells"]); log("tau contrasts (all)", TAU["all"]); log("flagged codebase pairs", CODEBASE)

# ============================================================================= 3. leave-one-paper-out over offset specs x K (D8, D9)
# Primary out-of-paper criterion: BLOCK-PREDICTED order of a held-out comparison (from its dataset / protocol / sensor
# blocks and the GeoFMs' capability vectors; nothing from the comparison itself), against the plain naive leaderboard
# (also nothing from the comparison; its sign is known a priori, so the test is conservative toward one ranking).
# Secondary: ANCHORED (loading estimated from half the comparison's GeoFMs, other half predicted) against the plain
# leaderboard on the same half.
specs = ["all", "multi_domain", "none"] if OFFSET == "select" else [OFFSET]
LO = run_parallel([(Y, s, K_) for s in specs for K_ in KS_LOPO])
for (s, K_), L_ in LO.items():
    L_["dataset"] = [td[t] for t in L_.task]; L_["dataset_seen_elsewhere"] = [dpp.get(td[t], 0) >= 2 for t in L_.task]
COLS = ("rho_struct", "rho_board", "rho_global", "rho_anch", "rho_half_board", "rho_anch_board", "acc_struct", "acc_board")
lopo_table = {s: {K_: {c: round(float(LO[(s, K_)][c].mean()), 4) for c in COLS} for K_ in KS_LOPO} for s in specs}
for s in specs: log("LOPO", s, {K_: (v_["rho_struct"], v_["rho_anch"]) for K_, v_ in lopo_table[s].items()}, "board", lopo_table[s][1]["rho_board"], "half-board", lopo_table[s][1]["rho_half_board"])
def choose_K_on(rows, col):
    means = {K_: float(v_[col].mean()) for K_, v_ in rows.items()}; bk = max(means, key=means.get); tests = {}
    for K_, v_ in rows.items():
        if K_ == bk: continue
        Aa = v_.set_index("task"); Bb = rows[bk].set_index("task"); j = Aa.index.intersection(Bb.index)
        tests[K_] = paired_boot(Aa.loc[j, col], Bb.loc[j, col], Aa.loc[j, "paper"])
    return min([bk] + [k_ for k_, t_ in tests.items() if t_["ci90"][1] >= 0]), bk, tests, means
PRIMARY = "rho_struct"
SPEC = max(specs, key=lambda s: max(lopo_table[s][K_][PRIMARY] for K_ in KS_LOPO))
spec_tests = {}
for s in specs:
    if s == SPEC: continue
    Ks_, Kb_ = max(KS_LOPO, key=lambda K_: lopo_table[s][K_][PRIMARY]), max(KS_LOPO, key=lambda K_: lopo_table[SPEC][K_][PRIMARY])
    Aa = LO[(s, Ks_)].set_index("task"); Bb = LO[(SPEC, Kb_)].set_index("task"); j = Aa.index.intersection(Bb.index)
    spec_tests[s] = dict(K=Ks_, vs_K=Kb_, **paired_boot(Aa.loc[j, PRIMARY], Bb.loc[j, PRIMARY], Aa.loc[j, "paper"]))
rows = {K_: LO[(SPEC, K_)] for K_ in KS_LOPO}
K, bestK, k_tests, _ = choose_K_on(rows, PRIMARY)
_, bestK_anch, k_tests_anch, _ = choose_K_on(rows, "rho_anch")
log("offset spec", SPEC, spec_tests, "| K", K, "best", bestK, k_tests)
Lsel = rows[K]; Lbest = rows[bestK]
lopo_gain = {"K1_vs_leaderboard": paired_boot(rows[1].rho_struct, rows[1].rho_board, rows[1].paper),
             "Kchosen_vs_leaderboard": dict(K=int(K), **paired_boot(Lsel.rho_struct, Lsel.rho_board, Lsel.paper)),
             "bestK_vs_leaderboard": dict(K=int(bestK), **paired_boot(Lbest.rho_struct, Lbest.rho_board, Lbest.paper)),
             "anchored_K1_vs_leaderboard_same_half": paired_boot(rows[1].rho_anch, rows[1].rho_half_board, rows[1].paper),
             "anchored_bestK_vs_leaderboard_same_half": dict(K=int(bestK_anch), **paired_boot(rows[bestK_anch].rho_anch, rows[bestK_anch].rho_half_board, rows[bestK_anch].paper))}
for flag, name in ((True, "dataset_seen_in_other_sources"), (False, "dataset_only_in_held_out_source")):
    s_ = Lbest[Lbest.dataset_seen_elsewhere == flag]
    if len(s_): lopo_gain[f"{name} (K={bestK}, blocks vs own one-ordering)"] = paired_boot(s_.rho_struct, s_.rho_global, s_.paper)
log("LOPO gain", lopo_gain)
REAL_BOARD = db.board_lopo_rho(Y, mask, tp)

# ============================================================================= 4. simulations calibrated to the real data (D16)
# Truth: a general factor plus specific factors, dataset-shared loadings and paper x model implementation effects
# (db.simulate, K_true = 2 for calibration). Calibration (v2.2, agent backlog N2): two-stage grid search for the point
# whose simulated statistics (mean over common seeds) are closest to the four real targets in units of their bootstrap
# SE (cluster bootstrap over sources); the fine stage is re-centred while its best point sits on a fine-grid edge that is
# not a bound of the parameter. Fit is then checked on fresh seeds. The calibrated truth is used to check the D9 K rule
# (K_true 1-4) and the cost of each D8 offset option, over SIM_SEEDS seeds each.
SIM_SEEDS = 5; CAL_SEEDS_1, CAL_SEEDS_2, CAL_SEEDS_CHECK = range(900, 908), range(2000, 2016), range(3000, 3020)
CAL_AXES_1 = ((0.2, 0.4, 0.6, 0.8, 1.0), (0.5, 1.0, 2.0, 4.0, 8.0, 16.0), (0.5, 0.75, 0.9, 1.0), (0.0, 0.5, 1.0, 1.5, 2.0, 3.0))
CAL_NAMES = ("general_mean", "snr", "dataset_share", "paper_effect"); CAL_BOUNDS = ((0.0, None), (0.0, None), (0.3, 1.0), (0.0, None))
sim_cal, sim_spec, sim_K, sim_rho_level = {}, [], [], {}
if not SKIP_SIM:
    CAL_T = db.calibration_target_intervals(Y, mask, td, tp, P=P_tau, B=2000, seed=SEED)
    IDX = db.tau_pair_index(mask)
    def _cal_job(a):
        p_, seeds = a; gm, snr, ds, pe = p_
        sts = [db.calibration_stats(db.simulate(mask, td, tp, 2, snr=snr, dataset_share=ds, paper_effect=pe, general_mean=gm, seed=s_)[0], mask, td, tp, IDX) for s_ in seeds]
        return p_, {k_: float(np.mean([x_[k_] for x_ in sts])) for k_ in sts[0]}, {k_: float(np.std([x_[k_] for x_ in sts], ddof=1)) for k_ in sts[0]}
    def _cal_run(points, seeds):
        with mp.get_context("fork").Pool(NPROC) as pool: return pool.map(_cal_job, [(p_, seeds) for p_ in points], chunksize=8)
    import itertools
    def _fine_axes(c):
        """Five values per parameter around the centre (snr on a log scale), clipped to the parameter's bounds."""
        out = []
        for v_, (lo_, hi_), steps in zip(c, CAL_BOUNDS, ((-0.1, -0.05, 0, 0.05, 0.1), None, (-0.1, -0.05, 0, 0.05, 0.1), (-0.25, -0.125, 0, 0.125, 0.25))):
            vals = [v_ * 2 ** e_ for e_ in (-0.5, -0.25, 0, 0.25, 0.5)] if steps is None else [v_ + d_ for d_ in steps]
            out.append(tuple(sorted({round(float(np.clip(x_, lo_, hi_ if hi_ is not None else np.inf)), 4) for x_ in vals})))
        return tuple(out)
    def _edge_names(ch, axes):
        out = []
        for i_ in ch["edge_params"]:
            v_ = ch["params"][i_]; lo_, hi_ = CAL_BOUNDS[i_]
            out.append({"param": CAL_NAMES[i_], "value": v_, "parameter_bound": v_ == lo_ or v_ == hi_})
        return out
    R1 = _cal_run(list(itertools.product(*CAL_AXES_1)), CAL_SEEDS_1)
    C1 = db.choose_calibration([(p_, st_) for p_, st_, _ in R1], CAL_T, CAL_AXES_1)
    inside1 = [p_ for p_, st_, _ in R1 if all(CAL_T[k_]["ci90"][0] <= st_[k_] <= CAL_T[k_]["ci90"][1] for k_ in CAL_T)]
    log("calibration stage 1", C1, "points with all targets inside:", len(inside1))
    centre, rounds, C2 = C1["params"], [], None
    for _ in range(3):
        AX2 = _fine_axes(centre); R2 = _cal_run(list(itertools.product(*AX2)), CAL_SEEDS_2)
        C2 = db.choose_calibration([(p_, st_) for p_, st_, _ in R2], CAL_T, AX2)
        e2 = _edge_names(C2, AX2); rounds.append({"axes": dict(zip(CAL_NAMES, AX2)), "points": len(R2), "chosen": dict(zip(CAL_NAMES, C2["params"])), "misfit": C2["misfit"], "edges": e2})
        log("calibration stage 2", rounds[-1])
        if all(x_["parameter_bound"] for x_ in e2) or C2["params"] == centre: break
        centre = C2["params"]
    GM, SNR, DS, PE = C2["params"]
    _, chk_m, chk_sd = _cal_job((C2["params"], CAL_SEEDS_CHECK))
    fit_chk = {k_: {"real": CAL_T[k_]["value"], "ci90": CAL_T[k_]["ci90"], "simulated": round(chk_m[k_], 4), "simulated_seed_sd": round(chk_sd[k_], 4),
                    "simulated_selection_seeds": C2["fit"][k_]["simulated"], "inside": bool(CAL_T[k_]["ci90"][0] <= chk_m[k_] <= CAL_T[k_]["ci90"][1]),
                    "miss": round(0.0 if CAL_T[k_]["ci90"][0] <= chk_m[k_] <= CAL_T[k_]["ci90"][1] else (chk_m[k_] - CAL_T[k_]["ci90"][1] if chk_m[k_] > CAL_T[k_]["ci90"][1] else chk_m[k_] - CAL_T[k_]["ci90"][0]), 4)}
               for k_ in CAL_T}
    sim_cal = {"method": "two-stage grid; misfit = sum over targets of ((simulated mean - real) / bootstrap SE)^2; coarse stage 8 common seeds, fine stage 16, re-centred up to 3 rounds while the best point is on a fine-grid edge that is not a parameter bound; fit checked on 20 fresh seeds",
               "targets": {k_: CAL_T[k_]["value"] for k_ in CAL_T}, "target_intervals": CAL_T,
               "chosen": {"general_mean": GM, "snr": SNR, "dataset_share": DS, "paper_effect": PE},
               "achieved": {k_: round(chk_m[k_], 4) for k_ in CAL_T}, "fit": fit_chk, "all_targets_inside": all(v_["inside"] for v_ in fit_chk.values()),
               "coarse": {"axes": dict(zip(CAL_NAMES, CAL_AXES_1)), "points": len(R1), "chosen": dict(zip(CAL_NAMES, C1["params"])), "misfit": C1["misfit"], "edges": _edge_names(C1, CAL_AXES_1),
                          "points_all_targets_inside": len(inside1),
                          "inside_region_range": {n_: [min(p_[i_] for p_ in inside1), max(p_[i_] for p_ in inside1)] for i_, n_ in enumerate(CAL_NAMES)} if inside1 else None},
               "fine_rounds": rounds, "grid_size": len(R1) + sum(r_["points"] for r_ in rounds), "K_true_used": 2,
               "previous_v2_1": {"grid_size": 54, "chosen": {"general_mean": 0.6, "snr": 2.0, "dataset_share": 0.9, "paper_effect": 0.5}, "edges": ["snr", "dataset_share"]}}
    log("calibration", {k_: sim_cal[k_] for k_ in ("chosen", "fit", "all_targets_inside")})
    # one pool for all simulation fits: (a) K recovery under the D9 rule, K_true = 1..4 (K_true = 1 is a single
    # leaderboard: general factor only), SIM_SEEDS seeds each; (b) offset cost under the calibrated truth (K_true = 2)
    def _sim_job(a):
        kind, Kt, s_, arg = a
        if kind == "K":
            Ys, _, _ = db.simulate(mask, td, tp, Kt, snr=SNR, dataset_share=DS, paper_effect=PE, general_mean=GM, seed=500 + Kt + 10 * s_)
            k = kw(SPEC); g = k.pop("groups"); return a, db.leave_one_paper_out(Ys, mask, tp, arg, g, **k)
        Ys, Ld_true, nmz = db.simulate(mask, td, tp, 2, snr=SNR, dataset_share=DS, paper_effect=PE, general_mean=GM, seed=701 + s_)
        k = kw(arg); g = k.pop("groups")
        L_ = db.leave_one_paper_out(Ys, mask, tp, 2, g, **k)
        f, _ = db.fit_heteroskedastic(Ys, mask, 2, g, **k); n2, Lh, _ = db.dataset_loadings(f, td, mask)
        return a, (L_, n2, Lh, Ld_true, nmz)
    jobs = [("K", Kt, s_, K_) for Kt in (1, 2, 3, 4) for s_ in range(SIM_SEEDS) for K_ in KS_LOPO] + \
           [("off", 2, s_, o_) for s_ in range(SIM_SEEDS) for o_ in ("all", "multi_domain", "none")]
    jobs.sort(key=lambda j_: -(j_[3] if j_[0] == "K" else 3))                # longest first, for load balance
    with mp.get_context("fork").Pool(NPROC) as pool: SIMR = dict(pool.map(_sim_job, jobs, chunksize=1))
    log("simulation fits done:", len(SIMR))
    for o_ in ("all", "multi_domain", "none"):
        per = []
        for s_ in range(SIM_SEEDS):
            L_, n2, Lh, Ld_true, nmz = SIMR[("off", 2, s_, o_)]
            multi_ = [i for i, n in enumerate(n2) if dpp.get(n, 0) >= 2]; Lt = np.array([Ld_true[nmz.index(n)] for n in n2])
            seen = L_[[dpp.get(td[t], 0) >= 2 for t in L_.task]]
            per.append(dict(rho=float(L_.rho_struct.mean()), board=float(L_.rho_board.mean()), dataset_gain_seen=float((seen.rho_struct - seen.rho_global).mean()),
                            recovery_multi_source_datasets=db.recovery(Lt[multi_], Lh[multi_]), recovery_all=db.recovery(Lt, Lh)))
        agg = {k_: round(float(np.mean([x_[k_] for x_ in per])), 4) for k_ in ("rho", "board", "dataset_gain_seen", "recovery_all")}
        agg.update({f"{k_}_sd": round(float(np.std([x_[k_] for x_ in per], ddof=1)), 4) for k_ in ("rho", "dataset_gain_seen")})
        rm = [x_["recovery_multi_source_datasets"] for x_ in per]
        sim_spec.append(dict(offset=o_, seeds=SIM_SEEDS, **agg, recovery_multi_source_datasets=round(float(np.median(rm)), 3),
                             recovery_multi_source_datasets_by_seed=[round(x_, 3) for x_ in rm]))
        log("sim offset", sim_spec[-1])
    for Kt in (1, 2, 3, 4):
        per = []
        for s_ in range(SIM_SEEDS):
            rr_ = {K_: SIMR[("K", Kt, s_, K_)] for K_ in KS_LOPO}
            Kc_, bk_, _, means = choose_K_on(rr_, PRIMARY)
            per.append(dict(seed=500 + Kt + 10 * s_, K_selected=int(Kc_), best_K=int(bk_), rho_by_K={K_: round(m_, 4) for K_, m_ in means.items()},
                            board=round(float(rr_[1].rho_board.mean()), 4), bestK_minus_board=round(float(rr_[bk_].rho_struct.mean() - rr_[1].rho_board.mean()), 4)))
        sim_K.append(dict(K_true=Kt, seeds=SIM_SEEDS, K_selected_counts={K_: sum(x_["K_selected"] == K_ for x_ in per) for K_ in KS_LOPO},
                          best_K_counts={K_: sum(x_["best_K"] == K_ for x_ in per) for K_ in KS_LOPO},
                          rho_by_K={K_: round(float(np.mean([x_["rho_by_K"][K_] for x_ in per])), 4) for K_ in KS_LOPO},
                          board=round(float(np.mean([x_["board"] for x_ in per])), 4), bestK_minus_board=round(float(np.mean([x_["bestK_minus_board"] for x_ in per])), 4),
                          per_seed=per))
        log("sim K", {k_: v_ for k_, v_ in sim_K[-1].items() if k_ != "per_seed"})
    # diagnostic, not a calibration target: leave-one-paper-out accuracy levels in the calibrated world (K_true = 2) vs real
    k2_ = next(x_ for x_ in sim_K if x_["K_true"] == 2)
    sim_rho_level = {"real": {"rho_struct_by_K": {K_: lopo_table[SPEC][K_]["rho_struct"] for K_ in KS_LOPO}, "board": lopo_table[SPEC][1]["rho_board"]},
                     "simulated_K_true_2": {"rho_struct_by_K": k2_["rho_by_K"], "board": k2_["board"]}, "offset": SPEC}
    log("rho level", sim_rho_level)

# ============================================================================= 5. dataset outputs at the best K (describes structure; see D9)
k = kw(SPEC); g = k.pop("groups"); k.update(n_restarts=3, n_iter=400)
fit, psi = db.fit_heteroskedastic(Y, mask, bestK, g, **k)
names, Ld, ntask = db.dataset_loadings(fit, td, mask)
k2 = kw(SPEC, groups=("dataset",)); g2 = k2.pop("groups")
fit2, _ = db.fit_heteroskedastic(Y, mask, bestK, g2, **k2); _, Ld2, _ = db.dataset_loadings(fit2, td, mask)
dmeta = TI.groupby("canonical_dataset").agg(domain=("domain", "first"), subdomain=("subdomain", "first"),
                                            task_type=("task_type", lambda s: s.mode().iat[0] if len(s.mode()) else ""),
                                            sensor=("sensor", lambda s: s.mode().iat[0] if len(s.mode()) else ""), sources=("paper_key", "nunique")).reindex(names)
multi = np.array([dmeta.at[n, "sources"] >= 2 for n in names])
NPERM = 500 if QUICK else 2000
assoc = {c: {"full_loading": db.metadata_association(Ld2[multi], dmeta[c].fillna("").values[multi], n_perm=NPERM),
             "direction_only": db.metadata_association(Ld2[multi], dmeta[c].fillna("").values[multi], n_perm=NPERM, direction_only=True)}
         for c in ("domain", "subdomain", "task_type", "sensor")}
for c in assoc:
    for v_ in assoc[c].values(): v_["p_bonferroni_4_labels"] = min(1.0, 4 * v_["p_value"])
log("assoc", {c: {kk: (round(a["r2"], 3), round(a["null_mean"], 3), a["p_value"], a["n"]) for kk, a in v_.items()} for c, v_ in assoc.items()})
# D13: publish dataset similarity only if (a) simulation shows it would be recoverable on this mask and (b) the real data
# shows dataset loadings transfer out of paper (credible positive gain for datasets seen in other sources): (a) is
# conditional on structure existing; (b) tests whether it does.
rec_ok = next((s_["recovery_multi_source_datasets_by_seed"] for s_ in sim_spec if s_["offset"] == SPEC), [])   # median over seeds
_seen = next((v_ for k_, v_ in lopo_gain.items() if k_.startswith("dataset_seen_in_other_sources")), None)
GEOMETRY_RECOVERABLE = bool(rec_ok) and float(np.median(rec_ok)) >= 0.7
DATASET_TRANSFER = bool(_seen) and _seen["ci90"][0] > 0
GEOMETRY_OK = GEOMETRY_RECOVERABLE and DATASET_TRANSFER
S = db.similarity(Ld)
tau_obs = {}
for n in names:
    vv = [(Y[mask[:, t], t].var(ddof=1), mask[:, t].sum(), TI.family.values[t]) for t in np.where(td == n)[0]]
    pts = [(a_, w_) for a_, w_, f_ in vv if f_ == "points"]
    tau_obs[n] = float(np.sqrt(np.average([a_ for a_, _ in pts], weights=[w_ for _, w_ in pts]))) if pts else np.nan

# ============================================================================= 6. seed-noise reliability where seed SDs are reported (note Eq. 3-6)
# sigma2_t: median over models of the squared seed SD of ONE evaluation, from the task's own cells (>= 3 models with an
# SD; never borrowed). tau2_t = tau2_obs - sigma2_t / n_reps (reported values are means of n_reps seeds).
# score = tau2 / (tau2 + sigma2): share of the comparison's model spread that is repeatable under re-seeding, for that
# comparison's models and implementation (not cross-implementation reproducibility; not a property of the dataset alone).
rel_rows, rng = [], np.random.default_rng(SEED)
for t in tasks:
    c_ = lc[lc.task == t]; s_ = c_[c_.sd.notna()]
    if len(s_) < 3 or len(c_) < 6: continue                # >= 6 GeoFMs: resampling 4-5 models says little
    y_ = c_.y.values; n_rep = float(np.median(s_.n_reps)); known = bool(s_.n_known.all())
    def score(y, sd, n):
        s2 = float(np.median(sd ** 2)); t2 = max(float(np.var(y, ddof=1)) - s2 / n, 0.0)
        return (t2 / (t2 + s2) if (t2 + s2) > 0 else np.nan), s2, t2
    sc, s2, t2 = score(y_, s_.sd.values, n_rep)
    boots = []
    for _ in range(500):                                   # resample models: spread and noise jointly
        i = rng.integers(0, len(c_), len(c_)); cc = c_.iloc[i]; ss = cc[cc.sd.notna()]
        if len(ss) >= 2 and cc.y.nunique() > 1: boots.append(score(cc.y.values, ss.sd.values, n_rep)[0])
    rel_rows.append(dict(task=t, dataset=TI.at[t, "canonical_dataset"], protocol=TI.at[t, "pf"], family=TI.at[t, "family"], source=TI.at[t, "paper_key"],
                         models=int(len(c_)), models_with_sd=int(len(s_)), n_reps=n_rep, n_reps_known=known, sigma=np.sqrt(s2), spread=float(np.std(y_, ddof=1)),
                         score=sc, score_lo=float(np.nanpercentile(boots, 5)) if boots else np.nan, score_hi=float(np.nanpercentile(boots, 95)) if boots else np.nan,
                         score_if_single_runs=score(y_, s_.sd.values, 1.0)[0]))
REL_T = pd.DataFrame(rel_rows)
rel_ds = []
if len(REL_T):
    for (d_, p_), gg in REL_T.groupby(["dataset", "protocol"]):
        w_ = gg.models.values.astype(float)
        rel_ds.append(dict(dataset=d_, protocol=p_, comparisons=int(len(gg)), sources=int(gg.source.nunique()), models_median=float(np.median(gg.models)),
                           sigma_median=round(float(np.median(gg.sigma)), 3), spread_median=round(float(np.median(gg.spread)), 3),
                           score=round(float(np.average(gg.score, weights=w_)), 3), score_min=round(float(gg.score.min()), 3), score_max=round(float(gg.score.max()), 3),
                           score_lo_min=round(float(gg.score_lo.min()), 3), score_if_single_runs=round(float(np.average(gg.score_if_single_runs, weights=w_)), 3),
                           n_reps_known=bool(gg.n_reps_known.all()), family=gg.family.iat[0],
                           comparisons_lo_ge_0_8=int((gg.score_lo >= 0.8).sum()), comparisons_lo_ge_0_5=int((gg.score_lo >= 0.5).sum())))
log(f"seed-noise reliability: {len(REL_T)} comparisons, {len(rel_ds)} dataset x protocol")

# ============================================================================= 7. cross-source reproducibility
base = cell[cell.task.isin(IMG)].merge(TINFO, left_on="task", right_index=True)
def repro(group_cols, label, min_shared, min_df):
    rr = base[base.variant == ""].copy()
    rr["group"] = rr[group_cols].astype(str).agg(" | ".join, axis=1)
    rr = rr.groupby(["group", "paper_key", "model_id"], as_index=False).y.mean()
    rep = db.cross_paper_reproducibility(rr.rename(columns={"paper_key": "paper", "model_id": "model"})[["group", "paper", "model", "y"]],
                                         min_shared=min_shared, min_df=min_df, n_boot=100 if QUICK else 500)
    cnt = []
    for gname, gg in rr.groupby("group"):
        if gg.paper_key.nunique() < 2: continue
        mc = gg.groupby("model_id").paper_key.nunique(); cnt.append(int((mc >= 2).sum()))
    cnt = np.array(cnt)
    return {"grouping": label, "min_shared": min_shared, "min_df": min_df, "groups_with_2plus_sources": int(len(cnt)),
            "with_3plus_shared": int((cnt >= 3).sum()), "with_5plus_shared": int((cnt >= 5).sum()), "estimable": rep.round(4).to_dict("records")}
REPRO = {"strict": repro(["canonical_dataset", "benchmark_id", "evaluation_protocol", "train_fraction_norm", "metric_s"], "dataset version x protocol x fraction x metric", 5, 5),
         "loose": repro(["canonical_dataset", "pf", "train_fraction_norm", "metric_s"], "dataset x protocol family x fraction x metric (versions pooled within source)", 4, 3)}
log("reproducibility", {k_: (v_["groups_with_2plus_sources"], len(v_["estimable"])) for k_, v_ in REPRO.items()})

# ============================================================================= write
def rnd(x, d=3):
    try: return None if x is None or not np.isfinite(x) else round(float(x), d)
    except TypeError: return None
Lb = Lbest
out = {"version": 2, "as_of": time.strftime("%Y-%m-%d"),
       "config": {"main_text_only": MAIN_ONLY, "leaderboard": WITH_LB, "regression": WITH_REG, "offset": OFFSET, "ridge": RIDGE, "ridge_paper_offset": RIDGE_PM},
       "scope": {"rows_in": n0, "rows_kept": int(len(r)), "dropped": steps, "reprint_pairs": reprint_pairs, "recited_by": recited_by, "model_scope": "data/model_scope.json"},
       "overlap": overlap,
       "offset": {"specs": specs, "chosen": SPEC, "rule": "highest best-K leave-one-paper-out Spearman among the prespecified specs", "paired_vs_chosen": spec_tests,
                  "multi_domain_sources": sorted(MULTI_DOM)},
       "K": {"chosen": int(K), "best": int(bestK), "rule": "smallest K not credibly worse than the best (paired bootstrap over sources); K is a floor",
             "lopo_by_spec_and_K": lopo_table, "paired_vs_best": k_tests, "primary_criterion": PRIMARY,
             "anchored": {"best": int(bestK_anch), "paired_vs_best": k_tests_anch}},
       "lopo_gain": lopo_gain, "board_lopo_rho_real": rnd(REAL_BOARD), "tau_tests": TAU, "simulation_calibration": sim_cal,
       "simulation_offset": sim_spec, "simulation_K": sim_K, "simulation_rho_level": sim_rho_level, "geometry_recoverable": GEOMETRY_OK,
       "geometry_gate": {"simulated_recovery_median": rnd(float(np.median(rec_ok))) if rec_ok else None, "recoverable_in_simulation": GEOMETRY_RECOVERABLE,
                         "dataset_loadings_transfer_out_of_paper": DATASET_TRANSFER, "published": GEOMETRY_OK},
       "metadata_association_multi_source": assoc,
       "datasets": {n: {"sources": int(dmeta.at[n, "sources"]), "comparisons": int((td == n).sum()), "models_per_comparison": round(float(np.mean(mask[:, td == n].sum(0))), 1),
                        "smallest_comparison": int(mask[:, td == n].sum(0).min()), "domain": dmeta.at[n, "domain"], "task_type": dmeta.at[n, "task_type"], "sensor": dmeta.at[n, "sensor"],
                        "families": sorted(set(TI.family.values[td == n])), "reported_separation_pts": rnd(tau_obs[n], 2),
                        "lopo_rho": rnd(Lb[Lb.dataset == n].rho_struct.mean()), "lopo_rho_naive_leaderboard": rnd(Lb[Lb.dataset == n].rho_board.mean()),
                        "lopo_tasks": int((Lb.dataset == n).sum()), "lopo_models_median": rnd(Lb[Lb.dataset == n].n_models.median(), 0),
                        "nearest": ([{"name": names[j], "similarity": round(float(S[i, j]), 3)} for j in np.argsort(-S[i])[1:6] if multi[j]][:5] if (GEOMETRY_OK and multi[i]) else None)}
                    for i, n in enumerate(names)},
       "seed_noise_reliability": {"comparisons": int(len(REL_T)), "by_dataset_protocol": rel_ds, "min_geofms": 6,
                                  "comparisons_lo_ge_0_8": int((REL_T.score_lo >= 0.8).sum()) if len(REL_T) else 0, "comparisons_lo_ge_0_5": int((REL_T.score_lo >= 0.5).sum()) if len(REL_T) else 0,
                                  "cells_sd_floored_to_print_precision": int(r.sd_floored.sum()),
                                  "n_reps_assumed_3_share": round(float((~REL_T.n_reps_known).mean()), 3) if len(REL_T) else None},
       "reproducibility": REPRO}
OUT.write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
log(f"wrote {OUT}")
