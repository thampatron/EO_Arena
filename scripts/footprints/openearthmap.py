"""Footprint for OpenEarthMap (Xia et al. 2023, WACV), Zenodo 7223446.

OpenEarthMap.zip (9.1 GB) holds 97 region folders with georeferenced 1024x1024 label GeoTIFFs (UTM). The
zip's central directory is read with HTTP range requests; then, for a stratified sample of labels (3 per
region, 300 max), the first 8 KB of each deflated member is fetched and decompressed, which is enough for
rasterio to parse the GeoTIFF header. Tile centres are reprojected to WGS84. Total transfer ~3 MB.
"""
import io, struct, sys, time, zipfile, zlib
from collections import defaultdict
from pathlib import Path

import rasterio
import requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "openearthmap"
URL = "https://zenodo.org/records/7223446/files/OpenEarthMap.zip?download=1"
PER_REGION, CAP, HEAD = 3, 300, 8192
SESSION = requests.Session()


def get(url, **kw):
    for i in range(8):
        try:
            r = SESSION.get(url, timeout=120, **kw)
            if r.status_code in (200, 206):
                return r
        except requests.RequestException:  # transient SSL EOF / resets from Zenodo
            r = None
        time.sleep(2 * (i + 1))
    if r is None:
        raise RuntimeError("request failed repeatedly")
    r.raise_for_status()


class RangeFile:
    def __init__(self, url):
        r = get(url, headers={"Range": "bytes=0-0"})
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


def tile_centre(rf, info, cache):
    o = info.header_offset
    blob = get(rf.url, headers={"Range": f"bytes={o}-{o + 30 + len(info.filename) + 512 + HEAD}"}).content
    nlen, xlen = struct.unpack("<HH", blob[26:30])
    data = blob[30 + nlen + xlen:30 + nlen + xlen + min(info.compress_size, HEAD)]
    if info.compress_type == zipfile.ZIP_DEFLATED:
        data = zlib.decompressobj(-15).decompress(data)
    with rasterio.open(io.BytesIO(data)) as src:
        bb, key = src.bounds, src.crs.to_epsg() or src.crs.to_wkt()  # Polish tiles carry a non-EPSG WKT (PL-1992)
    if key not in cache:
        cache[key] = Transformer.from_crs(f"EPSG:{key}" if isinstance(key, int) else key, "EPSG:4326", always_xy=True)
    return cache[key].transform((bb.left + bb.right) / 2, (bb.bottom + bb.top) / 2)


def main():
    rf = RangeFile(URL)
    z = zipfile.ZipFile(rf)
    by_region = defaultdict(list)
    for i in z.infolist():
        p = i.filename.split("/")
        if len(p) == 4 and p[2] == "labels" and p[3].endswith(".tif"):
            by_region[p[1]].append(i)
    n_total = sum(len(v) for v in by_region.values())
    picks = []
    for region in sorted(by_region):
        items = sorted(by_region[region], key=lambda i: i.filename)
        step = max(1, len(items) // PER_REGION)
        picks += items[::step][:PER_REGION]
    picks = picks[:CAP]
    pts, cache, failed = [], {}, 0
    for info in picks:
        try:
            pts.append(tile_centre(rf, info, cache))
        except Exception:
            failed += 1
    write_footprint(DS, pts, kind="samples", n_total=n_total, status="partial",
                    source={"label": "OpenEarthMap.zip label GeoTIFF headers (Zenodo)", "url": "https://zenodo.org/records/7223446",
                            "method": "centre of a stratified sample of label GeoTIFFs (3 per region) whose headers were read from the zip via HTTP range requests"},
                    note=f"{len(pts)} of {n_total} label tiles sampled across {len(by_region)} region folders (the 5,000-image count includes "
                         f"xBD-derived RGB images not in the zip); all tiles georeferenced in UTM." + (f" {failed} header reads failed." if failed else ""))


if __name__ == "__main__":
    main()
