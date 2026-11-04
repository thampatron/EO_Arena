# Agent backlog

Ordered; the scheduled job takes the first item that is `open` and has no open PR. See [`agent-team.md`](agent-team.md). Status values: `open`, `in PR #n`, `done`, `blocked: <reason>`.

## Ready

1. **T1 — Tests and CI for the dataset analysis** · `open`
   `tests/` with pytest: monotone objective of `fit_structured` (with and without the paper × model offset); `fit_heteroskedastic` scale independent of a task's own spread; K = 0/1 recovery on a small synthetic mask; recitation detection (relabelled protocol and benchmark id); `compare_headlines.py` exit codes; `workbook_from_archive.py` round trip on a tiny synthetic archive. A GitHub Actions workflow running the tests on PRs (no workbook needed: synthetic data only).

2. **T2 — Uncertainty for dataset-level outputs** · `open`
   Bootstrap over papers (and models within comparisons) for per-dataset reported separation and LOPO ρ; intervals in `data/dataset_analysis.json` and the §5 table. Flag datasets resting on one comparison of ≤ 5 GeoFMs. Report only; no new point estimates.

3. **T3 — Simulation calibrated to the real data** · `open`
   Estimate signal-to-residual and paper-effect size from the fitted model and rerun the leave-one-paper-out K-selection simulation at those values (K_true 1–4, ≥ 5 seeds each). Replace the fixed SNR grid in the report with the calibrated result, so the claim "K is not identifiable on this evidence" is checked at the real signal level.

4. **T4 — Replicate design from the evidence** · `open`
   Replace `docs/replicate-plan.md` (built on the old provisional scores) with a stage-2 design: which datasets × protocols × GeoFMs × seeds would make σ²_t, cross-paper reproducibility and dataset similarity estimable, chosen to cover the 20 multi-paper datasets and the protocol/sensor blocks with the fewest runs. Include a power calculation from the fitted residual scales. Planning document only.

5. **T5 — Robustness table** · `open`
   Rerun the headline analysis under: leaderboard included; ridge 1 and 10; no paper offset; datasets with ≥ 3 papers only; frozen vs fine-tuned protocols separately. One table in the report showing which findings survive. Sensitivity only: the main analysis stays as frozen.

6. **T6 — Site alignment with the new analysis** · `open`
   `benchmarks.html`: retitle from "Benchmark ranking" to an evidence map, remove verdicts and scores that rest on plug-in seed noise, and show the dataset analysis (evidence base, per-dataset reported separation, LOPO, papers). Move `data/model_profiles.json` out of the published `data/` folder (θ is a nuisance output). Update About/method text. Visual check of the pages at phone and desktop width.

7. **T7 — Geography and time metadata (Eq. 11)** · `open`
   From `data/datasets.json`, `data/footprints.json` and dataset papers, attach region (continent / climate zone) and acquisition period to each dataset; add them to the metadata association test (with blanks as missing and the multiplicity correction). Report whether the design is crossed enough to separate them from dataset.

## Needs a decision before work (do not implement)

- **D1 — Lost main-text results.** Galileo (main Tables 3–5), SatCLIP (main Table 2) and Prithvi-EO-2.0 (main-text GEO-Bench results) print condensed versions of appendix tables the workbook extracted instead. Options: transcribe the main tables from arXiv into `data/extraction/` (published values only), or keep appendix rows that a main table reprints. Changes the evidence base.
- **D2 — GEO-Bench-2 leaderboard in the main analysis** (currently a sensitivity variant only).

## Proposed (added by runs; a maintainer moves items up)
