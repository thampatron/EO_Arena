#!/usr/bin/env python3
"""Exploration on top of the note's first-stage fit (2026-11-11): what the task geometry tells us and how much of it is firm.

  python3 -I scripts/build_note_explore.py <workbook_dir> [--out data/note_explore.json] [--B 30]

1  uncertainty of every dataset's position (bootstrap over GeoFMs and over tasks, Procrustes-aligned)
2  varimax rotation of the K = 3 loadings
3  dataset uniqueness (note Eq. 5) and whether the unexplained part repeats across sources
4  pretraining group x dataset group: mean within-task rank percentile (no latent axes; groups, never single GeoFMs)
5  frozen-encoder-only fit: K by held-out cells, and whether the geometry changes
6  leave-one-source-out: which sources drive the geometry
7  slices: mean position by task type and by sensor, with bootstrap intervals
8  K = 4..6: what the extra dimensions are made of
Dataset- and group-level summaries only.
"""
import contextlib, io, json, sys, time
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dataset_benchmarking as db

A = sys.argv; SRC = A[1]
OUT = Path(A[A.index("--out") + 1]) if "--out" in A else ROOT / "data" / "note_explore.json"
BOOT = int(A[A.index("--B") + 1]) if "--B" in A else 30
K0 = 3; RIDGE = 3.0; t0 = time.time()
def log(*a): print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)
r4 = lambda x: None if x is None or not np.isfinite(x) else round(float(x), 4)

def matrix(flags=()):
    src = (ROOT / "scripts" / "build_dataset_analysis.py").read_text()
    src = src[:src.index("# ============================================================================= 2. model-free tests")]
    g = {"__file__": str(ROOT / "scripts" / "build_dataset_analysis.py"), "__name__": "matrix"}
    old = sys.argv; sys.argv = ["x", SRC, "--offset", "none", "--skip-sim", *flags]
    try:
        with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, "build_prefix", "exec"), g)
    finally: sys.argv = old
    return g

def groups_of(g): return {k: g["G_ALL"][k] for k in ("dataset", "protocol", "sensor")}
def kw(g, restarts=3, n_iter=300): return dict(ridge_u=RIDGE, ridge_theta=RIDGE, ridge_g={k: RIDGE for k in ("dataset", "protocol", "sensor")}, n_restarts=restarts, n_iter=n_iter, tol=1e-6, prior_group=g["FAM"])
def fit(g, Y, mask, K, seed=0, restarts=3, G=None, fam=None):
    k = kw(g, restarts)
    if fam is not None: k["prior_group"] = fam
    return db.fit_heteroskedastic(Y, mask, K, G if G is not None else groups_of(g), seed=seed, **k)
def principal(L, w):
    _, S_, Vt = np.linalg.svd(L * np.sqrt(w)[:, None], full_matrices=False); R = Vt.T; L2 = L @ R
    sg = np.sign([np.average(L2[:, k], weights=w) for k in range(L.shape[1])]); sg[sg == 0] = 1
    return R * sg, (S_ ** 2 / (S_ ** 2).sum())
def ds_load(L, w, td, names):
    out = np.full((len(names), L.shape[1]), np.nan)
    for i, n in enumerate(names):
        sel = (td == n) & (w > 0)
        if sel.any(): out[i] = np.average(L[sel], axis=0, weights=w[sel])
    return out
def procrustes(Ax, B):                                    # orthogonal R minimising |Ax R - B| on rows present in both
    ok = np.isfinite(Ax).all(1) & np.isfinite(B).all(1); U, _, Vt = np.linalg.svd(Ax[ok].T @ B[ok]); return U @ Vt
def varimax(L, n_iter=200, tol=1e-8):
    p, k = L.shape; R = np.eye(k); d = 0
    for _ in range(n_iter):
        Lr = L @ R; u, s, vt = np.linalg.svd(L.T @ (Lr ** 3 - Lr @ np.diag((Lr ** 2).sum(0)) / p)); R = u @ vt; d_new = s.sum()
        if d_new < d * (1 + tol): break
        d = d_new
    return R
