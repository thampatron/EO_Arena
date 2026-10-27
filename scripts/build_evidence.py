#!/usr/bin/env python3
"""Build data/evidence.json, data/model_profiles.json and data/replicate_plan.json from the GeoFM meta-analysis
workbook, following the scoring note "GeoFM Benchmark Scoring" (S. Wang, Oct 2026).  Statistics live in
scripts/geofm_scoring.py.

Inputs (not in this repository):
  <dir>/metaanalysis_benchmark_table_v4.xlsx   GeoFM meta-analysis workbook (V. Mancoridis, 2026, unpublished)
  data/benchmark_map.csv                       workbook benchmark_id -> canonical dataset, EOArena id, domain, subdomain, input_kind
                                               (hand-curated; a copy in <dir> takes precedence)
Only summary statistics are written: no individual scores leave the workbook.

Every dataset (and every dataset x protocol family) is scored under four analysis variants, so the pages can
toggle them: noise aggregation (median | mean of the per-model seed variances) x self-reported scores (kept |
dropped).  The latent-factor diagnostics are computed under two ridge strengths (10 = stable geometry, 3 =
better held-out prediction).  The main variant is median / kept / ridge 10.

Usage: python3 scripts/build_evidence.py <dir> [--boot N] [--fast] [--no-cache]
  --fast      skip the cross-validation, bootstrap-stability and residual permutation tests unless cached
  --no-cache  ignore scripts/.cache (fits are cached by a hash of their inputs)
"""
import csv, hashlib, json, re, sys, time
from collections import defaultdict
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from geofm_scoring import (fit_latent, cross_validate_K, select_K, task_scores, bootstrap_scores, frontier, shapley_information,
                           geometry_stability, principal_axes, residual_correlation_check, _als)

src = Path(sys.argv[1]); FAST = "--fast" in sys.argv; NO_CACHE = "--no-cache" in sys.argv
BOOT = int(sys.argv[sys.argv.index("--boot") + 1]) if "--boot" in sys.argv else 200
AS_OF = "2026-10-27"; MIN_MODELS = 4; MIN_SD_MODELS = 3; SEED = 0; K_MAX = 6
RIDGES = {"10": 10.0, "3": 3.0}; MAIN_RIDGE = "10"
NOISE_AGGS = ("median", "mean"); SELF_OPTS = ("all", "independent")
MAIN_VARIANT = "median|all"
CACHE = ROOT / "scripts" / ".cache"; CACHE.mkdir(exist_ok=True)
rng = np.random.default_rng(SEED)
t_start = time.time()
def log(*a): print(f"[{time.time()-t_start:6.0f}s]", *a, flush=True)

# ----------------------------------------------------------------------------- 1. rows
X = src / "metaanalysis_benchmark_table_v4.xlsx"
r = pd.read_excel(X, "results_long")
breg = pd.read_excel(X, "benchmark_registry").drop_duplicates("benchmark_id").set_index("benchmark_id")
mreg = pd.read_excel(X, "model_registry").drop_duplicates("model_id").set_index("model_id")
bmap = pd.read_csv((src / "benchmark_map.csv") if (src / "benchmark_map.csv").exists() else ROOT / "data" / "benchmark_map.csv", dtype=str).fillna("").set_index("benchmark_id")
known = {d["id"] for d in json.loads((ROOT / "data" / "datasets.json").read_text(encoding="utf-8"))}

r = r[(r.exclude_from_analysis != 1) & (r.agreement_vs_recitation == "original") & (~r.model_id.astype(str).str.contains("_abl"))
      & (r.is_non_foundation_baseline != 1) & (r.evaluation_protocol != "scratch")].copy()
r["v"] = pd.to_numeric(r.result_normalized, errors="coerce"); r = r[r.v.notna()].copy()
# replicate noise per cell: per-seed values listed in the cell, or a printed mean +/- sd, rescaled to result_normalized units
pat = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:±|\\pm|\+/-|\$\\pm\$)\s*(\d+(?:\.\d+)?)"); pat2 = re.compile(r"(-?\d+(?:\.\d+)?)\s*\(\s*(\d+(?:\.\d+)?)\s*\)")
pat_seeds = re.compile(r"seeds?\s+((?:\d+:\s*-?\d+(?:\.\d+)?,?\s*)+)")
def parse(s):
    m = pat_seeds.search(s)
    if m:
        vals = np.array([float(x) for x in re.findall(r"\d+:\s*(-?\d+(?:\.\d+)?)", m.group(1))])
        if len(vals) >= 3: return float(vals.mean()), float(vals.std(ddof=1)), "seeds", len(vals)
    m = pat.search(s) or pat2.search(s)
    return (float(m.group(1)), float(m.group(2)), "printed", np.nan) if m else (np.nan, np.nan, "", np.nan)
P = r.raw_cell.astype(str).map(parse)
r["pm_mean"] = [p[0] for p in P]; r["pm_sd"] = [p[1] for p in P]; r["sd_kind"] = [p[2] for p in P]; r["n_seeds"] = [p[3] for p in P]
# number of replicates behind a reported mean: the seed list's length, else the count the paper states (from its notes), else 3 (assumed)
N_REPS = {"geobench_v2_leaderboard": 5, "earthshift": 5, "geocross-bench": 5, "melt-salt": 10, "mind": 5, "presto": 3, "prithvi_v2": 10,
          "ss_vision_transformers_for_lc": 5, "tessera_v2": 5, "agbd_eval": 3}
