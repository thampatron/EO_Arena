"""NZ cattle (GEO-Bench m-nz-cattle): sample centres parsed from the GEO-Bench sample ids, which embed the
original lon,lat of each 50 m aerial chip ("<n>_<town>_(<years>)_<lon>,<lat>"). Read from METADATA/sample.parquet
inside the isp-uv-es/geobench-m-nz-cattle-taco zip on Hugging Face by HTTP range requests (~0.2 MB)."""
import sys, io, time, zipfile, re, collections
from pathlib import Path
import requests, pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

REPO = "https://huggingface.co/datasets/isp-uv-es/geobench-m-nz-cattle-taco"
URL = REPO + "/resolve/main/geobench-m-nz-cattle.zip"


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


zf = zipfile.ZipFile(HttpFile(URL, requests.Session()))
ids = pq.read_table(io.BytesIO(zf.open("METADATA/sample.parquet").read())).column("ml:sample_id").to_pylist()
pts, towns = [], collections.Counter()
for sid in ids:
    m = re.match(r"\d+_(.+?)_\(.*\)_(-?[\d.]+),(-?[\d.]+)(_shifted)?$", sid)
    if m:
        towns[m.group(1)] += 1; pts.append((float(m.group(2)), float(m.group(3))))
write_footprint("nz-cattle", pts, kind="samples", n_total=len(ids),
                source={"label": "GEO-Bench m-nz-cattle sample ids (TACO repackaging, ISP-UV)", "url": REPO,
                        "method": "lon,lat embedded in every GEO-Bench sample id, read from METADATA/sample.parquet inside the zip over HTTP"},
                note=f"{len(ids)} chips of 500x500 px at 0.1 m; towns: " + ", ".join(f"{k} {v}" for k, v in towns.most_common()) +
                     ". The chips' own GeoTIFF transforms in the GEO-Bench export are wrong (0.1 deg/pixel), so the ids are used instead. Half of the samples are \"_shifted\" copies of the same locations.")
