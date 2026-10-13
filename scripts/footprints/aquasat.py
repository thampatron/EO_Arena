"""AquaSat: matchup site coordinates (lat/long columns) read from byte-range slices of the official 291 MB
sr_wq_rs_join.csv on figshare. The file is ordered by Landsat path/row, so 80 evenly spaced 0.75 MB slices
(~60 MB total) sample the whole CONUS extent; only complete CSV lines inside each slice are parsed."""
import sys, csv, io
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

ARTICLE = "https://figshare.com/articles/dataset/AquaSat/8139383"
URL = "https://ndownloader.figshare.com/files/18733733"
N_SLICES, SLICE = 80, 750_000

s = requests.Session()
r0 = s.get(URL, headers={"Range": "bytes=0-4095"}, timeout=60)
size = int(r0.headers["Content-Range"].split("/")[-1])
header = r0.content.decode("utf-8", "replace").split("\n")[0].split(",")
ilat, ilon = header.index("lat"), header.index("long")
pts, rows, bytes_seen = set(), 0, 0
for k in range(N_SLICES):
    start = int(k * (size - SLICE) / (N_SLICES - 1))
    r = s.get(URL, headers={"Range": f"bytes={start}-{start + SLICE - 1}"}, timeout=120); r.raise_for_status()
    txt = r.content.decode("utf-8", "replace")
    lines = txt.split("\n")[1:-1]  # drop the partial first and last lines
    for rec in csv.reader(io.StringIO("\n".join(lines))):
        if len(rec) <= max(ilat, ilon): continue
        try: pts.add((float(rec[ilon]), float(rec[ilat])))
        except ValueError: continue
        rows += 1
    bytes_seen += len("\n".join(lines)) + 1
n_total = int(round(size / (bytes_seen / rows)))  # row count estimated from mean bytes per row
write_footprint("aquasat", sorted(pts), kind="sites", n_total=n_total,
                source={"label": "AquaSat sr_wq_rs_join.csv (figshare)", "url": ARTICLE,
                        "method": f"distinct lat/long of matchup sites parsed from {N_SLICES} byte-range slices of the CSV ({rows:,} matchup rows sampled)"},
                note=f"n_total is the matchup-row count estimated from file size / mean row length (paper: >600,000 matchups); {len(pts):,} distinct sites seen in the sampled slices, 3,000 drawn. CONUS lakes/rivers/estuaries (WQP, LAGOS).")
