# Agent backlog

Ordered; the scheduled job takes the first item that is `open` and has no remote `agent/<id>-*` branch. See [`agent-team.md`](agent-team.md). Status values: `open`, `in PR #n`, `done`, `blocked: <reason>`.

## Ready

Items N1–N6 come from the independent spec review of v2.1 (2026-11-04) and go first. All are sensitivity or robustness work: the frozen analysis stays as is, and results are reported next to it.

1. **N1 — Nested selection for the K and offset choice** · `open`
   The best K (and offset) is chosen among 12 configurations on the same leave-one-paper-out criterion it is scored on (D14). Implement nested selection: for each held-out source, choose offset and K by inner leave-one-paper-out on the training sources only, then score on the held-out source; paired bootstrap over sources vs the leaderboard and vs K = 1. Report next to the selected figures in §3. Also report a bootstrap of the max over the 12 configurations.

2. **N2 — Recalibrate the simulation on an extended grid** · `in PR`
   v2.1 calibration hits grid edges and under-matches within-source τ (0.12 simulated vs 0.26 real). Extend the grid (larger paper × model effects, lower SNR, finer general-factor strength) until all four targets (board ρ, τ cells) are within their bootstrap intervals or the misfit is documented. Rerun the K-recovery and offset-cost simulations at the new calibration (K_true 1–4, ≥ 5 seeds). Update D16 text.

3. **N3 — Optimiser restarts at K ≥ 3** · `open`
   Leave-one-paper-out fits use 3 starts. Rerun the K = 3 vs K = 4 comparison with ≥ 8 random starts (and report the spread of objectives per fold). If K = 4 is no longer credibly worse, say so in §3 and D17.

4. **N4 — Rounding uncertainty in seed-noise Eq. 6** · `open`
   Printed SDs carry rounding error. Propagate it: for each printed SD s with last digit d, draw the true SD uniformly in [max(s − d/2, d/4), s + d/2] inside the model bootstrap. Report how the counts of comparisons with lower bound ≥ 0.8 / ≥ 0.5 change.

5. **N5 — Shared-codebase flags from paper metadata** · `open`
   The τ dataset-identity evidence may partly reflect shared evaluation code (GEO-Bench / PANGAEA toolkits). From the papers (code links, "we use the X benchmark code"), record per source which evaluation toolkit it used, in `data/` (published facts only). Rerun the τ contrasts within and across toolkit groups.

6. **N6 — Seed-noise dependence** · `open`
   Comparisons from one paper share settings. Report seed-noise Eq. 6 counts aggregated per dataset × protocol and per source (one vote per source), alongside the per-comparison counts.

7. **N7 — Decompose the main-text vs full-data gap in leave-one-paper-out** · `open`
   Main text alone gives chosen K vs leaderboard +0.19 against +0.05 with appendices (D1). Score the full-data leave-one-paper-out predictions on main-text comparisons only, and on appendix comparisons only, for structured K = 1..4 and the leaderboard. If main-text comparisons score like the main-text-only run, appendix comparisons are simply harder to predict (keep D1); if not, appendix comparisons degrade the fit (open a `needs-decision` PR with the evidence). Also break the appendix comparisons down by setting (training fraction < 100%, shift settings).

8. **T1 — Tests and CI for the dataset analysis** · `open`
   `tests/` with pytest: monotone objective of `fit_structured` (with and without the paper × model offset); multi-start keeps the lowest objective and includes the leaderboard start; `fit_heteroskedastic` scale independent of a task's own spread; K = 1 recovery on a small synthetic mask with a general factor; τ contrasts equal 0 in expectation under one ranking plus noise; recitation detection (relabelled protocol and benchmark id); `compare_headlines.py` exit codes; `workbook_from_archive.py` round trip on a tiny synthetic archive. A GitHub Actions workflow running the tests on PRs (no workbook needed: synthetic data only).

9. **T2 — Uncertainty for dataset-level outputs** · `open`
   Bootstrap over sources (and models within comparisons) for the per-dataset τ contrasts and per-dataset outputs in §5; intervals in `data/dataset_analysis.json` and the §5 table. Flag datasets resting on one comparison of ≤ 5 GeoFMs. Report only.

