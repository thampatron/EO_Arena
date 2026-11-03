#!/usr/bin/env python3
"""Dataset-level benchmarking analysis: what each benchmark dataset measures, how much it overlaps with others, and how
reproducibly it separates GeoFMs.  Statistics in scripts/dataset_benchmarking.py; rows from scripts/evidence_rows.py
(identical inclusion rules to build_evidence.py).  Follows "GeoFM Benchmark Scoring" (S. Wang, Oct 2026).

Usage: python3 scripts/build_dataset_analysis.py <dir with metaanalysis_benchmark_table_v4.xlsx> [--quick]

Writes (summary statistics only; no individual scores leave the workbook):
  data/dataset_analysis.json   per-dataset geometry, communality, reproducibility, similarity, model-selection evidence
  docs/dataset-analysis.md     the report
"""
import json, sys, time
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dataset_benchmarking as db
from evidence_rows import load

SRC = Path(sys.argv[1]); QUICK = "--quick" in sys.argv
SEED = 0; KS = (0, 1, 2, 3, 4); FOLDS = 5
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:6.0f}s]", *a, flush=True)

r, TINFO, make_cells, breg, mreg, srcs = load(SRC)

# ----------------------------------------------------------------------------- inclusion rules beyond build_evidence.py
# (1) main-text results only: table placement from data/table_locations.json (rule on the source file name, plus a
#     check of each remaining table against the arXiv version); appendix, supplementary and unclear tables are dropped.
# (2) no ablations: models the workbook registers as ablations (row_role), tables that are ablation studies, and
#     variant axes that change the model, pretraining or training recipe.
# (3) evaluation-setting variants (test split, input bands, threshold, ...) become part of the task key instead of being
#     averaged into one cell with the paper's headline setting.
# (4) one canonical metric per comparison (metric twins computed on the same runs are not independent tasks).
# (5) fixed scale: bounded metrics in points (percent / fraction*100, R^2*100); unbounded error metrics are left out of
#     the latent fit and only counted.
LOC = json.loads((ROOT / "data" / "table_locations.json").read_text())
loc = pd.DataFrame(LOC["tables"]).set_index(["paper", "file", "table_id"])
r["file"] = r.locator.astype(str).str.replace(r":(\d+|p\d+)$", "", regex=True); r["table_id"] = r.table_id.astype(str)
k = list(zip(r.paper_key, r.file, r.table_id))
r["location"] = [loc.location.get(x, "unclear") for x in k]
_line = pd.to_numeric(r.locator.astype(str).str.extract(r":(\d+)$")[0], errors="coerce")
for o in LOC.get("line_overrides", []):
    hit = (r.paper_key == o["paper"]) & (r.file == o["file"]) & (_line >= o["appendix_from_line"])
    r.loc[hit, "location"] = "appendix"
r["table_ablation"] = [bool(loc.ablation.get(x, False)) for x in k]
mreg_role = mreg.row_role if "row_role" in mreg else pd.Series(dtype=str)
r["model_ablation"] = r.model_id.map(mreg_role).eq("ablation") | r.model_id.astype(str).str.contains("_abl")
ABLATION_AXES = set(LOC["ablation_axes"])
HEADLINE = LOC.get("headline_variants", {})          # axis -> the paper's headline setting, kept when an axis is an ablation
r["variant_ablation"] = [a in ABLATION_AXES and str(v) != HEADLINE.get(a) for a, v in zip(r.variant_axis.astype(str), r.config_variant.astype(str))]
r["variant_ablation"] = r.variant_ablation.astype(bool)
drops = {"appendix or supplementary": (r.location == "appendix").sum(), "location unclear": (r.location == "unclear").sum(),
         "ablation table": (r.table_ablation & (r.location == "main")).sum(), "ablation model": (r.model_ablation & (r.location == "main") & ~r.table_ablation).sum(),
         "ablation variant axis": (r.variant_ablation & (r.location == "main") & ~r.table_ablation & ~r.model_ablation).sum()}
