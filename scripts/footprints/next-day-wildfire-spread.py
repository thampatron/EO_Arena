"""Footprint for Next Day Wildfire Spread (Huot et al. 2022).

The dataset is distributed only on Kaggle (fantinehuot/next-day-wildfire-spread) as TFRecords of 64x64 px
(1 km) feature/fire-mask arrays with no coordinates or dates; the Google Earth Engine export code in
google-research/google-research/simulation_research/next_day_wildfire_spread samples fires from MODIS
across the contiguous US. Only the CONUS bounding box can be stated.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "next-day-wildfire-spread"
CONUS = [(-125.0, 24.5), (-66.9, 24.5), (-66.9, 49.4), (-125.0, 49.4)]


def main():
    write_footprint(DS, CONUS, kind="bbox", n_total=18545, status="partial",
                    source={"label": "Next Day Wildfire Spread (arXiv 2112.02447)", "url": "https://arxiv.org/abs/2112.02447",
                            "method": "contiguous-US bounding box from the paper; the Kaggle TFRecords carry no coordinates and Kaggle is not reachable here"},
                    note="18,545 samples (64 km x 64 km, 2012-2020; train 14,979 / eval 1,877 / test 1,689) of MODIS fire masks and "
                         "drivers over CONUS; sample locations are not published.")


if __name__ == "__main__":
    main()
