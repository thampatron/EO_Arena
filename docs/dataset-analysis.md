# What existing benchmarks measure: dataset-level latent-factor analysis

Analysis of 2026-11-03 on the GeoFM meta-analysis workbook v4, following *GeoFM Benchmark Scoring* (S. Wang, Oct 2026). Object of study: the benchmark **datasets** — what they measure, how much they overlap, and whether independent groups agree on the model differences they show. Model capability vectors are nuisance parameters; nothing here ranks models. Built by `scripts/build_dataset_analysis.py`; numbers in `data/dataset_analysis.json`.

## 1. Evidence base

11,580 extracted results → **3,100** kept. Rules, in order:

| Rule | Rows dropped |
|---|---|
| appendix / supplementary / unclear table | 4,928 |
| GEO-Bench-2 leaderboard snapshot (not a paper) | 533 |
| ablation-study table | 73 |
| registry ablation model | 15 |
| ablation variant axis (non-headline setting) | 452 |
| not a GeoFM (baseline / task architecture / uncategorised) | 1,503 |
| metric not bounded in points (error metrics, R^2) | 749 |
| recitation of an earlier paper's value | 57 |
| metric twin (one metric kept per comparison) | 170 |

Reprinted results (kept only in the earliest source): terrafm reprints copernicus (32 shared cells, 100% identical); anysat reprints pangea (18 shared cells, 83% identical).

Main-text placement of every source table is in `data/table_locations.json` (file-name rule, or checked against the arXiv version); model scope in `data/model_scope.json`.

Imagery comparisons with ≥ 4 GeoFMs: **85 GeoFMs × 218 tasks** (59 datasets, 19 papers), 11.7% of cells observed, median 9 GeoFMs per comparison. 53 of 85 GeoFMs are evaluated by a single paper and only 18 by three or more; 20 of 59 datasets are reported by more than one paper. Everything below is limited by this overlap.

## 2. How many shared capability dimensions? (the note's one-leaderboard test)

Model: y_mt = μ_t + λ_t′θ_m + c_{m,p(t)} + η_mt on the points scale, each task in units of its residual SD; λ_t = dataset + protocol-family + sensor blocks + task part (Eq. 11/12 group ridge); c_{m,p} = paper × model implementation offset.

**Primary criterion — leave one paper out.** Drop every task a paper reports, refit, predict the order of its GeoFMs from what the rest of the literature says about those GeoFMs and about the task's dataset, protocol and sensor. Spearman ρ between predicted and reported order, averaged over held-out tasks:

| K | structured prediction | one ordering for all tasks |
|---|---|---|
| 1 | 0.119 | 0.131 |
| 2 | 0.332 | 0.272 |
| 3 | 0.327 | 0.265 |
| 4 | 0.331 | 0.284 |

Chosen **K = 2** (leave-one-paper-out Spearman of predicted within-task model order; smallest K not credibly worse than the best (paired bootstrap over papers)). Paired differences to the best K: K=1: -0.213 (90% CI -0.358 to -0.085; 201 tasks, 15 papers); K=3: -0.006 (90% CI -0.105 to +0.100; 201 tasks, 15 papers); K=4: -0.001 (90% CI -0.102 to +0.125; 201 tasks, 15 papers).

Gain of the structured prediction over a single ordering: +0.060 (90% CI -0.011 to +0.144; 201 tasks, 15 papers). Split: datasets reported by other papers +0.012 (90% CI -0.041 to +0.077; 110 tasks, 13 papers); datasets reported only by the held-out paper (prediction from protocol and sensor alone) +0.119 (90% CI +0.007 to +0.228; 91 tasks, 10 papers).

**Held-out cells (secondary).** Pairwise ordering accuracy of held-out cells (within-paper information leaks into this criterion through c_{m,p}, so it is not used to choose K):

| spec | paper offset | K=0 | K=1 | K=2 | K=3 | K=4 |
|---|---|---|---|---|---|---|
| free (current) | yes | 0.736 | 0.726 | 0.720 | 0.724 | 0.730 |
| dataset + task | yes | – | 0.740 | 0.744 | 0.742 | 0.740 |
| dataset + protocol + sensor + task | yes | – | 0.739 | 0.750 | 0.738 | 0.742 |
| dataset + protocol + sensor + task | no | – | 0.706 | 0.747 | 0.747 | 0.737 |

**Can K be recovered on this mask?** Simulation with the real missingness pattern, a dataset-shared loading (60% of its variance), and paper × model implementation effects (0.5 noise SD):

| K true | SNR | K selected | dataset-similarity recovery (all / datasets in ≥ 2 papers) |
|---|---|---|---|
| 1 | 0.5 | 1 | – |
| 1 | 1.0 | 1 | – |
| 1 | 2.0 | 1 | – |
| 2 | 0.5 | 1 | 0.15 / 0.33 |
| 2 | 1.0 | 2 | 0.42 / 0.69 |
| 2 | 2.0 | 2 | 0.47 / 0.68 |
| 3 | 0.5 | 0 | 0.28 / 0.49 |
| 3 | 1.0 | 2 | 0.31 / 0.47 |
| 3 | 2.0 | 3 | 0.36 / 0.55 |

With the paper × model offset, selection never over-shoots K; at low signal it under-shoots. Without the offset (earlier run) it over-selected (K_true 1 → 2, 2 → 3): implementation effects masquerade as capabilities, which is why the current site's K = 3 should not be read as three capabilities.

## 3. What organises the datasets

Share of variance in dataset loadings explained by each label (datasets reported by ≥ 2 papers; permutation null shuffles labels across datasets):

| label | R² | null mean | p |
|---|---|---|---|
| domain | 0.14 | 0.21 | 0.760 |
| subdomain | 0.51 | 0.53 | 0.547 |
| task_type | 0.01 | 0.11 | 0.970 |
| sensor | 0.74 | 0.42 | 0.002 |

