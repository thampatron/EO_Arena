#!/usr/bin/env python3
"""Dataset-level benchmarking analysis: what each benchmark dataset measures, how much it overlaps with others, and how
reproducibly independent groups agree on the model differences it shows.  Statistics in scripts/dataset_benchmarking.py;
base rows from scripts/evidence_rows.py.  Follows "GeoFM Benchmark Scoring" (S. Wang, Oct 2026).

Usage: python3 scripts/build_dataset_analysis.py <dir with metaanalysis_benchmark_table_v4.xlsx> [--quick] [--include-leaderboard]

Writes (summary statistics only; no individual scores leave the workbook):
  data/dataset_analysis.json
"""
import json, sys, time
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dataset_benchmarking as db
from evidence_rows import load

SRC = Path(sys.argv[1]); QUICK = "--quick" in sys.argv; WITH_LB = "--include-leaderboard" in sys.argv
SEED = 0; KS = (0, 1, 2, 3, 4); FOLDS = 5; RIDGE = 3.0; RIDGE_PM = 3.0
t0 = time.time()
def log(*a): print(f"[{time.time()-t0:6.0f}s]", *a, flush=True)

r, _TINFO, _make_cells, breg, _mreg, srcs = load(SRC)
mreg_all = pd.read_excel(SRC / "metaanalysis_benchmark_table_v4.xlsx", "model_registry")

# ============================================================================= inclusion rules
# (1) main-text results of papers only: table placement from data/table_locations.json (file-name rule, or checked
#     against the arXiv version); appendix / supplementary / unclear tables dropped; the public GEO-Bench-2 leaderboard
#     snapshot is not a paper's main text and is excluded unless --include-leaderboard.
# (2) no ablations: registry ablation models, ablation-study tables, and variant axes that change the model,
#     pretraining or training recipe (the paper's headline setting is kept where it is known).
# (3) GeoFMs only: models whose registry category is a geospatial foundation model / representation; random-init,
#     ImageNet, task-architecture, trivial, classical and feature baselines are dropped.
# (4) no recitations: a value reprinted from an earlier paper (same model, benchmark version, protocol, fraction, metric,
#     setting and value) is kept only in the earliest source.
# (5) evaluation-setting variants are part of the comparison key; comparison = paper | table | benchmark version |
#     protocol | fraction | setting; one canonical metric per comparison.
# (6) fixed scale: bounded metrics in points (percent, fraction x 100). R^2 (unbounded below) and error metrics are
#     not in the fit.
LOC = json.loads((ROOT / "data" / "table_locations.json").read_text())
loc = pd.DataFrame(LOC["tables"]).set_index(["paper", "file", "table_id"])
r["file"] = r.locator.astype(str).str.replace(r":(\d+|p\d+)$", "", regex=True); r["table_id"] = r.table_id.astype(str)
k = list(zip(r.paper_key, r.file, r.table_id))
r["location"] = [loc.location.get(x, "unclear") for x in k]
_line = pd.to_numeric(r.locator.astype(str).str.extract(r":(\d+)$")[0], errors="coerce")
for o in LOC.get("line_overrides", []):
    r.loc[(r.paper_key == o["paper"]) & (r.file == o["file"]) & (_line >= o["appendix_from_line"]), "location"] = "appendix"
r["is_leaderboard"] = r.source_kind.astype(str).eq("leaderboard")
r["table_ablation"] = [bool(loc.ablation.get(x, False)) for x in k]
role = mreg_all.groupby("model_id").row_role.agg(lambda s: "ablation" if (s == "ablation").any() else "")
r["model_ablation"] = r.model_id.map(role).eq("ablation") | r.model_id.astype(str).str.contains("_abl")
AX = set(LOC["ablation_axes"]); HEAD = LOC.get("headline_variants", {})
r["variant_ablation"] = np.array([a in AX and str(v) != HEAD.get(a) for a, v in zip(r.variant_axis.astype(str), r.config_variant.astype(str))], bool)
SCOPE = json.loads((ROOT / "data" / "model_scope.json").read_text())
GFM_CATS = set(SCOPE["geofm_categories"]); GFM_EXTRA = set(SCOPE["geofm_uncategorised"])
cat = mreg_all.dropna(subset=["category"]).groupby("model_id").category.agg(lambda s: s.mode().iat[0])
r["category"] = r.model_id.map(cat).fillna("")
r["is_geofm"] = r.category.isin(GFM_CATS) | r.model_id.isin(GFM_EXTRA)

