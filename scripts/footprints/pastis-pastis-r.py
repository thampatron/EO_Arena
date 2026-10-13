"""PASTIS / PASTIS-R: patch centroids from the official metadata.geojson (2,433 patch polygons, EPSG:2154),
mirrored unchanged in the IGNF/PASTIS-HD Hugging Face repo (same patches as PASTIS/PASTIS-R)."""
import sys, shutil
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/IGNF/PASTIS-HD/resolve/main/metadata.geojson"
TMP = Path("/tmp/claude-0/fp/pastis-pastis-r"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "metadata.geojson"
if not f.exists():
    with requests.get(URL, stream=True, timeout=300) as r:
        r.raise_for_status(); f.write_bytes(r.content)
g = gpd.read_file(f)
c = g.geometry.centroid.to_crs(4326)
pts = list(zip(c.x, c.y))
write_footprint("pastis-pastis-r", pts, kind="samples", n_total=len(g),
                source={"label": "PASTIS metadata.geojson", "url": URL,
                        "method": "centroid of each 1.28 km patch polygon in metadata.geojson, reprojected EPSG:2154 -> EPSG:4326"},
                note="Patches lie in four S2 tiles (T30UXV, T31TFM, T31TFJ, T32ULU); PASTIS-R shares the same patch grid.")
shutil.rmtree(TMP, ignore_errors=True)
