#!/usr/bin/env python3
"""The scoring note's first-stage analysis, as written (2026-11-11).

  python3 -I scripts/build_note_analysis.py <workbook_dir> [--K n] [--spec free|structured] [--private <file>] [--out data/note_analysis.json]

Follows the note's section "Analysis with published single-score evaluations" (its Eq. 9): y_mt = mu_t + lambda_t' theta_m + eta_mt,
and reports the evidence map it lists: number of latent capabilities chosen on HELD-OUT GeoFM-task CELLS (the note's
rule), latent task similarity, observed task separation, support per task, protocol comparability, association of the
task geometry with metadata (Eq. 12), stability under bootstrap resampling of GeoFMs and of tasks, the test of the
diagonal residual assumption (Eq. 2), the unexplained share (Eq. 5) and the redundancy-adjusted contribution (Eq. 8).
GeoFM capability profiles (theta) go only to --private: the public repo carries no model-level quantity.
Reservations about these outputs are recorded separately in docs/analysis-decisions.md; this script does not gate them.
"""
import contextlib, io, json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.cluster.hierarchy import linkage, leaves_list, fcluster
from scipy.spatial.distance import squareform

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dataset_benchmarking as db

A = sys.argv; SRC = A[1]
OUT = Path(A[A.index("--out") + 1]) if "--out" in A else ROOT / "data" / "note_analysis.json"
PRIV = Path(A[A.index("--private") + 1]) if "--private" in A else None
K_FORCE = int(A[A.index("--K") + 1]) if "--K" in A else None
SPEC_FORCE = A[A.index("--spec") + 1] if "--spec" in A else None
KS = (1, 2, 3, 4, 5, 6); RIDGE = 3.0; SEED = 0; BOOT = 30; t0 = time.time()
def log(*a): print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)
r4 = lambda x: None if x is None or not np.isfinite(x) else round(float(x), 4)

src = (ROOT / "scripts" / "build_dataset_analysis.py").read_text()
src = src[:src.index("# ============================================================================= 2. model-free tests")]
g = {"__file__": str(ROOT / "scripts" / "build_dataset_analysis.py"), "__name__": "matrix"}
old = sys.argv; sys.argv = ["x", SRC, "--offset", "none", "--skip-sim"]
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, "build_prefix", "exec"), g)
sys.argv = old
Y, mask, tp, td, TI, models, G_ALL, FAM = g["Y"], g["mask"], g["tp"], g["td"], g["TI"], g["models"], g["G_ALL"], g["FAM"]
M, T = Y.shape; log("matrix", Y.shape, "fill", round(float(mask.mean()), 3))
SPECS = {"free": None, "structured": {k: G_ALL[k] for k in ("dataset", "protocol", "sensor")}}
def kw(spec, restarts=3, n_iter=300):
    k = dict(ridge_u=RIDGE, ridge_theta=RIDGE, n_restarts=restarts, n_iter=n_iter, tol=1e-6, prior_group=FAM)
    if SPECS[spec]: k["ridge_g"] = {x: RIDGE for x in SPECS[spec]}
    return k

# ------------------------------------------------------------------ 1. number of latent capabilities (note: held-out cells)
cv = json.loads(Path(A[A.index("--cv-json") + 1]).read_text()) if "--cv-json" in A else {}      # reuse an earlier run of this same loop
cv = {k: {a: r4(b) for a, b in v.items() if not a.endswith("by_seed")} for k, v in cv.items()}
for spec in ([] if cv else SPECS):
    for K in KS:
        rs = [db.heldout_cell_cv(Y, mask, K, SPECS[spec], folds=5, seed=s, **kw(spec, restarts=2, n_iter=200)) for s in (0, 1, 2)]
        cv[f"{spec}|{K}"] = {"rmse": r4(np.mean([r["rmse"] for r in rs])), "rmse_se": r4(np.mean([r["rmse_se"] for r in rs]) / np.sqrt(3)),
                             "pair_acc": r4(np.mean([r["pair_acc"] for r in rs])), "pair_acc_se": r4(np.mean([r["pair_acc_se"] for r in rs]) / np.sqrt(3)),
                             "n_heldout": rs[0]["n_heldout"]}
        log("cv", spec, K, cv[f"{spec}|{K}"])
def choose(spec):                                         # smallest K within one SE of the best pairwise ranking accuracy
    best = max(KS, key=lambda K: cv[f"{spec}|{K}"]["pair_acc"]); b = cv[f"{spec}|{best}"]
    return next(K for K in KS if cv[f"{spec}|{K}"]["pair_acc"] >= b["pair_acc"] - b["pair_acc_se"]), best
