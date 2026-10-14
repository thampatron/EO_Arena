"""Copernicus-Bench LC100 (Sentinel-3 OLCI classification / segmentation): sample names in lc100_s3.zip
(Hugging Face wangyi111/Copernicus-Bench, 1.7 GB) are <id>_<lon>_<lat> on a 0.25 degree grid, e.g.
0718869_-102.75_34.75. Only the zip's central directory (~2 MB) is read over HTTP range requests; the
coordinates are decoded from the lc100/<name>.tif label file names. Nothing else is downloaded."""
import sys, re, time, zipfile
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/wangyi111/Copernicus-Bench/resolve/main/l2_lc100_s3/lc100_s3.zip"
S = requests.Session()

def get(url, **kw):
    for i in range(6):
        r = S.get(url, timeout=180, **kw)
        if r.status_code != 429:
            r.raise_for_status(); return r
        time.sleep(5 * (i + 1))
    r.raise_for_status()

class RangeFile:
    def __init__(self, url):
        r = get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True)
        self.url, self.pos = r.url, 0
        self.size = int(r.headers["Content-Range"].split("/")[-1])
    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]; return self.pos
    def tell(self): return self.pos
    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        if n == 0: return b""
        b = get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}).content
        self.pos += len(b); return b
    def seekable(self): return True
    def readable(self): return True

z = zipfile.ZipFile(RangeFile(URL))
names = [i.filename for i in z.infolist() if i.filename.startswith("lc100_s3/lc100/") and i.filename.endswith(".tif")]
pts = []
for n in names:
    m = re.search(r"/(\d+)_(-?\d+\.\d+)_(-?\d+\.\d+)\.tif$", n)
    pts.append((float(m.group(2)), float(m.group(3))))

write_footprint("lc100-classification-segmentation", pts, kind="samples", n_total=len(names),
                source={"label": "Copernicus-Bench lc100_s3.zip file listing (Hugging Face)", "url": URL,
                        "method": "lon/lat decoded from the <id>_<lon>_<lat> sample names in the zip central directory (0.25 degree grid), one point per LC100 label patch"},
                note="Classification and segmentation variants share the same patches. Only the zip central directory was read (HTTP range requests); patch centres are the grid-cell coordinates in the file names.")
