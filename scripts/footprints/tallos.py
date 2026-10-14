"""Footprint for TalloS (Bountos et al. 2025, FoMo-Bench).

TalloS is built on the Tallo database (Jucker et al. 2022, Zenodo 6637599): every TalloS sample is a
Sentinel-1/2 + DEM + ERA5 time series around Tallo tree records in areas holding >= 50 trees (~335k of
Tallo's 498,838 records). The TalloS release itself is a Dropbox folder that only downloads as a single
156 GB zip with no index, so the parent Tallo.csv (49 MB; latitude/longitude per tree) is used instead.
Points therefore approximate the TalloS footprint (its sparse-area records are filtered out).
"""
import shutil, sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "tallos"
URL = "https://zenodo.org/records/6637599/files/Tallo.csv?download=1"
TMP = Path("/tmp/claude-0/fp") / DS


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    f = TMP / "Tallo.csv"
    r = requests.get(URL, timeout=600)
    r.raise_for_status()
    f.write_bytes(r.content)
    df = pd.read_csv(f, usecols=["latitude", "longitude"]).dropna()
    write_footprint(DS, list(zip(df["longitude"], df["latitude"])), kind="samples", n_total=335000, status="partial",
                    source={"label": "Tallo database (Jucker et al. 2022), Zenodo 6637599", "url": "https://zenodo.org/records/6637599",
                            "method": "latitude/longitude of every tree record in Tallo.csv, the inventory TalloS samples are centred on (TalloS's own file list is not public)"},
                    note=f"{len(df)} Tallo tree records; TalloS keeps ~335k of them (areas with >= 50 trees, 1,000+ genera) as 2016-2023 "
                         "S1/S2/DEM/ERA5 series. The TalloS archive (FoMo-Bench Dropbox folder, 156 GB zip) has no index, so points are the parent database.")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
