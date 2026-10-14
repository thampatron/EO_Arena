"""xBD / xView2: one point per 1024x1024 pre/post image pair, taken from the WGS84 building outlines that xBD ships
in its label JSONs (first vertex of the first building), as preserved in the isp-uv-es/xview2-taco repackaging on
Hugging Face (METADATA/sample.parquet inside xview2.zip; only the disaster, building-count and lng/lat polygon
columns are read by HTTP range requests, ~50 MB). The PNGs themselves carry no geotransform."""
import sys, io, time, zipfile, collections
from pathlib import Path
import requests, pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

REPO = "https://huggingface.co/datasets/isp-uv-es/xview2-taco"
URL = REPO + "/resolve/main/xview2.zip"


def fetch_range(session, url, a, b):
    for i in range(8):  # retry on throttling / transient errors
        try:
            r = session.get(url, headers={"Range": f"bytes={a}-{b}"}, timeout=120)
            if r.status_code == 206: return r
        except requests.RequestException:
            pass
        time.sleep(5 * (i + 1))
    raise IOError(f"no partial content for {url}")


class HttpFile(io.RawIOBase):
    """Minimal seekable read-only file over HTTP range requests (for zipfile)."""
    def __init__(self, url, session):
        self.url, self.s, self.pos = url, session, 0
        r = fetch_range(session, url, 0, 0)
        self.size = int(r.headers["Content-Range"].split("/")[-1])
        self.url = r.url  # resolved URL, so later reads skip the redirect
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]; return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0: return b""
        r = fetch_range(self.s, self.url, self.pos, self.pos + n - 1)
        self.pos += len(r.content); return r.content
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


class View(io.RawIOBase):
    """A byte range of an HttpFile exposed as its own file (for a stored, uncompressed zip member)."""
    def __init__(self, base, off, size): self.b, self.off, self.size, self.pos = base, off, size, 0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, o, w=0): self.pos = {0: o, 1: self.pos + o, 2: self.size + o}[w]; return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0: return b""
        d = fetch_range(self.b.s, self.b.url, self.off + self.pos, self.off + self.pos + n - 1).content
        self.pos += len(d); return d
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


hf = HttpFile(URL, requests.Session())
zf = zipfile.ZipFile(hf)
info = zf.getinfo("METADATA/sample.parquet")
assert info.compress_type == 0
raw = fetch_range(hf.s, hf.url, info.header_offset, info.header_offset + 29).content
start = info.header_offset + 30 + int.from_bytes(raw[26:28], "little") + int.from_bytes(raw[28:30], "little")
t = pq.ParquetFile(View(hf, start, info.file_size), pre_buffer=True).read(columns=["ml:disaster", "ml:polygon_lnglat"])
pts, events, empty = [], collections.Counter(), 0
for dis, poly in zip(t.column("ml:disaster").to_pylist(), t.column("ml:polygon_lnglat").to_pylist()):
    events[dis] += 1
    if poly and len(poly) >= 2: pts.append((poly[0], poly[1]))
    else: empty += 1
write_footprint("xbd-xview2", pts, kind="samples", n_total=t.num_rows,
                source={"label": "xBD label geometry via isp-uv-es/xview2-taco sample.parquet", "url": REPO,
                        "method": "first WGS84 building vertex of each image pair's label polygons (ml:polygon_lnglat), read from the TACO metadata inside the zip over HTTP"},
                note=f"{t.num_rows:,} image pairs over {len(events)} events (" + ", ".join(f"{k} {v}" for k, v in events.most_common()) +
                     f"); {empty} pairs contain no building and get no point. 3,000 of {len(pts):,} stored.")