N_REPS_DEFAULT = 3
r["n_reps"] = np.where(r.sd_kind == "seeds", r.n_seeds, np.where(r.sd_kind == "printed", r.paper_key.map(N_REPS).fillna(N_REPS_DEFAULT), 1.0)).astype(float)
r["n_reps_known"] = (r.sd_kind == "seeds") | r.paper_key.isin(N_REPS)
ratio = (r.v / r.pm_mean).where(r.pm_mean.abs() > 0); r["sd"] = r.pm_sd * ratio.where(ratio.notna(), 1.0)
r.loc[~np.isfinite(r.sd) | (r.sd <= 0), "sd"] = np.nan; r.loc[r.sd.isna(), "n_reps"] = 1.0   # a printed "± 0.00" is below the table's precision
r["y"] = np.where(r.higher_is_better.astype(str) == "True", r.v, -r.v)
r["pts"] = r.scale_basis.isin(["percent_printed", "fraction_printed"])
PF = lambda p: "fine-tuned" if p in ("FT", "PFT") else "frozen" if p in ("frozen_dec", "LP", "kNN", "frozen", "frozen_best", "PE", "MLP") else str(p)
r["pf"] = r.evaluation_protocol.map(PF)
for c in ["canonical_dataset", "eoarena_id", "domain", "subdomain", "input_kind"]: r[c] = r.benchmark_id.map(bmap[c]).fillna("")
r["task"] = r.paper_key.astype(str) + "|" + r.benchmark_id.astype(str) + "|" + r.evaluation_protocol.astype(str) + "|" + r.metric.astype(str) + "|" + r.train_fraction_norm.astype(str)
own = r[r.is_self_reported == True].groupby("model_id").paper_key.agg(set).to_dict()
r["self"] = [p in own.get(m, set()) for m, p in zip(r.model_id, r.paper_key)]
log(f"{len(r)} result rows")

TINFO = r.drop_duplicates("task").set_index("task")[["paper_key", "benchmark_id", "evaluation_protocol", "pf", "metric", "train_fraction_norm", "pts",
                                                      "canonical_dataset", "eoarena_id", "domain", "subdomain", "input_kind"]]
TINFO["task_type"] = TINFO.benchmark_id.map(breg.task_type).fillna(""); TINFO["sensor"] = TINFO.benchmark_id.map(breg.sensor).fillna("")

def make_cells(drop_self: bool):
    rr = r[~r.self] if drop_self else r
    cell = rr.groupby(["task", "model_id"]).agg(y=("y", "mean"), sd=("sd", "mean"), n_reps=("n_reps", "max"), n_known=("n_reps_known", "max"), selfrep=("self", "max")).rename(columns={"selfrep": "self"}).reset_index()
    n = cell.groupby("task").model_id.nunique(); return cell[cell.task.isin(n[n >= MIN_MODELS].index)].copy()

# ----------------------------------------------------------------------------- 2. latent-factor fits (cached)
def matrix(cell):
    lc = cell[cell.task.isin(TINFO[(TINFO.input_kind == "eo_imagery") & (~TINFO.domain.isin(["composite", "outside_taxonomy"]))].index)].copy()
    g = lc.groupby("task").y; lc["z"] = (lc.y - g.transform("mean")) / g.transform("std").replace(0, np.nan); lc = lc[lc.z.notna()]
    models = sorted(lc.model_id.unique()); tasks = sorted(lc.task.unique())
    mi = {m: i for i, m in enumerate(models)}; ti = {t: i for i, t in enumerate(tasks)}
    Y = np.zeros((len(models), len(tasks))); mask = np.zeros_like(Y, bool)
    Y[lc.model_id.map(mi), lc.task.map(ti)] = lc.z; mask[lc.model_id.map(mi), lc.task.map(ti)] = True
    return Y, mask, models, tasks

def cache_key(Y, mask, *parts):
    h = hashlib.sha1(); h.update(np.round(Y, 6).tobytes()); h.update(mask.tobytes()); h.update(json.dumps(parts, sort_keys=True).encode()); return h.hexdigest()[:16]
def cached(key, compute, label):
    f = CACHE / f"{key}.json"
    if f.exists() and not NO_CACHE: return json.loads(f.read_text())
    if FAST and label.startswith("slow:"): log(f"  skipped (fast): {label}"); return None
    t0 = time.time(); v = compute(); f.write_text(json.dumps(v)); log(f"  computed {label} in {time.time()-t0:.0f}s"); return v

