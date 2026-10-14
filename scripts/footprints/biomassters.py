"""Footprint for BioMassters (Nascetti et al. 2023), Hugging Face nascetti-a/BioMassters.

The two metadata CSVs (features / train_agbm) list chip ids, S3 paths and months but no coordinates, and the
AGBM/feature GeoTIFFs are deliberately stripped of georeferencing (checked: train_agbm/0003d2eb_agbm.tif read
from train_agbm.zip via HTTP range requests has no CRS or geotransform). The chips are anonymised 2.56 km
cells over Finland's forests, so only the national bounding box can be stated.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "biomassters"
FINLAND = [(19.5, 59.8), (31.6, 59.8), (31.6, 70.1), (19.5, 70.1)]


def main():
    write_footprint(DS, FINLAND, kind="bbox", n_total=13000, status="partial",
                    source={"label": "BioMassters on Hugging Face", "url": "https://huggingface.co/datasets/nascetti-a/BioMassters",
                            "method": "Finland bounding box only; the chip GeoTIFFs carry no CRS/geotransform and the metadata CSVs hold no coordinates"},
                    note="~13,000 anonymised 2,560 m chips (8,689 train AGBM labels + test) over Finnish forest; chip locations are "
                         "withheld by design (Finnish Forest Centre LiDAR AGB reference), so no sample-level points exist.")


if __name__ == "__main__":
    main()
