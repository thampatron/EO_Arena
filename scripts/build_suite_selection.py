#!/usr/bin/env python3
"""Which N datasets make the most complete benchmark suite, and how much of the full suite does any given set capture?

  python3 -I scripts/build_suite_selection.py <workbook_dir> [--B 60] [--out data/suite_selection.json]

Built on the note's Eq. 8. With dataset loadings L (rows in residual units, unit capability covariance), a suite A leaves
the posterior covariance (I + L_A' L_A)^-1 on a GeoFM's capabilities. Two readings of the same matrix:
  coverage(A)  = V(A) / V(all eligible),  V = log det(I + L_A' L_A)         (note Eq. 8, relative to running everything)
  resolved_k(A) = 1 - [(I + L_A' L_A)^-1]_kk                                 (share of capability k pinned down, 0..1)
Selection is made ROBUST to the uncertainty of the loadings: the chosen set maximises the mean coverage over B refits on
subsampled GeoFMs (greedy, then pairwise swaps; exhaustive for N <= 3), and every number is reported with its spread
over those refits. Eligible = datasets seen in >= 2 sources. Dataset-level output only.
"""
import contextlib, io, itertools, json, sys, time
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dataset_benchmarking as db

A = sys.argv; SRC = A[1]
OUT = Path(A[A.index("--out") + 1]) if "--out" in A else ROOT / "data" / "suite_selection.json"
B = int(A[A.index("--B") + 1]) if "--B" in A else 60
SUB = None if "--bootstrap" in A else float(A[A.index("--subsample") + 1]) if "--subsample" in A else 0.8
# Refits use 80% of the GeoFMs drawn WITHOUT replacement by default. A bootstrap with replacement duplicates GeoFMs, which
# shrinks the residual variance of thinly supported datasets and inflates their loadings (seen 2026-11-11: refit strength
# about twice the full-fit strength for datasets with 3-7 comparisons), biasing the selection toward them.
K0 = int(A[A.index("--K") + 1]) if "--K" in A else 3; RIDGE = 3.0; NMAX = 10; t0 = time.time()
def log(*a): print(f"[{time.time() - t0:6.0f}s]", *a, flush=True)
r4 = lambda x: None if x is None or not np.isfinite(x) else round(float(x), 4)

src = (ROOT / "scripts" / "build_dataset_analysis.py").read_text()
src = src[:src.index("# ============================================================================= 2. model-free tests")]
g = {"__file__": str(ROOT / "scripts" / "build_dataset_analysis.py"), "__name__": "matrix"}
old = sys.argv; sys.argv = ["x", SRC, "--offset", "none", "--skip-sim"] + (["--merge-families"] if "--merge-families" in A else [])   # one unit per GeoFM family
with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, "build_prefix", "exec"), g)
sys.argv = old
Y, mask, tp, td, TI = g["Y"], g["mask"], g["tp"], g["td"], g["TI"]; M, T = Y.shape
G = {k: g["G_ALL"][k] for k in ("dataset", "protocol", "sensor")}
def fit(Yx, mx, seed=0, restarts=3):
    return db.fit_heteroskedastic(Yx, mx, K0, G, seed=seed, ridge_u=RIDGE, ridge_theta=RIDGE, ridge_g={k: RIDGE for k in G}, n_restarts=restarts, n_iter=300, tol=1e-6, prior_group=g["FAM"])[0]
all_names = sorted(set(td)); dsrc = pd.Series(tp).groupby(td).nunique().reindex(all_names).values; dcmp = pd.Series(td).value_counts().reindex(all_names).values
names = [n for n, s in zip(all_names, dsrc) if s >= 2]; D = len(names)
def ds_load(f, mx):
    L = f.lam(); w = mx.sum(0).astype(float); return np.array([np.average(L[td == n], axis=0, weights=np.maximum(w[td == n], 1e-9)) for n in names])
def principal_rot(L, w):
    _, _, Vt = np.linalg.svd(L * np.sqrt(w)[:, None], full_matrices=False); return Vt.T
f0 = fit(Y, mask); w = mask.sum(0).astype(float); R0 = principal_rot(f0.lam(), w); L0 = ds_load(f0, mask) @ R0
sg = np.sign(L0.mean(0)); sg[sg == 0] = 1; L0 = L0 * sg
def procrustes(Ax, Bx): U, _, Vt = np.linalg.svd(Ax.T @ Bx); return U @ Vt
rng = np.random.default_rng(0); LB = []
for b in range(B):
    rows = rng.integers(0, M, M) if SUB is None else np.sort(rng.choice(M, int(round(SUB * M)), replace=False)); fb = fit(Y[rows], mask[rows], seed=100 + b, restarts=2); Lb = ds_load(fb, mask[rows]); LB.append(Lb @ procrustes(Lb, L0))
    if b % 10 == 9: log("refit", b + 1)
LB = np.array(LB)                                          # (B, D, K)

