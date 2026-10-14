"""Footprint for BRIGHT (Chen et al. 2025), Hugging Face Kullervo/BRIGHT.

target.zip (47 MB) holds one georeferenced 1024x1024 building-damage label GeoTIFF per tile
(UTM CRS). The zip is read with HTTP range requests, the head of each deflated member is
decompressed far enough to parse the GeoTIFF header, and each tile centre is reprojected to WGS84.
"""
import io, re, struct, sys, time, zipfile, zlib
from pathlib import Path

import rasterio
import requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "bright"
URL = "https://huggingface.co/datasets/Kullervo/BRIGHT/resolve/main/target.zip"
SESSION = requests.Session()


def get(url, **kw):
    for i in range(6):
        r = SESSION.get(url, timeout=300, **kw)
        if r.status_code != 429:
            r.raise_for_status()
            return r
        time.sleep(5 * (i + 1))
    r.raise_for_status()


class RangeFile:
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
    infos = sorted((i for i in z.infolist() if i.filename.endswith(".tif")), key=lambda i: i.header_offset)
    start, end = infos[0].header_offset, rf.size
    blob = bytearray()
    step = 8 * 1024 * 1024
    for off in range(start, end, step):
        rf.seek(off)
        blob += rf.read(min(step, end - off))
    pts, events, cache = [], set(), {}
    for i in infos:
        o = i.header_offset - start
        nlen, xlen = struct.unpack("<HH", blob[o + 26:o + 30])
        s = o + 30 + nlen + xlen
        data = bytes(blob[s:s + i.compress_size])
        if i.compress_type == zipfile.ZIP_DEFLATED:
            data = zlib.decompressobj(-15).decompress(data[:65536])  # header only
        with rasterio.open(io.BytesIO(data)) as src:
            bb, epsg = src.bounds, src.crs.to_epsg()
        if epsg not in cache:
            cache[epsg] = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        pts.append(cache[epsg].transform((bb.left + bb.right) / 2, (bb.bottom + bb.top) / 2))
        events.add(re.sub(r"_\d{6,}.*$", "", i.filename.split("/")[-1]))
    write_footprint(DS, pts, kind="samples", n_total=len(infos),
                    source={"label": "BRIGHT target.zip label GeoTIFFs (Hugging Face)", "url": URL,
                            "method": "centre of each georeferenced building-damage label tile, read from the zip via HTTP range requests"},
                    note=f"{len(infos)} 1024x1024 tiles over {len(events)} events: {', '.join(sorted(events))}.")


if __name__ == "__main__":
    main()
