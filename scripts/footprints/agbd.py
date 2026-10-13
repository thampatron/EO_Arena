"""AGBD: GEDI footprint lat/lon of the patches, read from the `metadata.lat`/`metadata.lon` columns of a
subsample of the prs-eth/AGBD_raw parquet shards on Hugging Face (HTTP range reads of the footer and the two
coordinate column chunks only; ~0.3 MB per shard, no imagery transferred)."""
import sys, io, time, random
from pathlib import Path
import requests, pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

REPO = "prs-eth/AGBD_raw"
TREE = f"https://huggingface.co/api/datasets/{REPO}/tree/main/data"
RAW = f"https://huggingface.co/datasets/{REPO}/resolve/main/"
N_TOTAL = 9949032 + 2681807 + 3303722  # dataset_info splits in the AGBD_raw README
N_SHARDS = 60  # of 2,658 parquet shards (~3 s per shard)


class HttpFile(io.RawIOBase):
    """Minimal seekable read-only file over HTTP range requests (for pyarrow.parquet)."""
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


def list_shards(session):
    url, out = TREE, []
    while url:
        r = session.get(url, timeout=60); r.raise_for_status()
        out += [x["path"] for x in r.json() if x["path"].endswith(".parquet")]
        url = r.links.get("next", {}).get("url")
    return sorted(out)


s = requests.Session()
shards = list_shards(s)
random.Random(0).shuffle(shards)
pts = []
for p in sorted(shards[:N_SHARDS]):
    try:
        pf = pq.ParquetFile(HttpFile(RAW + p, s), pre_buffer=True)
        t = pf.read(columns=["metadata.lat", "metadata.lon"]).column("metadata").flatten()
        lat, lon = t[0].to_pylist(), t[1].to_pylist()
        pts += list(zip(lon, lat))
    except Exception as e:  # noqa: BLE001
        print("skip", p, e)
write_footprint("agbd", pts, kind="samples", n_total=N_TOTAL,
                source={"label": "AGBD_raw parquet shards (Hugging Face)", "url": f"https://huggingface.co/datasets/{REPO}/tree/main/data",
                        "method": f"GEDI footprint lat/lon from the metadata columns of {N_SHARDS} randomly chosen parquet shards (of {len(shards)}), read by HTTP range requests"},
                note=f"Points are GEDI L4A footprints (one per 25x25 px patch); {len(pts):,} read from {N_SHARDS} of {len(shards)} shards, 3,000 kept. Per README the dataset covers S2 tiles in 11 regions; n_total from the AGBD_raw dataset_info.")
