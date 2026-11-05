# Analysis decisions (dataset-level latent-factor analysis, v2.1)

Each decision lists the options, the evidence from the workbook, the choice, its main risk, and the switch that reruns the analysis without it (`scripts/build_dataset_analysis.py`). Spec: *GeoFM Benchmark Scoring* (S. Wang, Oct 2026).

- **v1** = 2026-11-03 (`data/dataset_analysis_v1.json`).
- **v2 / v2.1** = 2026-11-04. The question that drove the revision: did v1's choices make datasets look indistinguishable?
- **v2.1** fixes errors found by the independent spec review of v2. They are listed under *What v2 got wrong*.

Changes the agent team may not make on its own: everything below marked **frozen**. Changing one requires the maintainer's sign-off (a `needs-decision` PR).

## What v2 got wrong (fixed in v2.1)
- **Optimiser.** With a single start from the SVD of the zero-filled matrix, the reweighted one-factor fit converged to a local optimum. Its factor anti-correlated with the general factor (Spearman −0.14 with the naive leaderboard; 52% negative loadings, where only 11% of tasks order GeoFMs against the leaderboard). A leaderboard-seeded start reaches a lower objective (5798.7 vs 5820.6). v2's "K = 1 is credibly worse than a leaderboard" and its offset and K choices rested on that fit. → D17.
- **Simulation.** It had no general factor: a naive leaderboard scored ρ ≈ 0 on simulated data against 0.23 on the real data. So its "the rule picks K = 1 when the truth is 2–3" did not describe this evidence. The direction of that under-selection does, however, reappear in the v2.2 calibrated world, which has a general factor (D16). → D16.
- **Dataset transfer.** The block-predicted out-of-paper test found no dataset transfer. A model-free comparison contradicts it: across papers, two comparisons of the same dataset agree more (Kendall τ 0.26) than comparisons of different datasets (0.10). → D15.
- **Within- vs out-of-paper.** v2 compared held-out-cell accuracy with leave-one-paper-out accuracy. That is not like for like: a held-out cell's task loading is estimated from the task's other cells. → D15, using τ across matched pairs.
- **Inclusion slips.**
  - Metric twins printed in separate tables (Infra-Bench) were not recognised.
  - Per-class sub-scores (Better-Together, GeoID-Flood) counted as separate comparisons.
  - Paper-internal objective and input variants (CSP, MeLT-SALT) passed the GeoFM scope.
  - The duplicate rule also collapsed coincident values from genuinely different settings.

## D1 — Which tables count as results: main text and appendix, ablations excluded wherever they are · frozen · switch `--main-text-only`
- **v1:** main-text tables only. The intent was to exclude ablations; location was used as a proxy.
- **Evidence:**
  - Of 4,856 appendix rows, 4,684 are not ablations.
  - Benchmark papers publish their full per-dataset results in appendices: PANGAEA (950 rows), Galileo (908), GeoCross-Bench (840), EarthShift (480), ExE-Bench (308), InfraBench (168).
  - Several main-text tables are condensed versions of these, and the workbook extracted only the appendix version.
  - Among in-scope rows, appendix results are more independent than main-text ones (12% vs 26% self-reported). They also carry most printed seed SDs (1,244 vs 236).
- **Choice:** include appendix tables. Exclude ablations by table-level classification against the arXiv version (`data/table_locations.json`): 83 ablation tables excluded, 53 of them in main text.
- **Risk:** benchmark papers' extended settings multiply comparisons from a few sources. Mitigations:
  - the setting is part of the comparison key;
  - metric twins and sub-scores are collapsed;
  - the τ tests and leave-one-paper-out resample whole sources.