n0 = len(r)
r = r[(r.location == "main") & ~r.table_ablation & ~r.model_ablation & ~r.variant_ablation].copy()
UNBOUNDED = {"rmse", "mse", "mae", "l1", "nmae", "rmse_utility", "far", "crps", "mape", "rel_l2"}
r["metric_s"] = r.metric.astype(str)
is_r2 = (r.metric_s == "r2") & (r.scale_basis == "not_percent")
r.loc[is_r2, "y"] = r.loc[is_r2, "v"] * 100; r.loc[is_r2, "pts"] = True
r["bounded"] = r.pts.astype(bool) & ~r.metric_s.isin(UNBOUNDED)
drops["unbounded metric (not in fit)"] = int((~r.bounded).sum())
r = r[r.bounded].copy()
r["variant"] = r.config_variant.astype(str).where(r.variant_axis.notna(), "")
r["comparison"] = r.paper_key.astype(str) + "|" + r.table_id.astype(str) + "|" + r.benchmark_id.astype(str) + "|" + r.evaluation_protocol.astype(str) + "|" + r.train_fraction_norm.astype(str) + "|" + r.variant
PRIORITY = ["miou", "iou", "f1", "map", "acc", "acc_top1", "oa", "bal_acc", "r2", "micro_f1", "weighted_f1", "acc_avg"]
nm = r.groupby(["comparison", "metric_s"]).model_id.nunique().reset_index(name="n")
nm["prio"] = nm.metric_s.map({m: i for i, m in enumerate(PRIORITY)}).fillna(len(PRIORITY))
canon = nm.sort_values(["comparison", "n", "prio", "metric_s"], ascending=[True, False, True, True]).drop_duplicates("comparison").set_index("comparison").metric_s
twins = int((nm.groupby("comparison").size() > 1).sum())
r = r[r.metric_s == r.comparison.map(canon)].copy()
r["task"] = r.comparison + "|" + r.metric_s
log(f"rows {n0} -> {len(r)}; dropped {drops}; {twins} comparisons had metric twins (kept one metric each)")

TINFO = r.drop_duplicates("task").set_index("task")[["paper_key", "benchmark_id", "evaluation_protocol", "pf", "metric", "train_fraction_norm", "variant",
                                                    "canonical_dataset", "eoarena_id", "domain", "subdomain", "input_kind"]]
TINFO["task_type"] = TINFO.benchmark_id.map(breg.task_type).fillna(""); TINFO["sensor"] = TINFO.benchmark_id.map(breg.sensor).fillna("")
def make_cells(drop_self):
    rr = r[~r.self] if drop_self else r
    cell = rr.groupby(["task", "model_id"]).agg(y=("y", "mean"), n_rows=("y", "size"), sd=("sd", "mean"), selfrep=("self", "max")).rename(columns={"selfrep": "self"}).reset_index()
    n = cell.groupby("task").model_id.nunique(); return cell[cell.task.isin(n[n >= 4].index)].copy()
cells = {"all": make_cells(False), "independent": make_cells(True)}
log(f"cells with >1 row after filtering (should be ~0): {(cells['all'].n_rows > 1).sum()}")

# ----------------------------------------------------------------------------- matrix on the fixed points scale
IMG = TINFO[(TINFO.input_kind == "eo_imagery") & (~TINFO.domain.isin(["composite", "outside_taxonomy"])) & (TINFO.canonical_dataset != "")].index
def matrix(cell):
    lc = cell[cell.task.isin(IMG)]
    models = sorted(lc.model_id.unique()); tasks = sorted(lc.task.unique())
    mi = {m: i for i, m in enumerate(models)}; ti = {t: i for i, t in enumerate(tasks)}
    Y = np.zeros((len(models), len(tasks))); mask = np.zeros_like(Y, bool)
    Y[lc.model_id.map(mi), lc.task.map(ti)] = lc.y; mask[lc.model_id.map(mi), lc.task.map(ti)] = True
    return Y, mask, models, tasks

