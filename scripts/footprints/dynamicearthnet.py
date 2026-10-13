"""DynamicEarthNet: centre of each AOI cube. AOI ids such as 1311_3077_13 are XYZ web-mercator tile indices at
zoom 13 (x_y_z); the TACO repackaging on Hugging Face (isp-uv-es/dynamicearthnet-taco, .tacocat/sample.parquet,
54 KB) also lists ml:lon / ml:lat per sample, which are used here and cross-checked against the decoded tile centres.
The original split files on vision.in.tum.de are offline and the TUM mediaTUM archive is multi-GB."""
import sys, math, shutil, time
from pathlib import Path
import requests, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

URL = "https://huggingface.co/datasets/isp-uv-es/dynamicearthnet-taco/resolve/main/.tacocat/sample.parquet"
TMP = Path("/tmp/claude-0/fp/dynamicearthnet"); TMP.mkdir(parents=True, exist_ok=True)
f = TMP / "sample.parquet"
if not f.exists():
    for _ in range(5):
        r = requests.get(URL, timeout=120, headers={"User-Agent": "curl/8"})
        if r.status_code == 200:
            f.write_bytes(r.content); break
        time.sleep(5)
    r.raise_for_status()

def xyz_centre(aoi):
    x, y, z = (int(v) for v in aoi.split("_"))
    n = 2 ** z
    lon = (x + 0.5) / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 0.5) / n))))
    return lon, lat

d = pd.read_parquet(f)
aoi = d.groupby("ml:aoi")[["ml:lon", "ml:lat"]].first()
pts = []
for a, row in aoi.iterrows():
    lon, lat = float(row["ml:lon"]), float(row["ml:lat"])
    dx, dy = xyz_centre(a)
    assert abs(dx - lon) < 0.1 and abs(dy - lat) < 0.1, (a, lon, lat, dx, dy)
    pts.append((lon, lat))

write_footprint("dynamicearthnet", pts, kind="tiles", n_total=75, status="partial" if len(pts) < 75 else "ok",
                source={"label": "DynamicEarthNet TACO repackaging, .tacocat/sample.parquet (ml:lon, ml:lat per AOI)", "url": URL,
                        "method": "one point per AOI cube from the per-sample lon/lat in the TACO metadata, cross-checked against the XYZ zoom-13 tile index encoded in each AOI id"},
                note=f"{len(pts)} of the 75 AOIs are present in the TACO repackaging (1,752 monthly samples; two cubes missing). Each AOI is a 1024x1024 px cube at 3 m (~3 km).")
shutil.rmtree(TMP, ignore_errors=True)