def sim_corr(La, Lb, sel):
    Sa, Sb = db.similarity(np.nan_to_num(La[sel])), db.similarity(np.nan_to_num(Lb[sel])); iu = np.triu_indices(int(sel.sum()), 1)
    ok = np.isfinite(La[sel]).all(1)[iu[0]] & np.isfinite(La[sel]).all(1)[iu[1]] & np.isfinite(Lb[sel]).all(1)[iu[0]] & np.isfinite(Lb[sel]).all(1)[iu[1]]
    return float(np.corrcoef(Sa[iu][ok], Sb[iu][ok])[0, 1])
def norm_tt(s):
    s = str(s).lower()
    return "change detection" if "change" in s else "segmentation" if "segment" in s else "regression" if "regress" in s else "detection" if "detect" in s else "classification" if "classif" in s else "other"
def norm_sensor(s):
    s = str(s).lower()
    if s in ("", "nan"): return ""
    sar = "s1" in s or "sar" in s; opt = any(k in s for k in ("s2", "landsat", "hls", "modis", "s3"))
    return "SAR + optical" if sar and opt else "SAR" if sar else "multispectral" if opt else "high-resolution optical" if any(k in s for k in ("aerial", "rgb", "planet", "naip", "worldview", "vhr", "maxar", "spot")) else "other"

g = matrix(); Y, mask, tp, td, TI, models = g["Y"], g["mask"], g["tp"], g["td"], g["TI"], g["models"]
M, T = Y.shape; w = mask.sum(0).astype(float); names = sorted(set(td)); nd = len(names)
dsrc = pd.Series(tp).groupby(td).nunique().reindex(names).values; multi = dsrc >= 2
tt = TI.task_type.map(norm_tt).values; ss = TI.sensor.map(norm_sensor).values
d_tt = np.array([pd.Series(tt[td == n]).mode().iat[0] for n in names]); d_ss = np.array([pd.Series(ss[td == n]).mode().iat[0] for n in names])
f0, psi0 = fit(g, Y, mask, K0); R0, share0 = principal(f0.lam(), w); L0 = f0.lam() @ R0; Ld0 = ds_load(L0, w, td, names)
log("reference fit", [round(float(x), 3) for x in share0])
out = {"as_of": "2026-11-11", "K": K0, "datasets": names, "sources_per_dataset": [int(x) for x in dsrc], "task_type": d_tt.tolist(), "sensor": d_ss.tolist(), "loading": [[r4(x) for x in r] for r in Ld0]}

# ---- 2 varimax
Rv = varimax(Ld0); Lv = Ld0 @ Rv
order = np.argsort(-(Lv ** 2).sum(0)); Lv = Lv[:, order]; sg = np.sign(Lv.mean(0)); sg[sg == 0] = 1; Lv = Lv * sg
def eta2(x, lab):
    keep = lab != ""; x, lab = x[keep], lab[keep]; tot = ((x - x.mean()) ** 2).sum()
    return float(1 - sum(((x[lab == l] - x[lab == l].mean()) ** 2).sum() for l in set(lab)) / tot)
out["varimax"] = {"loading": [[r4(x) for x in r] for r in Lv], "share": [r4(x) for x in (Lv ** 2).sum(0) / (Lv ** 2).sum()],
                  "axes": [{"top": [(names[i], r4(Lv[i, k])) for i in np.argsort(-Lv[:, k])[:8]], "bottom": [(names[i], r4(Lv[i, k])) for i in np.argsort(Lv[:, k])[:8]],
                            "eta2_sensor": r4(eta2(Lv[:, k], d_ss)), "eta2_task_type": r4(eta2(Lv[:, k], d_tt)),
                            "mean_by_sensor": {s: r4(Lv[d_ss == s, k].mean()) for s in sorted(set(d_ss)) if s}, "mean_by_task_type": {s: r4(Lv[d_tt == s, k].mean()) for s in sorted(set(d_tt))}} for k in range(K0)],
                  "hoyer_sparsity_principal": r4(np.mean([(np.sqrt(K0) - np.abs(r).sum() / np.linalg.norm(r)) / (np.sqrt(K0) - 1) for r in Ld0])),
                  "hoyer_sparsity_varimax": r4(np.mean([(np.sqrt(K0) - np.abs(r).sum() / np.linalg.norm(r)) / (np.sqrt(K0) - 1) for r in Lv]))}
