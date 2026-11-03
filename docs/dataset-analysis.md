# What existing benchmarks measure: dataset-level latent-factor analysis

Analysis of 2026-11-03 on the GeoFM meta-analysis workbook v4, following *GeoFM Benchmark Scoring* (S. Wang, Oct 2026). Object of study: the benchmark **datasets** — what they measure, how much they overlap, and whether independent groups agree on the model differences they show. Model capability vectors are nuisance parameters; nothing here ranks models. Built by `scripts/build_dataset_analysis.py`; numbers in `data/dataset_analysis.json`.

## Findings

1. **One leaderboard does not describe GeoFM performance.** Predicting how GeoFMs order on an unseen paper's tasks from all other papers, a one-factor model does no better than a naive leaderboard (-0.09 (90% CI -0.23 to +0.05)); the best multi-factor model (K = 4) beats it by Δρ = +0.12 (90% CI +0.07 to +0.18). Out-of-paper accuracy rises with K (ρ = 0.09, 0.21, 0.27, 0.30 for K = 1, 2, 3, 4); the smallest K not credibly worse than the best is 2, and on this mask that rule is conservative (in simulation it selects K = 1 for K_true = 1, K = 1 for K_true = 2, K = 1 for K_true = 3). So there are at least two shared dimensions and plausibly more; the exact number is not identifiable. Even the best model predicts little of each paper's ordering (ρ ≈ 0.30).
2. **What a dataset measures does not carry over across papers.** For datasets that other papers also report, adding the dataset's own loading changes out-of-paper accuracy by -0.06 (90% CI -0.13 to +0.01). Dataset-to-dataset similarity is not recoverable on this evidence and is not reported.
3. **No metadata label credibly organises the datasets.** Domain, subdomain, task type and sensor all fail to explain dataset loadings beyond chance after correcting for the four labels tested.
4. **No dataset's reliability can be judged from the main-text literature.** After removing reprints, no dataset version × protocol has ≥ 5 GeoFMs evaluated by two independent papers; σ²_t, EDI and the Eq. 6 score need repeated standardised runs (the replicate design).

## 1. Evidence base

11,580 extracted results → **3,433** kept. Rules, in order:

| Rule | Rows dropped |
|---|---|
| appendix / supplementary / unclear table | 4,928 |
| GEO-Bench-2 leaderboard snapshot (not a paper) | 533 |
| ablation-study table | 73 |
| registry ablation model | 15 |
| ablation variant axis (non-headline setting) | 452 |
| not a GeoFM (baseline / task architecture / uncategorised) | 1,118 |
| metric not bounded in points (error metrics, R^2) | 792 |
| recitation of an earlier paper's value | 66 |
| metric twin (one metric kept per comparison) | 170 |

Reprinted results (kept only in the earliest source): anysat reprints pangea (22 shared cells, 77% identical); terrafm reprints copernicus (32 shared cells, 100% identical).

Main-text placement of every source table is in `data/table_locations.json` (file-name rule, or checked against the arXiv version); model scope in `data/model_scope.json`.

Imagery comparisons with ≥ 4 GeoFMs: **93 GeoFMs × 228 tasks** (59 datasets, 20 papers), 11.9% of cells observed, median 10 GeoFMs per comparison. 57 of 93 GeoFMs are evaluated by a single paper and only 22 by three or more; 20 of 59 datasets are reported by more than one paper. Everything below is limited by this overlap.

## 2. How many shared capability dimensions? (the note's one-leaderboard test)

Model: y_mt = μ_t + λ_t′θ_m + c_{m,p(t)} + η_mt on the points scale, each task in units of its residual SD; λ_t = dataset + protocol-family + sensor blocks + task part (Eq. 11/12 group ridge); c_{m,p} = paper × model implementation offset.

**Primary criterion — leave one paper out.** Drop every task a paper reports, refit, predict the order of its GeoFMs from what the rest of the literature says about those GeoFMs and about the task's dataset, protocol and sensor. Spearman ρ between predicted and reported order, averaged over held-out tasks:

