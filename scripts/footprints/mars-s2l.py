"""MARS-S2L footprint: plume/no-plume Sentinel-2 + Landsat chips located by the lon/lat columns of the
train/val/test CSVs on the Hugging Face repo (UNEP-IMEO/MARS-S2L)."""
import sys, io, shutil
from pathlib import Path
import pandas as pd, requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

DS = "mars-s2l"
TMP = Path("/tmp/claude-0/fp") / DS
BASE = "https://huggingface.co/datasets/UNEP-IMEO/MARS-S2L/resolve/main/"
SPLITS = ["train.csv", "val.csv", "test.csv"]


def fetch(name):
    TMP.mkdir(parents=True, exist_ok=True)
    p = TMP / name
    if not p.exists():
        r = requests.get(BASE + name, timeout=120)
        r.raise_for_status()
        p.write_bytes(r.content)
    return p


def main():
    pts, n = [], 0
    for s in SPLITS:
        df = pd.read_csv(fetch(s), usecols=["lon", "lat"])
        n += len(df)
        pts += df[["lon", "lat"]].dropna().values.tolist()
    write_footprint(DS, pts, source={"label": "MARS-S2L train/val/test CSVs (Hugging Face)",
                                     "url": BASE + "train.csv",
                                     "method": "lon/lat columns of the train, val and test CSVs (one row per image chip)"},
                    kind="samples", n_total=n,
                    note="Chips cluster on monitored oil/gas and coal sites; each site has many revisits, so distinct locations are far fewer than rows.")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
