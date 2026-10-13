"""ReforesTree (6 agroforestry sites, Ecuador): per-tree lon/lat (lon_d, lat_d = detected-tree position mapped
to the drone orthomosaic georeference) from mapping/final_dataset.csv inside the Zenodo archive reforesTree.zip
(record 6813783, 7.5 GB). Only the zip central directory and that 2.6 MB CSV (stored uncompressed) are fetched
with HTTP range requests; the orthomosaics and tiles are not downloaded."""
import sys, io, zipfile, shutil
from pathlib import Path
import requests, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://zenodo.org/records/6813783/files/reforesTree.zip?download=1"
S = requests.Session()

class RangeFile:
    def __init__(self, url):
        r = S.get(url, headers={"Range": "bytes=0-0"}, timeout=60, allow_redirects=True)
        self.url, self.pos = r.url, 0
        self.size = int(r.headers["Content-Range"].split("/")[-1])
    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]; return self.pos
    def tell(self): return self.pos
    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        if n == 0: return b""
        b = S.get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}, timeout=180).content
        self.pos += len(b); return b
    def seekable(self): return True
    def readable(self): return True

TMP = Path("/tmp/claude-0/fp/reforestree"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "final_dataset.csv"
if not f.exists():
    z = zipfile.ZipFile(RangeFile(URL))
    f.write_bytes(z.read("mapping/final_dataset.csv"))

d = pd.read_csv(f)
pts = list(zip(d["lon_d"].astype(float), d["lat_d"].astype(float)))
sites = d["site"].nunique()

write_footprint("reforestree", pts, kind="samples", n_total=len(d),
                source={"label": "ReforesTree mapping/final_dataset.csv (inside reforesTree.zip, Zenodo 6813783)", "url": "https://zenodo.org/records/6813783",
                        "method": f"lon/lat of each of the {len(d)} mapped tree bounding boxes (lon_d, lat_d) across {sites} drone-surveyed sites, read from the CSV via HTTP range requests into the zip"},
                note="Each point is one annotated tree; the six sites are small (~0.1 km2) agroforestry plots in Los Rios / Guayas, Ecuador, so points cluster into six tight groups.")
shutil.rmtree(TMP, ignore_errors=True)
