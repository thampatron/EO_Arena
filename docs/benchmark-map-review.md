# Benchmark map: judgement calls to review

`data/benchmark_map.csv` maps each of the 483 benchmark ids in the meta-analysis workbook to a canonical dataset, an EOArena id (when the dataset is in the inventory), a domain, a subdomain and an input kind. 187 ids come from the earlier audited mapping, 291 were matched by name to the workbook's own dataset names, 5 were named by hand. The following decisions were made without confirmation and should be checked by whoever knows the workbook best (Viki). Correct them in the CSV; the build picks the file up directly.

| # | Benchmark ids | Decision | Alternative |
|---|---|---|---|
| 1 | `uc_merced`, `ucm`, `gfm_ucm_cls` | Separate canonical "UC Merced (classification)" | Merge with "UC Merced" (which the workbook tags as text–image retrieval, `ucm_retrieval`) |
| 2 | `oscd_cd`, `x_oscd` | Both → "OSCD"; `x_oscd` is GeoCrossBench's cross-sensor variant (S2→S1), same imagery | Keep the cross-sensor variant separate |
| 3 | `forest_cover` (Google static-maps imagery), `sled_torchspatial_forest_cover` (coordinates) | Both → "MOSAIKS Forest cover", tagged coords-only | The imagery one is `eo_imagery`; split by input |
| 4 | `elevation` (MOSAIKS imagery) | New "MOSAIKS elevation" | Merge with "Elevation (Mapzen)" (coordinate task) |
| 5 | `ms_elevation`, `ms_population_density`, `ms_biome`, `ms_country_code` | → "Elevation (Mapzen)", "Population density", "Biomes", "Countries" (assumed SatCLIP-style coordinate tasks) | Keep as a separate suite |
| 6 | `median_income` (coords) vs `income_per_household` (imagery) | Kept as "MOSAIKS Income" (coords) and "MOSAIKS income" (imagery), as the workbook names them | Merge, or rename to make the split visible |
| 7 | `population_density` (imagery, 24 rows) | → "MOSAIKS population density" (imagery); coordinate zero-shot variants → "Population density" | — |
| 8 | `rs2800` | → "RSSCN7" (2,800 images; name match by size only) | Verify |
| 9 | `sled_torchspatial_flickr` | → "YFCC" (coords), distinct from "YFCC26k" geolocalisation | Merge |
| 10 | `tessera_ethiopia_crop` (2 rows) + AEBench `ethiopia_crops` | → "Ethiopia crops"; `tessera_austrian_crop_cls_100x` (ablation) → "Austrian Crop" | — |
| 11 | `geonrw_seg_ft_ablation_composite` | → "GeoNRW" (single-dataset ablation average, not a composite) | Treat as composite and exclude |
| 12 | `awf_*_val`, `nandi_*_val` | Validation-split rows merged into AWF / Nandi | Keep validation splits separate |
| 13 | `satlas_naip_*`, `satlas_s2_*` (14 ids) | All → "SatlasPretrain (composite)" (the only workbook name), though they are per-task heads | Split into per-task datasets and tag them |
| 14 | `coordbench_*` (20 ids), `sled_chelsa_*` | → four CoordBench composites by target group; CHELSA variables → "CHELSA-TraCE21k", `sled_chelsa_composite` → "(composite)" | — |
| 15 | `panopticon_designablation_avg` | New composite "Panopticon design ablation (composite)", excluded from scoring | — |

Only imagery datasets (`input_kind = eo_imagery`) outside the `composite` and `outside_taxonomy` domains are scored, so decisions 3–9 affect the Explorer's unlisted list more than the ranking.
