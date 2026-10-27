#!/usr/bin/env python3
"""Build data/evidence.json: reliability-adjusted scores for every benchmark with published GeoFM results.

Implements the scoring note "GeoFM Benchmark Scoring" (S. Wang, Oct 2026); the statistics live in
scripts/geofm_scoring.py.  Inputs (not in this repository):

  <dir>/metaanalysis_benchmark_table_v4.xlsx   GeoFM meta-analysis workbook (V. Mancoridis, 2026, unpublished)
  data/benchmark_map.csv                       workbook benchmark_id -> canonical dataset, EOArena id, domain, subdomain, input_kind
                                               (curated by hand; a copy in <dir> takes precedence)

Only summary statistics are written: no individual scores leave the workbook.

Usage: python3 scripts/build_evidence.py <dir>  [--no-cv]  [--boot N]  [--ridge R]  [--K k]
(--no-cv --K 3 reproduces the published fit without the 10-minute cross-validation; the CV table is then omitted from the output.)
"""
import csv, json, re, sys, time
from collections import defaultdict
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from geofm_scoring import fit_latent, cross_validate_K, select_K, task_scores, bootstrap_scores, frontier, shapley_information, geometry_stability

src = Path(sys.argv[1]); NO_CV = "--no-cv" in sys.argv
BOOT = int(sys.argv[sys.argv.index("--boot") + 1]) if "--boot" in sys.argv else 200
AS_OF = "2026-10-27"; RIDGE = float(sys.argv[sys.argv.index("--ridge") + 1]) if "--ridge" in sys.argv else 10.0; MIN_MODELS = 4; MIN_SD_MODELS = 3; SEED = 0
rng = np.random.default_rng(SEED)

# ----------------------------------------------------------------------------- 1. rows -> cells -> tasks
X = src / "metaanalysis_benchmark_table_v4.xlsx"
r = pd.read_excel(X, "results_long")
breg = pd.read_excel(X, "benchmark_registry").drop_duplicates("benchmark_id").set_index("benchmark_id")
bmap = pd.read_csv((src / "benchmark_map.csv") if (src / "benchmark_map.csv").exists() else ROOT / "data" / "benchmark_map.csv", dtype=str).fillna("").set_index("benchmark_id")
known = {d["id"] for d in json.loads((ROOT / "data" / "datasets.json").read_text(encoding="utf-8"))}

r = r[(r.exclude_from_analysis != 1) & (r.agreement_vs_recitation == "original") & (~r.model_id.astype(str).str.contains("_abl"))
      & (r.is_non_foundation_baseline != 1) & (r.evaluation_protocol != "scratch")].copy()
r["v"] = pd.to_numeric(r.result_normalized, errors="coerce"); r = r[r.v.notna()].copy()
# replicate noise per cell: (a) per-seed values listed in the cell ("IQM of seeds 205: 0.9566, 913: 0.9566, ...": the
# GEO-Bench v2 leaderboard, 5 seeds), (b) a printed "53.7 ± 0.2" or "53.7 (0.2)" seed/run SD. Rescaled to result_normalized units.
pat = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:±|\\pm|\+/-|\$\\pm\$)\s*(\d+(?:\.\d+)?)"); pat2 = re.compile(r"(-?\d+(?:\.\d+)?)\s*\(\s*(\d+(?:\.\d+)?)\s*\)")
pat_seeds = re.compile(r"seeds?\s+((?:\d+:\s*-?\d+(?:\.\d+)?,?\s*)+)")
def parse(s):
    m = pat_seeds.search(s)
    if m:
        vals = np.array([float(x) for x in re.findall(r"\d+:\s*(-?\d+(?:\.\d+)?)", m.group(1))])
        if len(vals) >= 3: return float(vals.mean()), float(vals.std(ddof=1)), "seeds"
    m = pat.search(s) or pat2.search(s)
    return (float(m.group(1)), float(m.group(2)), "printed") if m else (np.nan, np.nan, "")