def latent_bundle(cell, ridge, want_K=None, slow=True):
    """Fit + diagnostics for one variant. K is chosen once, on the main variant, and reused."""
    Y, mask, models, tasks = matrix(cell)
    out = {"n_models": len(models), "n_tasks": len(tasks), "density": float(mask.mean()), "ridge": ridge}
    cv = stab = None
    if want_K is None:
        cv = cached(cache_key(Y, mask, "cv", ridge, K_MAX), lambda: {str(k): v for k, v in cross_validate_K(Y, mask, Ks=tuple(range(K_MAX + 1)), folds=5, seed=SEED, ridge_l=ridge, ridge_t=ridge, n_restarts=3, tol=1e-5).items()}, "slow:cross-validation")
        stab = cached(cache_key(Y, mask, "stab", ridge), lambda: {str(k): geometry_stability(Y, mask, k, fit_latent(Y, mask, k, models, tasks, ridge_l=ridge, ridge_t=ridge, seed=SEED).lam, n_boot=20, seed=SEED, ridge_l=ridge, ridge_t=ridge) for k in (1, 2, 3, 4)}, "slow:bootstrap stability")
        if cv and stab: K = select_K({int(k): v for k, v in cv.items()}, {int(k): v for k, v in stab.items()})
        elif stab: K = max([int(k) for k in stab if stab[k] >= 0.5] or [0])
        else: K = 3
        out.update(cv=cv, stability=stab, K_selection="smallest K within one SE of the best held-out RMSE, stepped down until bootstrap geometry stability >= 0.5")
    else: K = want_K
    fit = fit_latent(Y, mask, K, models, tasks, ridge_l=ridge, ridge_t=ridge, seed=SEED)
    lam, theta, var_share = principal_axes(fit.lam, fit.theta)
    out.update(K=K, var_share=[float(x) for x in var_share], n_iter=fit.n_iter)
    if slow:
        for k in sorted({K, K + 1}):
            f2 = fit if k == K else fit_latent(Y, mask, k, models, tasks, ridge_l=ridge, ridge_t=ridge, seed=SEED)
            for gname, gcol in (("paper", "paper_key"), ("dataset", "canonical_dataset"), ("sensor", "sensor")):
                out[f"residual_check_K{k}_by_{gname}"] = cached(cache_key(Y, mask, "resid3", ridge, k, gname), lambda f2=f2, gcol=gcol: residual_correlation_check(Y, mask, f2.mu, f2.lam, f2.theta, n_perm=200, seed=SEED, group=TINFO.loc[tasks, gcol].values.tolist()), f"slow:residual check K={k} by {gname}")
    return dict(Y=Y, mask=mask, models=models, tasks=tasks, fit=fit, lam=lam, theta=theta, meta=out)

def assoc(lam, tasks, col):
    if lam.shape[1] == 0: return None
    d = pd.get_dummies(TINFO.loc[tasks, col].astype(str)); Xd = np.c_[np.ones(len(tasks)), d.values.astype(float)]
    beta, *_ = np.linalg.lstsq(Xd, lam, rcond=None); res = lam - Xd @ beta
    return float(1 - res.var(0).sum() / max(lam.var(0).sum(), 1e-12))

cells = {s: make_cells(s == "independent") for s in SELF_OPTS}
log(f"cells: all {len(cells['all'])} in {cells['all'].task.nunique()} tasks; independent {len(cells['independent'])} in {cells['independent'].task.nunique()} tasks")
log("latent fit, main (ridge 10, all cells)")
L = {}
L["10"] = latent_bundle(cells["all"], RIDGES["10"])
K = L["10"]["meta"]["K"]; log(f"  K = {K}")
log("latent fit, ridge 3")
L["3"] = latent_bundle(cells["all"], RIDGES["3"], want_K=K, slow=False)
log("latent fit, independent cells (for model profiles)")
L["ind"] = latent_bundle(cells["independent"], RIDGES["10"], want_K=K, slow=False)
for key in ("10", "3"):
    b = L[key]; b["meta"]["geometry_assoc_r2"] = {c: assoc(b["lam"], b["tasks"], c) for c in ["domain", "subdomain", "task_type", "sensor", "pf", "canonical_dataset"]}

# ----------------------------------------------------------------------------- 3. task-level quantities per variant
def task_table(cell, noise_agg):
    agg = np.nanmedian if noise_agg == "median" else np.nanmean
    g = cell.groupby("task")
    T = TINFO.loc[cell.task.unique()].copy()
    T["n_models"] = g.model_id.nunique(); T["n_sd"] = g.sd.apply(lambda s: int(s.notna().sum()))
    T["tau2_obs"] = g.y.var(ddof=1); T["self_share"] = g.self.mean()
    T["sigma2_meas"] = g.sd.apply(lambda s: float(agg(s.dropna() ** 2)) if s.notna().sum() >= MIN_SD_MODELS else np.nan)
    T["n_reps"] = g.apply(lambda x: float(np.median(x.n_reps[x.sd.notna()])) if x.sd.notna().any() else 1.0, include_groups=False)
    T["n_reps_known"] = g.apply(lambda x: bool(x.n_known[x.sd.notna()].all()) if x.sd.notna().any() else False, include_groups=False)
    T["tau2_top"] = g.y.apply(lambda y: float(frontier(y.values).var(ddof=1))); T["n_top"] = g.y.apply(lambda y: int(len(frontier(y.values))))
    meas = T[T.sigma2_meas.notna()]
    plug_ds = meas.groupby(["canonical_dataset", "pf", "metric"]).apply(lambda d: np.average(d.sigma2_meas, weights=d.n_models), include_groups=False).to_dict()
    plug_pf = meas[meas.pts].groupby("pf").sigma2_meas.median().to_dict()
    def plug(row):
        if np.isfinite(row.sigma2_meas): return row.sigma2_meas, "measured"
        k = (row.canonical_dataset, row.pf, row.metric)
        if k in plug_ds: return plug_ds[k], "same dataset, same protocol family"
        if row.pts and row.pf in plug_pf: return plug_pf[row.pf], "protocol-family median"
        return np.nan, "none"
    pp = T.apply(plug, axis=1); T["sigma2"] = [p[0] for p in pp]; T["sigma2_source"] = [p[1] for p in pp]
    T.loc[T.sigma2_source != "measured", "n_reps"] = 1.0
    T = T.join(T.apply(lambda row: task_scores(row.tau2_obs, row.sigma2, row.n_reps), axis=1, result_type="expand"))
    T = T.join(T.apply(lambda row: task_scores(row.tau2_top, row.sigma2, row.n_reps), axis=1, result_type="expand").rename(columns={"tau2": "tau2f", "edi": "edi_top", "score": "score_top"}))
    T.loc[T.n_top >= T.n_models, ["score_top", "edi_top"]] = np.nan   # a 4-model comparison has no frontier distinct from the whole
    cy = {t: x.y.values for t, x in g}
    BS = np.full((BOOT, len(T)), np.nan); BT = np.full((BOOT, len(T)), np.nan)
    for j, t in enumerate(T.index):
        s2 = T.at[t, "sigma2"]
        if not np.isfinite(s2): continue
        BS[:, j] = bootstrap_scores(cy[t], s2, T.at[t, "n_reps"], BOOT, rng)
        if T.at[t, "n_top"] < T.at[t, "n_models"]: BT[:, j] = bootstrap_scores(frontier(cy[t]), s2, T.at[t, "n_reps"], BOOT, rng)
    T["score_lo"] = np.nanpercentile(BS, 5, axis=0); T["score_hi"] = np.nanpercentile(BS, 95, axis=0)
    return T, BS, BT, plug_pf

