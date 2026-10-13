"""TreeSatAI: 60 m patch centroids from geojson.zip (bb_60m.GeoJSON, EPSG:25832) in the Zenodo record."""
import sys, io, zipfile, shutil
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://zenodo.org/records/6598391/files/geojson.zip?download=1"
TMP = Path("/tmp/claude-0/fp/treesatai"); TMP.mkdir(parents=True, exist_ok=True)

z = TMP / "geojson.zip"
if not z.exists():
    z.write_bytes(requests.get(URL, timeout=120).content)
with zipfile.ZipFile(z) as zf:
    raw = zf.read("geojson/bb_60m.GeoJSON")
g = gpd.read_file(io.BytesIO(raw))
c = g.geometry.centroid.to_crs(4326)
pts = list(zip(c.x, c.y))
write_footprint("treesatai", pts, kind="samples", n_total=len(g),
                source={"label": "TreeSatAI geojson.zip (bb_60m.GeoJSON)", "url": URL,
                        "method": "centroids of the 60 m patch polygons in bb_60m.GeoJSON, reprojected from EPSG:25832"})
shutil.rmtree(TMP, ignore_errors=True)
