"""SustainBench crop yield: the county-level histograms, yields and keys (<country>_keys.npz with county ids) are
distributed only through a Google Drive folder, which cannot be fetched here; no public list of the counties/
departments exists outside it. One approximate point per country's soybean belt is written (partial)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

PAGE = "https://sustainlab-group.github.io/sustainbench/docs/datasets/sdg2/crop_yield.html"
SITES = {"US Corn Belt (county level)": (-91.5, 41.0), "Argentina Pampas (department level)": (-61.0, -33.0),
         "Brazil soybean states (microregion level)": (-52.0, -18.0)}
write_footprint("sustainbench-crop-yield", list(SITES.values()), kind="sites", n_total=11048, status="partial",
                source={"label": "SustainBench crop yield prediction page", "url": PAGE,
                        "method": "one approximate point per country soybean region (US, Argentina, Brazil); the administrative-unit keys are only inside the Google Drive download"},
                note="11,048 county-years of soybean yield (2005-16) over US counties, Argentine departments and Brazilian microregions; MODIS histograms. Data only on Google Drive (drive.google.com/drive/folders/1hsp2PlXAgcQ0pbx_vvPKHZcj_Am3rWx4), not downloadable from this environment.")
