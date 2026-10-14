"""Kruitwagen et al. 2021 global solar PV inventory footprint.

Zenodo record 5005868 holds predicted_set.geojson (the 68,661 facility polygons) as a 274 MB file, but the
same file sits deflated to 74 MB inside global_pv_inventory_all.zip. Only that member is fetched (one HTTP
range request on the zip), decompressed to a temp file, and each facility's centroid is taken. Temp files are
deleted afterwards.
"""
import json, shutil, struct, sys, zipfile, zlib
from pathlib import Path

import requests
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "kruitwagen-et-al-2021-solar-inventory"
ZIP = "https://zenodo.org/api/records/5005868/files/global_pv_inventory_all.zip/content"
MEMBER = "predicted_set.geojson"
TMP = Path("/tmp/claude-0/fp") / DS


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
        r = requests.get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}, timeout=600, stream=True)
        r.raise_for_status()
        b = r.content
        self.pos += len(b)
        return b

    def seekable(self):
        return True

    def readable(self):
        return True


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    out = TMP / MEMBER
    rf = RangeFile(ZIP)
    info = zipfile.ZipFile(rf).getinfo(MEMBER)
    rf.seek(info.header_offset)
    nlen, xlen = struct.unpack("<HH", rf.read(30)[26:30])
    rf.seek(info.header_offset + 30 + nlen + xlen)
    d = zlib.decompressobj(-15)
    with out.open("wb") as f:
        remaining = info.compress_size
        while remaining > 0:
            chunk = rf.read(min(16 * 1024 * 1024, remaining))
            remaining -= len(chunk)
            f.write(d.decompress(chunk))
        f.write(d.flush())
    with out.open(encoding="utf-8") as f:
        feats = json.load(f)["features"]
    pts = []
    for ft in feats:
        try:
            c = shape(ft["geometry"]).centroid
            pts.append((c.x, c.y))
        except Exception:
            pass
    shutil.rmtree(TMP, ignore_errors=True)
    write_footprint(DS, pts, kind="samples", n_total=len(feats),
                    source={"label": "Zenodo 5005868, predicted_set.geojson (inside global_pv_inventory_all.zip)",
                            "url": "https://zenodo.org/records/5005868",
                            "method": "centroid of every predicted PV facility polygon in predicted_set.geojson, extracted from the zip with one range request"},
                    note=f"{len(feats)} facility polygons in the predicted set (the ML-detected inventory, not the hand-labelled training polygons).")


if __name__ == "__main__":
    main()
