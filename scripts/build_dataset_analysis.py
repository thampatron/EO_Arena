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
cells = {"all": make_cells(False), "independent": make_cells(True)}

# ----------------------------------------------------------------------------- matrix (same task filter as build_evidence.matrix)
IMG = TINFO[(TINFO.input_kind == "eo_imagery") & (~TINFO.domain.isin(["composite", "outside_taxonomy"])) & (TINFO.canonical_dataset != "")].index
def matrix(cell):
    lc = cell[cell.task.isin(IMG)].copy()
    g = lc.groupby("task").y
    lc["z"] = (lc.y - g.transform("mean")) / g.transform("std").replace(0, np.nan); lc = lc[lc.z.notna()]
    models = sorted(lc.model_id.unique()); tasks = sorted(lc.task.unique())
    mi = {m: i for i, m in enumerate(models)}; ti = {t: i for i, t in enumerate(tasks)}
    Y = np.zeros((len(models), len(tasks))); mask = np.zeros_like(Y, bool)
    Y[lc.model_id.map(mi), lc.task.map(ti)] = lc.z; mask[lc.model_id.map(mi), lc.task.map(ti)] = True
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
RIDGES = (1.0, 3.0, 10.0) if not QUICK else (3.0,)
def kw(spec, ridge):
    gs, has_u = SPECS[spec]
    return dict(groups={g: G_ALL[g][0] for g in gs}, ridge_u=(ridge if has_u else 1e6), ridge_g={g: ridge for g in gs}, ridge_theta=ridge, n_restarts=1, n_iter=200, tol=1e-6)

# ----------------------------------------------------------------------------- 1. model selection: spec x K x ridge, held-out cells
sel = []
for spec in SPECS:
    for ridge in RIDGES:
        for K in KS:
            if K == 0 and (spec != "free (current)" or ridge != RIDGES[0]): continue
            k = kw(spec, ridge); g = k.pop("groups")
            cv = db.heldout_cell_cv(Y, mask, K, g, folds=FOLDS, seed=SEED, **k)
            sel.append(dict(spec=spec, ridge=ridge, K=K, **cv)); log("cv", spec, ridge, K, round(cv["rmse"], 4), round(cv["pair_acc"], 4))
sel = pd.DataFrame(sel)
best = sel.loc[sel.rmse.idxmin()]
thr = best.rmse + best.rmse_se
chosen = sel[sel.rmse <= thr].sort_values(["K", "rmse"]).iloc[0]           # one-SE rule: fewest factors within 1 SE of best
log("chosen", chosen.to_dict())
K = int(chosen.K); SPEC = chosen.spec; RIDGE = float(chosen.ridge)

# ----------------------------------------------------------------------------- 2. leave-one-paper-out: does dataset identity transfer?
k = kw("dataset + protocol + sensor + task", RIDGE); g = k.pop("groups")
lopo = db.leave_one_paper_out(Y, mask, tp, max(K, 1), g, **k)
lopo["dataset"] = [td[t] for t in lopo.task]
log("LOPO", lopo[["rho_struct", "rho_global", "acc_struct", "acc_global"]].mean().round(3).to_dict(), len(lopo))

# ----------------------------------------------------------------------------- 3. simulation on the real mask
sim = []
for Kt in (1, 2, 3):
    for snr in (0.5, 1.0, 2.0):
        Ys, Ld_true, nm = db.simulate(mask, td, tp, Kt, snr=snr, dataset_share=0.6, paper_effect=0.5, seed=10 * Kt + int(4 * snr))
        rm = {Kf: db.heldout_cell_cv(Ys, mask, Kf, g, folds=3, seed=SEED, **k)["rmse"] for Kf in KS}
        b = min(rm, key=rm.get)
        f = db.fit_structured(Ys, mask, Kt, g, **k); n2, Lh, _ = db.dataset_loadings(f, td)
        rec = db.recovery(np.array([Ld_true[nm.index(n)] for n in n2]), Lh)
        sim.append(dict(K_true=Kt, snr=snr, K_best_cv=b, recovery_at_true_K=rec, **{f"rmse_K{kk}": v for kk, v in rm.items()}))
        log("sim", sim[-1])
sim = pd.DataFrame(sim)

# ----------------------------------------------------------------------------- 4. dataset outputs at the chosen spec
k = kw(SPEC, RIDGE); g = k.pop("groups"); k["n_restarts"] = 3; k["n_iter"] = 400
fit = db.fit_structured(Y, mask, K, g, **k)
names, Ld, ntask = db.dataset_loadings(fit, td)
S = db.similarity(Ld) if K else None
comm = db.communality_by_dataset(Y, mask, fit, td)
dmeta = TI.groupby("canonical_dataset").agg(domain=("domain", "first"), subdomain=("subdomain", "first"), task_type=("task_type", lambda s: s.mode().iat[0] if len(s.mode()) else ""),
                                          sensor=("sensor", lambda s: s.mode().iat[0] if len(s.mode()) else ""), papers=("paper_key", "nunique")).reindex(names)
assoc = {c: db.metadata_association(Ld, dmeta[c].fillna("").values, n_perm=500 if QUICK else 2000) for c in ("domain", "subdomain", "task_type", "sensor")} if K else {}
log("assoc", {c: (round(a["r2"], 3), round(a["null_mean"], 3), a["p_value"]) for c, a in assoc.items()})

# cross-paper reproducibility on the raw (points) scale, per dataset x protocol family x metric
rr = cells["all"].merge(TINFO[["canonical_dataset", "pf", "metric", "paper_key", "pts"]], left_on="task", right_index=True)
rr = rr[rr.task.isin(IMG)]
rr = rr.groupby(["canonical_dataset", "pf", "metric", "paper_key", "model_id"], as_index=False).y.mean()
rr["group"] = rr.canonical_dataset + " | " + rr.pf + " | " + rr.metric.astype(str)
rep = db.cross_paper_reproducibility(rr.rename(columns={"paper_key": "paper", "model_id": "model"})[["group", "paper", "model", "y"]], n_boot=100 if QUICK else 500)
log(f"reproducibility: {len(rep)} dataset-protocol-metric groups")

# ----------------------------------------------------------------------------- write
out = {"as_of": time.strftime("%Y-%m-%d"), "overlap": overlap, "chosen": {"K": K, "spec": SPEC, "ridge": RIDGE},
       "model_selection": sel.round(4).to_dict("records"), "simulation": sim.round(4).to_dict("records"),
       "lopo": {"mean": lopo[["rho_struct", "rho_global", "acc_struct", "acc_global"]].mean().round(4).to_dict(), "n_tasks": int(len(lopo)),
                "by_dataset": lopo.groupby("dataset")[["rho_struct", "rho_global"]].mean().round(3).dropna(how="all").to_dict("index")},
       "metadata_association": assoc,
       "datasets": {n: {"n_tasks": int(ntask[i]), "papers": int(dmeta.at[n, "papers"]), "domain": dmeta.at[n, "domain"], "task_type": dmeta.at[n, "task_type"], "sensor": dmeta.at[n, "sensor"],
                        "communality": None if not np.isfinite(comm.get(n, np.nan)) else round(comm[n], 3),
                        "loading_norm": round(float(np.linalg.norm(Ld[i])), 3) if K else None,
                        "nearest": [{"name": names[j], "similarity": round(float(S[i, j]), 3)} for j in np.argsort(-S[i])[1:6]] if K else []}
                    for i, n in enumerate(names)},
       "reproducibility": rep.round(4).to_dict("records")}
(ROOT / "data" / "dataset_analysis.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
log("wrote data/dataset_analysis.json")
