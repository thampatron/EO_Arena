"""STARCOP footprint. The Zenodo record's train.csv/test.csv list every 512x512 tile as
<AVIRIS-NG flight line>_r<row>_c<col>_w512_h512 but carry no coordinates. The JPL AVIRIS-NG data portal publishes a
KML of 2019 flight-line footprints (4-corner polygons plus the line's sample/line counts), so each tile is placed by
interpolating its row/col window inside its flight line's polygon (assuming the first polygon edge is line 0; if the
line was flown the other way the point is mirrored along the same ~10-150 km strip)."""
import sys, re, shutil
from pathlib import Path
import pandas as pd, requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

DS = "starcop"
TMP = Path("/tmp/claude-0/fp") / DS
ZEN = "https://zenodo.org/records/7863343/files/"
KML = "https://avirisng.jpl.nasa.gov/arcgis/AVIRIS-NG_2019.kml"


def fetch(url, name):
    TMP.mkdir(parents=True, exist_ok=True)
    p = TMP / name
    if not p.exists():
        for _ in range(4):  # Zenodo intermittently returns empty bodies
            r = requests.get(url, timeout=120)
            if r.ok and r.content:
                p.write_bytes(r.content); break
        else:
            raise RuntimeError(f"could not fetch {url}")
    return p


def flight_lines():
    k = fetch(KML, "AVIRIS-NG_2019.kml").read_text(errors="ignore")
    out = {}
    for pm in re.findall(r"<Placemark>(.*?)</Placemark>", k, re.S):
        name = re.search(r"<name>(\S+)</name>", pm)[1]
        raw = re.search(r"<coordinates>(.*?)</coordinates>", pm, re.S)[1].split()
        try:
            coords = [tuple(map(float, c.split(",")[:2])) for c in raw]
        except ValueError:
            continue
        s = re.search(r"# Samples:</b> (\d+).*?# Lines:</b> (\d+)", pm)
        if len(coords) >= 4 and s:
            out[name] = (coords[:4], int(s[1]), int(s[2]))
    return out


def main():
    df = pd.concat([pd.read_csv(fetch(ZEN + f + "?download=1", f)) for f in ("train.csv", "test.csv")])
    fl = flight_lines()
    pts, missing = [], 0
    for tid, name in zip(df["id"], df["name"]):
        m = re.search(r"_r(\d+)_c(\d+)_w(\d+)_h(\d+)$", tid)
        if name not in fl or not m:
            missing += 1; continue
        (p0, p1, p2, p3), ns, nl = fl[name]
        r, c, w, h = map(int, m.groups())
        fr, fc = min((r + h / 2) / nl, 1.0), min((c + w / 2) / ns, 1.0)
        # edge p0->p1 is line 0 across-track; edge p3->p2 is the last line
        lon = (p0[0] + (p1[0] - p0[0]) * fc) * (1 - fr) + (p3[0] + (p2[0] - p3[0]) * fc) * fr
        lat = (p0[1] + (p1[1] - p0[1]) * fc) * (1 - fr) + (p3[1] + (p2[1] - p3[1]) * fc) * fr
        pts.append((lon, lat))
    write_footprint(DS, pts, source={"label": "STARCOP train/test CSVs + JPL AVIRIS-NG 2019 flight-line KML",
                                     "url": "https://zenodo.org/records/7863343/files/train.csv",
                                     "method": "tile row/col windows from the CSV ids interpolated inside the AVIRIS-NG flight-line polygons of the JPL 2019 KML"},
                    kind="samples", n_total=len(df),
                    note=f"{len(df)} tiles (train+test) on {df['name'].nunique()} Permian Basin flight lines; position along a flight line assumes the KML polygon's first edge is line 0 (error bounded by the strip length). {missing} tiles unmatched.")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
