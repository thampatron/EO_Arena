"""Sen1Floods11 footprint: chip centres from the STAC catalog (catalog.zip, 10 MB) in the public GCS bucket
gs://sen1floods11/v1.1/. Each *_source item carries a WGS84 bbox; hand-labelled (446) and weakly-labelled (4,385)
chips are both included."""
import sys, json, zipfile, shutil
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

DS = "sen1floods11"
TMP = Path("/tmp/claude-0/fp") / DS
URL = "https://storage.googleapis.com/sen1floods11/v1.1/catalog.zip"


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    zp = TMP / "catalog.zip"
    if not zp.exists():
        r = requests.get(URL, timeout=300); r.raise_for_status(); zp.write_bytes(r.content)
    z = zipfile.ZipFile(zp)
    seen, pts, n_hand = set(), [], 0
    for name in z.namelist():
        if not (name.endswith(".json") and "_source/" in name) or name.startswith("__MACOSX"):
            continue
        chip = name.rsplit("/", 1)[-1][:-5]
        if chip in seen:
            continue
        seen.add(chip)
        item = json.loads(z.read(name))
        if item.get("type") != "Feature":  # collection.json
            continue
        w, s, e, n = item["bbox"]
        pts.append(((w + e) / 2, (s + n) / 2))
        n_hand += "hand_labeled" in name
    write_footprint(DS, pts, source={"label": "Sen1Floods11 STAC catalog (GCS bucket sen1floods11/v1.1/catalog.zip)",
                                     "url": URL,
                                     "method": "bbox centres of every *_source STAC item (one per 512x512 chip)"},
                    kind="samples", n_total=len(pts),
                    note=f"{n_hand} hand-labelled and {len(pts) - n_hand} weakly-labelled chips across 11 flood events.")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