P = r.raw_cell.astype(str).map(parse); r["pm_mean"] = [p[0] for p in P]; r["pm_sd"] = [p[1] for p in P]; r["sd_kind"] = [p[2] for p in P]
# number of replicates behind a reported mean: the seed list's length, else the count the paper states (from its notes), else 3 (assumed)
N_REPS = {"geobench_v2_leaderboard": 5, "earthshift": 5, "geocross-bench": 5, "melt-salt": 10, "mind": 5, "presto": 3, "prithvi_v2": 10,
          "ss_vision_transformers_for_lc": 5, "tessera_v2": 5, "agbd_eval": 3}
N_REPS_DEFAULT = 3
r["n_reps"] = np.where(r.sd_kind == "seeds", r.raw_cell.astype(str).str.count(r"\d+:\s*-?\d"), np.where(r.sd_kind == "printed", r.paper_key.map(N_REPS).fillna(N_REPS_DEFAULT), 1.0)).astype(float)
r["n_reps_known"] = (r.sd_kind == "seeds") | r.paper_key.isin(N_REPS)
ratio = (r.v / r.pm_mean).where(r.pm_mean.abs() > 0); r["sd"] = r.pm_sd * ratio.where(ratio.notna(), 1.0)
r.loc[~np.isfinite(r.sd) | (r.sd <= 0), "sd"] = np.nan; r.loc[r.sd.isna(), "n_reps"] = 1.0   # a printed "± 0.00" is below the table's precision, not a measured noise
r["y"] = np.where(r.higher_is_better.astype(str) == "True", r.v, -r.v)
r["pts"] = r.scale_basis.isin(["percent_printed", "fraction_printed"])
PF = lambda p: "fine-tuned" if p in ("FT", "PFT") else "frozen" if p in ("frozen_dec", "LP", "kNN", "frozen", "frozen_best", "PE", "MLP") else str(p)
r["pf"] = r.evaluation_protocol.map(PF)
for c in ["canonical_dataset", "eoarena_id", "domain", "subdomain", "input_kind"]:
    r[c] = r.benchmark_id.map(bmap[c]).fillna("")
r["task"] = r.paper_key.astype(str) + "|" + r.benchmark_id.astype(str) + "|" + r.evaluation_protocol.astype(str) + "|" + r.metric.astype(str) + "|" + r.train_fraction_norm.astype(str)
own = r[r.is_self_reported == True].groupby("model_id").paper_key.agg(set).to_dict()
r["self"] = [p in own.get(m, set()) for m, p in zip(r.model_id, r.paper_key)]

cell = r.groupby(["task", "model_id"]).agg(y=("y", "mean"), sd=("sd", "mean"), n_reps=("n_reps", "max"), n_known=("n_reps_known", "max"), selfrep=("self", "max")).rename(columns={"selfrep": "self"}).reset_index()
n = cell.groupby("task").model_id.nunique(); cell = cell[cell.task.isin(n[n >= MIN_MODELS].index)].copy()
tinfo = r.drop_duplicates("task").set_index("task")[["paper_key", "benchmark_id", "evaluation_protocol", "pf", "metric", "train_fraction_norm", "pts",
                                                     "canonical_dataset", "eoarena_id", "domain", "subdomain", "input_kind"]]
tinfo = tinfo.loc[cell.task.unique()]
tinfo["task_type"] = tinfo.benchmark_id.map(breg.task_type).fillna(""); tinfo["sensor"] = tinfo.benchmark_id.map(breg.sensor).fillna("")
print(f"{len(r)} result rows -> {len(cell)} cells in {len(tinfo)} tasks (comparisons with >= {MIN_MODELS} models), {cell.model_id.nunique()} models")