def level_index(values):
    v = pd.Series(values).astype(str).replace({"": np.nan, "nan": np.nan})
    codes, uniq = pd.factorize(v); return np.asarray(codes, int), list(uniq)

Y, mask, models, tasks = matrix(cells["all"])
TI = TINFO.loc[tasks]
td = TI.canonical_dataset.values; tp = TI.paper_key.values
G_ALL = {}
for g, col in (("dataset", "canonical_dataset"), ("protocol", "pf"), ("sensor", "sensor"), ("task_type", "task_type"), ("domain", "domain")):
    G_ALL[g] = level_index(TI[col].values)
log(f"matrix {Y.shape}, density {mask.mean():.4f}; {len(set(td))} datasets, {len(set(tp))} papers")

# overlap structure: how many papers each model appears in (K is identified only through cross-paper overlap)
mp = pd.DataFrame({"m": np.repeat(np.arange(len(models)), mask.shape[1]), "p": np.tile(tp, len(models)), "o": mask.ravel()})
papers_per_model = mp[mp.o].groupby("m").p.nunique()
overlap = {"models": len(models), "tasks": len(tasks), "density": float(mask.mean()),
           "models_in_1_paper": int((papers_per_model == 1).sum()), "models_in_3plus_papers": int((papers_per_model >= 3).sum()),
           "tasks_per_dataset_median": float(pd.Series(td).value_counts().median()), "datasets_in_2plus_papers": int(TI.groupby("canonical_dataset").paper_key.nunique().ge(2).sum())}
log("overlap", overlap)

SPECS = {  # name -> (groups, has u)
    "free (current)": ([], True),
    "dataset": (["dataset"], False),
    "dataset + task": (["dataset"], True),
    "dataset + protocol + sensor + task": (["dataset", "protocol", "sensor"], True),
}
RIDGES = (3.0,)   # ridge 3 was best for every spec in the 1/3/10 grid of the first full run (no paper offsets)
PIDX = np.asarray(pd.factorize(tp)[0])
def kw(spec, ridge, paper_offset=True):
    """paper_offset adds the paper x model implementation effect c_{m,p}; without it, simulation on this mask shows
    held-out CV over-selects K (K_true 1 -> 2, 2 -> 3), because extra factors absorb implementation effects."""
    gs, has_u = SPECS[spec]
    k = dict(groups={g: G_ALL[g][0] for g in gs}, ridge_u=(ridge if has_u else 1e6), ridge_g={g: ridge for g in gs}, ridge_theta=ridge, n_restarts=1, n_iter=200, tol=1e-6)
    if paper_offset: k.update(paper=PIDX, ridge_pm=3.0)
    return k

# ----------------------------------------------------------------------------- 1. model selection: spec x K x ridge, held-out cells
sel = []
for spec in SPECS:
    for ridge in RIDGES:
        for K in KS:
            if K == 0 and (spec != "free (current)" or ridge != RIDGES[0]): continue
            k = kw(spec, ridge); g = k.pop("groups")
            cv = db.heldout_cell_cv(Y, mask, K, g, folds=FOLDS, seed=SEED, **k)
            sel.append(dict(spec=spec, ridge=ridge, K=K, paper_offset=True, **cv)); log("cv", spec, ridge, K, round(cv["rmse"], 4), round(cv["pair_acc"], 4))
for K in KS:   # the same structured spec without paper offsets, for the record (what the current site's fit corresponds to)
    k = kw("dataset + protocol + sensor + task", RIDGES[0], paper_offset=False); g = k.pop("groups")
    cv = db.heldout_cell_cv(Y, mask, K, g, folds=FOLDS, seed=SEED, **k)
    sel.append(dict(spec="dataset + protocol + sensor + task", ridge=RIDGES[0], K=K, paper_offset=False, **cv)); log("cv no-offset", K, round(cv["pair_acc"], 4))
