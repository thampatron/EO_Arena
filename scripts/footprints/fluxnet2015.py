"""FLUXNET2015: the 212 eddy-covariance tower sites, lat/lon from the AmeriFlux/FLUXNET site API that feeds the
site list on fluxnet.org/sites/site-list-and-pages (GRP_LOCATION per site). Every site-year of the dataset belongs
to one of these towers, so the towers are the complete spatial footprint."""
import sys
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://amfcdn.lbl.gov/api/v1/site_display/FLUXNET/FLUXNET2015"
sites = requests.get(URL, timeout=60).json()
pts, ccby = [], 0
for s in sites:
    loc = s.get("GRP_LOCATION") or {}
    if loc.get("LOCATION_LAT") and loc.get("LOCATION_LONG"):
        pts.append((float(loc["LOCATION_LONG"]), float(loc["LOCATION_LAT"])))
    ccby += bool(s.get("CCBY4_0"))

write_footprint("fluxnet2015", pts, kind="sites", n_total=len(sites),
                source={"label": "FLUXNET2015 site list (AmeriFlux site_display API used by fluxnet.org)", "url": URL,
                        "method": "tower lat/lon of all 212 FLUXNET2015 sites from the site-list API"},
                note=f"{ccby} of {len(sites)} sites carry CC-BY-4.0 site-years; the rest are Tier 2 only. One point per tower, not per site-year.")
