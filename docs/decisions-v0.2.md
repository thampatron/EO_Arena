# Evaluation decisions for task template v0.2

Status: proposed, 30 September 2026. Each decision gives the evidence, the reasoning, and what changes in the template. Anything the sources do not settle is marked **UNVERIFIED** or labelled as our own choice.

## Summary

| # | Question | Decision |
|---|---|---|
| 1 | Evaluation protocol | Two ranked tracks: **frozen encoder + fixed decoder** (primary, run first) and **fine-tuning** (second phase). kNN and linear probes are reported as diagnostics, not ranked. Rank agreement between tracks is published. |
| 2 | Time steps | Select by **calendar window**, not by index. Dates are always delivered. PANGAEA's index rule is run once per task, only to measure the difference. |
| 3 | Splits | Keep the official split, and add an **out-of-region test split** wherever geography allows. Report both. |
| 4 | Runs and uncertainty | **10 runs** on the frozen track, **5** on fine-tuning. Each run varies initialisation, data order and label subset. Report bootstrap CIs, IQM across tasks, and P(A>B). |
| 5 | Tuning budget | **Same search space and 16 trials** for every model, selected on validation only. Publish every trial. |
| 6 | Label fractions | **100%, 10% and 1%**, as fixed nested subsets, one subset per run. |
| 7 | Image size | Tasks deliver the native grid. Adapters tile larger images and upsample smaller ones to the model's input size, and must declare which they did. Metrics are always computed on the native label grid. |
| 8 | Normalisation | Use the model's own pretraining statistics when it ships them; otherwise use train-split statistics. The result records which. |
| 9 | Pinning data | Every split is a **manifest** of sample ids and per-file SHA-256, at a pinned data revision. A conformance check tests real samples against the template. |
| 10 | Pretraining overlap | Model cards declare their pretraining footprint. EOArena computes the share of test samples inside it and **flags** the result; nothing is excluded. |
| 11 | Inputs used | Results are grouped by the set of modalities a model actually read. |
| 12 | Template shape | A small required core, optional descriptive fields, and extra fields allowed until v1. |

## 1. Evaluation protocol