spec = SPEC_FORCE or max(SPECS, key=lambda s: max(cv[f"{s}|{K}"]["pair_acc"] for K in KS))
K_sel, K_best = choose(spec); K_use = K_FORCE or K_sel
log("spec", spec, "K selected", K_sel, "best", K_best, "used", K_use)

# ------------------------------------------------------------------ 2. full fit; rotate to principal axes of the task loadings
def fit_full(Yx, mx, K, seed=0, restarts=3):
    return db.fit_heteroskedastic(Yx, mx, K, SPECS[spec], seed=seed, **kw(spec, restarts=restarts))
explained = {}
for K in KS:
    f_, _ = fit_full(Y, mask, K); P_ = f_.predict(); num = den = 0.0
    for t in range(T):
        o = mask[:, t]; y = Y[o, t]; num += ((y - P_[o, t]) ** 2).sum() / max(y.var(ddof=1), 1e-9); den += ((y - y.mean()) ** 2).sum() / max(y.var(ddof=1), 1e-9)
    explained[K] = r4(1 - num / den)
log("in-sample share of between-GeoFM variance explained", explained)
fit, psi = fit_full(Y, mask, K_use); L = fit.lam(); TH = fit.theta
w = mask.sum(0).astype(float)
U_, S_, Vt = np.linalg.svd(L * np.sqrt(w)[:, None], full_matrices=False); Rm = Vt.T
L = L @ Rm; TH = TH @ Rm
for k in range(K_use):                                    # sign: the average task loads positively
    if np.average(L[:, k], weights=w) < 0: L[:, k] *= -1; TH[:, k] *= -1
axis_share = (S_ ** 2 / (S_ ** 2).sum()).tolist()
names = sorted(set(td)); nd = len(names)
Ld = np.array([np.average(L[td == n], axis=0, weights=w[td == n]) for n in names])
S = db.similarity(Ld)
dsrc = pd.Series(tp).groupby(td).nunique().reindex(names).values; dcmp = pd.Series(td).value_counts().reindex(names).values
dmod = np.array([int(mask[:, td == n].any(1).sum()) for n in names]); multi = dsrc >= 2

# ------------------------------------------------------------------ 3. per-dataset quantities
P = fit.predict(); E = np.where(mask, Y - P, np.nan)
sep = np.array([Y[mask[:, t], t].std(ddof=1) for t in range(T)])                    # Eq. 10, original scale
comm = db.communality_by_dataset(Y, mask, fit, td)
sh, sh_se = db.dataset_shapley(Ld, n_perm=400, seed=SEED); sh_m, _ = db.dataset_shapley(Ld[multi], n_perm=400, seed=SEED)
def norm_tt(s):
    s = str(s).lower()
    return "change detection" if "change" in s else "segmentation" if "segment" in s else "regression" if "regress" in s else "detection" if "detect" in s else "classification" if "classif" in s else "other"
def norm_sensor(s):
    s = str(s).lower()
    if s in ("", "nan"): return ""
    sar = "s1" in s or "sar" in s; opt = any(k in s for k in ("s2", "landsat", "hls", "modis", "s3"))
    return "SAR + optical" if sar and opt else "SAR" if sar else "multispectral" if opt else "high-resolution optical" if any(k in s for k in ("aerial", "rgb", "planet", "naip", "worldview", "vhr", "maxar", "spot")) else "other"
dmeta = TI.groupby("canonical_dataset").agg(domain=("domain", "first"), subdomain=("subdomain", "first"),
                                            task_type=("task_type", lambda s: s.map(norm_tt).mode().iat[0]), sensor=("sensor", lambda s: s.map(norm_sensor).mode().iat[0]),
                                            family=("family", lambda s: s.mode().iat[0])).reindex(names)

# ------------------------------------------------------------------ 4. stability under bootstrap (GeoFMs; tasks)
iu = np.triu_indices(nd, 1); ium = np.triu_indices(int(multi.sum()), 1)
def sim_of(Yx, mx, tdx, seed):
    f_, _ = fit_full(Yx, mx, K_use, seed=seed, restarts=2); Lx = f_.lam(); wx = mx.sum(0).astype(float)
    Ldx = np.full((nd, K_use), np.nan)
    for i, n in enumerate(names):
        sel = (tdx == n) & (wx > 0)
        if sel.any(): Ldx[i] = np.average(Lx[sel], axis=0, weights=wx[sel])
    Lf = np.where(np.isfinite(Ldx), Ldx, 0.0); Sx = db.similarity(Lf); bad = ~np.isfinite(Ldx).all(1); Sx[bad] = np.nan; Sx[:, bad] = np.nan
    return Sx
