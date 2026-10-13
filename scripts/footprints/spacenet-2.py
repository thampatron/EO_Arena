"""SpaceNet 2 (building footprints; Las Vegas, Paris, Shanghai, Khartoum): chip centres (ml:lon, ml:lat) for all
10,593 labelled chips from .tacocat/sample.parquet (21 MB) of the TACO repackaging on Hugging Face
(isp-uv-es/spacenet2-taco). The 3,525 test_public chips in the AWS bucket have no public labels and are not in
the repackaging; they lie in the same four AOIs."""
import sys, time, shutil
from pathlib import Path
import requests, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/isp-uv-es/spacenet2-taco/resolve/main/.tacocat/sample.parquet"
TMP = Path("/tmp/claude-0/fp/spacenet-2"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "sample.parquet"
if not f.exists():
    for i in range(6):
        r = requests.get(URL, timeout=300, headers={"User-Agent": "curl/8"})
        if r.status_code == 200:
            f.write_bytes(r.content); break
        time.sleep(5 * (i + 1))
    r.raise_for_status()

d = pd.read_parquet(f, columns=["ml:split", "ml:city", "ml:lon", "ml:lat"])
pts = list(zip(d["ml:lon"].astype(float), d["ml:lat"].astype(float)))

write_footprint("spacenet-2", pts, kind="tiles", n_total=len(d),
                source={"label": "SpaceNet 2 TACO repackaging, .tacocat/sample.parquet (Hugging Face isp-uv-es/spacenet2-taco)", "url": URL,
                        "method": "centre lon/lat (ml:lon, ml:lat) of every labelled 200 m chip in the four AOIs"},
                note=f"Chips per city: {d['ml:city'].value_counts().to_dict()}; splits {d['ml:split'].value_counts().to_dict()}. The 3,525 unlabelled test_public chips on AWS (14,118 chips in total) fall in the same AOIs.")
shutil.rmtree(TMP, ignore_errors=True)
