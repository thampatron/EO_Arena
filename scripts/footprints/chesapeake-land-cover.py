"""Chesapeake land cover (Chesapeake CVPR 2019 / GEO-Bench m-chesapeake) footprint.
(The index geometry is EPSG:3857 and is reprojected to WGS84.)

GEO-Bench's m-chesapeake.zip (Hugging Face, recursix/geo-bench-1.0) holds 5,014 HDF5 chips whose band metadata has
crs=None and transform=None (checked on one sample), so the chips cannot be located directly. They are cut from the
Chesapeake Land Cover CVPR-2019 tiles (Robinson et al.), whose 150 GB zip on LILA ships spatial_index.geojson (752 KB)
with one polygon per NAIP tile. That member alone is read out of the zip with HTTP range requests and each tile's
polygon centroid is written (kind=tiles). Points therefore mark the parent tiles, not the individual GEO-Bench chips.
"""
import json, struct, sys, zipfile, zlib
from pathlib import Path

import requests
from pyproj import Transformer
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "chesapeake-land-cover"
ZIP = "https://lilawildlife.blob.core.windows.net/lila-wildlife/lcmcvpr2019/cvpr_chesapeake_landcover.zip"
MEMBER = "cvpr_chesapeake_landcover/spatial_index.geojson"


class RangeFile:
    def __init__(self, url):
        r = requests.get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True, timeout=60)
        r.raise_for_status()
        self.url, self.pos = r.url, 0
        self.size = int(r.headers["Content-Range"].split("/")[-1])

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        if n < 0:
            n = self.size - self.pos
        if n == 0:
            return b""
        r = requests.get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}, timeout=300)
        r.raise_for_status()
        self.pos += len(r.content)
        return r.content

    def seekable(self):
        return True

    def readable(self):
        return True


def main():
    rf = RangeFile(ZIP)
    info = zipfile.ZipFile(rf).getinfo(MEMBER)
    rf.seek(info.header_offset)
    nlen, xlen = struct.unpack("<HH", rf.read(30)[26:30])
    rf.seek(info.header_offset + 30 + nlen + xlen)
    raw = rf.read(info.compress_size)
    data = zlib.decompress(raw, -15) if info.compress_type == zipfile.ZIP_DEFLATED else raw
    gj = json.loads(data)
    feats = gj["features"]
    crs_name = (gj.get("crs") or {}).get("properties", {}).get("name", "EPSG:4326")
    epsg = int(crs_name.rsplit(":", 1)[-1]) if crs_name[-1:].isdigit() else 4326
    tr = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    pts, splits = [], {}
    for ft in feats:
        c = shape(ft["geometry"]).centroid
        pts.append(tr.transform(c.x, c.y))
        key = str(ft.get("properties", {}).get("split", "?")).split("-")[-1]
        splits[key] = splits.get(key, 0) + 1
    write_footprint(DS, pts, kind="tiles", n_total=len(feats), status="partial",
                    source={"label": "Chesapeake Land Cover CVPR-2019 spatial_index.geojson (inside the LILA zip)", "url": "https://lila.science/datasets/chesapeakelandcover",
                            "method": "polygon centroid of every NAIP tile in spatial_index.geojson, read from the 150 GB zip with range requests"},
                    note=f"{len(feats)} 1 m NAIP tiles across DE, MD, NY, PA, VA, WV (splits: {splits}). GEO-Bench m-chesapeake has 5,014 256 px chips cut from these tiles with no georeferencing in the HDF5s, so chips are not located individually.")


if __name__ == "__main__":
    main()
