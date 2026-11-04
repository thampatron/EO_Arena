# Analysis decisions (dataset-level latent-factor analysis, v2)

Each decision lists the options, the evidence from the workbook, the choice, its main risk, and the switch that reruns the analysis without it (`scripts/build_dataset_analysis.py`). Spec: *GeoFM Benchmark Scoring* (S. Wang, Oct 2026). v1 = the analysis of 2026-11-03 (`data/dataset_analysis_v1.json`); v2 = this revision (2026-11-04). The question that drove the revision: did v1's choices make datasets look indistinguishable?

Changes the agent team may not make on its own: everything below marked **frozen**. Changing one requires the maintainer's sign-off (a `needs-decision` PR).

## D1 — Which tables count as results: main text and appendix, ablations excluded wherever they are · frozen · switch `--main-text-only`
- **v1:** main-text tables only. The intent was to exclude ablations; location was used as a proxy.
- **Evidence:** of 4,856 appendix rows, 4,684 are not ablations. Benchmark papers publish their full per-dataset results in appendices: PANGAEA (950 rows), Galileo (908), GeoCross-Bench (840), EarthShift (480), ExE-Bench (308) and InfraBench (168). Several main-text tables are condensed versions of these, and the workbook extracted only the appendix version (Galileo, SatCLIP, Prithvi-EO-2.0). Among in-scope rows, appendix results are *more* independent than main-text ones: 12% are self-reported vs 26% in main text. They also carry most of the printed seed SDs: 1,244 vs 236.
- **Choice:** include appendix tables. Exclude ablations by table-level classification instead of page location: all 298 source tables were checked against the arXiv version or classified by rule (`data/table_locations.json`), and 83 ablation tables were excluded (53 of them in main text).
- **Risk:** appendix tables add extended settings (label fractions, input modalities), multiplying comparisons per paper. Mitigation: the setting is part of the comparison key, the paper × model offset absorbs paper-wide model effects, and leave-one-paper-out resamples whole papers.

## D2 — Ablations · frozen
Excluded at three levels: ablation-study tables, models the registry declares as ablations, and variant axes that change the model, pretraining or training recipe. Where a paper's headline setting is known it is kept. Unchanged from v1, except that coverage is now complete.

## D3 — GEO-Bench-2 leaderboard: included as a source · frozen · switch `--no-leaderboard`
- **v1:** excluded as "not a paper's main text".
- **Evidence:** 427 in-scope cells, 0% self-reported, every cell with per-seed values, one standardised protocol. Its three result folders overlap on 75 keys and only 5 are identical, so they are separate runs: each folder is a separate comparison within one source.
- **Choice:** include it. It is the most independent and best-replicated evidence available, and it is the only source of measured seed noise for many GEO-Bench-2 datasets.
- **Risk:** it is not peer-reviewed. It is one implementation, so it contributes to seed-noise reliability but not to cross-implementation reproducibility.

## D4 — Metric scales: regression tasks included on a log-error scale · frozen · switch `--no-regression`
- **v1:** R² and error metrics excluded (R² is unbounded below; RMSE has units).
- **Evidence:** this removed 1,037 main-text rows across 40 datasets, mostly regression tasks (atmosphere, solid Earth, biomass). These are the tasks most likely to need a capability that classification benchmarks don't measure.
- **Choice:** y = −100 ln(err), with err = RMSE (√MSE, MAE, L1 or nMAE as reported) and err = √(1−R²) for R². This is the note's "fixed monotone transformation": within a task, R² and RMSE of the same runs differ only by a constant, which the task mean absorbs. Relative error changes are comparable across units, and negative R² is handled. Seed SDs are carried through by the delta method. Bounded classification and segmentation metrics stay in points.
- Each task has its own mean and residual scale, so the two families sit in one model. The residual-scale prior is pooled within each family, not across them.
- Precipitation skill scores (CSI, HSS, POD, FAR) stay out: they are bounded but not comparable, and they come from one paper.
- **Risk:** points near the ceiling (EuroSAT ≈ 99%) compress differences; a logit or log-error transform for classification is a candidate sensitivity.

