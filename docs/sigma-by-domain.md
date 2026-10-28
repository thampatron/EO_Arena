# What seed noise (σ²) tells us about existing benchmarks, by domain

Analysis of 2026-10-27 on the GeoFM meta-analysis workbook (V. Mancoridis), following *GeoFM Benchmark Scoring* (S. Wang): σ²ₜ is the run-to-run noise of one evaluation (Eq. 1); the score τ²/(τ²+σ²) (Eq. 6) needs it. Imagery comparisons only (paper × benchmark × protocol × metric × fraction, ≥ 4 models). σ of a comparison = √(median over models of the printed per-model seed variance), ≥ 3 models with an SD. Points-scale metrics only for σ in points (156 comparisons).

## 1. Where σ can be measured at all

| Domain | Scored datasets | with measured σ | Comparisons measured |
|---|---|---|---|
| Terrestrial ecosystems | 45 | 17 | 56 / 282 |
| Human systems | 27 | 12 | 50 / 155 |
| Agriculture | 18 | 8 | 36 / 161 |
| Inland water | 7 | 3 | 14 / 54 |
| Atmosphere | 7 | 2 | 4 / 13 |
| Solid Earth | 5 | 4 | 7 / 18 |
| Cryosphere | 5 | 1 | 2 / 17 |
| Oceans and coasts | 3 | **0** | 0 / 17 |
| Disasters | 2 | **0** | 0 / 6 |

Measured noise exists for 23% of imagery comparisons, and comes from 9 papers. Oceans and Disasters have none; Cryosphere rests on one dataset (CaFFe) in one paper. For those domains every score is provisional.

## 2. σ is small and similar across domains

| Domain | Comparisons | Papers | Datasets | σ median (IQR), pts | Spread median, pts | σ / spread |
|---|---|---|---|---|---|---|
| Terrestrial ecosystems | 52 | 7 | 15 | 0.72 (0.51–1.12) | 6.0 | 0.13 |
| Human systems | 48 | 7 | 11 | 0.72 (0.44–1.17) | 6.2 | 0.15 |
| Agriculture | 36 | 6 | 8 | 0.60 (0.43–1.06) | 3.0 | 0.20 |
| Inland water | 14 | 5 | 3 | 0.90 (0.15–1.88) | 6.1 | 0.21 |
| Atmosphere | 4 | 3 | 2 | 0.37 | 3.1 | 0.10 |
| Cryosphere | 2 | 1 | 1 | 1.53 | 4.6 | 0.42 |

Seed noise of one evaluation is typically 0.5–1 point of mIoU/accuracy, about a tenth to a fifth of how far apart published models are. Frozen and fine-tuned evaluations are equally noisy (0.67 vs 0.71). Agriculture has the smallest spread, so the highest relative noise of the large domains.

## 3. σ is a property of the implementation and the dataset, not the domain

Share of the variance in log σ explained:

| Factor | R² |
|---|---|
| Domain | 0.03 |
| Protocol family | 0.01 |
| Task type | 0.01 |
| Metric | 0.33 |
| **Paper** | **0.51** |
| **Dataset** | **0.62** |
| Paper + dataset | 0.73 |
| Domain added to paper | +0.02 |
| Dataset added to paper | +0.22 |

Holding the implementation fixed (GEO-Bench v2 leaderboard: same code, 5 seeds, 17 datasets in 6 domains), σ ranges from 0.2 (SpaceNet 2) to 3.8 points (DynamicEarthNet frozen), with no domain pattern: noisy datasets are DynamicEarthNet (2.6–3.8), So2Sat fine-tuned (1.6), CaFFe (1.4–1.7), Kuro Siwo frozen (1.5), ForestNet fine-tuned (1.2); quiet ones span agriculture, buildings and land cover. σ does not track test-set size (ρ = −0.12) or headroom (ρ = 0.12) within that leaderboard; across papers it correlates with headroom (ρ = 0.45), i.e. the pooled correlation is a paper effect.

**Implication for the note.** σ²ₜ should be estimated per dataset (and implementation), not borrowed from a domain. Domain-level plug-ins carry almost no information; the provisional scores already borrow from the same dataset first.

## 4. σ also differs between models inside one comparison

39% of the variance in log per-model SD is between models within the same comparison. The noisiest model in a comparison is typically 2× the median, 6× at the 90th percentile. Models consistently noisier than their comparison: Satlas S1 Swin-B (1.7×), ScaleMAE ViT-L (1.3×), SoftCon (1.3×), and location encoders (SatCLIP, GeoCLIP ~1.3×). Eq. 1 assumes one σ²ₜ per task; a per-model σ²ₘₜ would fit the evidence better.

## 5. Seed noise is not the main source of disagreement

For the same model on the same benchmark id, protocol and metric reported by two or more papers (62 cells, 17 datasets), the scores differ by a median SD of 2.8 points, against ~0.7 points of seed noise. Where both are available (14 datasets) cross-paper disagreement is a median 1.6× seed noise, and up to 6–12× (NZ cattle, South Africa crop type, NeonTree, Chesapeake). Implementation and protocol choices that the papers do not report move scores more than seeds do. The note's σ²ₜ is therefore a lower bound on what "re-running the benchmark" means across labs; a cross-lab variance term is what separates a reproducible benchmark from a reproducible paper.

## 6. Seeds needed

k ≈ 2(1.96σ/Δ)² runs per model to resolve a gap Δ at ~95%: at the median σ, 3–4 seeds resolve a 1-point gap in Agriculture, Terrestrial and Human systems, ~7 in Inland water, ~18 in Cryosphere (one dataset). The 5-seed (fine-tuned) / 10-seed (frozen) EOArena protocol is adequate for most datasets, not for DynamicEarthNet (σ 2.6–3.8: ~30–55 seeds per 1-point gap).

## Caveats

- 156 comparisons from 9 papers; two papers (GEO-Bench v2, Prithvi-v2) supply 60 of them.
- Printed SDs may be over seeds, folds or initialisations depending on the paper; assumed comparable.
- 283 workbook rows stored percent values as fractions; they were restored before this analysis (earlier today they produced false "σ < 0.1 pt" flags on five datasets).
