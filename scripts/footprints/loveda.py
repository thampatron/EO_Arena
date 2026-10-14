"""LoveDA (Wang et al. 2021) footprint.

Zenodo 5706578 holds Train/Val/Test zips (4.0, 2.4, 3.1 GB) of 1024x1024 PNG images with no georeferencing and no
location index, so no per-image points can be read. The dataset covers urban and rural scenes of three Chinese
cities named in the paper; one city-centre point each is written as sites (status partial).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "loveda"
SITES = {"Nanjing": (118.80, 32.06), "Changzhou": (119.97, 31.81), "Wuhan": (114.31, 30.59)}


def main():
    write_footprint(DS, list(SITES.values()), kind="sites", n_total=5987, status="partial",
                    source={"label": "LoveDA paper city list; data on Zenodo 5706578", "url": "https://zenodo.org/records/5706578",
                            "method": "one city-centre point per city named in the paper; the PNG images carry no georeferencing and Zenodo has no location index"},
                    note="5,987 0.3 m images (2,522 train / 1,669 val / 1,796 test) over urban and rural districts of Nanjing, Changzhou and Wuhan (Jiangsu/Hubei, China).")


if __name__ == "__main__":
    main()
