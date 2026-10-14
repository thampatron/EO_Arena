#!/usr/bin/env python3
"""Build data/evidence.json: how much published GeoFM evidence exists per dataset.

Inputs (not in this repository):
  registry_benchmark_ids.csv   workbook benchmark id -> canonical dataset, EOArena id, domain, subdomain
  benchmark_ranking.csv        per canonical dataset: models, papers, spread, headroom, rho vs consensus, verdict
  registry_datasets.csv        per canonical dataset: result_rows, benchmark_ids, eoarena_id
These come from the EOArena analysis of the GeoFM meta-analysis workbook (V. Mancoridis, 2026,
unpublished). No individual scores are written here, only counts and summary statistics.

Usage: python3 scripts/build_evidence.py <dir with the three CSVs>
"""
import csv, json, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = Path(sys.argv[1])
ids = list(csv.DictReader(open(src / "registry_benchmark_ids.csv", encoding="utf-8")))
rank = {r["dataset"]: r for r in csv.DictReader(open(src / "benchmark_ranking.csv", encoding="utf-8"))}
reg = {r["dataset"]: r for r in csv.DictReader(open(src / "registry_datasets.csv", encoding="utf-8"))}
known = {d["id"] for d in json.loads((ROOT / "data" / "datasets.json").read_text(encoding="utf-8"))}

VERDICT = {
    "distinct ranking (candidate unique signal)": "e_dist",
    "partly distinct": "e_part",
    "tracks the consensus (redundant)": "e_red",
    "model differences below cross-paper noise": "e_weak",
    "saturated": "e_weak",
    "too few models to judge": "e_few",
}
def num(x, f=float):
    try: return f(x)
    except (TypeError, ValueError): return None

bench_ids = defaultdict(list)
for r in ids:
    bench_ids[r["canonical_dataset"]].append(r["benchmark_id"])

def summary(name):
    g, k = reg.get(name, {}), rank.get(name, {})
    rows = num(g.get("result_rows"), int) or 0
    out = {"models": num(g.get("models"), int) or 0, "papers": num(g.get("papers"), int) or 0, "results": rows,
           "benchmark_ids": sorted(bench_ids.get(name, []))}
    if k:
        out.update({"spread_pts": num(k.get("spread_pts")), "headroom_pts": num(k.get("headroom_pts")),
                    "rho_consensus": num(k.get("rho_consensus")), "share_self_reported": num(k.get("share_self_reported")),
                    "verdict": VERDICT.get(k.get("verdict"), "e_few")})
    else:
        out["verdict"] = "e_few" if rows else "e_none"
    return out

datasets, unlisted = {}, []
for name, g in reg.items():
    eid = g.get("eoarena_id") or ""
    s = summary(name)
    if eid and eid in known:
        datasets[eid] = s
    elif s["results"] > 0:
        unlisted.append({"name": name, "domain": g["domain"], "subdomain": g.get("subdomain") or "",
                         "input_kind": g.get("input_kind") or "", **{k: v for k, v in s.items() if k != "benchmark_ids"}})
unlisted.sort(key=lambda x: (x["domain"], -x["models"]))

doms = defaultdict(lambda: {"datasets": 0, "scored": 0, "results": 0, "unlisted_scored": 0})
for name, g in reg.items():
    if g.get("input_kind") != "eo_imagery" or g["domain"] in ("composite", "outside_taxonomy"): continue
    d = doms[g["domain"]]; rows = num(g.get("result_rows"), int) or 0
    d["datasets"] += 1; d["results"] += rows
    if rows: d["scored"] += 1
    if rows and not (g.get("eoarena_id") in known): d["unlisted_scored"] += 1

out = {"as_of": "2026-10-08",
       "source": "GeoFM meta-analysis workbook v4 (V. Mancoridis, unpublished): 14,600 reported scores from 52 papers. Summary statistics only; no individual scores.",
       "method": "Original results only (no numbers copied from other papers), no ablation variants. A comparison is one paper's table with >= 4 models on the same benchmark, protocol, metric and train fraction. spread_pts: median SD of model scores within a comparison (percent metrics). headroom_pts: 100 minus the median best score. rho_consensus: Spearman correlation between the dataset's model ranking (z-scored within comparison, averaged per model) and the mean ranking over all other datasets; needs >= 10 models.",
       "verdicts": {"e_dist": "Ranks models unlike the consensus (rho < 0.3)", "e_part": "Partly distinct (0.3 <= rho < 0.7)", "e_red": "Tracks the consensus (rho >= 0.7)", "e_weak": "Saturated (< 3 pts headroom) or model spread below the 2.3-pt cross-paper noise", "e_few": "Scored, but fewer than 10 models", "e_none": "No published GeoFM scores found"},
       "datasets": datasets, "unlisted": unlisted, "domains": dict(sorted(doms.items()))}
(ROOT / "data" / "evidence.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"evidence.json: {len(datasets)} EOArena datasets with evidence, {len(unlisted)} scored datasets not in the inventory, {len(doms)} domains")
