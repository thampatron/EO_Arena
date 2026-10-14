"""Footprint for the Massachusetts Buildings dataset (Mnih 2013), cs.toronto.edu/~vmnih/data.

The train/valid/test 'sat' directories have HTML indexes listing the 151 1500x1500 px (1 m) tiles, and each
tile is a GeoTIFF in NAD83 Massachusetts Mainland (EPSG:26986). Only the header of each tile is read over
HTTP (rasterio /vsicurl/) to get its centre; the centre is reprojected to WGS84.
"""
import re, sys
from pathlib import Path

import rasterio
import requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "massachusetts-buildings"
BASE = "https://www.cs.toronto.edu/~vmnih/data/mass_buildings/"


def main():
    tiles = []
    for split in ("train", "valid", "test"):
        html = requests.get(f"{BASE}{split}/sat/index.html", timeout=120).text
        tiles += [(split, n) for n in sorted(set(re.findall(r"\d+_\d+\.tiff", html)))]
    tf = Transformer.from_crs("EPSG:26986", "EPSG:4326", always_xy=True)
    pts = []
    for split, name in tiles:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
            with rasterio.open(f"/vsicurl/{BASE}{split}/sat/{name}") as src:
                b = src.bounds
                assert src.crs.to_epsg() == 26986, (name, src.crs)
        pts.append(tf.transform((b.left + b.right) / 2, (b.bottom + b.top) / 2))
    counts = {s: sum(1 for t in tiles if t[0] == s) for s in ("train", "valid", "test")}
    write_footprint(DS, pts, kind="tiles", n_total=len(tiles),
                    source={"label": "Massachusetts Buildings tiles (Mnih, U. Toronto)", "url": BASE,
                            "method": "centre of each GeoTIFF tile (EPSG:26986), header read over HTTP via rasterio /vsicurl/"},
                    note=f"{len(tiles)} tiles of 1.5 x 1.5 km over the Boston area (train {counts['train']}, valid {counts['valid']}, test {counts['test']}).")


if __name__ == "__main__":
    main()
