# Contributing to the EOArena taxonomy

Thank you for helping. The taxonomy is only useful if it is accurate and complete, and the people who build and use EO datasets know them best.

## Quick corrections

Open an issue with:
- the dataset name,
- what is wrong (a tag, the licence, a size, a missing benchmark suite),
- a link to the source that shows the correct value (paper, dataset page, licence file).

## Adding or editing a dataset

1. Edit `data/datasets.json`. Copy an existing record as a template.
2. Use only values listed in `data/vocabulary.json`. Filters that can take several values: task family, sensor, resolution, ability. All others take exactly one.
3. Give at least one source URL, preferably the paper and the official data page.
4. For `licence`, quote the dataset's own licence (e.g. "CC BY 4.0"). Set the `tier` tag:
   - `open`: public domain, CC0, CC BY, CC BY-SA, ODbL, or an open agency policy;
   - `reg`: free, but with the provider's own terms (registration, no redistribution);
   - `nc`: non-commercial licences (CC BY-NC and similar);
   - `closed`: paid, quota or restricted access;
   - `unk`: you could not find the licence (write UNVERIFIED in `licence`).

   For `p` (label source), use `model` whenever the labels come from another model or product (for example a biomass map or a MODIS fire product). These are shown as model-derived.
5. Set `footprint.scope` to `countries` (and list ISO 3166-1 alpha-3 codes), `region` (and name it in `footprint.region`), `global`, or `unknown`. Use only what the dataset's own documentation states.
6. List `benchmark_suites` only if the dataset is actually used in that benchmark's published task list.
7. Run `python3 scripts/validate.py`. It must print `OK`. Then run `python3 scripts/export.py` to refresh the STAC and Croissant exports.
8. Open a pull request describing the change and its source.

## Record format

```json
{
  "id": "lowercase-words-with-hyphens",
  "name": "Dataset name",
  "domain": "1 · Agriculture",
  "subdomain": "1.1 Cropland and crop type",
  "task_description": "Semantic segmentation, time series",
  "sensors_description": "S2 (+S1)",
  "geography": "France",
  "size": "2,433 patches",
  "facets": {
    "task": ["SS"], "unit": ["P"], "val": ["C"], "tmp": ["T"],
    "sen": ["S2", "S1"], "res": ["M"], "p": ["measured"],
    "tier": ["open"], "ab": ["TD", "FU"]
  },
  "footprint": {"scope": "countries", "countries": ["FRA"]},
  "licence": "CC BY 4.0",
  "benchmark_suites": ["PANGAEA"],
  "sources": [{"label": "Paper", "url": "https://..."}]
}
```

## Changing the vocabulary

New filter values (for example a new sensor or task family) change how everything is grouped. Propose them in an issue first so they can be discussed before records use them.

## What counts as a dataset here

A labelled dataset that uses remote sensing inputs (satellite, aerial or drone) and has a public paper or data page. Map products without released training or reference labels are listed in the domain audit, not as datasets.

## Task cards

`data/tasks.json` holds task cards: the exact inputs (sensors, bands with centre wavelength, FWHM and resolution), image size, time steps, output classes, metric, split and protocol. Take values from a benchmark's published configuration or the dataset paper, and mark anything not stated there as UNVERIFIED. Band specifications for Sentinel-2, Landsat 8/9 and Sentinel-1 live in `data/sensor_specs.json`.