# ----------------------------------------------------------------------------- 2. latent-factor regression on imagery tasks
IMG = tinfo[(tinfo.input_kind == "eo_imagery") & (~tinfo.domain.isin(["composite", "outside_taxonomy"]))].index
lc = cell[cell.task.isin(IMG)].copy()
g = lc.groupby("task").y; lc["z"] = (lc.y - g.transform("mean")) / g.transform("std").replace(0, np.nan); lc = lc[lc.z.notna()]
models = sorted(lc.model_id.unique()); tasks = sorted(lc.task.unique())
mi = {m: i for i, m in enumerate(models)}; ti = {t: i for i, t in enumerate(tasks)}
Y = np.zeros((len(models), len(tasks))); mask = np.zeros_like(Y, bool)
Y[lc.model_id.map(mi), lc.task.map(ti)] = lc.z; mask[lc.model_id.map(mi), lc.task.map(ti)] = True
print(f"latent fit on {Y.shape[0]} models x {Y.shape[1]} imagery tasks, density {mask.mean():.3f}")
t0 = time.time()
prev = json.loads((ROOT / "data" / "evidence.json").read_text(encoding="utf-8")) if (ROOT / "data" / "evidence.json").exists() else {}
cv = ({int(k): v for k, v in prev["latent"]["cv"].items()} if NO_CV and prev.get("latent", {}).get("ridge") == RIDGE and prev["latent"].get("cv") else {}) if NO_CV else cross_validate_K(Y, mask, Ks=(0, 1, 2, 3, 4, 5, 6), folds=5, seed=SEED, ridge_l=RIDGE, ridge_t=RIDGE, n_restarts=3, tol=1e-5)
stab = {}
for k in (1, 2, 3, 4):
    f0 = fit_latent(Y, mask, k, models, tasks, ridge_l=RIDGE, ridge_t=RIDGE, seed=SEED)
    stab[k] = geometry_stability(Y, mask, k, f0.lam, n_boot=20, seed=SEED, ridge_l=RIDGE, ridge_t=RIDGE)
K = int(sys.argv[sys.argv.index("--K") + 1]) if "--K" in sys.argv else select_K(cv, stab) if cv else max([k for k in stab if stab[k] >= 0.5] or [0])
fit = fit_latent(Y, mask, K, models, tasks, ridge_l=RIDGE, ridge_t=RIDGE, seed=SEED)
print(f"K = {K} (cv {time.time()-t0:.0f}s; stability {stab}), fit {fit.n_iter} iterations")

# how much of the task geometry is associated with observed task descriptors (Eq. 12, one descriptor at a time)
def assoc(col):
    if K == 0: return None
    d = pd.get_dummies(tinfo.loc[tasks, col].astype(str)); Xd = np.c_[np.ones(len(tasks)), d.values.astype(float)]
    beta, *_ = np.linalg.lstsq(Xd, fit.lam, rcond=None); res = fit.lam - Xd @ beta
    return float(1 - res.var(0).sum() / fit.lam.var(0).sum())
geometry_assoc = {c: assoc(c) for c in ["domain", "subdomain", "task_type", "sensor", "pf", "canonical_dataset"]}

# ----------------------------------------------------------------------------- 3. task-level quantities
tau2_obs = cell.groupby("task").y.var(ddof=1)
n_models = cell.groupby("task").model_id.nunique()
n_sd = cell.groupby("task").sd.apply(lambda s: int(s.notna().sum()))
sigma2_meas = cell.groupby("task").sd.apply(lambda s: float(np.nanmedian(s.dropna() ** 2)) if s.notna().sum() >= MIN_SD_MODELS else np.nan)
self_share = cell.groupby("task").self.mean()
n_reps = cell.groupby("task").apply(lambda g: float(np.median(g.n_reps[g.sd.notna()])) if g.sd.notna().any() else 1.0, include_groups=False)
n_reps_known = cell.groupby("task").apply(lambda g: bool(g.n_known[g.sd.notna()].all()) if g.sd.notna().any() else False, include_groups=False)
tau2_top = cell.groupby("task").y.apply(lambda y: float(frontier(y.values).var(ddof=1)))
n_top = cell.groupby("task").y.apply(lambda y: int(len(frontier(y.values))))
T = tinfo.copy(); T["n_models"] = n_models; T["n_sd"] = n_sd; T["tau2_obs"] = tau2_obs; T["sigma2_meas"] = sigma2_meas; T["self_share"] = self_share
T["n_reps"] = n_reps; T["n_reps_known"] = n_reps_known; T["tau2_top"] = tau2_top; T["n_top"] = n_top
T["r2"] = pd.Series(fit.r2, index=tasks); T["resid_var"] = pd.Series(fit.resid_var, index=tasks)
for k in range(K): T[f"lam{k}"] = pd.Series(fit.lam[:, k], index=tasks)

