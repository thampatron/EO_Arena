"""CloudSEN12 (Cloud-S2): patch centroids from the TACO footer metadata of the tacofoundation/cloudsen12
L1C parts on Hugging Face (stac:centroid per 5090 m patch). Only the parquet footers are transferred (~1.3 MB)."""
import sys, io, struct
from pathlib import Path
import requests, pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

BASE = "https://huggingface.co/datasets/tacofoundation/cloudsen12/resolve/main/"
PARTS = [f"cloudsen12-l1c.{i:04d}.part.taco" for i in range(5)]

def taco_footer(url):
    r = requests.get(url, headers={"Range": "bytes=0-17"}, allow_redirects=True, timeout=60)
    r.raise_for_status()
    b = r.content
    assert b[:2] == b"WX", "not a TACO file"
    off, ln = struct.unpack("<Q", b[2:10])[0], struct.unpack("<Q", b[10:18])[0]
    r2 = requests.get(r.url, headers={"Range": f"bytes={off}-{off+ln-1}"}, timeout=120)
    r2.raise_for_status()
    return pq.read_table(io.BytesIO(r2.content))

pts, n = [], 0
for p in PARTS:
    t = taco_footer(BASE + p).to_pandas()
    n += len(t)
    for s in t["stac:centroid"]:
        x, y = s.replace("POINT (", "").rstrip(")").split()
        pts.append((float(x), float(y)))

write_footprint("cloudsen12-cloud-s2", pts, kind="samples", n_total=n,
                source={"label": "tacofoundation/cloudsen12 (TACO footer metadata, L1C parts)",
                        "url": "https://huggingface.co/datasets/tacofoundation/cloudsen12",
                        "method": "stac:centroid of every L1C patch read from the parquet footer of the 5 .taco parts via HTTP range requests"},
                note="Each ROI contributes ~5 patches at the same location (different dates); high, scribble and nolabel label types included.")