| K | structured prediction | its own one-ordering | naive leaderboard (fixed) |
|---|---|---|---|
| 1 | 0.091 | -0.066 | 0.178 |
| 2 | 0.214 | 0.223 | 0.178 |
| 3 | 0.268 | 0.235 | 0.178 |
| 4 | 0.298 | 0.180 | 0.178 |

The naive leaderboard orders the held-out paper's GeoFMs by their mean within-comparison z-score in all other papers: a single ranking that does not depend on K, so it is the fair one-leaderboard baseline.

Selection rule: the smallest K whose leave-one-paper-out accuracy is not credibly below the best K (paired bootstrap over papers) gives **K = 2**; the dataset outputs in §5 use it. Paired differences to the best K: K=1: -0.206 (90% CI -0.328 to -0.101; 213 tasks, 16 papers); K=2: -0.083 (90% CI -0.201 to +0.005; 213 tasks, 16 papers); K=3: -0.030 (90% CI -0.077 to +0.008; 213 tasks, 16 papers).

**One leaderboard vs more dimensions.** Structured prediction minus the naive leaderboard: K = 1 -0.087 (90% CI -0.229 to +0.047; 213 tasks, 16 papers); K = 2 +0.037 (90% CI -0.083 to +0.118; 213 tasks, 16 papers); K = 4 (best) +0.120 (90% CI +0.067 to +0.181; 213 tasks, 16 papers).

**Does knowing the dataset help?** Gain over the K-factor model's own single ordering: datasets also reported by other papers -0.063 (90% CI -0.132 to +0.014; 122 tasks, 14 papers); datasets reported only by the held-out paper (prediction from protocol and sensor) +0.064 (90% CI -0.011 to +0.138; 91 tasks, 10 papers). What a dataset 'measures', as estimated from other papers, does not carry over to a new paper's evaluation of it.

**Held-out cells (secondary).** Pairwise ordering accuracy of held-out cells (within-paper information leaks into this criterion through c_{m,p}, so it is not used to choose K):

| spec | paper offset | K=0 | K=1 | K=2 | K=3 | K=4 |
|---|---|---|---|---|---|---|
| free (current) | yes | 0.710 | 0.746 | 0.749 | 0.740 | 0.723 |
| dataset + task | yes | – | 0.746 | 0.745 | 0.741 | 0.740 |
| dataset + protocol + sensor + task | yes | – | 0.746 | 0.748 | 0.745 | 0.734 |
| dataset + protocol + sensor + task | no | – | 0.696 | 0.723 | 0.740 | 0.737 |

**Can K be recovered on this mask?** Simulation with the real missingness pattern, a dataset-shared loading (60% of its variance), and paper × model implementation effects (0.5 noise SD). Selection by the same leave-one-paper-out rule as the real data (SNR 1):

| K true | K selected (LOPO) | LOPO ρ by K |
|---|---|---|
| 1 | 1 | K1: 0.284, K2: 0.172, K3: 0.144, K4: 0.121 |
| 2 | 1 | K1: 0.137, K2: 0.112, K3: 0.116, K4: 0.079 |
| 3 | 1 | K1: 0.080, K2: 0.044, K3: 0.087, K4: 0.101 |

Held-out-cell selection and geometry recovery over three signal levels:

| K true | SNR | K selected (held-out cells) | dataset-similarity recovery (all / datasets in ≥ 2 papers) |
|---|---|---|---|
| 1 | 0.5 | 1 | – |
| 1 | 1.0 | 1 | – |
| 1 | 2.0 | 1 | – |
| 2 | 0.5 | 2 | 0.17 / 0.28 |
| 2 | 1.0 | 1 | 0.18 / 0.17 |
| 2 | 2.0 | 2 | 0.53 / 0.37 |
| 3 | 0.5 | 0 | 0.14 / 0.26 |
| 3 | 1.0 | 0 | 0.25 / 0.31 |
| 3 | 2.0 | 3 | 0.36 / 0.74 |

Under the same leave-one-paper-out rule the simulation selects K = 1 even when K_true is 2 or 3: with this little cross-paper overlap, extra dimensions only pay off out of paper when they are strong. That the real data keeps improving up to K = 4 is therefore evidence of more than one shared dimension; K = 2 is a floor, not an estimate. In an earlier run without the paper × model offset, held-out selection over-selected (K_true 1 → 2, 2 → 3): implementation effects can masquerade as capabilities, so the current site's K = 3 may partly reflect implementation effects and its broader model scope.