## D5 — Within-paper duplicates removed · frozen
An appendix table that repeats a main-text value is one measurement: same paper, model, benchmark, protocol, fraction, metric and value. Appendices often name the headline setting that main tables leave blank (PANGAEA's `joint`), so the setting label is ignored when matching. Main text wins. 83 rows removed.

## D6 — Reprints removed from the citing paper · frozen
A value reprinted from an earlier paper is one measurement made under the earlier paper's implementation. Matching ignores relabelled protocols and benchmark ids. A later paper whose shared cells with an earlier one are mostly identical (≥ 50% of ≥ 3) is treated as reprinting all of them. Found: TerraFM ← Copernicus-Bench (32 cells, 100% identical), TerraFM ← Galileo (66 cells, 95%), plus scattered single values.
- **Alternative considered:** keep reprinted values in the citing paper's comparison. Rejected: that mixes another group's implementation into what the model treats as one paper's protocol, and counts the measurement twice, which fakes reproducibility.

## D7 — GeoFMs only · frozen
Models pretrained on Earth-observation data and offered as reusable representations (`data/model_scope.json`). Random init, ImageNet/CLIP, task architectures, compression priors and paper-internal baselines are excluded. With baselines in v1, out-of-paper predictability was ρ ≈ 0.36, and most of it was GeoFM-vs-baseline separation: a trivial dominant factor that hides the differences between GeoFMs the paper is about. The note's baseline-relative transform is unnecessary because each task's mean absorbs its level.

## D8 — Paper × model implementation offset: chosen by out-of-paper prediction · frozen (rule) · switch `--offset all|multi_domain|none`
- **Why it exists:** v1 simulation showed that without it, held-out-cell selection over-selects K (true 1 → 2, 2 → 3). How a paper ran a model gets read as an extra capability.
- **Why it is a problem:** 9 of 28 sources cover a single domain. There, "this model is good at cryosphere" and "this paper's setup favours this model" are the same parameter. With the offset the variation is attributed to implementation; without it, to capability. Neither is identified from single-paper evidence.
- **Choice:** treat it as an empirical question about generalisation. Three prespecified options are compared by leave-one-paper-out accuracy (the held-out paper has no offset, so the test is neutral between attributions):
  - `all`: an offset for every source;
  - `multi_domain`: only for sources spanning ≥ 2 domains;
  - `none`.
  The rule: pick the option with the highest best-K accuracy. A simulation on the real mask with true dataset-specific signal measures what each option costs, with and without implementation effects. Results are in `data/dataset_analysis.json` → `offset`, `simulation_offset`.

## D9 — Number of dimensions K · frozen (rule)
Chosen by leave-one-paper-out with a paired bootstrap over sources: the smallest K not credibly worse than the best. Simulation shows this rule is conservative on this mask, so K is reported as a **floor**. Dataset-level summaries use the best K: they describe structure, and the conservative K would understate it.

## D10 — Ridge strength 3 for all blocks · frozen
Chosen in v1 (best of 1 / 3 / 10 for every specification) and deliberately not re-tuned, to avoid more forking paths with ~28 sources. Robustness to ridge is an agent-backlog item.

## D11 — Seed-noise reliability (note Eq. 3–6) only where a comparison reports its own seed SDs · frozen
- **v1:** none computed. With main-text-only and no leaderboard there were too few SDs, and borrowing noise from other datasets was rejected.
- **v2:** for each comparison with ≥ 3 models reporting an SD:
  - σ²_t = median over models of the squared seed SD of one evaluation;
  - τ² = τ²_obs − σ²_t / n_reps (reported values are means of n_reps seeds; 3 assumed when the paper does not say, with a single-run sensitivity);
  - score = τ² / (τ² + σ²_t), with a 90% interval by bootstrap over models.
- It is the share of the comparison's model spread that survives re-seeding, **for that comparison's models and implementation**. It is not cross-implementation reproducibility and not a property of the dataset alone.
- **Never** computed from borrowed or assumed noise.

## D12 — Cross-source reproducibility at two groupings · frozen
- **Strict:** dataset version × protocol × fraction × metric; ≥ 5 GeoFMs shared, df ≥ 5.
- **Loose:** dataset × protocol family × fraction × metric, versions pooled within a source; ≥ 4 GeoFMs shared, df ≥ 3. Coarser, and labelled as cross-source disagreement, which includes version differences.
- Only headline settings are used. Reprints never count. σ_xp is cross-implementation disagreement, not seed noise.

## D13 — Publication gates · frozen
- Dataset-level quantities only for datasets reported by ≥ 2 independent sources.
- Dataset-to-dataset similarity only if simulated recovery on the real mask (chosen offset) has median ≥ 0.7.
- No model ranking anywhere.

## D14 — Selection effects
Twelve configurations (3 offsets × 4 K) are compared by the same leave-one-paper-out criterion, so the best one's accuracy is optimistic. The report gives:
- the K = 1 comparison (one leaderboard);
- the chosen-K gain, which is conservative;
- the best-K gain, which is optimistic;
- and labels the best-K figure as selected.
