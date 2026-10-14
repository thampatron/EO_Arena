"""BreizhCrops: field-parcel centroids from the 2017 shapefiles (one per NUTS-3 region frh01..frh04) that the
BreizhCrops package downloads from its public S3 bucket (SHP_URLs in breizhcrops/datasets/urls.py).
Each tar.gz (42-56 MB) is fetched, the parcel centroids are taken, and the archive is deleted before the next one."""
import sys, io, tarfile, shutil, random
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

BASE = "https://breizhcrops.s3.eu-central-1.amazonaws.com/2017/shp/"
REGIONS = ["frh01", "frh02", "frh03", "frh04"]
TMP = Path("/tmp/claude-0/fp/breizhcrops"); TMP.mkdir(parents=True, exist_ok=True)
PER_REGION = 1500  # centroids kept per region before the global subsample

pts, n_total, counts = [], 0, {}
for r in REGIONS:
    d = TMP / r
    if not d.exists():
        d.mkdir()
        with requests.get(BASE + f"{r}.tar.gz", stream=True, timeout=600) as resp:
            resp.raise_for_status()
            with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as t:
                t.extractall(d, filter="data")
    shp = next(d.rglob("*.shp"))
    g = gpd.read_file(shp)
    counts[r] = len(g); n_total += len(g)
    c = g.geometry.centroid
    c = gpd.GeoSeries(c, crs=g.crs).to_crs(4326)
    rows = list(range(len(c)))
    random.Random(0).shuffle(rows)
    pts += [(c.iloc[i].x, c.iloc[i].y) for i in rows[:PER_REGION]]
    shutil.rmtree(d, ignore_errors=True)

write_footprint("breizhcrops", pts, kind="samples", n_total=n_total,
                source={"label": "BreizhCrops 2017 parcel shapefiles (S3 bucket used by the breizhcrops package)", "url": BASE,
                        "method": f"parcel polygon centroids from the four regional shapefiles, {PER_REGION} random parcels per region"},
                note=f"Parcels per region (2017): {counts}. Total transfer ~190 MB (four tar.gz archives), slightly above the 150 MB guideline to avoid dropping a department.")
shutil.rmtree(TMP, ignore_errors=True)