log("varimax", out["varimax"]["share"], [(a["eta2_sensor"], a["eta2_task_type"]) for a in out["varimax"]["axes"]])

# ---- 3 uniqueness
P = f0.predict(); Es = np.where(mask, Y - P, np.nan) / np.sqrt(psi0)[None, :]
comm = db.communality_by_dataset(Y, mask, f0, td); uniq = []
for i, n in enumerate(names):
    idx = np.where(td == n)[0]; rr_x, rr_w = [], []
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            o = mask[:, idx[a]] & mask[:, idx[b]]
            if o.sum() >= 6:
                x, y = Es[o, idx[a]], Es[o, idx[b]]
                if x.std() > 0 and y.std() > 0: (rr_x if tp[idx[a]] != tp[idx[b]] else rr_w).append(float(np.corrcoef(x, y)[0, 1]))
    uniq.append({"dataset": n, "sources": int(dsrc[i]), "unexplained_share": r4(1 - comm[n]) if np.isfinite(comm[n]) else None,
                 "residual_r_across_sources": r4(np.mean(rr_x)) if rr_x else None, "pairs_across_sources": len(rr_x),
                 "residual_r_within_source": r4(np.mean(rr_w)) if rr_w else None, "pairs_within_source": len(rr_w)})
out["uniqueness"] = uniq

# ---- 4 pretraining group x dataset group (no latent axes)
attrs = json.loads((ROOT / "data" / "model_attributes.json").read_text())["models"]; pg = np.array([attrs.get(m, {}).get("pretraining") or "" for m in models])
PCT = np.full(Y.shape, np.nan)
for t in range(T):
    o = np.where(mask[:, t])[0]
    if len(o) >= 4: PCT[o, t] = (pd.Series(Y[o, t]).rank().values - 1) / (len(o) - 1)
def group_table(lab_t, levels):
    rows = []
    for G_ in sorted(set(pg) - {""}):
        for lv in levels:
            cols = np.where(lab_t == lv)[0]; v = []; srcs = []
            for t in cols:
                x = PCT[pg == G_, t]; x = x[np.isfinite(x)]
                oth = PCT[(pg != G_) & (pg != ""), t]; oth = oth[np.isfinite(oth)]
                if len(x) and len(oth): v.append(x.mean()); srcs.append(tp[t])
            if len(v) >= 5:
                v, srcs = np.array(v), np.array(srcs); rng = np.random.default_rng(0); u = pd.unique(srcs)
                bs = [np.concatenate([v[srcs == s] for s in rng.choice(u, len(u))]).mean() for _ in range(1000)]
                rows.append({"pretraining": G_, "group": lv, "mean_rank_percentile": r4(v.mean()), "ci90": [r4(np.percentile(bs, 5)), r4(np.percentile(bs, 95))], "tasks": int(len(v)), "sources": int(len(u))})
    return rows
dim2_t = L0[:, 1]; q = np.quantile(dim2_t, [1 / 3, 2 / 3]); band = np.where(dim2_t <= q[0], "low on dimension 2", np.where(dim2_t >= q[1], "high on dimension 2", "middle"))
out["pretraining_by_group"] = {"by_sensor": group_table(ss, [s for s in ("multispectral", "SAR + optical", "SAR", "high-resolution optical") ]),
                               "by_task_type": group_table(tt, ["classification", "segmentation", "regression", "change detection"]),
                               "by_dimension2_band": group_table(band, ["low on dimension 2", "middle", "high on dimension 2"]),
                               "geofms_per_group": {G_: int((pg == G_).sum()) for G_ in sorted(set(pg) - {""})}}
