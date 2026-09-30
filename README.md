# EOArena task taxonomy

An open, filterable taxonomy of Earth observation (EO) tasks and labelled datasets, built to guide the benchmarking of geospatial foundation models (GeoFMs). Part of EOArena, a project of the Earth Intelligence Lab at MIT.

**Status: draft v0.1.** Tags, licences and the ability facet are under review. Items marked UNVERIFIED could not be confirmed from a primary source.

**Site:** https://thampatron.github.io/EO_Arena/ (once GitHub Pages is enabled)

## What is here

| Page | What it shows |
|---|---|
| `index.html` | Explorer: every audited dataset tagged on 13 facets. Filter, search, cross two facets in a matrix, open a dataset for details, export CSV. Filter state lives in the URL, so views can be shared. |
| `domains.html` | 8 domains and 32 subdomains: framework anchors, open sensors, datasets, benchmark status, gaps and proposed changes. |
| `sensors.html` | Open EO sensors by type: resolution, revisit, status, licence and use in GeoFM benchmarks. |
| `about.html` | Method, facet definitions and how to contribute. |

## Data

The explorer reads two files, so the taxonomy can be corrected without touching any page code:

- `data/vocabulary.json`: the facets and every allowed value (the controlled vocabulary).
- `data/datasets.json`: one record per dataset, with its facet tags, licence, benchmark suites and sources.
- `data/domains.json` and `data/sensors.json`: the domain and sensor audits.

`scripts/validate.py` checks every record against the vocabulary. It runs automatically on each pull request.

### Facets

Domain · Subdomain · Task family · Output unit · Output value · Time structure · Sensor · Resolution · Label source · Licence · Benchmark use · Coverage · Ability tested (hypothesis)

The ability facet records which capability a task is expected to test (spectral, spatial, temporal, physical quantity, fusion). It is a hypothesis to be tested against how models rank across tasks, not an established fact.

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
