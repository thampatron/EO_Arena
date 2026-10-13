#!/usr/bin/env python3
"""Combine data/footprints/<id>.json into data/footprints.json for the map page."""
import json, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
out = {}
for f in sorted(glob.glob(str(ROOT / "data" / "footprints" / "*.json"))):
    r = json.loads(Path(f).read_text(encoding="utf-8"))
    out[r["id"]] = {k: r[k] for k in ("status", "kind", "n_total", "n_points", "bbox", "points", "source", "note", "built")}
(ROOT / "data" / "footprints.json").write_text(json.dumps(out, separators=(",", ":")) + "\n", encoding="utf-8")
st = {}
for r in out.values(): st[r["status"]] = st.get(r["status"], 0) + 1
print(f"footprints.json: {len(out)} datasets, {sum(r['n_points'] for r in out.values())} points, {st}")
