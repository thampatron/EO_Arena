"""SDS_Benchmark: centroid of every cross-shore transect (<SITE>_transects.geojson, WGS84/CRS84) in the GitHub repo,
for the benchmark sites listed in sites_info.txt (the four of the paper; Cala Millor has no transect file yet)."""
import sys, json
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

REPO = "https://github.com/kvos/SDS_Benchmark"
RAW = "https://raw.githubusercontent.com/kvos/SDS_Benchmark/main/datasets/"

info = json.loads(requests.get(RAW + "sites_info.txt", timeout=60).text)
pts, per_site = [], {}
for site, meta in info.items():
    r = requests.get(f"{RAW}{site}/{site}_transects.geojson", timeout=60)
    if r.status_code != 200:
        print("skip", site, r.status_code); continue
    g = gpd.GeoDataFrame.from_features(r.json()["features"], crs="EPSG:4326")  # files are CRS84 lon/lat
    c = g.geometry.centroid
    per_site[site] = len(g); pts += list(zip(c.x, c.y))
write_footprint("sds-benchmark", pts, kind="samples", n_total=len(pts),
                source={"label": "SDS_Benchmark transect GeoJSONs (GitHub)", "url": REPO,
                        "method": "centroid of each cross-shore transect line in datasets/<SITE>/<SITE>_transects.geojson (CRS84 lon/lat)"},
                note="Transects per site: " + ", ".join(f"{k} {v}" for k, v in per_site.items()) + ". Shoreline time series are evaluated per transect; Cala Millor (in sites_info.txt) has no transect file in the repo.")
