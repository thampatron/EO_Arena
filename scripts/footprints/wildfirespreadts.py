"""WildfireSpreadTS footprint. The Zenodo release is a single 48 GB zip with no index, but the TACO repackaging on
Hugging Face (isp-uv-es/wildfirespreadts-taco) carries a 62 KB .tacocat/sample.parquet with one row per fire event
and its centre lon/lat (ml:lon, ml:lat)."""
import sys, shutil
from pathlib import Path
import pandas as pd, requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

DS = "wildfirespreadts"
TMP = Path("/tmp/claude-0/fp") / DS
URL = "https://huggingface.co/datasets/isp-uv-es/wildfirespreadts-taco/resolve/main/.tacocat/sample.parquet"


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    p = TMP / "sample.parquet"
    if not p.exists():
        r = requests.get(URL, timeout=120); r.raise_for_status(); p.write_bytes(r.content)
    df = pd.read_parquet(p, columns=["ml:fire_id", "ml:lon", "ml:lat"])
    pts = df[["ml:lon", "ml:lat"]].values.tolist()
    write_footprint(DS, pts, source={"label": "WildfireSpreadTS TACO repackaging, .tacocat/sample.parquet",
                                     "url": URL,
                                     "method": "ml:lon/ml:lat centre of each of the 607 fire-event rasters in the TACO sample index"},
                    kind="samples", n_total=len(df),
                    note="One point per fire event (raster 111-128 km across). Index comes from the ISP-UV TACO repackaging of the Zenodo release, not the Zenodo zip itself.")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
