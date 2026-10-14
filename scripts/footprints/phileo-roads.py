"""PhilEO downstream dataset, roads task (Fibaek et al. 2024) footprint.

The data sit in a 10-part split zip on Hugging Face (PhilEO-community/PhilEO-downstream, downstream_dataset_tifszip.*,
~150 GB). Only the zip central directory (1.2 MB at the end of the last part) is read to list the 9,500 members;
tile names (<region>_<n>_<t>.tif) carry no coordinates, so for an even subsample of up to 300 of the 846 tiles that
have a _label_roads.tif, the first 32 KB of the deflated Sentinel-2 image member are fetched from the right zip
part and inflated: GDAL-written GeoTIFFs keep the IFD at the start, so rasterio reads the CRS and bounds from the
truncated buffer. Points are tile centres (2500 x 2500 px at 10 m, i.e. 25 km tiles).
"""
import io, re, struct, sys, time, zlib
from pathlib import Path

import rasterio, requests
from rasterio.warp import transform

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "phileo-roads"
BASE = "https://huggingface.co/datasets/PhilEO-community/PhilEO-downstream/resolve/main/data/downstream_dataset_tifszip."
LAST_DISK = 9
CAP = 300
HEAD = 32768
_urls = {}


def get(url, **kw):
    for i in range(8):
        r = requests.get(url, timeout=120, allow_redirects=True, **kw)
        if r.status_code not in (429, 500, 502, 503, 504):
            r.raise_for_status()
            return r
        time.sleep(10 * (i + 1))
    r.raise_for_status()


def part_url(disk):
    if disk not in _urls:
        _urls[disk] = get(BASE + ("zip" if disk == LAST_DISK else f"z{disk + 1:02d}"), headers={"Range": "bytes=0-0"}).url
    return _urls[disk]


def central_directory():
    r = get(BASE + "zip", headers={"Range": "bytes=0-0"})
    size = int(r.headers["Content-Range"].split("/")[-1])
    tail = get(r.url, headers={"Range": f"bytes={size - 65536}-{size - 1}"}).content
    j = tail.rfind(b"PK\x06\x06")
    if j >= 0:
        z = struct.unpack("<IQHHIIQQQQ", tail[j:j + 56])
        cd_size, cd_off = z[8], z[9]
    else:
        e = struct.unpack("<IHHHHIIH", tail[tail.rfind(b"PK\x05\x06"):][:22])
        cd_size, cd_off = e[5], e[6]
    cd = get(r.url, headers={"Range": f"bytes={cd_off}-{cd_off + cd_size - 1}"}).content
    ents, p = [], 0
    while p < len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        (_, _, _, _, meth, _, _, _, csz, usz, n, m, k, disk, _, _, lho) = struct.unpack("<IHHHHHHIIIHHHHHII", cd[p:p + 46])
        name, extra = cd[p + 46:p + 46 + n].decode(), cd[p + 46 + n:p + 46 + n + m]
        q = 0
        while q + 4 <= len(extra):
            hid, hs = struct.unpack("<HH", extra[q:q + 4])
            if hid == 1:
                body, b = extra[q + 4:q + 4 + hs], 0
                if usz == 0xFFFFFFFF:
                    usz, b = struct.unpack("<Q", body[b:b + 8])[0], b + 8
                if csz == 0xFFFFFFFF:
                    csz, b = struct.unpack("<Q", body[b:b + 8])[0], b + 8
                if lho == 0xFFFFFFFF:
                    lho, b = struct.unpack("<Q", body[b:b + 8])[0], b + 8
                if disk == 0xFFFF:
                    disk = struct.unpack("<I", body[b:b + 4])[0]
            q += 4 + hs
        ents.append((name, meth, csz, disk, lho))
        p += 46 + n + m + k
    return ents


def tile_centre(ent):
    name, meth, csz, disk, lho = ent
    u = part_url(disk)
    h = get(u, headers={"Range": f"bytes={lho}-{lho + 29}"}).content
    n, m = struct.unpack("<HH", h[26:30])
    start = lho + 30 + n + m
    c = get(u, headers={"Range": f"bytes={start}-{start + min(HEAD, csz) - 1}"}).content
    d = zlib.decompressobj(-15).decompress(c) if meth == 8 else c
    with rasterio.open(io.BytesIO(d)) as s:
        b = s.bounds
        lon, lat = transform(s.crs, "EPSG:4326", [(b.left + b.right) / 2], [(b.bottom + b.top) / 2])
    return (lon[0], lat[0])


def main():
    ents = central_directory()
    roads = {re.search(r"/([a-z\-]+\d*_\d+)_label_roads\.tif$", e[0])[1] for e in ents if e[0].endswith("_label_roads.tif")}
    imgs = {m[1]: e for e in ents if (m := re.search(r"/([a-z\-]+\d*_\d+)_0\.tif$", e[0]))}
    tiles = sorted(t for t in roads if t in imgs)
    step = max(1, len(tiles) // CAP)
    sample = tiles[::step][:CAP]
    pts = []
    for t in sample:
        try:
            pts.append(tile_centre(imgs[t]))
        except Exception as e:
            print("skip", t, e)
    write_footprint(DS, pts, kind="tiles", n_total=len(tiles), status="partial",
                    source={"label": "PhilEO-downstream split zip on Hugging Face (central directory + GeoTIFF headers)",
                            "url": "https://huggingface.co/datasets/PhilEO-community/PhilEO-downstream/tree/main/data",
                            "method": f"tile centres from the GeoTIFF headers of an even {len(sample)}-of-{len(tiles)} subsample of the road-labelled 25 km Sentinel-2 tiles, inflating only the first 32 KB of each zip member"},
                    note=f"{len(tiles)} tiles carry a road-density label (of 1,392 PhilEO downstream tiles across east-africa, nigeria, europe, south-america, north-america, ghana, senegal, japan, denmark, egypt, ...). Region names only in file names; coordinates read from headers.")


if __name__ == "__main__":
    main()
