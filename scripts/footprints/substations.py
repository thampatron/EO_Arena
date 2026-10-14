"""Footprint for the Substation dataset (Mukherjee et al. 2024; TorchGeo `Substation`), GCS tz-ml-public.

metadata.tar.gz (2.9 MB) in the dataset's bucket folder holds one JSON per sample, named
lat_<lat>_lon_<lon>.json and carrying the patch centre lat/lon. Only the file names are used.
"""
import re, sys, tarfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "substations"
BASE = "https://storage.googleapis.com/tz-ml-public/substation-over-10km2-csv-main-444e360fd2b6444b9018d509d0e4f36e/"
TMP = Path("/tmp/claude-0/fp") / DS


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    f = TMP / "metadata.tar.gz"
    f.write_bytes(requests.get(BASE + "metadata.tar.gz", timeout=300).content)
    info = requests.get(BASE + "dataset_info.json", timeout=60).json()
    pts = []
    with tarfile.open(f) as t:
        for m in t.getmembers():
            g = re.search(r"lat_(-?\d+\.\d+)_lon_(-?\d+\.\d+)\.json$", m.name)
            if g:
                pts.append((float(g.group(2)), float(g.group(1))))
    write_footprint(DS, pts, kind="samples", n_total=len(pts),
                    source={"label": "Substation dataset metadata.tar.gz (GCS tz-ml-public)", "url": BASE + "metadata.tar.gz",
                            "method": "lat/lon parsed from each per-sample metadata JSON file name (patch centre)"},
                    note=f"{len(pts)} Sentinel-2 patches (228 px, {info.get('images_start')} to {info.get('images_end')}) centred on "
                         "OSM substations worldwide (bucket folder 'substation-over-10km2'); positives only (the random-negative set is a separate bucket folder).")
    f.unlink(missing_ok=True)
    TMP.rmdir()


if __name__ == "__main__":
    main()
