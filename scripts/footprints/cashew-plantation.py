"""Cashew plantation (GEO-Bench m-cashew-plant / Smallholder Cashew Plantations in Benin): chip centres of the
original scene, from the GeoTIFF headers of the 20 label chips in the isp-uv-es/benin-cashews-taco repackaging
(each 3.4 KB label chip is read from the zip by HTTP range request). The GEO-Bench HDF5 export (and its TACO copy,
isp-uv-es/geobench-m-cashew-plant-taco) carries the same dummy transform on all 1,800 samples, so per-sample
locations cannot be recovered from GEO-Bench itself; the samples are crops/dates of this one ~10 x 13 km scene."""
import sys, io, time, zipfile
from pathlib import Path
import requests, rasterio, pyarrow.parquet as pq
from rasterio.warp import transform
from rasterio.io import MemoryFile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

REPO = "https://huggingface.co/datasets/isp-uv-es/benin-cashews-taco"
URL = REPO + "/resolve/main/benin-cashews.zip"


class HttpFile(io.RawIOBase):
    def __init__(self, url, session):
        self.url, self.s, self.pos = url, session, 0
        r = self._get(0, 0)
        self.size = int(r.headers["Content-Range"].split("/")[-1])
        self.url = r.url  # keep the resolved (CDN) URL so later range reads skip the resolver
    def _get(self, a, b):
        for i in range(8):  # retry on throttling / transient errors
            try:
                r = self.s.get(self.url, headers={"Range": f"bytes={a}-{b}"}, timeout=120)
                if r.status_code == 206: return r
            except requests.RequestException:
                pass
            time.sleep(5 * (i + 1))
        raise IOError(f"no partial content for {self.url}")
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]; return self.pos
    def read(self, n=-1):
        if n is None or n < 0: n = self.size - self.pos
        if n == 0: return b""
        r = self._get(self.pos, self.pos + n - 1)
        self.pos += len(r.content); return r.content
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


zf = zipfile.ZipFile(HttpFile(URL, requests.Session()))
ch = pq.read_table(io.BytesIO(zf.open("METADATA/children.parquet").read())).to_pandas()
labels = sorted(p for p in ch["internal:relative_path"] if str(p).endswith("label.tif"))
pts = []
for p in labels:
    with MemoryFile(zf.open(f"DATA/{p}").read()) as mf, mf.open() as src:  # ~3.4 KB per label chip
        b = src.bounds
        xs, ys = transform(src.crs, "EPSG:4326", [(b.left + b.right) / 2], [(b.bottom + b.top) / 2])
        pts.append((xs[0], ys[0]))
write_footprint("cashew-plantation", pts, kind="tiles", n_total=len(labels),
                source={"label": "benin-cashews TACO repackaging (ISP-UV, Hugging Face)", "url": REPO,
                        "method": "centre of each of the 20 georeferenced 2.56 km label chips, from the GeoTIFF headers of the label chips read inside the zip over HTTP, EPSG:32631 -> WGS84"},
                note="One Sentinel-2 scene in central Benin (Collines), 2019-11 to 2020-10. GEO-Bench m-cashew-plant has 1,800 samples but its HDF5 export gives every sample the same transform, so only the scene's 20-chip grid is plottable.")
