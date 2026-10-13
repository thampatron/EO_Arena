"""FLAIR #1 / FLAIR #2: aerial patch centroids from the official flair_aerial_metadata.json (IGNF/FLAIR-1-2 on
Hugging Face), which stores patch_centroid_x/y in Lambert-93 (EPSG:2154) for all 93,462 aerial patches
(FLAIR #1 = 77,412 patches; FLAIR #2 adds 16,050; same aerial patch set)."""
import sys, json, shutil
from pathlib import Path
import requests
from pyproj import Transformer
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/IGNF/FLAIR-1-2/resolve/main/aux-data/flair_aerial_metadata.json"
TMP = Path("/tmp/claude-0/fp/flair-flair-2"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "flair_aerial_metadata.json"
if not f.exists():
    r = requests.get(URL, timeout=300); r.raise_for_status(); f.write_bytes(r.content)
d = json.loads(f.read_text())
tr = Transformer.from_crs(2154, 4326, always_xy=True)
xs = [v["patch_centroid_x"] for v in d.values()]; ys = [v["patch_centroid_y"] for v in d.values()]
lon, lat = tr.transform(xs, ys)
write_footprint("flair-flair-2", list(zip(lon, lat)), kind="samples", n_total=len(d),
                source={"label": "FLAIR aerial patch metadata (flair_aerial_metadata.json)", "url": URL,
                        "method": "patch_centroid_x/y of every 512x512 aerial patch, reprojected Lambert-93 -> WGS84"})
shutil.rmtree(TMP, ignore_errors=True)