log("pretraining x sensor", [(r["pretraining"][:10], r["group"][:10], r["mean_rank_percentile"]) for r in out["pretraining_by_group"]["by_sensor"]])

# ---- 8 K = 4..6: what the extra dimensions are made of
extra = {}
for K in (3, 4, 5, 6):
    fK, _ = fit(g, Y, mask, K) if K != K0 else (f0, None); RK, shK = principal(fK.lam(), w); LK = fK.lam() @ RK; LdK = ds_load(LK, w, td, names); dims = []
    for k in range(K):
        e = w * LK[:, k] ** 2; by_src = pd.Series(e).groupby(tp).sum().sort_values(ascending=False); by_ds = pd.Series(e).groupby(td).sum().sort_values(ascending=False)
        dims.append({"dimension": k + 1, "share_of_loading_variance": r4(shK[k]), "top_source": by_src.index[0], "top_source_share": r4(by_src.iloc[0] / e.sum()), "top3_sources_share": r4(by_src.iloc[:3].sum() / e.sum()),
                     "top_dataset": by_ds.index[0], "top_dataset_share": r4(by_ds.iloc[0] / e.sum()), "eta2_sensor": r4(eta2(LdK[:, k], d_ss)), "eta2_task_type": r4(eta2(LdK[:, k], d_tt)),
                     "top": [names[i] for i in np.argsort(-LdK[:, k])[:5]], "bottom": [names[i] for i in np.argsort(LdK[:, k])[:5]]})
    extra[K] = dims; log("K", K, [(x["dimension"], x["share_of_loading_variance"], x["top_source"], x["top_source_share"], x["top_dataset_share"]) for x in dims])
src_w = pd.Series(w).groupby(tp).sum(); out["extra_dimensions"] = {"by_K": extra, "largest_source_share_of_cells": r4(src_w.max() / src_w.sum()), "largest_source": src_w.idxmax()}

# ---- 6 leave one source out
loso = []
for s in pd.unique(tp):
    keep = tp != s; m2 = mask[:, keep]; rows = m2.any(1)
    fs, _ = fit(g, Y[rows][:, keep], m2[rows], K0, restarts=2, G={k: v[keep] for k, v in groups_of(g).items()}, fam=g["FAM"][keep])
    Ls = ds_load(fs.lam(), m2[rows].sum(0).astype(float), td[keep], names); Rs = procrustes(Ls, Ld0); La = Ls @ Rs
    sel = multi & np.isfinite(La).all(1)
    loso.append({"source": s, "tasks": int((~keep).sum()), "share_of_cells": r4(w[~keep].sum() / w.sum()), "similarity_map_r_multi_source": r4(sim_corr(La, Ld0, sel)),
                 "dimension_r": [r4(np.corrcoef(La[sel, k], Ld0[sel, k])[0, 1]) for k in range(K0)]})
    log("loso", loso[-1])
out["leave_one_source_out"] = sorted(loso, key=lambda x: x["similarity_map_r_multi_source"])

# ---- 1 + 7 bootstrap clouds and slices
rng = np.random.default_rng(0); clouds = {"geofms": [], "tasks": []}
for b in range(BOOT):
    rows = rng.integers(0, M, M); fb, _ = fit(g, Y[rows], mask[rows], K0, seed=100 + b, restarts=2); Lb = ds_load(fb.lam(), mask[rows].sum(0).astype(float), td, names); clouds["geofms"].append(Lb @ procrustes(Lb, Ld0))
    cols = rng.integers(0, T, T); fb, _ = fit(g, Y[:, cols], mask[:, cols], K0, seed=200 + b, restarts=2, G={k: v[cols] for k, v in groups_of(g).items()}, fam=g["FAM"][cols])
    Lb = ds_load(fb.lam(), mask[:, cols].sum(0).astype(float), td[cols], names); clouds["tasks"].append(Lb @ procrustes(Lb, Ld0))
    if b % 10 == 9: log("bootstrap", b + 1)
