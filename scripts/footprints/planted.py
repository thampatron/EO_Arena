"""Footprint for PLANTED (Pazos-Outon et al. 2024), Google planted-forest dataset.

Each example carries lat/lon metadata, but the only distribution is gs://planted-datasets/public, which
refuses anonymous listing and object reads (401/403 checked via the JSON and XML endpoints and gsutil), and
no Hugging Face / Zenodo mirror exists; AnySat loads it from a local copy (labels2.json). Nothing public to
extract, and the paper gives only a map figure (41 countries, 2.26 M examples).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "planted"


def main():
    write_footprint(DS, [], kind="samples", n_total=2264747, status="unavailable",
                    source={"label": "PLANTED paper (arXiv 2406.18554)", "url": "https://arxiv.org/abs/2406.18554",
                            "method": "no public index: the GCS bucket gs://planted-datasets/public requires authenticated access and there is no mirror"},
                    note="2,264,747 examples (AnySat subset 1,346,662 tiles) with per-example lat/lon inside the TFRecords, 64 tree classes "
                         "in 41 countries; the bucket denies anonymous reads, so no coordinates could be retrieved.")


if __name__ == "__main__":
    main()
