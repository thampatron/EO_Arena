"""SEN12MS: 180,662 patch triplets in 252 ROI scenes worldwide. The only distribution (mediaTUM 1474000 /
dataserv.ub.tum.de share m1474000) is twelve season x sensor tar.gz archives (421 GiB) plus seasons.csv (scene
ids and true season only). Patch names (ROIs1158_spring_s2_1_p1) carry no coordinates, no scene-location index is
published, the toolbox notebook that maps the ROIs reads the GeoTIFFs locally, and gzip tars cannot be
range-read, so no sample locations can be derived without downloading the archives."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

write_footprint("sen12ms", [], status="unavailable", n_total=180662,
                source={"label": "SEN12MS mediaTUM record and data share (seasons.csv, SupportingDocument.txt)", "url": "https://mediatum.ub.tum.de/1474000",
                        "method": "no public index of scene or patch coordinates; data only inside 12 tar.gz archives (421 GiB)"},
                note="252 ROI scenes sampled over global land masses in four seasons (2016-2017). seasons.csv on the share lists scene ids and hemisphere-corrected seasons but no coordinates; the authors' Sen12MSOverview notebook derives ROI positions from local GeoTIFF headers.")