10. **T4 — Replicate design from the evidence** · `open`
   Replace `docs/replicate-plan.md` with a stage-2 design: which datasets × protocols × GeoFMs × seeds × independent implementations would make σ²_t, cross-source reproducibility and dataset similarity estimable, chosen to cover the multi-source datasets outside the GEO-Bench family and the protocol/sensor blocks with the fewest runs. Power calculation from the fitted residual scales and the τ contrasts. Planning document only.

11. **T5 — Robustness table, remaining variants** · `open`
    v2.1 has sensitivity runs for main-text-only, no leaderboard, no regression and all v1 decisions. Add: ridge 1 and 10; datasets with ≥ 3 sources only; frozen vs fine-tuned protocols separately. Extend the report's sensitivity table. Sensitivity only.

12. **T6 — Site alignment with the new analysis** · `open`
    `benchmarks.html`: retitle from "Benchmark ranking" to an evidence map, remove verdicts and scores that rest on plug-in seed noise, and show the dataset analysis (evidence base, τ dataset-identity per dataset, seed-noise lower bounds where measured, sources). No model ranking. Update About/method text. Visual check at phone and desktop width.

13. **T7 — Geography and time metadata (Eq. 11)** · `open`
    From `data/datasets.json`, `data/footprints.json` and dataset papers, attach region (continent / climate zone) and acquisition period to each dataset; add them to the metadata association test (blanks as missing, multiplicity correction updated). Report whether the design is crossed enough to separate them from dataset.

Done in the v2 / v2.1 revision: T3 (calibrated simulation — refinement is N2), most of T5.

## Needs a decision before work (do not implement)

- **D1 — Lost main-text results** (partly moot since v2 includes non-ablation appendix tables; still open for papers whose main table is not a subset of the appendix). Galileo (main Tables 3–5), SatCLIP (main Table 2) and Prithvi-EO-2.0 (main-text GEO-Bench results) print condensed versions of appendix tables the workbook extracted instead. Options: transcribe the main tables from arXiv into `data/extraction/` (published values only), or keep appendix rows that a main table reprints. Changes the evidence base.
- ~~D2 — GEO-Bench-2 leaderboard in the main analysis~~ — decided 2026-11-04: included (D3); `--no-leaderboard` is the sensitivity variant.

## Proposed (added by runs; a maintainer moves items up)
- **P-N2a — A fifth calibration target for D16** (from N2). The four targets do not identify the four simulation parameters: 58 of 720 coarse points fit all four, across most of the grid. The calibrated world is still easier than the real one (structured out-of-paper ρ 0.37–0.39 vs 0.17–0.30; dataset loadings transfer in simulation, +0.13, but not in the real data, −0.00). Candidates: the unused τ cell (same dataset, same source; 0.45), the real structured ρ at K = 1, or the real dataset-transfer gain. Changes the D16 calibration, not the rule.
- **P-N2b — K recovery across the acceptable calibration region** (from N2). The N2 K-recovery check runs at one point, with 5 tables per K_true, and the rule picked fewer dimensions than the truth in 11 of 11 misses. Repeat at 3–5 points spanning the region where all targets fit, with ≥ 10 tables per K_true, to see whether the under-selection is robust. The D13 gate (a) median (0.669 vs threshold 0.7) also needs more tables to settle.
- **P-N2c — Build time** (from N2). The full build now takes ~3.6 h on 2 cores (≈ 13,100 s), up from ~35 min. The 95 simulated leave-one-paper-out fits for K recovery and offset cost (≈ 2.8 h) dominate it. A `--sim-seeds N` switch or caching the simulation section by calibration and code hash would keep verifier reruns practical.
- **P-N2d — needs-decision: pin how D13 gate (a) is computed** (from N2 review). Since N2 the gate uses the median over the 5 offset-cost tables under the offset chosen on the real data. That choice decides the outcome: the median is 0.669 under `none` but 0.80 / 0.81 under `all` / `multi_domain`, and the per-table values range 0.59–0.89 around the 0.7 threshold. The maintainer should fix the number of tables and the offset (or whether to pool offsets) before more tables are run (P-N2b). D13 text is unchanged.
- **P-N2e — Move the calibration grid helpers into the module, and handle single-source tables** (from N2 review). `_fine_axes` and `_edge_names` live in `build_dataset_analysis.py` and are untested; moving them changes the build script, which the review round did not allow without a rebuild. `calibration_target_intervals` raises on a table with one source (empty cross-source cells give empty bootstrap lists) instead of returning zero-width or missing intervals; an xfail test documents it.