- **Re-examined with the v2.1 main-text-only sensitivity run** (all v2.1 fixes, offset none). Main text alone gives *larger* point estimates: τ dataset identity +0.47 vs +0.15; chosen K vs leaderboard +0.19 vs +0.05; best K minus K = 1 +0.31 vs +0.13; and the domain label survives correction. The decision stands, for three reasons:
  - **Breadth of evidence.** Main text alone has 67 cross-source same-dataset pairs from **4** source pairs (3 positive; sign test p = 0.31). With appendices: 814 pairs from 14 source pairs (11 positive; p = 0.03). The larger estimate rests on too few independent sources to carry a claim.
  - **The gap is overlap, not appendix quality.** Within the full data, the τ contrast rises with the number of GeoFMs a pair shares (+0.15 at ≥ 4, +0.33 at ≥ 5, +0.42 at ≥ 7), and pairs involving appendix tables at ≥ 7 shared GeoFMs show +0.32. Main-text pairs share more GeoFMs (median 7 vs 4); the many low-overlap pairs that appendices add pull the pooled mean toward 0. Appendix rows dilute the point estimate by adding noisy pairs; they do not reverse it.
  - **Seed noise and reproducibility need appendices:** 152 vs 32 comparisons with a seed-noise score (with vs without appendices); 29 vs 27 datasets in ≥ 2 sources.
- The leave-one-paper-out gap (main text +0.19 vs +0.05) is not yet decomposed: it may be that appendix comparisons (low-data fractions, shift settings) are harder to predict for every method, or that they degrade the fit. Scoring the full-data fit on main-text comparisons only separates the two (agent backlog N7).

