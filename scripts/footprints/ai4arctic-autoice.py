"""AI4Arctic / AutoICE footprint.

The only small public index is metadata.csv in the TorchGeo Hugging Face rehost (torchgeo/ai4artic-sea-ice-challenge):
one row per scene with the ice-chart region id (CIS or DMI) but no coordinates. The scenes themselves are 25-300 MB
NetCDFs inside 60 GB tarballs (and DTU's S3 host is unreachable from here), so the per-scene geolocation is not
read. Each of the 16 ice-chart regions is placed at an approximate centre; status is partial.
"""
import csv, io, sys, time
from collections import Counter
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "ai4arctic-autoice"
META = "https://huggingface.co/datasets/torchgeo/ai4artic-sea-ice-challenge/resolve/main/metadata.csv"

# Approximate centres (lon, lat) of the CIS and DMI regional ice-chart areas used in the dataset.
REGIONS = {
    "SGRDIEA": (-70.0, 72.0),      # CIS Eastern Arctic (Baffin Bay, Lancaster Sound)
    "SGRDIWA": (-125.0, 72.0),     # CIS Western Arctic (Beaufort Sea, Amundsen Gulf)
    "SGRDIHA": (-85.0, 59.0),      # CIS Hudson Bay
    "SGRDIMID": (-95.0, 75.0),     # CIS central Arctic archipelago
    "SGRDIFOXE": (-78.0, 66.0),    # CIS Foxe Basin
    "SGRDINFLD": (-55.0, 52.0),    # CIS Newfoundland and Labrador
    "CapeFarewell_RIC": (-44.0, 59.5),
    "CentralEast_RIC": (-25.0, 70.0),
    "CentralWest_RIC": (-55.0, 68.0),
    "NorthAndCentralEast_RIC": (-20.0, 74.0),
    "NorthEast_RIC": (-17.0, 78.0),
    "NorthWest_RIC": (-70.0, 76.0),
    "North_RIC": (-40.0, 82.0),
    "Qaanaaq_RIC": (-70.0, 77.5),
    "SouthEast_RIC": (-38.0, 63.0),
    "SouthWest_RIC": (-50.0, 63.0),
}


def main():
    for i in range(6):
        r = requests.get(META, timeout=120, allow_redirects=True)
        if r.status_code == 200:
            break
        time.sleep(5 * (i + 1))
    r.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r.text)))
    counts = Counter(row["region_id"] for row in rows)
    missing = sorted(set(counts) - set(REGIONS))
    pts = [REGIONS[k] for k in counts if k in REGIONS]
    write_footprint(DS, pts, kind="sites", n_total=len(rows), status="partial",
                    source={"label": "TorchGeo AI4Arctic rehost metadata.csv (region ids) + approximate region centres",
                            "url": "https://huggingface.co/datasets/torchgeo/ai4artic-sea-ice-challenge/blob/main/metadata.csv",
                            "method": "one approximate centre per CIS/DMI ice-chart region named in metadata.csv; per-scene coordinates sit inside 60 GB NetCDF tarballs and were not read"},
                    note=f"{len(rows)} scenes (513 train, 20 test) over {len(counts)} regions; scenes per region: "
                         + ", ".join(f"{k} {v}" for k, v in counts.most_common())
                         + (f". Unmapped regions: {missing}" if missing else "") + ". Region centres are hand-placed, not from the data.")


if __name__ == "__main__":
    main()