steps, n0 = [], len(r)
def keep(mask, why):
    global r
    steps.append({"rule": why, "dropped": int((~mask).sum())}); r = r[mask].copy()
keep(r.location.eq("main") | r.is_leaderboard, "appendix / supplementary / unclear table")
if not WITH_LB: keep(~r.is_leaderboard, "GEO-Bench-2 leaderboard snapshot (not a paper)")
keep(~r.table_ablation, "ablation-study table")
keep(~r.model_ablation, "registry ablation model")
keep(~r.variant_ablation, "ablation variant axis (non-headline setting)")
keep(r.is_geofm, "not a GeoFM (baseline / task architecture / uncategorised)")
r["metric_s"] = r.metric.astype(str)
UNBOUNDED = {"rmse", "mse", "mae", "l1", "nmae", "rmse_utility", "far", "crps", "mape", "rel_l2", "r2"}
keep(r.pts.astype(bool) & ~r.metric_s.isin(UNBOUNDED), "metric not bounded in points (error metrics, R^2)")
# recitations
r["variant"] = r.config_variant.astype(str).where(r.variant_axis.notna(), "")
_arx = srcs.identifier.astype(str).str.extract(r"(\d{4}\.\d{4,5})")[0].fillna("9999.99999")
REL = (srcs.release_year_month.astype(str) + "|" + _arx).to_dict()      # month, then arXiv number, as the precedence key
r["release"] = r.paper_key.map(REL).fillna("9999")
# a reprint often relabels the protocol (e.g. 'frozen' for the source's 'frozen_dec' or 'LP'), so values are matched on
# model x benchmark version x metric x value (1 decimal), ignoring protocol and fraction labels; and a later paper whose
# shared cells with an earlier paper are mostly identical (>= 50% of >= 3) is treated as reprinting all of them
r["vkey"] = list(zip(r.model_id, r.benchmark_id, r.metric_s, r.y.round(1)))
first = r.sort_values(["release", "paper_key"]).drop_duplicates("vkey").set_index("vkey").paper_key
recited = r.paper_key.values != r.vkey.map(first).values
sk = list(zip(r.model_id, r.benchmark_id, r.metric_s))
r["skey"] = sk
rel = REL
reprint_pairs = []
for (pa, pb) in {(a_, b_) for a_ in r.paper_key.unique() for b_ in r.paper_key.unique() if a_ < b_}:
    A = r[r.paper_key == pa].groupby("skey").y.first().round(1); Bv = r[r.paper_key == pb].groupby("skey").y.first().round(1)
    sh = A.index.intersection(Bv.index)
    if len(sh) >= 3 and (A[sh] == Bv[sh]).mean() >= 0.5:
        later = pb if (rel.get(pb, ""), pb) > (rel.get(pa, ""), pa) else pa
        reprint_pairs.append({"earlier": pa if later == pb else pb, "later": later, "shared_cells": int(len(sh)), "identical_share": round(float((A[sh] == Bv[sh]).mean()), 2)})
        recited |= (r.paper_key.values == later) & r.skey.isin(set(sh)).values
pair = r[recited].groupby(["paper_key"]).size().to_dict()
keep(~recited, "recitation of an earlier paper's value")
r["comparison"] = (r.paper_key.astype(str) + "|" + r.table_id + "|" + r.benchmark_id.astype(str) + "|" + r.evaluation_protocol.astype(str)
                   + "|" + r.train_fraction_norm.astype(str) + "|" + r.variant)
PRIORITY = ["miou", "iou", "f1", "map", "acc", "acc_top1", "oa", "bal_acc", "micro_f1", "weighted_f1", "acc_avg"]
nm = r.groupby(["comparison", "metric_s"]).model_id.nunique().reset_index(name="n")
nm["prio"] = nm.metric_s.map({m: i for i, m in enumerate(PRIORITY)}).fillna(len(PRIORITY))
canon = nm.sort_values(["comparison", "n", "prio", "metric_s"], ascending=[True, False, True, True]).drop_duplicates("comparison").set_index("comparison").metric_s
keep(r.metric_s.values == r.comparison.map(canon).values, "metric twin (one metric kept per comparison)")
r["task"] = r.comparison + "|" + r.metric_s
log(f"rows {n0} -> {len(r)}"); [log(f"   dropped {s['dropped']:5d}  {s['rule']}") for s in steps]
log(f"   recitations by citing paper: {dict(sorted(pair.items(), key=lambda x: -x[1])[:8])}; reprint pairs: {reprint_pairs}")

