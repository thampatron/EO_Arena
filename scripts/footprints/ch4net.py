"""CH4Net: the 23 super-emitter sites in Turkmenistan, lon/lat from Table 2 of Vaughan et al. (2024, AMT 17:2583),
published as an xlsx next to the open-access article. Every image in the dataset is a Sentinel-2 crop at one of
these sites, so the sites are the full spatial footprint. The Hugging Face dataset (av555/ch4net) is gated."""
import sys, shutil
from pathlib import Path
import requests, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://amt.copernicus.org/articles/17/2583/2024/amt-17-2583-2024-t02.xlsx"
TMP = Path("/tmp/claude-0/fp/ch4net"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "t02.xlsx"
if not f.exists():
    f.write_bytes(requests.get(URL, timeout=60).content)
d = pd.read_excel(f, header=None)
d = d[d[0].astype(str).str.match(r"^T\d+$")]
pts = [(float(lon), float(lat)) for lon, lat in zip(d[1], d[2])]
assert len(pts) == 23

write_footprint("ch4net", pts, kind="sites", n_total=10046,
                source={"label": "CH4Net paper, Table 2 (site longitude/latitude)", "url": URL,
                        "method": "lon/lat of the 23 super-emitter sites from Table 2 of the AMT paper; all 10,046 images are crops centred on these sites"},
                note="Hugging Face dataset av555/ch4net is gated (login required); site table from the open-access paper used instead. Several sites are within a few km of each other.")
shutil.rmtree(TMP, ignore_errors=True)
