# What existing benchmarks measure: dataset-level analysis (v2.1)

Analysis of 2026-11-04 on the GeoFM meta-analysis workbook v4, following *GeoFM Benchmark Scoring* (S. Wang, Oct 2026). Object of study: the benchmark **datasets** — what they measure, how much they overlap, whether independent groups agree on the model differences they show, and how reliably they separate GeoFMs where seed noise is reported. Model capability vectors are nuisance parameters; nothing here ranks models. Every analysis decision, with its justification and a switch to undo it, is in [`analysis-decisions.md`](analysis-decisions.md). Built by `scripts/build_dataset_analysis.py`; numbers in `data/dataset_analysis.json`.

## Findings

1. **Where several groups evaluate the same dataset, its GeoFM ordering carries over — directionally robust, narrow in scope.** Same-dataset comparisons by different sources agree more (Kendall τ = 0.24) than different-dataset comparisons across sources (0.09); under a single ranking plus noise the two would be equal. The evidence comes from 14 source pairs: 11 of them show a positive contrast (one-sided sign test p = 0.029; unweighted mean +0.16), and leaving out any one source keeps it between +0.12 and +0.23. 85% of the same-dataset pairs come from six datasets (EuroSAT, BigEarthNet v1 / v2 (reBEN), So2Sat LCZ42 (LCZ-S2), Brick kilns, Cashew plantation, South Africa crop type), mostly GEO-Bench-family benchmarks, so the claim holds for widely re-evaluated benchmarks, not datasets in general. Possible shared evaluation code between sources cannot be ruled out from values alone. Pooled estimate +0.15 (90% CI +0.01 to +0.48); the interval is wide and skewed because few source pairs are informative. This estimate is conservative: pairs sharing only four GeoFMs pull it toward 0, and among pairs sharing ≥ 5 it is +0.33 (post hoc, 6 source pairs; §2).
2. **Orderings are also paper-specific.** Different datasets evaluated in the same paper agree more (τ = 0.26) than across papers (0.09): +0.17 (90% CI +0.04 to +0.27). A paper's task suite, protocol, model set or implementation shapes its orderings; these cannot be separated with published results.
3. **A dataset- and protocol-aware model may predict new papers' orderings better than a fixed leaderboard — credibly only for the selected best configuration, and not robustly to the optimiser's starts; whether that needs more than one dimension is suggestive only.** Predicting a held-out source from the other sources, the best structured model (K = 3) beats the naive leaderboard by +0.09 (90% CI +0.03 to +0.14) — but this is the best of 12 configurations scored on the same criterion; the prespecified rule's K = 2 gives +0.05 (90% CI -0.02 to +0.11). Beating the leaderboard is not itself evidence of several dimensions: in simulation with a single true dimension a one-factor structured model also beats it, by learning each dataset's direction. The dimensionality test proper — K = 3 against K = 1 within the same model — gives +0.13 (90% CI +0.03 to +0.21), also after selection. Anchored check: +0.06 (90% CI -0.04 to +0.14). Calibrated simulation recovers K = 1, 2, 3 under this rule, but in a world easier than the real one (higher predictability, weaker paper effects), so it does not settle the number of dimensions. Optimiser sensitivity (§3): refitting each held-out source with 10 starts instead of 3, in 3 sets of random starts, the rule chooses K = 2 in 2 sets, K = 3 in 1 set; ρ moves with the starts (K = 1: 0.168 with 3 starts, 0.030–0.112 with 10; K = 2: 0.258, 0.173–0.267; K = 3: 0.298, 0.218–0.308), and the best K credibly beats the leaderboard in 1 of the 3 sets. These figures, including the comparison with the leaderboard, depend on the optimiser; this does not strengthen the dimensionality evidence, which stays suggestive.
4. **The latent model does not yet turn dataset identity into out-of-paper predictions.** Predicting a held-out comparison from its dataset, protocol and sensor blocks alone, for datasets other sources report, differs from the model's own single ordering by -0.00 (90% CI -0.08 to +0.07). Finding 1 shows the information exists in the raw orderings; a likely (untested) reason the model cannot use it is that each dataset's loading is estimated from few comparisons (median 2). Dataset-to-dataset similarity is therefore not published (D13).
5. **Metadata labels do not credibly organise the datasets.** Domain, subdomain, task type and sensor all fail after correction for the four labels tested. Domain is the label closest to the threshold: it survives correction in two sensitivity runs (main text only; no regression tasks; p ≈ 0.04), so whether domain organises datasets is unresolved rather than ruled out (§8).
6. **Where seed noise is reported, model differences mostly survive re-seeding — with wide uncertainty.** 152 comparisons (≥ 6 GeoFMs, seed SDs printed for ≥ 3) across 57 dataset × protocol pairs: 73 have a 90% lower bound ≥ 0.8 on the share of model spread that survives re-seeding (note Eq. 6), 112 ≥ 0.5; comparisons from one paper share settings and are not independent (per dataset × protocol counts in §5). This is reliability within one implementation, and rounding of printed SDs is not yet propagated.
7. **Independent groups rarely evaluate the same GeoFMs on the same dataset and protocol.** Cross-source reproducibility is estimable for 0 strict and 2 loose dataset groups: BioMassters (2 sources, 6 GeoFMs, agreement 0.99); PASTIS / PASTIS-R (4 sources, 8 GeoFMs, agreement 0.89). Close values between sources can mean a shared evaluation codebase rather than independent replication. Standardised re-evaluation of the same GeoFMs by different groups is the missing evidence.

## 1. Evidence base

11,580 extracted results → **6,687** kept (configuration: main_text_only=False, leaderboard=True, regression=True, offset=select, ridge=3.0, ridge_paper_offset=3.0). Rules in order:

