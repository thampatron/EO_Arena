"""Footprint for Kuro Siwo (Bountos et al. 2023), GitHub Orion-AI-Lab/KuroSiwo.

Reads pickle/KuroV2_grid_dict.gz (9 MB, gzip-pickled dict of all 31,707 2.24 km grid cells with
their polygon in EPSG:3857, catalogue.yaml CRS: 3857) and reprojects each cell centre to WGS84.
"""
import gzip, pickle, re, sys
from pathlib import Path

import requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "kuro-siwo-flood-s1"
URL = "https://raw.githubusercontent.com/Orion-AI-Lab/KuroSiwo/main/pickle/KuroV2_grid_dict.gz"
TMP = Path("/tmp/claude-0/fp") / DS


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    f = TMP / "grid_dict.gz"
    if not f.exists():
        r = requests.get(URL, timeout=180)
        r.raise_for_status()
        f.write_bytes(r.content)
    d = pickle.load(gzip.open(f))  # repository data, trusted
    tr = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    pts, acts = [], set()
    for v in d.values():
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", v["info"]["geom"])]
        xs, ys = nums[0::2], nums[1::2]
        pts.append(tr.transform((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
        acts.add(v["info"]["actid"])
    write_footprint(DS, pts, kind="samples", n_total=len(d),
                    source={"label": "KuroSiwo pickle/KuroV2_grid_dict.gz (GitHub)", "url": URL,
                            "method": "centre of each 2.24 km grid-cell polygon (EPSG:3857) in the dataset's grid dictionary"},
                    note=f"{len(d)} grid cells over {len(acts)} Copernicus EMS flood activations (GRD v2 release).")
    for p in TMP.iterdir():
        p.unlink()
    TMP.rmdir()


if __name__ == "__main__":
    main()