## D2 — Ablations · frozen
Excluded at three levels:
- ablation-study tables;
- models the registry declares as ablations;
- variant axes that change the model, pretraining or training recipe (the paper's headline setting is kept where known).

## D3 — GEO-Bench-2 leaderboard: included as a source · frozen · switch `--no-leaderboard`
- **Evidence:** 427 in-scope cells, 0% self-reported, all with per-seed values, standardised protocols. Its result folders are different protocols, so each is a separate comparison.
- **Risk:** not peer-reviewed, and one implementation: it contributes to seed-noise reliability, not to cross-implementation reproducibility.

## D4 — Metric scales: regression on a log-error scale · frozen · switch `--no-regression`
- **Transform:** y = −100 ln(err), with err = RMSE (√MSE, MAE, L1, nMAE as reported) and err = √(1−R²) for R². Within a task, R² and RMSE of the same runs differ by a constant that the task mean absorbs (the note's fixed monotone transformation). Negative R² is handled, and seed SDs are carried through by the delta method.
- Bounded classification and segmentation metrics stay in points.
- The residual-scale prior is pooled within each metric family.
- Skill scores (CSI, HSS, POD, FAR) are excluded.
- **Risk:** points near the ceiling compress differences.

## D5 — One measurement counted once · frozen
- **(a) Within-paper duplicates.** An appendix copy of a main-text value is dropped: same model, benchmark, protocol, fraction, metric and value, with the setting label ignored because appendices name the headline setting that main tables leave blank (PANGAEA `joint`). The leaderboard's "best of" setting duplicates `s2_main` and is kept once. Coincident values from different settings in one location are **not** collapsed: they are separate experiments.
- **(b) Metric twins.** One canonical metric per paper × benchmark × protocol × fraction × setting (most GeoFMs, then a fixed priority), including when a paper prints each metric in its own table.
- **(c) Sub-scores.** Per-class sub-scores of a headline result reported in the same paper are dropped (`table_locations.json` → `subscore_tables`, `subscore_benchmarks`).

## D6 — Reprints removed from the citing paper · frozen
- A value reprinted from an earlier paper is one measurement made under the earlier paper's implementation. Matching ignores relabelled protocols and benchmark ids.
- A later paper whose shared cells with an earlier one are mostly identical (≥ 50% of ≥ 3) is treated as reprinting all of them.
- Found: TerraFM ← Copernicus-Bench (32 cells, 100%), TerraFM ← Galileo (66, 95%), AnySat ← PANGAEA (22, 77%), plus single values.
- Keeping reprints in the citing paper's comparison would mix another group's implementation into one paper's protocol and fake reproducibility.

## D7 — GeoFMs only · frozen
- **In scope:** models pretrained on Earth-observation data and offered as reusable representations (`data/model_scope.json`).
- **Out of scope:** random init, ImageNet/CLIP, task architectures, compression priors and paper-internal baselines. With them, v1's out-of-paper predictability was mostly GeoFM-vs-baseline separation.
- **Paper-internal variants** of the introducing paper's own method are also excluded: alternative objectives, input subsets, data fractions, and baselines it trained itself, reported side by side (CSP, MeLT-SALT). They are an ablation in effect even when the registry gives them a GeoFM category. The released or full model is kept.

## D8 — Paper × model implementation offset: chosen by out-of-paper prediction · frozen (rule) · switch `--offset all|multi_domain|none`
- **The problem:** in single-domain sources, domain-specific capability and implementation effects are the same parameter. Neither attribution is identified from single-paper evidence.
- **The rule:** three prespecified options are compared by anchored leave-one-paper-out accuracy (D9), which is neutral between attributions:
  - `all`: an offset for every source;
  - `multi_domain`: only for sources spanning ≥ 2 domains;
  - `none`.
  Pick the option with the highest best-K accuracy.
- A calibrated simulation (D16) reports what each option costs in recovering dataset structure.

## D9 — Number of dimensions K and the one-leaderboard test · frozen (rule)
- **Primary, block-predicted leave-one-paper-out.** Hold out every comparison of a source and refit. Predict each held-out comparison's GeoFM order from its dataset, protocol and sensor blocks and the GeoFMs' capability vectors, using nothing from the comparison itself.
- **Leaderboard comparator:** the plain naive leaderboard (each GeoFM's mean within-comparison z-score in the other sources). It also uses nothing from the comparison. Beating it shows that a dataset- and protocol-aware model predicts better than a fixed ranking. It is **not** a dimensionality test: in calibrated simulation with one true dimension, a one-factor structured model beats the leaderboard (ρ at K = 1 minus leaderboard ρ: +0.15 on average over 5 tables at the v2.2 calibration, range +0.08 to +0.19; +0.28 from one table at v2.1's), because block-predicted loadings learn each dataset's direction and size. (An earlier v2.1 draft called this test "conservative toward one ranking"; that was wrong.)
- **Dimensionality test:** structured K ≥ 2 against structured K = 1, in the same block-predicted family. The best K is selected among 12 configurations on the same criterion it is scored on, so its gains are optimistic. Nested selection (choose offset and K within the training sources) is an agent-backlog item.
- **K rule:** the smallest K whose accuracy is not credibly below the best K (paired bootstrap over sources). The offset option (D8) uses the same criterion.
- **Secondary, anchored.** Estimate the held-out comparison's loading from a random half of its GeoFMs and predict the other half (10 splits), against the plain leaderboard scored on the same half.
- An earlier v2.1 draft compared the anchored model with a leaderboard whose sign was also re-estimated from 3–5 GeoFMs. That comparator scored ρ 0.05 against 0.21 for the plain leaderboard and was replaced before any result was reported.
- Dataset-level summaries use the best K.

## D10 — Ridge strength 3 for all blocks · frozen
Chosen in v1 (best of 1 / 3 / 10 for every specification). Not re-tuned, to avoid more forking paths with ~27 sources. Robustness to ridge is an agent-backlog item.

## D11 — Seed-noise reliability (note Eq. 3–6) only where a comparison reports its own seed SDs · frozen
- **Applies to:** comparisons with ≥ 6 GeoFMs, of which ≥ 3 print an SD.
- **σ²_t:** median over models of the squared seed SD of one evaluation. Each printed SD is floored at half its last printed digit, because a printed "± 0.1" means only that the SD is at least 0.05.
- **Score:** τ² = τ²_obs − σ²_t / n_reps (3 runs assumed when the paper does not say, with a single-run sensitivity), and score = τ² / (τ² + σ²_t).
- **Interval:** 90% by bootstrap over models. Comparisons are counted by their **lower bound**, not their point estimate.
- **Note:** in v2.1 the floor binds on no cell (it is a no-op). Rounding uncertainty in printed SDs is not yet propagated; that is an agent-backlog item.
- **Meaning:** the share of the comparison's model spread that survives re-seeding, for its models and implementation. It is not cross-implementation reproducibility, and it is never computed from borrowed or assumed noise.

## D12 — Cross-source reproducibility at two groupings · frozen
- **Strict:** dataset version × protocol × fraction × metric; ≥ 5 GeoFMs shared, df ≥ 5.
- **Loose:** dataset × protocol family × fraction × metric, versions pooled within source; ≥ 4 shared, df ≥ 3.
- Only headline settings are used, and reprints never count.
- σ_xp is cross-implementation disagreement. Source pairs whose matched values are within a median of 1 point are flagged as possibly sharing an evaluation codebase.

## D13 — Publication gates · frozen
- Dataset-level quantities only for datasets reported by ≥ 2 independent sources.
- Dataset-to-dataset similarity only if (a) simulated recovery on the real mask has median ≥ 0.7, and (b) block-predicted dataset loadings credibly improve out-of-paper prediction for datasets seen in other sources. (a) says the structure would be recoverable if it existed; (b) tests whether the model's estimated loadings capture it.
- No model ranking anywhere.

## D14 — Selection effects
Twelve configurations (3 offsets × 4 K) are compared by the same criterion, so the best one's accuracy is optimistic. The report gives K = 1, the chosen K and the best K, and labels the best-K figure as selected.

## D15 — Model-free tests from pairwise Kendall τ (primary for dataset identity and paper specificity) · frozen
For every pair of comparisons sharing ≥ 4 GeoFMs, compute Kendall τ of their orderings over the shared GeoFMs. Two contrasts:
- **Dataset identity:** τ(same dataset, different sources) − τ(different datasets, different sources). Under one ranking plus task noise it is 0. Also computed per dataset, with each dataset as its own control.
- **Paper specificity:** τ(different datasets, same source) − τ(different datasets, different sources).

90% intervals come from a cluster bootstrap over sources. Each contrast is computed on all pairs, on same-protocol-family pairs, and without source pairs flagged as possible shared codebases. These tests need no model, no optimiser and no transform choice beyond each metric's direction.

Robustness (reproduced by `tau_robustness`): per-source-pair contrasts, a sign test over source pairs, leave-one-source-out range. Post hoc sensitivity: inverse-null-variance weighting of pairs and minimum shared GeoFMs 5 / 6 / 7. The primary estimate keeps pair weighting at ≥ 4 shared GeoFMs; the sensitivity shows it is conservative (larger contrasts at higher overlap, on fewer source pairs).

## D16 — Simulations calibrated to the real data · frozen (rule)
- **Truth:** a general factor (every task's loading on factor 1 has a positive mean: a single leaderboard exists) plus mean-zero specific factors. Dataset-shared loadings and paper × model implementation effects are included (`simulate`; the implementation effect is in units of the noise SD, so the implementation-plus-noise variance is noise² × (1 + effect²)).
- **Targets:** four real-data statistics, each with a 90% interval from a cluster bootstrap over sources (as in D15):
  - the naive leaderboard's out-of-paper ρ;
  - τ for different datasets across sources;
  - τ for the same dataset across sources;
  - τ for different datasets within a source.
- **Calibration (v2.2, 2026-11-05, agent backlog N2; replaces v2.1's 54-point grid).** K_true = 2. Misfit = Σ ((simulated mean − real) / bootstrap SE)², so less precisely measured targets count less. Two stages:
  - coarse: 720 points over general-factor mean 0.2–1.0, SNR 0.5–16, dataset share 0.5–1.0 and implementation effect 0–3 noise SD, each point averaged over the same 8 seeds;
  - fine: 375–625 points around the best point (16 seeds), re-centred while the best point sits on a fine-grid edge that is not a bound of the parameter (3 rounds; 2,345 points in all);
  - the chosen point is then re-simulated on 20 fresh seeds, and inside / outside is judged on those.
- **Result.** Chosen: general-factor mean 0.7, SNR 2.38, dataset share 0.8, implementation effect 0.875 noise SD. It is strictly inside the coarse grid's range on every parameter and on no edge of the last fine round. All four targets are inside their intervals (fresh seeds, mean ± seed SD): leaderboard ρ 0.251 ± 0.091 (real 0.209, 0.121–0.310); τ different datasets across sources 0.089 ± 0.056 (0.093, −0.003–0.220); τ same dataset across sources 0.248 ± 0.094 (0.240, 0.084–0.617); τ different datasets within a source 0.248 ± 0.034 (0.263, 0.163–0.353). v2.1's under-matched within-source τ (0.12) is consistent with too small an implementation effect (v2.1's grid stopped at 0.5 noise SD); SNR is not pinned down by the targets (fitting points span 0.5–16).
- **K recovery under the D9 rule (5 tables per K_true).** Selected K = K_true in 5/5 tables for K_true = 1, 1/5 for 2, 2/5 for 3 and 1/5 for 4. In this simulated world the rule never chose more dimensions than the truth (0 of 15 tables where that was possible) and chose fewer in 11 of 15. The unpenalised best K exceeded the truth in 5 of 15 tables where it could (2/5 at K_true = 1, 2/5 at K_true = 2, 1/5 at K_true = 3), which bears on the real best K = 3 (already labelled as selected, D14). Part of the under-selection is built into the design: `simulate` scales every factor's random loadings by 1/√K_true, so each extra factor is weaker at higher K_true. With 5 tables per K_true, at one of many equally fitting parameter points, in a world easier to predict than the real one, this does not make the real chosen K a lower bound. K recovery runs under offset `none` (the real choice) only, does not replay the selection among 12 configurations (D14), and worlds with K_true ≠ 2 are not separately calibrated. v2.1's "recovers K = 1, 2, 3" came from one table per K_true in an easier world and does not hold here.
- **Offset cost (D8, 5 tables, K_true = K = 2).** `all` and `multi_domain` recover dataset geometry for ≥ 2-source datasets with medians 0.80 and 0.81; `none`, the option chosen on the real data, gives 0.67 and slightly lower out-of-paper ρ (0.41 vs 0.44–0.45).
- **How D13 gate (a) is computed (v2.2).** The simulated recovery median is taken over the 5 offset-cost tables under the offset chosen on the real data (`none`); in v2.1 it was a single table. D13 itself is unchanged; pinning the number of tables and the offset for gate (a) is a decision for the maintainer (backlog P-N2d).
- **Gate (a) is borderline and unresolved:** median 0.669 over 5 tables (range 0.59–0.89), below 0.7; 0.80 / 0.81 under the `all` / `multi_domain` offsets; at one of many acceptable calibration points (v2.1: 0.716 from one table at the old calibration). Gate (b) — dataset loadings do not credibly transfer out of paper — is the operative reason similarity is not published, before and after this change. More tables and calibration points: backlog P-N2b.
- **Limits.**
  - The four targets do not identify the four parameters. 58 of the 720 coarse points put all four simulated means inside the intervals, spanning general-factor mean 0.4–1.0, SNR 0.5–16, dataset share 0.5–1.0 and implementation effect 0.5–2. The results above hold at the chosen point, not across that region.
  - Each statistic varies a lot between simulated tables (seed SD up to 0.09; largest for τ same dataset across sources, 0.094, then the leaderboard ρ, 0.091). The chosen point's misfit (0.05) is within that noise, so neighbouring points fit as well, and the count of 58 coarse points inside the intervals is itself noisy (8 tables per point).
  - The leaderboard target's interval is approximate: the cluster bootstrap resamples held-out sources but does not refit the leaderboard on each resample.
  - The simulated world is still easier for the structured model. This is a diagnostic, not a target: out-of-paper structured ρ at K_true = 2 is 0.37–0.39 for K = 1–4, against 0.17–0.30 on the real data. Simulated dataset loadings also transfer out of paper (dataset gain +0.13 to +0.15), where real ones do not (−0.00).
  - So K recovery here checks the rule in a world that matches four summary statistics of these data. It does not identify K on the real data.
- The sensitivity runs (`data/dataset_analysis_sens_*.json`) skip the simulation (`--skip-sim`), so they are unaffected.

## D17 — Optimiser · frozen
Each structured fit starts from:
- the naive leaderboard (plus leading singular vectors of the residual for K > 1);
- the SVD of the zero-filled matrix;
- four random starts.

It keeps the lowest penalised objective. Multi-start runs on the first reweighting round; later rounds warm-start from the previous solution, which the review checked does not reintroduce a bad optimum. **As run in v2.1, leave-one-paper-out fits use 1 random start (3 starts in all) and final fits use 3.** At K ≥ 3 different starts reach different optima (K = 4: objectives 1267–1294 from six starts on the full data), so the "K = 4 worse than K = 3" comparison may partly be an optimiser artefact. Raising restarts for K ≥ 3 is an agent-backlog item.
