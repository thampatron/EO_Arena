"""EMIT L2B CH4 plume complexes (EMITL2BCH4PLM) footprint.

Granule metadata is public in NASA CMR (no login needed): each plume complex is one granule whose record carries
its bounding polygon in lat lon order. The JSON search is paged with CMR-Search-After; only metadata is fetched.
One point per plume complex (polygon vertex mean). V001 has been retired from CMR, so V002 is used.
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "emit-l2b-ch-plumes"
URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
PARAMS = {"short_name": "EMITL2BCH4PLM", "page_size": 2000}


def main():
    pts, hits, headers = [], None, {}
    while True:
        r = requests.get(URL, params=PARAMS, headers=headers, timeout=120)
        r.raise_for_status()
        hits = int(r.headers.get("CMR-Hits", 0))
        entries = r.json()["feed"]["entry"]
        if not entries:
            break
        for e in entries:
            ring = None
            if e.get("polygons"):
                ring = [float(v) for v in e["polygons"][0][0].split()]
            elif e.get("boxes"):
                ring = [float(v) for v in e["boxes"][0].split()]
            if not ring:
                continue
            lats, lons = ring[0::2], ring[1::2]
            pts.append((sum(lons) / len(lons), sum(lats) / len(lats)))
        sa = r.headers.get("CMR-Search-After")
        if not sa:
            break
        headers = {"CMR-Search-After": sa}
    write_footprint(DS, pts, kind="samples", n_total=hits,
                    source={"label": "NASA CMR granule search, EMITL2BCH4PLM V002", "url": f"{URL}?short_name=EMITL2BCH4PLM&page_size=2000",
                            "method": "mean of the bounding-polygon vertices of every plume-complex granule returned by the CMR granule search"},
                    note=f"{hits} plume-complex granules in CMR at build time; the collection grows as EMIT acquires and the team reviews new plumes.")


if __name__ == "__main__":
    main()
