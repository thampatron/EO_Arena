"""CropHarvest: label point locations from labels.geojson in the Zenodo record (v10251170)."""
import sys, shutil
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://zenodo.org/api/records/10251170/files/labels.geojson/content"
TMP = Path("/tmp/claude-0/fp/cropharvest"); TMP.mkdir(parents=True, exist_ok=True)

f = TMP / "labels.geojson"
if not f.exists():
    with requests.get(URL, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(f, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
g = gpd.read_file(f)
if "lon" in g.columns and "lat" in g.columns:
    pts = list(zip(g["lon"].astype(float), g["lat"].astype(float)))
else:
    c = g.geometry.representative_point()
    pts = list(zip(c.x, c.y))
write_footprint("cropharvest", pts, kind="samples", n_total=len(g),
                source={"label": "CropHarvest labels.geojson (Zenodo 10251170)", "url": URL,
                        "method": "lon/lat of every label point in labels.geojson (one point per sample)"})
shutil.rmtree(TMP, ignore_errors=True)
