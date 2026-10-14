"""Landslide4Sense: the 4,844 128x128 patches are distributed as bare HDF5 arrays (image_N.h5 / mask_N.h5, mirrored
at huggingface.co/datasets/ibm-nasa-geospatial/Landslide4sense) with no georeference or site label, so patch
locations cannot be recovered. The four landslide-affected regions named in the paper are written as sites."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

PAPER = "https://arxiv.org/abs/2206.00515"
SITES = {"Iburi-Tobu, Hokkaido (2018 earthquake)": (142.0, 42.75), "Kodagu, Karnataka (2018 monsoon)": (75.74, 12.42),
         "Gorkha, Nepal (2015 earthquake)": (84.7, 28.0), "Taiwan (2009 typhoon Morakot)": (120.9, 23.3)}
write_footprint("landslide4sense", list(SITES.values()), kind="sites", n_total=4844, status="partial",
                source={"label": "Landslide4Sense paper (Ghorbanzadeh et al. 2022)", "url": PAPER,
                        "method": "approximate centre of each of the four event regions named in the paper; the released patches carry no coordinates"},
                note="3,799 train / 245 val / 800 test patches of 1.28 km (S2 + ALOS PALSAR slope/DEM); the per-patch region is not published.")
