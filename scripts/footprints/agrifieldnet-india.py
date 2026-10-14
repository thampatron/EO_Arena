"""AgriFieldNet India: centre lon/lat of all 1,165 256x256 Sentinel-2 tiles (train 929 + test 236) from
METADATA/sample.parquet (38 KB) inside the TACO repackaging on Hugging Face (isp-uv-es/agrifieldnet-india-taco,
agrifieldnet-india.zip, 212 MB), read with HTTP range requests on the zip central directory only. The 7,081
labelled fields lie inside these tiles (ml:n_fields per tile). Supersedes an earlier 300-tile header subsample
from the source.coop bucket."""
import sys, time, zipfile, shutil
from pathlib import Path
import requests, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/isp-uv-es/agrifieldnet-india-taco/resolve/main/agrifieldnet-india.zip"
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

TMP = Path("/tmp/claude-0/fp/agrifieldnet-india"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "sample.parquet"
if not f.exists():
    f.write_bytes(zipfile.ZipFile(RangeFile(URL)).read("METADATA/sample.parquet"))

d = pd.read_parquet(f, columns=["ml:split", "ml:lon", "ml:lat", "ml:n_fields"])
pts = list(zip(d["ml:lon"].astype(float), d["ml:lat"].astype(float)))

write_footprint("agrifieldnet-india", pts, kind="tiles", n_total=len(d),
                source={"label": "AgriFieldNet India TACO metadata (METADATA/sample.parquet in agrifieldnet-india.zip, Hugging Face isp-uv-es/agrifieldnet-india-taco)", "url": URL,
                        "method": "centre lon/lat (ml:lon, ml:lat) of every 256x256 tile, read from the zip via HTTP range requests"},
                note=f"1,165 tiles ({d['ml:split'].value_counts().to_dict()}) in Uttar Pradesh, Rajasthan, Odisha and Bihar; {int(d['ml:n_fields'].sum())} field ids counted in the tile metadata (7,081 fields in the original release).")
shutil.rmtree(TMP, ignore_errors=True)
