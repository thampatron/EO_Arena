# EOArena task taxonomy

An open, filterable taxonomy of Earth observation (EO) tasks and labelled datasets, built to guide the benchmarking of geospatial foundation models (GeoFMs). Part of EOArena, a project of the Earth Intelligence Lab at MIT.

**Status: draft v0.1.** Tags, licences and the ability filter are under review. Items marked UNVERIFIED could not be confirmed from a primary source.

**Site:** https://thampatron.github.io/EO_Arena/ (once GitHub Pages is enabled)

## What is here

| Page | What it shows |
|---|---|
| `index.html` | Explorer: every audited dataset tagged on 13 facets. Filter, search, cross two facets in a matrix, open a dataset for details, export CSV. Filter state lives in the URL. |
| `map.html` | Where labelled datasets exist, by country. |
| `tasks.html` | Task cards: exact inputs, bands, outputs, metric, split and protocol. |
| `arena.html` | The expert arena: blind pairwise comparisons for needs without labels. Rating formula to be decided. |
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

`scripts/export.py` writes machine-readable exports: a STAC catalogue (one Collection per dataset, `export/stac/`) and Croissant JSON-LD records (`export/croissant/`). Both validate against their official schemas.

### Interface spec (draft)

- `docs/model-input-survey.md` and `data/model_inputs.json`: how 10 geospatial foundation models declare their inputs and outputs.
- `docs/decisions-v0.2.md`: evaluation decisions with evidence.
- `docs/task-template.md`: the v0.2 task template and its conventions.
- `spec/`: task, result and model-card schemas, shared protocols, and five tasks (PASTIS-R, Sen1Floods11, EuroSAT, BioMassters, CH4Net).
- `scripts/make_manifest.py` and `scripts/conformance.py`: split manifests with checksums, and a check of real samples against a task.

`scripts/validate.py` checks every record against the vocabulary and every task template against the schema, band registry and protocols. It runs automatically on each pull request.

### Filters

Domain · Subdomain · Task family · Output unit · Output value · Time structure · Sensor · Resolution · Label source · Licence · Benchmark use · Footprint · Ability tested (hypothesis)

The ability filter records which capability a task is expected to test (spectral, spatial, temporal, physical quantity, fusion). It is a hypothesis to be tested against how models rank across tasks, not an established fact.

## Roadmap

- **Map of every sample.** Once EOArena hosts task data, the map will plot the location of every tile or sample in each hosted dataset, instead of only the countries it names. This needs sample-level footprints (for example STAC items per tile), which also let us check spatial splits and geographic bias directly.
- **Task cards for all datasets**, with the split type (spatial or random) confirmed for each.
- **Arena voting**, once the rating formula is decided.

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