TINFO = r.drop_duplicates("task").set_index("task")[["paper_key", "benchmark_id", "evaluation_protocol", "pf", "metric_s", "train_fraction_norm", "variant",
                                                    "canonical_dataset", "eoarena_id", "domain", "subdomain", "input_kind"]]
TINFO["task_type"] = TINFO.benchmark_id.map(breg.task_type).fillna(""); TINFO["sensor"] = TINFO.benchmark_id.map(breg.sensor).fillna("")
cell = r.groupby(["task", "model_id"]).agg(y=("y", "mean"), n_rows=("y", "size"), selfrep=("self", "max")).reset_index()
nmod = cell.groupby("task").model_id.nunique(); cell = cell[cell.task.isin(nmod[nmod >= 4].index)]
assert (cell.n_rows == 1).all(), "a (task, model) cell still averages several rows"

IMG = TINFO[(TINFO.input_kind == "eo_imagery") & (~TINFO.domain.isin(["composite", "outside_taxonomy"])) & (TINFO.canonical_dataset != "")].index
lc = cell[cell.task.isin(IMG)]
models = sorted(lc.model_id.unique()); tasks = sorted(lc.task.unique())
mi = {m: i for i, m in enumerate(models)}; ti = {t: i for i, t in enumerate(tasks)}
Y = np.zeros((len(models), len(tasks))); mask = np.zeros_like(Y, bool)
Y[lc.model_id.map(mi), lc.task.map(ti)] = lc.y; mask[lc.model_id.map(mi), lc.task.map(ti)] = True
TI = TINFO.loc[tasks]; td = TI.canonical_dataset.values; tp = TI.paper_key.values
PIDX = np.asarray(pd.factorize(tp)[0])
def lev(col):
    v = pd.Series(TI[col].values).astype(str).replace({"": np.nan, "nan": np.nan}); return np.asarray(pd.factorize(v)[0], int)
G_ALL = {"dataset": lev("canonical_dataset"), "protocol": lev("pf"), "sensor": lev("sensor")}
ppm = pd.DataFrame({"m": np.nonzero(mask)[0], "p": tp[np.nonzero(mask)[1]]}).groupby("m").p.nunique()
dpp = TI.groupby("canonical_dataset").paper_key.nunique()
overlap = {"models": len(models), "tasks": len(tasks), "datasets": int(len(set(td))), "papers": int(len(set(tp))), "density": round(float(mask.mean()), 4),
           "models_in_1_paper": int((ppm == 1).sum()), "models_in_3plus_papers": int((ppm >= 3).sum()), "datasets_in_2plus_papers": int((dpp >= 2).sum()),
           "models_per_task_median": float(np.median(mask.sum(0)))}
log("matrix", overlap)

SPECS = {"free (current)": ([], True), "dataset + task": (["dataset"], True), "dataset + protocol + sensor + task": (["dataset", "protocol", "sensor"], True)}
MAIN = "dataset + protocol + sensor + task"
def kw(spec, paper_offset=True):
    """paper_offset adds the paper x model implementation effect c_{m,p}. Without it, simulation on this mask shows
    held-out CV over-selects K (K_true 1 -> 2, 2 -> 3): extra factors absorb implementation effects."""
    gs, _ = SPECS[spec]
    k = dict(groups={g: G_ALL[g] for g in gs}, ridge_u=RIDGE, ridge_g={g: RIDGE for g in gs}, ridge_theta=RIDGE, n_restarts=1, n_iter=200, tol=1e-6)
    if paper_offset: k.update(paper=PIDX, ridge_pm=RIDGE_PM)
    return k

