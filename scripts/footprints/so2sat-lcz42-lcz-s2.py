"""Footprint for So2Sat LCZ42 (Zhu et al. 2020), geolocation files on Hugging Face zhu-xlab/So2Sat-LCZ42 (v4).

training_geo.h5 / validation_geo.h5 / testing_geo.h5 (3.8 MB + 2 x 0.24 MB) give, for every 32x32 px
patch, the UTM EPSG code, a TFW-style transform (10 m pixels) and the city. The patch centre
(origin + 16 px) is reprojected from its UTM zone to WGS84.
"""
import shutil, sys
from pathlib import Path

import h5py
import numpy as np
import requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "so2sat-lcz42-lcz-s2"
BASE = "https://huggingface.co/datasets/zhu-xlab/So2Sat-LCZ42/resolve/main/v4/"
FILES = ["training_geo.h5", "validation_geo.h5", "testing_geo.h5"]
TMP = Path("/tmp/claude-0/fp") / DS


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    pts, cities, counts = [], set(), {}
    for name in FILES:
        f = TMP / name
        f.write_bytes(requests.get(BASE + name, timeout=300).content)
        with h5py.File(f) as h:
            epsg = h["epsg"][:].ravel()
            tfw = h["tfw"][:]
            cities |= {c.decode() for c in np.unique(h["city"][:])}
        counts[name.split("_")[0]] = len(epsg)
        cx = tfw[:, 4] + 16 * tfw[:, 0]
        cy = tfw[:, 5] + 16 * tfw[:, 3]
        for code in np.unique(epsg):
            m = epsg == code
            lon, lat = Transformer.from_crs(f"EPSG:{int(code)}", "EPSG:4326", always_xy=True).transform(cx[m], cy[m])
            pts += list(zip(lon, lat))
    write_footprint(DS, pts, kind="samples", n_total=len(pts),
                    source={"label": "So2Sat LCZ42 v4 *_geo.h5 (Hugging Face)", "url": BASE + "training_geo.h5",
                            "method": "patch centre from each patch's UTM TFW transform (10 m pixels, 32 px) in the geolocation HDF5 files, reprojected to WGS84"},
                    note=f"{len(pts)} patches (" + ", ".join(f"{k} {v}" for k, v in counts.items()) + f") over {len(cities)} cities: "
                         + ", ".join(sorted(cities)) + ".")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
