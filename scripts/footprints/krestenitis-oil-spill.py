"""Krestenitis et al. oil spill dataset (MKLab / M4D, CERTH-ITI): ~1,110 JPEG crops of Sentinel-1 scenes around
EMSA CleanSeaNet-confirmed spills in European waters (2015-09 to 2017-10). The data is distributed only by
e-mail application under terms of use; the JPEGs carry no georeferencing and no public list of the EMSA spill
coordinates exists. No footprint can be derived; the paper's region ("European waters") is recorded as a note."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

write_footprint("krestenitis-oil-spill", [], status="unavailable",
                source={"label": "M4D oil spill detection dataset page", "url": "https://m4d.iti.gr/oil-spill-detection-dataset/",
                        "method": "no public index of image locations; access is by e-mail application and the images are non-georeferenced JPEG crops"},
                note="~1,000 train + 110 test JPEG crops of Sentinel-1 scenes at EMSA CleanSeaNet-reported spills in European seas, 2015-09-28 to 2017-10-31. The spill coordinates come from EMSA records that are not published with the dataset.")
