"""Global Mangrove Watch v3 (v4 uses the same tiling): centres of the 1x1 degree product tiles listed in gmw_v3_tiles.geojson
on the Zenodo record (one tile per 1-degree cell containing mangroves)."""
import sys, shutil
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://zenodo.org/api/records/6894273/files/gmw_v3_tiles.geojson/content"
TMP = Path("/tmp/claude-0/fp/global-mangrove-watch-v3-v4"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "gmw_v3_tiles.geojson"
if not f.exists():
    r = requests.get(URL, timeout=300); r.raise_for_status(); f.write_bytes(r.content)
g = gpd.read_file(f)
c = g.geometry.centroid
write_footprint("global-mangrove-watch-v3-v4", list(zip(c.x, c.y)), kind="tiles", n_total=len(g),
                source={"label": "GMW v3 tile index (gmw_v3_tiles.geojson, Zenodo 6894273)", "url": "https://zenodo.org/records/6894273",
                        "method": "centre of each 1x1 degree GMW product tile polygon in the tile index"},
                note="Tiles are 1-degree cells that contain mangroves; the map product itself is a raster/vector extent, not samples.")
shutil.rmtree(TMP, ignore_errors=True)
