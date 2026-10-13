"""xView3-SAR (Paolo et al. 2022) footprint.

Scenes, labels (train/validation CSVs with detect_lat/detect_lon) and the scene list are only downloadable after
registering at https://iuu.xview.us/, and no public mirror or STAC index exists, so no sample points are read.
The paper (Table 2 / Fig. 4) names five regional groupings; one approximate centre per region is written as
sites (status partial).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "xview3-sar"
SITES = {  # approximate centre of each region named in the paper
    "Adriatic Sea": (15.0, 43.5),
    "Bay of Biscay": (-4.0, 46.0),
    "Gulf of Guinea (West Africa)": (3.0, 4.0),
    "Iceland": (-20.0, 64.5),
    "Norway (North Sea / Norwegian Sea)": (5.0, 60.5),
}


def main():
    write_footprint(DS, list(SITES.values()), kind="sites", n_total=991, status="partial",
                    source={"label": "xView3-SAR paper (arXiv 2206.00897), Table 2 regions", "url": "https://arxiv.org/abs/2206.00897",
                            "method": "one hand-placed centre per region named in the paper; scene footprints and label CSVs are behind registration at iuu.xview.us"},
                    note="991 Sentinel-1 scenes, 243,018 objects, over five regional groupings: " + "; ".join(SITES) + ". Per-scene coordinates not public without an account.")


if __name__ == "__main__":
    main()