allc = np.array(clouds["geofms"] + clouds["tasks"])                                     # (2B, D, K)
sd = np.nanstd(allc, axis=0); cov12 = [np.cov(allc[np.isfinite(allc[:, i, 0]), i, :2].T).tolist() if np.isfinite(allc[:, i, 0]).sum() > 3 else None for i in range(nd)]
out["position_uncertainty"] = {"B_each": BOOT, "sd": [[r4(x) for x in r] for r in sd], "cov_dim12": [[[r4(x) for x in r] for r in c] if c else None for c in cov12],
                               "sign_stable_dim2": [r4(max(np.nanmean(allc[:, i, 1] > 0), np.nanmean(allc[:, i, 1] < 0))) for i in range(nd)],
                               "median_sd_multi_source": [r4(x) for x in np.nanmedian(sd[multi], axis=0)], "median_sd_single_source": [r4(x) for x in np.nanmedian(sd[~multi], axis=0)]}
def slice_ci(lab, levels):
    rows = []
    for lv in levels:
        sel = lab == lv
        if sel.sum() < 3: continue
        pt = Ld0[sel].mean(0); bs = np.array([np.nanmean(c[sel], axis=0) for c in allc])
        rows.append({"group": lv, "datasets": int(sel.sum()), "mean": [r4(x) for x in pt], "ci90": [[r4(np.nanpercentile(bs[:, k], 5)), r4(np.nanpercentile(bs[:, k], 95))] for k in range(K0)]})
    return rows
out["slices"] = {"by_task_type": slice_ci(d_tt, ["classification", "segmentation", "regression", "change detection", "detection"]),
                 "by_sensor": slice_ci(d_ss, ["multispectral", "SAR + optical", "SAR", "high-resolution optical", "other"])}
log("slices", [(r["group"], r["mean"][1], r["ci90"][1]) for r in out["slices"]["by_sensor"]])
OUT.write_text(json.dumps(out, indent=1)); log("wrote (before frozen)", OUT)

# ---- 5 frozen-only
gf = matrix(("--protocol", "frozen")); Yf, mf, tpf, tdf = gf["Y"], gf["mask"], gf["tp"], gf["td"]; wf = mf.sum(0).astype(float)
cvf = {}
for K in (1, 2, 3, 4, 5):
    rs = [db.heldout_cell_cv(Yf, mf, K, groups_of(gf), folds=5, seed=s, **kw(gf, restarts=2, n_iter=200)) for s in (0, 1, 2)]
    cvf[K] = {"pair_acc": r4(np.mean([r["pair_acc"] for r in rs])), "pair_acc_se": r4(np.mean([r["pair_acc_se"] for r in rs]) / np.sqrt(3)), "rmse": r4(np.mean([r["rmse"] for r in rs])), "n_heldout": rs[0]["n_heldout"]}
    log("frozen cv", K, cvf[K])
ff, _ = fit(gf, Yf, mf, K0); Lf = ds_load(ff.lam(), wf, tdf, names); Lfa = Lf @ procrustes(Lf, Ld0); sel = multi & np.isfinite(Lfa).all(1)
out["frozen_only"] = {"matrix": {"geofms": int(Yf.shape[0]), "tasks": int(Yf.shape[1]), "datasets": int(len(set(tdf))), "fill": r4(mf.mean())}, "cv_heldout_cells": cvf,
                      "similarity_map_r_with_all_protocols_multi_source": r4(sim_corr(Lfa, Ld0, sel)), "datasets_compared": int(sel.sum()),
                      "dimension_r": [r4(np.corrcoef(Lfa[sel, k], Ld0[sel, k])[0, 1]) for k in range(K0)], "loading": [[r4(x) for x in r] for r in Lfa]}
log("frozen", {k: v for k, v in out["frozen_only"].items() if k not in ("loading", "cv_heldout_cells")})
OUT.write_text(json.dumps(out, indent=1)); log("wrote", OUT)