| Rule | Rows dropped |
|---|---|
| table placement unclear | 72 |
| ablation status of table not checked | 0 |
| ablation-study table | 140 |
| registry ablation model | 50 |
| ablation variant axis (non-headline setting) | 524 |
| not a GeoFM (baseline / task architecture / uncategorised) | 2,055 |
| paper-internal variant of the introducing paper's own method (D7) | 188 |
| per-class sub-score of a headline result (D5) | 120 |
| regression value outside the metric's domain | 0 |
| metric not on a bounded-points or log-error scale (skill scores etc.) | 226 |
| within-paper duplicate (appendix repeats main text; leaderboard 'best of' repeats s2_main) | 14 |
| recitation of an earlier paper's value | 156 |
| metric twin (one metric per paper x benchmark x protocol x fraction x setting) | 1,348 |

Reprinting papers (kept only in the earliest source): anysat ← pangea (22 cells, 77% identical); terrafm ← copernicus (32 cells, 100% identical); terrafm ← galileo (66 cells, 95% identical).

Imagery comparisons with ≥ 4 GeoFMs: **100 GeoFMs × 496 tasks** (95 datasets, 27 sources: papers plus the GEO-Bench-2 leaderboard), 10.5% of cells observed, median 9 GeoFMs per comparison; 207 comparisons come from appendix tables, 32 from the leaderboard, 56 are regression tasks. 52 of 100 GeoFMs appear in a single source, 32 in three or more; 29 of 95 datasets are reported by more than one source; 8 sources cover a single domain.

## 2. Model-free tests: do orderings agree across comparisons? (D15)

Kendall τ between the GeoFM orderings of every pair of comparisons sharing ≥ 4 GeoFMs (median 4). 0 = unrelated orderings, 1 = identical.

| | different source | same source |
|---|---|---|
| different dataset | 0.093 (21,583 pairs) | 0.263 (7,207 pairs) |
| same dataset | 0.240 (814 pairs) | 0.446 (813 pairs) |

| contrast | all pairs | same protocol family | without flagged source pairs |
|---|---|---|---|
| dataset identity (same − different dataset, across sources) | +0.15 (90% CI +0.01 to +0.48) | +0.18 (90% CI +0.03 to +0.48) | +0.15 (90% CI +0.02 to +0.48) |
| … each dataset as its own control | +0.13 (90% CI +0.02 to +0.43) | +0.16 (90% CI +0.04 to +0.44) | +0.13 (90% CI +0.01 to +0.43) |
| paper specificity (same − different source, different datasets) | +0.17 (90% CI +0.04 to +0.27) | +0.17 (90% CI +0.04 to +0.30) | +0.17 (90% CI +0.05 to +0.27) |

Per source pair (cross-source pairs on the same dataset vs on different datasets): 11 of 14 positive, one-sided sign test p = 0.029; leave-one-source-out range +0.12 to +0.23.

| sources | same-dataset pairs | contrast | datasets |
|---|---|---|---|
| galileo × geocross-bench | 232 | +0.13 | BigEarthNet v1 / v2 (reBEN), Brick kilns, Cashew plantation, EuroSAT … |
| galileo × olmoearth_v12 | 127 | +0.21 | BigEarthNet v1 / v2 (reBEN), BreizhCrops, Brick kilns, Cashew plantation … |
| geocross-bench × olmoearth_v12 | 82 | +0.20 | BigEarthNet v1 / v2 (reBEN), Brick kilns, Cashew plantation, EuroSAT … |
| earthshift × geocross-bench | 72 | -0.06 | BigEarthNet v1 / v2 (reBEN), EuroSAT, Sen1Floods11 |
| earthshift × galileo | 64 | +0.31 | BigEarthNet v1 / v2 (reBEN), EuroSAT |
| croma × galileo | 48 | -0.16 | BigEarthNet v1 / v2 (reBEN), EuroSAT |
| dofa × galileo | 40 | +0.08 | BigEarthNet v1 / v2 (reBEN), Brick kilns, Cashew plantation, EuroSAT … |
| galileo × panopticon | 40 | +0.14 | BigEarthNet v1 / v2 (reBEN), Brick kilns, Cashew plantation, EuroSAT … |
| geocross-bench × panopticon | 40 | +0.02 | BigEarthNet v1 / v2 (reBEN), Brick kilns, Cashew plantation, EuroSAT … |
| pangea × tessera | 36 | +0.57 | BioMassters, PASTIS / PASTIS-R |
| earthshift × olmoearth_v12 | 16 | -0.01 | BigEarthNet v1 / v2 (reBEN), EuroSAT |
| anysat × galileo | 8 | +0.18 | So2Sat LCZ42 (LCZ-S2) |
| pangea × sustainfm | 6 | +0.30 | HLS Burn Scars, MADOS |
| geobench_v2_leaderboard × prithvi_v2 | 3 | +0.37 | BigEarthNet v1 / v2 (reBEN), ForestNet, So2Sat LCZ42 (LCZ-S2) |

Sensitivity of the pooled contrast to pair overlap (post hoc: added after the main estimate was seen). Kendall τ over 4 shared GeoFMs is noisy and, where the shared GeoFMs are close in capability, pulled toward 0 in both cells. Weighting pairs by the inverse of τ's null variance, or requiring more shared GeoFMs, raises the contrast but rests on fewer source pairs:

| pairs sharing ≥ | same-dataset pairs | source pairs | pair-weighted | inverse-variance weighted |
|---|---|---|---|---|
| 4 GeoFMs | 814 | 14 | +0.15 (90% CI +0.03 to +0.47) | +0.18 (90% CI +0.02 to +0.49) |
| 5 GeoFMs | 156 | 6 | +0.33 (90% CI +0.03 to +0.61) | +0.35 (90% CI +0.04 to +0.59) |
| 6 GeoFMs | 116 | 4 | +0.34 (90% CI +0.07 to +0.56) | +0.35 (90% CI +0.08 to +0.57) |
| 7 GeoFMs | 50 | 2 | +0.42 (90% CI +0.19 to +0.44) | +0.43 (90% CI +0.19 to +0.44) |

Possible shared-codebase source pairs (matched values within a median of 1 point): none. Intervals: cluster bootstrap over sources (2,000 draws).

## 3. How many shared dimensions? (the note's one-leaderboard test)

Model: y_mt = μ_t + λ_t′θ_m + c_{m,p(t)} + η_mt, each task in units of its residual SD (pooled prior within metric family); λ_t = dataset + protocol-family + sensor blocks + task part (Eq. 11/12 group ridge); c = paper × model implementation offset. Leave-one-paper-out Spearman ρ of predicted vs reported within-task order (naive leaderboard = mean within-comparison z-score in all other sources, a K-independent single ranking):

Block-predicted (primary, D9): nothing from the held-out comparison is used; the plain leaderboard likewise. Anchored (secondary): the comparison's loading is estimated from half its GeoFMs and the other half predicted; the leaderboard is scored on the same half.

| offset | anchored K=1 | anchored K=2 | anchored K=3 | anchored K=4 | anchored leaderboard | blocks K=1 | blocks K=2 | blocks K=3 | blocks K=4 | leaderboard |
|---|---|---|---|---|---|---|---|---|---|---|
| all | -0.017 | 0.038 | 0.165 | 0.149 | 0.209 | 0.132 | 0.191 | 0.206 | 0.153 | 0.182 |
| multi_domain | 0.016 | 0.054 | 0.151 | 0.172 | 0.209 | 0.132 | 0.185 | 0.213 | 0.155 | 0.182 |
| none (chosen) | 0.168 | 0.258 | 0.298 | 0.221 | 0.209 | 0.087 | 0.203 | 0.242 | 0.121 | 0.182 |

Offset choice (D8): all (K=3) minus chosen (K=3): -0.13 (90% CI -0.24 to -0.04); multi_domain (K=4) minus chosen (K=3): -0.13 (90% CI -0.25 to -0.01).

K (D9): best K = 3; chosen (smallest not credibly worse) K = 2. Paired differences to the best: K=1: -0.13 (90% CI -0.21 to -0.03); K=2: -0.04 (90% CI -0.09 to +0.01); K=4: -0.08 (90% CI -0.12 to -0.04).

Against the leaderboard: K = 1 -0.04 (90% CI -0.14 to +0.05); K = 2 (chosen) +0.05 (90% CI -0.02 to +0.11); K = 3 (best, selected — optimistic) +0.09 (90% CI +0.03 to +0.14). Anchored: K = 1 -0.10 (90% CI -0.19 to -0.01); K = 3 +0.06 (90% CI -0.04 to +0.14).

**Calibrated simulation (D16).** A general factor (one leaderboard) plus specific factors, dataset-shared loadings and implementation effects, fitted on a 54-point grid to the real data: targets board 0.209, tau_xs_dd 0.093, tau_xs_sd 0.240, tau_ss_dd 0.263; achieved board 0.195, tau_xs_dd 0.043, tau_xs_sd 0.264, tau_ss_dd 0.120 with general-factor mean 0.6, SNR 2.0, dataset share 0.9, implementation effect 0.5 noise SD.

| K true | K selected by the rule | best K | ρ by K | leaderboard | best K − leaderboard |
|---|---|---|---|---|---|
| 1 | 1 | 1 | K1: 0.409, K2: 0.385, K3: 0.371, K4: 0.354 | 0.132 | +0.28 (90% CI +0.19 to +0.35) |
| 2 | 2 | 2 | K1: 0.441, K2: 0.464, K3: 0.422, K4: 0.394 | 0.414 | +0.05 (90% CI +0.02 to +0.08) |
| 3 | 3 | 3 | K1: 0.319, K2: 0.347, K3: 0.402, K4: 0.376 | 0.257 | +0.15 (90% CI +0.11 to +0.19) |

Offset options under the calibrated truth (K = 2):

| offset | ρ (K = 2) | leaderboard | dataset gain (seen datasets) | geometry recovery (≥ 2-source datasets) |
|---|---|---|---|---|
| all | 0.529 | 0.362 | +0.209 | 0.79 |
| multi_domain | 0.534 | 0.362 | +0.212 | 0.79 |
| none | 0.519 | 0.362 | +0.198 | 0.72 |

**Optimiser restarts (D17, sensitivity).** The leave-one-paper-out fits above use 3 starts (naive-leaderboard seed, SVD, 1 random). For the chosen offset only — the D8 offset choice was made with 3-start fits and is not re-examined — every fold was refitted with 10 starts (the leaderboard and SVD starts plus 8 random), keeping the lowest objective at the reweighting round where the build compares starts. This was done for 3 sets of random starts: the build's seed 0 in every fold (its 3 starts are a subset of the 10; rerunning those 3 reproduces the table above exactly), and 2 sets whose random starts differ between folds.