I = np.eye(K0)
def V(L, idx): return np.linalg.slogdet(I + L[idx].T @ L[idx])[1] if len(idx) else 0.0
def post(L, idx): return np.linalg.inv(I + L[idx].T @ L[idx])
VALL = np.array([V(LB[b], list(range(D))) for b in range(B)]); V0ALL = V(L0, list(range(D)))
def cov_b(idx): return np.array([V(LB[b], idx) for b in range(B)]) / VALL
def score(idx): return float(cov_b(idx).mean())
def describe(idx):
    c = cov_b(idx); res = np.array([1 - np.diag(post(LB[b], idx)) for b in range(B)])
    return {"datasets": [names[i] for i in idx], "coverage_mean": r4(c.mean()), "coverage_ci90": [r4(np.percentile(c, 5)), r4(np.percentile(c, 95))], "coverage_point_fit": r4(V(L0, idx) / V0ALL),
            "resolved_by_dimension_mean": [r4(x) for x in res.mean(0)], "resolved_by_dimension_ci90": [[r4(np.percentile(res[:, k], 5)), r4(np.percentile(res[:, k], 95))] for k in range(K0)]}

# ---- robust best set for each N: greedy on mean coverage, then swaps; exhaustive for N <= 3
best = {}; cur = []
for N in range(1, NMAX + 1):
    cur = cur + [max((i for i in range(D) if i not in cur), key=lambda i: score(cur + [i]))]
    s = list(cur); improved = True
    while improved:
        improved = False; base = score(s)
        for a in range(len(s)):
            for j in range(D):
                if j in s: continue
                t = s[:a] + [j] + s[a + 1:]; sc = score(t)
                if sc > base + 1e-6: s, base, improved = t, sc, True
    if N <= 3:
        ex = max(itertools.combinations(range(D), N), key=lambda c: score(list(c)))
        if score(list(ex)) > score(s) + 1e-6: s = list(ex)
    best[N] = describe(sorted(s, key=lambda i: cur.index(i) if i in cur else 99)); best[N]["nested_in_next"] = None
    rnd = np.array([cov_b(list(rng.choice(D, N, replace=False))).mean() for _ in range(300)])
    used = list(np.argsort(-np.array([dcmp[all_names.index(n)] for n in names]))[:N])
    best[N]["random_set_mean"] = r4(rnd.mean()); best[N]["random_set_p95"] = r4(np.percentile(rnd, 95)); best[N]["most_used_set"] = describe(used)
    log(N, best[N]["datasets"], best[N]["coverage_mean"], best[N]["coverage_ci90"], "random", best[N]["random_set_mean"], "most used", best[N]["most_used_set"]["coverage_mean"], "resolved", best[N]["resolved_by_dimension_mean"])
    cur = s
for N in range(1, NMAX): best[N]["nested_in_next"] = bool(set(best[N]["datasets"]) <= set(best[N + 1]["datasets"]))

# ---- how often is each dataset picked when the selection is redone on each refit alone?
def greedy(L, N):
    s = []
    for _ in range(N): s.append(max((i for i in range(D) if i not in s), key=lambda i: V(L, s + [i])))
    return s
picks = np.array([greedy(LB[b], NMAX) for b in range(B)]); p0 = greedy(L0, NMAX)
freq = {names[i]: {"top3": r4(np.mean([i in p[:3] for p in picks])), "top5": r4(np.mean([i in p[:5] for p in picks])), "top10": r4(np.mean([i in p for p in picks])),
                   "rank_in_point_fit": (p0.index(i) + 1 if i in p0 else None), "sources": int(dsrc[all_names.index(names[i])]), "comparisons": int(dcmp[all_names.index(names[i])]),
                   "strength_mean": r4(np.linalg.norm(LB[:, i, :], axis=1).mean()), "strength_sd": r4(np.linalg.norm(LB[:, i, :], axis=1).std())} for i in range(D)}
single = {names[i]: r4(score([i])) for i in range(D)}
loo = {names[i]: r4(1 - score([j for j in range(D) if j != i])) for i in range(D)}        # what the full suite loses without it

out = {"as_of": "2026-11-11", "eligible_datasets": names, "B": B, "K": K0, "resampling": "bootstrap of GeoFMs with replacement" if SUB is None else f"{SUB:.0%} of GeoFMs without replacement",
       "definitions": {"coverage": "V(A) / V(all eligible datasets), V = log det(I + L_A' L_A) (note Eq. 8); 1 = as informative about the shared capabilities as running all eligible datasets",
                       "resolved": "1 - posterior variance of each capability given the suite; 0 = nothing learnt, 1 = pinned down",
                       "robust": "sets maximise mean coverage over B refits on subsampled GeoFMs; intervals are the 5th-95th percentile over refits"},
       "best_by_N": best, "selection_frequency": freq, "coverage_alone": single, "loss_if_removed": loo,
       "full_suite_resolved_mean": [r4(x) for x in np.mean([1 - np.diag(post(LB[b], list(range(D)))) for b in range(B)], axis=0)],
       "loadings_reference": [[r4(x) for x in r] for r in L0], "loadings_refits": LB.round(3).tolist()}
OUT.write_text(json.dumps(out)); log("wrote", OUT)
