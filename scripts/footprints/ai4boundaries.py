"""Footprint for AI4Boundaries (d'Andrimont et al. 2023, ESSD), JRC open data FTP.

sampling/ai4boundaries_sampling.gpkg (2.4 MB, EPSG:3035) holds one polygon per sample (7,831 = the
paper's sample count, one 4 km x 4 km cell each, with country in `adm`). Centroids -> WGS84.
"""
import shutil, sys
from pathlib import Path

import geopandas as gpd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "ai4boundaries"
URL = "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/DRLL/AI4BOUNDARIES/sampling/ai4boundaries_sampling.gpkg"
TMP = Path("/tmp/claude-0/fp") / DS


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    f = TMP / "sampling.gpkg"
    with requests.get(URL, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(f, "wb") as fh:
            shutil.copyfileobj(r.raw, fh)
    g = gpd.read_file(f)
    c = g.geometry.centroid.to_crs(4326)
    counts = g["adm"].value_counts().to_dict()
    write_footprint(DS, list(zip(c.x, c.y)), kind="samples", n_total=len(g),
                    source={"label": "AI4Boundaries sampling GeoPackage (JRC FTP)", "url": URL,
                            "method": "centroid of each sample polygon in ai4boundaries_sampling.gpkg (EPSG:3035 -> WGS84)"},
                    note=f"{len(g)} samples (4 km cells), 2019: " + ", ".join(f"{k} {v}" for k, v in counts.items()) + ".")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
