"""CropNet (Lin et al. 2024) footprint.

CropNet's samples are US counties (the imagery is packed into per-state HDF5 files with no public index). The
county set is taken from the USDA crop yield CSVs in the Hugging Face repo (state_ansi + county_ansi for every
county-year with a yield label, 4 crops x 7 years, ~135 KB each) and each county is placed at its centroid
from the US Census 2023 county gazetteer (140 KB zip). One point per distinct county.
"""
import csv, io, sys, time, zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "cropnet"
REPO = "https://huggingface.co/datasets/CropNet/CropNet/resolve/main/"
CROPS = {"Corn": "Corn", "Cotton": "Cotton", "Soybeans": "Soybeans", "WinterWheat": "WinterWheat"}
YEARS = range(2016, 2023)
GAZ = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_counties_national.zip"


def get(url):
    for i in range(6):
        r = requests.get(url, timeout=120, allow_redirects=True)
        if r.status_code == 404:
            return r
        if r.status_code not in (429, 503):
            r.raise_for_status()
            return r
        time.sleep(5 * (i + 1))
    r.raise_for_status()


def main():
    fips = set()
    for crop in CROPS:
        for y in YEARS:
            url = f"{REPO}USDA%20Crop%20Dataset/{crop}/{y}/USDA_{CROPS[crop]}_County_{y}.csv"
            r = get(url)
            if r.status_code == 404:
                continue
            for row in csv.DictReader(io.StringIO(r.text)):
                s, c = row.get("state_ansi", "").strip(), row.get("county_ansi", "").strip()
                if s.isdigit() and c.isdigit():
                    fips.add(s.zfill(2) + c.zfill(3))
    z = zipfile.ZipFile(io.BytesIO(get(GAZ).content))
    txt = z.read(z.namelist()[0]).decode("latin-1")
    cent = {}
    for row in csv.DictReader(io.StringIO(txt), delimiter="\t"):
        row = {k.strip(): v.strip() for k, v in row.items()}
        cent[row["GEOID"]] = (float(row["INTPTLONG"]), float(row["INTPTLAT"]))
    pts = [cent[f] for f in fips if f in cent]
    write_footprint(DS, pts, kind="samples", n_total=len(fips),
                    source={"label": "CropNet USDA Crop Dataset CSVs (Hugging Face) + Census county gazetteer",
                            "url": "https://huggingface.co/datasets/CropNet/CropNet/tree/main/USDA%20Crop%20Dataset",
                            "method": "distinct state+county FIPS from the county-level yield CSVs (4 crops, 2016-2022), placed at Census gazetteer county centroids"},
                    note=f"{len(fips)} counties with at least one yield label; {len(fips) - len(pts)} FIPS not matched in the 2023 gazetteer. Imagery HDF5s are per state and carry no public per-county index.")


if __name__ == "__main__":
    main()
