"""Footprint for MMFlood (Montello et al. 2022), Zenodo 6534637.

mmflood.zip (11 GB) stores one mask GeoTIFF per tile (EPSG:4326, ~5-6 KB each with Deflate64 zip
compression) under mmflood/<activation>/mask/. The zip's central directory is read with HTTP range
requests; then, per activation, the contiguous byte span of its mask members is fetched in one request
(~10 MB in total for all 1,748 tiles), each member is inflated with the inflate64 package (Deflate64 is not
supported by zlib) and rasterio reads the tile bounds. Tile centres are the footprint. If inflate64 is
missing, the script falls back to the per-activation points of data/activations.json in the code repo.
"""
import io, struct, sys, time, zipfile
from collections import defaultdict
from pathlib import Path

import rasterio
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "mmflood"
URL = "https://zenodo.org/records/6534637/files/mmflood.zip?download=1"
ACT_URL = "https://raw.githubusercontent.com/edornd/mmflood/main/data/activations.json"
SESSION = requests.Session()


def get(url, **kw):
    for i in range(8):
        try:
            r = SESSION.get(url, timeout=180, **kw)
            if r.status_code in (200, 206):
                return r
        except requests.RequestException:
            pass
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"request failed repeatedly: {url[:80]}")


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


def fallback_sites():
    d = get(ACT_URL).json()
    pts = [(v["lon"], v["lat"]) for v in d.values() if v.get("lat") is not None]
    write_footprint(DS, pts, kind="sites", n_total=1748, status="partial",
                    source={"label": "mmflood/data/activations.json (GitHub)", "url": ACT_URL,
                            "method": "one representative lat/lon per Copernicus EMS activation (inflate64 not installed, zip members not readable)"},
                    note=f"{len(d)} activations, one point each.")


def main():
    try:
        import inflate64
    except ImportError:
        return fallback_sites()
    rf = RangeFile(URL)
    z = zipfile.ZipFile(rf)
    by_act = defaultdict(list)
    for i in z.infolist():
        p = i.filename.split("/")
        if len(p) == 4 and p[2] == "mask" and p[3].endswith(".tif"):
            by_act[p[1]].append(i)
    pts, n_total, failed = [], 0, 0
    for act, items in sorted(by_act.items()):
        items.sort(key=lambda i: i.header_offset)
        start = items[0].header_offset
        end = items[-1].header_offset + 30 + len(items[-1].filename) + 512 + items[-1].compress_size
        blob = get(rf.url, headers={"Range": f"bytes={start}-{end}"}).content
        for i in items:
            n_total += 1
            o = i.header_offset - start
            nlen, xlen = struct.unpack("<HH", blob[o + 26:o + 30])
            s = o + 30 + nlen + xlen
            data = blob[s:s + i.compress_size]
            try:
                if i.compress_type == 9:
                    data = inflate64.Inflater().inflate(data)
                elif i.compress_type == zipfile.ZIP_DEFLATED:
                    import zlib
                    data = zlib.decompressobj(-15).decompress(data)
                with rasterio.open(io.BytesIO(data)) as src:
                    b = src.bounds
                    assert src.crs.to_epsg() == 4326
                pts.append(((b.left + b.right) / 2, (b.bottom + b.top) / 2))
            except Exception:
                failed += 1
    write_footprint(DS, pts, kind="samples", n_total=n_total,
                    source={"label": "mmflood.zip mask GeoTIFFs (Zenodo)", "url": "https://zenodo.org/records/6534637",
                            "method": "centre of every flood-mask GeoTIFF tile (EPSG:4326), members read from the zip via HTTP range requests and Deflate64-inflated"},
                    note=f"{len(pts)} tiles across {len(by_act)} Copernicus EMS activation parts (95 activations, 2014-2021)."
                         + (f" {failed} tiles unreadable." if failed else ""))


if __name__ == "__main__":
    main()