sel = pd.DataFrame(sel)
cand = sel[sel.paper_offset]
best = cand.loc[cand.pair_acc.idxmax()]
thr = best.pair_acc - best.pair_acc_se
chosen = cand[cand.pair_acc >= thr].sort_values(["K", "pair_acc"], ascending=[True, False]).iloc[0]   # one-SE rule on held-out ordering accuracy
log("chosen", chosen.to_dict())
K = int(chosen.K); SPEC = chosen.spec; RIDGE = float(chosen.ridge)

# ----------------------------------------------------------------------------- 2. leave-one-paper-out: does dataset identity transfer?
k = kw("dataset + protocol + sensor + task", RIDGE); g = k.pop("groups")
lopo = db.leave_one_paper_out(Y, mask, tp, max(K, 1), g, **k)
lopo["dataset"] = [td[t] for t in lopo.task]
log("LOPO", lopo[["rho_struct", "rho_global", "acc_struct", "acc_global"]].mean().round(3).to_dict(), len(lopo))
# paired bootstrap over papers: is the dataset-structured prediction better than one general ordering?
_d = lopo.dropna(subset=["rho_struct", "rho_global"]).assign(diff=lambda x: x.rho_struct - x.rho_global)
_pp = _d.groupby("paper")["diff"].apply(list).to_dict(); _keys = list(_pp); _rng = np.random.default_rng(SEED)
_bs = [np.mean(sum((_pp[_keys[i]] for i in _rng.integers(0, len(_keys), len(_keys))), [])) for _ in range(2000)]
lopo_gain = {"mean_rho_gain": float(_d["diff"].mean()), "ci90": [float(np.percentile(_bs, 5)), float(np.percentile(_bs, 95))],
             "p_gain_le_0": float(np.mean(np.array(_bs) <= 0)), "n_tasks": int(len(_d)), "n_papers": len(_keys)}
log("LOPO gain", lopo_gain)

# ----------------------------------------------------------------------------- 3. simulation on the real mask
sim = []
for Kt in (1, 2, 3):
    for snr in (0.5, 1.0, 2.0):
        Ys, Ld_true, nm = db.simulate(mask, td, tp, Kt, snr=snr, dataset_share=0.6, paper_effect=0.5, seed=10 * Kt + int(4 * snr))
        cvs = {Kf: db.heldout_cell_cv(Ys, mask, Kf, g, folds=3, seed=SEED, **k) for Kf in KS}
        rm = {Kf: v["pair_acc"] for Kf, v in cvs.items()}
        bk = max(rm, key=rm.get); b = min(Kf for Kf in KS if rm[Kf] >= rm[bk] - cvs[bk]["pair_acc_se"])
        f, _ = db.fit_heteroskedastic(Ys, mask, Kt, g, **k); n2, Lh, _ = db.dataset_loadings(f, td)
        rec = db.recovery(np.array([Ld_true[nm.index(n)] for n in n2]), Lh)
        sim.append(dict(K_true=Kt, snr=snr, K_best_cv=b, recovery_at_true_K=rec, **{f"pair_acc_K{kk}": v for kk, v in rm.items()}))
        log("sim", sim[-1])
sim = pd.DataFrame(sim)

# ----------------------------------------------------------------------------- 4. dataset outputs at the chosen spec
k = kw(SPEC, RIDGE); g = k.pop("groups"); k["n_restarts"] = 3; k["n_iter"] = 400
fit, psi = db.fit_heteroskedastic(Y, mask, K, g, **k)
names, Ld, ntask = db.dataset_loadings(fit, td)
S = db.similarity(Ld) if K else None
comm = db.communality_by_dataset(Y, mask, fit, td)
shap, shap_se = db.dataset_shapley(Ld, n_perm=200 if QUICK else 1000)
# reported separation (note Eq. 10): model-count-weighted mean within-comparison variance, points^2, its own model sets
tau_obs = {}
for n in names:
    cols = np.where(td == n)[0]; v = [(Y[mask[:, t], t].var(ddof=1), mask[:, t].sum()) for t in cols if mask[:, t].sum() > 1]
    tau_obs[n] = float(np.sqrt(np.average([a for a, _ in v], weights=[w for _, w in v]))) if v else np.nan
