"""SPARCS (USGS, 80 Landsat 8 1000x1000 px subscenes): the only distribution is l8cloudmasks.zip (1.55 GB) on
landsat.usgs.gov. The zip's central directory is fetched with an HTTP suffix range to list the 80
<scene id>_<n>_data.tif entries (stored uncompressed). For entries in the first ~600 MB of the archive the
GeoTIFF IFD (last ~1 KB of the entry) is range-fetched and the exact subscene centre is computed; the USGS edge
blocks range requests with offsets beyond ~600 MB, so the remaining subscenes fall back to the centre of the
parent Landsat 8 scene (WRS-2 path/row + acquisition date, decoded from the scene id and resolved through the
Planetary Computer landsat-c2-l2 STAC). Total transfer well under 1 MB."""
import sys, re, struct, zipfile, datetime, io
from pathlib import Path
import requests
from rasterio.io import MemoryFile
from rasterio.warp import transform
from pystac_client import Client
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://landsat.usgs.gov/cloud-validation/sparcs/l8cloudmasks.zip"
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0"
LIMIT = 590_000_000

def rng(spec):
    r = S.get(URL, headers={"Range": f"bytes={spec}"}, timeout=120)
    if r.status_code != 206:
        raise RuntimeError(f"range {spec}: HTTP {r.status_code}")
    return r.content

size = int(S.head(URL, timeout=60).headers["Content-Length"])
tail = rng("-65536")
# parse the central directory from the tail using zipfile on a padded buffer
buf = io.BytesIO(bytes(size - len(tail)) + tail)
entries = [(i.filename, i.header_offset, i.compress_size, i.compress_type) for i in zipfile.ZipFile(buf).infolist()
           if i.filename.endswith("_data.tif")]
assert len(entries) == 80, len(entries)

cat = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
pts, exact, coarse = [], 0, 0
for name, off, csize, ctype in entries:
    sid = re.search(r"(LC8\d{13}LGN\d\d)", name).group(1)
    d0 = off + 30 + len(name.encode())
    if ctype == zipfile.ZIP_STORED and d0 + csize < LIMIT:
        h = rng(f"{d0}-{d0 + 7}")
        ifd = struct.unpack("<I", h[4:8])[0]
        t = rng(f"{d0 + ifd}-{d0 + csize - 1}")
        with MemoryFile(h + bytes(ifd - 8) + t) as mf, mf.open() as src:
            b = src.bounds
            lon, lat = transform(src.crs, "EPSG:4326", [(b.left + b.right) / 2], [(b.bottom + b.top) / 2])
            pts.append((lon[0], lat[0])); exact += 1
    else:
        path, row, year, doy = sid[3:6], sid[6:9], int(sid[9:13]), int(sid[13:16])
        d = datetime.date(year, 1, 1) + datetime.timedelta(days=doy - 1)
        items = list(cat.search(collections=["landsat-c2-l2"], datetime=f"{d}/{d + datetime.timedelta(days=1)}",
                                query={"landsat:wrs_path": {"eq": path}, "landsat:wrs_row": {"eq": row}}, limit=2).items())
        if not items:
            items = list(cat.search(collections=["landsat-c2-l2"], query={"landsat:wrs_path": {"eq": path}, "landsat:wrs_row": {"eq": row}}, limit=1).items())
        if items:
            w, s_, e, n = items[0].bbox
            pts.append(((w + e) / 2, (s_ + n) / 2)); coarse += 1

write_footprint("sparcs", pts, kind="tiles", n_total=80, status="partial",
                source={"label": "USGS SPARCS l8cloudmasks.zip (entry list + GeoTIFF headers via HTTP ranges) and Planetary Computer Landsat STAC", "url": URL,
                        "method": f"exact 30 km subscene centres from the GeoTIFF IFD for {exact} subscenes; parent Landsat 8 scene centres (WRS-2 path/row + date via STAC) for {coarse}"},
                note="Subscenes are 1000x1000 px (30 km) crops of 80 Landsat 8 scenes, 2013-2014, worldwide. The USGS server refuses byte-range requests beyond ~600 MB into the archive, so later entries use the parent scene centre (within ~90 km of the subscene).")
