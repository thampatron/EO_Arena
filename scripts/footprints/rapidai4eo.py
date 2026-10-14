"""RapidAI4EO: centres of the 500,000 sample footprints (600 m squares) from the official geometries file
rapidai4eo_geometries.geojson.gz in the dataset's resources/ folder on Radiant MLHub's Azure blob (15.8 MB)."""
import sys, gzip, json, shutil
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://radiantearth.blob.core.windows.net/mlhub/rapidai4eo/resources/rapidai4eo_geometries.geojson.gz"
TMP = Path("/tmp/claude-0/fp/rapidai4eo"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "geoms.geojson.gz"
if not f.exists():
    r = requests.get(URL, timeout=300); r.raise_for_status(); f.write_bytes(r.content)
feats = json.load(gzip.open(f))["features"]
pts = []
for ft in feats:
    ring = ft["geometry"]["coordinates"][0][:4]
    pts.append((sum(p[0] for p in ring) / 4, sum(p[1] for p in ring) / 4))
write_footprint("rapidai4eo", pts, kind="samples", n_total=len(feats),
                source={"label": "RapidAI4EO sample geometries (rapidai4eo_geometries.geojson.gz)", "url": URL,
                        "method": "centre of each 600 m sample polygon in the official geometries file (WGS84)"},
                note="Mirrored on source.coop (planet/rapidai4eo) and Azure; 3,000 of 500,000 locations stored.")
shutil.rmtree(TMP, ignore_errors=True)
