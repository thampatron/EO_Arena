"""Footprint for Copernicus-Bench Cloud-S3 (Wang et al. 2025), Sentinel-3 OLCI cloud segmentation.

The data live in cloud_s3.zip (7 GB) on Hugging Face. Rather than download it, the zip's central
directory is read with HTTP range requests, then the contiguous byte range holding the 1,995
cloud_multi label GeoTIFFs (~0.5 KB compressed each, EPSG:4326, 256x256 px) is fetched (~1 MB)
and each tile's centre taken from its bounds.
"""
import io, struct, sys, time, zipfile, zlib
from pathlib import Path

import rasterio
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "cloud-s3"
URL = "https://huggingface.co/datasets/wangyi111/Copernicus-Bench/resolve/main/l1_cloud_s3/cloud_s3.zip"
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
                    if i.filename.startswith("cloud_s3/cloud_multi/") and i.filename.endswith(".tif")),
                   key=lambda i: i.header_offset)
    start = infos[0].header_offset
    end = infos[-1].header_offset + 30 + len(infos[-1].filename.encode()) + 64 + infos[-1].compress_size
    blob = bytearray()
    step = 8 * 1024 * 1024
    for off in range(start, end, step):
        rf.seek(off)
        blob += rf.read(min(step, end - off))
    pts = []
    for i in infos:
        o = i.header_offset - start
        nlen, xlen = struct.unpack("<HH", blob[o + 26:o + 30])
        data = bytes(blob[o + 30 + nlen + xlen:o + 30 + nlen + xlen + i.compress_size])
        if i.compress_type == zipfile.ZIP_DEFLATED:
            data = zlib.decompress(data, -15)
        with rasterio.open(io.BytesIO(data)) as src:
            bb = src.bounds
            assert src.crs.to_epsg() == 4326
        pts.append(((bb.left + bb.right) / 2, (bb.bottom + bb.top) / 2))
    write_footprint(DS, pts, kind="samples", n_total=len(infos),
                    source={"label": "Copernicus-Bench cloud_s3.zip (Hugging Face)", "url": URL,
                            "method": "centre of each cloud_multi label GeoTIFF (EPSG:4326) read from the zip via HTTP range requests"},
                    note="1,995 Sentinel-3 OLCI 256x256 patches (train/val/test 1197/399/399), global.")


if __name__ == "__main__":
    main()
