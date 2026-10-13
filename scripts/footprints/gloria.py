"""Footprint for GLORIA (Lehmann et al. 2023), PANGAEA 948492.

GLORIA-2022.zip (59 MB) contains GLORIA_meta_and_lab.csv with Latitude/Longitude for each of the
7,572 spectra. Only that member (2.7 MB) is read, via HTTP range requests on the zip.
"""
import io, sys, time, zipfile
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "gloria"
URL = "https://download.pangaea.de/dataset/948492/files/GLORIA-2022.zip"
SESSION = requests.Session()


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
        r = SESSION.get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}, timeout=300)
        r.raise_for_status()
        self.pos += len(r.content)
        return r.content

    def seekable(self):
        return True

    def readable(self):
        return True


def main():
    z = zipfile.ZipFile(RangeFile(URL))
    d = pd.read_csv(io.BytesIO(z.read("GLORIA_2022/GLORIA_meta_and_lab.csv")), low_memory=False)
    pts = list(zip(d["Longitude"], d["Latitude"]))
    write_footprint(DS, pts, kind="samples", n_total=len(d),
                    source={"label": "GLORIA_meta_and_lab.csv inside GLORIA-2022.zip (PANGAEA 948492)", "url": URL,
                            "method": "Latitude/Longitude columns of the per-spectrum metadata table"},
                    note=f"{len(d)} in-situ hyperspectral Rrs measurements, {d['Country'].nunique()} countries, "
                         f"{d['Site_name'].nunique()} named sites.")


if __name__ == "__main__":
    main()
