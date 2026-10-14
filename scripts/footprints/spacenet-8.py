"""SpaceNet 8: tile centres from the GeoTIFF headers of a stratified random sample of 300 PRE-event image tiles
(of 1,007) in the public spacenet-dataset S3 bucket (Germany_Training_Public, Louisiana-East_Training_Public,
Louisiana-West_Test_Public), read with rasterio over /vsicurl (headers only)."""
import sys, re, random, logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests, rasterio
from rasterio.warp import transform
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

BUCKET = "https://spacenet-dataset.s3.amazonaws.com/"
PREFIX = "spacenet/SN8_floods/"
AREAS = ["Germany_Training_Public", "Louisiana-East_Training_Public", "Louisiana-West_Test_Public"]
N_SAMPLE = 300


def list_keys(prefix):
    keys, token = [], None
    while True:
        url = f"{BUCKET}?list-type=2&prefix={prefix}&max-keys=1000" + (f"&continuation-token={requests.utils.quote(token)}" if token else "")
        t = requests.get(url, timeout=60).text
        keys += re.findall(r"<Key>([^<]+)</Key>", t)
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", t)
        if not m: return keys
        token = m.group(1)


tiles = {a: [k for k in list_keys(f"{PREFIX}{a}/PRE-event/") if k.endswith(".tif")] for a in AREAS}
n_total = sum(len(v) for v in tiles.values())
rng = random.Random(0)
sample = []
for a, ks in tiles.items():
    sample += rng.sample(ks, round(N_SAMPLE * len(ks) / n_total))


def centre(key):
    try:
        with rasterio.Env(CPL_LOG="/dev/null", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(f"/vsicurl/{BUCKET}{key}") as src:
            b = src.bounds
            xs, ys = transform(src.crs, "EPSG:4326", [(b.left + b.right) / 2], [(b.bottom + b.top) / 2])
            return (xs[0], ys[0])
    except Exception as e:  # noqa: BLE001
        print("skip", key, e); return None


logging.disable(logging.CRITICAL)
with ThreadPoolExecutor(8) as ex:
    pts = [p for p in ex.map(centre, sample) if p]
write_footprint("spacenet-8", pts, kind="tiles", n_total=n_total,
                source={"label": "SpaceNet 8 on AWS (spacenet-dataset bucket)", "url": "https://spacenet.ai/sn8-challenge/",
                        "method": f"centre of {len(sample)} randomly chosen PRE-event image tiles (stratified by area) from GeoTIFF headers read over HTTP, UTM -> WGS84"},
                note="PRE-event tiles: " + ", ".join(f"{a} {len(k)}" for a, k in tiles.items()) +
                     ". Two flood events: Ahr valley, Germany (July 2021) and Hurricane Ida, Louisiana, USA (Sept 2021); the test area is Louisiana-West.")
