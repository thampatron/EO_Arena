"""SICKLE (Sani et al. 2024, WACV) footprint.

The dataset (388 surveyed plots, 2,370 time-series samples) is released only through a Google Form request and
Google Drive, and the GitHub repo holds no plot coordinates, so no sample points can be read. The paper and
README place all plots in the Cauvery Delta region of Tamil Nadu, India; an approximate bounding box of the
delta (Thanjavur-Tiruvarur-Nagapattinam-Mayiladuthurai districts) is written (status partial).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "sickle-paddy-classification"
W, S, E, N = 78.9, 10.2, 79.9, 11.3  # Cauvery Delta, Tamil Nadu


def main():
    write_footprint(DS, [(W, S), (E, S), (E, N), (W, N)], kind="bbox", n_total=388, status="partial",
                    source={"label": "SICKLE README / paper study-area description", "url": "https://github.com/Depanshu-Sani/SICKLE",
                            "method": "approximate bounding box of the Cauvery Delta region named as the study area; plot coordinates are only in the form-gated Google Drive release"},
                    note="388 surveyed paddy plots (avg 0.38 acre), 2,370 time-series samples, Jan 2018-Mar 2021; data access requires a Google Form and Google Drive download, not used.")


if __name__ == "__main__":
    main()