def attach_latent(T, bundle):
    """Residual-based quantities for one latent variant, aligned to T's tasks."""
    fit = bundle["fit"]; idx = {t: i for i, t in enumerate(bundle["tasks"])}
    r2 = pd.Series({t: fit.r2[idx[t]] for t in T.index if t in idx}, dtype=float); rv = pd.Series({t: fit.resid_var[idx[t]] for t in T.index if t in idx}, dtype=float)
    out = pd.DataFrame({"r2": r2, "resid_var": rv}).reindex(T.index)
    def unexpl(row):
        if not np.isfinite(row.resid_var) or not np.isfinite(row.sigma2) or row.tau2_obs <= 0: return np.nan
        psi = max(row.resid_var * row.tau2_obs - row.sigma2 / row.n_reps, 0.0); tau2 = row.tau2_obs - row.sigma2 / row.n_reps
        return float(min(psi / tau2, 1.0)) if tau2 > 0 else np.nan
    out["unexplained_share"] = T.join(out).apply(unexpl, axis=1)
    return out

TABLES = {}
for s in SELF_OPTS:
    for na in NOISE_AGGS:
        T, BS, BT, plug_pf = task_table(cells[s], na); TABLES[f"{na}|{s}"] = dict(T=T, BS=BS, BT=BT, plug_pf=plug_pf, BSI={t: j for j, t in enumerate(T.index)})
        log(f"variant {na}|{s}: {len(T)} tasks, {(T.sigma2_source=='measured').sum()} measured")
LAT = {key: {rk: attach_latent(TABLES[key]["T"], L[rk]) for rk in ("10", "3")} for key in TABLES}

# ----------------------------------------------------------------------------- 4. aggregation (dataset, dataset x protocol)
def wmean(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float); ok = np.isfinite(x) & (w > 0)
    return float(np.average(x[ok], weights=w[ok])) if ok.any() else None
def rnd(x, d=3):
    try: return None if x is None or not np.isfinite(x) else round(float(x), d)
    except TypeError: return None
def edi_of(score): return None if score is None else (1e9 if score >= 1 else score / (1 - score))

def verdict(d):
    if d["models"] < 4 or d["tasks_n"] == 0: return "e_few"
    if d["score"] is None: return "e_spread"
    if d["sigma2_source"] == "measured": return "e_reliable" if d["score"] >= 0.8 else "e_moderate" if d["score"] >= 0.5 else "e_weak"
    return "e_prov_high" if d["score"] >= 0.8 else "e_prov_low"

EMPTY = {"tasks_n": 0, "models": 0, "papers": 0, "results": 0, "score": None, "score_lo": None, "score_hi": None, "score_top": None, "edi": None, "edi_top": None, "spread_pts": None, "noise_sd": None, "verdict": "e_few", "sigma2_source": "none"}

def score_block(Tg, V, cell):
    """Score summary for a group of tasks under one variant."""
    if not len(Tg): return dict(EMPTY)
    cg = cell[cell.task.isin(Tg.index)]
    d = {"tasks_n": int(len(Tg)), "models": int(cg.model_id.nunique()), "papers": int(Tg.paper_key.nunique()), "results": int(len(cg))}
    pts = Tg[Tg.pts]
    d["spread_pts"] = rnd(np.sqrt(np.average(pts.tau2_obs, weights=pts.n_models)), 2) if len(pts) else None
    d["n_sd_models"] = int(Tg.n_sd.sum())
    own = Tg[Tg.sigma2_source.isin(["measured", "same dataset, same protocol family"]) & Tg.score.notna()]
    use = own if len(own) else Tg[Tg.score.notna()]
    d["sigma2_source"] = "measured" if len(own) else (use.sigma2_source.mode().iat[0] if len(use) else "none")
    d["score"] = wmean(use.score, use.n_models) if len(use) else None
    d["score_top"] = wmean(use.score_top, use.n_models) if len(use) else None
    d["sigma2"] = wmean(use.sigma2, use.n_models) if len(use) else None
    d["noise_sd"] = None if d["sigma2"] is None or not Tg.pts.any() else float(np.sqrt(d["sigma2"]))
    meas = use[use.sigma2_source == "measured"]
    d["n_reps"] = wmean(meas.n_reps, meas.n_models) if len(meas) else None; d["n_reps_known"] = bool(meas.n_reps_known.all()) if len(meas) else False
    d["edi"] = edi_of(d["score"]); d["edi_top"] = edi_of(d["score_top"])
    for arr, lo, hi in ((V["BS"], "score_lo", "score_hi"), (V["BT"], "score_top_lo", "score_top_hi")):
        if len(use):
            cols = [V["BSI"][t] for t in use.index]; w = use.n_models.values.astype(float); M = arr[:, cols]; ok = np.isfinite(M)
            den = (ok * w).sum(axis=1); agg = np.where(den > 0, np.nansum(M * w, axis=1) / np.maximum(den, 1e-12), np.nan)
            d[lo], d[hi] = (rnd(np.nanpercentile(agg, 5)), rnd(np.nanpercentile(agg, 95))) if np.isfinite(agg).any() else (None, None)
        else: d[lo] = d[hi] = None
    d["score_all"] = wmean(Tg.score, Tg.n_models); d["self_share"] = wmean(Tg.self_share, Tg.n_models)
    d["verdict"] = verdict(d)
    for k in ("score", "score_top", "score_all", "sigma2", "self_share", "n_reps"): d[k] = rnd(d[k])
    d["noise_sd"] = rnd(d["noise_sd"], 2); d["edi"] = rnd(d["edi"], 1); d["edi_top"] = rnd(d["edi_top"], 1)
    return d

