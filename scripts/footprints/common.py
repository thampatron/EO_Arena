"""Shared writer for sample-level dataset footprints (data/footprints/<id>.json).

Each footprint records WHERE a dataset's samples are, as lon/lat points, so the map can show
the real spatial distribution instead of the countries a paper names.

Usage from an extraction script (scripts/footprints/<id>.py):
    from common import write_footprint
    write_footprint("sen1floods11", points, source={"label": "Sen1Floods11 metadata CSV",
                    "url": "https://...", "method": "chip centroids from the catalog CSV"},
                    kind="samples", n_total=len(points))
    # or, when nothing usable exists:
    write_footprint("some-id", [], source={...}, status="unavailable",
                    note="Imagery is registration-only; no public index of sample locations.")

Schema written:
  id, status (ok | partial | unavailable), kind (samples | tiles | sites | bbox), crs (EPSG:4326),
  n_total (samples in the dataset, if known), n_points (points stored, <= MAX_POINTS),
  bbox [w, s, e, n], points [[lon, lat], ...] (3 decimals), source {label, url, method}, note, built
"""
import json, random, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "footprints"
MAX_POINTS = 3000

def write_footprint(ds_id, points, source, kind="samples", n_total=None, status=None, note=""):
    pts = []
    for p in points:
        try:
            lon, lat = float(p[0]), float(p[1])
        except (TypeError, ValueError, IndexError):
            continue
        if -180 <= lon <= 180 and -90 <= lat <= 90 and not (lon == 0 and lat == 0):
            pts.append((round(lon, 3), round(lat, 3)))
    pts = sorted(set(pts))
    if status is None:
        status = "ok" if pts else "unavailable"
    if len(pts) > MAX_POINTS:
        random.Random(0).shuffle(pts); pts = sorted(pts[:MAX_POINTS])
    bbox = [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)] if pts else None
    rec = {"id": ds_id, "status": status, "kind": kind, "crs": "EPSG:4326", "n_total": n_total, "n_points": len(pts),
           "bbox": bbox, "points": [list(p) for p in pts], "source": source, "note": note,
           "built": datetime.date.today().isoformat()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{ds_id}.json").write_text(json.dumps(rec, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{ds_id}: {status}, {len(pts)} points" + (f" of {n_total}" if n_total else ""))
    return rec