# plug-in noise for tasks without a replicate SD: (a) same dataset, protocol family and metric, (b) protocol-family median (points-scale metrics only)
meas = T[T.sigma2_meas.notna()]
plug_ds = meas.groupby(["canonical_dataset", "pf", "metric"]).apply(lambda d: np.average(d.sigma2_meas, weights=d.n_models), include_groups=False).to_dict()
plug_pf = meas[meas.pts].groupby("pf").sigma2_meas.median().to_dict()
def plug(row):
    if np.isfinite(row.sigma2_meas): return row.sigma2_meas, "measured"
    if (row.canonical_dataset, row.pf, row.metric) in plug_ds: return plug_ds[(row.canonical_dataset, row.pf, row.metric)], "same dataset, same protocol family"
    if row.pts and row.pf in plug_pf: return plug_pf[row.pf], "protocol-family median"
    return np.nan, "none"
pp = T.apply(plug, axis=1); T["sigma2"] = [p[0] for p in pp]; T["sigma2_source"] = [p[1] for p in pp]
# provisional tasks report single scores whose replicate count is unknown: n_reps = 1 (subtract the full plug-in sigma2)
T.loc[T.sigma2_source != "measured", "n_reps"] = 1.0
sc = T.apply(lambda row: task_scores(row.tau2_obs, row.sigma2, row.n_reps), axis=1, result_type="expand"); T = T.join(sc)
sct = T.apply(lambda row: task_scores(row.tau2_top, row.sigma2, row.n_reps), axis=1, result_type="expand").rename(columns={"tau2": "tau2f", "edi": "edi_top", "score": "score_top"}); T = T.join(sct)
# unexplained stable share (Eq. 5): residual variance minus noise, over tau2, in observed-variance units
def unexpl(row):
    if not np.isfinite(row.resid_var) or not np.isfinite(row.sigma2) or row.tau2_obs <= 0: return np.nan
    psi = max(row.resid_var * row.tau2_obs - row.sigma2 / row.n_reps, 0.0); tau2 = row.tau2_obs - row.sigma2 / row.n_reps
    return float(min(psi / tau2, 1.0)) if tau2 > 0 else np.nan
T["unexplained_share"] = T.apply(unexpl, axis=1)

# bootstrap (resample models within each comparison) for the score
cell_y = {t: g.y.values for t, g in cell.groupby("task")}
def boot_scores(ts, B=BOOT):
    """B x len(ts) matrix of bootstrap task scores (NaN where no noise estimate)."""
    out = np.full((B, len(ts)), np.nan)
    for j, t in enumerate(ts):
        y = cell_y[t]; s2 = T.at[t, "sigma2"]
        if len(y) < MIN_MODELS or not np.isfinite(s2): continue
        out[:, j] = bootstrap_scores(y, s2, T.at[t, "n_reps"], B, rng)
    return out
BS = boot_scores(list(T.index)); BSI = {t: j for j, t in enumerate(T.index)}
T["score_lo"] = np.nanpercentile(BS, 5, axis=0); T["score_hi"] = np.nanpercentile(BS, 95, axis=0)
def boot_dataset(Tg):
    if not len(Tg): return None, None
    cols = [BSI[t] for t in Tg.index]; w = Tg.n_models.values.astype(float); M = BS[:, cols]
    ok = np.isfinite(M); num = np.nansum(M * w, axis=1); den = (ok * w).sum(axis=1)
    agg = np.where(den > 0, num / np.maximum(den, 1e-12), np.nan)
    return (None, None) if not np.isfinite(agg).any() else (float(np.nanpercentile(agg, 5)), float(np.nanpercentile(agg, 95)))

# ----------------------------------------------------------------------------- 4. dataset-level aggregation
def wmean(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float); ok = np.isfinite(x) & (w > 0)
    return float(np.average(x[ok], weights=w[ok])) if ok.any() else None
def rnd(x, d=3):
    try: return None if x is None or not np.isfinite(x) else round(float(x), d)
    except TypeError: return None

def verdict(d):
    if d["models"] < 4: return "e_few"
    if d["score"] is None: return "e_spread"
    if d["sigma2_source"] == "measured":
        return "e_reliable" if d["score"] >= 0.8 else "e_moderate" if d["score"] >= 0.5 else "e_weak"
    return "e_prov_high" if d["score"] >= 0.8 else "e_prov_low"