def latent_block(Tg, LT, w):
    sub = LT.reindex(Tg.index)
    return {"unexplained_share": rnd(wmean(sub.unexplained_share, w)), "r2_shared": rnd(wmean(sub.r2, w))}

def task_rec(t, T, LT):
    row = T.loc[t]; lt = LT.loc[t] if t in LT.index else None
    return {"paper": row.paper_key, "benchmark_id": row.benchmark_id, "protocol": row.evaluation_protocol, "protocol_family": row.pf, "metric": row.metric,
            "train_fraction": None if row.train_fraction_norm in ("unspecified", "nan") else row.train_fraction_norm, "n_models": int(row.n_models),
            "spread_pts": rnd(np.sqrt(row.tau2_obs), 2) if row.pts else None, "spread_units": None if row.pts else rnd(np.sqrt(row.tau2_obs), 3),
            "noise_sd": rnd(np.sqrt(row.sigma2), 3), "noise_source": row.sigma2_source, "n_sd_models": int(row.n_sd), "n_reps": rnd(row.n_reps, 1), "n_reps_known": bool(row.n_reps_known),
            "n_top": int(row.n_top), "spread_top_pts": rnd(np.sqrt(row.tau2_top), 2) if row.pts else None, "score_top": rnd(row.score_top), "edi_top": rnd(row.edi_top, 1),
            "score": rnd(row.score), "score_lo": rnd(row.score_lo), "score_hi": rnd(row.score_hi), "edi": rnd(row.edi, 1),
            "r2_shared": rnd(lt.r2) if lt is not None else None, "unexplained_share": rnd(lt.unexplained_share) if lt is not None else None, "self_share": rnd(row.self_share, 2)}

def explain(d, K):
    p = [f"{d['tasks_n']} comparison{'s' if d['tasks_n'] != 1 else ''} ({d['models']} models, {d['papers']} paper{'s' if d['papers'] != 1 else ''})."]
    if d["spread_pts"] is not None: p.append(f"GeoFMs differ by an SD of {d['spread_pts']:.2f} pts within a comparison.")
    if d["score"] is None: p.append("No paper prints a seed/run standard deviation for this benchmark, and no plug-in noise is available, so the observed spread cannot be separated from evaluation noise.")
    else:
        noise = f"{np.sqrt(d['sigma2']):.2f} pts" if d["spread_pts"] is not None else f"{np.sqrt(d['sigma2']):.3g} (metric units)"
        if d["sigma2_source"] == "measured":
            reps = f"reported values average {d['n_reps']:.0f} replicates{'' if d['n_reps_known'] else ' (assumed)'}"
            p.append(f"Seed noise SD of one evaluation is {noise} ({d['n_sd_models']} model entries with SDs; {reps}), so {100*d['score']:.0f}% of the spread is repeatable model difference (score {d['score']:.2f}, 90% CI {d['score_lo']:.2f}-{d['score_hi']:.2f}).")
            if d.get("score_top") is not None: p.append(f"Among the leading half of the models only, {100*d['score_top']:.0f}% of the spread is repeatable (frontier score {d['score_top']:.2f}).")
        else: p.append(f"No printed seed SD; with a plug-in noise SD of {noise} ({d['sigma2_source']}) about {100*d['score']:.0f}% of the spread would be repeatable (provisional score {d['score']:.2f}).")
    if d.get("unexplained_share") is not None: p.append(f"{100*d['unexplained_share']:.0f}% of the stable model differences are not explained by the {K} shared capability factor{'s' if K != 1 else ''} (dataset-specific signal).")
    if d.get("info_share"): p.append(f"Contributes {100*d['info_share']:.1f}% of the information the whole suite gives about shared capabilities (redundancy-adjusted).")
    return " ".join(p)

