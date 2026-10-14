"""ZueriCrop: patch centres reconstructed from the study-area label raster. The official release is a single 41 GB
HDF5 of 24x24 px patches with no coordinates, but the crop-classification/zueri-crop-2 mirror on Hugging Face holds
the full 51.2 x 51.2 km label map as a 1.9 MB COG (EPSG:32632, 10 m). Tiling it into 24 px windows and keeping those
with at least one labelled pixel reproduces the patch grid (28,193 windows vs 27,977 patches in the paper)."""
import sys
from pathlib import Path
import numpy as np, rasterio
from rasterio.warp import transform
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

REPO = "https://huggingface.co/datasets/crop-classification/zueri-crop-2"
URL = REPO + "/resolve/main/labels_cog.tif"
P = 24

with rasterio.Env(CPL_LOG="/dev/null"), rasterio.open(f"/vsicurl/{URL}") as src:
    a = src.read(1); tr = src.transform; crs = src.crs
n = a.shape[0] // P
lab = (a[:n * P, :n * P].reshape(n, P, n, P) > 0).any(axis=(1, 3))
rows, cols = np.nonzero(lab)
xs, ys = tr * ((cols + 0.5) * P, (rows + 0.5) * P)
lon, lat = transform(crs, "EPSG:4326", list(xs), list(ys))
write_footprint("zuericrop", list(zip(lon, lat)), kind="samples", n_total=27977,
                source={"label": "ZueriCrop label map COG (crop-classification/zueri-crop-2 mirror)", "url": REPO,
                        "method": "centre of every 24x24 px (240 m) window of the 5120x5120 label raster that contains a labelled pixel, EPSG:32632 -> WGS84"},
                note=f"{len(rows):,} labelled windows reconstructed (paper: 27,977 patches over Zurich/Thurgau, 48 classes); the HDF5 release itself has no georeference. 3,000 stored.")
