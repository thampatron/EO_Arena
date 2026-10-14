"""AI4SmallFarms: centre of each Sentinel-2 image tile in the Cambodia/Vietnam part of the dataset (sentinel-2-asia
train/validate/test), from the GeoTIFF headers of the label masks on the DANS Data Station (Dataverse), read via
rasterio /vsicurl (headers only)."""
import sys
from pathlib import Path
import requests, rasterio
from rasterio.warp import transform
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

DOI = "doi:10.17026/dans-xy6-ngg6"
API = "https://phys-techsciences.datastations.nl/api"
PAGE = f"https://phys-techsciences.datastations.nl/dataset.xhtml?persistentId={DOI}"

files = requests.get(f"{API}/datasets/:persistentId/?persistentId={DOI}", timeout=120).json()["data"]["latestVersion"]["files"]
masks = [f for f in files if f.get("directoryLabel", "").startswith("sentinel-2-asia/") and f["directoryLabel"].endswith("/masks")]
pts, n_nl = [], sum(1 for f in files if f.get("directoryLabel", "").startswith("sentinel-2-nl/") and f["directoryLabel"].endswith("/masks"))
for f in masks:
    url = f"/vsicurl/{API}/access/datafile/{f['dataFile']['id']}"
    try:
        with rasterio.open(url) as src:
            b = src.bounds
            xs, ys = transform(src.crs, "EPSG:4326", [(b.left + b.right) / 2], [(b.bottom + b.top) / 2])
            pts.append((xs[0], ys[0]))
    except Exception as e:  # noqa: BLE001
        print("skip", f["dataFile"]["filename"], e)
write_footprint("ai4smallfarms", pts, kind="tiles", n_total=len(masks),
                source={"label": "AI4SmallFarms on DANS Data Station (Dataverse)", "url": PAGE,
                        "method": "centre of each sentinel-2-asia label-mask GeoTIFF (train/validate/test), from headers read over HTTP and reprojected to WGS84"},
                note=f"{len(masks)} S2 tiles in Cambodia and Vietnam (the PANGAEA subset); the deposit also holds {n_nl} Netherlands tiles (sentinel-2-nl) not used by the benchmark and not plotted.")
