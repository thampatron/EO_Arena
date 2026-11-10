#!/usr/bin/env python3
"""Extensions to the dataset analysis that do not rely on the pooled latent fit (2026-11-10).

  python3 -I scripts/build_dataset_extensions.py <workbook_dir> [--out data/dataset_extensions.json]

E1  within-benchmark: inside one source the same GeoFMs are run with one codebase, so dataset-to-dataset rank
    agreement is free of the "who ran it" confound. (a) dataset identity within a source (same dataset under another
    protocol / fraction vs another dataset under the same protocol); (b) dataset x dataset agreement per source;
    (c) does that agreement structure replicate in a second source (Mantel test, raw and with dataset main effects
    removed)?
E2  the model-free tau contrasts on restricted matrices: GeoFMs in >= N sources, frozen / fine-tuned only, family-merged.
E3  model attributes (SAR in pretraining, size tier): what a comparison rewards, and whether that is a dataset property.
E6  design: cells needed to complete a panel of the best-connected GeoFMs on the datasets seen in >= 2 sources.

Outputs summary statistics only: no individual score, no model ranking.
"""
import contextlib, io, json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import kendalltau, binomtest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dataset_benchmarking as db

A = sys.argv; SRC = A[1]
OUT = Path(A[A.index("--out") + 1]) if "--out" in A else ROOT / "data" / "dataset_extensions.json"
SEED = 20261110; MIN_SHARED = 6; t0 = time.time()
def log(*a): print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)
r4 = lambda x: None if x is None or not np.isfinite(x) else round(float(x), 4)


def matrix(flags=()):
    """The model x comparison matrix exactly as build_dataset_analysis.py builds it (its section 1), under extra flags."""
    src = (ROOT / "scripts" / "build_dataset_analysis.py").read_text()
    src = src[:src.index("# ============================================================================= 2. model-free tests")]
    g = {"__file__": str(ROOT / "scripts" / "build_dataset_analysis.py"), "__name__": "matrix"}
    old = sys.argv; sys.argv = ["x", SRC, "--offset", "none", "--skip-sim", *flags]
    try:
        with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, "build_prefix", "exec"), g)
    finally: sys.argv = old
    return g


def ktau(Y, mask, i, j, min_shared=MIN_SHARED):
    sh = mask[:, i] & mask[:, j]
    if sh.sum() < min_shared: return np.nan, int(sh.sum())
    a, b = Y[sh, i], Y[sh, j]
    if np.ptp(a) == 0 or np.ptp(b) == 0: return np.nan, int(sh.sum())
    return float(kendalltau(a, b).statistic), int(sh.sum())


def boot_mean(d, groups, B=2000, seed=SEED):
    """Mean of d with a cluster bootstrap over groups (sources)."""
    d = np.asarray(d, float); groups = np.asarray(groups); ok = np.isfinite(d); d, groups = d[ok], groups[ok]
    if not len(d): return {"mean": None, "ci90": [None, None], "n": 0, "n_sources": 0}
    parts = [d[groups == g_] for g_ in pd.unique(groups)]; rng = np.random.default_rng(seed)
    bs = [np.concatenate([parts[i] for i in rng.integers(0, len(parts), len(parts))]).mean() for _ in range(B)]
    return {"mean": r4(d.mean()), "ci90": [r4(np.percentile(bs, 5)), r4(np.percentile(bs, 95))], "n": int(len(d)), "n_sources": len(parts)}


# ============================================================================= E1 within-benchmark
def within_source(Y, mask, tp, td, TI):
    setting = (TI.evaluation_protocol.astype(str) + "|" + TI.train_fraction_norm.astype(str)).values
    pairs = []                                            # every within-source comparison pair with >= MIN_SHARED GeoFMs
    for s in pd.unique(tp):
        idx = np.where(tp == s)[0]
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                i, j = idx[a], idx[b]; t_, n_ = ktau(Y, mask, i, j)
                if np.isfinite(t_): pairs.append((s, td[i], td[j], setting[i] == setting[j], t_, n_))
    P = pd.DataFrame(pairs, columns=["source", "da", "db", "same_setting", "tau", "n"])
    P["same_dataset"] = P.da == P.db
    return P


