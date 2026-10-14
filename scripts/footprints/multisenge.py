"""MultiSenGE: patch centres decoded from the label file names {S2tile}_{x-pixel}_{y-pixel}.json in labels.zip on the
Zenodo record (8,157 patches of 256x256 px at 10 m). The pixel offset is relative to the Sentinel-2 tile's upper-left corner,
whose UTM coordinates are derived from the MGRS tile id."""
import sys, shutil, zipfile
from pathlib import Path
import requests
from pyproj import Transformer
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://zenodo.org/api/records/6375466/files/labels.zip/content"
TMP = Path("/tmp/claude-0/fp/multisenge"); TMP.mkdir(parents=True, exist_ok=True)

COLS = {1: "ABCDEFGH", 2: "JKLMNPQR", 0: "STUVWXYZ"}
ROWS = "ABCDEFGHJKLMNPQRSTUV"
BANDS = "CDEFGHJKLMNPQRSTUVWX"
def s2_tile_origin(tile):
    """(epsg, ulx, uly) of a Sentinel-2 MGRS tile such as '31UFQ' (100 km square corner, +-20 m vs the real S2 grid)."""
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

f = TMP / "labels.zip"
if not f.exists():
    r = requests.get(URL, timeout=300); r.raise_for_status(); f.write_bytes(r.content)
names = [n.split("/")[-1] for n in zipfile.ZipFile(f).namelist() if n.endswith(".json")]
pts, cache = [], {}
for n in names:
    tile, x, y = n[:-5].split("_"); x, y = int(x), int(y)
    if tile not in cache:
        epsg, ulx, uly = s2_tile_origin(tile)
        cache[tile] = (ulx, uly, Transformer.from_crs(epsg, 4326, always_xy=True))
    ulx, uly, tr = cache[tile]
    pts.append(tr.transform(ulx + (x + 128) * 10, uly - (y + 128) * 10))
write_footprint("multisenge", pts, kind="samples", n_total=len(names),
                source={"label": "MultiSenGE labels.zip (Zenodo 6375466)", "url": "https://zenodo.org/records/6375466",
                        "method": "patch centre = S2 tile upper-left corner (from the MGRS tile id) + 10 m x (pixel offset + 128), decoded from the label file names"})
shutil.rmtree(TMP, ignore_errors=True)
