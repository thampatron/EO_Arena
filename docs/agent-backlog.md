# Agent backlog

Ordered; the scheduled job takes the first item that is `open` and has no remote `agent/<id>-*` branch. See [`agent-team.md`](agent-team.md). Status values: `open`, `in PR #n`, `done`, `blocked: <reason>`.

## Ready

Items N1–N6 come from the independent spec review of v2.1 (2026-11-04) and go first. All are sensitivity or robustness work: the frozen analysis stays as is, and results are reported next to it.

1. **N1 — Nested selection for the K and offset choice** · `in PR #3`
   The best K (and offset) is chosen among 12 configurations on the same leave-one-paper-out criterion it is scored on (D14). Implement nested selection: for each held-out source, choose offset and K by inner leave-one-paper-out on the training sources only, then score on the held-out source; paired bootstrap over sources vs the leaderboard and vs K = 1. Report next to the selected figures in §3. Also report a bootstrap of the max over the 12 configurations.

2. **N2 — Recalibrate the simulation on an extended grid** · `open`
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

- **P1 — §3 LOPO table column labels swapped** (found in N1). `scripts/dataset_report.py` heads the first K block "anchored K=…" and the second "blocks K=…", but fills the first with `rho_struct` (block-predicted) and the leaderboard column with `rho_board`, the second with `rho_anch` and `rho_half_board`. The numbers are right; the headers are the wrong way round (e.g. the "anchored K=1" cell for `none` is the block-predicted 0.168 that §3's "K = 1 −0.04 vs leaderboard" is computed from). Report-only fix.
- **P2 — Stale comment in `build_dataset_analysis.py` §3** (found in N1). The section comment still calls the plain-leaderboard comparison "conservative toward one ranking", which D9 records as wrong. Comment-only fix.
- **P3 — needs-decision: D9/D14 K rule** (found in N1 review). The frozen rule keeps the smallest K not credibly worse than the best; the note retains a factor only when its predictive benefit exceeds uncertainty. Under nested selection the rule's K minus K = 1 is +0.08 (90% CI −0.01 to +0.15), which the note-style criterion would not retain. Decision for Jordi; no implementation.
