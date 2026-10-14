"""Massachusetts Roads (Mnih 2013): tile centres decoded from the MassGIS tile ids in the file names listed on the
dataset's index pages (train/valid/test sat/index.html). Each 1500 x 1500 m tile is named PPPPSSSS_15 with origin
left = PPPP*100 - 713.56 m, top = SSSS*100 + 771.02 m in NAD83 / Massachusetts Mainland (EPSG:26986); the rule
is verified against the GeoTIFF header of four tiles read with rasterio over HTTP."""
import sys, re
from pathlib import Path
import requests, rasterio
from rasterio.warp import transform
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

BASE = "https://www.cs.toronto.edu/~vmnih/data/mass_roads/"
PAGE = "https://www.cs.toronto.edu/~vmnih/data/"
TILE = 1500.0

names = []
for split in ("train", "valid", "test"):
    t = requests.get(f"{BASE}{split}/sat/index.html", timeout=60).text
    names += [(split, n) for n in re.findall(r'href="[^"]*/(\d{8}_15)\.tiff"', t)]


def origin(name):
    p, s = int(name[:4]), int(name[4:8])
    if p >= 9000:  # tiles west of easting 100 km use a 3-digit x prefix (e.g. 99238660 -> x 992, y 8660)
        p = int(name[:3])
    return p * 100 - 713.56, s * 100 + 771.02  # left, top


with rasterio.Env(CPL_LOG="/dev/null"):
    for split, n in (names[0], names[len(names) // 2], names[-1], next(x for x in names if x[1].startswith("99"))):
        with rasterio.open(f"/vsicurl/{BASE}{split}/sat/{n}.tiff") as src:
            left, top = origin(n)
            assert src.crs.to_epsg() == 26986 and abs(src.bounds.left - left) < 2 and abs(src.bounds.top - top) < 2, (n, src.bounds)
xs = [origin(n)[0] + TILE / 2 for _, n in names]
ys = [origin(n)[1] - TILE / 2 for _, n in names]
lon, lat = transform("EPSG:26986", "EPSG:4326", xs, ys)
write_footprint("massachusetts-roads", list(zip(lon, lat)), kind="tiles", n_total=len(names),
                source={"label": "Massachusetts Roads index pages (U. Toronto)", "url": PAGE,
                        "method": "centre of each 1.5 km aerial tile decoded from its MassGIS tile id in the file name (EPSG:26986 -> WGS84), rule checked against four GeoTIFF headers"},
                note=f"{len(names)} tiles: train {sum(1 for s, _ in names if s == 'train')}, valid {sum(1 for s, _ in names if s == 'valid')}, test {sum(1 for s, _ in names if s == 'test')}; 1 m aerial imagery over ~2,600 km2 of Massachusetts.")