def explain(d):
    parts = [f"{d['tasks_n']} comparison{'s' if d['tasks_n'] != 1 else ''} ({d['models']} models, {d['papers']} paper{'s' if d['papers'] != 1 else ''})."]
    if d["spread_pts"] is not None: parts.append(f"GeoFMs differ by an SD of {d['spread_pts']:.2f} pts within a comparison.")
    if d["score"] is None:
        parts.append("No paper prints a seed/run standard deviation for this benchmark, and no plug-in noise is available, so the observed spread cannot be separated from evaluation noise.")
    else:
        noise = f"{np.sqrt(d['sigma2']):.2f} pts" if d["spread_pts"] is not None else f"{np.sqrt(d['sigma2']):.3g} (metric units)"
        if d["sigma2_source"] == "measured":
            reps = f"reported values average {d['n_reps']:.0f} replicates{'' if d['n_reps_known'] else ' (assumed)'}"
            parts.append(f"Seed noise SD of one evaluation is {noise} ({d['n_sd_models']} model entries with SDs; {reps}), so {100*d['score']:.0f}% of the spread is repeatable model difference (score {d['score']:.2f}, 90% CI {d['score_lo']:.2f}-{d['score_hi']:.2f}).")
            if d.get("score_top") is not None: parts.append(f"Among the leading half of the models only, {100*d['score_top']:.0f}% of the spread is repeatable (frontier score {d['score_top']:.2f}).")
        else:
            parts.append(f"No printed seed SD; with a plug-in noise SD of {noise} ({d['sigma2_source']}) about {100*d['score']:.0f}% of the spread would be repeatable (provisional score {d['score']:.2f}).")
    if d["unexplained_share"] is not None:
        parts.append(f"{100*d['unexplained_share']:.0f}% of the stable model differences are not explained by the {K} shared capability factor{'s' if K != 1 else ''} (dataset-specific signal).")
    if d.get("info_share") is not None and d["info_share"] > 0:
        parts.append(f"Contributes {100*d['info_share']:.1f}% of the information the whole suite gives about shared capabilities (redundancy-adjusted).")
    return " ".join(parts)

def task_rec(t):
    row = T.loc[t]
    return {"paper": row.paper_key, "benchmark_id": row.benchmark_id, "protocol": row.evaluation_protocol, "protocol_family": row.pf, "metric": row.metric,
            "train_fraction": None if row.train_fraction_norm in ("unspecified", "nan") else row.train_fraction_norm, "n_models": int(row.n_models),
            "spread_pts": rnd(np.sqrt(row.tau2_obs), 2) if row.pts else None, "spread_units": None if row.pts else rnd(np.sqrt(row.tau2_obs), 3),
            "noise_sd": rnd(np.sqrt(row.sigma2), 3), "noise_source": row.sigma2_source, "n_sd_models": int(row.n_sd), "n_reps": rnd(row.n_reps, 1), "n_reps_known": bool(row.n_reps_known),
            "n_top": int(row.n_top), "spread_top_pts": rnd(np.sqrt(row.tau2_top), 2) if row.pts else None, "score_top": rnd(row.score_top), "edi_top": rnd(row.edi_top, 1),
            "score": rnd(row.score), "score_lo": rnd(row.score_lo), "score_hi": rnd(row.score_hi), "edi": rnd(row.edi, 1),
            "r2_shared": rnd(row.r2), "unexplained_share": rnd(row.unexplained_share), "self_share": rnd(row.self_share, 2)}

