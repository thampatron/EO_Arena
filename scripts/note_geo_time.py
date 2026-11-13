#!/usr/bin/env python3
"""Add geography and imagery period to the note's Eq. 12 association, from the loadings already in data/note_analysis.json.
  python3 -I scripts/note_geo_time.py     (no workbook needed)"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT / "scripts"))
import dataset_benchmarking as db
p = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "note_analysis.json"; d = json.loads(p.read_text()); gt = json.loads((ROOT / "data" / "dataset_geo_time.json").read_text())["datasets"]
names = list(d["datasets"]); Ld = np.array([d["datasets"][n]["loading"] for n in names]); multi = np.array([d["datasets"][n]["sources"] >= 2 for n in names])
r4 = lambda v: round(float(v), 4) if isinstance(v, float) else v
for key, lab in (("geography", "geography"), ("period", "time_period")):
    L = np.array([gt[n][key] or "" for n in names]); cnt = {x: int((L == x).sum()) for x in set(L) if x}
    keep = np.array([l != "" and cnt[l] >= 2 for l in L])                      # a level with one dataset explains itself
    Lk = np.where(keep, L, "")
    d["metadata_association"][lab] = {"all_datasets": {a: r4(b) for a, b in db.metadata_association(Ld, Lk, n_perm=2000, seed=0).items()},
                                      "all_datasets_direction_only": {a: r4(b) for a, b in db.metadata_association(Ld, Lk, n_perm=2000, seed=0, direction_only=True).items()},
                                      "multi_source": {a: r4(b) for a, b in db.metadata_association(Ld[multi], Lk[multi], n_perm=2000, seed=0).items()},
                                      "levels": {k: v for k, v in sorted(cnt.items(), key=lambda x: -x[1])}, "unlabelled": int((L == "").sum())}
    # global vs regional, the coarsest contrast
    if key == "geography":
        B = np.where(L == "", "", np.where(L == "Global", "global", "regional"))
        d["metadata_association"]["geography_global_vs_regional"] = {"all_datasets": {a: r4(b) for a, b in db.metadata_association(Ld, B, n_perm=2000, seed=0).items()}}
    print(lab, {k: (v["r2"], v["null_mean"], v["p_value"], v["n_levels"], v["n"]) for k, v in d["metadata_association"][lab].items() if isinstance(v, dict) and "r2" in v})
print(d["metadata_association"]["geography_global_vs_regional"])
d["metadata_not_available"] = ["spatial resolution", "label source"]; d["metadata_first_pass_unverified"] = ["geography", "time_period"]
p.write_text(json.dumps(d, indent=1))