| start set | ρ K=1 | ρ K=2 | ρ K=3 | ρ K=4 | K=4 − K=3 | K rule: best / chosen | K=1 − leaderboard | best K − leaderboard |
|---|---|---|---|---|---|---|---|---|
| 3 starts (v2.1) | 0.168 | 0.258 | 0.298 | 0.221 | -0.08 (90% CI -0.12 to -0.04) | 3 / 2 | -0.04 (90% CI -0.14 to +0.05) | +0.09 (90% CI +0.03 to +0.14) |
| 10 starts, seed 0 in every fold (as the build) | 0.112 | 0.173 | 0.308 | 0.216 | -0.09 (90% CI -0.20 to +0.01) | 3 / 3 | -0.10 (90% CI -0.22 to +0.02) | +0.10 (90% CI +0.04 to +0.15) |
| 10 starts, seed 1000 + fold index | 0.045 | 0.250 | 0.218 | 0.231 | +0.01 (90% CI -0.02 to +0.05) | 2 / 2 | -0.16 (90% CI -0.26 to -0.07) | +0.04 (90% CI -0.03 to +0.11) |
| 10 starts, seed 2000 + fold index | 0.030 | 0.267 | 0.237 | 0.221 | -0.02 (90% CI -0.06 to +0.02) | 2 / 2 | -0.18 (90% CI -0.29 to -0.07) | +0.06 (90% CI -0.00 to +0.12) |
| leaderboard | 0.209 | 0.209 | 0.209 | 0.209 | | | | |

Within a fold, the objectives reached from the 10 starts (range over the 3 sets):

| K | spread, median % of the fold's best | spread, max % | starts within 0.1% of the best (median) | starts stopped at the 200-iteration cap |
|---|---|---|---|---|
| 1 | 4.0–7.3 | 10.3–13.1 | 1 | 3 to 5 of 270 |
| 2 | 6.9–7.1 | 10.4–11.3 | 1 to 2 | 133 to 165 of 270 |
| 3 | 4.2–4.8 | 7.2–8.1 | 1 to 2 | 220 to 234 of 270 |
| 4 | 4.1–4.8 | 5.9–7.4 | 1 | 250 to 253 of 270 |

Start dependence is not confined to K ≥ 3 or to the iteration cap: K = 1 fits converge (3 to 5 of 270 starts at the cap) yet their objectives differ between starts by a median of 4.0–7.3%. Where K ≥ 3 starts stop at the cap, their objective was still falling by a median of 3–6 millionths of its value per iteration (2 sets with this record); at that rate, if the per-iteration decrease does not rise, even 1,000 more iterations would lower it by under 1%, against spreads of several per cent. The 10-start fits keep the lowest of 10 objectives (in the seed-0 set never above the 3-start fit), but do not improve out-of-paper prediction (K = 1: ρ 0.168 with 3 starts, 0.030 to 0.112 with 10), so the 10-start figures are an alternative, not a correction. The scoring note asks that extra factors be kept only where the task geometry they describe is stable; a geometry that moves with the optimiser's starting point does not meet that, which is a further reason the dimensionality result (Finding 3) stays suggestive.

K = 4 minus K = 3 is -0.08 (90% CI -0.12 to -0.04) with 3 starts; with 10 starts it is -0.09 (90% CI -0.20 to +0.01); +0.01 (90% CI -0.02 to +0.05); -0.02 (90% CI -0.06 to +0.02). K = 4 is not credibly worse than K = 3 in any of the 3 sets. This is not because K = 4 got better: its ρ is 0.216 to 0.231 with 10 starts against 0.221 with 3, while K = 3 ranges 0.218 to 0.308 (3 starts: 0.298), so the 3-start gap depended on which K = 3 optimum was reached. K = 4 is also less stable across folds: its interval against the leaderboard is -0.06 to +0.08 with 3 starts and as wide as -0.14 to +0.14 with 10. These bootstrap intervals are conditional on the fitted optima and leave optimiser variation out; the spread across the seed sets is the optimiser part.

Applying the D9 K rule to the 10-start fits gives best / chosen K = 3 / 3, 2 / 2, 2 / 2 in the 3 sets (3 starts: 3 / 2). Chosen K equals best K in every set, so its gain over the leaderboard is still a selected figure (best of 4 K within the offset chosen in v2.1; D14), not a prespecified one; that best K credibly beats the leaderboard in 1 of the 3 sets (the seed-0 set, whose random starts are shared across folds; backlog P-N3c). The chosen K changes because the ρ of every K moves with the starts, not because K is better identified; this does not strengthen the dimensionality evidence. Sensitivity only: the frozen analysis and the figures above are unchanged.

## 4. Do datasets measure different things?

Out of paper, for datasets also reported by other sources: -0.00 (90% CI -0.08 to +0.07). Datasets seen only in the held-out source: +0.10 (90% CI -0.00 to +0.19).

Variance in dataset loadings explained by each label, over datasets reported by ≥ 2 sources (blank labels missing; permutation null over datasets; Bonferroni over 4 labels). 'Direction only' asks what a dataset measures, not how strongly it separates GeoFMs:

| label | R² (full) | null | p (Bonf.) | R² (direction) | null | p (Bonf.) | datasets |
|---|---|---|---|---|---|---|---|
| domain | 0.29 | 0.21 | 0.59 | 0.30 | 0.21 | 0.59 | 29 |
| subdomain | 0.48 | 0.47 | 1.00 | 0.47 | 0.46 | 1.00 | 29 |
| task_type | 0.11 | 0.11 | 1.00 | 0.14 | 0.11 | 1.00 | 29 |
| sensor | 0.47 | 0.42 | 1.00 | 0.45 | 0.42 | 1.00 | 27 |

Dataset-to-dataset similarity is **not published** (D13): simulated recovery on this mask would allow it (median 0.716), but dataset loadings do not credibly transfer across papers on the real data, so the estimated similarities would describe single papers, not datasets.

## 5. Seed-noise reliability where it is reported (note Eq. 3–6)

