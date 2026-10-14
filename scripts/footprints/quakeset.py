"""Footprint for QuakeSet (Cambrin & Garza 2024), Hugging Face DarthReca/quakeset.

Reads epicenters.parquet (16 MB): one row per sample with per-pixel lon/lat arrays; the patch
centre is the mean of those arrays.
"""
import shutil, sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "quakeset"
URL = "https://huggingface.co/datasets/DarthReca/quakeset/resolve/main/epicenters.parquet"
TMP = Path("/tmp/claude-0/fp") / DS


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    f = TMP / "epicenters.parquet"
    if not f.exists():
        r = requests.get(URL, timeout=120)
        r.raise_for_status()
        f.write_bytes(r.content)
    d = pd.read_parquet(f)
    pts = [(float(np.mean(lo)), float(np.mean(la))) for lo, la in zip(d["lon"], d["lat"])]
    write_footprint(DS, pts, kind="samples", n_total=len(d),
                    source={"label": "QuakeSet epicenters.parquet (Hugging Face)", "url": URL,
                            "method": "mean of the per-pixel lon/lat arrays stored for each Sentinel-1 patch"},
                    note="3,327 patches around 155 earthquakes (pre/post Sentinel-1 pairs).")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
