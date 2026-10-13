"""NeonTreeEvaluation footprint. The annotation XML names (annotations.zip, 0.5 MB, Zenodo 5914554) encode the
location of every image: evaluation plots are NEON TOS plots (SITE_NNN_YEAR -> NEON API location
<SITE_NNN>.basePlot.all, which carries lat/lon) and training tiles are NEON 1 km AOP tiles
(YEAR_SITE_V_EASTING_NORTHING -> tile centre in the site's UTM zone)."""
import sys, re, zipfile, shutil, time
from pathlib import Path
import requests
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

DS = "neontreeevaluation"
TMP = Path("/tmp/claude-0/fp") / DS
ZIP = "https://zenodo.org/records/5914554/files/annotations.zip?download=1"
NEON = "https://data.neonscience.org/api/v0/"


def get_json(url):
    for k in range(4):
        try:
            r = requests.get(url, timeout=60)
            if r.ok:
                return r.json()
            if r.status_code == 400:
                return None
        except requests.RequestException:
            pass
        time.sleep(2 * (k + 1))
    return None


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    zp = TMP / "annotations.zip"
    if not zp.exists():
        for k in range(4):
            r = requests.get(ZIP, timeout=120)
            if r.ok and len(r.content) > 1000:
                zp.write_bytes(r.content); break
            time.sleep(3)
    names = [n.rsplit("/", 1)[-1][:-4] for n in zipfile.ZipFile(zp).namelist()
             if n.endswith(".xml") and not n.startswith("__MACOSX")]

    sites, plots, pts, unresolved = {}, {}, [], []
    for n in names:
        m_tile = re.match(r"^(\d{4})_([A-Z]{4})_\d_(\d{6})_(\d{7})", n)
        m_plot = re.match(r"^([A-Z]{4})_(\d{3})_\d{4}$", n)
        site = (m_tile[2] if m_tile else (m_plot[1] if m_plot else n.split("_")[0]))
        if site not in sites:
            s = get_json(NEON + f"sites/{site}")
            sites[site] = (s["data"]["siteLongitude"], s["data"]["siteLatitude"]) if s else None
        if m_tile and sites[site]:
            lon0, lat0 = sites[site]
            zone = int((lon0 + 180) // 6) + 1
            to_ll = Transformer.from_crs(f"EPSG:{32600 + zone}", "EPSG:4326", always_xy=True)
            pts.append(to_ll.transform(int(m_tile[3]) + 500, int(m_tile[4]) + 500))
        elif m_plot:
            key = f"{m_plot[1]}_{m_plot[2]}"
            if key not in plots:
                j = get_json(NEON + f"locations/{key}.basePlot.all")
                d = j["data"] if j else None
                plots[key] = (d["locationDecimalLongitude"], d["locationDecimalLatitude"]) if d else sites.get(site)
            if plots[key]:
                pts.append(plots[key])
            else:
                unresolved.append(n)
        elif sites.get(site):
            pts.append(sites[site])  # e.g. OSBS_1: site centre only
        else:
            unresolved.append(n)
    write_footprint(DS, pts, source={"label": "NeonTreeEvaluation annotations.zip (Zenodo 5914554) + NEON API plot/site locations",
                                     "url": "https://zenodo.org/records/5914554",
                                     "method": "evaluation plots geolocated via NEON API <plot>.basePlot.all; training tiles decoded from the UTM easting/northing in their names"},
                    kind="samples", n_total=len(names),
                    note=f"One point per annotated image ({len(names)} XMLs across 22 NEON sites; 30,975 crowns). {len(unresolved)} names unresolved.")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
