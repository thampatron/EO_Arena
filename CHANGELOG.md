# Changelog

## v0.3 — 2026-10-27

Benchmark scoring rebuilt on the lab's note *GeoFM Benchmark Scoring* (S. Wang, Oct 2026).

- **Scoring.** Per comparison: observed separation τ²_obs, replicate noise σ² from printed seed SDs and per-seed leaderboard values, τ² = τ²_obs − σ²/n (n = replicates behind each reported mean), EDI = τ²/σ², score = τ²/(τ²+σ²) with bootstrap intervals; plug-in noise marked provisional. Frontier score on the leading half of each comparison. Replaces headroom, ρ-vs-consensus and the distinct/redundant verdicts.
- **Latent-factor regression** (alternating ridge least squares, K = 3 by held-out CV and bootstrap stability): dataset-specific signal, redundancy-adjusted info share, model capability profiles θ, residual-correlation test of the diagonal-Ψ assumption.
- **Variants.** Every dataset and dataset × protocol family is scored under σ² median/mean × self-reported kept/dropped; latent diagnostics under ridge 10/3. An *Analysis settings* strip switches the pages between them.
- **Pages.** Benchmark ranking rewritten (new columns, per-comparison detail, (i) definitions on every metric); new Evidence map (per-domain scatter plots); Model ranking opens on capability profiles with the z-score ranking as a second view; Explorer evidence panel leads with the score.
- **Data.** `data/evidence.json` new schema; `data/model_profiles.json`, `data/replicate_plan.json`, `data/benchmark_map.csv` added. `scripts/geofm_scoring.py` holds the statistics; `scripts/build_evidence.py` rebuilds everything from the workbook (fits cached in `scripts/.cache`).
- **Docs.** `docs/replicate-plan.md` (where measured noise is missing), `docs/benchmark-map-review.md` (mapping judgement calls).

## v0.2 — 2026-10-14

Benchmark ranking and model ranking from the meta-analysis workbook (descriptive: models, papers, spread, headroom, ρ vs consensus, within-comparison z-scores); sample-location map view; GeoFM evidence summaries in the Explorer.

## v0.1 — 2026-09

Task taxonomy, explorer, domains, sensors, task template v0.2 and the five task specifications.