def identity_within(P):
    """Same dataset under another setting vs another dataset under the same setting, inside one source."""
    rows = []
    for s, g_ in P.groupby("source"):
        a = g_[g_.same_dataset & ~g_.same_setting].tau; b = g_[~g_.same_dataset & g_.same_setting].tau
        if len(a) >= 3 and len(b) >= 3: rows.append({"source": s, "same_dataset_other_setting": r4(a.mean()), "n_same": int(len(a)),
                                                     "other_dataset_same_setting": r4(b.mean()), "n_other": int(len(b)), "contrast": r4(a.mean() - b.mean())})
    d = np.array([x["contrast"] for x in rows]); pos = int((d > 0).sum())
    rng = np.random.default_rng(SEED); bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)] if len(d) else [np.nan]
    return {"per_source": rows, "sources": len(rows), "positive": pos, "mean_contrast": r4(d.mean()) if len(d) else None,
            "ci90_over_sources": [r4(np.percentile(bs, 5)), r4(np.percentile(bs, 95))],
            "sign_test_p_one_sided": r4(binomtest(pos, len(d), 0.5, alternative="greater").pvalue) if len(d) else None,
            "mean_same_dataset_other_setting": r4(np.mean([x["same_dataset_other_setting"] for x in rows])) if rows else None,
            "mean_other_dataset_same_setting": r4(np.mean([x["other_dataset_same_setting"] for x in rows])) if rows else None}


def dataset_matrices(P):
    """Per source: dataset x dataset mean tau (same-setting comparison pairs preferred, any pair otherwise)."""
    out = {}
    for s, g_ in P[~P.same_dataset].groupby("source"):
        g_ = g_.assign(a=np.minimum(g_.da, g_.db), b=np.maximum(g_.da, g_.db))
        m_same = g_[g_.same_setting].groupby(["a", "b"]).tau.mean(); m_any = g_.groupby(["a", "b"]).tau.mean()
        m = m_same.combine_first(m_any); n = g_.groupby(["a", "b"]).n.median()
        names = sorted(set(g_.a) | set(g_.b))
        if len(names) < 3: continue
        S = pd.DataFrame(np.nan, index=names, columns=names)
        for (a, b), v in m.items(): S.loc[a, b] = S.loc[b, a] = v
        out[s] = (S, float(n.median()))
    return out


def eig_share(S):
    X = S.dropna(axis=0, thresh=len(S) - 1).copy(); X = X.loc[X.index, X.index]
    if X.isna().values[~np.eye(len(X), dtype=bool)].any() or len(X) < 4: return None, len(X)
    M = X.values.copy(); np.fill_diagonal(M, 1.0); w = np.linalg.eigvalsh(M)[::-1]
    return float(w[0] / len(w)), len(X)


def additive_resid(M):
    """Residual of tau_ab after dataset main effects (tau_ab = m + r_a + r_b), least squares on the observed pairs."""
    n = len(M); iu = [(a, b) for a in range(n) for b in range(a + 1, n) if np.isfinite(M[a, b])]
    if len(iu) <= n: return None
    X = np.zeros((len(iu), n + 1)); y = np.array([M[a, b] for a, b in iu]); X[:, 0] = 1
    for k, (a, b) in enumerate(iu): X[k, a + 1] = X[k, b + 1] = 1
    res = y - X @ np.linalg.lstsq(X, y, rcond=None)[0]; R = np.full((n, n), np.nan)
    for k, (a, b) in enumerate(iu): R[a, b] = R[b, a] = res[k]
    return R


