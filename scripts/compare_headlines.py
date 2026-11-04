#!/usr/bin/env python3
"""Compare the headline numbers of two data/dataset_analysis.json files (base vs. proposed change).

Prints a markdown table for the PR description. Exit status 0 = no headline changed beyond tolerance, 3 = at least one
did (the PR must carry the `changes-results` label and say why), 1 = error.

Usage: python3 scripts/compare_headlines.py <base.json> <head.json>
"""
import json, sys

TOL_RHO = 0.01

def headlines(d):
    h = {}
    sc, o, K = d.get("scope", {}), d.get("overlap", {}), d.get("K", {})
    h["rows kept"] = sc.get("rows_kept")
    for k in ("models", "tasks", "datasets", "papers", "datasets_in_2plus_papers"): h[f"evidence: {k}"] = o.get(k)
    h["K chosen"] = K.get("chosen")
    for k, v in (K.get("lopo_by_K") or {}).items():
        h[f"LOPO rho, K={k}"] = v.get("rho_struct")
    for name, v in (d.get("lopo_gain_vs_one_ordering") or {}).items():
        h[f"gain {name}: mean"] = v.get("mean")
        h[f"gain {name}: CI excludes 0"] = None if not v.get("ci90") else (v["ci90"][0] > 0 or v["ci90"][1] < 0)
    for lab, v in (d.get("metadata_association_multi_paper") or {}).items():
        for kind, a in (v.items() if isinstance(v, dict) and "r2" not in v else [("full_loading", v)]):
            p = a.get("p_bonferroni_4_labels", a.get("p_value"))
            h[f"assoc {lab} ({kind}) significant"] = None if p is None else p < 0.05
    h["geometry recoverable"] = d.get("geometry_recoverable")
    re_ = d.get("replication_evidence") or {}
    h["replication groups (>=5 shared GeoFMs)"] = re_.get("with_5plus_shared_geofms")
    h["reproducibility groups estimable"] = len(d.get("reproducibility") or [])
    return h

def changed(a, b, key):
    if a is None or b is None: return a != b
    if isinstance(a, bool) or isinstance(b, bool) or isinstance(a, int) and isinstance(b, int): return a != b
    tol = TOL_RHO if ("rho" in key or "gain" in key) else 1e-9
    return abs(float(a) - float(b)) > tol

try:
    A, B = (headlines(json.load(open(p))) for p in sys.argv[1:3])
except Exception as e:
    print(f"error: {e}"); sys.exit(1)
rows, n = [], 0
for k in sorted(set(A) | set(B), key=lambda k: (list(A) + [x for x in B if x not in A]).index(k)):
    c = changed(A.get(k), B.get(k), k); n += c
    fmt = lambda v: "–" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))
    rows.append(f"| {k} | {fmt(A.get(k))} | {fmt(B.get(k))} | {'**changed**' if c else ''} |")
print("| headline | base | this PR | |\n|---|---|---|---|\n" + "\n".join(rows))
print(f"\n{n} headline(s) changed (rho tolerance {TOL_RHO}).")
sys.exit(3 if n else 0)
