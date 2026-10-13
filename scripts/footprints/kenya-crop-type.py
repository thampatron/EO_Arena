"""Kenya crop type (SustainBench crop_type_kenya): the data (crop_type_kenya_2017_metadata.csv + per-field npz
time series) are distributed only through a Google Drive folder, which cannot be fetched here, and no public index
of field locations exists. The three surveyed counties named on the dataset page are written as sites (partial)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

PAGE = "https://sustainlab-group.github.io/sustainbench/docs/datasets/sdg2/crop_type_mapping_kenya.html"
# county centres (lon, lat); fields per county from the dataset page
SITES = {"Bungoma": ((34.56, 0.57), 2098), "Busia": ((34.11, 0.46), 1957), "Siaya": ((34.29, 0.06), 1638)}
write_footprint("kenya-crop-type", [v[0] for v in SITES.values()], kind="sites", n_total=5693, status="partial",
                source={"label": "SustainBench crop type mapping (Kenya) page", "url": PAGE,
                        "method": "approximate centre of each of the three surveyed counties (Bungoma, Busia, Siaya) named on the dataset page; field coordinates are not publicly indexed"},
                note="5,693 fields / 39,568 S2 pixel time series (2017): Bungoma 2,098, Busia 1,957, Siaya 1,638 fields. Data only on Google Drive (drive.google.com/drive/folders/1Rq1F-ys-rkjftAUnbdGJ1T6udsZWnEyo), not downloadable from this environment.")
