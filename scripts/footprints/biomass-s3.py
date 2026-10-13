"""Biomass-S3 (Copernicus-Bench, Wang et al. 2025) footprint.

The data are one 1.26 GB biomass_s3.zip on Hugging Face. Only the zip's central directory is read (HTTP range
requests, ~2 MB). Each label patch is named after the ESA CCI Biomass 10x10 degree tile it was cut from and its
row/column inside that tile, e.g. N30E080_ESACCI-BIOMASS-L4-AGB-MERGED-100m-2020-fv4.0_29_32.tif: the tile's
north-west corner is 30N 80E and the patch is 282 x 282 pixels of 1/1125 degree (0.250667 deg), row 29, column 32
(1-based from the NW corner). Verified against the GeoTIFF bounds of six patches. One point per label patch.
"""
import re, sys, time, zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "biomass-s3"
URL = "https://huggingface.co/datasets/wangyi111/Copernicus-Bench/resolve/main/l3_biomass_s3/biomass_s3.zip"
PATCH_DEG = 282 * (1.0 / 1125.0)  # 0.250667 degrees


class RangeFile:
    def __init__(self, url):
        r = self._get(url, headers={"Range": "bytes=0-0"})
        self.url, self.pos = r.url, 0
        self.size = int(r.headers["Content-Range"].split("/")[-1])

    @staticmethod
    def _get(url, **kw):
        for i in range(6):
            r = requests.get(url, timeout=120, allow_redirects=True, **kw)
            if r.status_code != 429:
                r.raise_for_status()
                return r
            time.sleep(5 * (i + 1))
        r.raise_for_status()

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
        b = self._get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}).content
        self.pos += len(b)
        return b

    def seekable(self):
        return True

    def readable(self):
        return True


PAT = re.compile(r"([NS])(\d{2})([EW])(\d{3})_ESACCI-BIOMASS.*?_(\d+)_(\d+)\.tif$")


def centre(name):
    m = PAT.search(name)
    if not m:
        return None
    lat0 = int(m[2]) * (1 if m[1] == "N" else -1)
    lon0 = int(m[4]) * (1 if m[3] == "E" else -1)
    row, col = int(m[5]), int(m[6])
    return lon0 + (col - 0.5) * PATCH_DEG, lat0 - (row - 0.5) * PATCH_DEG


def main():
    z = zipfile.ZipFile(RangeFile(URL))
    names = [i.filename for i in z.infolist() if i.filename.startswith("biomass_s3/biomass/") and i.filename.endswith(".tif")]
    pts = [c for c in (centre(n) for n in names) if c]
    write_footprint(DS, pts, kind="samples", n_total=len(names),
                    source={"label": "Copernicus-Bench biomass_s3.zip (Hugging Face) file listing", "url": URL,
                            "method": "patch centres decoded from the CCI-Biomass 10-degree tile id and row/column index in each label filename, read from the zip central directory"},
                    note=f"{len(names)} AGB label patches (282 px at 100 m) with 3-5 Sentinel-3 OLCI views each; train/val/test 3000/1000/1000.")


if __name__ == "__main__":
    main()
