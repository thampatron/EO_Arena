"""Global Pasture Watch grassland samples: centres of the VHR interpretation tiles (gpw_grassland_fscs.vi.vhr_tile.samples ... .gpkg,
EPSG:3857, 8,199 tiles) from Zenodo 15631655. The point samples themselves (940 MB gpkg) are not downloaded;
every point sample sits inside one of these 1 km tiles."""
import sys, shutil
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://zenodo.org/records/15631655/files/gpw_grassland_fscs.vi.vhr_tile.samples_20000101_20241231_go_epsg.4326_v1.gpkg?download=1"
TMP = Path("/tmp/claude-0/fp/gpw"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "tiles.gpkg"
if not f.exists():
    f.write_bytes(requests.get(URL, timeout=300).content)
g = gpd.read_file(f)
c = g.geometry.centroid.to_crs(4326)
n_samples = int(g["n_samples_all"].sum()) if "n_samples_all" in g.columns else None
write_footprint("global-pasture-watch-grassland-samples", list(zip(c.x, c.y)), kind="tiles", n_total=n_samples,
                source={"label": "GPW VHR interpretation tile index (Zenodo 15631655)", "url": URL,
                        "method": f"centroids of the {len(g)} 1 km VHR interpretation tiles (EPSG:3857 -> 4326); n_total is the sum of per-tile sample counts"},
                note=f"{len(g)} tiles hold the point samples; per-point gpkg (940 MB) not downloaded.")
shutil.rmtree(TMP, ignore_errors=True)
