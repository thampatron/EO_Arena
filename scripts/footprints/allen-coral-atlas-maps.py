"""Allen Coral Atlas geomorphic/benthic maps footprint.

The Atlas is a wall-to-wall map product over the world's shallow tropical reefs (about 30N-30S). Region
geometries and the map downloads sit behind a login on allencoralatlas.org (the /api/v2 region endpoints answer
404 without a session) and there is no public index of mapped sites or validation points, so no sample points
are read. The tropical band stated in the methods page is written as a bbox (status partial).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint  # noqa: E402

DS = "allen-coral-atlas-maps"
W, S, E, N = -180.0, -30.0, 180.0, 30.0


def main():
    write_footprint(DS, [(W, S), (E, S), (E, N), (W, N)], kind="bbox", n_total=None, status="partial",
                    source={"label": "Allen Coral Atlas methods page", "url": "https://allencoralatlas.org/methods/",
                            "method": "bounding box of the tropical reef band (30N-30S) the Atlas maps; region polygons and map tiles require an Atlas login"},
                    note="Wall-to-wall PlanetScope-derived geomorphic and benthic maps of shallow reefs worldwide; no public per-region or validation-point index without an account, so only the latitude band is drawn.")


if __name__ == "__main__":
    main()
