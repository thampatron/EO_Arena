"""Open-Canopy: centroids of the 1 km x 1 km lidar/SPOT tiles listed in canopy_height/geometries.geojson
on the Hugging Face repo AI4Forest/Open-Canopy (EPSG:2154 -> EPSG:4326). 95,429 tiles (train/val/test/buffer)."""
import sys, shutil
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/AI4Forest/Open-Canopy/resolve/main/canopy_height/geometries.geojson"
TMP = Path("/tmp/claude-0/fp/open-canopy"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "geometries.geojson"
if not f.exists():
    with requests.get(URL, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(f, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)

g = gpd.read_file(f)
n_total = len(g)
splits = g["split"].value_counts().to_dict()
c = g.geometry.centroid
pts_ll = gpd.GeoSeries(c, crs=g.crs).to_crs(4326)
pts = [(p.x, p.y) for p in pts_ll]

write_footprint("open-canopy", pts, kind="tiles", n_total=n_total,
                source={"label": "Open-Canopy geometries.geojson (Hugging Face)", "url": URL,
                        "method": "centroids of the 95,429 1 km tiles in geometries.geojson, reprojected from EPSG:2154 (Lambert-93) to EPSG:4326"},
                note=f"Tiles per split: {splits}. 'buffer' tiles are not used for training or evaluation.")
shutil.rmtree(TMP, ignore_errors=True)
