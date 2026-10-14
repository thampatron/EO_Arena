"""Fields of The World footprint: chip polygons from the per-country chips_<country>.parquet GeoParquet files on
source.coop (kerner-lab/fields-of-the-world), one row per 256x256 chip (train/val/test). Centroids are used."""
import sys, re, shutil, time
from pathlib import Path
import requests, geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

DS = "fields-of-the-world"
TMP = Path("/tmp/claude-0/fp") / DS
BASE = "https://data.source.coop/kerner-lab/fields-of-the-world/"


def get(url, dest=None):
    for k in range(4):
        try:
            r = requests.get(url, timeout=120)
            if r.ok:
                if dest: dest.write_bytes(r.content)
                return r
        except requests.RequestException:
            pass
        time.sleep(2 * (k + 1))
    raise RuntimeError(url)


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    listing = get(BASE + "?list-type=2&delimiter=/").text
    countries = re.findall(r"<Prefix>fields-of-the-world/([a-z_]+)/</Prefix>", listing)
    pts, n = [], 0
    for c in countries:
        p = TMP / f"chips_{c}.parquet"
        if not p.exists():
            get(BASE + f"{c}/chips_{c}.parquet", p)
        g = gpd.read_parquet(p)
        if g.crs and g.crs.to_epsg() != 4326:
            g = g.to_crs(4326)
        b = g.geometry.bounds  # chip squares: bbox centre == centroid, without the geographic-CRS warning
        pts += list(zip((b.minx + b.maxx) / 2, (b.miny + b.maxy) / 2)); n += len(g)
        print(f"{c}: {len(g)} chips")
    write_footprint(DS, pts, source={"label": "FTW chips_<country>.parquet GeoParquet files (source.coop)",
                                     "url": BASE + "austria/chips_austria.parquet",
                                     "method": "bbox centres of the chip polygons in the 25 per-country chips_*.parquet files"},
                    kind="samples", n_total=n,
                    note=f"{n} chips across {len(countries)} country/region folders (Corsica is listed separately from France).")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