def summarise(name, Tg):
    cg = cell[cell.task.isin(Tg.index)]; w = Tg.n_models.values
    d = {"name": name, "tasks_n": int(len(Tg)), "models": int(cg.model_id.nunique()), "papers": int(Tg.paper_key.nunique()), "results": int(len(cg)),
         "benchmark_ids": sorted(Tg.benchmark_id.unique().tolist()), "protocol_families": sorted(Tg.pf.unique().tolist())}
    pts = Tg[Tg.pts]
    d["spread_pts"] = rnd(np.sqrt(np.average(pts.tau2_obs, weights=pts.n_models)), 2) if len(pts) else None
    d["task_type"] = str(Tg.task_type.mode().iat[0]) if Tg.task_type.replace("", np.nan).notna().any() else ""
    d["n_sd_models"] = int(Tg.n_sd.sum())
    # headline: tasks whose noise is measured on this dataset (directly, or carried over to its other comparisons with the same
    # protocol family and metric); otherwise provisional tasks. Interval: joint bootstrap of the models within each comparison.
    own = Tg[Tg.sigma2_source.isin(["measured", "same dataset, same protocol family"]) & Tg.score.notna()]
    use = own if len(own) else Tg[Tg.score.notna()]
    d["sigma2_source"] = "measured" if len(own) else (use.sigma2_source.mode().iat[0] if len(use) else "none")
    d["score"] = wmean(use.score, use.n_models) if len(use) else None
    d["sigma2"] = wmean(use.sigma2, use.n_models) if len(use) else None
    d["score_lo"], d["score_hi"] = boot_dataset(use)
    d["edi"] = None if d["score"] is None else (d["score"] / (1 - d["score"]) if d["score"] < 1 else float("inf"))
    d["score_top"] = wmean(use.score_top, use.n_models) if len(use) else None
    d["edi_top"] = None if d["score_top"] is None else (d["score_top"] / (1 - d["score_top"]) if d["score_top"] < 1 else float("inf"))
    d["n_reps"] = wmean(use.n_reps, use.n_models) if len(use) else None
    d["n_reps_known"] = bool(use.n_reps_known.all()) if len(use) else False
    d["noise_sd"] = None if d["sigma2"] is None or not Tg.pts.any() else float(np.sqrt(d["sigma2"]))
    d["score_all"] = wmean(Tg.score, w)
    d["unexplained_share"] = wmean(Tg.unexplained_share, w)
    d["r2_shared"] = wmean(Tg.r2, w)
    d["self_share"] = wmean(Tg.self_share, w)
    d["by_protocol"] = {pf: {"n_tasks": int(len(g)), "n_models": int(cell[cell.task.isin(g.index)].model_id.nunique()), "score": wmean(g.score, g.n_models),
                             "spread_pts": rnd(np.sqrt(np.average(g[g.pts].tau2_obs, weights=g[g.pts].n_models)), 1) if g.pts.any() else None,
                             "sigma2_source": "measured" if (g.sigma2_source == "measured").any() else g.sigma2_source.mode().iat[0]} for pf, g in Tg.groupby("pf")}
    if K:
        Tl = Tg[Tg[[f"lam{k}" for k in range(K)]].notna().all(axis=1)]
        if len(Tl):
            lam = Tl[[f"lam{k}" for k in range(K)]].values.astype(float)
            nrm = np.linalg.norm(lam, axis=1, keepdims=True); u = lam / np.maximum(nrm, 1e-9)
            d["loading"] = [rnd(x) for x in np.average(u, axis=0, weights=Tl.n_models.values)]
    d["tasks"] = [task_rec(t) for t in Tg.sort_values("n_models", ascending=False).index]
    d["verdict"] = verdict(d)
    return d

groups = {name: g for name, g in T.groupby("canonical_dataset") if name}
summ = {name: summarise(name, g) for name, g in groups.items()}
# redundancy-adjusted information contribution (Eq. 8) over imagery datasets, using standardised loadings
if K:
    c = np.maximum(fit.resid_var, 0.05); grp = {}
    for name, g in groups.items():
        rows = np.array([ti[t] for t in g.index if t in ti]);
        if len(rows): grp[name] = rows
    shap = shapley_information(grp, fit.lam, c, K, n_perm=300, seed=SEED); tot = sum(v for v in shap.values() if v > 0)
    for name, v in shap.items(): summ[name]["info_share"] = rnd(v / tot, 4) if tot > 0 else None; summ[name]["info_nats"] = rnd(v, 3)
for d in summ.values(): d["explanation"] = explain(d)

