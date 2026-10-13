"""SICKLE (Cauvery Delta, Tamil Nadu, India): the dataset is distributed through a Google Form (Drive) and the paper
states that the GPS coordinates of the 388 plots are withheld for privacy. No public index of plot locations
exists, so only the study region is recorded: the four Cauvery Delta districts the paper refers to (via the ICAR
2013 reclassification it cites: Thanjavur, Tiruvarur, Nagapattinam, Cuddalore), as district-headquarter points."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

SITES = {"Thanjavur": (79.14, 10.79), "Tiruvarur": (79.64, 10.77), "Nagapattinam": (79.84, 10.77), "Cuddalore": (79.77, 11.75)}
write_footprint("sickle", list(SITES.values()), kind="sites", n_total=388, status="partial",
                source={"label": "SICKLE paper (arXiv 2312.00069) study-region description", "url": "https://arxiv.org/abs/2312.00069",
                        "method": "approximate district centres of the four Cauvery Delta districts named via the ICAR 2013 reclassification the paper cites; plot coordinates are withheld by the authors"},
                note="388 plots / 2,370 season samples, Jan 2018-Mar 2021. Data access requires a Google Form (Drive download); the paper states plot GPS centroids are withheld for privacy, so no sample-level footprint is possible. District identity is inferred, not stated verbatim in the paper.")
