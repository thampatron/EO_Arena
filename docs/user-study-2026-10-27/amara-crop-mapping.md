# Amara — 45-minute session on EOArena (Draft v0.3)

Third-year PhD, remote sensing, smallholder crop-type mapping in West Africa with S1/S2 time series. Have fine-tuned Prithvi and DOFA. Not a statistician. Never seen the site before. Screenshots are in this folder (01_…28_).

## 1. What I concluded

### Q1 — which GeoFM to try first

**Conclusion: croma_vitl, with softcon or clay_vitb as the second attempt. Confidence: low.**

Why low: the site gave me three different "number ones" depending on which view I was in, and nothing on any page told me which to believe.

| Where | What convinced me | Winner |
|---|---|---|
| Model ranking, default view ("Capability profiles"), column **General (independent)** | croma_vitl +0.17, croma_vitb +0.14, softcon +0.11, spectralgpt/terramind/dofa +0.10 | croma_vitl |
| Same view, sorted by **θ1** (after reading "What the axes separate" at the bottom: Axis 1's high-loading datasets are BreizhCrops +0.16, NeuCo-Bench Crops +0.16, PASTIS +0.15 — i.e. my task) | softcon +2.59, ssl4eo_vits_dino +2.14, olmoearth_v1_base +2.02, prithvi_v1_100m +1.93; **dofa_vitb −1.19** | softcon |
| **Z-score view, Scope = 1.1 Cropland and crop type** | clay_vitb +1.47 (15 comparisons, 4 benchmarks, 3 papers), dinov2_vitb (general vision) +1.05 (10 comps, 2 benchmarks), olmoearth_v1_base +0.78, skysense +0.70, prithvi_v2_600m_tl +0.67 (5 comps), croma_vitl +0.56 (87 comps, 10 benchmarks, 8 papers), dofa_vitb +0.07 (#26) | clay_vitb |
| Z-score view, Scope = All | skysense +0.73, olmoearth_v1_base +0.70, gfm_swin_swint +0.70, **convnext_l_imagenet (ImageNet baseline) #4 +0.69**; croma_vitl #13 | skysense |

What I did with this: I discounted clay (15 comparisons on 4 benchmarks vs croma's 87 on 10 — I trust volume when no uncertainty is shown), discounted dinov2/convnext because an ImageNet backbone at #2 for crop type smells like a protocol artefact, and went with croma because it is #1 on the default view and still top-10 in the crop scope. Softcon is the hedge because the θ1 axis is clearly "crop time series" and softcon is far ahead on it.

The one solid, actionable finding: **DOFA — which I have already used — is bad for my task** on every view (θ1 −1.19; crop-scope z +0.07, rank 26; FT z −0.26). That alone was worth the visit, and the site never says it; I had to assemble it.

What I wanted and never got: "On PASTIS / South Africa crop type, which model scored highest?" The PASTIS panel says "72 models scored… no individual scores". The Model ranking footer says "What this ranking is not: a verdict on which model is best." The site refuses Q1 by design and only says so in the last paragraph of the Model ranking page.

### Q2 — which benchmark datasets to evaluate on so reviewers believe it

**Conclusion: PASTIS / PASTIS-R (primary), South Africa crop type, CropHarvest; add CropTypeMapping Ghana / South Sudan as the regional one but flag it as weak evidence. Confidence: medium-high.**

What convinced me, in order:

1. **Evidence map, Domain = Agriculture, X = Models, Y = Score, Label all** (screenshot 25). Top-right cluster (many models, score > 0.9, filled = measured noise): PASTIS / PASTIS-R, South Africa crop type, Cashew plantation. Mid: CropHarvest (0.86), Fields of The World (0.84). Hollow top-left (one paper, plug-in noise): Ghana / South Sudan, BreizhCrops, Nandi, Canadian Cropland. Isolated low: AI4SmallFarms (0.65). This single picture did the job.
2. **Benchmark ranking, Domain = 1 · Agriculture**, columns Models / Papers / Score / Verdict: PASTIS 72 models, 8 papers, 37 comparisons, score 0.96 (0.92–0.96), Reliable. South Africa crop type 69 / 9 / 16, 0.95, Reliable. CropHarvest 41 / 4 / 12, 0.86, Reliable. Fields of The World 26 / 2 / 10, 0.84, Reliable. Ghana/South Sudan 12 / 1 / 15, 0.99 but **Provisional (high)**. AI4SmallFarms 0.65, Provisional (low). SICKLE and TimeSen2Crop: "Under 4 models".
3. **Explorer PASTIS panel, "Benchmarks" row**: PANGAEA, GEO-Bench-2, Galileo, AnySat, OmniSat, TerraMind. That list is what my reviewers recognise. This row was the most useful single field on the site for Q2.

Caveats: Cashew plantation is a binary plantation mask in Benin, not crop type, so I dropped it although its numbers match South Africa's. Ghana/South Sudan: 1 paper, 12 models, "Licence unverified" — I would still include it because it is West Africa, but the site makes clear a reviewer could say "one paper".

## 2. Timeline

**0–5 min, Explorer (index.html).** First impression good: Agriculture is domain 1, crop-type datasets are the first rows, "118 datasets / 54 with published GeoFM scores" tells me what the site is. I read the badges "Reliable", "Provisional (high)", "Under 4 models", "No GeoFM scores" and did not know what they meant — I expected a licence or data-quality badge, I saw a word I could not place (the legend lives on the Benchmark ranking page). I ticked 1 · Agriculture and Time series: 15 datasets, all plausible. I did not use Subdomain, Output unit, Output value, Resolution, Label source, Footprint, Ability tested — too many filters, and names like "Footprint" and "Ability tested" did not tell me what they filter.

**5–12 min, Explorer, PASTIS detail panel.** Top half (Geography, Size, Licence, Benchmarks) — used all of it. "GeoFM evidence" card: 12 statistics. I understood Models scored (72), Papers (8), Model spread (7.56 pts); half-understood Seed noise; did not understand EDI (27.4), Info share (8.1%), Dataset-specific signal (42%), Frontier score (0.88), Replicates per value "2 (assumed)". The prose paragraph under the stats restates the same numbers, twice the reading for nothing. I expected "best model on this dataset: X"; I saw "no individual scores". I clicked the (i) on Score: the first sentence ("share of the observed model spread that is repeatable") was enough; the τ² formula I skipped. I opened Ghana / South Sudan: EDI 192 vs PASTIS 27.4 — I misread that as "Ghana is seven times better evidence" until I noticed PASTIS is Reliable and Ghana is Provisional with 1 paper. A bigger EDI with worse evidence is confusing.

**12–22 min, Model ranking (models.html).** Intro: "capability profile from the latent-factor regression of the scoring note (θm, K axes)" — I did not understand the first sentence. Yellow warning box: good, I read it. At 1400 px the table is cut off after θ1; I did not realise θ2, θ3, Tasks (ind.), Datasets (ind.) existed until I scrolled sideways. I read General (independent) and took croma_vitl. I tried to sort by θ1 by clicking the header cell — nothing happened. Later I found that clicking the column *name text* sorts; clicking elsewhere in the header (including near the ⇅ glyphs) does nothing. I scrolled to the bottom, found "What the axes separate", realised Axis 1 = crop time series, went back up and sorted by θ1. Three screens of travel to learn the column I needed was θ1, not General. "How to read it" mentions "The Scope control", but there is no Scope control in the default view; it only appears after switching View to "Z-score ranking". The Z-score view then produced a different top-10 (skysense, an ImageNet ConvNeXt at #4). Expected: the two views to roughly agree. Saw: croma #1 → #13. Scope = 1.1 Cropland: clay_vitb #1 with 15 comparisons. Nothing says how much to trust +1.47 from 15 comparisons vs +0.56 from 87.

**22–32 min, Benchmark ranking (benchmarks.html).** Legend of the seven verdicts at the top — this is what I needed on the Explorer. Analysis settings strip: five dropdowns (Seed noise σ² median/mean, Self-reported kept/dropped, Headline full/frontier, Unit dataset/dataset × protocol family, Latent fit ridge 10/ridge 3). I understood only "Self-reported: dropped". I tried it: PASTIS 0.96 → 0.98, South Africa stayed 0.95, CropHarvest 0.86 → 0.97, order barely changed, so my shortlist is robust — a useful 30 seconds. I tried Headline = frontier: South Africa and Cashew became "Moderate", CropHarvest 0.63 Moderate, PASTIS 0.88. I did not know what to do with that and set it back. Rank column skips numbers (1, 2, 4, 7, 9…) because "Imagery tasks only" is ticked — I thought rows were missing. Table cut off after Score at my width; Frontier / EDI / Dataset-specific / Info share / Self-reported / Verdict are off-screen, so the Verdict column — the one that summarises — is last and hidden. I clicked "PASTIS / PASTIS-R" expecting the row to expand (footer: "the expandable detail lists them"); it navigated to the Explorer with a search and lost my Agriculture filter. Clicking a number cell expands the row instead; nothing indicates this. The expanded per-paper table (olmoearth, galileo, geobench, tessera, pangaea…) is what I'd cite, but its header reads "fine-tuned · undefined comp. · undefined models · score 0.98 frozen · undefined comp. · undefined models".

**32–40 min, Evidence map (evidence.html).** Default: small multiples of all 9 domains, X = Score, Y = Frontier score, with all agriculture points squashed between 0.8 and 1.0 and no labels. I set Domain = Agriculture, X = Models, Y = Score, Label all: that is the Q2 answer in one picture. The strip said "25 datasets shown", the panel said "15 datasets · 10 without these metrics" — contradictory for a moment. Labels overlap at the top-left (Ghana / BreizhCrops / Canadian Cropland / Multi-Temporal Crop Class… overprint). Y axis 0–1 with everything above 0.6.

**40–45 min, Tasks, Domains, About.** Tasks: 5 draft tasks, one is "Crop type segmentation from Sentinel-2 and Sentinel-1 time series (PASTIS-R)" with mIoU, frozen-decoder 10 runs / finetune 5 runs, 100/10/1% label fractions — exactly the protocol I'd copy, and the only page that says *how* to evaluate. It is called "Tasks" in the nav, so I almost skipped it. Domains: 1.1 Cropland and crop type is labelled "Saturated". On the Benchmark ranking "Weak / saturated" means "models cannot be told apart"; here it means "well covered by suites". I read it the first way. About: "13 filters"; Explorer header says "14 filters".

Pages skipped: Map, Sensors (no time).

## 3. Three things I would change first

**(a) Model ranking: make the default view answer "best for my task".**
- Default View = z-score view *with Scope visible*; Scope should also exist on the capability-profile view. Hiding Scope inside the second view is the single biggest reason I spent 10 minutes here.
- z-score column order: Model · Independent z · Comparisons · Benchmarks · Papers · Win rate · FT z · Frozen z · Backbone · Pretraining data · Self-reported z · Self comps. I used z, comparisons, benchmarks, papers, FT/Frozen; I never used Backbone or Pretraining data, yet they sit in columns 3–4.
- Capability-view order: Model · General (independent) · θ1 · θ2 · θ3 · Tasks (ind.) · Datasets (ind.) · General (all) · Self-report gap · Backbone · Pretraining data · Mean z (ind.). Under each θ header, a 3-word hint from "What the axes separate" (e.g. "θ1 — crop/forest time series ↑, VHR damage/change ↓") so I do not scroll to the footer to learn which axis is mine.
- First sentence: "Models ranked by how they score on benchmarks run by *other* groups. Pick a domain in Scope to see the ranking on those benchmarks only; fewer than ~30 comparisons means the rank is one paper's opinion." Then the yellow box.
- Make the whole header cell sortable, with an arrow on the active sort.
- Show an interval on Independent z (as the Score column has on the Benchmark page). Without it, clay +1.47 (15 comps) vs croma +0.56 (87 comps) is uninterpretable.

**(b) Benchmark ranking: lead with verdict and evidence size, hide diagnostics by default.**
- Column order: Benchmark · Domain · Verdict · Score (CI) · Models · Papers · Comparisons · Spread · Seed noise · [collapsed "more": Frontier score · EDI · Dataset-specific · Info share · Self-reported]. Verdict is currently last and off-screen at laptop width; it is the column I read.
- Renumber ranks after filtering (or drop the rank; the score already orders rows).
- Expand on click anywhere in the row; move "open in Explorer" to a small link icon. Fix the "undefined comp. · undefined models" header and the "1?" replicates cell (say "1 (assumed)" as the Explorer does).
- First sentence: "Which benchmarks can tell GeoFMs apart. Score = share of the gap between models that survives re-running with another seed; Reliable means ≥ 80% and measured, Provisional means we had to guess the noise." The current first sentence contains τ²/(τ² + σ²).
- Analysis settings: collapse by default behind "Advanced: alternative scoring choices from the method note", or give each dropdown a plain label ("Drop scores from a model's own paper", "Score only the top half of models"). "Latent fit ridge 10 (stable) / ridge 3 (predictive)" belongs on the About page.

**(c) Explorer: explain the badge where it is, and put "which benchmarks / which models" before the statistics.**
- The evidence badge in the row list needs a tooltip or a one-line legend above the list; today the legend is on another page.
- Detail panel "GeoFM evidence" card: three numbers big (Models scored, Papers, Score + verdict), one sentence, then a "show 9 more diagnostics" toggle for EDI / Info share / Dataset-specific / Frontier / Replicates / Self-reported. Delete the paragraph that restates the numbers.
- Move the "Benchmarks" row (PANGAEA, GEO-Bench-2, …) above the description — it is the field a PhD student uses to decide whether reviewers will recognise the dataset.
- Default view that would have answered Q2 fastest: Explorer pre-filtered to evidence badge = Reliable, grouped by Subdomain, sorted by Models scored descending. For Agriculture that is seven rows and is the answer.

## 4. Things that looked wrong or contradictory

1. **Benchmark ranking, expanded row header**: "fine-tuned · undefined comp. · undefined models · score 0.98 frozen · undefined comp. · undefined models · score 0.96". Literal `undefined`.
2. **Benchmark ranking with Headline = frontier, Domain = Agriculture**: PASTIS shows Score 0.88 with interval 0.73–0.86 — the point estimate is outside its own 90% interval. Same for South Africa 0.79 (0.67–0.78) and Fields of The World 0.68 (0.51–0.67). The interval is not recomputed when the headline switches, or the columns swap.
3. **Counts disagree across pages**: Benchmark ranking "192 benchmarks with GeoFM scores · 57 with measured seed noise · 51 reliable"; Evidence map "155 benchmark datasets · 104 with a score · 47 measured noise"; Explorer "54 with published GeoFM scores"; Domains page Agriculture "18 of 25 known datasets scored"; Explorer Agriculture count 22; Benchmark ranking Agriculture rows 25. Some are imagery-only vs all, in-inventory vs not, but nothing says which, and "measured noise" is 57 on one page and 47 on the next.
4. **"14 filters" (Explorer header) vs "13 filters" (About page)**. The Explorer sidebar has 14 facets including "Ability tested".
5. **"Saturated" means opposite things**: Domains status "Saturated" = heavily covered by suites; Benchmark ranking verdict "Weak / saturated" = models cannot be separated. 1.1 Cropland is "Saturated" on Domains while PASTIS is "Reliable" (the opposite) on Benchmarks.
6. **"Comparisons" means different things**: Model ranking crop scope says "18 benchmarks, 1,838 comparisons"; Benchmark ranking Agriculture rows sum to ~170 comparisons. One counts model-rows, the other paper tables. Same word, 10× different number.
7. **Evidence map**: "25 datasets shown" in the control strip vs "15 datasets · 10 without these metrics" in the panel.
8. **Benchmark ranking ordering**: Dynamic World (spread 0.22 pts, noise 0.01) is #7 and WorldClim Bioclim (spread 0.04 pts, noise 0.00) is #10, above PASTIS (spread 7.56) at #26. Ranking purely on τ²/(τ²+σ²) puts benchmarks where models differ by 0.04 points at the top. Not an arithmetic bug, but a rank that puts it above PASTIS undermines my trust in the rank.
9. **Model ranking, capability view**: the (i) next to "Self-report gap" has aria-label "About General ability" — the wrong popover is wired to that column.
10. **Model ranking z-score view, crop scope**: dinov2_vitb (ImageNet/LVD) is #2 for crop type on 10 comparisons / 2 benchmarks, and convnext_l_imagenet is #4 overall. Either untick general-vision baselines by default or add a note; as presented it reads as "an ImageNet ViT beats every GeoFM at crop type", a claim a reviewer would jump on.
11. **Ghana / South Sudan EDI = 192 vs PASTIS EDI = 27.4**, while Ghana has 1 paper / plug-in noise and PASTIS 8 papers / measured noise. EDI as displayed rewards the absence of measured noise. The verdict chip corrects for it, but the number is bigger and comes first.
12. **Model ranking header counts**: capability view "91 models", z-score view "93 models", both "Ranked only".
13. **Benchmark name click (benchmarks.html → index.html?q=…)** loses the domain filter; the back button returns with the filter gone.

## Columns I used vs ignored

- Explorer list: used Name, Subdomain, Task family · Time structure, Sensors, evidence badge. Ignored licence badge (for later, not for choosing).
- Explorer panel: used Geography, Size, Licence, Benchmarks, Models scored, Papers, verdict. Ignored EDI, Info share, Dataset-specific, Frontier, Replicates, Self-reported, Seed noise.
- Model ranking: used General (independent), θ1 (after a detour), Independent z, Comparisons, Benchmarks, Papers, FT z / Frozen z. Ignored Backbone, Pretraining data, General (all), Self-report gap, θ2, θ3, Mean z (ind.), Self-reported z, Self comps., Win rate.
- Benchmark ranking: used Benchmark, Domain, Models, Papers, Score, Verdict. Ignored Spread, Seed noise, Frontier, EDI, Dataset-specific, Info share, Self-reported. Order needed: Verdict and Score first, Models/Papers next; order given: those last.
- Evidence map: used Domain, X, Y, Label all. Ignored Colour, Size by models (left on), Provisional, Not in inventory, Table view, Analysis settings.
