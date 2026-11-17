# Dataset properties for discriminating GeoFMs: gaps, angles, findability, suspect input labels

Companion to `dataset_parameters.json` (94 datasets, one object each). Values come from public sources that I opened: arXiv HTML/PDF of the benchmark-suite papers and the dataset papers, plus one DTU data page. Benchmark-suite papers used: GEO-Bench, GEO-Bench-2, PANGAEA, Copernicus-Bench, OlmoEarth v1/v1.2, NeuCo-Bench, MMEarth-Bench, Cryo-Bench v1/v2, SustainFM, Better Together, GeoCrossBench, EarthShift, Panopticon, TESSERA, Galileo, CROMA, SatMAE, Presto, AGBD-eval, Infra-Bench, GEOID-Flood and ExEBench.

## Part 1: properties worth collecting, and why each could matter

- **Number of classes / target type.** Few-class tasks (binary water, burn scar) leave little room between models. Many-class or multi-label and fine-grained tasks (FBP 24, MADOS 15, GEA 110) separate representations more. Regression tasks behave differently again.
- **Train/val/test sizes (in the benchmark version).** Small training sets make pretraining matter more, which aids discrimination. Very small test sets (Cashew 50, SICD 20 scenes, OSCD, DSE 98 tiles) add seed noise that can swamp the differences between models.
- **GSD (finest/coarsest).** Models pretrained at 10 m differ from models pretrained on VHR imagery. PANGAEA and Cryo-Bench both show that resolution mismatch reorders rankings.
- **Number and type of bands.** RGB-only models are handicapped on spectral tasks such as MADOS, BioMassters and crops. SAR-only and L-band inputs test cross-modal transfer.
- **Patch size (px).** This interacts with ViT patch size and resizing. OlmoEarth and Galileo report sensitivity to patch size (Cashew, MADOS).
- **Temporal structure / number of timesteps.** Most GeoFMs are single-image, so time-series tasks (PASTIS, BioMassters, DynamicEarthNet, CTM-SS) reward temporal models. Pooling choices also change results.
- **Label source** (manual / map product / in-situ / model-derived / crowdsourced). Model-derived labels (Dynamic World, GEDI, WorldPop) partly measure agreement with another model. OSM weak labels (Infra-Bench, Substations) put a ceiling on accuracy.
- **Label granularity** (pixel / patch / box / point). This sets which decoder and pooling are used, and thus the dependence on the protocol.
- **Class imbalance.** Rare classes make mIoU unstable (MADOS, SICD, GLID at 1.9% foreground) and add between-seed variance unrelated to the model.
- **Geographic extent / number of regions.** Single-site datasets (Borneo CHM, Houston, Nandi) test local fit. Global ones test the breadth of pretraining.
- **Split type** (random / spatially disjoint / temporal). Random splits leak spatial autocorrelation: Infra-Bench reports that 46.5% of tiles changed assignment under spatial blocking. Spatially or temporally disjoint splits measure generalisation and change rankings (MMEarth-Bench Africa test, EarthShift).
- **Imagery years.** These matter for overlap with pretraining years and for label/imagery mismatch (Better Together uses 2024 embeddings with 2020 GEDI labels).
- **Publication year.** Older datasets are more likely to sit inside pretraining corpora and to be tuned against.
- **Saturation / spread of published scores.** Near-ceiling datasets (EuroSAT-S2, m-brick-kiln, PV4GER) and narrow-spread datasets (GSDD 4.1 points, Sen1Floods11, Kuro Siwo, GEOID-Flood, SpaceNet 1) cannot rank models. Spread is a better measure than the raw ceiling.
- **Overlap with pretraining corpora.** Examples: fMoW and fMoW-Sentinel are inside the SatMAE and Panopticon pretraining data; SpectralEarth (the source of EnMAP-CORINE) is inside Panopticon's; OSM infrastructure classes are inside the SatlasPretrain and OlmoEarth objectives; MMEarth-Bench shares MMEarth's modalities. Overlap inflates scores for the models concerned.
- **Standard metric.** mIoU, accuracy, R2 and RMSE have different sensitivities. bIoU vs mIoU changed conclusions on Harvey (GeoCrossBench).
- **Licence.** This affects which suites include the dataset (GEO-Bench-2 filters to permissive licences, e.g. only the CC-BY-SA part of FTW).
- **Canonical paper / data URL.** Needed for provenance.
- **Additional angles worth adding:**
  - Evaluation protocol per suite: frozen vs fine-tuned, decoder type, how timesteps are pooled. The same dataset (PASTIS, Sen1Floods11, BigEarthNet) appears in 3 to 6 different configurations.
  - Whether a supervised baseline (UNet) beats the GFMs: PANGAEA HLS Burn Scars, Sen1Floods11, AI4SmallFarms; Cryo-Bench overall.
  - Inputs that are precomputed embeddings rather than raw imagery (the Better Together tasks and TESSERA's Borneo task).
  - Number of independent scenes or events behind the samples (SICD 461 scenes, OSCD 24 cities, Kuro Siwo 43 events). This is the effective sample size for the test.
  - Variance across seeds, where it is reported.

## Findability

- **Found for most datasets (>=75/94):** target type, band description, temporal structure, label granularity, label source (87), geographic extent (89), GSD (82), publication year (92), patch size (75), number of timesteps (76).
- **Found for about half:** split type (70), n_classes (71; null mostly where the target is regression), n_bands (61), number of countries/regions (54), best-score note (54), saturation flag (46), licence (49).
- **Hard to find:**
  - Exact train/val/test sizes in the evaluated version (about 40). Suite papers often give totals only; SustainFM gives no splits.
  - Imagery years (39).
  - Class-imbalance figures (16).
  - Pretraining-overlap statements (15; only filled when a source states it).
  - Data URLs (10).
- **Weakest entries:**
  - OlmoEarth partner tasks (AWF, Nandi, LFMC, Mangrove, GEA, Forest Loss Driver, Solar Farm, Vessel x3). The OlmoEarth paper gives total counts and classes only, with no GSD, patch size, split or years.
  - TropicalCyclone, Hyperview, RSBD and DSE: few details read.

## Input labels that look wrong or misleading (field: input value, then what the source says)

1. **AGBD** `sensor_raw=s2_s1`. AGBD and the AGBD-eval paper use Sentinel-2 plus ALOS-2 PALSAR-2 L-band HH/HV, plus DEM, canopy height and land cover. Sentinel-1 is not an input. AGBD-eval also notes that no GFM natively supports the L-band input.
2. **CORINE (Panopticon)** `sensor_class=high-resolution optical`. The inputs are SuperDove/MODIS bands simulated from 30 m EnMAP hyperspectral (SpectralEarth EnMAP-CORINE), so the class should be hyperspectral-derived, 30 m.
3. **Hyperview** `sensor_class=high-resolution optical`, domain/subdomain empty. The inputs are SuperDove/MODIS simulated from 150-band hyperspectral imagery (Intuition-1 configuration). The target is soil P/K/Mg/pH from lab analysis in Poland, i.e. an agriculture/soil domain.
4. **MMEarth-Bench species** `subdomain=2.4 Vegetation structure`. The target is the occurrence of 100 terrestrial mammal species from IUCN range polygons, i.e. biodiversity/species distribution.
5. **EverWatch** `subdomain=2.4 Vegetation structure`. The task is detection of wading-bird species (wildlife/biodiversity).
6. **AI4SmallFarms** `n_samples_known=439001`. This is the number of field polygons, not samples (the dataset has 62 tiles of 5x5 km).
7. **CropTypeMapping South Sudan** `n_samples_known=837`. This is the number of fields.
8. **GEOID-Flood** `n_samples_known=2674`. The paper reports 14,282 tiles; 2674 is probably a subset or test count.
9. **Brick kilns** `region=South Asia`. The source dataset is Bangladesh.
10. **ForestNet** region empty. The dataset is Indonesia; the GEO-Bench-2 appendix wrongly says South Asia.
11. **Empty sensor fields.** Chesapeake is NAIP aerial RGBN at 1 m. DIOR and RESISC45 are Google Earth RGB (0.2–30 m, high-resolution optical).
12. **Better Together tasks** (GRIP4, WorldClim, WorldPop, MMEarth Biomass, CropHarvest bt_, and Dynamic World labelled `s2 multispectral`). Inputs are precomputed 2024 AlphaEarth/TESSERA pixel embeddings plus location encoders, not imagery. The Dynamic World labels are themselves model outputs.
13. **CloudSEN12** `sensor_class=SAR + optical`. This holds only for the GEO-Bench-2 version; the Copernicus-Bench Cloud-S2 version is Sentinel-2 only.
14. **OlmoEarth Vessel Detection** `sensor_class=SAR`. It includes a Landsat (optical) variant.
15. **AWF and Nandi** `sensor_class=multispectral`. Their variants include Sentinel-1-only and S1+S2.
16. **NeuCo-Bench Landcover** `subdomain=1.1 Cropland`. It has two targets: agriculture fraction and forest fraction.
17. **GeoCrossBench Hurricane Harvey** `task=change detection` for both ids. x-harvey-building is building segmentation; only x-harvey-flood is change detection.
18. **GLD.** This exists only in Cryo-Bench v1. Cryo-Bench v2 replaced it with GLB (global, S2+S1+terrain, 11 bands).
19. **BigEarthNet v1/v2 merged into one row.** Class counts differ: 43 in GEO-Bench m-bigearthnet vs 19 in BENv2/Copernicus. Splits also differ (random-ish v1 vs geographic v2). Consider splitting the row by version.
20. **Kuro Siwo.** GEO-Bench-2 lists 4 classes; Copernicus-Bench Flood-S1 uses 3. Same row, different targets.
21. **Missing or odd subdomain codes.** xBD (`Post-event damage...` with no code), GAZADeepDAV (`z.1`), and null subdomains for Digital Typhoon, TropicalCyclone, WorldClim, WorldPop, Hyperview and the MMEarth soil tasks.

## Observations relevant to the sensor-explains-everything finding

- Several properties co-vary with sensor and could confound it:
  - Label source: the SAR tasks are mostly flood or ice, with expert labels.
  - GSD: VHR RGB tasks are mostly object or building tasks.
  - Use of embeddings instead of imagery: the Better Together tasks.
  - Split type and saturation are worth adding as covariates before attributing variance to sensor.
- Low-discrimination datasets according to their own suites:
  - GSDD (4.1-point spread)
  - Sen1Floods11 (78–80% for all models per OlmoEarth; UNet best in PANGAEA)
  - Copernicus Flood-S1 (75–78)
  - GEOID-Flood (0.84–0.88 IoU)
  - SpaceNet 1 (86–90)
  - m-eurosat, m-brick-kiln and m-pv4ger (>95%)
