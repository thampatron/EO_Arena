"""CaFFe (CAlving Fronts and where to Find thEm, Gourmelon et al. 2022, ESSD) footprint.

The data are one zip on PANGAEA (doi:10.1594/PANGAEA.940950) of 681 SAR images in local image coordinates with no
per-image geolocation index, so no sample points are read. The paper covers seven glaciers; one approximate
terminus coordinate per glacier is written as sites (status partial).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "caffe"
SITES = {  # (lon, lat) of the calving front area
    "Columbia Glacier, Alaska": (-147.05, 61.13),
    "Jakobshavn Isbrae, Greenland": (-49.90, 69.17),
    "Mapple Glacier, Antarctic Peninsula": (-62.20, -65.95),
    "Crane Glacier, Antarctic Peninsula": (-62.30, -65.40),
    "Jorum Glacier, Antarctic Peninsula": (-61.90, -65.70),
    "Dinsmoor-Bombardier-Edgeworth, Antarctic Peninsula": (-60.90, -64.75),
    "Sjogren Inlet, Antarctic Peninsula": (-58.85, -64.23),
}


def main():
    write_footprint(DS, list(SITES.values()), kind="sites", n_total=681, status="partial",
                    source={"label": "ESSD paper (Gourmelon et al. 2022) glacier list; data on PANGAEA", "url": "https://doi.pangaea.de/10.1594/PANGAEA.940950",
                            "method": "one hand-placed terminus coordinate per glacier named in the paper; the PANGAEA zip has no per-image geolocation index"},
                    note="681 SAR images (ERS, Envisat, RADARSAT-1, ALOS, TSX/TDX, S1; 1995-2020) of 7 glaciers: " + "; ".join(SITES) + ". Test set = Mapple and Columbia.")


if __name__ == "__main__":
    main()