Dataset-to-dataset similarity is **not published**: simulated recovery of the similarity geometry on this mask stays below 0.7 (geometry_recoverable = False). The evidence supports how many dimensions there are and what label aligns with them, not which specific datasets are near-duplicates.

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

Reported separation = model-count-weighted SD of reported scores within the dataset's comparisons, over each paper's own GeoFM set (note Eq. 10: not quality). Shared signal = |λ_d|², shared-capability variance in units of residual variance (residual = stable task-specific interaction + evaluation noise, not separable from single scores). Info share = Shapley share of V(A) = log det(I + Σ λ_dλ_d′) among these datasets (Eq. 8; each dataset once). LOPO ρ = mean leave-one-paper-out Spearman of its tasks (structured / one ordering).

| dataset | domain | papers | tasks | GeoFMs/task | reported separation (pts) | shared signal | info share (± MC SE) | LOPO ρ |
|---|---|---|---|---|---|---|---|---|
| RESISC45 | Terrestrial ecosystems | 2 | 3 | 6 | 14.2 | 8.02 | 0.170 (± 0.003) | -0.35 / -0.05 |
| Chesapeake land cover | Terrestrial ecosystems | 2 | 2 | 8 | 6.5 | 6.48 | 0.128 (± 0.003) | 0.55 / 0.34 |
| Sen1Floods11 | Inland water | 3 | 6 | 11 | 5.8 | 3.28 | 0.085 (± 0.002) | 0.57 / 0.54 |
| So2Sat LCZ42 (LCZ-S2) | Human systems | 6 | 7 | 11 | 7.2 | 3.82 | 0.083 (± 0.002) | 0.30 / 0.35 |
| fMoW | Human systems | 4 | 11 | 5 | 5.2 | 4.43 | 0.078 (± 0.002) | 0.72 / 0.65 |
| NeonTreeEvaluation | Terrestrial ecosystems | 2 | 2 | 8 | 4.0 | 4.55 | 0.077 (± 0.002) | 0.34 / 0.58 |
| Cashew plantation | Agriculture | 4 | 6 | 12 | 10.3 | 1.93 | 0.045 (± 0.002) | 0.29 / 0.20 |
| PASTIS / PASTIS-R | Agriculture | 4 | 14 | 11 | 8.1 | 1.43 | 0.041 (± 0.001) | 0.21 / 0.19 |
| MADOS | Oceans and coasts | 3 | 6 | 12 | 7.3 | 1.73 | 0.036 (± 0.001) | 0.43 / 0.43 |
| BigEarthNet v1 / v2 (reBEN) | Terrestrial ecosystems | 8 | 15 | 8 | 3.6 | 1.17 | 0.035 (± 0.001) | 0.35 / 0.17 |
| EuroSAT | Terrestrial ecosystems | 6 | 12 | 8 | 4.5 | 1.20 | 0.032 (± 0.001) | 0.44 / 0.45 |
| PV4GER | Human systems | 2 | 5 | 7 | 2.9 | 1.03 | 0.031 (± 0.001) | 0.20 / 0.63 |
| BreizhCrops | Agriculture | 2 | 2 | 14 | 4.6 | 0.62 | 0.026 (± 0.001) | 0.43 / 0.45 |
| HLS Burn Scars | Terrestrial ecosystems | 3 | 5 | 8 | 3.2 | 0.78 | 0.025 (± 0.001) | 0.67 / 0.41 |
| NZ cattle | Agriculture | 2 | 3 | 7 | 2.5 | 1.08 | 0.025 (± 0.001) | 0.67 / 0.57 |
| CropHarvest | Agriculture | 3 | 10 | 15 | 4.5 | 0.48 | 0.023 (± 0.001) | 0.26 / 0.25 |
| DFC2020 | Terrestrial ecosystems | 2 | 3 | 4 | 2.0 | 0.64 | 0.019 (± 0.001) | -0.33 / -0.40 |
| ForestNet | Terrestrial ecosystems | 3 | 4 | 9 | 3.7 | 0.70 | 0.019 (± 0.001) | 0.53 / 0.38 |
| South Africa crop type | Agriculture | 4 | 5 | 14 | 3.7 | 0.69 | 0.018 (± 0.001) | 0.06 / 0.23 |
| Brick kilns | Human systems | 4 | 5 | 14 | 2.0 | 0.21 | 0.005 (± 0.000) | 0.09 / 0.04 |

39 further datasets are reported by a single paper; their loadings cannot be separated from that paper's GeoFM selection and implementation, so no dataset-level quantity is reported for them.

Shared signal vs GeoFMs per comparison: Spearman -0.217 (the ridge shrinks small comparisons; read signal alongside GeoFMs/task).

## 6. Limits and open decisions

- **Main-text rule loses some results.** Several papers' main-text tables are condensed versions of appendix tables that the workbook extracted instead (e.g. Galileo, SatCLIP, Prithvi-EO-2.0 GEO-Bench results). Those main-text numbers are currently lost. Decide whether to re-extract the main tables or keep appendix rows that a main table reprints.
- **GEO-Bench-2 leaderboard** is excluded as not a paper's main text; `--include-leaderboard` adds it.
- Uncategorised models were scoped by hand (`data/model_scope.json`); `vanilla_mae` and `convmae` are excluded because the same id is EO-pretrained in some papers and ImageNet-pretrained in others.
- Geography and time blocks of Eq. 11 are not fitted: the workbook has no geography/time metadata, and the evaluation design is not crossed enough to separate them from dataset.
- K is a lower bound at the signal levels seen here (simulation under-shoots at SNR ≤ 1).
