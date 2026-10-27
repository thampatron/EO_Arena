# EOArena task taxonomy

An open, filterable taxonomy of Earth observation (EO) tasks and labelled datasets, built to guide the benchmarking of geospatial foundation models (GeoFMs). Part of EOArena, a project of the Earth Intelligence Lab at MIT.

**Status: draft v0.3** (see [CHANGELOG.md](CHANGELOG.md)). Tags, licences and the ability filter are under review. Items marked UNVERIFIED could not be confirmed from a primary source.

**Site:** https://thampatron.github.io/EO_Arena/ (once GitHub Pages is enabled)

## What is here

| Page | What it shows |
|---|---|
| `index.html` | Explorer: every audited dataset tagged on 13 facets. Filter, search, cross two facets in a matrix, open a dataset for details, export CSV. Filter state lives in the URL. |
| `map.html` | Where labelled datasets exist: by country, or as the actual sample locations (Samples view). |
| `tasks.html` | Task template v0.2: shared rules, scoring, and the five task specifications from `spec/tasks/`. |
| `benchmarks.html` | Benchmark ranking: every benchmark with published GeoFM results, scored by how reliably it separates models (share of the observed model spread that exceeds seed noise), with dataset-specific signal and redundancy-adjusted information from a latent-factor fit. Static, from papers. The expert pairwise arena is planned for later. |
| `evidence.html` | Evidence map: one scatter plot per domain of every scored benchmark dataset on any two of the scoring metrics (score, frontier score, EDI, spread, seed noise, dataset-specific signal, info share, models…), coloured by subdomain, task family or verdict, hover for the numbers, click to open the dataset. |
| `domains.html` | 8 domains and 32 subdomains: framework anchors, sensors, datasets, benchmark status, gaps. |
| `sensors.html` | Open EO sensors by type: resolution, revisit, status, licence, benchmark use. |
| `about.html` | Method, filter definitions and how to contribute. |

## Data

The explorer reads two files, so the taxonomy can be corrected without touching any page code:

- `data/vocabulary.json`: the 13 filters and every allowed value (called `facets` in the files).
- `data/datasets.json`: one record per dataset, with its tags, licence, benchmark suites and sources.
- `data/domains.json` and `data/sensors.json`: the domain and sensor audits.
- `data/tasks.json` and `data/sensor_specs.json`: task cards and band specifications.
- `data/countries.geojson`: Natural Earth boundaries for the map.
- `data/evidence.json`: per-dataset scores from published GeoFM evidence following the lab's *GeoFM Benchmark Scoring* note: observed model spread, replicate (seed) noise where papers print it, the number of replicates behind each value, the reliability score τ²/(τ²+σ²) (τ² = τ²_obs − σ²/n) with bootstrap intervals, a frontier score on the leading half of each comparison, effective discriminative information, dataset-specific signal and redundancy-adjusted information share from a latent-factor regression, per-comparison detail and a plain-English explanation; counts and statistics only, no individual scores. Every dataset and dataset × protocol family is also scored under the analysis variants (σ² median/mean, self-reported kept/dropped, ridge 10/3) that the pages' *Analysis settings* strip switches. Built by `scripts/build_evidence.py` on top of `scripts/geofm_scoring.py` (fits cached in `scripts/.cache/`; `--fast` skips the slow diagnostics unless cached); see About → GeoFM evidence.
- `data/model_profiles.json`: model capability profiles θ from the latent-factor fit (independent and all evaluations), the principal axes with the datasets that load on them, and a general-ability scalar — kept for analysis; no page shows a model ranking at present; `data/replicate_plan.json` and `docs/replicate-plan.md`: the provisional datasets and the models to re-run with seeds to measure σ². `docs/benchmark-map-review.md` lists the mapping judgement calls to check.
- `data/benchmark_map.csv`: how each workbook benchmark id maps to a canonical dataset, an EOArena id (when the dataset is in the inventory), domain, subdomain and input kind. Hand-curated; correct it here when a mapping is wrong.
- `data/footprints/<id>.json` and the combined `data/footprints.json`: sample-level footprints (chip, tile, field or site centroids, up to 3,000 per dataset) with the source file and method each came from; built by `scripts/footprints/<id>.py` and `scripts/footprints/build_index.py`. See `scripts/footprints/BRIEF.md` for the extraction rules.

`scripts/export.py` writes machine-readable exports: a STAC catalogue (one Collection per dataset, `export/stac/`) and Croissant JSON-LD records (`export/croissant/`). Both validate against their official schemas.

### Interface spec (draft)

- `docs/model-input-survey.md` and `data/model_inputs.json`: how 10 geospatial foundation models declare their inputs and outputs.
- `docs/decisions-v0.2.md`: evaluation decisions with evidence.
- `docs/task-template.md`: the v0.2 task template and its conventions.
- `spec/`: task, result and model-card schemas, shared protocols, and five tasks (PASTIS-R, Sen1Floods11, EuroSAT, BioMassters, CH4Net).
- `scripts/make_manifest.py` and `scripts/conformance.py`: split manifests with checksums, and a check of real samples against a task.

`scripts/validate.py` checks every record against the vocabulary and every task template against the schema, band registry and protocols. It runs automatically on each pull request.

### Filters

Domain · Subdomain · Task family · Output unit · Output value · Time structure · Sensor · Resolution · Label source · Licence · Benchmark use · Footprint · GeoFM evidence · Ability tested (hypothesis)

The ability filter records which capability a task is expected to test (spectral, spatial, temporal, physical quantity, fusion). It is a hypothesis to be tested against how models rank across tasks, not an established fact.

## Roadmap

- **Map of every sample.** Done for 74 of 118 datasets (Samples view). 36 datasets have only named sites or a bounding box because their distribution (Google Drive, Kaggle, registration) or format (non-georeferenced chips) hides sample locations; 8 have no public location data. Next: footprints of pretraining corpora, to compare where models were trained with where benchmarks are.
- **Task cards for all datasets**, with the split type (spatial or random) confirmed for each.
- **Arena voting** (blind pairwise expert comparisons for needs without labels), once the rating formula is decided; the Benchmark ranking page currently holds the static benchmark ranking.

## Run locally

The pages load JSON, so serve the folder rather than opening files directly:

```
python3 -m http.server 8000
# open http://localhost:8000
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Corrections and missing datasets are welcome, as issues or pull requests.

## Licence

Code: MIT (see `LICENSE`). Taxonomy data (`data/`) and page text: CC BY 4.0. Each listed dataset keeps the licence set by its original provider; this repository does not redistribute any dataset.