def replication(mats, n_perm=5000):
    """Does the dataset x dataset agreement structure of one source reappear in another? Mantel: permute dataset labels in
    the second source. 'raw' centres each source on its own mean; 'residual' also removes dataset main effects (a noisy
    dataset agrees less with everything: that is reliability, not a second dimension)."""
    rng = np.random.default_rng(SEED); srcs = sorted(mats); per = []; stat = {"raw": [], "residual": []}
    def corr_parts(Ma, Mb, kind):
        if kind == "residual":
            Ma, Mb = additive_resid(Ma), additive_resid(Mb)
            if Ma is None or Mb is None: return None
        iu = np.triu_indices(len(Ma), 1); x, y = Ma[iu], Mb[iu]; ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() < 3: return None
        x, y = x[ok] - x[ok].mean(), y[ok] - y[ok].mean()
        return float((x * y).sum()), float((x * x).sum()), float((y * y).sum()), int(ok.sum())
    blocks = []
    for i in range(len(srcs)):
        for j in range(i + 1, len(srcs)):
            Sa, Sb = mats[srcs[i]][0], mats[srcs[j]][0]; sh = sorted(set(Sa.index) & set(Sb.index))
            if len(sh) < 3: continue
            blocks.append((srcs[i], srcs[j], sh, Sa.loc[sh, sh].values, Sb.loc[sh, sh].values))
    res = {}
    for kind in ("raw", "residual"):
        obs = [(a, b, sh, corr_parts(Ma, Mb, kind)) for a, b, sh, Ma, Mb in blocks]
        use = [k for k, o in enumerate(obs) if o[3] is not None and o[3][1] > 0 and o[3][2] > 0]
        if not use: res[kind] = {"source_pairs": 0}; continue
        def pooled(parts): return sum(p[0] for p in parts) / np.sqrt(sum(p[1] for p in parts) * sum(p[2] for p in parts))
        r_obs = pooled([obs[k][3] for k in use]); null = []
        for _ in range(n_perm):
            parts = []
            for k in use:
                _, _, sh, Ma, Mb = blocks[k]; p = rng.permutation(len(sh)); c = corr_parts(Ma, Mb[np.ix_(p, p)], kind)
                if c is not None: parts.append(c)
            null.append(pooled(parts) if parts else 0.0)
        per_pair = [{"a": obs[k][0], "b": obs[k][1], "shared_datasets": len(obs[k][2]), "dataset_pairs": obs[k][3][3],
                     "r": r4(obs[k][3][0] / np.sqrt(obs[k][3][1] * obs[k][3][2]))} for k in use]
        rr = np.array([p["r"] for p in per_pair]); bs = [pooled([obs[use[i]][3] for i in rng.integers(0, len(use), len(use))]) for _ in range(2000)]
        res[kind] = {"pooled_r": r4(r_obs), "mantel_p_one_sided": r4((1 + np.sum(np.array(null) >= r_obs)) / (n_perm + 1)),
                     "ci90_over_source_pairs": [r4(np.percentile(bs, 5)), r4(np.percentile(bs, 95))], "source_pairs": len(use),
                     "positive_source_pairs": int((rr > 0).sum()), "dataset_pairs": int(sum(p["dataset_pairs"] for p in per_pair)),
                     "datasets": sorted({d for k in use for d in obs[k][2]}), "per_source_pair": per_pair}
    return res


