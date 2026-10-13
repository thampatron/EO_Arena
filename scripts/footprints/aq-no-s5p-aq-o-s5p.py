"""Footprint for Copernicus-Bench AQ-NO2-S5P / AQ-O3-S5P (Wang et al. 2025).

The data live in airquality_s5p.zip (270 MB) on Hugging Face. Rather than download it, the zip's
central directory is read with HTTP range requests, then the contiguous byte range holding the
2,467 annual NO2 S5P GeoTIFFs (~10 KB each, EPSG:3035, 51x51 px at 1.1 km) is fetched in a few
large ranges (~25 MB total) and each tile's centre is reprojected to WGS84. NO2 and O3 use the
same tile set, so one footprint covers both datasets.
"""
import io, struct, sys, time, zipfile, zlib
from pathlib import Path

import rasterio
import requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "aq-no-s5p-aq-o-s5p"
URL = "https://huggingface.co/datasets/wangyi111/Copernicus-Bench/resolve/main/l3_airquality_s5p/airquality_s5p.zip"
SESSION = requests.Session()


def get(url, **kw):
    for i in range(6):
        r = SESSION.get(url, timeout=180, **kw)
        if r.status_code != 429:
            r.raise_for_status()
            return r
        time.sleep(5 * (i + 1))
    r.raise_for_status()


class RangeFile:
    """Minimal seekable file over HTTP range requests (enough for zipfile)."""

    def __init__(self, url):
        r = get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True)
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
        b = get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}).content
        self.pos += len(b)
        return b

    def seekable(self):
        return True

    def readable(self):
        return True


def main():
    rf = RangeFile(URL)
    z = zipfile.ZipFile(rf)
    infos = sorted((i for i in z.infolist()
                    if i.filename.startswith("airquality_s5p/no2/s5p_annual/") and i.filename.endswith(".tif")),
                   key=lambda i: i.header_offset)
    start = infos[0].header_offset
    end = infos[-1].header_offset + 30 + len(infos[-1].filename.encode()) + 64 + infos[-1].compress_size
    blob = bytearray()
    step = 8 * 1024 * 1024
    for off in range(start, end, step):
        rf.seek(off)
        blob += rf.read(min(step, end - off))
    tr = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=True)
    pts = []
    for i in infos:
        o = i.header_offset - start
        nlen, xlen = struct.unpack("<HH", blob[o + 26:o + 30])
        data = bytes(blob[o + 30 + nlen + xlen:o + 30 + nlen + xlen + i.compress_size])
        if i.compress_type == zipfile.ZIP_DEFLATED:
            data = zlib.decompress(data, -15)
        with rasterio.open(io.BytesIO(data)) as src:
            bb = src.bounds
        pts.append(tr.transform((bb.left + bb.right) / 2, (bb.bottom + bb.top) / 2))
    write_footprint(DS, pts, kind="samples", n_total=len(infos),
                    source={"label": "Copernicus-Bench airquality_s5p.zip (Hugging Face)", "url": URL,
                            "method": "centre of each annual NO2 S5P GeoTIFF tile (EPSG:3035) read from the zip via HTTP range requests"},
                    note="2,467 EEA 1 km-grid tiles over Europe; identical tile set for NO2 and O3 (train/val/test 1480/493/494).")


if __name__ == "__main__":
    main()
