# Task template, v0.2 draft

A task template fixes three things: what a model is given, what it must predict, and how it is scored. v0.2 implements the decisions in [decisions-v0.2.md](decisions-v0.2.md), which gives the evidence for each. The input conventions come from the [model input survey](model-input-survey.md).

## Files

| File | What it is |
|---|---|
| [`spec/task.schema.json`](../spec/task.schema.json) | Schema for a task. Only a core is required; extra fields are allowed until v1 |
| [`spec/protocols.json`](../spec/protocols.json) | Rules shared by every task: tracks, runs, tuning, reporting, adapter rules, pretraining overlap |
| [`spec/result.schema.json`](../spec/result.schema.json) | One record per model, task, track, label fraction and run, including what the adapter did |
| [`spec/model_card.schema.json`](../spec/model_card.schema.json) | Stub: what a model must declare (inputs, outputs, pretraining footprint) |
| [`spec/tasks/`](../spec/tasks) | Five tasks (below) |
| [`scripts/validate.py`](../scripts/validate.py) | Checks tasks against the schema, band registry, dataset list and protocols (runs in CI) |
| [`scripts/make_manifest.py`](../scripts/make_manifest.py) | Builds split manifests with per-file SHA-256, and nested label-fraction subsets |
| [`scripts/conformance.py`](../scripts/conformance.py) | Checks real samples against a task: shape, dtype, nodata masking, physical value range, dates, location, labels |

## The five tasks

| Task | Type | Inputs | Official split | Extra test | Why it is here |
|---|---|---|---|---|---|
| `pastis-r-cropseg` | segmentation | S2 L2A + S1 ascending, 6 calendar windows | folds with a 1 km buffer | hold out tile T32ULU (proposed) | multi-temporal, multi-modal |
| `sen1floods11-water` | segmentation | S2 L1C + S1, single date | random 60/20/20 | Bolivia (defined by the dataset) | S1 no-data handling |
| `eurosat-landcover` | classification | S2, 13 bands, 64 px | random 60/20/20 (TorchGeo) | longitude split (TorchGeo EuroSATSpatial) | image-level path; small inputs |
| `biomassters-agb` | pixel regression | S2 L2A + S1 asc + S1 desc, 12 months | random within year | 2021 held out; spatial blocks (proposed) | physical-unit target; missing months |
| `ch4net-plumes` | segmentation | S2 L1C, single date | temporal (2021 test) | new site: not possible | subdomain 6.1 has no benchmark task |

## Conventions that hold for every task

| Convention | Rule |
|---|---|
| Inputs | A dictionary keyed by modality; each is `(T, C, H, W)` with a `(T, H, W)` boolean valid mask, **true = valid** |
| Bands | Every channel names a band in `data/sensor_specs.json` (wavelengths in µm), or is a declared derived or auxiliary layer |
| Values | Physical units: physical = stored × scale + offset. Pixels equal to nodata are marked invalid and never passed as values |
| Time | Multi-step inputs are chosen by calendar window, not by index. Every step carries an ISO 8601 date (a month, `YYYY-MM`, for monthly composites). Empty windows are masked invalid. An existing harness's rule is kept only as `comparison_rule`, run once to measure the difference |
| Location | `{lon, lat}` in EPSG:4326 |
| Target | Metrics are computed on the task's target grid; labels are never resampled to fit a model |
| Data | Every split and label subset is a manifest of sample ids and per-file SHA-256 at a pinned revision |

## Evaluation (from `spec/protocols.json`)

- **Ranked tracks:**
  - `frozen-decoder`: UPerNet for dense tasks, an MLP for image-level tasks, L-TAE for single-step models on time series; 10 runs.
  - `finetune`: 5 runs.
- **Unranked diagnostics:** `knn` and `linear-probe`.
- **Tuning:** 16 Optuna TPE trials per model, task and track, selected on validation only. Learning rate 1e-5 to 1e-2 on the frozen track and 1e-6 to 1e-3 for fine-tuning; batch size 8, 16 or 32; AdamW, weight decay 0.01, up to 50 epochs, early stopping after 10.
- **Label fractions:** 100%, 10% and 1%, nested and stratified, one subset per run. Fractions leaving fewer than the task's minimum sample count are skipped.
- **Reporting:**
  - per task, a 95% bootstrap interval over runs and over test samples;
  - across tasks, the interquartile mean of min-max normalised scores with a stratified bootstrap;
  - pairwise, P(A>B), with 0.25–0.75 reported as tied;
  - Kendall's τ between the two tracks;
  - results grouped by the modalities each model read;
  - every run and trial published.
- **Adapter rules:** declare the bands used and the fill rule, the resizing method (tile or bilinear upsampling, no resampling to the pretraining resolution) and the normalisation source; map predictions back to the target grid. The result record stores all of it.
- **Pretraining overlap:** the share of test samples inside the model's declared pretraining footprint. Results are flagged above 0.1 (a placeholder), never excluded.

## What is not done yet

- **Manifests.** None are built yet; every task has `manifest_status: pending`. Building them needs the data downloaded, and each dataset converted into the delivery format the conformance check expects.
- **Tool testing.** The conformance and manifest scripts were tested on synthetic samples only.
- **Choices still to test:**
  - the final-layer-only rule for Clay and AnySat;
  - the learning-rate range for the frozen track;
  - kNN with k = 20;
  - the MLP head size;
  - tuning once at 100% labels and reusing the result for every fraction.
- **Model cards.** Only a stub exists; the model-side contract is the next step.

## What writing the new tasks found

- **CH4Net:**
  - Its data are licensed **CC BY-NC-ND 4.0** on Hugging Face, not CC BY 4.0 as our taxonomy said; the record is now corrected. EOArena probably cannot redistribute converted copies.
  - The release has 8,255 / 255 / 2,473 files, which does not match the paper's 10,046 images.
  - The code uses 12 bands where the paper says 13.
  - There is no site or date metadata.
- **BioMassters:**
  - PANGAEA's normalisation statistics are placeholder zeros.
  - PANGAEA fills missing months and S1 no-data with zeros without masking them.
  - PANGAEA's RMSE is not the competition's per-chip RMSE.
  - Sources disagree on whether label 0 can mean missing data, and on the unit.
- **EuroSAT:** the channel order puts B8A after B12. GEO-Bench's `m-eurosat` records the wrong band names for most channels.
- **PASTIS:** the four tiles span 2018-09-17 to 2019-10-27. No cloud mask is shipped, so windows use the acquisition nearest each window's centre.
