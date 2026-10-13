"""Footprint for 38-Cloud (Mohajerani & Saeedi 2019), Landsat 8 cloud segmentation.

The full scene-ID lists (training_sceneids_38-Cloud.csv, test_sceneids_38-Cloud.csv) ship only inside the
Kaggle / Google Drive archive, which this environment cannot fetch. The GitHub repo does carry the
20 test scene IDs (in evaluation/.../numerical_results_...xlsx) and one training scene ID (sample patch
names). Each Landsat product ID gives WRS-2 path/row + date; the scene centre is taken from the matching
item's bbox in the Planetary Computer landsat-c2-l2 STAC collection.
"""
import io, re, sys, zipfile
from pathlib import Path

import requests
from pystac_client import Client

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "38-cloud"
RAW = "https://raw.githubusercontent.com/SorourMo/38-Cloud-A-Cloud-Segmentation-Dataset/master/"
XLSX = RAW + ("evaluation/Numerical%20results%20over%2038-Cloud%20test%20set/numerical_results_entire_masks_"
              "Cloud-Net_trained_on_38-Cloud_training_patches_train_192_test_384.xlsx")
SAMPLE_TRAIN = ["LC08_L1TP_002053_20160520_20170324_01_T1"]  # scene of the sample patches in the repo


def scene_centre(client, pid):
    path, row, date = pid[10:13], pid[13:16], pid[17:25]
    d = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    items = list(client.search(collections=["landsat-c2-l2"], datetime=f"{d}/{d}",
                               query={"landsat:wrs_path": {"eq": path}, "landsat:wrs_row": {"eq": row}},
                               max_items=1).items())
    if not items:
        return None
    w, s, e, n = items[0].bbox
    return ((w + e) / 2, (s + n) / 2)


def main():
    z = zipfile.ZipFile(io.BytesIO(requests.get(XLSX, timeout=120).content))
    text = z.read("xl/sharedStrings.xml").decode()
    test = sorted(set(re.findall(r"LC08_L1TP_\d{6}_\d{8}_\d{8}_\d{2}_T\d", text)))
    client = Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
    pts, missing = [], []
    for pid in test + SAMPLE_TRAIN:
        c = scene_centre(client, pid)
        (pts.append(c) if c else missing.append(pid))
    write_footprint(DS, pts, kind="tiles", n_total=38, status="partial",
                    source={"label": "38-Cloud GitHub repo (test scene IDs) + Planetary Computer Landsat STAC",
                            "url": "https://github.com/SorourMo/38-Cloud-A-Cloud-Segmentation-Dataset",
                            "method": "WRS-2 path/row/date parsed from the Landsat product IDs listed in the repo, scene centre from the matching Planetary Computer landsat-c2-l2 STAC item"},
                    note=f"{len(pts)} of 38 scenes located (20 test scenes + 1 training scene named in the repo); the other "
                         "17 training scene IDs are only in training_sceneids_38-Cloud.csv inside the Kaggle/Drive archive. "
                         "All scenes are Landsat 8 over North/South America (2016)."
                         + (f" Unresolved: {missing}" if missing else ""))


if __name__ == "__main__":
    main()