# attach dataset descriptors and split into inventory / unlisted
datasets, unlisted = {}, []
for name, g in groups.items():
    d = summ[name]; d["domain"] = g.domain.iat[0]; d["subdomain"] = g.subdomain.iat[0]; d["input_kind"] = g.input_kind.iat[0]
    eid = g.eoarena_id.iat[0]
    for k in ["score", "score_lo", "score_hi", "score_all", "score_top", "sigma2", "unexplained_share", "r2_shared", "self_share"]: d[k] = rnd(d[k])
    for k in ["edi", "edi_top"]: d[k] = None if d[k] is None else (rnd(d[k], 1) if np.isfinite(d[k]) else 1e9)
    d["n_reps"] = rnd(d["n_reps"], 1); d["noise_sd"] = rnd(d["noise_sd"], 2)
    for pf in d["by_protocol"].values(): pf["score"] = rnd(pf["score"])
    if eid and eid in known: d["id"] = eid; datasets[eid] = d
    else: unlisted.append(d)
# datasets with published rows but no comparison of >= 4 models, and inventory datasets with nothing
rows_by = r[~r.canonical_dataset.isin(groups)].groupby("canonical_dataset")
for name, g in rows_by:
    if not name: continue
    d = {"name": name, "tasks_n": 0, "models": int(g.model_id.nunique()), "papers": int(g.paper_key.nunique()), "results": int(len(g)), "benchmark_ids": sorted(g.benchmark_id.unique().tolist()),
         "protocol_families": sorted(g.pf.unique().tolist()), "task_type": str(g.benchmark_id.map(breg.task_type).dropna().mode().iat[0]) if g.benchmark_id.map(breg.task_type).notna().any() else "", "spread_pts": None, "n_sd_models": 0, "sigma2_source": "none", "score": None, "score_lo": None, "score_hi": None, "score_all": None,
         "edi": None, "score_top": None, "edi_top": None, "n_reps": None, "n_reps_known": False, "sigma2": None, "noise_sd": None, "unexplained_share": None, "r2_shared": None, "self_share": rnd(g.self.mean()), "by_protocol": {}, "tasks": [], "verdict": "e_few",
         "domain": g.domain.iat[0], "subdomain": g.subdomain.iat[0], "input_kind": g.input_kind.iat[0]}
    d["explanation"] = f"{d['models']} model{'s' if d['models'] != 1 else ''} scored in {d['papers']} paper{'s' if d['papers'] != 1 else ''}, but no single comparison has 4 or more models, so spread and reliability cannot be assessed."
    eid = g.eoarena_id.iat[0]
    if eid and eid in known: d["id"] = eid; datasets[eid] = d
    else: unlisted.append(d)
for eid in known - set(datasets):
    datasets[eid] = {"id": eid, "tasks_n": 0, "models": 0, "papers": 0, "results": 0, "benchmark_ids": [], "verdict": "e_none", "score": None, "sigma2_source": "none", "explanation": "No published GeoFM scores found in the workbook."}
unlisted.sort(key=lambda x: (x["domain"], -x["models"]))

doms = defaultdict(lambda: {"datasets": 0, "scored": 0, "measured": 0, "results": 0, "unlisted_scored": 0})
for d in list(datasets.values()) + unlisted:
    if d.get("input_kind") != "eo_imagery" or d.get("domain", "") in ("composite", "outside_taxonomy", ""): continue
    x = doms[d["domain"]]; x["datasets"] += 1; x["results"] += d["results"]; x["scored"] += d["tasks_n"] > 0; x["measured"] += d["sigma2_source"] == "measured"; x["unlisted_scored"] += "id" not in d

