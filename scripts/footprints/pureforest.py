"""PureForest: patch centroids from the official metadata/PureForest-patches.gpkg (IGNF/PureForest on Hugging Face),
one 50 m x 50 m polygon per patch in EPSG:2154."""
import sys, shutil
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/IGNF/PureForest/resolve/main/metadata/PureForest-patches.gpkg"
TMP = Path("/tmp/claude-0/fp/pureforest"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "PureForest-patches.gpkg"
if not f.exists():
    r = requests.get(URL, timeout=300); r.raise_for_status(); f.write_bytes(r.content)
g = gpd.read_file(f)
c = g.geometry.centroid.to_crs(4326)
write_footprint("pureforest", list(zip(c.x, c.y)), kind="samples", n_total=len(g),
                source={"label": "PureForest-patches.gpkg", "url": URL,
                        "method": "centroid of each 50 m patch polygon in the metadata geopackage, EPSG:2154 -> WGS84"},
                note="135,569 patches (each has a paired aerial image and ALS point cloud); the paper's 449 stands are the parent forest polygons.")
shutil.rmtree(TMP, ignore_errors=True)
