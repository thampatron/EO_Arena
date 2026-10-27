# EOArena user study — Ben (2nd-year ML PhD, multi-sensor S1/S2/NAIP GeoFM, NeurIPS D&B eval section)

Session: ~1 hour, Chromium 1400x900 (one pass at 1280x800). Order: Explorer -> Benchmark ranking -> (i) popovers -> Analysis settings -> Model ranking (both views) -> Evidence map -> About -> dataset drawers -> Tasks -> Domains. Screenshots/dumps in /home/claude/analysis/study_ben/.

## 1. Answers

### Q1 Suite (8-10 benchmarks, reliable + non-redundant)
Used: Benchmark ranking (default settings) columns Verdict, Papers, Frontier score, Info share, Seed noise, plus the "Benchmarks" (suite membership) list in each dataset drawer. Ignored the default sort (verdict -> EDI) because it ranks single-paper, "not in inventory", model-derived-label regression tasks first (MMEarth-Bench SOC, WorldClim Bioclim, GRIP4, MOSAIKS: 1 paper, 1-2 comparisons, 50-64% self-reported). My filter: Reliable (measured noise), >=3 papers, frontier >= ~0.65, sensor I support; then de-duplicated by task family x sensor by hand.

| Benchmark | Score (90% CI) | Frontier | Papers/models | Seed noise | Info share |
|---|---|---|---|---|---|
| PASTIS / PASTIS-R | 0.96 (0.92-0.96) | 0.88 | 8/72 | 1.14 | 8.1% |
| So2Sat LCZ42 | 0.92 (0.82-0.91) | 0.65 | 13/83 | 1.14 | 6.2% |
| EuroSAT | 0.86 (0.84-0.86) | 0.78 | 16/97 | 0.87 | 5.7% |
| BigEarthNet v1/v2 | 0.87 (0.81-0.87) | 0.70 | 18/110 | 1.46 | 4.2% |
| HLS Burn Scars | 0.94 (0.87-0.94) | 0.54 | 6/39 | 0.73 | 4.2% |
| South Africa crop type | 0.95 (0.91-0.95) | 0.79 | 9/69 | 0.63 | 3.5% |
| Cashew plantation | 0.90 (0.86-0.90) | 0.78 | 9/69 | 2.20 | 3.1% |
| SpaceNet 7 | 0.93 (0.89-0.94) | 0.82 | 3/29 | 0.64 | 1.3% |
| TreeSatAI (aerial+S1+S2) | 0.92 (0.85-0.92) | 0.72 | 4/36 | 0.70 | 1.2% |
| CloudSEN12 | 0.97 (0.89-0.98) | 0.89 | 3/24 | 0.44 | 0.3% |

Excluded: Sen1Floods11 (Moderate 0.54, frontier 0.28, yet 6.5% info share and an EOArena launch task), DynamicEarthNet (0.26; sigma 3.52 ~ spread 3.58), fMoW (1.00 but sigma 0.03 pts, 45% self-reported), Kuro Siwo (0.99 full / 0.17 frontier), PV4GER (0.89 / 0.28), Brick kilns (0.79).
Confidence: medium on reliable/unreliable split; low on the non-redundancy part (Info share tracks number of comparisons; Dataset-specific changes 2-8x between ridge 10 and ridge 3).

### Q2 Baselines
Profile view "General (independent)": croma_vitl +0.17, croma_vitb +0.14, softcon +0.11, spectralgpt +0.10, terramind_v1b/dofa_vitb/terramind_v1l +0.10, olmoearth_v1_base/galileo_base +0.07. Z-score view of the same page: skysense +0.73, olmoearth_v1_base +0.70, gfm_swin_swint +0.70, convnext_l_imagenet +0.69, convnext_xl_imagenet +0.68, dinov2_vitb +0.65, clay_vitb +0.61; croma_vitl #13, croma_vitb #32, dofa_vitb #28; "5 of 10 top-10 are general-vision".
My set (robust to the view, many independent evals): CROMA ViT-L, TerraMind v1 B/L, DOFA ViT-B, SoftCon, SpectralGPT, OlmoEarth v1 base, Galileo base, plus DINOv2 ViT-B and ImageNet ConvNeXt-L as controls; AlphaEarth if runnable (mean z +0.89 on 42 tasks). Confidence: medium-high on the set, low on the order (General spans -0.22..+0.17, ~20 models within +-0.03, no CI; views dated 2026-10-27 vs 2026-10-08 with different counts).

