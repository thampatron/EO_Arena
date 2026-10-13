"""HKH Glacier Mapping (LILA / ICIMOD): the 35 Landsat 7 source tiles are listed by GEE scene id
(LE07_<path><row>_<date>) in conf/masking_paths.yaml of the authors' GitHub repo krisrs1128/glacier_mapping.
Each id is resolved to the scene footprint via the Planetary Computer landsat-c2-l2 STAC (WRS path/row + date)
and the scene centre is recorded. The 14,190 512x512 patches and their geojson metadata are only inside a
69 GB tar.gz on LILA, so patch-level points are not extracted."""
import sys, re, datetime
from pathlib import Path
import requests
from pystac_client import Client
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

YAML = "https://raw.githubusercontent.com/krisrs1128/glacier_mapping/master/conf/masking_paths.yaml"
ids = sorted(set(re.findall(r"LE07_(\d{3})(\d{3})_(\d{8})", requests.get(YAML, timeout=60).text)))
cat = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")

pts, missing = [], []
for path, row, date in ids:
    d = datetime.date(int(date[:4]), int(date[4:6]), int(date[6:]))
    s = cat.search(collections=["landsat-c2-l2"], datetime=f"{d}/{d + datetime.timedelta(days=1)}",
                   query={"landsat:wrs_path": {"eq": path}, "landsat:wrs_row": {"eq": row}, "platform": {"eq": "landsat-7"}}, limit=5)
    items = list(s.items())
    if not items:  # fall back to any Landsat-7 scene of that path/row for the footprint
        s = cat.search(collections=["landsat-c2-l2"], query={"landsat:wrs_path": {"eq": path}, "landsat:wrs_row": {"eq": row}, "platform": {"eq": "landsat-7"}}, limit=1)
        items = list(s.items()); missing.append(f"{path}{row}_{date}")
    if items:
        w, s_, e, n = items[0].bbox
        pts.append(((w + e) / 2, (s_ + n) / 2))

write_footprint("hkh-glacier-mapping", pts, kind="tiles", n_total=14190, status="partial",
                source={"label": "Landsat 7 scene ids in krisrs1128/glacier_mapping conf/masking_paths.yaml, footprints from Planetary Computer STAC", "url": YAML,
                        "method": "centre of each of the 35 Landsat 7 source scenes (WRS-2 path/row + date resolved through the landsat-c2-l2 STAC collection)"},
                note="One point per Landsat scene (~185 km), not per 512 px patch; the 14,190 patches and their geojson metadata sit inside a 69 GB tar.gz (hkh_patches.tar.gz) on LILA." + (f" Scenes not matched on date, footprint from another acquisition: {missing}." if missing else ""))
