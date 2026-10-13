"""fMoW footprint. The original S3 bucket only offers the metadata as a 245 MB groundtruth.tar.bz2, so we use the
fMoW-RGB parquet mirror on Hugging Face (EVER-Z/fMoW_rgb, 363,572 train + 53,041 val images), whose rows carry the
image's WKT `polygon` (raw_location). Only the polygon column chunks are read, with HTTP range requests (tens of MB in
total; images are never transferred)."""
import sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests, pyarrow as pa, pyarrow.parquet as pq
from shapely import wkt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

DS = "fmow"
REPO = "EVER-Z/fMoW_rgb"
API = f"https://huggingface.co/api/datasets/{REPO}/tree/main/data"
RAW = f"https://huggingface.co/datasets/{REPO}/resolve/main/"


def _req(method, url, **kw):
    """requests call with backoff on Hugging Face 429/5xx throttling."""
    for i in range(8):
        r = requests.request(method, url, allow_redirects=True, timeout=120, **kw)
        if r.status_code not in (429, 500, 502, 503, 504):
            r.raise_for_status()
            return r
        time.sleep(10 * (i + 1))
    r.raise_for_status()


class RangeFile:
    closed = False

    def __init__(self, url):
        self.url, self.pos, self.transferred = url, 0, 0
        self.size = int(_req("HEAD", url).headers["Content-Length"])

    def seek(self, o, w=0):
        self.pos = o if w == 0 else (self.pos + o if w == 1 else self.size + o)
        return self.pos

    def tell(self): return self.pos
    def readable(self): return True
    def seekable(self): return True
    def writable(self): return False
    def close(self): pass

    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        if n == 0: return b""
        r = _req("GET", self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"})
        self.pos += len(r.content); self.transferred += len(r.content)
        return r.content


def main():
    try:
        files = [f["path"] for f in _req("GET", API).json() if f["path"].endswith(".parquet")]
    except Exception:  # the tree endpoint sometimes 500s; the dataset-info endpoint lists the same files
        files = [s["rfilename"] for s in _req("GET", f"https://huggingface.co/api/datasets/{REPO}").json()["siblings"]
                 if s["rfilename"].startswith("data/") and s["rfilename"].endswith(".parquet")]
    def one(f):
        rf = RangeFile(RAW + f)
        t = pq.ParquetFile(pa.PythonFile(rf, mode="r")).read(columns=["polygon"])
        out = []
        for w in t.column("polygon").to_pylist():
            try:
                c = wkt.loads(w).centroid; out.append((c.x, c.y))
            except Exception:
                pass
        print(f"{f}: {t.num_rows} rows, {rf.transferred} bytes", flush=True)
        return out, t.num_rows, rf.transferred

    pts, total, moved = [], 0, 0
    with ThreadPoolExecutor(4) as ex:
        for out, n, m in ex.map(one, sorted(files)):
            pts += out; total += n; moved += m
    write_footprint(DS, pts, source={"label": "fMoW-RGB parquet mirror on Hugging Face (polygon column)",
                                     "url": f"https://huggingface.co/datasets/{REPO}/tree/main/data",
                                     "method": "centroids of the WKT raw_location polygon of every fMoW-RGB train/val image, read from the parquet shards with HTTP range requests"},
                    kind="samples", n_total=total,
                    note=f"{total} fMoW-RGB train+val images (the test set and the full-res multispectral release are not in this mirror); multi-temporal views share a site. {moved/1e6:.1f} MB transferred.")


if __name__ == "__main__":
    main()
