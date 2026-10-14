"""PhenoCam Dataset v2.0 (393 cameras, data through 2018): the ORNL DAAC release is behind an Earthdata login and
the paper has no site table, so camera locations come from the live PhenoCam network ROI list API
(https://phenocam.nau.edu/api/roilists/), keeping every site that has a region of interest whose record starts
on or before 2018-12-31. This is a superset (~500 sites) of the 393 cameras in v2.0, which additionally excluded
auto-white-balance cameras and short records; status is therefore 'partial'."""
import sys
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://phenocam.nau.edu/api/roilists/?format=json&limit=5000"
d = requests.get(URL, timeout=120).json()
rows = d["results"] if isinstance(d, dict) else d
sites = {}
for x in rows:
    if x.get("first_date") and x["first_date"] <= "2018-12-31" and x.get("lat") is not None:
        sites[x["site"]] = (float(x["lon"]), float(x["lat"]))

write_footprint("phenocam-v2-0", list(sites.values()), kind="sites", n_total=393, status="partial",
                source={"label": "PhenoCam network ROI list API (phenocam.nau.edu)", "url": URL,
                        "method": f"camera lat/lon of every PhenoCam site with an ROI record starting by 2018-12-31 ({len(sites)} sites), a superset of the 393 v2.0 cameras"},
                note="PhenoCam v2.0 itself (ORNL DAAC doi:10.3334/ORNLDAAC/1674) requires an Earthdata login; the exact 393-camera list is not published openly, so the live network list filtered by date is used.")
