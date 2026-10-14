"""Footprint for DOTA v2 / iSAID (Ding et al. 2021; Zamir et al. 2019).

DOTA images are Google Earth screenshots plus GF-2 / JL-1 scenes and CycloMedia aerial tiles distributed as
plain PNG/JPEG with oriented-box annotations only (Google Drive / Baidu); neither DOTA nor iSAID publishes
image coordinates, acquisition sites or tile ids that encode location. Nothing to extract.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "dota-v2-isaid"


def main():
    write_footprint(DS, [], kind="samples", n_total=5229, status="unavailable",
                    source={"label": "DOTA dataset page", "url": "https://captain-whu.github.io/DOTA/dataset.html",
                            "method": "no coordinates: images are non-georeferenced PNG/JPEG (Google Earth, GF-2, JL-1, aerial) on Google Drive/Baidu with box annotations only"},
                    note="5,229 DOTA-v2 images (iSAID: 2,806 from DOTA-v1) with no public location metadata; described only as "
                         "'global' in the papers.")


if __name__ == "__main__":
    main()