# ============================================================================= 1. K: leave-one-paper-out (primary) and held-out cells
seen_elsewhere = lambda t, p: (dpp.get(td[t], 0) >= 2)
lopo_by_K, lopo_rows = {}, {}
for K in (1, 2, 3, 4):
    k = kw(MAIN); g = k.pop("groups")
    L = db.leave_one_paper_out(Y, mask, tp, K, g, **k)
    L["dataset_seen_elsewhere"] = [seen_elsewhere(t, None) for t in L.task]; L["dataset"] = [td[t] for t in L.task]
    lopo_rows[K] = L
    lopo_by_K[K] = {c: round(float(L[c].mean()), 4) for c in ("rho_struct", "rho_global", "acc_struct", "acc_global")}
    log("LOPO K", K, lopo_by_K[K], len(L))

def paired_boot(a, b, papers, B=2000):
    """Mean of (a - b) over tasks, 90% interval and P(<=0) by resampling papers (tasks of one paper are not independent)."""
    d = pd.DataFrame({"d": np.asarray(a) - np.asarray(b), "p": papers}).dropna(); groups = [g.d.values for _, g in d.groupby("p")]
    rng = np.random.default_rng(SEED); bs = np.array([np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))]).mean() for _ in range(B)])
    return {"mean": round(float(d.d.mean()), 4), "ci90": [round(float(np.percentile(bs, 5)), 4), round(float(np.percentile(bs, 95)), 4)],
            "p_le_0": round(float((bs <= 0).mean()), 4), "n_tasks": int(len(d)), "n_papers": len(groups)}
# K by LOPO: smallest K whose paired difference to the best K is not credibly negative
bestK = max(lopo_by_K, key=lambda K: lopo_by_K[K]["rho_struct"])
k_tests = {}
for K in lopo_by_K:
    if K == bestK: continue
    A = lopo_rows[K].set_index("task"); Bm = lopo_rows[bestK].set_index("task"); j = A.index.intersection(Bm.index)
    k_tests[K] = paired_boot(A.loc[j, "rho_struct"], Bm.loc[j, "rho_struct"], A.loc[j, "paper"])
K = min([bestK] + [k_ for k_, t in k_tests.items() if t["ci90"][1] >= 0])
log("K by LOPO", K, "best", bestK, k_tests)
Lsel = lopo_rows[K]
lopo_gain = {"all": paired_boot(Lsel.rho_struct, Lsel.rho_global, Lsel.paper)}
for flag, name in ((True, "dataset_seen_in_other_papers"), (False, "dataset_only_in_held_out_paper")):
    s = Lsel[Lsel.dataset_seen_elsewhere == flag]
    if len(s): lopo_gain[name] = paired_boot(s.rho_struct, s.rho_global, s.paper)
log("LOPO gain", lopo_gain)

sel = []
for spec in SPECS:
    for Kc in KS:
        if Kc == 0 and spec != "free (current)": continue
        k = kw(spec); g = k.pop("groups")
        cv = db.heldout_cell_cv(Y, mask, Kc, g, folds=FOLDS, seed=SEED, **k)
        sel.append(dict(spec=spec, K=Kc, paper_offset=True, pair_acc=round(cv["pair_acc"], 4), pair_acc_se=round(cv["pair_acc_se"], 4)))
        log("cv", spec, Kc, sel[-1]["pair_acc"])
for Kc in KS[1:]:
    k = kw(MAIN, paper_offset=False); g = k.pop("groups")
    cv = db.heldout_cell_cv(Y, mask, Kc, g, folds=FOLDS, seed=SEED, **k)
    sel.append(dict(spec=MAIN, K=Kc, paper_offset=False, pair_acc=round(cv["pair_acc"], 4), pair_acc_se=round(cv["pair_acc_se"], 4)))
    log("cv no-offset", Kc, sel[-1]["pair_acc"])

