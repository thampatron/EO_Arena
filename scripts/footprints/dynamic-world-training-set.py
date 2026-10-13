"""Dynamic World training set: tile centres (lon/lat columns) from the official metadata table
v1_dw_tile_metadata_for_public_release.xlsx on PANGAEA (4.4 MB, one row per labelled 5.1 km tile)."""
import sys, shutil
from pathlib import Path
import requests, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

RECORD = "https://doi.pangaea.de/10.1594/PANGAEA.933475"
URL = "https://download.pangaea.de/dataset/933475/files/v1_dw_tile_metadata_for_public_release.xlsx"
TMP = Path("/tmp/claude-0/fp/dynamic-world-training-set"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "meta.xlsx"
with requests.get(URL, stream=True, timeout=300) as r:
    r.raise_for_status(); f.write_bytes(r.content)
d = pd.read_excel(f, usecols=["dw_id", "labeler", "lon", "lat"])
d = d.dropna(subset=["lon", "lat"])
lab = d["labeler"].value_counts().to_dict()
write_footprint("dynamic-world-training-set", list(zip(d["lon"], d["lat"])), kind="tiles", n_total=len(d),
                source={"label": "Dynamic World tile metadata (PANGAEA)", "url": RECORD,
                        "method": "lon/lat of every labelled tile from v1_dw_tile_metadata_for_public_release.xlsx"},
                note=f"{len(d):,} tile labels (" + ", ".join(f"{k}: {v:,}" for k, v in lab.items()) +
                     "); the 409 validation tiles are in validation_set_tiles.zip and are not listed in the metadata table. 3,000 tiles stored.")
shutil.rmtree(TMP, ignore_errors=True)
