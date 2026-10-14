"""TimeSen2Crop: the 1.2 M pixel time series are stored as <tile>/<class>/<n>.csv with no coordinates, so only the
Sentinel-2 (MGRS) tile of each sample is known. Tile ids and per-tile sample counts are read from the central
directory of TimeSen2Crop.zip on Zenodo (HTTP range requests, ~40 MB of directory, no data); each tile is reduced to
the centre of its 100 km MGRS square (status partial). The dataset covers Austria, not Slovenia."""
import sys, io, time, zipfile, collections
from pathlib import Path
import requests
from pyproj import Transformer
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

RECORD = "https://zenodo.org/records/4715631"
URL = "https://zenodo.org/api/records/4715631/files/TimeSen2Crop.zip/content"

COLS = {1: "ABCDEFGH", 2: "JKLMNPQR", 0: "STUVWXYZ"}
ROWS = "ABCDEFGHJKLMNPQRSTUV"
BANDS = "CDEFGHJKLMNPQRSTUVWX"
def s2_tile_origin(tile):
    """(epsg, ulx, uly) of a Sentinel-2 MGRS tile such as '31TCF' (100 km square corner, +-20 m vs the real S2 grid)."""
    tile = tile.upper().lstrip("T")
    zone, band, col, row = int(tile[:2]), tile[2], tile[3], tile[4]
    epsg = (32700 if band < "N" else 32600) + zone
    e_min = 100000 * (COLS[zone % 3].index(col) + 1)
    rows = ROWS if zone % 2 else ROWS[5:] + ROWS[:5]
    n_base = 100000 * rows.index(row)
    bi = BANDS.index(band); lat_min = -80 + 8 * bi; lat_max = lat_min + (12 if band == "X" else 8)
    tr = Transformer.from_crs(4326, epsg, always_xy=True)
    _, n_lo = tr.transform(zone * 6 - 183, lat_min); _, n_hi = tr.transform(zone * 6 - 183, lat_max)
    best = None
    for k in range(6):
        n = n_base + k * 2000000; mid = n + 50000
        d = 0 if n_lo - 100000 <= mid <= n_hi + 100000 else min(abs(mid - n_lo), abs(mid - n_hi))
        if best is None or d < best[0]: best = (d, n)
    return epsg, e_min, best[1] + 100000


def fetch_range(session, url, a, b):
    for i in range(8):  # retry on throttling / transient errors
        try:
            r = session.get(url, headers={"Range": f"bytes={a}-{b}"}, timeout=120)
            if r.status_code == 206: return r
        except requests.RequestException:
            pass
        time.sleep(5 * (i + 1))
    raise IOError(f"no partial content for {url}")


class HttpFile(io.RawIOBase):
    """Minimal seekable read-only file over HTTP range requests (for zipfile)."""
    def __init__(self, url, session):
        self.url, self.s, self.pos = url, session, 0
        r = fetch_range(session, url, 0, 0)
        self.size = int(r.headers["Content-Range"].split("/")[-1])
        self.url = r.url  # resolved URL, so later reads skip the redirect
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]; return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0: return b""
        r = fetch_range(self.s, self.url, self.pos, self.pos + n - 1)
        self.pos += len(r.content); return r.content
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


zf = zipfile.ZipFile(HttpFile(URL, requests.Session()))
counts = collections.Counter()
for n in zf.namelist():
    if n.endswith(".csv") and n.split("/")[-1] != "dates.csv":
        counts[n.split("/")[1]] += 1
pts = []
for tile in counts:
    epsg, ulx, uly = s2_tile_origin(tile.split("_")[-1])
    pts.append(Transformer.from_crs(epsg, 4326, always_xy=True).transform(ulx + 50000, uly - 50000))
write_footprint("timesen2crop", pts, kind="tiles", n_total=sum(counts.values()), status="partial",
                source={"label": "TimeSen2Crop.zip directory (Zenodo)", "url": RECORD,
                        "method": "centre of the MGRS 100 km square of each Sentinel-2 tile folder in the zip; per-pixel coordinates are not published"},
                note=f"{sum(counts.values()):,} labelled pixel time series in {len(counts)} tile folders over Austria (2017-18 agronomic year, plus a 2019 33UVP set): "
                     + ", ".join(f"{k} {v:,}" for k, v in counts.most_common()) + ".")