# ============================================================================= E3 model attributes
def attribute_effects(Y, mask, models, tp, td, TI, attrs):
    out = {}
    sens = TI.sensor.astype(str).str.lower().values; has_sar = np.array(["s1" in s or "sar" in s for s in sens])
    for name in ("sar_pretrained", "size_tier"):
        x = np.array([np.nan if attrs.get(m, {}).get(name) is None else float(attrs[m][name]) for m in models])
        eff = np.full(Y.shape[1], np.nan)
        for t in range(Y.shape[1]):
            ok = mask[:, t] & np.isfinite(x)
            if ok.sum() >= 6 and np.ptp(x[ok]) > 0 and np.ptp(Y[ok, t]) > 0 and min((x[ok] == x[ok].max()).sum(), (x[ok] < x[ok].max()).sum()) >= 2:
                eff[t] = kendalltau(x[ok], Y[ok, t]).statistic
        o = {"comparisons": int(np.isfinite(eff).sum()), "all": boot_mean(eff, tp)}
        o["frozen"] = boot_mean(eff[TI.pf.values == "frozen"], tp[TI.pf.values == "frozen"]); o["fine_tuned"] = boot_mean(eff[TI.pf.values == "fine-tuned"], tp[TI.pf.values == "fine-tuned"])
        if name == "sar_pretrained":
            o["on_sar_input_comparisons"] = boot_mean(eff[has_sar], tp[has_sar]); o["on_optical_only_comparisons"] = boot_mean(eff[~has_sar], tp[~has_sar])
            ok = np.isfinite(eff); grp = pd.unique(tp[ok]); rng = np.random.default_rng(SEED); bs = []
            for _ in range(2000):
                pick = rng.choice(grp, len(grp)); e = np.concatenate([eff[ok & (tp == g_)] for g_ in pick]); h = np.concatenate([has_sar[ok & (tp == g_)] for g_ in pick])
                if h.any() and (~h).any(): bs.append(e[h].mean() - e[~h].mean())
            o["sar_input_minus_optical"] = {"mean": r4(eff[ok & has_sar].mean() - eff[ok & ~has_sar].mean()), "ci90": [r4(np.percentile(bs, 5)), r4(np.percentile(bs, 95))]}
        # is "what the comparison rewards" a dataset property? same dataset in two sources vs different datasets in two sources
        ok = np.where(np.isfinite(eff))[0]; same, diff = [], []
        for a in range(len(ok)):
            for b in range(a + 1, len(ok)):
                i, j = ok[a], ok[b]
                if tp[i] == tp[j]: continue
                (same if td[i] == td[j] else diff).append(abs(eff[i] - eff[j]))
        if same and diff:
            obs = np.mean(diff) - np.mean(same); rng = np.random.default_rng(SEED); null = []
            alld = np.array(same + diff); ns = len(same)
            for _ in range(2000):
                p = rng.permutation(len(alld)); null.append(alld[p[ns:]].mean() - alld[p[:ns]].mean())
            o["dataset_specific"] = {"mean_abs_diff_same_dataset": r4(np.mean(same)), "mean_abs_diff_other_dataset": r4(np.mean(diff)), "contrast": r4(obs),
                                     "same_dataset_pairs": len(same), "p_perm_pairs_one_sided": r4((1 + np.sum(np.array(null) >= obs)) / 2001),
                                     "note": "pair-level permutation; pairs are not independent, so the p-value is optimistic"}
        out[name] = o
    return out


# ============================================================================= E6 design
def panel_completion(mask, models, tp, td, sizes=(8, 12, 16)):
    ns = pd.Series({m: len(set(tp[mask[i]])) for i, m in enumerate(models)}).sort_values(ascending=False, kind="stable")
    dsrc = pd.Series(tp).groupby(td).nunique(); multi = sorted(dsrc[dsrc >= 2].index)
    have = pd.DataFrame({d: mask[:, td == d].any(1) for d in sorted(set(td))}, index=models)
    out = {"datasets_in_2plus_sources": len(multi), "panels": []}
    for k in sizes:
        panel = list(ns.index[:k]); H = have.loc[panel, multi]
        out["panels"].append({"panel_size": k, "min_sources_per_model": int(ns.iloc[k - 1]), "cells": int(H.size), "already_published": int(H.values.sum()),
                              "to_run": int((~H.values).sum()), "share_published": r4(H.values.mean()), "models": sorted(panel),
                              "datasets_complete": int(H.all(0).sum()),
                              "missing_by_dataset": {d: int((~H[d]).sum()) for d in multi if (~H[d]).any()}})
    return out


