"""Footprint for the Sentinel-2 Cloud Mask Catalogue (Francis et al. 2020, Zenodo 4172871).

Downloads the small shapefiles.zip (1.4 MB: one polygon per subscene, in the tile's UTM CRS),
reprojects each to EPSG:4326 and takes its centroid.
"""
import io, shutil, sys, zipfile
from pathlib import Path

import geopandas as gpd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "s2-cloud-mask-catalogue"
URL = "https://zenodo.org/records/4172871/files/shapefiles.zip?download=1"
TMP = Path("/tmp/claude-0/fp") / DS


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    z = TMP / "shapefiles.zip"
    if not z.exists():
        for _ in range(3):
            try:
                r = requests.get(URL, timeout=120)
                r.raise_for_status()
                z.write_bytes(r.content)
                break
            except requests.RequestException:
                continue
    with zipfile.ZipFile(z) as zf:
        zf.extractall(TMP)
    pts = []
    for shp in sorted((TMP / "shapefiles").glob("*/*.shp")):
        g = gpd.read_file(shp)
        c = gpd.GeoSeries(g.geometry.centroid, crs=g.crs).to_crs(4326)  # centroid in UTM, then to WGS84
        pts.extend([(p.x, p.y) for p in c])
    write_footprint(DS, pts, kind="samples", n_total=len(pts),
                    source={"label": "Zenodo 4172871 shapefiles.zip",
                            "url": URL,
                            "method": "centroid of each subscene polygon in the per-subscene shapefiles (UTM -> WGS84)"},
                    note="513 subscenes (1022x1022 px, Sentinel-2 L1C), randomly sampled over land, 2018.")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
