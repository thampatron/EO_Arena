"""CY-Bench: centroid of every administrative unit (adm_id) in the official centroids.zip (one point shapefile per
country, EPSG:4326) of the CY-Bench Zenodo record. Units are the spatial sampling units of the yield time series."""
import sys, io, zipfile, shutil
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

RECORD = "https://zenodo.org/records/17279151"
URL = "https://zenodo.org/api/records/17279151/files/centroids.zip/content"
TMP = Path("/tmp/claude-0/fp/cy-bench"); TMP.mkdir(parents=True, exist_ok=True)

r = requests.get(URL, timeout=300); r.raise_for_status()
zipfile.ZipFile(io.BytesIO(r.content)).extractall(TMP)
pts, per_country = [], {}
for shp in sorted(TMP.glob("centroids/*/*.shp")):
    g = gpd.read_file(shp)
    if g.crs is not None and g.crs.to_epsg() != 4326: g = g.to_crs(4326)
    g = g[g.geometry.notna()]
    per_country[shp.stem] = len(g)
    pts += list(zip(g.geometry.x, g.geometry.y))
write_footprint("cy-bench", pts, kind="samples", n_total=len(pts),
                source={"label": "CY-Bench centroids.zip (Zenodo)", "url": RECORD,
                        "method": "centroid point of every administrative unit in the per-country centroid shapefiles (adm_id), EPSG:4326"},
                note=f"{len(pts):,} administrative units in {len(per_country)} countries (largest: " +
                     ", ".join(f"{k} {v}" for k, v in sorted(per_country.items(), key=lambda x: -x[1])[:5]) +
                     "); 3,000 units stored. Maize and wheat yield series are per unit-year (BR shapefile has no CRS and is taken as WGS84).")
shutil.rmtree(TMP, ignore_errors=True)
