"""Footprint for WorldFloods v2 (Portalés-Julià et al. 2023), Hugging Face isp-uv-es/WorldFloodsv2.

Reads dataset_metadata.csv (120 KB): one row per flood map with its UTM bounds and CRS; the
centre of each bounds box is reprojected to WGS84.
"""
import ast, io, sys
from pathlib import Path

import pandas as pd
import requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "worldfloods-v2"
URL = "https://huggingface.co/datasets/isp-uv-es/WorldFloodsv2/resolve/main/dataset_metadata.csv"


def main():
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    pts = []
    for b, crs in zip(d["bounds"], d["crs"]):
        w, s, e, n = ast.literal_eval(b)
        tr = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
        pts.append(tr.transform((w + e) / 2, (s + n) / 2))
    write_footprint(DS, pts, kind="samples", n_total=len(d),
                    source={"label": "WorldFloods v2 dataset_metadata.csv (Hugging Face)", "url": URL,
                            "method": "centre of each flood map's UTM bounds, reprojected to WGS84"},
                    note=f"{len(d)} flood-map/S2 pairs across train/val/test (Copernicus EMS activations).")


if __name__ == "__main__":
    main()
