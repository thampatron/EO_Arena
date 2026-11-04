# Analysis decisions (dataset-level latent-factor analysis, v2.1)

Each decision lists the options, the evidence from the workbook, the choice, its main risk, and the switch that reruns the analysis without it (`scripts/build_dataset_analysis.py`). Spec: *GeoFM Benchmark Scoring* (S. Wang, Oct 2026).

- **v1** = 2026-11-03 (`data/dataset_analysis_v1.json`).
- **v2 / v2.1** = 2026-11-04. The question that drove the revision: did v1's choices make datasets look indistinguishable?
- **v2.1** fixes errors found by the independent spec review of v2. They are listed under *What v2 got wrong*.

Changes the agent team may not make on its own: everything below marked **frozen**. Changing one requires the maintainer's sign-off (a `needs-decision` PR).

## What v2 got wrong (fixed in v2.1)
- **Optimiser.** With a single start from the SVD of the zero-filled matrix, the reweighted one-factor fit converged to a local optimum. Its factor anti-correlated with the general factor (Spearman −0.14 with the naive leaderboard; 52% negative loadings, where only 11% of tasks order GeoFMs against the leaderboard). A leaderboard-seeded start reaches a lower objective (5798.7 vs 5820.6). v2's "K = 1 is credibly worse than a leaderboard" and its offset and K choices rested on that fit. → D17.
- **Simulation.** It had no general factor: a naive leaderboard scored ρ ≈ 0 on simulated data against 0.23 on the real data. So its "the rule picks K = 1 when the truth is 2–3" did not describe this evidence. → D16.
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

## D9 — Number of dimensions K · frozen (rule)
- **Primary criterion: anchored leave-one-paper-out.** Hold out every comparison of a source and refit. For each held-out comparison with ≥ 6 eligible GeoFMs, estimate its loading on the fitted capability vectors from a random half of its GeoFMs, then predict the order of the other half (10 random splits).
  - The one-ranking comparator does exactly the same with the naive leaderboard (each GeoFM's mean within-comparison z-score in the other sources) as a one-dimensional predictor.
  - This tests whether K-dimensional capability vectors beat a single ranking without depending on predicted loadings or their sign.
- **K rule:** the smallest K whose anchored accuracy is not credibly below the best K (paired bootstrap over sources).
- **Secondary, block-predicted:** no information from the held-out comparison. It tests whether what is known about its dataset, protocol and sensor transfers.
- Dataset-level summaries use the best K.

## D10 — Ridge strength 3 for all blocks · frozen
Chosen in v1 (best of 1 / 3 / 10 for every specification). Not re-tuned, to avoid more forking paths with ~27 sources. Robustness to ridge is an agent-backlog item.

## D11 — Seed-noise reliability (note Eq. 3–6) only where a comparison reports its own seed SDs · frozen
- **Applies to:** comparisons with ≥ 6 GeoFMs, of which ≥ 3 print an SD.
- **σ²_t:** median over models of the squared seed SD of one evaluation. Each printed SD is floored at half its last printed digit, because a printed "± 0.1" means only that the SD is at least 0.05.
- **Score:** τ² = τ²_obs − σ²_t / n_reps (3 runs assumed when the paper does not say, with a single-run sensitivity), and score = τ² / (τ² + σ²_t).
- **Interval:** 90% by bootstrap over models. Comparisons are counted by their **lower bound**, not their point estimate.
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

## D16 — Simulations calibrated to the real data · frozen (rule)
- **Truth:** a general factor (every task's loading on factor 1 has a positive mean: a single leaderboard exists) plus mean-zero specific factors. Dataset-shared loadings and paper × model implementation effects are included.
- **Calibration:** a 54-point grid over general-factor strength, signal-to-noise, dataset share and implementation-effect size is fitted to four real-data targets:
  - the naive leaderboard's out-of-paper ρ;
  - τ for different datasets across sources;
  - τ for the same dataset across sources;
  - τ for different datasets within a source.
- The calibrated truth is used to test K recovery under the D9 rule and the cost of each D8 option.

## D17 — Optimiser · frozen
Each structured fit starts from:
- the naive leaderboard (plus leading singular vectors of the residual for K > 1);
- the SVD of the zero-filled matrix;
- four random starts.

It keeps the lowest penalised objective. Multi-start runs on the first reweighting round; later rounds warm-start from the previous solution. At K ≥ 3 different starts reach different optima (K = 4: objectives 1267–1294 from six starts on the full data), so restarts are needed.
