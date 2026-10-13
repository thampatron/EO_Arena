"""Footprint for ForestNet (Irvin et al. 2020), Stanford ML Group.

ForestNetDataset.zip (3.4 GB) on download.cs.stanford.edu holds train/val/test CSVs with a latitude/longitude
column per example (the forest-loss event centroid). The zip's central directory and the three deflated CSV
members (~80 KB) are fetched with HTTP range requests; nothing else is downloaded.
"""
import io, struct, sys, time, zipfile, zlib
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "forestnet"
URL = "https://download.cs.stanford.edu/deep/ForestNetDataset.zip"
SESSION = requests.Session()


def get(**kw):
    for i in range(8):  # the server answers some range requests with a transient 503
        r = SESSION.get(URL, timeout=120, **kw)
        if r.status_code in (200, 206):
            return r
        time.sleep(2 * (i + 1))
    r.raise_for_status()


class RangeFile:
    def __init__(self):
        r = get(headers={"Range": "bytes=0-0"})
        self.size, self.pos = int(r.headers["Content-Range"].split("/")[-1]), 0

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
        b = get(headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}).content
        self.pos += len(b)
        return b

    def seekable(self):
        return True

    def readable(self):
        return True


def member_bytes(rf, info):
    rf.seek(info.header_offset)
    nlen, xlen = struct.unpack("<HH", rf.read(30)[26:30])
    rf.seek(info.header_offset + 30 + nlen + xlen)
    data = rf.read(info.compress_size)
    return zlib.decompressobj(-15).decompress(data) if info.compress_type == zipfile.ZIP_DEFLATED else data


def main():
    rf = RangeFile()
    z = zipfile.ZipFile(rf)
    frames = []
    for i in z.infolist():
        if i.filename.endswith((".csv",)) and i.filename.split("/")[-1] in ("train.csv", "val.csv", "test.csv"):
            df = pd.read_csv(io.BytesIO(member_bytes(rf, i)))
            df["split"] = i.filename.split("/")[-1][:-4]
            frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    splits = df["split"].value_counts().to_dict()
    write_footprint(DS, list(zip(df["longitude"], df["latitude"])), kind="samples", n_total=len(df),
                    source={"label": "ForestNet train/val/test CSVs (inside ForestNetDataset.zip)", "url": URL,
                            "method": "latitude/longitude columns of the split CSVs, read from the zip via HTTP range requests"},
                    note=f"{len(df)} forest-loss events in Indonesia, 2001-2016 (" + ", ".join(f"{k} {v}" for k, v in splits.items())
                         + "); each example is a Landsat 8 composite centred on the event polygon.")


if __name__ == "__main__":
    main()
