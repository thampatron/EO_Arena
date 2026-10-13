"""Footprint for MADOS (Kikaki et al. 2024), Zenodo 10664073.

No usable index: the only distribution is a 4 GB MADOS.zip whose patch GeoTIFFs (checked via HTTP
range reads of the zip's central directory and a few members) carry no geotransform, scenes are
anonymised as Scene_0..Scene_173, and neither the GitHub repo (gkakogeorgiou/mados), the project
page nor the Zenodo description lists tile IDs or coordinates.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "mados"


def main():
    write_footprint(DS, [], status="unavailable", kind="samples", n_total=2803,
                    source={"label": "MADOS on Zenodo", "url": "https://zenodo.org/records/10664073",
                            "method": "no coordinates recoverable: patch GeoTIFFs in MADOS.zip are not georeferenced and scenes are anonymised"},
                    note="2,803 patches from 174 anonymised Sentinel-2 scenes (47 tiles, 2015-2022), globally distributed per the "
                         "paper; the ISPRS paper's location map is an image only. A 4 GB zip with no index; not downloaded.")


if __name__ == "__main__":
    main()