# ============================================================================= 2. simulation on the real mask
sim = []
k = kw(MAIN); g = k.pop("groups")
for Kt in (1, 2, 3):
    for snr in ((1.0,) if QUICK else (0.5, 1.0, 2.0)):
        Ys, Ld_true, nmz = db.simulate(mask, td, tp, Kt, snr=snr, dataset_share=0.6, paper_effect=0.5, seed=10 * Kt + int(4 * snr))
        cvs = {Kf: db.heldout_cell_cv(Ys, mask, Kf, g, folds=3, seed=SEED, **k) for Kf in KS}
        acc = {Kf: v["pair_acc"] for Kf, v in cvs.items()}; bk = max(acc, key=acc.get)
        kc = min(Kf for Kf in KS if acc[Kf] >= acc[bk] - cvs[bk]["pair_acc_se"])
        f, _ = db.fit_heteroskedastic(Ys, mask, Kt, g, **k); n2, Lh, _ = db.dataset_loadings(f, td, mask)
        multi = [i for i, n in enumerate(n2) if dpp.get(n, 0) >= 2]
        Lt = np.array([Ld_true[nmz.index(n)] for n in n2])
        rec_all = db.recovery(Lt, Lh) if Kt > 1 else None
        rec_multi = db.recovery(Lt[multi], Lh[multi]) if Kt > 1 and len(multi) > 3 else None
        sim.append(dict(K_true=Kt, snr=snr, K_selected_cv=kc, recovery_all=rec_all, recovery_multi_paper_datasets=rec_multi, pair_acc={Kf: round(a, 4) for Kf, a in acc.items()}))
        log("sim", sim[-1])

# ============================================================================= 3. dataset outputs at K
k = kw(MAIN); g = k.pop("groups"); k.update(n_restarts=3, n_iter=400)
fit, psi = db.fit_heteroskedastic(Y, mask, K, g, **k)
names, Ld, ntask = db.dataset_loadings(fit, td, mask)
comm = db.communality_by_dataset(Y, mask, fit, td)
# dataset-level quantities need independent evidence: a dataset reported by one paper has a loading that mixes that
# paper's model set and implementation with what the dataset measures, and Eq. 8 would credit it for looking distinct
MULTI = np.array([dpp.get(n, 0) >= 2 for n in names])
shap = np.full(len(names), np.nan); shap_se = np.full(len(names), np.nan)
_s, _se = db.dataset_shapley(Ld[MULTI], n_perm=200 if QUICK else 1000); shap[MULTI] = _s; shap_se[MULTI] = _se
k2 = kw("dataset + task"); g2 = k2.pop("groups")            # metadata association on a fit with no metadata blocks but dataset
fit2, _ = db.fit_heteroskedastic(Y, mask, K, g2, **k2); _, Ld2, _ = db.dataset_loadings(fit2, td, mask)
dmeta = TI.groupby("canonical_dataset").agg(domain=("domain", "first"), subdomain=("subdomain", "first"),
                                            task_type=("task_type", lambda s: s.mode().iat[0] if len(s.mode()) else ""),
                                            sensor=("sensor", lambda s: s.mode().iat[0] if len(s.mode()) else ""), papers=("paper_key", "nunique")).reindex(names)
multi = np.array([dmeta.at[n, "papers"] >= 2 for n in names])
assoc = {c: db.metadata_association(Ld2[multi], dmeta[c].fillna("").values[multi], n_perm=500 if QUICK else 2000) for c in ("domain", "subdomain", "task_type", "sensor")} if K else {}
log("assoc (datasets in >= 2 papers)", {c: (round(a["r2"], 3), round(a["null_mean"], 3), a["p_value"]) for c, a in assoc.items()})
nmods = {n: float(np.mean(mask[:, td == n].sum(0))) for n in names}
tau_obs = {}
for n in names:
    v = [(Y[mask[:, t], t].var(ddof=1), mask[:, t].sum()) for t in np.where(td == n)[0]]
    tau_obs[n] = float(np.sqrt(np.average([a for a, _ in v], weights=[w for _, w in v])))
sig = np.array([Ld[i] @ Ld[i] for i in range(len(names))]) if K else np.zeros(len(names))
from scipy.stats import spearmanr
sig_vs_n = float(spearmanr(sig, [nmods[n] for n in names]).statistic) if K else None
rec_ok = [s["recovery_multi_paper_datasets"] for s in sim if s["K_true"] == max(K, 2) and s["recovery_multi_paper_datasets"] is not None]
GEOMETRY_OK = bool(rec_ok) and float(np.median(rec_ok)) >= 0.7
S = db.similarity(Ld) if K else None
log(f"signal vs models-per-task rho={sig_vs_n}; geometry recoverable={GEOMETRY_OK} ({rec_ok})")

