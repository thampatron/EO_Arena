"""GlobalBuildingMap (Zhu et al. 2024) footprint.

The GitHub repo zhu-xlab/GlobalBuildingMap ships assets/merged_roi.geojson (97 MB): one feature per processed
0.2 x 0.2 degree PlanetScope mosaic tile, with the tile's W_N_E_S corner coordinates in its `file` name
(e.g. -153.6_58.8_-153.4_58.6_bm_mosaic_tile.tif) and the geometry in Web Mercator. The file is streamed to a
temp path, tile centres are decoded from the names (falling back to the geometry), and the temp file is deleted.
The product rasters on mediaTUM (rsync only) are never touched.
"""
import json, re, shutil, sys
from pathlib import Path

import requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "globalbuildingmap"
URL = "https://raw.githubusercontent.com/zhu-xlab/GlobalBuildingMap/main/assets/merged_roi.geojson"
TMP = Path("/tmp/claude-0/fp") / DS
PAT = re.compile(r"^(-?\d+(?:\.\d+)?)_(-?\d+(?:\.\d+)?)_(-?\d+(?:\.\d+)?)_(-?\d+(?:\.\d+)?)_")


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    f = TMP / "merged_roi.geojson"
    with requests.get(URL, stream=True, timeout=600) as r:
        r.raise_for_status()
        with f.open("wb") as out:
            for chunk in r.iter_content(1 << 20):
                out.write(chunk)
    with f.open(encoding="utf-8") as fh:
        feats = json.load(fh)["features"]
    to_ll = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    pts, fallback = [], 0
    for ft in feats:
        m = PAT.match(ft.get("properties", {}).get("file", "") or "")
        if m:
            w, n, e, s = map(float, m.groups())
            pts.append(((w + e) / 2, (n + s) / 2))
        else:
            try:
                ring = ft["geometry"]["coordinates"][0]
                xs, ys = [p[0] for p in ring], [p[1] for p in ring]
                pts.append(to_ll.transform((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
                fallback += 1
            except Exception:
                pass
    shutil.rmtree(TMP, ignore_errors=True)
    write_footprint(DS, pts, kind="tiles", n_total=len(feats),
                    source={"label": "zhu-xlab/GlobalBuildingMap assets/merged_roi.geojson", "url": "https://github.com/zhu-xlab/GlobalBuildingMap/blob/main/assets/merged_roi.geojson",
                            "method": "centre of each processed 0.2-degree PlanetScope mosaic tile, decoded from the W_N_E_S corners in the feature's file name"},
                    note=f"{len(feats)} mosaic-tile ROIs built from 790,101 PlanetScope scenes ({fallback} centres taken from the Web Mercator geometry instead of the name). Product rasters are 5-degree tiles on mediaTUM.")


if __name__ == "__main__":
    main()
