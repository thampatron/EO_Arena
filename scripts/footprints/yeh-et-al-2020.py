"""Footprint for Yeh et al. 2020 (Nat. Comms, "Using publicly available satellite imagery and deep
learning to understand economic well-being in Africa"), GitHub sustainlab-group/africa_poverty.

Reads data/dhs_clusters.csv (one row per DHS cluster/village with lat, lon, country, year).
"""
import io, sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "yeh-et-al-2020"
URL = "https://raw.githubusercontent.com/sustainlab-group/africa_poverty/master/data/dhs_clusters.csv"


def main():
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    pts = list(zip(d["lon"], d["lat"]))
    write_footprint(DS, pts, kind="samples", n_total=len(d),
                    source={"label": "africa_poverty/data/dhs_clusters.csv (GitHub)", "url": URL,
                            "method": "DHS cluster lat/lon from the repository's cluster table (one row per village)"},
                    note=f"{len(d)} DHS clusters, {d['country'].nunique()} countries, surveys {d['year'].min()}-{d['year'].max()}; "
                         "DHS coordinates are jittered up to 2 km (urban) / 5 km (rural).")


if __name__ == "__main__":
    main()
