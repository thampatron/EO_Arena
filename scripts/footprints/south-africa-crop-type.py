"""South Africa crop type (Radiant Earth 'Spot the Crop', Western Cape): tile centres read from the GeoTIFF headers of a
subsample of the per-tile label rasters on source.coop (train/labels/<id>.tif, test/labels/<id>.tif; 256x256 px at 10 m).
No metadata file with tile locations exists in the repo, so headers are read over HTTP (<= 300 files)."""
import sys, re, random
from pathlib import Path
import requests, rasterio
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

BASE = "https://data.source.coop/radiantearth/south-africa-crops-competition/"
CAP = 300

def list_keys(prefix):
    keys, marker = [], ""
    while True:
        r = requests.get(BASE, params={"prefix": prefix, "marker": marker, "delimiter": "/"}, timeout=60); r.raise_for_status()
        ks = re.findall(r"<Key>(.*?)</Key>", r.text); keys += [k for k in ks if k.endswith(".tif") and "_field_ids" not in k]
        # NextMarker in the response is in another namespace; paginate from the last key instead
        if "<IsTruncated>true" in r.text and ks: marker = ks[-1].split("south-africa-crops-competition/", 1)[-1]
        else: return keys

keys = list_keys("train/labels/")  # test tiles have no public label rasters
n_total = len(keys)
random.Random(0).shuffle(keys)
pts = []
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
    for k in keys[:CAP]:
        k = k.split("south-africa-crops-competition/", 1)[-1]
        try:
            with rasterio.open("/vsicurl/" + BASE + k) as ds:
                pts.append(ds.lnglat())
        except Exception as e:
            print("skip", k, e)
write_footprint("south-africa-crop-type", pts, kind="tiles", n_total=n_total, status="partial",
                source={"label": "source.coop radiantearth/south-africa-crops-competition label tiles", "url": BASE,
                        "method": f"centre of {len(pts)} randomly sampled label GeoTIFFs (of {n_total} train tiles) read from headers via /vsicurl"},
                note=f"Subsample of {CAP} of {n_total} 2.56 km training tiles (no tile index file is published; the 1,137 test tiles carry imagery only); all in the Western Cape.")