rng = np.random.default_rng(SEED); boots = {"geofms": [], "tasks": []}
for b in range(BOOT):
    rows = rng.integers(0, M, M); boots["geofms"].append(sim_of(Y[rows], mask[rows], td, 100 + b))
    cols = rng.integers(0, T, T); boots["tasks"].append(sim_of(Y[:, cols], mask[:, cols], td[cols], 200 + b))
    if b % 10 == 9: log("bootstrap", b + 1)
stab = {}
for kind, arr in boots.items():
    arr = np.array(arr); cors, corm = [], []
    for Sx in arr:
        x, y = S[iu], Sx[iu]; ok = np.isfinite(y); cors.append(np.corrcoef(x[ok], y[ok])[0, 1])
        xm, ym = S[np.ix_(multi, multi)][ium], Sx[np.ix_(multi, multi)][ium]; ok = np.isfinite(ym); corm.append(np.corrcoef(xm[ok], ym[ok])[0, 1])
    stab[kind] = {"median_r_all_datasets": r4(np.median(cors)), "range_all": [r4(np.min(cors)), r4(np.max(cors))],
                  "median_r_multi_source": r4(np.median(corm)), "range_multi_source": [r4(np.min(corm)), r4(np.max(corm))], "B": BOOT}
    stab[kind + "_sd"] = np.nanstd(arr, axis=0)
pair_sd = np.sqrt((stab.pop("geofms_sd") ** 2 + stab.pop("tasks_sd") ** 2) / 2)
log("stability", stab)

# ------------------------------------------------------------------ 5. clusters of datasets seen in >= 2 sources
mi = np.where(multi)[0]; Sm = S[np.ix_(mi, mi)]; Dm = np.clip(1 - Sm, 0, 2); np.fill_diagonal(Dm, 0)
Z = linkage(squareform(Dm, checks=False), "average"); order = leaves_list(Z).tolist()
ncl = min(4, max(2, K_use + 1)); cl = fcluster(Z, ncl, "maxclust")
clusters = [{"cluster": int(c), "datasets": [names[mi[i]] for i in order if cl[i] == c],
             "mean_within_similarity": r4(np.mean([Sm[a, b] for a in np.where(cl == c)[0] for b in np.where(cl == c)[0] if a < b]) if (cl == c).sum() > 1 else np.nan)} for c in sorted(set(cl))]

# ------------------------------------------------------------------ 6. protocol comparability: same dataset, frozen vs fine-tuned
pf = TI.pf.values; pc = []
for n in names:
    a, b = (td == n) & (pf == "frozen"), (td == n) & (pf == "fine-tuned")
    if a.any() and b.any():
        la, lb = np.average(L[a], axis=0, weights=w[a]), np.average(L[b], axis=0, weights=w[b])
        pc.append({"dataset": n, "cosine": r4(la @ lb / max(np.linalg.norm(la) * np.linalg.norm(lb), 1e-12)), "strength_frozen": r4(np.linalg.norm(la)), "strength_fine_tuned": r4(np.linalg.norm(lb))})
Lf_ = np.array([np.average(L[(td == n) & (pf == "frozen")], axis=0, weights=w[(td == n) & (pf == "frozen")]) for n in names if ((td == n) & (pf == "frozen")).any()])
Sf_ = db.similarity(Lf_); base = float(np.mean(Sf_[np.triu_indices(len(Sf_), 1)]))
protocol = {"datasets_with_both": len(pc), "median_cosine_frozen_vs_fine_tuned_same_dataset": r4(np.median([x["cosine"] for x in pc])),
            "share_cosine_above_0_5": r4(np.mean([x["cosine"] > 0.5 for x in pc])), "mean_cosine_between_different_datasets_frozen": r4(base),
            "median_strength_frozen": r4(np.median([x["strength_frozen"] for x in pc])), "median_strength_fine_tuned": r4(np.median([x["strength_fine_tuned"] for x in pc])), "per_dataset": pc}

# ------------------------------------------------------------------ 7. metadata and the task geometry (Eq. 12)
assoc = {}
for c in ("domain", "subdomain", "task_type", "sensor"):
    lab = dmeta[c].fillna("").astype(str).values
    assoc[c] = {"all_datasets": db.metadata_association(Ld, lab, n_perm=2000, seed=SEED), "all_datasets_direction_only": db.metadata_association(Ld, lab, n_perm=2000, seed=SEED, direction_only=True),
                "multi_source": db.metadata_association(Ld[multi], lab[multi], n_perm=2000, seed=SEED)}
    assoc[c] = {k: {a: r4(b) if isinstance(b, float) else b for a, b in v.items()} for k, v in assoc[c].items()}
