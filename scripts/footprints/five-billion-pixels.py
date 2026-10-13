"""Footprint for Five-Billion-Pixels (Tong et al. 2023, ISPRS), 150 Gaofen-2 scenes over China.

The official release (incl. the separately announced "coordinate information") is Google Drive / Baidu only.
The Hugging Face mirror yuxuanw8/FBP (44 GB zip, 1.09 M 96x96 patches from 139 scenes) was inspected via
HTTP range reads of its central directory: the patches are tifffile exports with no CRS/geotransform and
metadata.csv lists only split/paths. GF-2 product ids (L1A000xxxxxxx) do not encode location. Only the
paper's statement (scenes spread across China, >50,000 km2) remains, written as the mainland China bbox.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "five-billion-pixels"
CHINA = [(73.5, 18.0), (135.1, 18.0), (135.1, 53.6), (73.5, 53.6)]


def main():
    write_footprint(DS, CHINA, kind="bbox", n_total=150, status="partial",
                    source={"label": "Five-Billion-Pixels project page", "url": "https://x-ytong.github.io/project/Five-Billion-Pixels.html",
                            "method": "mainland China bounding box; the scene coordinate file is only on Google Drive/Baidu and the HF mirror's patches are not georeferenced"},
                    note="150 GF-2 scenes (6800x7200 px, 4 m) across China; the project page announces a coordinate file but it is "
                         "distributed only via Google Drive / Baidu, which this environment cannot reach.")


if __name__ == "__main__":
    main()
