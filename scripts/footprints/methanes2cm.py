"""MethaneS2CM footprint: 32x32 Sentinel-2 patches around Carbon Mapper plumes, located by the latitude/longitude
columns of the split CSVs on the Hugging Face repo (H1deaki/MethaneS2CM). Union of the three splits' train+test CSVs."""
import sys, shutil
from pathlib import Path
import pandas as pd, requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

DS = "methanes2cm"
TMP = Path("/tmp/claude-0/fp") / DS
BASE = "https://huggingface.co/datasets/H1deaki/MethaneS2CM/resolve/main/"
FILES = [f"{d}/{s}.csv" for d in ("l1c_temporal_split_32x32", "l2a_temporal_split_32x32", "l2a_location_split_32x32")
         for s in ("train", "test")]


def fetch(name):
    TMP.mkdir(parents=True, exist_ok=True)
    p = TMP / name.replace("/", "_")
    if not p.exists():
        r = requests.get(BASE + name, timeout=120)
        r.raise_for_status()
        p.write_bytes(r.content)
    return p


def main():
    pts, n = [], 0
    for f in FILES:
        df = pd.read_csv(fetch(f), usecols=["latitude", "longitude"])
        n += len(df)
        pts += df[["longitude", "latitude"]].dropna().values.tolist()
    write_footprint(DS, pts, source={"label": "MethaneS2CM split CSVs (Hugging Face)",
                                     "url": BASE + "l2a_location_split_32x32/train.csv",
                                     "method": "latitude/longitude columns of the train/test CSVs of the three splits (one row per patch)"},
                    kind="samples", n_total=n,
                    note="n_total counts rows across all three splits (patches are augmented crops of ~7k raw samples), so the same plume appears many times.")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
