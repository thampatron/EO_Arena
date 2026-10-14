"""SustainBench DHS tasks (asset wealth, child mortality, women BMI, water/sanitation index, education):
the labels file dhs_final_labels.csv and dhs_metadata.csv, which hold the (DHS-jittered) cluster lat/lon of the
~117k clusters in 48-56 countries, are distributed only through a Google Drive folder (link in
sustainbench/datasets/dhs_dataset.py and on the docs page); the underlying DHS GPS data additionally require
DHS Program registration. Google Drive is not reachable here, so no sample-level footprint is written.
The Africa-only predecessor (Yeh et al. 2020, 19,669 clusters) has its own footprint from a public CSV."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

write_footprint("sustainbench-dhs-tasks", [], status="unavailable",
                source={"label": "SustainBench DHS datasets page / dhs_dataset.py download_url", "url": "https://sustainlab-group.github.io/sustainbench/docs/datasets/dhs.html",
                        "method": "cluster coordinates are only in dhs_final_labels.csv / dhs_metadata.csv on Google Drive (folder 1tzWDfd4Y5MvJnJb-lHieOuD-aVcUqzcu), which could not be fetched"},
                note="~87k-117k DHS clusters per task across 48-56 countries (surveys 1996-2019); coordinates are DHS-jittered (2 km urban / 5 km rural). See footprint yeh-et-al-2020 for the 23-country African subset.")