dom_levels = sorted(set(dmeta.domain.dropna()))
by_domain = [{"domain": d, "datasets": int((dmeta.domain.values == d).sum()), "mean_loading": [r4(x) for x in Ld[dmeta.domain.values == d].mean(0)],
              "mean_strength": r4(np.linalg.norm(Ld[dmeta.domain.values == d], axis=1).mean())} for d in dom_levels]

# ------------------------------------------------------------------ 8. is the residual covariance diagonal? (Eq. 2)
Es = E / np.sqrt(psi)[None, :]; rc = []
for i in range(T):
    for j in range(i + 1, T):
        o = mask[:, i] & mask[:, j]
        if o.sum() >= 6:
            a, b = Es[o, i], Es[o, j]
            if a.std() > 0 and b.std() > 0: rc.append((tp[i] == tp[j], td[i] == td[j], float(np.corrcoef(a, b)[0, 1])))
rc = pd.DataFrame(rc, columns=["same_source", "same_dataset", "r"])
resid = {f"{'same' if a else 'different'}_source_{'same' if b else 'different'}_dataset": {"mean_r": r4(x.r.mean()), "pairs": int(len(x))} for (a, b), x in rc.groupby(["same_source", "same_dataset"])}
log("residual correlation", resid)

# ------------------------------------------------------------------ output
nn = []
for i, n in enumerate(names):
    s = S[i].copy(); s[i] = -np.inf; j = int(np.argmax(s)); nn.append((names[j], float(S[i, j]), float(pair_sd[i, j])))
datasets = {n: {"sources": int(dsrc[i]), "comparisons": int(dcmp[i]), "geofms": int(dmod[i]), "domain": dmeta.domain.iat[i], "task_type": dmeta.task_type.iat[i], "sensor": dmeta.sensor.iat[i],
                "observed_separation_median": r4(np.median(sep[td == n])), "metric_family": dmeta.family.iat[i],
                "loading": [r4(x) for x in Ld[i]], "strength": r4(np.linalg.norm(Ld[i])), "explained_share": r4(comm[n]), "unexplained_share": r4(1 - comm[n]) if np.isfinite(comm[n]) else None,
                "contribution_all": r4(sh[i]), "contribution_share_all": r4(sh[i] / sh.sum()), "nearest": nn[i][0], "nearest_similarity": r4(nn[i][1]), "nearest_bootstrap_sd": r4(nn[i][2])}
            for i, n in enumerate(names)}
for k, i in enumerate(mi): datasets[names[i]]["contribution_share_multi_source"] = r4(sh_m[k] / sh_m.sum())
out = {"as_of": "2026-11-11", "model": "y_mt = mu_t + lambda_t' theta_m + eta_mt (note Eq. 9), residual variance per task, ridge 3", "spec": spec,
       "matrix": {"geofms": M, "tasks": T, "datasets": nd, "sources": int(len(set(tp))), "fill": r4(mask.mean()), "geofms_per_task_median": float(np.median(w)), "datasets_in_2plus_sources": int(multi.sum())},
       "cv_heldout_cells": cv, "K": {"selected_one_se_rule": K_sel, "best": K_best, "used": K_use, "rule": "smallest K within one standard error of the best held-out pairwise ranking accuracy"},
       "explained_in_sample": explained, "axis_share_of_loading_variance": [r4(x) for x in axis_share],
       "stability": stab, "clusters_multi_source": clusters, "similarity_multi_source": {"names": [names[mi[i]] for i in order], "S": [[r4(Sm[a, b]) for b in order] for a in order],
                                                                                     "bootstrap_sd": [[r4(pair_sd[mi[a], mi[b]]) for b in order] for a in order]},
       "protocol_comparability": protocol, "metadata_association": assoc, "by_domain": by_domain, "residual_correlation": resid, "datasets": datasets,
       "metadata_not_available": ["geography", "time period", "spatial resolution", "label source"]}
OUT.write_text(json.dumps(out, indent=1)); log("wrote", OUT)
if PRIV:
    PRIV.write_text(json.dumps({"models": list(models), "theta": TH.round(4).tolist(), "tasks_per_model": mask.sum(1).tolist(), "sources_per_model": [int(len(set(tp[mask[i]]))) for i in range(M)]}))
    log("wrote private capability profiles", PRIV)