Comparisons where ≥ 3 GeoFMs report a seed SD: 152. σ = median seed SD of one evaluation (points, or log-error ×100 for regression); spread = SD of the reported scores; score = τ²/(τ²+σ²) with τ² = spread² − σ²/n_reps: the share of the comparison's model differences that survives re-seeding, for its models and implementation. 'If single runs' treats every reported value as one run (most conservative). 5% of comparisons do not state how many runs a reported mean averages; 3 is assumed. Printed SDs are floored at half their last printed digit (0 cells); comparisons need ≥ 6 GeoFMs. Lower bounds ≥ 0.8: 73 of 152 comparisons; ≥ 0.5: 112.

| dataset | protocol | comparisons | sources | GeoFMs | σ | spread | score (range) | comparisons with lower bound ≥ 0.8 | lowest 5% bound | if single runs |
|---|---|---|---|---|---|---|---|---|---|---|
| BigEarthNet v1 / v2 (reBEN) | fine-tuned | 7 | 4 | 9 | 0.47 | 3.55 | 0.88 (0.54–1.00) | 4 of 7 | 0.19 | 0.83 |
| So2Sat LCZ42 (LCZ-S2) | fine-tuned | 5 | 3 | 9 | 1.54 | 3.66 | 0.82 (0.57–0.97) | 1 of 5 | 0.23 | 0.76 |
| BigEarthNet v1 / v2 (reBEN) | frozen | 6 | 3 | 8 | 0.61 | 11.35 | 0.91 (0.45–1.00) | 5 of 6 | 0.04 | 0.84 |
| EuroSAT | fine-tuned | 6 | 3 | 8 | 1.20 | 11.98 | 0.96 (0.90–1.00) | 4 of 6 | 0.66 | 0.96 |
| Brick kilns | fine-tuned | 4 | 2 | 9 | 0.27 | 0.77 | 0.74 (0.29–1.00) | 0 of 4 | 0.03 | 0.65 |
| Cashew plantation | fine-tuned | 4 | 2 | 9 | 3.94 | 7.88 | 0.76 (0.41–0.92) | 0 of 4 | 0.23 | 0.64 |
| ForestNet | fine-tuned | 2 | 2 | 11 | 1.36 | 2.75 | 0.79 (0.73–0.84) | 0 of 2 | 0.27 | 0.73 |
| Fields of The World | fine-tuned | 9 | 2 | 8 | 0.46 | 1.17 | 0.83 (0.38–0.99) | 0 of 9 | 0.00 | 0.78 |
| South Africa crop type | fine-tuned | 4 | 2 | 9 | 0.88 | 3.67 | 0.88 (0.76–0.99) | 1 of 4 | 0.39 | 0.86 |
| Fields of The World | frozen | 9 | 2 | 8 | 0.35 | 2.03 | 0.93 (0.78–0.98) | 2 of 9 | 0.39 | 0.91 |
| Sen1Floods11 | fine-tuned | 5 | 2 | 9 | 2.46 | 13.77 | 0.96 (0.87–1.00) | 3 of 5 | 0.27 | 0.95 |
| Sen1Floods11 | frozen | 5 | 2 | 9 | 2.05 | 12.71 | 0.96 (0.88–1.00) | 4 of 5 | 0.33 | 0.96 |
| NZ cattle | fine-tuned | 2 | 2 | 9 | 0.43 | 3.06 | 0.98 (0.96–0.99) | 1 of 2 | 0.80 | 0.98 |
| So2Sat LCZ42 (LCZ-S2) | frozen | 4 | 2 | 9 | 0.73 | 9.33 | 0.99 (0.98–1.00) | 3 of 4 | 0.52 | 0.99 |
| EuroSAT | frozen | 5 | 2 | 9 | 0.56 | 18.15 | 1.00 (0.99–1.00) | 5 of 5 | 0.91 | 1.00 |
| DynamicEarthNet | frozen | 1 | 1 | 8 | 4.26 | 3.54 | 0.33 (0.33–0.33) | 0 of 1 | 0.00 | 0.00 |
| Infra-Bench | frozen | 2 | 1 | 6 | 1.56 | 2.41 | 0.67 (0.66–0.69) | 0 of 2 | 0.00 | 0.58 |
| DynamicEarthNet | fine-tuned | 1 | 1 | 11 | 2.58 | 3.92 | 0.68 (0.68–0.68) | 0 of 1 | 0.29 | 0.56 |
| CaFFe | fine-tuned | 1 | 1 | 11 | 1.77 | 2.79 | 0.70 (0.70–0.70) | 0 of 1 | 0.45 | 0.60 |
| OSCD | fine-tuned | 3 | 1 | 9 | 4.42 | 7.54 | 0.73 (0.71–0.76) | 0 of 3 | 0.27 | 0.66 |
| SpaceNet 7 | fine-tuned | 1 | 1 | 11 | 0.72 | 1.59 | 0.82 (0.82–0.82) | 0 of 1 | 0.63 | 0.79 |
| GeoCrossBench Hurricane Harvey | frozen | 6 | 1 | 9 | 1.25 | 6.26 | 0.87 (0.65–1.00) | 3 of 6 | 0.07 | 0.84 |
| PV4GER | fine-tuned | 2 | 1 | 10 | 0.21 | 0.76 | 0.89 (0.82–0.97) | 1 of 2 | 0.53 | 0.88 |
| EverWatch | fine-tuned | 1 | 1 | 7 | 0.47 | 1.51 | 0.91 (0.91–0.91) | 0 of 1 | 0.48 | 0.90 |
| CloudSEN12 (Cloud-S2) | frozen | 1 | 1 | 8 | 0.53 | 1.76 | 0.92 (0.92–0.92) | 0 of 1 | 0.50 | 0.91 |
| SpaceNet 7 | frozen | 1 | 1 | 8 | 0.61 | 2.11 | 0.92 (0.92–0.92) | 0 of 1 | 0.67 | 0.92 |
| NeonTreeEvaluation | fine-tuned | 1 | 1 | 11 | 0.55 | 2.06 | 0.93 (0.93–0.93) | 0 of 1 | 0.75 | 0.93 |
| SpaceNet 2 | fine-tuned | 1 | 1 | 11 | 0.24 | 0.92 | 0.93 (0.93–0.93) | 1 of 1 | 0.85 | 0.93 |
| Substations | fine-tuned | 1 | 1 | 7 | 0.56 | 2.10 | 0.93 (0.93–0.93) | 1 of 1 | 0.81 | 0.93 |
| Chesapeake land cover | fine-tuned | 1 | 1 | 11 | 1.32 | 5.09 | 0.94 (0.94–0.94) | 0 of 1 | 0.76 | 0.93 |
| FLAIR / FLAIR 2 | fine-tuned | 1 | 1 | 11 | 0.88 | 3.47 | 0.94 (0.94–0.94) | 0 of 1 | 0.77 | 0.94 |
| OSCD | frozen | 3 | 1 | 9 | 2.11 | 8.84 | 0.94 (0.92–0.95) | 2 of 3 | 0.65 | 0.94 |
| South Africa crop type | frozen | 3 | 1 | 9 | 0.81 | 4.11 | 0.94 (0.89–0.98) | 2 of 3 | 0.76 | 0.94 |
| CaFFe | frozen | 1 | 1 | 8 | 1.41 | 5.95 | 0.95 (0.95–0.95) | 1 of 1 | 0.84 | 0.94 |
| Cashew plantation | frozen | 3 | 1 | 9 | 0.76 | 7.17 | 0.95 (0.85–1.00) | 2 of 3 | 0.15 | 0.94 |
| ForestNet | frozen | 1 | 1 | 8 | 0.93 | 3.90 | 0.95 (0.95–0.95) | 0 of 1 | 0.64 | 0.94 |
| GeoCrossBench Hurricane Harvey | fine-tuned | 6 | 1 | 9 | 2.08 | 8.28 | 0.95 (0.85–0.99) | 2 of 6 | 0.47 | 0.94 |
| DeepGlobe Land Cover / DFC2022 (EarthShift) | fine-tuned | 2 | 1 | 8 | 2.28 | 10.81 | 0.96 (0.94–0.98) | 0 of 2 | 0.45 | 0.95 |
| Brick kilns | frozen | 3 | 1 | 9 | 0.66 | 6.33 | 0.97 (0.92–1.00) | 2 of 3 | 0.74 | 0.96 |
| TreeSatAI | frozen | 1 | 1 | 8 | 0.61 | 3.59 | 0.97 (0.97–0.97) | 1 of 1 | 0.87 | 0.97 |
| Kuro Siwo (Flood-S1) | frozen | 1 | 1 | 8 | 1.87 | 11.56 | 0.97 (0.97–0.97) | 0 of 1 | 0.53 | 0.97 |
| FLAIR / FLAIR 2 | frozen | 1 | 1 | 8 | 0.82 | 5.16 | 0.97 (0.97–0.97) | 1 of 1 | 0.92 | 0.97 |
| TreeSatAI | fine-tuned | 1 | 1 | 11 | 0.46 | 3.08 | 0.98 (0.98–0.98) | 1 of 1 | 0.83 | 0.98 |
| MMEarth-Bench soil nitrogen | fine-tuned | 2 | 1 | 7 | 0.96 | 6.99 | 0.98 (0.97–0.99) | 1 of 2 | 0.72 | 0.98 |
| MMEarth-Bench soil pH | fine-tuned | 1 | 1 | 7 | 1.10 | 7.51 | 0.98 (0.98–0.98) | 0 of 1 | 0.74 | 0.98 |
| CloudSEN12 (Cloud-S2) | fine-tuned | 1 | 1 | 11 | 0.47 | 3.50 | 0.98 (0.98–0.98) | 1 of 1 | 0.96 | 0.98 |
| PASTIS / PASTIS-R | fine-tuned | 2 | 1 | 9 | 0.50 | 3.71 | 0.98 (0.98–0.99) | 2 of 2 | 0.88 | 0.98 |
| PASTIS / PASTIS-R | frozen | 1 | 1 | 8 | 0.71 | 5.24 | 0.98 (0.98–0.98) | 1 of 1 | 0.95 | 0.98 |
| SpaceNet 2 | frozen | 1 | 1 | 8 | 0.24 | 1.89 | 0.98 (0.98–0.98) | 1 of 1 | 0.96 | 0.98 |
| HLS Burn Scars | fine-tuned | 1 | 1 | 11 | 0.69 | 6.10 | 0.99 (0.99–0.99) | 0 of 1 | 0.25 | 0.99 |
| DeepGlobe Land Cover / DFC2022 (EarthShift) | frozen | 2 | 1 | 8 | 0.88 | 9.83 | 0.99 (0.98–1.00) | 1 of 2 | 0.68 | 0.99 |
| MMEarth-Bench Biomass | fine-tuned | 1 | 1 | 7 | 0.94 | 9.81 | 0.99 (0.99–0.99) | 1 of 1 | 0.94 | 0.99 |
| Kuro Siwo (Flood-S1) | fine-tuned | 1 | 1 | 11 | 0.89 | 10.06 | 0.99 (0.99–0.99) | 1 of 1 | 0.80 | 0.99 |
| RESISC45 / UCMerced (EarthShift) | fine-tuned | 4 | 1 | 8 | 0.97 | 19.28 | 0.99 (0.98–1.00) | 4 of 4 | 0.84 | 0.99 |
| MMEarth-Bench soil organic carbon | fine-tuned | 2 | 1 | 7 | 1.26 | 19.06 | 0.99 (0.99–1.00) | 2 of 2 | 0.96 | 0.99 |
| HLS Burn Scars | frozen | 1 | 1 | 8 | 0.61 | 8.54 | 0.99 (0.99–0.99) | 1 of 1 | 0.82 | 0.99 |
| RESISC45 / UCMerced (EarthShift) | frozen | 4 | 1 | 8 | 0.72 | 18.56 | 1.00 (1.00–1.00) | 4 of 4 | 0.97 | 1.00 |

