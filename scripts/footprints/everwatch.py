"""EverWatch (Weecology, Everglades wading-bird colonies): the dataset archive on Zenodo (17317117) is a 22 GB zip
of PNG crops with pixel-space annotations and no per-image geolocation. The companion release
weecology/everwatch-predictions v0.1.1 (Zenodo 11192497, 24 MB) is a georeferenced shapefile (EPSG:32617) of
model-predicted birds with a Site and Year attribute over the same colony surveys (2020-2023). One point per
colony (median location of 2020-2022 detections) is used as the site footprint."""
import sys, io, zipfile, shutil
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://zenodo.org/api/records/11192497/files/weecology/everwatch-predictions-v0.1.1.zip/content"
TMP = Path("/tmp/claude-0/fp/everwatch"); TMP.mkdir(parents=True, exist_ok=True)
shp = TMP / "PredictedBirds.shp"
if not shp.exists():
    outer = zipfile.ZipFile(io.BytesIO(requests.get(URL, timeout=300).content))
    inner_name = next(n for n in outer.namelist() if n.endswith("PredictedBirds.zip"))
    zipfile.ZipFile(io.BytesIO(outer.read(inner_name))).extractall(TMP)

g = gpd.read_file(shp)
g = g[g["Year"].astype(str).isin(["2020", "2021", "2022"])]
c = g.geometry.centroid
g = g.assign(x=c.x, y=c.y)
sites = g.groupby("Site")[["x", "y"]].median()
ll = gpd.GeoSeries(gpd.points_from_xy(sites.x, sites.y), crs=g.crs).to_crs(4326)
pts = [(p.x, p.y) for p in ll]

write_footprint("everwatch", pts, kind="sites", n_total=5127, status="partial",
                source={"label": "weecology/everwatch-predictions v0.1.1 PredictedBirds.shp (Zenodo 11192497)", "url": URL,
                        "method": f"median location of georeferenced bird detections per colony (Site attribute) for the 2020-2022 surveys, {len(pts)} colonies in Florida"},
                note="Dataset images (4,438 train / 493 val / 196 test PNG crops, Zenodo 17317117, 22 GB) carry no coordinates; colony locations come from the companion georeferenced prediction shapefile over the same surveys, so this is the set of surveyed colonies rather than per-crop positions.")
shutil.rmtree(TMP, ignore_errors=True)
