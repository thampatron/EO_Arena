"""HLS Burn Scars footprint. The Hugging Face repo holds one 2.6 GB tar.gz with no index, but HF's auto-converted
parquet branch (refs/convert/parquet) stores each scene's filename in the `image.path` column. We read only that
column with HTTP range requests (~70 KB per parquet file) and decode the MGRS 100 km tile id embedded in the
filename (subsetted_512x512_HLS.S30.T14SME.2018138.v1.4_merged.tif -> 14SME). Points are tile centres, so the
precision is ~100 km; the 512x512 (15 km) scene lies somewhere inside that tile."""
import sys, re
from pathlib import Path
import requests, pyarrow as pa, pyarrow.parquet as pq
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

DS = "hls-burn-scars"
API = "https://datasets-server.huggingface.co/parquet?dataset=ibm-nasa-geospatial/hls_burn_scars"


class RangeFile:
    """Minimal seekable read-only file over HTTP range requests (for pyarrow.PythonFile)."""
    closed = False

    def __init__(self, url):
        self.url, self.pos, self.transferred = url, 0, 0
        self.size = int(requests.head(url, allow_redirects=True, timeout=60).headers["Content-Length"])

    def seek(self, o, w=0):
        self.pos = o if w == 0 else (self.pos + o if w == 1 else self.size + o)
        return self.pos

    def tell(self): return self.pos
    def readable(self): return True
    def seekable(self): return True
    def writable(self): return False
    def close(self): pass

    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        if n == 0: return b""
        r = requests.get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}, allow_redirects=True, timeout=120)
        r.raise_for_status()
        self.pos += len(r.content); self.transferred += len(r.content)
        return r.content


COLS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
ROWS = "ABCDEFGHJKLMNPQRSTUV"
BANDS = "CDEFGHJKLMNPQRSTUVWX"


def mgrs100k_centre(tile):
    """Centre lon/lat of an MGRS 100 km square such as '14SME'."""
    m = re.fullmatch(r"(\d{1,2})([C-X])([A-Z])([A-Z])", tile)
    zone, band, col, row = int(m[1]), m[2], m[3], m[4]
    s = (zone - 1) % 3
    easting = (COLS.index(col) - 8 * s + 1) * 100000 + 50000
    rowidx = (ROWS.index(row) - (5 if zone % 2 == 0 else 0)) % 20
    northing = rowidx * 100000 + 50000
    south = band < "N"
    epsg = (32700 if south else 32600) + zone
    to_utm = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    to_ll = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    lat_min = -80 + 8 * BANDS.index(band)
    _, n_min = to_utm.transform(-183 + 6 * zone, lat_min)  # band's southern edge on the central meridian
    while northing < n_min - 100000:
        northing += 2000000
    return to_ll.transform(easting, northing)


def main():
    files = requests.get(API, timeout=60).json()["parquet_files"]
    names, total = set(), 0
    for f in files:
        if f["split"] not in ("train", "validation"):  # test duplicates validation in this loader
            continue
        rf = RangeFile(f["url"])
        t = pq.ParquetFile(pa.PythonFile(rf, mode="r")).read(columns=["image.path"])
        paths = t.column(0).combine_chunks().field("path").to_pylist()
        total += len(paths)
        names.update(paths)
        print(f"{f['split']}/{f['filename']}: {len(paths)} rows, {rf.transferred} bytes")
    tiles = sorted({re.search(r"\.T(\d{2}[C-X][A-Z]{2})\.", n)[1] for n in names})
    pts = [mgrs100k_centre(t) for t in tiles]
    write_footprint(DS, pts, source={"label": "HLS Burn Scars parquet conversion (image.path column)",
                                     "url": "https://huggingface.co/datasets/ibm-nasa-geospatial/hls_burn_scars/tree/refs%2Fconvert%2Fparquet",
                                     "method": "MGRS 100 km tile ids parsed from scene filenames in the parquet image.path column; points are tile centres"},
                    kind="tiles", n_total=total, status="partial",
                    note=f"{total} scenes on {len(tiles)} MGRS 100 km tiles; a point marks the tile centre, not the 15 km scene, since the tar.gz has no per-scene index and reading its GeoTIFFs would mean downloading 2.6 GB.")


if __name__ == "__main__":
    main()
