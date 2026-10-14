"""DeepGlobe 2018 Road Extraction: 8,570 1024x1024 px (6,226 labelled) 0.5 m DigitalGlobe JPEG tiles over
Thailand, Indonesia and India. The release (Kaggle / CodaLab, login required) contains no georeferencing and the
challenge paper (Demir et al. 2018) names only the three countries, not sites, so no sample footprint exists."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import write_footprint

write_footprint("deepglobe-roads", [], status="unavailable",
                source={"label": "DeepGlobe 2018 challenge paper (arXiv 1805.06561)", "url": "https://arxiv.org/abs/1805.06561",
                        "method": "JPEG tiles carry no georeferencing and the paper names only the countries (Thailand, Indonesia, India); Kaggle/CodaLab distribution not accessible"},
                note="8,570 tiles (6,226 train / 1,243 val / 1,101 test) at 0.5 m; the country-level footprint is already carried by the dataset record.")
