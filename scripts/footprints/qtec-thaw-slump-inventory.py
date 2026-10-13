"""QTEC retrogressive thaw slump inventory (Xia et al. 2022, ESSD) footprint.

Zenodo record 6397029 ships the 875 slump polygons as RTS_inventory.gpkg (1.6 MB). It is read with geopandas
and one centroid per polygon is written. Temp file deleted afterwards.
"""
import shutil, sys
from pathlib import Path

import geopandas as gpd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "qtec-thaw-slump-inventory"
URL = "https://zenodo.org/api/records/6397029/files/RTS_inventory.gpkg/content"
TMP = Path("/tmp/claude-0/fp") / DS


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    f = TMP / "RTS_inventory.gpkg"
    r = requests.get(URL, timeout=300)
    r.raise_for_status()
    f.write_bytes(r.content)
    g = gpd.read_file(f)
    n = len(g)
    if g.crs is None:
        g = g.set_crs(4326)
    c = g.to_crs(4326).geometry.centroid if g.crs.is_geographic else g.geometry.centroid.to_crs(4326)
    pts = list(zip(c.x, c.y))
    shutil.rmtree(TMP, ignore_errors=True)
    write_footprint(DS, pts, kind="samples", n_total=n,
                    source={"label": "Zenodo 6397029, RTS_inventory.gpkg", "url": "https://zenodo.org/records/6397029",
                            "method": "centroid of each thaw-slump polygon in the GeoPackage"},
                    note=f"{n} slump polygons along the Qinghai-Tibet Engineering Corridor (PlanetScope 2019 mapping).")


if __name__ == "__main__":
    main()
