"""NASA Marine Debris (Radiant MLHub archive, Azure container radiantearth/mlhub used by TorchGeo): chip names
such as 20160928_153233_0e16_16816-29821-16 are <PlanetScope scene id>_<x>-<y>-<zoom> web-mercator tile indices
(zoom 16). The blob listing of nasa-marine-debris/labels/ is paged through (names only, no downloads) and the
tile centre is decoded for every chip; a check against one label GeoJSON (CRS84 boxes) confirmed the decoding."""
import sys, re, math
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

BASE = "https://radiantearth.blob.core.windows.net/mlhub"
names, marker = set(), None
while True:
    url = f"{BASE}?restype=container&comp=list&prefix=nasa-marine-debris/labels/&maxresults=5000" + (f"&marker={marker}" if marker else "")
    t = requests.get(url, timeout=60).text
    for n in re.findall(r"<Name>nasa-marine-debris/labels/(.*?)\.geojson</Name>", t):
        names.add(n)
    m = re.search(r"<NextMarker>(.+?)</NextMarker>", t)
    if not m:
        break
    marker = m.group(1)

def centre(x, y, z):
    n = 2 ** z
    lon = (x + 0.5) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / n))))
    return lon, lat

pts = []
for n in sorted(names):
    m = re.search(r"_(\d+)-(\d+)-(\d+)$", n)
    pts.append(centre(int(m.group(1)), int(m.group(2)), int(m.group(3))))

write_footprint("nasa-marine-debris", pts, kind="samples", n_total=len(names),
                source={"label": "Radiant MLHub nasa-marine-debris blob listing (labels/*.geojson names)", "url": f"{BASE}/nasa-marine-debris/README.md",
                        "method": "centre of the zoom-16 web-mercator tile encoded in each chip name (x-y-z suffix), one point per 256x256 PlanetScope chip"},
                note="Mostly the Bay Islands, Honduras, with a few chips off Ghana and Greece (per the dataset README).")
