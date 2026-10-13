"""Footprint for Sen2Fire (Xu et al. 2024), Zenodo 10881058.

The only distribution is Sen2Fire.zip (6.3 GB) of 2,466 .npz patches (image/aerosol/label arrays,
no georeferencing; checked via HTTP range reads of the zip). The paper names four study areas in
New South Wales (2019-20 bushfire season) only in a map figure, without coordinates or tile IDs,
so the footprint is the New South Wales bounding box, status partial.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "sen2fire"
# New South Wales, Australia (approximate state bounding box)
W, S, E, N = 141.0, -37.5, 153.64, -28.16


def main():
    pts = [(W, S), (W, N), (E, S), (E, N)]
    write_footprint(DS, pts, kind="bbox", n_total=2466, status="partial",
                    source={"label": "Sen2Fire paper (arXiv 2403.17884), Fig. 1 study areas", "url": "https://arxiv.org/abs/2403.17884",
                            "method": "New South Wales bounding box; the four study areas are shown only as a map figure"},
                    note="2,466 512x512 patches from 4 Sentinel-2 scenes (864/594/504/504; areas 1-2 train, 3 val, 4 test) "
                         "stored as non-georeferenced .npz in a 6.3 GB zip; no coordinates published.")


if __name__ == "__main__":
    main()
