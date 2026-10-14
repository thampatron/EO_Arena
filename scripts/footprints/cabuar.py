"""CaBuAr: patch centres from metadata.parquet in the DarthReca/california_burned_areas Hugging Face repo, which lists
per patch the UTM x/y pixel coordinate vectors (crs = EPSG:32610/32611) for every pre/post Sentinel-2 patch."""
import sys, shutil
from pathlib import Path
import requests, pyarrow.parquet as pq, numpy as np
from pyproj import Transformer
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/DarthReca/california_burned_areas/resolve/main/metadata.parquet"
TMP = Path("/tmp/claude-0/fp/cabuar"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "metadata.parquet"
if not f.exists():
    r = requests.get(URL, timeout=300); r.raise_for_status(); f.write_bytes(r.content)
t = pq.read_table(f).to_pandas()
t = t.drop_duplicates(["uuid", "patch"])  # pre and post share the same footprint
pts = []
for crs, sub in t.groupby("crs"):
    tr = Transformer.from_crs(int(crs), 4326, always_xy=True)
    xs = np.array([np.mean(v) for v in sub["x"]]); ys = np.array([np.mean(v) for v in sub["y"]])
    lon, lat = tr.transform(xs, ys); pts += list(zip(lon, lat))
write_footprint("cabuar", pts, kind="samples", n_total=len(t),
                source={"label": "CaBuAr metadata.parquet (Hugging Face)", "url": URL,
                        "method": "centre of each 512x512 patch from its UTM x/y coordinate vectors, reprojected to WGS84; pre/post pairs deduplicated"},
                note=f"{t['uuid'].nunique()} fire events, each tiled into up to 121 patches.")
shutil.rmtree(TMP, ignore_errors=True)
