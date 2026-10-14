"""SustainBench brick kiln classification (Bangladesh) footprint.

The 73,613 64x64 Sentinel-2 chips, their HDF5 `bounds` arrays and the per-image metadata CSV are distributed only
through a Google Drive folder linked from the SustainBench docs, which cannot be fetched from here, and the
SustainBench GitHub repo holds no chip index. The docs state the chips cover Bangladesh, so the country's bounding
box is written (status partial).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "brick-kilns"
W, S, E, N = 88.0, 20.6, 92.7, 26.6  # Bangladesh


def main():
    write_footprint(DS, [(W, S), (E, S), (E, N), (W, N)], kind="bbox", n_total=73613, status="partial",
                    source={"label": "SustainBench brick kiln dataset page", "url": "https://sustainlab-group.github.io/sustainbench/docs/datasets/sdg13/brick_kiln.html",
                            "method": "bounding box of Bangladesh, the coverage stated in the docs; the per-chip bounds live in HDF5/CSV files on Google Drive"},
                    note="6,329 kiln and 67,284 no-kiln 64 px Sentinel-2 chips (Oct 2018-May 2019) over Bangladesh; data on Google Drive (folder 1VvDQHTorD8sa6YJ6_Z9UoEFGu7QpR2dT), not reachable here.")


if __name__ == "__main__":
    main()
