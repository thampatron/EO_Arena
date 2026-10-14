"""Footprint for the CAS Landslide Dataset (Xu et al. 2024, Sci Data), Zenodo 10294997.

The record ships "study areas shp.zip" (27 KB): one polygon per study area / sensor (11 shapefiles for the
9 regions; Moxi town and Tiburon Peninsula appear twice for different sensors). Each polygon centroid is one
site point. The 20,865 image chips themselves live in per-region zips (25 MB - 2 GB) as non-indexed images.
"""
import glob, shutil, sys, zipfile
from pathlib import Path

import geopandas as gpd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "cas-landslide"
URL = "https://zenodo.org/api/records/10294997/files/study%20areas%20shp.zip/content"
TMP = Path("/tmp/claude-0/fp") / DS


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    z = TMP / "shp.zip"
    z.write_bytes(requests.get(URL, timeout=120).content)
    zipfile.ZipFile(z).extractall(TMP)
    pts, names = [], []
    for shp in sorted(glob.glob(str(TMP / "**" / "*.shp"), recursive=True)):
        g = gpd.read_file(shp)
        c = g.to_crs(3857).geometry.centroid.to_crs(4326)
        pts += list(zip(c.x, c.y))
        names.append(Path(shp).stem.replace("_", " "))
    write_footprint(DS, pts, kind="sites", n_total=20865, status="partial",
                    source={"label": "CAS Landslide study-area shapefiles (Zenodo)", "url": "https://zenodo.org/records/10294997",
                            "method": "centroid of each study-area polygon in 'study areas shp.zip' (one per region/sensor), reprojected to WGS84"},
                    note=f"{len(pts)} study-area polygons for the 9 regions ({'; '.join(names)}); the 20,865 chips are not individually "
                         "georeferenced in a public index, so points are site centroids, not samples.")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
