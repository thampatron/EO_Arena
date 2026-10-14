"""S1S2-Water footprint. The Zenodo record (11278238) is six 20-33 GB zips plus a STAC catalog.json whose items
(<n>/sentinel12_<n>_meta.json) live inside the zips. Zenodo serves HTTP range requests, so this script reads each
zip's central directory (~14 KB) and then only the tiny STAC item JSONs (a few KB each), taking each scene's
bbox centre. Transfer is well under 1 MB."""
import sys, struct, zlib, json, time
from pathlib import Path
import requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

DS = "s1s2-water"
REC = "https://zenodo.org/records/11278238/files/"
PARTS = [f"part{i}.zip" for i in range(1, 7)]


def rng(url, a, b):
    for k in range(6):  # Zenodo intermittently drops connections or returns empty bodies
        try:
            r = requests.get(url, headers={"Range": f"bytes={a}-{b}"}, allow_redirects=True, timeout=120)
            if r.status_code in (200, 206) and r.content:
                return r.content
        except requests.RequestException:
            pass
        time.sleep(2 * (k + 1))
    raise RuntimeError(f"range request failed: {url} {a}-{b}")


def zip_entries(url):
    size = int(requests.head(url, allow_redirects=True, timeout=60).headers["Content-Length"])
    tail = rng(url, size - 200000, size - 1)
    i = tail.rfind(b"PK\x06\x07")
    if i >= 0:  # zip64
        eocd64 = struct.unpack("<Q", tail[i + 8:i + 16])[0]
        e = rng(url, eocd64, eocd64 + 55)
        cd_size, cd_off = struct.unpack("<QQ", e[40:56])
    else:
        i = tail.rfind(b"PK\x05\x06")
        cd_size, cd_off = struct.unpack("<II", tail[i + 12:i + 20])
    cd = rng(url, cd_off, cd_off + cd_size - 1)
    p, out = 0, []
    while p < len(cd) and cd[p:p + 4] == b"PK\x01\x02":
        comp = struct.unpack("<H", cd[p + 10:p + 12])[0]
        csize, usize, nlen, elen, clen = struct.unpack("<IIHHH", cd[p + 20:p + 34])
        lho = struct.unpack("<I", cd[p + 42:p + 46])[0]
        name = cd[p + 46:p + 46 + nlen].decode()
        extra = cd[p + 46 + nlen:p + 46 + nlen + elen]
        q = 0
        while q + 4 <= len(extra):
            hid, hs = struct.unpack("<HH", extra[q:q + 4])
            if hid == 1:
                vals = list(struct.unpack("<" + "Q" * (hs // 8), extra[q + 4:q + 4 + hs]))
                if usize == 0xFFFFFFFF: usize = vals.pop(0)
                if csize == 0xFFFFFFFF: csize = vals.pop(0)
                if lho == 0xFFFFFFFF: lho = vals.pop(0)
            q += 4 + hs
        out.append((name, comp, csize, lho))
        p += 46 + nlen + elen + clen
    return out


def read_entry(url, comp, csize, lho):
    lh = rng(url, lho, lho + 29)
    nlen, elen = struct.unpack("<HH", lh[26:30])
    start = lho + 30 + nlen + elen
    data = rng(url, start, start + csize - 1)
    return zlib.decompress(data, -15) if comp == 8 else data


def main():
    to_ll = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    pts, ids = [], []
    for part in PARTS:
        url = REC + part + "?download=1"
        for name, comp, csize, lho in zip_entries(url):
            if not name.endswith("_meta.json"):
                continue
            item = json.loads(read_entry(url, comp, csize, lho))
            w, s, e, n = item["bbox"]  # STAC bbox is in EPSG:3857 metres in this catalog
            pts.append(to_ll.transform((w + e) / 2, (s + n) / 2)); ids.append(item["id"])
        print(f"{part}: {len(ids)} scenes so far")
    write_footprint(DS, pts, source={"label": "S1S2-Water STAC items (sentinel12_<n>_meta.json inside the Zenodo zips)",
                                     "url": "https://zenodo.org/records/11278238/files/catalog.json",
                                     "method": "bbox centres (EPSG:3857 -> WGS84) of the per-scene STAC item JSONs, read out of the zips with HTTP range requests"},
                    kind="tiles", n_total=len(pts),
                    note="One point per 100 km x 100 km Sentinel-2 tile-grid scene (S1 + S2 + DEM triplet).")


if __name__ == "__main__":
    main()
