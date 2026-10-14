"""Open Cities AI Challenge footprint.

The dataset lives on source.coop (open-cities/ai-challenge) as a STAC catalog: one item JSON per training drone
mosaic (train_tier_1 + train_tier_2, 10 African cities, label items beside them) and one per 1024x1024 test chip.
The test items carry a dummy (0,0)-(0.045,0.045) geometry because the competition hid test locations, so only the
training-scene items (a few KB each) are read and each polygon centroid taken. Imagery is never touched.
"""
import re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "open-cities-ai"
B = "https://data.source.coop/open-cities/ai-challenge/"


def list_keys(prefix):
    keys, marker = [], None
    while True:
        t = requests.get(B + f"?prefix={prefix}" + (f"&marker={marker}" if marker else ""), timeout=60).text
        page = re.findall(r"<Key>(.*?)</Key>", t)
        keys += page
        if "<IsTruncated>true</IsTruncated>" not in t or not page:
            break
        marker = page[-1].split("ai-challenge/", 1)[1]
    return keys


def item_centroid(key):
    url = B + key.split("ai-challenge/", 1)[1]
    for _ in range(3):
        try:
            j = requests.get(url, timeout=60).json()
            c = shape(j["geometry"]).centroid
            return (c.x, c.y)
        except Exception:
            pass
    return None


def main():
    train = [k for p in ("train_tier_1/", "train_tier_2/") for k in list_keys(p)
             if k.endswith(".json") and "-labels" not in k and not k.endswith(("catalog.json", "collection.json"))]
    n_test = sum(1 for k in list_keys("test/") if k.endswith(".json") and not k.endswith(("catalog.json", "collection.json")))
    with ThreadPoolExecutor(8) as ex:
        pts = [p for p in ex.map(item_centroid, train) if p]
    write_footprint(DS, pts, kind="tiles", n_total=len(train) + n_test, status="partial",
                    source={"label": "Open Cities AI Challenge STAC items on source.coop", "url": "https://source.coop/open-cities/ai-challenge",
                            "method": f"polygon centroids of the {len(train)} training-scene STAC items (tier 1 + tier 2 drone mosaics)"},
                    note=f"{len(train)} training mosaics over 10 cities (Accra, Dar es Salaam, Kampala, Monrovia, Niamey, Pointe-Noire, Zanzibar, ...) hold the ~790k building labels; the {n_test} test chips have a dummy (0,0) geometry in their STAC items, so they are not placed.")


if __name__ == "__main__":
    main()