## 6. Do independent sources agree? (cross-source reproducibility)

**Strict** — dataset version x protocol x fraction x metric; ≥ 5 GeoFMs shared, ≥ 5 residual df: 13 groups reported by ≥ 2 sources, 6 share ≥ 3 GeoFMs, 0 share ≥ 5; estimable: 0.

**Loose** — dataset x protocol family x fraction x metric (versions pooled within source); ≥ 4 GeoFMs shared, ≥ 3 residual df: 42 groups reported by ≥ 2 sources, 15 share ≥ 3 GeoFMs, 5 share ≥ 5; estimable: 2.

| group | sources | GeoFMs | median Kendall τ between sources | cross-source disagreement σ_xp | stable between-model SD | agreement τ²/(τ²+σ²_xp) (90% CI) |
|---|---|---|---|---|---|---|
| BioMassters · frozen · 100% · rmse | 2 | 6 | 1.00 | 1.03 | 12.46 | 0.99 (0.98–1.00) |
| PASTIS / PASTIS-R · frozen · 100% · miou | 4 | 8 | 0.73 | 2.19 | 6.38 | 0.89 (0.80–0.99) |

σ_xp is disagreement between implementations about the same GeoFM (protocol and implementation differences plus seed noise of a mean); it is not seed noise.

## 7. Datasets reported by ≥ 2 sources (descriptive)