MAIN = TABLES[MAIN_VARIANT]; Tm = MAIN["T"]
groups = {name: g for name, g in Tm.groupby("canonical_dataset") if name}
# info share per latent variant (Shapley over datasets)
INFO = {}
for rk in ("10", "3"):
    b = L[rk]; ti = {t: i for i, t in enumerate(b["tasks"])}; c = np.maximum(b["fit"].resid_var, 0.05)
    grp = {name: np.array([ti[t] for t in g.index if t in ti]) for name, g in groups.items()}; grp = {k: v for k, v in grp.items() if len(v)}
    shap = shapley_information(grp, b["fit"].lam, c, K, n_perm=300, seed=SEED); tot = sum(v for v in shap.values() if v > 0)
    INFO[rk] = {k: (rnd(v / tot, 4) if tot > 0 else None, rnd(v, 3)) for k, v in shap.items()}
log("info shares done")

def summarise(name, Tg_main):
    d = {"name": name, **score_block(Tg_main, MAIN, cells["all"])}
    d["benchmark_ids"] = sorted(Tg_main.benchmark_id.unique().tolist()); d["protocol_families"] = sorted(Tg_main.pf.unique().tolist())
    d["task_type"] = str(Tg_main.task_type.mode().iat[0]) if Tg_main.task_type.replace("", np.nan).notna().any() else ""
    w = Tg_main.n_models.values
    d.update(latent_block(Tg_main, LAT[MAIN_VARIANT]["10"], w)); d["info_share"], d["info_nats"] = INFO["10"].get(name, (None, None))
    d["variants"] = {}
    for key, V in TABLES.items():
        if key == MAIN_VARIANT: continue
        Tg = V["T"][V["T"].canonical_dataset == name]; s = cells["independent"] if key.endswith("independent") else cells["all"]
        d["variants"][key] = score_block(Tg, V, s)
    d["latent_variants"] = {"3": {**latent_block(Tg_main, LAT[MAIN_VARIANT]["3"], w), "info_share": INFO["3"].get(name, (None, None))[0]}}
    d["by_protocol"] = {}
    for pf, g in Tg_main.groupby("pf"):
        bp = score_block(g, MAIN, cells["all"]); bp.update(latent_block(g, LAT[MAIN_VARIANT]["10"], g.n_models.values)); bp["variants"] = {}
        for key, V in TABLES.items():
            if key == MAIN_VARIANT: continue
            Tg = V["T"][(V["T"].canonical_dataset == name) & (V["T"].pf == pf)]; s = cells["independent"] if key.endswith("independent") else cells["all"]
            bp["variants"][key] = score_block(Tg, V, s)
        bp["latent_variants"] = {"3": latent_block(g, LAT[MAIN_VARIANT]["3"], g.n_models.values)}
        d["by_protocol"][pf] = bp
    d["tasks"] = [task_rec(t, Tm, LAT[MAIN_VARIANT]["10"]) for t in Tg_main.sort_values("n_models", ascending=False).index]
    d["explanation"] = explain(d, K)
    return d

datasets, unlisted = {}, []
for name, g in groups.items():
    d = summarise(name, g); d["domain"] = g.domain.iat[0]; d["subdomain"] = g.subdomain.iat[0]; d["input_kind"] = g.input_kind.iat[0]
    eid = g.eoarena_id.iat[0]
    if eid and eid in known: d["id"] = eid; datasets[eid] = d
    else: unlisted.append(d)
for name, g in r[~r.canonical_dataset.isin(groups)].groupby("canonical_dataset"):
    if not name: continue
    d = {"name": name, **EMPTY, "models": int(g.model_id.nunique()), "papers": int(g.paper_key.nunique()), "results": int(len(g)), "benchmark_ids": sorted(g.benchmark_id.unique().tolist()),
         "protocol_families": sorted(g.pf.unique().tolist()), "task_type": str(g.benchmark_id.map(breg.task_type).dropna().mode().iat[0]) if g.benchmark_id.map(breg.task_type).notna().any() else "",
         "n_sd_models": 0, "score_all": None, "n_reps": None, "n_reps_known": False, "sigma2": None, "unexplained_share": None, "r2_shared": None, "info_share": None, "self_share": rnd(g.self.mean()),
         "by_protocol": {}, "variants": {}, "latent_variants": {}, "tasks": [], "domain": g.domain.iat[0], "subdomain": g.subdomain.iat[0], "input_kind": g.input_kind.iat[0]}
    d["explanation"] = f"{d['models']} model{'s' if d['models'] != 1 else ''} scored in {d['papers']} paper{'s' if d['papers'] != 1 else ''}, but no single comparison has 4 or more models, so spread and reliability cannot be assessed."
    eid = g.eoarena_id.iat[0]
    if eid and eid in known: d["id"] = eid; datasets[eid] = d
    else: unlisted.append(d)
for eid in known - set(datasets):
    datasets[eid] = {"id": eid, **EMPTY, "verdict": "e_none", "benchmark_ids": [], "variants": {}, "latent_variants": {}, "by_protocol": {}, "explanation": "No published GeoFM scores found in the workbook."}
unlisted.sort(key=lambda x: (x["domain"], -x["models"]))
log(f"{len(datasets)} inventory datasets, {len(unlisted)} unlisted")

doms = defaultdict(lambda: {"datasets": 0, "scored": 0, "measured": 0, "results": 0, "unlisted_scored": 0})
for d in list(datasets.values()) + unlisted:
    if d.get("input_kind") != "eo_imagery" or d.get("domain", "") in ("composite", "outside_taxonomy", ""): continue
    x = doms[d["domain"]]; x["datasets"] += 1; x["results"] += d["results"]; x["scored"] += d["tasks_n"] > 0; x["measured"] += d["sigma2_source"] == "measured"; x["unlisted_scored"] += "id" not in d

