"""Maus et al. 2022 global mining polygons (Version 2): centroids of the 44,929 polygons in
global_mining_polygons_v2.gpkg (25 MB, WGS84) from the PANGAEA record 10.1594/PANGAEA.942325."""
import sys, shutil
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://download.pangaea.de/dataset/942325/files/global_mining_polygons_v2.gpkg"
TMP = Path("/tmp/claude-0/fp/maus-et-al-2022-mining-polygons"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "global_mining_polygons_v2.gpkg"
if not f.exists():
    with requests.get(URL, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(f, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)

g = gpd.read_file(f)
assert g.crs.to_epsg() == 4326
c = g.geometry.representative_point()
pts = list(zip(c.x, c.y))
n_countries = g["ISO3_CODE"].nunique() if "ISO3_CODE" in g else None

write_footprint("maus-et-al-2022-mining-polygons", pts, kind="samples", n_total=len(g),
                source={"label": "Global-scale mining polygons v2, PANGAEA 942325 (global_mining_polygons_v2.gpkg)", "url": "https://doi.org/10.1594/PANGAEA.942325",
                        "method": "representative point of each of the 44,929 mine-area polygons in the GeoPackage (WGS84)"},
                note=f"Polygons in {n_countries} countries; digitised on the 2019 Sentinel-2 cloudless mosaic within 10 km of S&P mine coordinates.")
shutil.rmtree(TMP, ignore_errors=True)