## 3. What organises the datasets

Share of variance in dataset loadings explained by each label, over datasets reported by ≥ 2 papers (blank labels treated as missing; permutation null shuffles labels across datasets; p adjusted for the 4 labels tested). 'Direction only' normalises each loading to unit length: it asks what a dataset measures, not how strongly it separates GeoFMs.

| label | R² (full) | null | p (Bonf.) | R² (direction only) | null | p (Bonf.) | datasets |
|---|---|---|---|---|---|---|---|
| domain | 0.39 | 0.21 | 0.27 | 0.29 | 0.21 | 0.51 | 20 |
| subdomain | 0.62 | 0.52 | 0.98 | 0.66 | 0.53 | 0.26 | 20 |
| task_type | 0.07 | 0.10 | 1.00 | 0.24 | 0.10 | 0.08 | 20 |
| sensor | 0.50 | 0.35 | 0.61 | 0.45 | 0.35 | 0.28 | 18 |

Read these as weak evidence at best: about 20 datasets, many-level labels, and loadings that do not transfer across papers (§2).

Dataset-to-dataset similarity is **not published**: simulated recovery of the similarity geometry on this mask stays below 0.7 (geometry_recoverable = False). The evidence supports a minimum number of dimensions, not which specific datasets are near-duplicates.

## 4. Do independent groups agree on what a dataset shows?

Grouping by exact benchmark version × protocol × training fraction × metric × setting, after removing reprints: 15 groups are reported by ≥ 2 papers; 6 share ≥ 3 GeoFMs and 0 share ≥ 5. Cross-paper reproducibility (additive paper + model fit, ≥ 5 shared GeoFMs, ≥ 5 residual df) is estimable for **0** groups. Main-text literature does not contain the independent re-evaluations needed to judge any dataset's reliability; the note's σ²_t (and with it EDI and the Eq. 6 score) requires repeated standardised runs.

| group | papers | GeoFMs in ≥ 2 papers |
|---|---|---|
| Cashew plantation · geobench_m_cashew_s2 · LP · unspecified · miou | 2 | 4 |
| South Africa crop type · geobench_m_sacrop_s2 · LP · unspecified · miou | 2 | 4 |
| Chesapeake land cover · m_chesapeake · frozen_dec · unspecified · miou | 2 | 3 |
| NeonTreeEvaluation · geobench_m_neontree · frozen_dec · unspecified · miou | 2 | 3 |
| PV4GER · geobench_m_pv4ger_seg_rgb · frozen_dec · unspecified · miou | 2 | 3 |
| NZ cattle · geobench_m_nzcattle_rgb · frozen_dec · unspecified · miou | 2 | 3 |
| Brick kilns · geobench_m_brick_kiln · LP · unspecified · acc_top1 | 2 | 1 |
| PV4GER · geobench_m_pv4ger · LP · unspecified · acc_top1 | 2 | 1 |
| ForestNet · geobench_m_forestnet_l8 · LP · unspecified · acc_top1 | 2 | 1 |
| EuroSAT · geobench_m_eurosat · LP · unspecified · acc_top1 | 2 | 1 |

## 5. Datasets with independent evidence (≥ 2 papers)

Descriptive evidence only. Reported separation = model-count-weighted SD of reported scores within the dataset's comparisons, over each paper's own GeoFM set (note Eq. 10: reported separation, not quality or discriminative power). LOPO ρ = mean leave-one-paper-out Spearman over the dataset's tasks (structured / naive leaderboard), with the number of tasks and median GeoFMs behind it. In-sample loading summaries (shared signal, Eq. 8 information share) are kept in the JSON but not shown: they do not transfer across papers (§2) and are driven by single small comparisons (e.g. RESISC45 rests on one 4-GeoFM comparison).