meta = {
    "as_of": AS_OF,
    "source": "GeoFM meta-analysis workbook v4 (V. Mancoridis, unpublished): 14,600 reported scores from 52 papers. Summary statistics only; no individual scores.",
    "method": ("Scoring follows 'GeoFM Benchmark Scoring' (S. Wang, Oct 2026). A task is one paper's comparison of >= 4 GeoFMs on one benchmark, protocol, metric and training fraction "
               "(original results only; ablations, non-foundation baselines and from-scratch rows dropped). tau2_obs = variance of model scores within the comparison (observed separation). "
               "sigma2 = replicate noise of one evaluation: the median over models of the squared seed/run SD, from per-seed values listed in the cell (GEO-Bench v2 leaderboard) or a printed mean +/- sd, when >= 3 models in the comparison have one (measured); otherwise a plug-in "
               "from the same dataset, protocol family and metric (still counted as measured for the dataset), or the protocol-family median seed SD for points-scale metrics (provisional). tau2 = tau2_obs - sigma2/n_reps, where n_reps is the number of replicates behind each reported mean (seed-list length, the count the paper states, or 3 assumed; 1 for provisional tasks); EDI = tau2/sigma2; score = tau2/(tau2+sigma2) in [0,1]: "
               "the share of observed model spread that is repeatable. score_top repeats this on the leading half of each comparison (at least 4 models): the frontier score. A dataset's score is the model-count-weighted mean over its measured comparisons (provisional ones if none is measured); "
               "90% intervals bootstrap the models within each comparison. The latent-factor regression y = mu_t + lambda_t'theta_m + eta is fit by alternating ridge least squares on "
               "standardised imagery tasks; K is chosen by held-out-cell cross-validation (one-SE rule on RMSE). unexplained_share = stable variation not captured by the K factors "
               "(diagnostic, not a penalty). info_share = Monte-Carlo Shapley share of log det(I + Lambda'C^-1 Lambda), the redundancy-adjusted information the dataset adds about shared capabilities."),
    "verdicts": {"e_reliable": "Reliable discriminator: >= 80% of the model spread is repeatable (measured seed noise)",
                 "e_moderate": "Moderate: 50-80% of the spread is repeatable (measured seed noise)",
                 "e_weak": "Weak or saturated: < 50% of the spread exceeds measured seed noise",
                 "e_prov_high": "Provisional: >= 80% repeatable under plug-in noise (no printed seed SD)",
                 "e_prov_low": "Provisional: < 80% repeatable under plug-in noise (no printed seed SD)",
                 "e_spread": "Spread only: no noise estimate, so reliability cannot be assessed",
                 "e_few": "Scored, but fewer than 4 models in any one comparison",
                 "e_none": "No published GeoFM scores found"},
    "latent": {"K": K, "K_selection": "smallest K within one SE of the best held-out RMSE, stepped down until bootstrap geometry stability >= 0.5", "ridge": RIDGE, "n_models": len(models), "n_tasks": len(tasks), "density": rnd(mask.mean(), 4),
               "cv": {str(k): {a: rnd(b, 4) for a, b in v.items()} for k, v in cv.items()},
               "geometry_stability": {str(k): rnd(v) for k, v in stab.items()}, "geometry_assoc_r2": {k: rnd(v) for k, v in geometry_assoc.items()}},
    "counts": {"tasks": int(len(T)), "tasks_measured": int((T.sigma2_source == "measured").sum()), "tasks_provisional": int(T.sigma2_source.isin(["same dataset, same protocol family", "protocol-family median"]).sum()),
               "tasks_no_noise": int((T.sigma2_source == "none").sum()), "cells_with_sd": int(cell.sd.notna().sum()),
               "noise_sd_by_protocol_family_pts": {pf: rnd(np.sqrt(v), 2) for pf, v in plug_pf.items()}, "cells_with_seed_lists": int((r.sd_kind == "seeds").sum())},
    "datasets": datasets, "unlisted": unlisted, "domains": dict(sorted(doms.items()))}
(ROOT / "data" / "evidence.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"evidence.json: {len(datasets)} EOArena datasets, {len(unlisted)} unlisted, {meta['counts']}")
vc = pd.Series([d["verdict"] for d in list(datasets.values()) + unlisted]).value_counts(); print(vc.to_string())
print("K:", K, "cv:", {k: (v["rmse"], v["pair_acc"]) for k, v in cv.items()}, "stability:", stab, "assoc:", geometry_assoc)
top = sorted([d for d in list(datasets.values()) + unlisted if d["sigma2_source"] == "measured"], key=lambda d: -d["edi"])[:20]
for d in top: print(f"{d['score']:.3f} edi {d['edi']:8.1f} {d['name'][:40]:40s} tasks {d['tasks_n']:3d} models {d['models']:3d} spread {d['spread_pts']} noise_sd {d['noise_sd']} unexpl {d['unexplained_share']} info {d.get('info_share')}")