**Evidence**
- The protocol changes the ranking:
  - PANGAEA found "no strong downstream performance advantage between a frozen encoder and end-to-end fine-tuning" ([PANGAEA §1, §5.8](https://arxiv.org/html/2412.04204)).
  - GEO-Bench-2 found the opposite: "full fine-tuning consistently outperformed the frozen backbone approach… ranking changes for over 20% of model pairs". It also found a linear decoder "consistently underperformed… leading to notable ranking changes" ([GEO-Bench-2 §5, App. 6.3.3](https://arxiv.org/html/2511.15658v2)).
  - In natural images, linear probing and fine-tuning "are largely uncorrelated" ([MAE §4.3](https://arxiv.org/html/2111.06377)).
  - kNN and linear probing reverse the order of SeCo and ImageNet weights on EuroSAT ([Corley et al., Table 8](https://arxiv.org/html/2305.13456)).
- Model papers each use a different protocol:
  - TerraMind uses PANGAEA's frozen encoder with UPerNet.
  - Copernicus-FM uses frozen encoders with linear probes and UPerNet.
  - Galileo uses kNN, linear probes and fine-tuning.
  - DOFA uses all three.

**Reasoning.** Every single protocol builds a bias into the leaderboard, so the choice has to be deliberate.
- The frozen encoder with a fixed decoder is cheap. It isolates the representation, which is the question the CAREER aim asks: which model to use for which task. It is also directly comparable with PANGAEA.
- Fine-tuning is how practitioners actually use models, and it is where GEO-Bench-2 saw the rankings move.
- A linear head on dense tasks is too weak. GEO-Bench-2 shows it reorders models for reasons unrelated to the representation.

This reverses my earlier suggestion to make the linear probe primary.

**Decision**
- **Frozen track (primary, run first).**
  - Dense tasks use UPerNet.
  - Image-level tasks use an MLP head.
  - If a model exposes only its final layer (Clay, AnySat), that layer feeds every decoder level. The result is flagged. This is our own rule and needs a check that it does not systematically penalise those models.
- **Fine-tuning track (second phase).** Run under the same tuning budget (decision 5).
- **kNN and linear probe.** Reported as cheap diagnostics, not ranked.
- **Rank agreement.** Publish Kendall's τ between tracks per task, as GEO-Bench-2 did.

## 2. Time-step selection

**Evidence**
- **PANGAEA** keeps "6 captures evenly distributed over time" by index (`torch.linspace` over positions). It returns empty metadata, so dates never reach the model ([PANGAEA App. A.3](https://arxiv.org/html/2412.04204); `pangaea/datasets/pastis.py`).
- **GEO-Bench-2** also selects by index stride. It returns the *last* N dates, which do not match the selected frames (`geobench_v2/datasets/pastis.py`, main branch).
- **Galileo** uses monthly aggregates for PASTIS, so its selection is date-based ([Galileo App. C](https://arxiv.org/html/2502.09356)).
- **No study ablates date-based against index-based selection** (UNVERIFIED that none exists; none was found).
- Temporal encoders (PSE-TAE, L-TAE) use days elapsed "instead of its index" to handle irregular sampling ([PSE-TAE](https://arxiv.org/abs/1911.07757)).

**Reasoning**
- With index selection, two samples can see different seasons at the same position.
- Date-aware models (Prithvi-TL, AnySat, Galileo, Copernicus-FM) are denied the information they were built to use.
- Calendar windows make position t mean the same period for every sample. Measuring the gap once turns an untested assumption into a finding.

**Decision**
- Each task defines T calendar windows over its season.
- Per window, the delivered frame is the clearest acquisition. Compositing is allowed if declared.
- Empty windows are marked invalid in the mask, never zero-filled.
- Dates are delivered for every step.
- PANGAEA's index rule runs once per task as a comparison, not as a leaderboard setting.

## 3. Splits

**Evidence**
- Random splits overstate accuracy on spatially autocorrelated data:
  - In Ploton et al., random 10-fold CV gave R² 0.53; spatial CV gave 0.14, with blocks set just above the ~150 km autocorrelation range ([Ploton et al. 2020](https://www.nature.com/articles/s41467-020-18321-y)).
  - Rolf et al. recommend blocking, buffering, or varying the train–test distance ([Rolf et al. 2024 §2.3](https://arxiv.org/html/2402.01444)).
- Blocking is not automatically right. Spatial CV that ignores where the model will be used "tended to be overly pessimistic"; the test distances should match the use case ([Linnenbrink et al. 2024, kNNDM](https://gmd.copernicus.org/articles/17/5897/2024/)).
- **PASTIS** folds have "a 1km buffer between images" but interleave within the same Sentinel-2 tiles ([Garnot & Landrieu 2021 §4.1](https://arxiv.org/abs/2107.07933)).
- **Sen1Floods11** uses "a random 60-20-20 split", and "All hand-labeled data from Bolivia is held out for a distinct test set" ([Bonafilia et al. 2020](https://openaccess.thecvf.com/content_CVPRW_2020/papers/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.pdf)).
- **GEO-Bench-2** rebuilt several splits as grids or checkerboards and kept others ([App. 6.1](https://arxiv.org/html/2511.15658v2)).

**Reasoning.** The official split measures interpolation within regions the model has seen. An out-of-region split measures transfer, which is the harder question and the one GFM claims are about. The two answer different questions, so both are reported rather than one replacing the other.

**Decision**
- Keep the official split for comparability.
- Add an out-of-region test split wherever the data allows:
  - Sen1Floods11: Bolivia.
  - PASTIS: hold out whole Sentinel-2 tiles.
- Blocks should be at least the label's autocorrelation range where it can be estimated; otherwise use whole tiles or regions.
- The template's split `kind` gains `buffered-random`.

## 4. Runs and uncertainty

**Evidence**
- **Run counts in EO benchmarks:**
  - GEO-Bench: "at least 10 different seeds"; IQM of normalised scores; "stratified bootstrap, where seeds are sampled with replacement individually for each dataset" ([GEO-Bench §4.1](https://arxiv.org/html/2306.03831)).
  - GEO-Bench-2: 5 repeats and 100 bootstrap resamples.
  - Copernicus-Bench: 3 runs.
  - PANGAEA: a single run.
- **Sources of variance.** Variance comes from "data sampling, parameter initialization and hyperparameter choice"; randomising only the seed gives "only a small improvement". The recommendation is P(A>B) with a 0.75 threshold ([Bouthillier et al. 2021](https://arxiv.org/html/2103.03098)).
- **Aggregation.** Use stratified bootstrap CIs, IQM and performance profiles, not point estimates ([Agarwal et al. 2021](https://arxiv.org/html/2108.13264)).

**Reasoning**
- Three runs cannot separate models whose gap is smaller than run-to-run noise. PANGAEA itself notes that training noise is as large as the gains from tuning.
- Frozen runs are cheap, so 10 is affordable there; fine-tuning is not.
- Varying the label subset per run captures the data-sampling variance that seeds alone miss.
- These runs are also what the aggregation rule needs: spread between models divided by spread across runs.

**Decision**
- 10 runs on the frozen track, 5 on fine-tuning. Each run changes initialisation, data order and label subset.
- **Per task:** mean and a 95% CI, from bootstrapping over runs and over test samples.
- **Across tasks:** IQM of normalised scores with a stratified bootstrap.
- **Pairwise:** P(A>B). Models within 0.75 of each other are reported as tied.
- All per-run results are published.

## 5. Tuning budget

**Evidence**
- GEO-Bench: "maximum budget of 16 trials per task".
- GEO-Bench-2: 16 trials, Optuna TPE, a search space "fixed across all models and datasets" (lr 1e-6 to 1e-3; batch 8, 16 or 32; AdamW with weight decay 0.01; 50 epochs; early stopping).
- PANGAEA: no per-model tuning. Its learning-rate sweep on two datasets did not change the ranking much.
- The better model can depend on the budget, so budgets must be equal and reported ([Dodge et al. 2019](https://arxiv.org/html/1909.03004)).

**Reasoning.** Without an equal budget, a ranking partly measures how much effort each model received. Sixteen trials is the one number two benchmarks agree on, and it also favours models that are robust to tuning.

**Decision**
- Every model gets 16 trials per task and protocol, chosen by TPE, selected on validation only.
- Fine-tuning reuses GEO-Bench-2's search space.
- The frozen track uses lr 1e-5 to 1e-2. This is our choice: it covers PANGAEA's 1e-4 default and its sweep range.
- Every trial is published, so expected validation performance against budget can be plotted.

## 6. Label fractions

**Evidence**
- GEO-Bench uses train ratios from 0.01 to 1. It found rankings change ("ConvNeXt often becomes better than SwinV2 as the training set decreases") and discriminativity rises as data shrinks. All subsets together cost about 1.88× one full run.
- PANGAEA used 10%, 50% and 100%. UNet leads with full labels but loses its lead at 10%, where GFMs pull ahead. This rests on single runs.

**Reasoning.** Low-label performance is the main promise of foundation models, and it is where tasks separate models best. Three fractions spanning two orders of magnitude cover that range at modest cost.

**Decision**
- Fractions of 100%, 10% and 1%, stratified by class or target distribution.
- Subsets are nested and fixed in manifests, one per run. This keeps runs reproducible while still varying data sampling.
- Each subset has a minimum sample count, set per task.

## 7. Image size and resizing

**Evidence**
- Resizing EuroSAT from 64 to 224 px raised ImageNet ResNet-50 kNN accuracy from 0.82 to 0.91. The recommendation is to follow each model's own pretraining preprocessing ([Corley et al.](https://arxiv.org/html/2305.13456)).
- PANGAEA crops larger images and resizes smaller ones, with sliding-window inference.
- Downsampling FiveBillionPixels to match pretraining resolution collapsed scores (CROMA 51.83 → 21.10; PANGAEA Table 9).
- GEO-Bench-2 randomly crops images above 224 px and uses tiled inference.

**Decision**
- Tasks deliver the native grid.
- Adapters bring images to the model's input size by tiling (larger) or bilinear upsampling (smaller), and declare which.
- Predictions are mapped back to the native label grid. Labels are never resampled to fit the model.
- There is no default resampling to match the pretraining resolution.

## 8. Normalisation

**Evidence**
- Corley et al. recommend using the model's own normalisation.
- PANGAEA and GEO-Bench-2 standardise with dataset statistics. GEO-Bench-2 notes this "might penalize some base models expecting a different input distribution".

**Decision.** Keep the v0.1 rule: use the model's shipped statistics when available, otherwise train-split statistics. Record which was used.

## 9. Pinning data and checking it

**Evidence**
- TorchGeo pins its data to a fixed Hugging Face commit and ships per-split sample lists with their own SHA-256.
- Croissant supports a sha256 per file, but its file sets have no per-member hash, so exact sample lists need a separate manifest.
- Hugging Face datasets check only the number of examples per split, not sample ids.
- GEO-Bench keeps partition JSONs, but its README notes mislabelled channel order in two datasets that "is not regenerated".

**Decision**
- Each task ships a manifest per split and per label subset: sample id, file path and SHA-256, at a pinned data revision.
- The manifest's own hash goes into the task.
- A conformance script loads real samples and checks dtype, shape, value range, units and no-data against the template. Declarations alone missed the GEO-Bench channel error.

## 10. Pretraining overlap

**Evidence**
- No GEO-Bench, PANGAEA or GEO-Bench-2 paper measures overlap between pretraining data and benchmark test sets. Nor do the other papers checked, including SSL4EO-S12, Prithvi-EO-2.0 and AlphaEarth. Galileo and TerraMind could not be searched.
- An IBM AGU 2023 abstract raises the issue but reports no effect.
- In natural images, the effect ranges from negligible (CLIP: rarely more than 0.1%) to large (CIFAR duplicates: 9–14% accuracy drop). For EO it is unmeasured.

**Decision**
- Model cards declare their pretraining footprint: datasets, plus tiles or bounding boxes where available.
- For each task, EOArena reports the share of test samples inside that footprint. Results above a threshold (to be set) are flagged, not excluded.
- This is also a publishable measurement in its own right.

## 11. Inputs actually used

**Decision.** A model that reads only Sentinel-2 on a Sentinel-2 plus Sentinel-1 task is solving an easier or different problem. Results are therefore grouped by the set of modalities read, taken from the adapter's `bands_used`, and ranked within each group.

## 12. Template shape

**Decision**
- **Required core:** inputs, target, splits with manifests, metrics, protocols.
- **Optional:** normalisation statistics, orbit, compositing, notes.
- Extra fields are allowed until v1.
- `harness_notes` and `open_questions` move to the docs.
- Protocols reduce to frozen-decoder, fine-tune and diagnostics.

## Still to test

- Whether feeding a final-only layer to every decoder level (decision 1) is fair to Clay and AnySat. This can be checked by running the same rule on a model that has intermediate layers.
- Autocorrelation ranges per task, to size the spatial blocks.
- Three new tasks to stress the template: a classification task, a regression task in physical units (BioMassters), and a non-PANGAEA dataset from a subdomain no benchmark covers.
