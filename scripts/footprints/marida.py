"""MARIDA: annotation locations from docs/Report_1_Map.html (a Plotly map of every annotated polygon, with lat/lon and
customdata [date, ..., S2 tile, UTM x, UTM y, id]) in the MARIDA code repository archived on Zenodo (5152217).
Annotations are grouped by (date, tile, 2.56 km cell) to approximate the 256x256 px patch centres."""
import sys, re, json, zipfile, io, shutil
from pathlib import Path
from collections import defaultdict
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://zenodo.org/records/5152217/files/marine-debris/marine-debris.github.io-v1.0.0.zip?download=1"
TMP = Path("/tmp/claude-0/fp/marida"); TMP.mkdir(parents=True, exist_ok=True)
z = TMP / "repo.zip"
if not z.exists():
    z.write_bytes(requests.get(URL, timeout=300).content)
with zipfile.ZipFile(z) as zf:
    name = [n for n in zf.namelist() if n.endswith("docs/Report_1_Map.html")][0]
    html = zf.read(name).decode("utf-8", "replace")

lats = [json.loads(x) for x in re.findall(r'"lat":\s*(\[[^\]]*\])', html)]
lons = [json.loads(x) for x in re.findall(r'"lon":\s*(\[[^\]]*\])', html)]
cds = [json.loads(x) for x in re.findall(r'"customdata":\s*(\[\[.*?\]\])', html)]
assert len(lats) == len(lons) == len(cds)

groups = defaultdict(list)
n_ann = 0
for la, lo, cd in zip(lats, lons, cds):
    for lat, lon, row in zip(la, lo, cd):
        n_ann += 1
        key = (row[0], row[3], int(row[4] // 2560), int(row[5] // 2560))
        groups[key].append((lon, lat))
pts = [(sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g)) for g in groups.values()]
write_footprint("marida", pts, kind="samples", n_total=1381,
                source={"label": "MARIDA repository docs/Report_1_Map.html (Zenodo 5152217)", "url": URL,
                        "method": f"{n_ann} annotated-polygon lat/lon points from the Plotly map report, averaged per (date, S2 tile, 2.56 km cell) to approximate the {len(pts)} patch centres"},
                note="Patch centres are approximated from annotation locations (1,457 cells vs 1,381 patches); MARIDA.zip (1.1 GB) was not downloaded.")
shutil.rmtree(TMP, ignore_errors=True)
