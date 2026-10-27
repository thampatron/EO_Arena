#!/usr/bin/env python3
"""Write docs/replicate-plan.md from data/replicate_plan.json: the datasets where measured seed noise is missing,
ordered by how much published evidence rests on them, with the models to re-run."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
p = json.loads((ROOT / "data" / "replicate_plan.json").read_text())
L = ["# Replicate plan: where measured seed noise is missing", "",
     f"Generated {p['as_of']} by `scripts/build_evidence.py`. {p['method']}", "",
     "The score of every dataset below is **provisional**: its noise σ² is plugged in from similar comparisons. Re-running the suggested models with ≥ 5 seeds (same protocol family, same metric) measures σ² directly and moves the dataset to the measured tier. Evidence mass = models × comparisons; the first rows carry the most published evidence per unit of work.", "",
     "| # | Dataset | Domain | Models | Papers | Comparisons | Evidence mass | Provisional score | Protocols | Suggested models (comparisons they appear in) |", "|---|---|---|---|---|---|---|---|---|---|"]
for i, d in enumerate(p["datasets"], 1):
    sm = ", ".join(f"{m['model_id']} ({m['comparisons']})" for m in d["suggested_models"])
    L.append(f"| {i} | {d['name']}{'' if d.get('id') else ' *(not in inventory)*'} | {d['domain'].split('· ')[-1]} | {d['models']} | {d['papers']} | {d['tasks_n']} | {d['evidence_mass']} | {'–' if d['provisional_score'] is None else f'{d['provisional_score']:.2f}'} | {', '.join(d['protocol_families'])} | {sm} |")
top = p["datasets"][:12]
L += ["", "## A first batch", "", f"The top {len(top)} rows cover {sum(d['evidence_mass'] for d in top)} of {sum(d['evidence_mass'] for d in p['datasets'])} evidence-mass units. Models that recur across them:", ""]
from collections import Counter
c = Counter(m["model_id"] for d in top for m in d["suggested_models"])
L += [f"- {m}: in {n} of the {len(top)} datasets' suggestions" for m, n in c.most_common(10)]
L += ["", "Running these models on these datasets at 5 seeds each, under the protocol family listed, is the smallest job that converts most of the provisional mass to measured. Pangaea-style frozen-decoder evaluation is the common denominator for the segmentation sets; GEO-Bench-style fine-tuning for the classification sets."]
(ROOT / "docs" / "replicate-plan.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("docs/replicate-plan.md:", len(p["datasets"]), "datasets")
