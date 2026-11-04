# What existing benchmarks measure: dataset-level latent-factor analysis (v2)

Analysis of 2026-11-04 on the GeoFM meta-analysis workbook v4, following *GeoFM Benchmark Scoring* (S. Wang, Oct 2026). Object of study: the benchmark **datasets** — what they measure, how much they overlap, whether independent groups agree on the model differences they show, and how reliably they separate GeoFMs where seed noise is reported. Model capability vectors are nuisance parameters; nothing here ranks models. Every analysis decision, with its justification and a switch to undo it, is in [`analysis-decisions.md`](analysis-decisions.md). Built by `scripts/build_dataset_analysis.py`; numbers in `data/dataset_analysis.json`.

## Findings

1. **GeoFM orderings are far more consistent within a paper than across papers.** At K = 4, a paper's own other comparisons predict a GeoFM's held-out position with 71% pairwise accuracy; the rest of the literature predicts a new paper's orderings with 60% (Spearman ρ = 0.25). Much of a GeoFM's reported advantage is specific to the paper — its suite of tasks, protocol, model set or implementation. In the two cases where independent groups ran the same dataset and protocol (finding 6) they agree well, which points to task suite and protocol rather than implementation; two cases are too few to decide.
2. **Out of paper, no multi-factor model beats a single ranking.** A naive leaderboard (each GeoFM's mean within-comparison z-score in the other sources) predicts a new source's orderings with ρ = 0.23; the best structured model (K = 4, selected among 12 configurations) differs by +0.02 (90% CI -0.13 to +0.15). Extra dimensions fit within papers but do not transfer across them. Simulation on this evidence: the selection rule picks K = 1 when the truth is 1, K = 1 when the truth is 2, K = 1 when the truth is 3, so the test cannot detect moderate structure: absence of evidence, not evidence of a single dimension. (A one-factor structured model scores below the naive leaderboard, -0.18 (90% CI -0.33 to -0.05), because it predicts each held-out task's loading from dataset, protocol and sensor blocks whose sign can be wrong; that is a weakness of the predictor, not evidence against a single ranking.)
3. **What a dataset measures does not measurably carry over across papers.** For datasets other sources also report, the dataset-structured prediction differs from the model's own single ordering by +0.02 (90% CI -0.14 to +0.16); for datasets seen only in the held-out source (protocol and sensor carry the prediction) by -0.01 (90% CI -0.15 to +0.11). Dataset-to-dataset similarity is therefore not reported: simulation shows it would be recoverable if datasets measured distinct things this strongly, but the real data shows no such transfer.
4. **Metadata labels do not credibly organise the datasets.** Domain, subdomain, task type and sensor all fail after correction for the four labels tested.
5. **Seed-noise reliability (note Eq. 6) is now measurable for 68 dataset × protocol pairs** (203 comparisons with seed SDs for ≥ 3 GeoFMs): 58 have ≥ 80% of their model spread repeatable under re-seeding, 3 have < 50%. This is reliability within one implementation, not agreement across groups.
6. **Independent groups rarely evaluate the same GeoFMs on the same dataset.** With appendix tables and the GEO-Bench-2 leaderboard, cross-source reproducibility is estimable for 0 strict and 2 loose dataset groups. Where it is estimable, independent sources agree well: BioMassters (frozen, 2 sources, 6 GeoFMs): Kendall τ 1.00, agreement 0.99; PASTIS / PASTIS-R (frozen, 4 sources, 8 GeoFMs): Kendall τ 0.73, agreement 0.89. Two groups cannot characterise the literature: standardised re-evaluation of the same GeoFMs by different groups is the missing evidence.

## 1. Evidence base

11,580 extracted results → **7,333** kept (configuration: main_text_only=False, leaderboard=True, regression=True, offset=select, ridge=3.0, ridge_paper_offset=3.0). Rules in order:

| Rule | Rows dropped |
|---|---|
| table placement unclear | 72 |
| ablation status of table not checked | 0 |
| ablation-study table | 140 |
| registry ablation model | 50 |
| ablation variant axis (non-headline setting) | 524 |
| not a GeoFM (baseline / task architecture / uncategorised) | 2,055 |
| regression value outside the metric's domain | 0 |
| metric not on a bounded-points or log-error scale (skill scores etc.) | 226 |
| within-paper duplicate (appendix repeats a main-text value) | 83 |
| recitation of an earlier paper's value | 151 |
| metric twin (one metric kept per comparison) | 946 |

Reprinting papers (kept only in the earliest source): terrafm ← copernicus (32 cells, 100% identical); terrafm ← galileo (66 cells, 95% identical).

Imagery comparisons with ≥ 4 GeoFMs: **105 GeoFMs × 563 tasks** (95 datasets, 28 sources: papers plus the GEO-Bench-2 leaderboard), 9.6% of cells observed, median 9 GeoFMs per comparison; 256 comparisons come from appendix tables, 32 from the leaderboard, 64 are regression tasks. 56 of 105 GeoFMs appear in a single source, 32 in three or more; 29 of 95 datasets are reported by more than one source; 9 sources cover a single domain.

## 2. Within-paper vs out-of-paper consistency

Held-out cells (a random fifth of results hidden and predicted from everything else, including the same paper's other comparisons) vs leave-one-paper-out (all of a source's comparisons hidden). Pairwise ordering accuracy, 50% = chance:

| | within paper (held-out cells) | out of paper (leave-one-paper-out) |
|---|---|---|
| K = 1 | 65.2% | 51.5% |
| K = 4 | 71.1% | 59.5% |

## 3. How many shared dimensions? (the note's one-leaderboard test)

Model: y_mt = μ_t + λ_t′θ_m + c_{m,p(t)} + η_mt, each task in units of its residual SD (pooled prior within metric family); λ_t = dataset + protocol-family + sensor blocks + task part (Eq. 11/12 group ridge); c = paper × model implementation offset. Leave-one-paper-out Spearman ρ of predicted vs reported within-task order (naive leaderboard = mean within-comparison z-score in all other sources, a K-independent single ranking):

| offset | K=1 | K=2 | K=3 | K=4 | naive leaderboard |
|---|---|---|---|---|---|
| all | 0.013 | 0.082 | 0.197 | 0.151 | 0.227 |
| multi_domain | 0.022 | 0.096 | 0.199 | 0.135 | 0.227 |
| none (chosen) | 0.043 | 0.224 | 0.206 | 0.248 | 0.227 |

Offset choice (D8): all (K=3) minus chosen (K=4): -0.05 (90% CI -0.16 to +0.07); multi_domain (K=3) minus chosen (K=4): -0.05 (90% CI -0.17 to +0.09).

K (D9): best K = 4; chosen (smallest not credibly worse) K = 2. Paired differences to the best: K=1: -0.20 (90% CI -0.33 to -0.10); K=2: -0.02 (90% CI -0.14 to +0.11); K=3: -0.04 (90% CI -0.11 to +0.03).

Against a single ranking (naive leaderboard, ρ = 0.227): K = 1 -0.18 (90% CI -0.33 to -0.05); K = 2 (chosen) -0.00 (90% CI -0.07 to +0.07); K = 4 (best, selected — optimistic) +0.02 (90% CI -0.13 to +0.15).

**What the offset costs (simulation on the real mask, true K = 2 with dataset-shared loadings, SNR 1).** Recovery = correlation of true and estimated dataset-similarity structure among datasets in ≥ 2 sources; dataset gain = how much the dataset-structured prediction beats the model's own single ordering out of paper.

| implementation effects | offset | LOPO ρ | dataset gain (seen datasets) | geometry recovery |
|---|---|---|---|---|
| 0.0 SD | all | 0.226 | +0.214 | 0.64 |
| 0.0 SD | multi_domain | 0.222 | +0.221 | 0.63 |
| 0.0 SD | none | 0.198 | +0.167 | 0.64 |
| 0.5 SD | all | 0.303 | +0.310 | 0.82 |
| 0.5 SD | multi_domain | 0.298 | +0.309 | 0.82 |
| 0.5 SD | none | 0.296 | +0.285 | 0.77 |

**Can leave-one-paper-out recover K?** (chosen offset, SNR 1)

| K true | K chosen by the rule | best K | LOPO ρ by K |
|---|---|---|---|
| 1 | 1 | 1 | K1: 0.115, K2: 0.093, K3: 0.079, K4: 0.045 |
| 2 | 1 | 1 | K1: 0.126, K2: 0.090, K3: 0.091, K4: 0.082 |
| 3 | 1 | 4 | K1: 0.159, K2: 0.127, K3: 0.177, K4: 0.216 |

## 4. Do datasets measure different things?

Out of paper, for datasets also reported by other sources: +0.02 (90% CI -0.14 to +0.16). Datasets seen only in the held-out source: -0.01 (90% CI -0.15 to +0.11).

Variance in dataset loadings explained by each label, over datasets reported by ≥ 2 sources (blank labels missing; permutation null over datasets; Bonferroni over 4 labels). 'Direction only' asks what a dataset measures, not how strongly it separates GeoFMs:

| label | R² (full) | null | p (Bonf.) | R² (direction) | null | p (Bonf.) | datasets |
|---|---|---|---|---|---|---|---|
| domain | 0.29 | 0.21 | 0.77 | 0.31 | 0.22 | 0.30 | 29 |
| subdomain | 0.47 | 0.46 | 1.00 | 0.52 | 0.46 | 0.87 | 29 |
| task_type | 0.07 | 0.11 | 1.00 | 0.12 | 0.11 | 1.00 | 29 |
| sensor | 0.40 | 0.42 | 1.00 | 0.50 | 0.42 | 0.60 | 27 |

Dataset-to-dataset similarity is **not published** (D13): simulated recovery on this mask would allow it (median 0.704), but dataset loadings do not credibly transfer across papers on the real data, so the estimated similarities would describe single papers, not datasets.

## 5. Seed-noise reliability where it is reported (note Eq. 3–6)

Comparisons where ≥ 3 GeoFMs report a seed SD: 203. σ = median seed SD of one evaluation (points, or log-error ×100 for regression); spread = SD of the reported scores; score = τ²/(τ²+σ²) with τ² = spread² − σ²/n_reps: the share of the comparison's model differences that survives re-seeding, for its models and implementation. 'If single runs' treats every reported value as one run (most conservative). 26% of comparisons do not state how many runs a reported mean averages; 3 is assumed.

| dataset | protocol | comparisons | sources | GeoFMs | σ | spread | score (range) | lowest 5% bound | if single runs |
|---|---|---|---|---|---|---|---|---|---|
| BigEarthNet v1 / v2 (reBEN) | fine-tuned | 7 | 4 | 9 | 0.47 | 3.55 | 0.88 (0.54–1.00) | 0.21 | 0.83 |
| So2Sat LCZ42 (LCZ-S2) | fine-tuned | 5 | 3 | 9 | 1.54 | 3.66 | 0.82 (0.57–0.97) | 0.25 | 0.76 |
| BigEarthNet v1 / v2 (reBEN) | frozen | 6 | 3 | 8 | 0.61 | 11.35 | 0.91 (0.45–1.00) | 0.03 | 0.84 |
| Sen1Floods11 | fine-tuned | 6 | 3 | 8 | 1.89 | 11.82 | 0.94 (0.87–1.00) | 0.03 | 0.94 |
| EuroSAT | fine-tuned | 6 | 3 | 8 | 1.20 | 11.98 | 0.96 (0.90–1.00) | 0.66 | 0.96 |
| EuroSAT | frozen | 7 | 3 | 8 | 0.53 | 12.38 | 0.99 (0.96–1.00) | 0.40 | 0.99 |
| CropHarvest | frozen | 2 | 2 | 4 | 1.19 | 3.82 | 0.50 (0.00–0.99) | 0.00 | 0.50 |
| Brick kilns | fine-tuned | 4 | 2 | 9 | 0.29 | 0.77 | 0.72 (0.29–1.00) | 0.04 | 0.63 |
| Cashew plantation | fine-tuned | 4 | 2 | 9 | 3.94 | 7.88 | 0.76 (0.41–0.92) | 0.22 | 0.64 |
| ForestNet | fine-tuned | 2 | 2 | 11 | 1.36 | 2.75 | 0.79 (0.73–0.84) | 0.28 | 0.73 |
| Fields of The World | fine-tuned | 9 | 2 | 8 | 0.46 | 1.17 | 0.83 (0.38–0.99) | 0.00 | 0.78 |
| South Africa crop type | fine-tuned | 4 | 2 | 9 | 0.90 | 3.30 | 0.85 (0.69–0.99) | 0.00 | 0.81 |
| TreeSatAI | frozen | 2 | 2 | 6 | 1.05 | 2.86 | 0.86 (0.65–0.97) | 0.00 | 0.82 |
| Fields of The World | frozen | 9 | 2 | 8 | 0.35 | 2.03 | 0.93 (0.78–0.98) | 0.40 | 0.91 |
| CloudSEN12 (Cloud-S2) | frozen | 2 | 2 | 6 | 0.36 | 1.40 | 0.93 (0.92–0.96) | 0.40 | 0.93 |
| HLS Burn Scars | fine-tuned | 2 | 2 | 8 | 0.70 | 3.80 | 0.93 (0.82–0.99) | 0.22 | 0.92 |
| PASTIS / PASTIS-R | frozen | 2 | 2 | 6 | 1.46 | 6.08 | 0.96 (0.91–0.98) | 0.04 | 0.95 |
| Sen1Floods11 | frozen | 5 | 2 | 9 | 2.05 | 12.71 | 0.96 (0.88–1.00) | 0.33 | 0.96 |
| Kuro Siwo (Flood-S1) | frozen | 2 | 2 | 6 | 0.98 | 6.15 | 0.98 (0.97–0.98) | 0.50 | 0.98 |
| NZ cattle | fine-tuned | 2 | 2 | 9 | 0.43 | 3.06 | 0.98 (0.96–0.99) | 0.75 | 0.98 |
| So2Sat LCZ42 (LCZ-S2) | frozen | 4 | 2 | 9 | 0.73 | 9.33 | 0.99 (0.98–1.00) | 0.57 | 0.99 |
| BioMassters | frozen | 1 | 1 | 4 | 6.35 | 1.86 | 0.00 (0.00–0.00) | 0.00 | 0.00 |
| DynamicEarthNet | frozen | 1 | 1 | 8 | 4.26 | 3.54 | 0.33 (0.33–0.33) | 0.00 | 0.00 |
| DynamicEarthNet | fine-tuned | 1 | 1 | 11 | 2.58 | 3.92 | 0.68 (0.68–0.68) | 0.36 | 0.56 |
| CaFFe | fine-tuned | 1 | 1 | 11 | 1.77 | 2.79 | 0.70 (0.70–0.70) | 0.40 | 0.60 |
| OSCD | fine-tuned | 3 | 1 | 9 | 4.42 | 7.54 | 0.73 (0.71–0.76) | 0.23 | 0.66 |
| GRIP4 distance to road | frozen | 1 | 1 | 4 | 0.60 | 1.16 | 0.77 (0.77–0.77) | 0.00 | 0.73 |
| Infra-Bench | frozen | 10 | 1 | 6 | 1.25 | 2.83 | 0.82 (0.66–0.95) | 0.00 | 0.79 |
| SpaceNet 7 | fine-tuned | 1 | 1 | 11 | 0.72 | 1.59 | 0.82 (0.82–0.82) | 0.65 | 0.79 |
| GeoCrossBench Hurricane Harvey | frozen | 6 | 1 | 9 | 1.25 | 6.26 | 0.87 (0.65–1.00) | 0.08 | 0.84 |
| PV4GER | fine-tuned | 2 | 1 | 10 | 0.21 | 0.76 | 0.89 (0.82–0.97) | 0.50 | 0.88 |
| EverWatch | fine-tuned | 1 | 1 | 7 | 0.47 | 1.51 | 0.91 (0.91–0.91) | 0.36 | 0.90 |
| SpaceNet 7 | frozen | 1 | 1 | 8 | 0.61 | 2.11 | 0.92 (0.92–0.92) | 0.69 | 0.92 |
| OSCD | frozen | 3 | 1 | 9 | 2.11 | 8.84 | 0.93 (0.90–0.95) | 0.33 | 0.93 |
| NeonTreeEvaluation | fine-tuned | 1 | 1 | 11 | 0.55 | 2.06 | 0.93 (0.93–0.93) | 0.74 | 0.93 |
| SpaceNet 2 | fine-tuned | 1 | 1 | 11 | 0.24 | 0.92 | 0.93 (0.93–0.93) | 0.85 | 0.93 |
| Substations | fine-tuned | 1 | 1 | 7 | 0.56 | 2.10 | 0.93 (0.93–0.93) | 0.82 | 0.93 |
| Chesapeake land cover | fine-tuned | 1 | 1 | 11 | 1.32 | 5.09 | 0.94 (0.94–0.94) | 0.79 | 0.93 |
| FLAIR / FLAIR 2 | fine-tuned | 1 | 1 | 11 | 0.88 | 3.47 | 0.94 (0.94–0.94) | 0.75 | 0.94 |
| South Africa crop type | frozen | 3 | 1 | 9 | 0.81 | 4.11 | 0.94 (0.89–0.98) | 0.76 | 0.94 |
| CaFFe | frozen | 1 | 1 | 8 | 1.41 | 5.95 | 0.95 (0.95–0.95) | 0.84 | 0.94 |
| Cashew plantation | frozen | 3 | 1 | 9 | 0.76 | 7.17 | 0.95 (0.85–1.00) | 0.25 | 0.94 |
| ForestNet | frozen | 1 | 1 | 8 | 0.93 | 3.90 | 0.95 (0.95–0.95) | 0.71 | 0.94 |
| GeoCrossBench Hurricane Harvey | fine-tuned | 6 | 1 | 9 | 2.08 | 8.28 | 0.95 (0.85–0.99) | 0.44 | 0.94 |
| WorldPop population density | frozen | 1 | 1 | 4 | 1.67 | 7.88 | 0.96 (0.96–0.96) | 0.76 | 0.95 |
| DeepGlobe Land Cover / DFC2022 (EarthShift) | fine-tuned | 2 | 1 | 8 | 2.28 | 10.81 | 0.96 (0.94–0.98) | 0.36 | 0.95 |
| Austrian Crop | frozen | 1 | 1 | 4 | 2.12 | 10.47 | 0.96 (0.96–0.96) | 0.00 | 0.96 |
| Brick kilns | frozen | 3 | 1 | 9 | 0.66 | 6.33 | 0.97 (0.92–1.00) | 0.74 | 0.96 |
| FLAIR / FLAIR 2 | frozen | 1 | 1 | 8 | 0.82 | 5.16 | 0.97 (0.97–0.97) | 0.92 | 0.97 |
| TreeSatAI | fine-tuned | 1 | 1 | 11 | 0.46 | 3.08 | 0.98 (0.98–0.98) | 0.83 | 0.98 |
| MMEarth-Bench soil nitrogen | fine-tuned | 2 | 1 | 7 | 0.96 | 6.99 | 0.98 (0.97–0.99) | 0.66 | 0.98 |
| MMEarth-Bench soil pH | fine-tuned | 1 | 1 | 7 | 1.10 | 7.51 | 0.98 (0.98–0.98) | 0.70 | 0.98 |
| CloudSEN12 (Cloud-S2) | fine-tuned | 1 | 1 | 11 | 0.47 | 3.50 | 0.98 (0.98–0.98) | 0.95 | 0.98 |
| PASTIS / PASTIS-R | fine-tuned | 2 | 1 | 9 | 0.50 | 3.71 | 0.98 (0.98–0.99) | 0.87 | 0.98 |
| SpaceNet 2 | frozen | 1 | 1 | 8 | 0.24 | 1.89 | 0.98 (0.98–0.98) | 0.95 | 0.98 |
| MMEarth Biomass | frozen | 2 | 1 | 4 | 1.82 | 15.12 | 0.99 (0.98–0.99) | 0.35 | 0.99 |
| WorldClim Bioclim | frozen | 1 | 1 | 4 | 1.06 | 9.10 | 0.99 (0.99–0.99) | 0.91 | 0.99 |
| Infra-Bench | fine-tuned | 10 | 1 | 5 | 1.05 | 11.81 | 0.99 (0.97–1.00) | 0.10 | 0.99 |
| DeepGlobe Land Cover / DFC2022 (EarthShift) | frozen | 2 | 1 | 8 | 0.88 | 9.83 | 0.99 (0.98–1.00) | 0.64 | 0.99 |
| MMEarth-Bench Biomass | fine-tuned | 1 | 1 | 7 | 0.94 | 9.81 | 0.99 (0.99–0.99) | 0.94 | 0.99 |
| Kuro Siwo (Flood-S1) | fine-tuned | 1 | 1 | 11 | 0.89 | 10.06 | 0.99 (0.99–0.99) | 0.79 | 0.99 |
| RESISC45 / UCMerced (EarthShift) | fine-tuned | 4 | 1 | 8 | 0.97 | 19.28 | 0.99 (0.98–1.00) | 0.80 | 0.99 |
| MMEarth-Bench soil organic carbon | fine-tuned | 2 | 1 | 7 | 1.26 | 19.06 | 0.99 (0.99–1.00) | 0.96 | 0.99 |
| Dynamic World | frozen | 10 | 1 | 4 | 0.92 | 23.84 | 0.99 (0.97–1.00) | 0.00 | 0.99 |
| HLS Burn Scars | frozen | 1 | 1 | 8 | 0.61 | 8.54 | 0.99 (0.99–0.99) | 0.86 | 0.99 |
| DFC2020 | frozen | 2 | 1 | 4 | 0.10 | 1.70 | 1.00 (0.99–1.00) | 0.00 | 1.00 |
| RESISC45 / UCMerced (EarthShift) | frozen | 4 | 1 | 8 | 0.72 | 18.56 | 1.00 (1.00–1.00) | 0.96 | 1.00 |
| fMoW | frozen | 4 | 1 | 6 | 0.03 | 0.94 | 1.00 (1.00–1.00) | 0.94 | 1.00 |

## 6. Do independent sources agree? (cross-source reproducibility)

**Strict** — dataset version x protocol x fraction x metric; ≥ 5 GeoFMs shared, ≥ 5 residual df: 13 groups reported by ≥ 2 sources, 6 share ≥ 3 GeoFMs, 0 share ≥ 5; estimable: 0.

**Loose** — dataset x protocol family x fraction x metric (versions pooled within source); ≥ 4 GeoFMs shared, ≥ 3 residual df: 43 groups reported by ≥ 2 sources, 15 share ≥ 3 GeoFMs, 5 share ≥ 5; estimable: 2.

| group | sources | GeoFMs | median Kendall τ between sources | cross-source disagreement σ_xp | stable between-model SD | agreement τ²/(τ²+σ²_xp) (90% CI) |
|---|---|---|---|---|---|---|
| BioMassters · frozen · 100% · rmse | 2 | 6 | 1.00 | 1.03 | 12.46 | 0.99 (0.98–1.00) |
| PASTIS / PASTIS-R · frozen · 100% · miou | 4 | 8 | 0.73 | 2.19 | 6.38 | 0.89 (0.80–0.99) |

σ_xp is disagreement between implementations about the same GeoFM (protocol and implementation differences plus seed noise of a mean); it is not seed noise.

## 7. Datasets reported by ≥ 2 sources (descriptive)

Reported separation = model-count-weighted SD of reported scores within the dataset's comparisons (points-scale comparisons only), over each source's own GeoFMs (note Eq. 10: not quality). LOPO ρ = leave-one-paper-out Spearman over the dataset's comparisons at the best K (structured / naive leaderboard), with comparisons and median GeoFMs behind it.

| dataset | domain | sources | comparisons | smallest | reported separation | LOPO ρ: structured / leaderboard (n, GeoFMs) |
|---|---|---|---|---|---|---|
| BigEarthNet v1 / v2 (reBEN) | Terrestrial ecosystems | 13 | 40 | 4 | 7.1 | 0.12 / 0.29 (36, 8) |
| EuroSAT | Terrestrial ecosystems | 11 | 33 | 4 | 10.4 | 0.19 / 0.15 (33, 8) |
| So2Sat LCZ42 (LCZ-S2) | Human systems | 11 | 28 | 4 | 7.2 | 0.29 / 0.17 (28, 8) |
| PASTIS / PASTIS-R | Agriculture | 7 | 25 | 4 | 7.5 | 0.63 / 0.23 (24, 10) |
| Brick kilns | Human systems | 7 | 20 | 7 | 3.5 | 0.22 / 0.32 (20, 12) |
| Cashew plantation | Agriculture | 7 | 19 | 7 | 8.6 | 0.25 / 0.37 (19, 8) |
| South Africa crop type | Agriculture | 7 | 18 | 7 | 3.6 | 0.20 / 0.48 (18, 8) |
| Sen1Floods11 | Inland water | 6 | 22 | 5 | 8.9 | 0.04 / 0.21 (22, 8) |
| ForestNet | Terrestrial ecosystems | 6 | 8 | 4 | 4.3 | 0.67 / 0.10 (6, 8) |
| NZ cattle | Agriculture | 5 | 8 | 4 | 5.4 | 0.14 / -0.05 (5, 8) |
| fMoW | Human systems | 4 | 12 | 4 | 4.8 | 0.92 / 0.58 (7, 6) |
| CropHarvest | Agriculture | 4 | 11 | 4 | 4.4 | 0.23 / 0.15 (9, 14) |
| MADOS | Oceans and coasts | 4 | 11 | 10 | 6.6 | 0.17 / 0.25 (11, 13) |
| PV4GER | Human systems | 4 | 11 | 4 | 4.1 | 0.62 / 0.36 (7, 8) |
| HLS Burn Scars | Terrestrial ecosystems | 4 | 10 | 5 | 3.9 | 0.42 / 0.24 (10, 12) |
| Chesapeake land cover | Terrestrial ecosystems | 4 | 6 | 4 | 6.2 | 0.24 / 0.46 (3, 8) |
| NeonTreeEvaluation | Terrestrial ecosystems | 4 | 6 | 4 | 3.0 | 0.45 / 0.46 (3, 8) |
| BioMassters | Terrestrial ecosystems | 3 | 10 | 4 | – | 0.67 / 0.46 (9, 10) |
| TreeSatAI | Terrestrial ecosystems | 3 | 9 | 4 | 2.5 | 0.13 / 0.19 (8, 8) |
| Fields of The World | Agriculture | 2 | 18 | 8 | 1.8 | 0.14 / 0.12 (18, 8) |
| DynamicEarthNet | Terrestrial ecosystems | 2 | 8 | 8 | 3.2 | 0.29 / 0.16 (8, 12) |
| SpaceNet 7 | Human systems | 2 | 8 | 8 | 3.8 | 0.37 / 0.06 (8, 12) |
| Austrian Crop | Agriculture | 2 | 7 | 4 | 8.3 | 0.15 / 0.50 (6, 10) |
| CaFFe | Cryosphere | 2 | 5 | 8 | 9.3 | 0.54 / -0.04 (5, 13) |
| CloudSEN12 (Cloud-S2) | Atmosphere | 2 | 3 | 4 | 2.7 | 0.21 / 0.34 (3, 7) |
| DFC2020 | Terrestrial ecosystems | 2 | 3 | 4 | 4.7 | 0.11 / 0.08 (3, 4) |
| Kuro Siwo (Flood-S1) | Inland water | 2 | 3 | 4 | 9.8 | 0.41 / -0.36 (3, 7) |
| RESISC45 | Terrestrial ecosystems | 2 | 3 | 4 | 14.2 | 0.60 / 0.45 (2, 4) |
| BreizhCrops | Agriculture | 2 | 2 | 5 | 10.0 | 0.39 / -0.08 (2, 11) |

66 further datasets are reported by a single source; no dataset-level quantity is reported for them.

## 8. Sensitivity: which findings depend on the analysis decisions

| | v1 (main text, no leaderboard, no regression, offset all) | **v2 (this report)** |
|---|---|---|
| evidence (GeoFMs × tasks) | 93×228, 20 src | 105×563, 28 src |
| datasets in ≥ 2 sources | 20 | 29 |
| K chosen / best | 2 / 4 | 2 / 4 |
| offset | all | none |
| K=1 vs leaderboard | -0.09 (90% CI -0.23 to +0.05) | -0.18 (90% CI -0.33 to -0.05) |
| best K vs leaderboard | +0.12 (90% CI +0.07 to +0.18) | +0.02 (90% CI -0.13 to +0.15) |
| dataset transfer (seen) | -0.06 (90% CI -0.13 to +0.01) | +0.02 (90% CI -0.14 to +0.16) |
| labels surviving correction | none | none |
| similarity recoverable | no | no |
| comparisons with seed-noise score | 0 | 203 |
| reproducibility groups (strict / loose) | 0 / – | 0 / 2 |

## 9. Limits

- Single reported scores: the residual mixes stable task-specific interaction with evaluation noise (note Eq. 9); seed-noise scores exist only where seed SDs are printed, and describe one implementation.
- The best-K figures are selected among 12 configurations and are optimistic (D14); the leave-one-paper-out test has limited power on this evidence (§3 simulation).
- In single-domain sources, domain-specific capability and implementation effects are not separable (D8).
- Geography and time blocks of Eq. 11 are not fitted: no geography/time metadata, and the evaluation design is not crossed enough to separate them from dataset.
- Points near the ceiling compress differences for classification benchmarks (D4).
- Seed-noise scores come only from papers that print seed SDs, which may be the more careful ones; a printed SD below 0.1 point (e.g. fMoW) makes the score close to 1 by construction.
