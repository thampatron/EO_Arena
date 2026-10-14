"""Sen4AgriNet (S4A): patch centres decoded from the patch ids (<year>_<S2 tile>_patch_<row>_<col>) listed in the TACO
repackaging's sample index (isp-uv-es/sen4agrinet-taco, .tacocat/sample.parquet, 319 kB). Patches are 366x366 px at 10 m
on a 30x30 grid per Sentinel-2 tile; the tile's upper-left corner is derived from the MGRS id."""
import sys, io
from pathlib import Path
import requests, pyarrow.parquet as pq
from pyproj import Transformer
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/isp-uv-es/sen4agrinet-taco/resolve/main/.tacocat/sample.parquet"

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

r = requests.get(URL, timeout=120); r.raise_for_status()
t = pq.read_table(io.BytesIO(r.content)).to_pandas()
PATCH = 366 * 10
pts, cache, seen = [], {}, set()
for tile, name in zip(t["ml:tile"], t["ml:patch_name"]):
    row, col = map(int, name.split("_")[1:3])
    key = (tile, row, col)
    if key in seen: continue  # same grid cell in 2019 and 2020
    seen.add(key)
    if tile not in cache:
        epsg, ulx, uly = s2_tile_origin(tile)
        cache[tile] = (ulx, uly, Transformer.from_crs(epsg, 4326, always_xy=True))
    ulx, uly, tr = cache[tile]
    pts.append(tr.transform(ulx + (col + 0.5) * PATCH, uly - (row + 0.5) * PATCH))
write_footprint("sen4agrinet", pts, kind="samples", n_total=len(t),
                source={"label": "Sen4AgriNet patch index (isp-uv-es/sen4agrinet-taco sample.parquet)", "url": URL,
                        "method": "patch centre from <tile>_patch_<row>_<col>: S2 tile corner (MGRS id) + 3.66 km x (index + 0.5); 2019/2020 duplicates of the same cell merged"},
                note=f"{len(t)} patch-years (Catalonia 2019-20, France 2019) over {len(pts)} distinct grid cells in 11 S2 tiles; the original release also has Catalonia 2016-18 on the same grid.")
