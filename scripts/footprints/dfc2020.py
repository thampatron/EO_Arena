"""DFC2020 (2020 IEEE GRSS Data Fusion Contest) footprint.

The 6,114 validation+test patches (986 + 5,128) were released without geolocation on purpose (IEEE DataPort,
login; also rehosted in Copernicus-Bench on Hugging Face, where the GeoTIFFs carry an identity transform, as
checked on S1 and label tiles). The contest outcome paper (Robinson et al. 2021, Fig. 2) names the seven cities,
so one point per city is written as sites (status partial).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "dfc2020"
SITES = {
    "Khabarovsk, Russia": (135.07, 48.48),
    "Mumbai, India": (72.88, 19.08),
    "Kippa-Ring, Australia": (153.08, -27.22),
    "Mexico City, Mexico": (-99.13, 19.43),
    "Bandar Anzali, Iran": (49.46, 37.47),
    "Black Forest, Germany": (8.20, 48.00),
    "Cape Town, South Africa": (18.42, -33.93),
}


def main():
    write_footprint(DS, list(SITES.values()), kind="sites", n_total=6114, status="partial",
                    source={"label": "Robinson et al. 2021 (contest outcome paper), Fig. 2 region list", "url": "https://ieeexplore.ieee.org/document/9369830",
                            "method": "one city-centre point per region named in the outcome paper; the released patches deliberately carry no georeferencing"},
                    note="6,114 256 px S1+S2 patches (986 validation, 5,128 test) from seven cities: " + "; ".join(SITES) + ". Copernicus-Bench rehost on Hugging Face (dfc2020.zip, 8.8 GB) has identity geotransforms.")


if __name__ == "__main__":
    main()
