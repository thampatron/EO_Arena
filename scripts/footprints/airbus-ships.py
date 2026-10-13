"""Airbus Ship Detection (Kaggle challenge, 2018; used by SatlasPretrain as 'Airbus Ships'): 192,556 768x768 px
JPEG crops of Airbus SPOT/Pleiades imagery with run-length-encoded ship masks. The images are not georeferenced,
the only distribution is Kaggle (login required, not reachable here), and neither the competition page nor the
SatlasPretrain paper gives locations, so no footprint can be derived."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

write_footprint("airbus-ships", [], status="unavailable",
                source={"label": "Kaggle Airbus Ship Detection Challenge", "url": "https://www.kaggle.com/c/airbus-ship-detection",
                        "method": "no georeferencing in the JPEG crops and no public index of image locations; Kaggle download not accessible"},
                note="~192k 768x768 px crops with RLE ship masks (train_ship_segmentations_v2.csv); locations are not disclosed by Airbus.")
