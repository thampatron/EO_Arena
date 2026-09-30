# Contributing to the EOArena taxonomy

Thank you for helping. The taxonomy is only useful if it is accurate and complete, and the people who build and use EO datasets know them best.

## Quick corrections

Open an issue with:
- the dataset name,
- what is wrong (a tag, the licence, a size, a missing benchmark suite),
- a link to the source that shows the correct value (paper, dataset page, licence file).

## Adding or editing a dataset

1. Edit `data/datasets.json`. Copy an existing record as a template.
2. Use only values listed in `data/vocabulary.json`. Facets that can take several values: task family, sensor, resolution, ability. All others take exactly one.
3. Give at least one source URL, preferably the paper and the official data page.
4. For `licence`, quote the dataset's own licence (e.g. "CC BY 4.0"). Set the `tier` facet:
   - `open`: public domain, CC0, CC BY, CC BY-SA, ODbL, or an open agency policy;
   - `reg`: free, but with the provider's own terms (registration, no redistribution);
   - `nc`: non-commercial licences (CC BY-NC and similar);
   - `closed`: paid, quota or restricted access;
   - `unk`: you could not find the licence (write UNVERIFIED in `licence`).
5. List `benchmark_suites` only if the dataset is actually used in that benchmark's published task list.
6. Run `python3 scripts/validate.py`. It must print `OK`.
7. Open a pull request describing the change and its source.

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
    "tier": ["open"], "covk": ["c4"], "ab": ["TD", "FU"]
  },
  "licence": "CC BY 4.0",
  "benchmark_suites": ["PANGAEA"],
  "sources": [{"label": "Paper", "url": "https://..."}]
}
```

## Changing the vocabulary

New facet values (for example a new sensor or task family) change how everything is grouped. Propose them in an issue first so they can be discussed before records use them.

## What counts as a dataset here

A labelled dataset that uses remote sensing inputs (satellite, aerial or drone) and has a public paper or data page. Map products without released training or reference labels are listed in the domain audit, not as datasets.