resid_sd = {n: float(np.sqrt(np.median(psi[td == n]))) for n in names}
dmeta = TI.groupby("canonical_dataset").agg(domain=("domain", "first"), subdomain=("subdomain", "first"), task_type=("task_type", lambda s: s.mode().iat[0] if len(s.mode()) else ""),
                                          sensor=("sensor", lambda s: s.mode().iat[0] if len(s.mode()) else ""), papers=("paper_key", "nunique")).reindex(names)
assoc = {c: db.metadata_association(Ld, dmeta[c].fillna("").values, n_perm=500 if QUICK else 2000) for c in ("domain", "subdomain", "task_type", "sensor")} if K else {}
log("assoc", {c: (round(a["r2"], 3), round(a["null_mean"], 3), a["p_value"]) for c, a in assoc.items()})

# cross-paper reproducibility on the raw (points) scale, per dataset x protocol family x metric
rr = cells["all"].merge(TINFO[["canonical_dataset", "pf", "metric", "paper_key"]], left_on="task", right_index=True)
rr = rr[rr.task.isin(IMG)]
rr = rr.groupby(["canonical_dataset", "pf", "metric", "paper_key", "model_id"], as_index=False).y.mean()
rr["group"] = rr.canonical_dataset + " | " + rr.pf + " | " + rr.metric.astype(str)
rep = db.cross_paper_reproducibility(rr.rename(columns={"paper_key": "paper", "model_id": "model"})[["group", "paper", "model", "y"]], n_boot=100 if QUICK else 500)
log(f"reproducibility: {len(rep)} dataset-protocol-metric groups")

# ----------------------------------------------------------------------------- write
out = {"as_of": time.strftime("%Y-%m-%d"), "overlap": overlap, "chosen": {"K": K, "spec": SPEC, "ridge": RIDGE},
       "model_selection": sel.round(4).to_dict("records"), "simulation": sim.round(4).to_dict("records"),
       "lopo": {"gain_vs_global": lopo_gain, "mean": lopo[["rho_struct", "rho_global", "acc_struct", "acc_global"]].mean().round(4).to_dict(), "n_tasks": int(len(lopo)),
                "by_dataset": lopo.groupby("dataset")[["rho_struct", "rho_global"]].mean().round(3).dropna(how="all").to_dict("index")},
       "metadata_association": assoc,
       "datasets": {n: {"n_tasks": int(ntask[i]), "papers": int(dmeta.at[n, "papers"]), "domain": dmeta.at[n, "domain"], "task_type": dmeta.at[n, "task_type"], "sensor": dmeta.at[n, "sensor"],
                        "communality": None if not np.isfinite(comm.get(n, np.nan)) else round(comm[n], 3),
                        "shared_signal_to_residual": round(float(Ld[i] @ Ld[i]), 3) if K else None,
                        "reported_separation_pts": round(tau_obs[n], 2) if np.isfinite(tau_obs[n]) else None,
                        "residual_sd_pts": round(resid_sd[n], 2),
                        "info_share": round(float(shap[i] / max(shap.sum(), 1e-12)), 4) if K else None, "info_share_mc_se": round(float(shap_se[i] / max(shap.sum(), 1e-12)), 4) if K else None,
                        "nearest": [{"name": names[j], "similarity": round(float(S[i, j]), 3)} for j in np.argsort(-S[i])[1:6]] if K else []}
                    for i, n in enumerate(names)},
       "reproducibility": rep.round(4).to_dict("records")}
(ROOT / "data" / "dataset_analysis.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
log("wrote data/dataset_analysis.json")
