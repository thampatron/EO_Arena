"""Footprint for EuroCropsML (Reuss et al. 2025), Zenodo 15095445.

preprocess.zip (1.4 GB) holds one small .npz per parcel (706,683 files) with a 'center' array
([lon, lat] of the parcel centroid). The zip's central directory is read with HTTP range requests;
members are stored in random order (countries/regions interleaved), so three contiguous windows
of 1,000 members (~7 MB in total) are fetched as a random sample and their centres decoded.
"""
import io, struct, sys, zipfile, zlib
from pathlib import Path

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "eurocropsml"
URL = "https://zenodo.org/records/15095445/files/preprocess.zip?download=1"
SESSION = requests.Session()
WINDOWS, PER_WINDOW = 3, 1000


class RangeFile:
    def __init__(self, url):
        r = SESSION.get(url, headers={"Range": "bytes=0-0"}, timeout=120)
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
        r = SESSION.get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}, timeout=600)
        r.raise_for_status()
        self.pos += len(r.content)
        return r.content

    def seekable(self):
        return True

    def readable(self):
        return True


def main():
    rf = RangeFile(URL)
    z = zipfile.ZipFile(rf)
    infos = sorted((i for i in z.infolist() if i.filename.endswith(".npz")), key=lambda i: i.header_offset)
    n_total = len(infos)
    pts, countries = [], set()
    for w in range(WINDOWS):
        k = w * n_total // WINDOWS
        chunk = infos[k:k + PER_WINDOW]
        start = chunk[0].header_offset
        last = chunk[-1]
        end = last.header_offset + 30 + len(last.filename.encode()) + 64 + last.compress_size
        rf.seek(start)
        blob = rf.read(end - start)
        for i in chunk:
            o = i.header_offset - start
            nlen, xlen = struct.unpack("<HH", blob[o + 26:o + 30])
            s = o + 30 + nlen + xlen
            data = bytes(blob[s:s + i.compress_size])
            if i.compress_type == zipfile.ZIP_DEFLATED:
                data = zlib.decompress(data, -15)
            c = np.load(io.BytesIO(data))["center"]
            pts.append((float(c[0]), float(c[1])))
            countries.add(Path(i.filename).name[:2])
    write_footprint(DS, pts, kind="samples", n_total=n_total,
                    source={"label": "EuroCropsML preprocess.zip per-parcel .npz 'center' (Zenodo 15095445)", "url": URL,
                            "method": f"parcel centroids from {len(pts)} .npz members sampled in {WINDOWS} contiguous windows of the randomly ordered zip, via HTTP range requests"},
                    note=f"{n_total} parcels (Latvia 431k, Estonia 176k, Portugal 100k), Sentinel-2 2021; {len(pts)} sampled.")


if __name__ == "__main__":
    main()
