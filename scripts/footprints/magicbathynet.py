"""MagicBathyNet: centres of a random sample of 300 of the Sentinel-2 image patches (img/s2/img_N.tif, 180 m,
georeferenced in UTM) read from the GeoTIFF headers inside MagicBathyNet.zip on Zenodo (zip central directory +
the first ~8 KB of each .tif via HTTP range requests). Two sites: Agia Napa (Cyprus) and Puck Lagoon (Poland)."""
import sys, io, time, zlib, zipfile, random, logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests, rasterio
from rasterio.io import MemoryFile
from rasterio.warp import transform
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

RECORD = "https://zenodo.org/records/10470959"
URL = "https://zenodo.org/api/records/10470959/files/MagicBathyNet.zip/content"
N_SAMPLE, HEAD = 300, 6000


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


logging.disable(logging.CRITICAL)  # GDAL warns about the truncated tif bodies; only the header is needed
hf = HttpFile(URL, requests.Session())
zf = zipfile.ZipFile(hf)
tifs = [i for i in zf.infolist() if "/img/s2/" in i.filename and i.filename.endswith(".tif")]
sites = {s: sum(1 for i in tifs if f"/{s}/" in i.filename) for s in ("agia_napa", "puck_lagoon")}
sample = random.Random(0).sample(tifs, N_SAMPLE)
cdn, session = hf.url, requests.Session()


def centre(info):
    """One range request per patch: local file header + first ~8 KB of the deflate stream, inflated partially."""
    try:
        a = info.header_offset
        raw = fetch_range(session, cdn, a, a + 30 + 8192).content
        nlen, xlen = int.from_bytes(raw[26:28], "little"), int.from_bytes(raw[28:30], "little")
        body = raw[30 + nlen + xlen:]
        data = body if info.compress_type == 0 else zlib.decompressobj(-15).decompress(body, HEAD)
        with rasterio.Env(CPL_LOG="/dev/null"), MemoryFile(data) as mf, mf.open() as src:
            b = src.bounds
            xs, ys = transform(src.crs, "EPSG:4326", [(b.left + b.right) / 2], [(b.bottom + b.top) / 2])
            return (xs[0], ys[0])
    except Exception as e:  # noqa: BLE001
        print("skip", info.filename, e); return None


with ThreadPoolExecutor(8) as ex:
    pts = [p for p in ex.map(centre, sample) if p]
write_footprint("magicbathynet", pts, kind="samples", n_total=len(tifs),
                source={"label": "MagicBathyNet.zip (Zenodo)", "url": RECORD,
                        "method": f"centre of {N_SAMPLE} randomly chosen Sentinel-2 180 m patches (img/s2), from GeoTIFF headers read inside the zip over HTTP, UTM -> WGS84"},
                note=f"{len(tifs):,} S2 patches (" + ", ".join(f"{k} {v:,}" for k, v in sites.items()) + "); SPOT-6 and aerial patches are co-registered to the same footprints. " + f"{len(pts)} sampled (seed 0).")
