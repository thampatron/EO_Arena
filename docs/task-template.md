# Task template, v0.1 draft

A task template fixes three things: what a model is given, what it must predict, and how it is scored. It is written once per task, and every model is evaluated against it through its own adapter.

The template is built from the [model input survey](model-input-survey.md). Where existing tools already agree, we adopt their convention. Where they disagree, the template picks one convention and the model adapter converts to whatever its model expects.

Files:

| File | What it is |
|---|---|
| [`spec/task.schema.json`](../spec/task.schema.json) | JSON Schema for a task |
| [`spec/protocols.json`](../spec/protocols.json) | Evaluation protocols a task can name |
| [`spec/tasks/`](../spec/tasks) | Worked examples: PASTIS-R crop types, Sen1Floods11 surface water |
| [`scripts/validate.py`](../scripts/validate.py) | Checks each task against the schema, the band registry, the dataset list and the protocols |

## Conventions that hold for every task

These are fixed by the spec, not chosen per task. Each one answers a problem found in the survey.

| Convention | Rule | Survey problem it removes |
|---|---|---|
| Inputs | A dictionary keyed by modality (`s2`, `s1_asc`, …) | Channel-stacking sensors with different grids and dates |
| Layout | Each modality is `(T, C, H, W)` per sample, `(B, T, C, H, W)` batched | Five different layouts across models |
| Band identity | Every channel names a band in `data/sensor_specs.json`. Wavelengths are in µm; SAR bands carry polarisation and frequency | B02 vs B2 vs BLUE; µm vs nm; SAR placeholders |
| Derived layers | Declared by formula (`VV - VH`), never by name alone | PASTIS's ambiguous `VV-VH` layer |
| Values | Delivered in physical units: reflectance 0–1, backscatter in dB. Each modality declares `scale`, `offset`, `nodata` and `unit`, following the STAC raster extension | Undeclared ×10⁴ scaling, linear vs dB |
| Missing data | A boolean `valid` mask per modality, shape `(T, H, W)`, where **true = valid**. No-data pixels are never replaced by a number | AnySat 1 = valid vs Galileo 1 = missing; PANGAEA turning S1 NaN into 0 dB |
| Time | ISO 8601 UTC date per time step, per modality | Five date encodings; 0- vs 1-based day of year |
| Location | `{lon, lat}` in EPSG:4326, as named keys | lat/lon order disagreements |
| Resolution | `gsd_m` of the delivered grid, per modality | Only two models take GSD; the rest assume it |
| Normalisation | Not applied by the task. The task offers train-split statistics; the adapter uses them or its model's pretraining statistics, and the result records which | PANGAEA normalising with dataset statistics against the model authors' intent |

## Rules for model adapters

The template is task-side. These rules, which the model-side contract will formalise, keep comparisons honest:

1. **No silent band handling.** An adapter declares which task bands it uses and how it fills bands the model expects but the task lacks. Every result records `bands_used` and `fill_rule`. This replaces PANGAEA's silent drop and zero-fill.
2. **Encoding happens in the adapter.** Dates, location and GSD are converted there into the model's format: Prithvi's `[year, doy]`, Galileo's months, Clay's sin/cos, and so on.
3. **Declared outputs.** An adapter returns a pooled embedding, a list of feature maps with their strides, or both. A protocol that needs something the model cannot give is reported as not applicable, not approximated.

## Fields of a task

| Field | Holds |
|---|---|
| `id`, `title`, `dataset_id` | The link to `data/datasets.json`, which supplies domain, subdomain and licence |
| `task_type` | classification, multilabel, segmentation, pixel or image regression, change detection, detection |
| `inputs.<modality>` | `sensor`, `product` (L1C, L2A, GRD), `quantity` (TOA or surface reflectance, σ⁰…), `orbit`, `required`, `bands`, `raster`, `grid`, `time`. `time.selection` must say how the delivered steps are chosen |
| `sample_metadata` | Whether location and dates exist, and at what granularity |
| `target` | Kind, the grid it shares, classes with indices, `ignore_index`, units for regression, `label_source` |
| `splits` | Kind (random, spatial blocks, regions, temporal, or predefined-unknown) and the exact definition |
| `evaluation` | Primary and secondary metrics with their averaging, protocols, inference mode, number of seeds, label fractions |
| `normalisation_stats` | Optional per-band mean and std in physical units, with where they were computed |
| `harness_notes` | Where PANGAEA or another harness does something different |
| `unverified` | JSON Pointers to every field not confirmed by a primary source; the validator checks they resolve |
| `open_questions` | Decisions still to take for this task |

## Protocols

| Protocol | Trained | Model must return | Notes |
|---|---|---|---|
| `frozen-knn` | nothing | pooled embedding | Classification only |
| `frozen-linear` | linear head | pooled embedding, or last-layer tokens for dense tasks | Every surveyed model can run it |
| `frozen-upernet-pangaea` | UPerNet (+ L-TAE for time series) | four feature maps | PANGAEA defaults: AdamW 1e-4, 80 epochs, batch 8 |
| `finetune` | encoder and head | as the head needs | Budget to be decided |

The two example tasks use three seeds, not PANGAEA's single default seed, so that between-model differences can be compared against seed noise. This is the quantity the aggregation rule needs.

## What the worked examples showed

Writing the two examples from primary sources turned up problems in the current PANGAEA versions:

- **PASTIS-R.** PANGAEA chooses 6 time steps by index, not date, and drops the dates, so no model can use acquisition time. It uses only the ascending Sentinel-1 series. The S2 product level, the scale factor and the meaning of the third SAR layer are not stated in the dataset's README.
- **Sen1Floods11.** PANGAEA replaces S1 no-data (NaN) with 0 dB, which is bright backscatter, with no mask. Chips without event metadata get the date 13 October 1998. The README confirms L1C TOA reflectance ×10⁴ and S1 in dB.

## Decisions for the lab

Proposed answers, with evidence, are in [decisions-v0.2.md](decisions-v0.2.md).

1. **Time-step selection.** Should we keep PANGAEA's 6 index-spaced steps for comparability, or pick steps by calendar date?
2. **Variable-length series.** Should a task also offer the full series for models built for it?
3. **Default protocol for the leaderboard.** `frozen-linear` measures the representation and runs on every model; `frozen-upernet-pangaea` matches published numbers but excludes Clay and AnySat.
4. **Splits.** Neither example's official split is region-disjoint (PASTIS folds are buffered by 1 km within the same tiles; Sen1Floods11 is random, with Bolivia held out). Should we add a spatial split alongside the official one?
5. **Label fractions.** Should every task also run at, for example, 1% and 10% of training labels?
