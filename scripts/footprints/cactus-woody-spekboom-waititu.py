"""FoMo-Bench aerial datasets Cactus (Mexico), Woody (Chile), Spekboom (South Africa), Waititu (New Zealand).
Woody, Spekboom and Waititu are UAV orthomosaics on Zenodo (records 7565500/7565490/7565546, 7564954, 7648984;
1-16 GB zips, as listed in FoMo-Bench's downloading_scripts/*.sh). Each labelled orthomosaic ships with a small
<name>_AOI shapefile; these are read out of the zips with HTTP range requests (central directory + the few-KB
shapefile members only) and their centroids used as site points. Cactus is a Kaggle-only dataset of 32x32 px
aerial crops from the Tehuacan-Cuicatlan valley (Lopez-Jimenez et al. 2019) with no coordinates; its study area
is added as one approximate point."""
import sys, time, zipfile, shutil, re
from pathlib import Path
import requests, geopandas as gpd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

ZIPS = {
    "woody/pinus": "https://zenodo.org/record/7565500/files/data_pinus_radiata.zip?download=1",
    "woody/ulex": "https://zenodo.org/record/7565490/files/data_ulex_europaeus.zip?download=1",
    "woody/acacia": "https://zenodo.org/record/7565546/files/data_acacia_dealbata.zip?download=1",
    "spekboom": "https://zenodo.org/record/7564954/files/data_spekboom.zip?download=1",
    "waititu": "https://zenodo.org/record/7648984/files/data_treespecies_waitutu_nz.zip?download=1",
}
CACTUS = (-97.47, 18.33)  # Tehuacan-Cuicatlan Biosphere Reserve (Zapotitlan Salinas), approximate
S = requests.Session(); S.headers["User-Agent"] = "curl/8"

def get(url, **kw):
    for i in range(6):
        r = S.get(url, timeout=180, **kw)
        if r.status_code not in (429, 500, 502, 503):
            r.raise_for_status(); return r
        time.sleep(5 * (i + 1))
    r.raise_for_status()

class RangeFile:
    def __init__(self, url):
        r = get(url, headers={"Range": "bytes=0-0"}, allow_redirects=True)
        self.url, self.pos = r.url, 0
        self.size = int(r.headers["Content-Range"].split("/")[-1])
    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]; return self.pos
    def tell(self): return self.pos
    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        if n == 0: return b""
        b = get(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"}).content
        self.pos += len(b); return b
    def seekable(self): return True
    def readable(self): return True

TMP = Path("/tmp/claude-0/fp/cactus-woody-spekboom-waititu"); TMP.mkdir(parents=True, exist_ok=True)
pts, counts = [CACTUS], {"cactus": 1}
for key, url in ZIPS.items():
    z = zipfile.ZipFile(RangeFile(url))
    shps = [i.filename for i in z.infolist() if re.search(r"_AOI\.shp$", i.filename, re.I)]
    n = 0
    for shp in shps:
        stem = shp[:-4]
        d = TMP / key.replace("/", "_") / Path(stem).name; d.mkdir(parents=True, exist_ok=True)
        for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
            try:
                (d / (Path(stem).name + ext)).write_bytes(z.read(stem + ext))
            except KeyError:
                pass
        try:
            g = gpd.read_file(d / (Path(stem).name + ".shp"))
            if g.crs is None:
                print("no CRS, skipped", shp); continue
            c = g.geometry.union_all().centroid
            lon, lat = gpd.GeoSeries([c], crs=g.crs).to_crs(4326).iloc[0].coords[0]
            pts.append((lon, lat)); n += 1
        except Exception as e:
            print("skip", shp, e)
    counts[key] = n

write_footprint("cactus-woody-spekboom-waititu", pts, kind="sites", n_total=len(pts), status="partial",
                source={"label": "AOI shapefiles inside the Zenodo UAV archives listed by FoMo-Bench (Woody: Pinus/Ulex/Acacia, Spekboom, Waititu) + Cactus study area", "url": "https://github.com/RolnickLab/FoMo-Bench",
                        "method": "centroid of each labelled orthomosaic's AOI polygon, read from the zips via HTTP range requests; Cactus (Kaggle, no georeference) as one approximate study-area point"},
                note=f"Sites per dataset: {counts}. Each AOI is a UAV plot of ~0.01-1 km2; the Cactus point is the Tehuacan-Cuicatlan reserve centre, not a measured location.")
shutil.rmtree(TMP, ignore_errors=True)