### Q3 Seeds
Not answered where I looked (ranking, About). Pieces: Tasks page: EOArena protocol = 10 runs frozen-decoder, 5 runs fine-tune, ties when 0.25<P(A>B)<0.75. Replicates popover/About: papers printing seeds use 5 (GEO-Bench v2, EarthShift, GeoCrossBench, TESSERA) or 10 (Prithvi-v2); unstated assumed 3; replicate plan re-runs at 5 seeds. Seed noise column lets me compute k ~ 2(2 sigma/Delta)^2: sigma ~1 pt (PASTIS, So2Sat, EuroSAT) -> ~8 seeds per 1-pt gap; Cashew sigma 2.2 -> ~10 seeds for a 2-pt gap. Decision: 5 seeds fine-tuned, 10 frozen. Confidence medium; the site scatters this over three pages and a popover.

## 2. Timeline (expected X / saw Y)
- Explorer: expected a "building a suite? start here"; saw a 14-facet catalogue. "Reliable" badges unexplained. "GeoFM evidence" is the last facet.
- Benchmark ranking: first 900px is title + 6 tiles + 7-item legend + settings strip + filters; table below the fold. Tiles say 192 benchmarks vs Explorer 118/54; took ~45 min to reconcile (138 of 192 "not in inventory", badge never explained). Ranks skip (1,2,4,7,9...) because "Imagery tasks only" hides rows but keeps global ranks; I assumed a bug.
- Table: 15 columns; at 1400px EDI, Dataset-specific, Info share, Self-reported, Verdict are off-screen; at 1280px Frontier too. Verdict (what the legend explains) is the last column. Scrolling right loses the name column, scrolling down loses the header. Order I needed: Benchmark, Verdict, Score, Frontier, Papers, Models, Seed noise, Info share.
- (i) popovers: best part of the site; formulas given. Unhelpful bits: "Eq. 6", "Definitions follow S. Wang, GeoFM Benchmark Scoring (Oct 2026)" and script paths I cannot open. Header renders "Models ⇅ i ⇅" so I hit sort before info.
- Analysis settings: frontier headline re-ranks everything and changes tiles 51 reliable/18 below 0.8 -> 26/60 (Kuro Siwo 0.99->0.17, PV4GER 0.89->0.28, HLS Burn Scars 0.94->0.54). Self-reported dropped: 192->184, fMoW leaves top, CropHarvest 0.86->0.97, some Reliable rows now have 4 models. Unit = protocol family: 261 rows, "fMoW · frozen" etc., tiles not comparable. Seed noise mean: fMoW sigma 0.03->0.15, EDI 12,964->471. Ridge 3: Score unchanged but Dataset-specific/Info share change everywhere. Settings follow to Evidence map via storage, URL param dropped; no strip on Model ranking.
- Model ranking: needed the "How to read it" block that sits below 91 rows. croma_vitb #2 by General but Mean z +0.20 vs alphaearth #15 with Mean z +0.89. "nan" backbones; "vit_b (size not stated verbatim; inferred from <100M param restriction)" in a cell; theta3 = +6.39 (dofa) / -5.08 (anysat) with Cov(theta)=I.
- Evidence map: default X=Score has no resolution (everything at 0.85-1.0). Legend swatches render as ~440px circles (inline svg without width/height); page 11,520px tall. Tiles 155/104/47 vs ranking 192/57. Labels overlap.
- About: real method section (tau2obs - sigma2/n, n assumed 3, provisional n=1, 18 papers print SDs = 187 of 825 comparisons, residual check 0.35 vs null 0.30). Contradictions: "averaged over models" vs median default; 13 vs 14 filters; "written into the URL". Mentions docs/replicate-plan.md with no link.
- Dataset drawer (two clicks from ranking via index.html?q=...): best single view - verdict, CI, replicates per value, suites, sensors, licence, plain-English summary. Replicates show "2 (assumed)", "4 (assumed)", "1 (assumed)" while popover says assumed = 3.
- Tasks: 10/5 runs, P(A>B) ties, EOArena's 5 launch tasks incl. Sen1Floods11.
- Domains: "Saturated" = many suites; on ranking "Weak / saturated" = noise >= spread.