# ============================================================================= run
g = matrix(); Y, mask, tp, td, TI, models = g["Y"], g["mask"], g["tp"], g["td"], g["TI"], g["models"]
log("matrix", Y.shape)
P = within_source(Y, mask, tp, td, TI); log("within-source comparison pairs", len(P))
ident = identity_within(P); log("within-source identity", {k: v for k, v in ident.items() if k != "per_source"})
mats = dataset_matrices(P)
blocks = []
for s, (S, nmed) in sorted(mats.items()):
    iu = np.triu_indices(len(S), 1); v = S.values[iu]; v = v[np.isfinite(v)]; es, ne = eig_share(S)
    blocks.append({"source": s, "datasets": len(S), "dataset_pairs": int(len(v)), "median_shared_geofms": nmed, "mean_tau": r4(v.mean()),
                   "share_pairs_tau_below_0": r4((v < 0).mean()), "first_eigen_share": r4(es) if es is not None else None, "eigen_datasets": ne,
                   "names": list(S.index), "tau": [[r4(x) for x in row] for row in S.values]})
allv = np.concatenate([np.array([x for row in b["tau"] for x in row if x is not None]) for b in blocks])
log("blocks", [(b["source"], b["datasets"], b["mean_tau"], b["first_eigen_share"]) for b in blocks])
rep = replication(mats); log("replication", {k: {a: b for a, b in v.items() if a not in ("per_source_pair", "datasets")} for k, v in rep.items()})
src_of = P[~P.same_dataset].copy()
within_summary = boot_mean(np.concatenate([np.array(b["tau"], float)[np.triu_indices(b["datasets"], 1)] for b in blocks]),
                           np.concatenate([[b["source"]] * (b["datasets"] * (b["datasets"] - 1) // 2) for b in blocks]))

attrs = json.loads((ROOT / "data" / "model_attributes.json").read_text())["models"]
E3 = attribute_effects(Y, mask, models, tp, td, TI, attrs); log("attributes", {k: (v["comparisons"], v["all"]) for k, v in E3.items()})
E6 = panel_completion(mask, models, tp, td); log("panels", [(p["panel_size"], p["to_run"], p["cells"]) for p in E6["panels"]])

def tau_block(flags, label):
    h = matrix(flags); Yh, mh, tph, tdh, TIh = h["Y"], h["mask"], h["tp"], h["td"], h["TI"]
    Pt = db.tau_pairs(Yh, mh, min_shared=4)
    T = db.tau_contrasts(Pt, tph, tdh, TIh.pf.values, B=1000, seed=SEED); R = db.tau_robustness(Pt, tph, tdh, B=500, seed=SEED)
    o = {"flags": list(flags), "matrix": h["overlap"], "identity": T["all"].get("dataset_identity"), "paper": T["all"].get("paper_specificity"), "cells": T["cells"],
         "source_pairs": R.get("source_pairs_with_same_dataset_pairs"), "positive": R.get("positive_contrasts"), "sign_test_p": R.get("sign_test_p_one_sided"),
         "cross_source_same_dataset_pairs": T["all"].get("cross_source_same_dataset_pairs")}
    log(label, o["matrix"]["models"], o["matrix"]["tasks"], o["matrix"]["density"], o["identity"], o["source_pairs"], o["positive"], o["sign_test_p"]); return o
E2 = {k: tau_block(f, k) for k, f in {"all": (), "models_in_2plus_sources": ("--min-model-sources", "2"), "models_in_3plus_sources": ("--min-model-sources", "3"),
                                      "models_in_4plus_sources": ("--min-model-sources", "4"), "frozen_only": ("--protocol", "frozen"),
                                      "fine_tuned_only": ("--protocol", "fine-tuned"), "families_merged": ("--merge-families",),
                                      "families_merged_3plus_sources": ("--merge-families", "--min-model-sources", "3")}.items()}

out = {"as_of": "2026-11-10", "min_shared_geofms": MIN_SHARED,
       "about": "Analyses that do not use the pooled latent fit. Summary statistics only; no individual score and no model ranking.",
       "within_source": {"identity": ident, "dataset_pair_tau": within_summary, "blocks": blocks, "replication": rep},
       "restricted_tau": E2, "model_attributes": E3, "panel_completion": E6}
OUT.write_text(json.dumps(out, indent=1)); log("wrote", OUT)
