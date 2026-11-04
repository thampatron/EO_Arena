#!/usr/bin/env python3
"""Compare the headline numbers of two data/dataset_analysis.json files (base vs. proposed change).

Prints a markdown table for the PR description. Exit status 0 = no headline changed beyond tolerance, 3 = at least one
did (the PR must carry the `changes-results` label and say why), 1 = error.

Usage: python3 scripts/compare_headlines.py <base.json> <head.json>
"""
import json, sys

TOL_RHO = 0.01

def _ci(h, name, v):
    if not isinstance(v, dict): return
    if v.get("mean", v.get("estimate")) is None: return
    h[f"{name}: estimate"] = v.get("mean", v.get("estimate"))
    ci = v.get("ci90")
    h[f"{name}: CI excludes 0"] = None if not ci else (ci[0] > 0 or ci[1] < 0)

def headlines(d):
    """v2.1 keys (2026-11-04); v1 keys still read where present so an old JSON compares field by field."""
    h = {}
    sc, o, K = d.get("scope", {}), d.get("overlap", {}), d.get("K", {})
    h["rows kept"] = sc.get("rows_kept")
    for k in ("models", "tasks", "datasets", "sources", "papers", "datasets_in_2plus_sources", "datasets_in_2plus_papers"):
        if k in o: h[f"evidence: {k}"] = o.get(k)
    h["offset chosen"] = (d.get("offset") or {}).get("chosen")
    h["K chosen"] = K.get("chosen"); h["K best"] = K.get("best")
    # tau tests (model-free dataset identity and paper specificity)
    ta = (d.get("tau_tests") or {}).get("all") or {}
    for name in ("dataset_identity", "dataset_identity_per_dataset", "paper_specificity"): _ci(h, f"tau {name}", ta.get(name))
    rb = (d.get("tau_tests") or {}).get("robustness") or {}
    if rb: h["tau: positive source-pair contrasts"] = f"{rb.get('positive_contrasts')}/{rb.get('source_pairs_with_same_dataset_pairs')}"
    # LOPO
    spec = (d.get("offset") or {}).get("chosen")
    for k, v in (((K.get("lopo_by_spec_and_K") or {}).get(spec)) or K.get("lopo_by_K") or {}).items():
        h[f"LOPO rho, K={k}"] = v.get("rho_struct")
    for name, v in (d.get("lopo_gain") or d.get("lopo_gain_vs_one_ordering") or {}).items(): _ci(h, f"gain {name}", v)
    for k, v in (K.get("paired_vs_best") or {}).items(): _ci(h, f"K={k} minus best K", v)
    # metadata
    for lab, v in (d.get("metadata_association_multi_source") or d.get("metadata_association_multi_paper") or {}).items():
        for kind, a in (v.items() if isinstance(v, dict) and "r2" not in v else [("full_loading", v)]):
            p = a.get("p_bonferroni_4_labels", a.get("p_value"))
            h[f"assoc {lab} ({kind}) significant"] = None if p is None else p < 0.05
    g = d.get("geometry_gate") or {}
    h["geometry published"] = g.get("published", d.get("geometry_recoverable"))
    h["dataset loadings transfer out of paper"] = g.get("dataset_loadings_transfer_out_of_paper")
    sn = d.get("seed_noise_reliability") or {}
    for k in ("comparisons", "comparisons_lo_ge_0_8", "comparisons_lo_ge_0_5"):
        if k in sn: h[f"seed noise: {k}"] = sn[k]
    rp = d.get("reproducibility") or {}
    if isinstance(rp, dict):
        for k in ("strict", "loose"): h[f"reproducibility {k}: estimable groups"] = len((rp.get(k) or {}).get("estimable") or [])
    else: h["reproducibility groups estimable"] = len(rp)
    return h

def changed(a, b, key):
    if a is None or b is None: return a != b
    if isinstance(a, bool) or isinstance(b, bool) or isinstance(a, int) and isinstance(b, int): return a != b
    if isinstance(a, str) or isinstance(b, str): return a != b
    tol = TOL_RHO if any(x in key for x in ("rho", "gain", "tau", "minus")) else 1e-9
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
