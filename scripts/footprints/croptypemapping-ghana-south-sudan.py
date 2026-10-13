"""Footprint for CropTypeMapping Ghana / South Sudan (Rustowicz et al. 2019; SustainBench).

SustainBench serves the data only from a Google Drive folder, and the original Radiant MLHub records
(10.34911/rdnt.ry138p, rdnt.v6kx6n) are offline and not archived on source.coop. The original repo's
dataset_splits/*.txt list 3,563 64x64 tile ids without coordinates. The CVPRW 2019 paper (Fig. 1) maps the
fields (jittered up to 3 km) over northern Ghana (1 W-0.5 E, 9-10 N) and South Sudan (24-36 E, 4-12 N);
those two frames are written as bounding boxes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "croptypemapping-ghana-south-sudan"
BOXES = {"northern Ghana": (-1.0, 9.0, 0.5, 10.0), "South Sudan": (24.0, 4.0, 36.0, 12.0)}


def main():
    pts = []
    for w, s, e, n in BOXES.values():
        pts += [(w, s), (e, s), (e, n), (w, n)]
    write_footprint(DS, pts, kind="bbox", n_total=3563, status="partial",
                    source={"label": "Rustowicz et al. 2019 (CVPRW), Figure 1 map frames",
                            "url": "https://openaccess.thecvf.com/content_CVPRW_2019/papers/cv4gc/Rustowicz_Semantic_Segmentation_of_Crop_Type_in_Africa_A_Novel_Dataset_CVPRW_2019_paper.pdf",
                            "method": "corners of the two map frames in the paper's Figure 1 (northern Ghana; South Sudan); no public coordinate index"},
                    note="3,563 64x64 tiles (Ghana 2,878; South Sudan 685) listed by id only in roserustowicz/crop-type-mapping; imagery and "
                         "labels are on Google Drive (SustainBench) and the Radiant MLHub records are offline. Field locations were "
                         "jittered up to 3 km for anonymity even in the paper.")


if __name__ == "__main__":
    main()
