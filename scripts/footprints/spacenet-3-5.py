"""SpaceNet 3 (roads) and SpaceNet 5 (roads + speed) footprint.

Both live in the public s3://spacenet-dataset bucket (HTTPS listing, no credentials). The per-AOI label CSVs
hold pixel-space WKT only, so the PS-RGB GeoTIFFs are listed per AOI (train + test_public, 7 AOIs) and an even
subsample of up to 300 of them is opened with rasterio over /vsicurl; only the header is read and each chip's
centre is reprojected to WGS84 (chips are 400 m tiles, 10 MB each, but only a few KB per header move).
"""
import re, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import rasterio, requests
from rasterio.warp import transform

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "spacenet-3-5"
B = "https://spacenet-dataset.s3.amazonaws.com/"
CAP = 300
AOIS = [("SN3_roads", s, a) for s in ("train", "test_public") for a in ("AOI_2_Vegas", "AOI_3_Paris", "AOI_4_Shanghai", "AOI_5_Khartoum")] + \
       [("SN5_roads", "train", a) for a in ("AOI_7_Moscow", "AOI_8_Mumbai")] + \
       [("SN5_roads", "test_public", a) for a in ("AOI_7_Moscow", "AOI_8_Mumbai", "AOI_9_San_Juan")]


def list_keys(prefix):
    keys, marker = [], None
    while True:
        t = requests.get(B + f"?prefix={prefix}" + (f"&marker={marker}" if marker else ""), timeout=60).text
        page = re.findall(r"<Key>(.*?)</Key>", t)
        keys += page
        if "<IsTruncated>true</IsTruncated>" not in t or not page:
            break
        marker = page[-1]
    return keys


def centre(key):
    try:
        with rasterio.open("/vsicurl/" + B + key) as s:
            b = s.bounds
            lon, lat = transform(s.crs, "EPSG:4326", [(b.left + b.right) / 2], [(b.bottom + b.top) / 2])
            return (lon[0], lat[0])
    except Exception as e:
        print("skip", key, e)
        return None


def main():
    groups = {}
    for ds, split, aoi in AOIS:
        ks = [k for k in list_keys(f"spacenet/{ds}/{split}/{aoi}/PS-RGB/") if k.endswith(".tif")]
        groups[(ds, split, aoi)] = sorted(ks)
    n_total = sum(len(v) for v in groups.values())
    sample = []
    for g, ks in groups.items():
        n = max(1, round(CAP * len(ks) / n_total))
        step = max(1, len(ks) // n)
        sample += ks[::step][:n]
    sample = sample[:CAP]
    with ThreadPoolExecutor(8) as ex:
        pts = [p for p in ex.map(centre, sample) if p]
    counts = ", ".join(f"{a} {len(ks)}" for (ds, s, a), ks in groups.items())
    write_footprint(DS, pts, kind="tiles", n_total=n_total, status="partial",
                    source={"label": "spacenet-dataset S3 bucket, SN3_roads and SN5_roads PS-RGB GeoTIFFs", "url": B + "?prefix=spacenet/SN3_roads/",
                            "method": f"chip centres from the GeoTIFF headers of an even {len(sample)}-of-{n_total} subsample of PS-RGB tiles across the 7 AOIs (train + test_public), read over /vsicurl"},
                    note=f"{n_total} PS-RGB chips: {counts}. SN3 = Vegas, Paris, Shanghai, Khartoum; SN5 = Moscow, Mumbai, San Juan.")


if __name__ == "__main__":
    main()
