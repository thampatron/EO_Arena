"""BraDD-S1TS: no public per-sample coordinates. The 17.6 GB Zenodo zip holds only meta.csv (sample id, date,
sampling type, Brazilian state, split) and .pt tensors (image/label/dates, no georeference); the GitHub repo shows
sample centres only as a figure (CenterLocationMap.svg). meta.csv is read from inside the zip by HTTP range
requests (~3 MB: central directory + the 0.3 MB compressed csv) and the footprint is reduced to one point per
Legal-Amazon state, weighted by nothing (status partial, kind sites)."""
import sys, io, time, zipfile, csv, collections
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

RECORD = "https://zenodo.org/records/8060250"
ZIP = "https://zenodo.org/api/records/8060250/files/BraDD-S1TS_zenodo.zip/content"
# approximate geographic centres of the Brazilian states (lon, lat)
STATE = {"PA": (-53.0, -4.0), "MT": (-55.5, -13.0), "AM": (-64.5, -4.0), "RO": (-62.8, -11.0), "AC": (-70.5, -9.0),
         "RR": (-61.4, 2.0), "MA": (-45.3, -5.2), "AP": (-52.0, 1.5), "TO": (-48.3, -10.0)}


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


zf = zipfile.ZipFile(HttpFile(ZIP, requests.Session()))
rows = list(csv.DictReader(io.TextIOWrapper(zf.open("BraDD-S1TS_zenodo/meta.csv"), encoding="utf-8")))
counts = collections.Counter(r["state"] for r in rows)
pts = [STATE[s] for s in counts if s in STATE]
write_footprint("bradd-s1ts", pts, kind="sites", n_total=len(rows), status="partial",
                source={"label": "BraDD-S1TS meta.csv (inside the Zenodo zip)", "url": RECORD,
                        "method": "one point per Brazilian state listed in meta.csv (approximate state centres); the dataset publishes no sample coordinates"},
                note="25,988 Sentinel-1 time-series samples (~2.5 km) across the Legal Amazon; per-state counts: " +
                     ", ".join(f"{s} {n}" for s, n in counts.most_common()) +
                     ". The .pt samples carry image/label/dates only; the true centre map exists only as pictures/CenterLocationMap.svg in the GitHub repo.")
