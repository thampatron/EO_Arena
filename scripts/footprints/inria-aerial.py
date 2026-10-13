"""Footprint for the Inria Aerial Image Labeling dataset (Maggiori et al. 2017).

The 180 georeferenced 5000x5000 tiles (0.3 m) are distributed only as a 20 GB split 7z archive on
files.inria.fr (no per-tile index), and the Hugging Face mirrors are re-chunked binaries without geolocation.
The dataset page names the 10 cities (36 tiles each: 5 train, 5 test), so one point per city is written.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "inria-aerial"
CITIES = {  # name: (lon, lat, split)
    "Austin, TX": (-97.743, 30.267, "train"), "Chicago, IL": (-87.630, 41.878, "train"),
    "Kitsap County, WA": (-122.640, 47.640, "train"), "Vienna": (16.373, 48.208, "train"),
    "West Tyrol (Landeck/Imst)": (10.566, 47.139, "train"),
    "Bellingham, WA": (-122.488, 48.750, "test"), "Bloomington, IN": (-86.526, 39.165, "test"),
    "Innsbruck": (11.393, 47.268, "test"), "San Francisco, CA": (-122.419, 37.775, "test"),
    "East Tyrol (Lienz)": (12.769, 46.830, "test"),
}


def main():
    write_footprint(DS, [(v[0], v[1]) for v in CITIES.values()], kind="sites", n_total=360, status="partial",
                    source={"label": "Inria Aerial Image Labeling dataset page", "url": "https://project.inria.fr/aerialimagelabeling/",
                            "method": "one point per named city (10 cities, 36 tiles each); the georeferenced tiles are only inside a 20 GB split 7z archive without an index"},
                    note="360 tiles of 1.5 x 1.5 km: train = Austin, Chicago, Kitsap County, Vienna, West Tyrol; test = Bellingham, "
                         "Bloomington, Innsbruck, San Francisco, East Tyrol. City coordinates are approximate centres, not tile positions.")


if __name__ == "__main__":
    main()
