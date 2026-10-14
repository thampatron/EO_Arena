"""xView (DIUx/NGA, WorldView-3 object detection): the original download needs an xviewdataset.org account, but
the TACO repackaging on Hugging Face (isp-uv-es/xview-taco) stores per-image centre lon/lat (ml:lon, ml:lat) in
METADATA/sample.parquet inside xview.zip (15 GB). Only the zip central directory and that 7 MB parquet (stored
uncompressed) are read through HTTP range requests; no imagery is transferred."""
import sys, time, zipfile, shutil
from pathlib import Path
import requests, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/isp-uv-es/xview-taco/resolve/main/xview.zip"
S = requests.Session(); S.headers["User-Agent"] = "curl/8"

def get(url, **kw):
    for i in range(6):
        r = S.get(url, timeout=180, **kw)
        if r.status_code not in (429, 500, 502, 503):
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

TMP = Path("/tmp/claude-0/fp/xview"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "sample.parquet"
if not f.exists():
    f.write_bytes(zipfile.ZipFile(RangeFile(URL)).read("METADATA/sample.parquet"))

d = pd.read_parquet(f, columns=["ml:split", "ml:lon", "ml:lat", "ml:n_objects"])
pts = list(zip(d["ml:lon"].astype(float), d["ml:lat"].astype(float)))
n_obj = int(d["ml:n_objects"].sum())

write_footprint("xview", pts, kind="tiles", n_total=len(d),
                source={"label": "xView TACO repackaging, METADATA/sample.parquet inside xview.zip (Hugging Face isp-uv-es/xview-taco)", "url": URL,
                        "method": f"centre lon/lat (ml:lon, ml:lat) of each of the {len(d)} released WorldView-3 training images, read from the zip via HTTP range requests"},
                note=f"846 train/val images with {n_obj:,} boxes in the public release (the ~1M-object figure includes the withheld test set). Splits: {d['ml:split'].value_counts().to_dict()}.")
shutil.rmtree(TMP, ignore_errors=True)