# ============================================================================= 4. cross-paper reproducibility (exact version x protocol x fraction x metric x setting)
rr = cell[cell.task.isin(IMG)].merge(TINFO, left_on="task", right_index=True)
rr["group"] = rr.canonical_dataset + " | " + rr.benchmark_id.astype(str) + " | " + rr.evaluation_protocol.astype(str) + " | " + rr.train_fraction_norm.astype(str) + " | " + rr.metric_s + (" | " + rr.variant).where(rr.variant != "", "")
rr = rr.groupby(["group", "paper_key", "model_id"], as_index=False).y.mean()
rep = db.cross_paper_reproducibility(rr.rename(columns={"paper_key": "paper", "model_id": "model"})[["group", "paper", "model", "y"]], n_boot=100 if QUICK else 500)
log(f"reproducibility: {len(rep)} groups with >= 5 shared models and df >= 5")
repl = []
for gname, gg in rr.groupby("group"):
    ps = gg.paper_key.unique()
    if len(ps) < 2: continue
    mc = gg.groupby("model_id").paper_key.nunique()
    repl.append({"group": gname, "papers": int(len(ps)), "geofms_in_2plus_papers": int((mc >= 2).sum())})
repl = pd.DataFrame(repl)
replication = {"groups_with_2plus_papers": int(len(repl)), "with_3plus_shared_geofms": int((repl.geofms_in_2plus_papers >= 3).sum()) if len(repl) else 0,
               "with_5plus_shared_geofms": int((repl.geofms_in_2plus_papers >= 5).sum()) if len(repl) else 0,
               "groups": repl.sort_values("geofms_in_2plus_papers", ascending=False).head(15).to_dict("records") if len(repl) else []}
log("replication", {k: v for k, v in replication.items() if k != "groups"})

# ============================================================================= write
def rnd(x, d=3):
    return None if x is None or not np.isfinite(x) else round(float(x), d)
out = {"as_of": time.strftime("%Y-%m-%d"),
       "scope": {"rows_in": n0, "rows_kept": int(len(r)), "dropped": steps, "reprint_pairs": reprint_pairs, "include_leaderboard": WITH_LB, "model_scope": "data/model_scope.json"},
       "overlap": overlap,
       "K": {"chosen": K, "criterion": "leave-one-paper-out Spearman of predicted within-task model order; smallest K not credibly worse than the best (paired bootstrap over papers)",
             "lopo_by_K": lopo_by_K, "paired_vs_best": k_tests, "heldout_cells": sel},
       "lopo_gain_vs_one_ordering": lopo_gain,
       "simulation": sim,
       "geometry_recoverable": GEOMETRY_OK,
       "metadata_association_multi_paper": assoc,
       "signal_vs_models_per_task_spearman": rnd(sig_vs_n),
       "datasets": {n: {"papers": int(dmeta.at[n, "papers"]), "tasks": int(ntask[i]), "models_per_task": round(nmods[n], 1),
                        "domain": dmeta.at[n, "domain"], "task_type": dmeta.at[n, "task_type"], "sensor": dmeta.at[n, "sensor"],
                        "reported_separation_pts": rnd(tau_obs[n], 2), "residual_sd_pts": rnd(float(np.sqrt(np.median(psi[td == n]))), 2),
                        "shared_signal_to_residual": rnd(sig[i]) if MULTI[i] else None, "communality_in_sample": rnd(comm.get(n, np.nan)) if MULTI[i] else None,
                        "evidence": "independent (>= 2 papers)" if MULTI[i] else "single paper: dataset-level quantities not estimable",
                        "info_share_among_multi_paper": rnd(shap[i] / np.nansum(shap), 4) if (K and MULTI[i]) else None, "info_share_mc_se": rnd(shap_se[i] / np.nansum(shap), 4) if (K and MULTI[i]) else None,
                        "lopo_rho": rnd(Lsel[Lsel.dataset == n].rho_struct.mean()), "lopo_rho_one_ordering": rnd(Lsel[Lsel.dataset == n].rho_global.mean()),
                        "nearest": ([{"name": names[j], "similarity": round(float(S[i, j]), 3)} for j in np.argsort(-S[i])[1:6]] if (GEOMETRY_OK and multi[i]) else None)}
                    for i, n in enumerate(names)},
       "reproducibility": rep.round(4).to_dict("records"), "replication_evidence": replication}
(ROOT / "data" / "dataset_analysis.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
log("wrote data/dataset_analysis.json")