Reported separation = model-count-weighted SD of reported scores within the dataset's comparisons (points-scale comparisons only), over each source's own GeoFMs (note Eq. 10: not quality). LOPO ρ = leave-one-paper-out Spearman over the dataset's comparisons at the best K (structured / naive leaderboard), with comparisons and median GeoFMs behind it.

| dataset | domain | sources | comparisons | smallest | reported separation | LOPO ρ: structured / leaderboard (n, GeoFMs) |
|---|---|---|---|---|---|---|
| BigEarthNet v1 / v2 (reBEN) | Terrestrial ecosystems | 13 | 40 | 4 | 7.1 | 0.21 / 0.27 (36, 8) |
| EuroSAT | Terrestrial ecosystems | 11 | 33 | 4 | 10.4 | 0.22 / 0.15 (33, 8) |
| So2Sat LCZ42 (LCZ-S2) | Human systems | 11 | 28 | 4 | 7.2 | 0.18 / 0.16 (28, 8) |
| PASTIS / PASTIS-R | Agriculture | 7 | 22 | 4 | 7.3 | 0.48 / 0.19 (21, 10) |
| Brick kilns | Human systems | 7 | 20 | 7 | 3.5 | 0.41 / 0.29 (20, 12) |
| Cashew plantation | Agriculture | 7 | 17 | 7 | 8.6 | 0.36 / 0.25 (17, 8) |
| South Africa crop type | Agriculture | 7 | 16 | 7 | 3.4 | 0.40 / 0.35 (16, 8) |
| Sen1Floods11 | Inland water | 6 | 20 | 5 | 9.3 | 0.20 / 0.24 (20, 8) |
| ForestNet | Terrestrial ecosystems | 6 | 8 | 4 | 4.3 | 0.42 / 0.15 (6, 8) |
| NZ cattle | Agriculture | 5 | 6 | 4 | 4.7 | 0.19 / -0.13 (5, 8) |
| CropHarvest | Agriculture | 4 | 11 | 4 | 4.4 | 0.12 / 0.14 (9, 14) |
| MADOS | Oceans and coasts | 4 | 10 | 10 | 6.7 | 0.31 / 0.21 (10, 14) |
| PV4GER | Human systems | 4 | 9 | 4 | 3.5 | 0.65 / 0.29 (7, 8) |
| HLS Burn Scars | Terrestrial ecosystems | 4 | 7 | 5 | 4.5 | 0.45 / 0.33 (7, 9) |
| Chesapeake land cover | Terrestrial ecosystems | 4 | 4 | 4 | 5.7 | 0.42 / 0.39 (3, 8) |
| NeonTreeEvaluation | Terrestrial ecosystems | 4 | 4 | 4 | 3.1 | 0.72 / 0.36 (3, 8) |
| BioMassters | Terrestrial ecosystems | 3 | 10 | 4 | – | 0.57 / 0.45 (9, 10) |
| TreeSatAI | Terrestrial ecosystems | 3 | 9 | 4 | 2.5 | -0.10 / 0.19 (8, 8) |
| fMoW | Human systems | 3 | 8 | 4 | 5.9 | 0.75 / 0.58 (7, 6) |
| Fields of The World | Agriculture | 2 | 18 | 8 | 1.8 | 0.18 / 0.13 (18, 8) |
| Austrian Crop | Agriculture | 2 | 7 | 4 | 8.3 | 0.28 / 0.49 (6, 10) |
| CaFFe | Cryosphere | 2 | 5 | 8 | 9.3 | 0.65 / -0.03 (5, 13) |
| DynamicEarthNet | Terrestrial ecosystems | 2 | 5 | 8 | 3.2 | 0.25 / 0.10 (5, 12) |
| SpaceNet 7 | Human systems | 2 | 5 | 8 | 3.4 | 0.36 / 0.06 (5, 12) |
| CloudSEN12 (Cloud-S2) | Atmosphere | 2 | 3 | 4 | 2.7 | 0.14 / 0.34 (3, 7) |
| DFC2020 | Terrestrial ecosystems | 2 | 3 | 4 | 4.7 | -0.06 / 0.41 (3, 4) |
| Kuro Siwo (Flood-S1) | Inland water | 2 | 3 | 4 | 9.8 | -0.22 / -0.22 (3, 7) |
| RESISC45 | Terrestrial ecosystems | 2 | 3 | 4 | 14.2 | 0.60 / 0.45 (2, 4) |
| BreizhCrops | Agriculture | 2 | 2 | 5 | 10.0 | 0.71 / -0.10 (2, 11) |

