"""SWED (Sentinel-2 Water Edges Dataset, UKHO) footprint.

SWED.zip (18 GB) is served without registration from the UKHO S3 bucket, so only its central directory is read
(HTTP range requests). Training chips are .npy arrays named <S2 product>_image_<row>_<col>.npy: 256 px chips cut
on a regular grid from the 10 m Sentinel-2 tile named in the product id (row/col up to 42 = 10980/256), so each
chip centre is decoded from the MGRS tile's UTM origin plus (col+0.5, row+0.5) x 2560 m. The 98 test chips are
hand-picked GeoTIFFs (EPSG:4326, ~0.5 MB each deflated) whose georeferencing is read after extracting them from
the zip (~45 MB in total). One point per chip.
"""
import io, re, struct, sys, zipfile, zlib
from pathlib import Path

import rasterio, requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "swed"
URL = "https://ukho-openmldata.s3.eu-west-2.amazonaws.com/SWED.zip"
COLS, ROWS, BANDS = "ABCDEFGHJKLMNPQRSTUVWXYZ", "ABCDEFGHJKLMNPQRSTUV", "CDEFGHJKLMNPQRSTUVWX"
CHIP_M = 256 * 10.0


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


def tile_origin(tile):
    """UTM (easting, northing) of the MGRS 100 km square's SW corner and its EPSG code; the S2 tile's UL corner is 100 km north of it."""
    m = re.fullmatch(r"(\d{1,2})([C-X])([A-Z])([A-Z])", tile)
    zone, band, col, row = int(m[1]), m[2], m[3], m[4]
    s = (zone - 1) % 3
    e = (COLS.index(col) - 8 * s + 1) * 100000
    n = ((ROWS.index(row) - (5 if zone % 2 == 0 else 0)) % 20) * 100000
    epsg = (32700 if band < "N" else 32600) + zone
    _, n_min = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True).transform(-183 + 6 * zone, -80 + 8 * BANDS.index(band))
    while n < n_min - 100000:
        n += 2000000
    return e, n, epsg


def member_bytes(rf, info):
    rf.seek(info.header_offset)
    nlen, xlen = struct.unpack("<HH", rf.read(30)[26:30])
    rf.seek(info.header_offset + 30 + nlen + xlen)
    d = rf.read(info.compress_size)
    return zlib.decompress(d, -15) if info.compress_type == zipfile.ZIP_DEFLATED else d


def main():
    rf = RangeFile(URL)
    infos = zipfile.ZipFile(rf).infolist()
    train = [i.filename for i in infos if i.filename.startswith("SWED/train/images/") and i.filename.endswith(".npy")]
    test = [i for i in infos if i.filename.startswith("SWED/test/images/") and i.filename.endswith(".tif")]
    pts, tr_cache = [], {}
    for name in train:
        m = re.search(r"_T(\d{2}[C-X][A-Z]{2})_.*_image_(\d+)_(\d+)\.npy$", name)
        e, n, epsg = tile_origin(m[1])
        r, c = int(m[2]), int(m[3])
        tr = tr_cache.setdefault(epsg, Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True))
        pts.append(tr.transform(e + (c + 0.5) * CHIP_M, n + 100000 - (r + 0.5) * CHIP_M))
    for i in test:
        with rasterio.open(io.BytesIO(member_bytes(rf, i))) as s:
            b = s.bounds
            lon, lat = (b.left + b.right) / 2, (b.bottom + b.top) / 2
            if s.crs and s.crs.to_epsg() != 4326:
                lon, lat = Transformer.from_crs(s.crs, "EPSG:4326", always_xy=True).transform(lon, lat)
            pts.append((lon, lat))
    write_footprint(DS, pts, kind="samples", n_total=len(train) + len(test),
                    source={"label": "SWED.zip file listing (UKHO S3) + test GeoTIFF headers", "url": "https://openmldata.ukho.gov.uk/",
                            "method": "train chip centres decoded from the Sentinel-2 tile id and grid row/col in each filename; test chip centres from their GeoTIFF bounds"},
                    note=f"{len(train)} training chips on 16 Sentinel-2 tiles (grid position inferred from the filename index, not from georeferencing, since the chips are .npy) and {len(test)} hand-picked test chips.")


if __name__ == "__main__":
    main()
