"""Footprint for SpaceNet 7 (Van Etten et al. 2021), public S3 bucket spacenet-dataset.

Lists the AOI folders under spacenet/SN7_buildings/train/ and test_public/ (anonymous S3
ListObjectsV2). AOI names end in <x>_<y>_<z> slippy-map tile indices at zoom 13 (e.g.
L15-0331E-1257N_1327_3160_13); the tile centre is decoded from them. Verified against one
raster's EPSG:3857 bounds.
"""
import math, re, sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "spacenet-7"
BUCKET = "https://spacenet-dataset.s3.amazonaws.com/"


def list_prefixes(prefix):
    r = requests.get(BUCKET, params={"list-type": "2", "prefix": prefix, "delimiter": "/"}, timeout=60)
    r.raise_for_status()
    return [p for p in re.findall(r"<Prefix>(.*?)</Prefix>", r.text) if p != prefix]


def main():
    aois = []
    for split in ("train", "test_public"):
        aois += list_prefixes(f"spacenet/SN7_buildings/{split}/")
    pts = []
    for a in aois:
        m = re.search(r"_(\d+)_(\d+)_(\d+)/$", a)
        x, y, z = map(int, m.groups())
        n = 2 ** z
        lon = (x + 0.5) / n * 360 - 180
        lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / n))))
        pts.append((lon, lat))
    write_footprint(DS, pts, kind="tiles", n_total=len(aois),
                    source={"label": "SpaceNet 7 AOI folders on S3 (spacenet-dataset)", "url": BUCKET + "?prefix=spacenet/SN7_buildings/",
                            "method": "AOI folder names carry zoom-13 slippy-map tile x/y; decoded to the tile centre"},
                    note=f"{len(aois)} public AOIs (60 train + 20 test_public); the ~21 private test AOIs are not public. "
                         "Each AOI is one ~4 km x 4 km Planet mosaic tile with ~24 monthly images.")


if __name__ == "__main__":
    main()