# ----------------------------------------------------------------------------- 5. model capability profiles
def profiles(bundle):
    Y, mask, models, tasks, lam, theta = bundle["Y"], bundle["mask"], bundle["models"], bundle["tasks"], bundle["lam"], bundle["theta"]
    pred = bundle["fit"].mu[None, :] + (theta @ lam.T if K else 0)
    tds = TINFO.loc[tasks, "canonical_dataset"].values; out = {}
    for i, m in enumerate(models):
        obs = mask[i]
        out[m] = {"theta": [rnd(x) for x in theta[i]], "general": rnd(float(pred[i].mean())), "general_obs": rnd(float(pred[i, obs].mean())) if obs.any() else None,
                  "mean_z_obs": rnd(float(Y[i, obs].mean())) if obs.any() else None, "n_tasks": int(obs.sum()), "n_datasets": int(len(set(tds[obs])))}
    return out
PR_all = profiles(L["10"]); PR_ind = profiles(L["ind"])
lam10 = L["10"]["lam"]; tasks10 = L["10"]["tasks"]; tds10 = TINFO.loc[tasks10, "canonical_dataset"]
axes = []
for k in range(K):
    s = pd.Series(lam10[:, k], index=tasks10).groupby(tds10.values).mean().sort_values()
    axes.append({"axis": k + 1, "var_share": rnd(L["10"]["meta"]["var_share"][k]), "high": [{"name": n, "loading": rnd(v)} for n, v in s[::-1].head(8).items()],
                 "low": [{"name": n, "loading": rnd(v)} for n, v in s.head(8).items()],
                 "assoc_r2": {c: rnd(assoc(lam10[:, [k]], tasks10, c)) for c in ["domain", "subdomain", "task_type", "sensor", "pf"]}})
mp = []
for m in sorted(set(PR_all) | set(PR_ind)):
    a = PR_all.get(m); b = PR_ind.get(m); inreg = m in mreg.index
    rec = {"id": m, "name": m, "backbone": str(mreg.at[m, "backbone"]) if inreg and "backbone" in mreg else "", "pretraining_dataset": str(mreg.at[m, "pretraining_dataset"]) if inreg and "pretraining_dataset" in mreg else "",
           "category": str(mreg.at[m, "category"]) if inreg and "category" in mreg else "", "all": a, "independent": b}
    rec["ranked"] = bool(b and b["n_tasks"] >= 10 and b["n_datasets"] >= 5)
    mp.append(rec)
mp.sort(key=lambda x: (not x["ranked"], -(x["independent"]["general"] if x["independent"] and x["independent"]["general"] is not None else -9)))
for i, x in enumerate(mp): x["rank"] = i + 1 if x["ranked"] else None
(ROOT / "data" / "model_profiles.json").write_text(json.dumps({
    "as_of": AS_OF, "K": K, "axes": axes, "n_ranked": sum(x["ranked"] for x in mp),
    "method": ("theta_m from the latent-factor regression y_mt = mu_t + lambda_t'theta_m + eta_mt (alternating ridge least squares, ridge 10, K factors chosen by held-out CV and bootstrap stability) "
               "on standardised imagery comparisons. Axes are the principal axes of the task loadings (a display convention: the fit is rotation-invariant), with Cov(theta) = I over models. "
               "general = mean over ALL imagery tasks of the predicted standardised score lambda_t'theta_m: the scalar a one-factor leaderboard would give, computed from the full profile. "
               "general_obs = the same mean over the tasks the model was actually evaluated on; mean_z_obs = the raw within-comparison z-score mean (the previous ranking). "
               "independent = fitted on evaluations by papers that did not introduce the model; all = every evaluation. Ranked with >= 10 independent tasks on >= 5 datasets."),
    "models": mp}, indent=1), encoding="utf-8")
log(f"model profiles: {len(mp)} models, {sum(x['ranked'] for x in mp)} ranked")

# ----------------------------------------------------------------------------- 6. replicate plan: where measured noise is missing
plan = []
for d in list(datasets.values()) + unlisted:
    if d.get("input_kind") != "eo_imagery" or d.get("domain", "") in ("composite", "outside_taxonomy", "") or d["tasks_n"] == 0 or d["sigma2_source"] == "measured": continue
    g = Tm[Tm.canonical_dataset == d["name"]]; cg = cells["all"][cells["all"].task.isin(g.index)]
    top_models = cg.groupby("model_id").task.nunique().sort_values(ascending=False).head(6)
    plan.append({"name": d["name"], "id": d.get("id"), "domain": d["domain"], "subdomain": d["subdomain"], "models": d["models"], "papers": d["papers"], "tasks_n": d["tasks_n"], "results": d["results"],
                 "evidence_mass": int(d["models"] * d["tasks_n"]), "provisional_score": d["score"], "protocol_families": d["protocol_families"],
                 "suggested_models": [{"model_id": m, "comparisons": int(n)} for m, n in top_models.items()], "benchmark_ids": d["benchmark_ids"]})
plan.sort(key=lambda x: -x["evidence_mass"])
(ROOT / "data" / "replicate_plan.json").write_text(json.dumps({"as_of": AS_OF, "method": "Datasets with published comparisons but no measured seed noise (score provisional), ordered by evidence mass = models x comparisons. Suggested models are the ones that appear in most of the dataset's comparisons; re-evaluating them with >= 5 seeds under the listed protocol families would convert the dataset's score from provisional to measured.", "datasets": plan}, indent=1), encoding="utf-8")
log(f"replicate plan: {len(plan)} provisional datasets")

