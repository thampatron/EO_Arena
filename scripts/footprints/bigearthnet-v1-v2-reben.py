"""BigEarthNet v2 (reBEN): patch centres decoded from the patch ids in metadata.parquet
(Hugging Face hackelle/BigEarthNetV2-LMDB, 10 MB). A patch id such as
S2A_MSIL2A_20170613T101031_N9999_R022_T33UUP_27_57 encodes the Sentinel-2 MGRS tile (T33UUP) and the
horizontal/vertical 1200 m patch index inside it; the tile's upper-left corner is derived from the MGRS 100 km
square (S2 tile UL = square origin, +100 km north). The index orientation (first = column, second = row) was
verified against the per-patch country column (70% country agreement at Natural Earth 110m vs 62% swapped)."""
import sys, re, shutil
from pathlib import Path
import requests, pandas as pd
from pyproj import Transformer
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/hackelle/BigEarthNetV2-LMDB/resolve/main/metadata.parquet"
TMP = Path("/tmp/claude-0/fp/bigearthnet-v1-v2-reben"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "metadata.parquet"
if not f.exists():
    f.write_bytes(requests.get(URL, timeout=300).content)

COLS = ["ABCDEFGH", "JKLMNPQR", "STUVWXYZ"]
ROWS = "ABCDEFGHJKLMNPQRSTUV"
BANDS = "CDEFGHJKLMNPQRSTUVWX"

def tile_ul(tile):
    """UTM EPSG and upper-left (easting, northing) of Sentinel-2 tile e.g. '33UUP'."""
    zone, band, sq = int(tile[:2]), tile[2], tile[3:5]
    e0 = (COLS[(zone - 1) % 3].index(sq[0]) + 1) * 100000
    n0 = ((ROWS.index(sq[1]) - (0 if zone % 2 else 5)) % 20) * 100000
    south = band < "N"
    epsg = (32700 if south else 32600) + zone
    lat_min, lon_c = -80 + BANDS.index(band) * 8, -183 + zone * 6
    _, nmin = Transformer.from_crs(4326, epsg, always_xy=True).transform(lon_c, lat_min)
    while n0 < nmin - 100000:
        n0 += 2000000
    return epsg, e0, n0 + 100000

d = pd.read_parquet(f, columns=["patch_id", "split"])
d["tile"] = d.patch_id.str.extract(r"_T(\d{2}[C-X][A-Z]{2})_")[0]
ij = d.patch_id.str.extract(r"_(\d+)_(\d+)$").astype(int)
d["col"], d["row"] = ij[0], ij[1]

pts = []
for t, g in d.groupby("tile"):
    epsg, e0, n0 = tile_ul(t)
    tr = Transformer.from_crs(epsg, 4326, always_xy=True)
    lon, lat = tr.transform((e0 + g.col * 1200 + 600).values, (n0 - g.row * 1200 - 600).values)
    pts += list(zip(lon, lat))

write_footprint("bigearthnet-v1-v2-reben", pts, kind="samples", n_total=549488,
                source={"label": "BigEarthNet v2 metadata.parquet (Hugging Face mirror)", "url": URL,
                        "method": "1200 m patch centres decoded from the MGRS tile and patch column/row index in each patch_id (480,038 patches in the metadata file)"},
                note="reBEN has 549,488 S1/S2 patch pairs; this metadata copy lists 480,038 patch ids over 54 Sentinel-2 tiles in 10 countries. v1 patches are a subset of the same grid.")
shutil.rmtree(TMP, ignore_errors=True)
