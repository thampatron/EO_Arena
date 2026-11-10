#!/usr/bin/env python3
"""Build findings.html: one panel per question, each with one conclusion, from the analysis JSON files (no workbook needed).

  python3 -I scripts/build_findings_page.py [--artifact <path>]

Writes findings.html (site page, standalone) and, with --artifact, the same body without the document wrapper.
Summary statistics only: no individual score and no model ranking.
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent; DATA = ROOT / "data"
def J(n):
    p = DATA / n; return json.loads(p.read_text()) if p.exists() else None

main, ext = J("dataset_analysis.json"), J("dataset_extensions.json")
ws = ext["within_source"]; rt = ext["restricted_tau"]; at = ext["model_attributes"]; pc = ext["panel_completion"]

def lopo(name, label, rows):
    d = J(name)
    if d is None: return None
    L = d["K"]["lopo_by_spec_and_K"]["none"]
    return {"label": label, "rows": rows, "board": L["1"]["rho_board"], "k": [[int(k), v["rho_struct"]] for k, v in sorted(L.items(), key=lambda x: int(x[0]))],
            "models": d["overlap"]["models"], "tasks": d["overlap"]["tasks"]}
curves = [c for c in (lopo("dataset_analysis_sens_k6_log_all.json", "All rows", "all"), lopo("dataset_analysis_sens_k6_log_main.json", "Main-text tables only", "main"),
                      lopo("dataset_analysis_sens_k6_linear_all.json", "All rows, linear regression scale", "all-linear"),
                      lopo("dataset_analysis_sens_k6_linear_main.json", "Main-text tables only, linear scale", "main-linear"),
                      lopo("dataset_analysis_sens_core3.json", "GeoFMs in 3 or more sources", "core3"), lopo("dataset_analysis_sens_frozen.json", "Frozen-encoder protocols only", "frozen"),
                      lopo("dataset_analysis_sens_families.json", "Model families merged", "families")) if c]

LAB = {"all": "All GeoFMs and comparisons", "models_in_2plus_sources": "GeoFMs in 2 or more sources", "models_in_3plus_sources": "GeoFMs in 3 or more sources",
       "models_in_4plus_sources": "GeoFMs in 4 or more sources", "frozen_only": "Frozen-encoder protocols only", "fine_tuned_only": "Fine-tuning only",
       "families_merged": "Model families merged", "families_merged_3plus_sources": "Families merged, in 3 or more sources"}
forest = [{"label": LAB[k], "est": v["identity"]["estimate"], "lo": v["identity"]["ci90"][0], "hi": v["identity"]["ci90"][1], "pos": v["positive"], "n": v["source_pairs"],
           "p": v["sign_test_p"], "models": v["matrix"]["models"], "tasks": v["matrix"]["tasks"]} for k, v in rt.items()]

# replication scatter: dataset-pair agreement in one source against the same pair in another, each centred on its source-pair mean
mats = {b["source"]: (b["names"], np.array([[np.nan if x is None else x for x in r] for r in b["tau"]], float)) for b in ws["blocks"]}
pts = []
src = sorted(mats)
for i in range(len(src)):
    for j in range(i + 1, len(src)):
        na, Ma = mats[src[i]]; nb, Mb = mats[src[j]]; sh = sorted(set(na) & set(nb))
        if len(sh) < 3: continue
        xs, ys, lab = [], [], []
        for a in range(len(sh)):
            for b in range(a + 1, len(sh)):
                x = Ma[na.index(sh[a]), na.index(sh[b])]; y = Mb[nb.index(sh[a]), nb.index(sh[b])]
                if np.isfinite(x) and np.isfinite(y): xs.append(x); ys.append(y); lab.append(f"{sh[a]} and {sh[b]}")
        if len(xs) < 3: continue
        xs, ys = np.array(xs) - np.mean(xs), np.array(ys) - np.mean(ys)
        pts += [[round(float(x), 3), round(float(y), 3), l, src[i], src[j]] for x, y, l in zip(xs, ys, lab)]
rep = ws["replication"]; assert len(pts) == rep["raw"]["dataset_pairs"], (len(pts), rep["raw"]["dataset_pairs"])

sn = main["seed_noise_reliability"]; cells = {(c["same_dataset"], c["same_source"]): c for c in main["tau_tests"]["cells"]}
p8 = pc["panels"][0]
D = {"overlap": main["overlap"], "cells": [{"ds": a, "src": b, "tau": cells[(a, b)]["mean_tau"], "pairs": cells[(a, b)]["pairs"]} for a in (True, False) for b in (True, False)],
     "paper": main["tau_tests"]["all"]["paper_specificity"], "forest": forest,
     "within": ws["identity"], "blocks": [{k: b[k] for k in ("source", "datasets", "dataset_pairs", "median_shared_geofms", "mean_tau")} for b in ws["blocks"]],
     "within_mean": ws["dataset_pair_tau"], "rep": {k: {a: b for a, b in v.items() if a not in ("per_source_pair", "datasets")} for k, v in rep.items()}, "pts": pts,
     "curves": curves, "attr": at, "seed": {"n": sn["comparisons"], "hi": sn["comparisons_lo_ge_0_8"], "mid": sn["comparisons_lo_ge_0_5"], "total": main["overlap"]["tasks"]},
     "panel": {k: p8[k] for k in ("models", "datasets", "published", "cells", "already_published", "to_run")}, "panels": [{k: p[k] for k in ("panel_size", "cells", "already_published", "to_run")} for p in pc["panels"]],
     "as_of": ext["as_of"]}

BODY = (ROOT / "scripts" / "findings_template.html").read_text().replace("/*__DATA__*/null", json.dumps(D, separators=(",", ":")))
(ROOT / "findings.html").write_text('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n' + BODY + "\n</body>\n</html>\n")
if "--artifact" in sys.argv: Path(sys.argv[sys.argv.index("--artifact") + 1]).write_text(BODY)
print("wrote findings.html", len(BODY), "bytes;", len(pts), "replication points;", len(curves), "curves")