66 further datasets are reported by a single source; no dataset-level quantity is reported for them.

## 8. Sensitivity: which findings depend on the analysis decisions

| | v1 (main text, no leaderboard, no regression, offset all) | v2 · a_main_text_only | v2 · b_no_leaderboard | v2 · c_no_regression | v2 · d_all_v1_decisions | **v2.1 (this report)** |
|---|---|---|---|---|---|---|
| evidence (GeoFMs × tasks) | 93×228, 20 src | 94×295, 22 src | 98×464, 26 src | 98×440, 25 src | 88×218, 19 src | 100×496, 27 src |
| datasets in ≥ 2 sources | 20 | 27 | 23 | 28 | 20 | 29 |
| dataset identity, model-free τ (v2.1+) | – | +0.47 (90% CI +0.13 to +0.63) | +0.15 (90% CI +0.00 to +0.49) | +0.14 (90% CI +0.01 to +0.46) | +0.43 (90% CI +0.09 to +0.67) | +0.15 (90% CI +0.01 to +0.48) |
| τ: source pairs with positive contrast (sign test) | – | 3/4 (p = 0.31) | 10/13 (p = 0.05) | 10/14 (p = 0.09) | 3/4 (p = 0.31) | 11/14 (p = 0.03) |
| K chosen / best | 2 / 4 | 2 / 2 | 3 / 3 | 2 / 3 | 2 / 2 | 2 / 3 |
| offset | all | none | none | none | all | none |
| K=1 vs leaderboard (block-predicted) | -0.09 (90% CI -0.23 to +0.05) | -0.12 (90% CI -0.21 to -0.02) | -0.07 (90% CI -0.16 to +0.02) | -0.10 (90% CI -0.23 to +0.03) | -0.19 (90% CI -0.33 to -0.06) | -0.04 (90% CI -0.14 to +0.05) |
| chosen K vs leaderboard | – | +0.19 (90% CI +0.14 to +0.23) | +0.10 (90% CI +0.04 to +0.16) | +0.06 (90% CI -0.02 to +0.13) | +0.13 (90% CI +0.08 to +0.16) | +0.05 (90% CI -0.02 to +0.11) |
| best K vs leaderboard (selected) | +0.12 (90% CI +0.07 to +0.18) | +0.19 (90% CI +0.14 to +0.23) | +0.10 (90% CI +0.04 to +0.16) | +0.11 (90% CI +0.05 to +0.17) | +0.13 (90% CI +0.08 to +0.16) | +0.09 (90% CI +0.03 to +0.14) |
| best K minus K=1 (dimensionality, selected) | – | +0.31 (90% CI +0.20 to +0.40) | +0.17 (90% CI +0.09 to +0.24) | +0.21 (90% CI +0.09 to +0.30) | +0.31 (90% CI +0.19 to +0.44) | +0.13 (90% CI +0.03 to +0.21) |
| dataset transfer (seen) | -0.06 (90% CI -0.13 to +0.01) | +0.09 (90% CI -0.01 to +0.17) | +0.00 (90% CI -0.09 to +0.07) | +0.04 (90% CI -0.03 to +0.10) | +0.06 (90% CI -0.09 to +0.24) | -0.00 (90% CI -0.08 to +0.07) |
| labels surviving correction | none | domain | none | domain | none | none |
| similarity gate: recoverable in simulation / loadings transfer | no | not run / no | not run / no | not run / no | not run / no | yes / no |
| comparisons with seed-noise score | 0 | 32 | 120 | 146 | 0 | 152 |
| reproducibility groups (strict / loose) | 0 / – | 0 / 4 | 0 / 2 | 0 / 1 | 0 / 3 | 0 / 2 |

Across the 5 v2-code runs: the τ dataset-identity contrast is positive with a 90% interval above 0 in 5; best K beats K = 1 with an interval above 0 in 5 of 5 (range +0.13 to +0.31; selected, so optimistic); the prespecified chosen K beats the leaderboard with an interval above 0 in 3. Runs on main text only have the largest effects but rest on 4 source pairs for the τ test (D1). All runs use the build's 3-start optimiser; see §3 for optimiser dependence.

## 9. Limits

- Single reported scores: the residual mixes stable task-specific interaction with evaluation noise (note Eq. 9); seed-noise scores exist only where seed SDs are printed, and describe one implementation.
- The best-K figures are selected among 12 configurations and are optimistic (D14).
- τ contrasts rest on a median of 4–5 shared GeoFMs per pair and on which GeoFMs happen to be shared; shared evaluation codebases can only be flagged from close values, not identified.
- In single-domain sources, domain-specific capability and implementation effects are not separable (D8).
- Geography and time blocks of Eq. 11 are not fitted: no geography/time metadata, and the evaluation design is not crossed enough to separate them from dataset.
- Points near the ceiling compress differences for classification benchmarks (D4).
- Seed-noise scores come only from papers that print seed SDs, which may be the more careful ones; a printed SD below 0.1 point (e.g. fMoW) makes the score close to 1 by construction.