| dataset | domain | papers | comparisons | smallest comparison | reported separation (pts) | LOPO ρ: structured / leaderboard (tasks, GeoFMs) |
|---|---|---|---|---|---|---|
| BigEarthNet v1 / v2 (reBEN) | Terrestrial ecosystems | 9 | 19 | 4 | 3.2 | 0.20 / 0.21 (15, 6) |
| EuroSAT | Terrestrial ecosystems | 7 | 14 | 4 | 4.3 | 0.32 / 0.21 (14, 6) |
| So2Sat LCZ42 (LCZ-S2) | Human systems | 7 | 11 | 4 | 6.3 | -0.03 / 0.04 (11, 4) |
| PASTIS / PASTIS-R | Agriculture | 4 | 14 | 5 | 8.1 | -0.04 / -0.05 (14, 8) |
| fMoW | Human systems | 4 | 11 | 4 | 5.0 | 0.66 / 0.36 (6, 6) |
| Cashew plantation | Agriculture | 4 | 6 | 8 | 10.2 | 0.10 / 0.57 (6, 8) |
| Brick kilns | Human systems | 4 | 5 | 8 | 2.0 | 0.05 / 0.24 (5, 8) |
| South Africa crop type | Agriculture | 4 | 5 | 8 | 3.7 | -0.14 / 0.45 (5, 8) |
| CropHarvest | Agriculture | 3 | 10 | 4 | 4.5 | 0.12 / 0.13 (9, 13) |
| MADOS | Oceans and coasts | 3 | 6 | 10 | 7.3 | 0.47 / 0.45 (6, 11) |
| Sen1Floods11 | Inland water | 3 | 6 | 5 | 5.6 | 0.25 / 0.09 (5, 11) |
| HLS Burn Scars | Terrestrial ecosystems | 3 | 5 | 5 | 2.9 | 0.26 / 0.01 (4, 11) |
| ForestNet | Terrestrial ecosystems | 3 | 4 | 5 | 4.1 | 0.49 / 0.51 (3, 6) |
| PV4GER | Human systems | 2 | 5 | 6 | 3.1 | 0.35 / 0.24 (5, 6) |
| DFC2020 | Terrestrial ecosystems | 2 | 3 | 4 | 4.7 | -0.32 / -0.18 (3, 4) |
| NZ cattle | Agriculture | 2 | 3 | 8 | 3.5 | -0.13 / 0.07 (3, 8) |
| RESISC45 | Terrestrial ecosystems | 2 | 3 | 4 | 14.2 | -0.80 / -0.50 (2, 4) |
| BreizhCrops | Agriculture | 2 | 2 | 5 | 10.0 | 0.54 / 0.39 (2, 10) |
| Chesapeake land cover | Terrestrial ecosystems | 2 | 2 | 8 | 6.5 | 0.14 / 0.57 (2, 6) |
| NeonTreeEvaluation | Terrestrial ecosystems | 2 | 2 | 8 | 3.8 | 0.24 / 0.33 (2, 6) |

39 further datasets are reported by a single paper; their loadings cannot be separated from that paper's GeoFM selection and implementation, so no dataset-level quantity is reported for them.

## 6. Limits and open decisions

- **Main-text rule loses some results.** Several papers' main-text tables are condensed versions of appendix tables that the workbook extracted instead (e.g. Galileo, SatCLIP, Prithvi-EO-2.0 GEO-Bench results). Those main-text numbers are currently lost. Decide whether to re-extract the main tables or keep appendix rows that a main table reprints.
- **GEO-Bench-2 leaderboard** is excluded as not a paper's main text; `--include-leaderboard` adds it.
- Uncategorised models were scoped by hand (`data/model_scope.json`); `vanilla_mae` and `convmae` are excluded because the same id is EO-pretrained in some papers and ImageNet-pretrained in others.
- Geography and time blocks of Eq. 11 are not fitted: the workbook has no geography/time metadata, and the evaluation design is not crossed enough to separate them from dataset.
- The number of shared dimensions is not identifiable on this evidence (≥ 2; out-of-paper accuracy still rising at K = 4).
- `data/model_profiles.json` (existing build) still publishes θ as a nuisance output and `benchmarks.html` is still titled 'Benchmark ranking'; both predate this analysis.
