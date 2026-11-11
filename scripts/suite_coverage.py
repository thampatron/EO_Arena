#!/usr/bin/env python3
"""How much of the full benchmark suite does a given set of datasets capture?  (no workbook needed)

  python3 -I scripts/suite_coverage.py "PASTIS / PASTIS-R" "EuroSAT" "fMoW"
  python3 -I scripts/suite_coverage.py --list

Reads data/suite_selection.json (dataset loadings from the note's regression, refit on subsampled GeoFMs).
coverage = V(A) / V(all eligible), V = log det(I + L_A' L_A)  (note Eq. 8); resolved_k = share of capability k pinned down.
"""
import json, sys
from pathlib import Path
import numpy as np
d = json.loads((Path(__file__).resolve().parent.parent / "data" / "suite_selection.json").read_text())
names = d["eligible_datasets"]; LB = np.array(d["loadings_refits"]); B, D, K = LB.shape; I = np.eye(K)
if "--list" in sys.argv or len(sys.argv) < 2: print("\n".join(names)); sys.exit(0)
low = {n.lower(): i for i, n in enumerate(names)}; idx = []
for a in sys.argv[1:]:
    m = [i for n, i in low.items() if a.lower() == n] or [i for n, i in low.items() if a.lower() in n]
    if len(m) != 1: sys.exit(f"'{a}' matches {len(m)} eligible datasets; use --list")
    idx.append(m[0])
idx = sorted(set(idx)); V = lambda L, s: np.linalg.slogdet(I + L[s].T @ L[s])[1]
cov = np.array([V(LB[b], idx) / V(LB[b], list(range(D))) for b in range(B)]); res = np.array([1 - np.diag(np.linalg.inv(I + LB[b][idx].T @ LB[b][idx])) for b in range(B)])
ref = d["best_by_N"].get(str(len(idx)))
print(f"{len(idx)} datasets: " + ", ".join(names[i] for i in idx))
print(f"coverage of the {D}-dataset suite: {100*cov.mean():.0f}%  (90% interval {100*np.percentile(cov,5):.0f}-{100*np.percentile(cov,95):.0f}%)")
print("resolved share by capability: " + ", ".join(f"{k+1}: {100*res[:,k].mean():.0f}%" for k in range(K)) + "   (full suite: " + ", ".join(f"{100*x:.0f}%" for x in d["full_suite_resolved_mean"]) + ")")
if ref: print(f"for comparison at N = {len(idx)}: best set {100*ref['coverage_mean']:.0f}%, random set {100*ref['random_set_mean']:.0f}%")
