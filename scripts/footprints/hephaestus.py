"""Hephaestus: one point per LiCSAR frame. The frame ids of the 19,919 annotated interferograms come from the
official annotation files (annotations_hephaestus.zip, 11.7 MB, Dropbox link in the GitHub README); the frame
outlines come from the COMET LiCSAR product archive (<frame>-poly.txt per frame) and are reduced to their centre."""
import sys, io, json, zipfile, collections
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

REPO = "https://github.com/Orion-AI-Lab/Hephaestus"
ANN = "https://www.dropbox.com/s/i08mz5514gczksz/annotations_hephaestus.zip?dl=1"
LICS = "https://gws-access.jasmin.ac.uk/public/nceo_geohazards/LiCSAR_products/{track}/{frame}{suffix}/metadata/{frame}-poly.txt"
# four frames were retired after Hephaestus was built; their archive directories carry a suffix
SUFFIX = {"022D_04826_121209": ".backup", "106A_09090_000404": ".toremove", "124D_05291_081406": ".backup", "155D_02579_100800": ".todel"}

r = requests.get(ANN, timeout=300); r.raise_for_status()
zf = zipfile.ZipFile(io.BytesIO(r.content))
frames = collections.Counter()
for n in zf.namelist():
    if n.endswith(".json"):
        frames[json.loads(zf.read(n))["frameID"]] += 1
pts, missing = [], []
for frame in sorted(frames):
    url = LICS.format(track=int(frame[:3]), frame=frame, suffix=SUFFIX.get(frame, ""))
    try:
        rr = requests.get(url, timeout=60); rr.raise_for_status()
        poly = [tuple(map(float, ln.split())) for ln in rr.text.strip().splitlines() if ln.strip()]
        pts.append((sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)))
    except Exception as e:  # noqa: BLE001
        missing.append(frame); print("skip", frame, e)
write_footprint("hephaestus", pts, kind="tiles", n_total=sum(frames.values()),
                source={"label": "Hephaestus annotations + COMET LiCSAR frame polygons", "url": REPO,
                        "method": "centre of the LiCSAR frame polygon (<frame>-poly.txt) for each of the 38 frames named in the 19,919 annotation JSON files"},
                note=f"{len(frames)} Sentinel-1 LiCSAR frames (~250 km) over volcanoes; interferograms per frame range {min(frames.values())}-{max(frames.values())}."
                     + (f" Frames without a polygon: {', '.join(missing)}." if missing else ""))