# ----------------------------------------------------------------------------- 7. write
m10 = L["10"]["meta"]
meta = {
    "as_of": AS_OF,
    "source": "GeoFM meta-analysis workbook v4 (V. Mancoridis, unpublished): 14,600 reported scores from 52 papers. Summary statistics only; no individual scores.",
    "method": ("Scoring follows 'GeoFM Benchmark Scoring' (S. Wang, Oct 2026). A task is one paper's comparison of >= 4 GeoFMs on one benchmark, protocol, metric and training fraction "
               "(original results only; ablations, non-foundation baselines and from-scratch rows dropped). tau2_obs = variance of model scores within the comparison (observed separation). "
               "sigma2 = replicate noise of one evaluation: the median (main; mean as a variant) over models of the squared seed/run SD, from per-seed values listed in the cell (GEO-Bench v2 leaderboard) or a printed mean +/- sd, when >= 3 models in the comparison have one (measured); otherwise a plug-in "
               "from the same dataset, protocol family and metric (still counted as measured for the dataset), or the protocol-family median seed SD for points-scale metrics (provisional). "
               "tau2 = tau2_obs - sigma2/n_reps, where n_reps is the number of replicates behind each reported mean (seed-list length, the count the paper states, or 3 assumed; 1 for provisional tasks); EDI = tau2/sigma2; score = tau2/(tau2+sigma2) in [0,1]: "
               "the share of observed model spread that is repeatable. score_top repeats this on the leading half of each comparison (at least 4 models): the frontier score. A dataset's score is the model-count-weighted mean over its measured comparisons (provisional ones if none is measured); "
               "90% intervals bootstrap the models within each comparison jointly. by_protocol repeats everything per dataset x protocol family. variants[noise|self] repeats the scores with the mean instead of the median seed variance and/or with self-reported cells dropped "
               "(a comparison must keep >= 4 models). The latent-factor regression y = mu_t + lambda_t'theta_m + eta is fit by alternating ridge least squares on standardised imagery tasks; K is chosen by held-out-cell cross-validation (one-SE rule on RMSE) subject to bootstrap stability of the task geometry. "
               "unexplained_share = stable variation not captured by the K factors (diagnostic, not a penalty); info_share = Monte-Carlo Shapley share of log det(I + Lambda'C^-1 Lambda). latent_variants['3'] repeats these with ridge 3."),
    "verdicts": {"e_reliable": "Reliable discriminator: >= 80% of the model spread is repeatable (measured seed noise)", "e_moderate": "Moderate: 50-80% of the spread is repeatable (measured seed noise)",
                 "e_weak": "Weak or saturated: < 50% of the spread exceeds measured seed noise", "e_prov_high": "Provisional: >= 80% repeatable under plug-in noise (no printed seed SD)",
                 "e_prov_low": "Provisional: < 80% repeatable under plug-in noise (no printed seed SD)", "e_spread": "Spread only: no noise estimate, so reliability cannot be assessed",
                 "e_few": "Scored, but fewer than 4 models in any one comparison", "e_none": "No published GeoFM scores found"},
    "variants": {"main": MAIN_VARIANT, "noise": list(NOISE_AGGS), "self": list(SELF_OPTS), "ridge": list(RIDGES), "main_ridge": MAIN_RIDGE,
                 "counts": {key: {"tasks": int(len(V["T"])), "measured": int((V["T"].sigma2_source == "measured").sum()), "cells": int(V["T"].n_models.sum())} for key, V in TABLES.items()}},
    "latent": {"K": K, "ridge": RIDGES[MAIN_RIDGE], "n_models": m10["n_models"], "n_tasks": m10["n_tasks"], "density": rnd(m10["density"], 4), "K_selection": m10.get("K_selection"),
               "cv": m10.get("cv"), "geometry_stability": m10.get("stability"), "geometry_assoc_r2": {k: rnd(v) for k, v in m10["geometry_assoc_r2"].items()}, "var_share": [rnd(x) for x in m10["var_share"]],
               "residual_check": {k: v for k, v in m10.items() if k.startswith("residual_check")},
               "ridge3": {"geometry_assoc_r2": {k: rnd(v) for k, v in L["3"]["meta"]["geometry_assoc_r2"].items()}, "var_share": [rnd(x) for x in L["3"]["meta"]["var_share"]]}},
    "counts": {"tasks": int(len(Tm)), "tasks_measured": int((Tm.sigma2_source == "measured").sum()), "tasks_provisional": int(Tm.sigma2_source.isin(["same dataset, same protocol family", "protocol-family median"]).sum()),
               "tasks_no_noise": int((Tm.sigma2_source == "none").sum()), "cells_with_sd": int(cells["all"].sd.notna().sum()), "cells_with_seed_lists": int((r.sd_kind == "seeds").sum()),
               "noise_sd_by_protocol_family_pts": {pf: rnd(np.sqrt(v), 2) for pf, v in MAIN["plug_pf"].items()}},
    "datasets": datasets, "unlisted": unlisted, "domains": dict(sorted(doms.items()))}
(ROOT / "data" / "evidence.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
log(f"evidence.json written; K={K}")
for k, v in meta["latent"]["residual_check"].items():
    if v: print(k, {kk: round(vv, 3) for kk, vv in v["observed"].items() if vv is not None}, "null:", {kk: round(vv["mean"], 3) for kk, vv in v["null"].items()})
vc = pd.Series([d["verdict"] for d in list(datasets.values()) + unlisted]).value_counts(); print(vc.to_string())
