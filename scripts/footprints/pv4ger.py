"""PV4GER (GEO-Bench m-pv4ger, rooftop solar PV classification, Germany): per-chip coordinates are encoded in the
GEO-Bench sample ids ("lat,lon" or "lon,lat" strings such as 50.909,6.521), which the TACO repackaging on Hugging
Face (isp-uv-es/geobench-m-pv4ger-taco) exposes in METADATA/sample.parquet inside geobench-m-pv4ger.zip (1.15 GB).
Only the zip central directory and the 0.5 MB parquet are read via HTTP range requests. The two coordinate
orders are told apart by range (Germany: lat 47-55, lon 5-16). The segmentation variant (m-pv4ger-seg) uses chips
from the same source imagery."""
import sys, time, zipfile, shutil
from pathlib import Path
import requests, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/isp-uv-es/geobench-m-pv4ger-taco/resolve/main/geobench-m-pv4ger.zip"
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

TMP = Path("/tmp/claude-0/fp/pv4ger"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "sample.parquet"
if not f.exists():
    f.write_bytes(zipfile.ZipFile(RangeFile(URL)).read("METADATA/sample.parquet"))

d = pd.read_parquet(f, columns=["ml:split", "ml:sample_id", "ml:class_name"])
pts, bad = [], 0
for sid in d["ml:sample_id"]:
    try:
        a, b = (float(v) for v in sid.split(","))
    except ValueError:
        bad += 1; continue
    lat, lon = (a, b) if 46 <= a <= 56 else (b, a)
    if 46 <= lat <= 56 and 5 <= lon <= 16:
        pts.append((lon, lat))
    else:
        bad += 1

write_footprint("pv4ger", pts, kind="samples", n_total=len(d),
                source={"label": "GEO-Bench m-pv4ger sample ids (TACO METADATA/sample.parquet, Hugging Face isp-uv-es/geobench-m-pv4ger-taco)", "url": URL,
                        "method": "chip centre lat/lon parsed from each GEO-Bench sample id (13,812 320x320 px chips at 0.1 m), read from the zip via HTTP range requests"},
                note=f"Splits: {d['ml:split'].value_counts().to_dict()}; classes: {d['ml:class_name'].value_counts().to_dict()}. {bad} ids could not be parsed. Chips come from North Rhine-Westphalia orthophotos (3D-PV-Locator, Mayer et al. 2022).")
shutil.rmtree(TMP, ignore_errors=True)