## 3. Three changes
1. Ranking table first screen: Benchmark (sticky) · Verdict · Score (CI) · Frontier · Papers · Models · Seed noise · Replicates · In suites · Info share · Sensors. Drop Domain, Comparisons, Spread, EDI (sort option only), Dataset-specific, Self-reported from the default. Sticky header; collapse legend into Verdict popover; default sort Verdict, Papers desc, Frontier; renumber after filtering; explain "not in inventory" in the intro. First sentence: "Which published benchmarks can tell strong GeoFMs apart, and which are redundant? Reliable = >=80% of model spread survives measured seed noise; Frontier = same test among the top half; In suites = who already uses it."
2. A "Reproducibility" box on the ranking + About: seeds used by papers (5/10), EOArena's 10 frozen / 5 fine-tune, P(A>B) tie rule, and k ~ 2(2 sigma/Delta)^2 with the Seed noise column (PASTIS sigma 1.1 -> 8 seeds per 1-pt gap). Link docs/replicate-plan.md.
3. Model ranking: same snapshot for both views or print the discrepancy; bootstrap CI on General (independent); "—" not "nan"; "How to read it" above the table; rename General to "Predicted mean z (independent evals)"; general-vision as a column not a suffix. Cheap extras: fix legend svg size; Evidence map default X=EDI(log) Y=Frontier; one-click drawer from ranking.

## 4. Statistical objections
1. Percentile bootstrap resampling 4-8 models with replacement biases tau2obs down; point estimates fall outside their own 90% interval: Sen4Map 0.94 (0.69-0.93), So2Sat 0.92 (0.82-0.91), SatlasPretrain 0.90 (0.55-0.87); under frontier 7 of 60 rows (PASTIS 0.88 / 0.73-0.86, South Africa 0.79 / 0.67-0.78, MADOS 0.97 / 0.89-0.96). Use jackknife/BCa or interval on log EDI.
2. Top of ranking driven by sigma ~0: fMoW 0.03 pts (EDI 12,964), DFC2020 0.10, Dynamic World 0.01, WorldClim spread 0.04 / sigma 0.00, GRIP4 0.03/0.01 - unit artefacts despite the "rescaled" claim; median->mean moves fMoW EDI 27x. Floor sigma or flag.
3. 19 of 43 default Reliable rows have Papers = 1; 17 are not in inventory. Within-one-paper reliability does not test cross-lab separation. Require >=2 papers or label "Reliable (1 paper)".
4. n_reps assumed for most rows; popover says 3, drawers show 1/2/4/5 "(assumed)"; provisional uses n=1 with a borrowed sigma2 -> ratio of two plug-ins, yet 47 Provisional (high) rows at 0.96-0.99 look identical to measured ones.
5. Latent diagnostics not robust: Dataset-specific 69%->30% (fMoW), 66%->8% (Dynamic World), 83%->46% (MOSAIKS) from ridge 10 -> 3; About's own residual check (0.59 within dataset) says the diagonal C used by the Shapley is wrong, so same-dataset comparisons double count - exactly why PASTIS (37 comps) tops Info share.
6. Info share = popularity: top rows are the most-reported datasets; Sen1Floods11 (score 0.54) is second.
7. General ability: extrapolated over ~800 tasks from 11-50 observed; theta up to +-6 with Cov=I means a few models dominate; no CI.
8. Frontier with top ceil(n/2) floored at 4 equals the full score for every 4-model comparison (Sen4Map, Landslide4Sense, HLS Burn Intensity) - should show "—".
9. Self-reported kept by default (fMoW 45%, Dynamic World 64%) inflates spread; "not used in the score" is the problem, not a reassurance.

## 5. Wrong or contradictory between pages
- Counts: Explorer 118/54; ranking 192/57 measured/51 reliable; Evidence map 155/104/47; Domains 118/54; Model ranking 91 ranked/217 profiled vs 93 ranked/169 independent; dates 2026-10-27 vs 2026-10-08; "Measured noise only" shows 47 vs tile 57.
- sigma2: About "averaged" vs default "median". Replicates: popover 3 vs drawers 1/2/4/5 assumed. Filters: 13 vs 14. "Saturated" two meanings.
- Sen1Floods11 Moderate on ranking, launch task on Tasks. Kuro Siwo Reliable 0.99 with frontier 0.17.
- Reliable rows with "–" spread and noise (MMEarth-Bench SOC, MOSAIKS, BioMassters) vs legend "measured from printed SDs".
- Ranks skip under default filter. Clicking a benchmark opens Explorer search, not the drawer (Evidence map intro says "click it to open the dataset"). URL state dropped on nav.
- Z-view: ImageNet ConvNeXt-L #4 / XL #5; profile view #74 / #79.
- Evidence map legend 440px circles. "nan" cells; annotator note in a backbone cell; "general vision"/"not in inventory" glued to names in copy.

One line: the reliability/frontier scores and the popovers are genuinely useful; the ranking page is ordered for whoever computed the numbers, not for someone choosing a suite, and the rows at the very top (sigma 0.01-0.03, EDI in the thousands, intervals excluding their own point) are what a reviewer will use to dismiss the method.
