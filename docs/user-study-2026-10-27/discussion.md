# Amara and Ben, after the EOArena sessions

**Ben:** So. Did it tell you which model to use?

**Amara:** It told me which model *not* to use. DOFA is bad for crop time series on every view I opened: θ1 −1.19, rank 26 in the crop scope, negative fine-tuned z. I have already spent three months fine-tuning DOFA. That one finding paid for the hour. But nothing on the site says it; I assembled it from three tables.

**Ben:** Funny, DOFA is in my baseline set.

**Amara:** As the model you expect to beat?

**Ben:** As a control, yes. I want things with many independent evaluations, and DOFA has them. That's not a disagreement about DOFA, it's a different question. You want the strongest model on crops; I want a set that's robust to the view. For what it's worth, your DOFA finding is the one kind of claim I'd trust from that page, because it survives every view. The *top* of the ranking doesn't.

**Amara:** You mean croma. I took croma_vitl because it's #1 on General (independent) and still top-10 in the crop scope with 87 comparisons.

**Ben:** General (independent) runs from −0.22 to +0.17 and about twenty models sit within ±0.03 of each other. No interval. croma_vitb is #2 on General and alphaearth is #15, but alphaearth has mean z +0.89 to croma's +0.20. That column is a regression extrapolated over about 800 tasks from 11–50 observed per model. I wouldn't cite the order.

**Amara:** Then why did you end up with croma too?

**Ben:** Because it's near the top on both views and has the most independent comparisons. Not because of +0.17. The reason I'd pick it is "appears in 8 papers on 10 benchmarks", which is a count, not a model.

**Amara:** Fine, I'll say that in the paper instead. What about θ1? The footer says Axis 1 loads on BreizhCrops, NeuCo-Bench Crops, PASTIS. That's my task. Softcon is at +2.59 on it, DOFA at −1.19.

**Ben:** Which footer did you have to scroll to? Three screens. θ3 is +6.39 for DOFA and −5.08 for AnySat with Cov(θ) = I. The scale is arbitrary and nothing says how far apart two θs need to be. I'm not saying softcon isn't good on crop time series, I'm saying the site gives you no way to know if +2.59 versus +2.14 means anything.

**Amara:** But the sign for DOFA is consistent with the crop-scope z and the fine-tuned z. Three independent views, one direction.

**Ben:** Agreed. That's the resolution: use the θ axis to find which models are *far* out on your task and check it against the scope ranking. Don't use it to order the top five. What I can't resolve is whether softcon really is ahead of croma on crops. Neither can you.

**Amara:** No. And clay_vitb at +1.47 in the crop scope on 15 comparisons versus croma +0.56 on 87. I discounted clay on volume. Was that right?

**Ben:** It's what I'd do without an interval, which is the point. They print a CI on the Benchmark score and nothing on the model z. Unresolvable from the site.

**Amara:** Then the thing I'm sure about: dinov2_vitb at #2 for crop type on 10 comparisons and two benchmarks. An ImageNet ViT. A reviewer would say "so why do we need GeoFMs."

**Ben:** I want those models in the table. They're my controls.

**Amara:** Then a column saying "general vision", not a suffix glued to the name, and not in the default ranking. Agreed?

**Ben:** Agreed.

**Amara:** Benchmarks. Did your suite overlap mine?

**Ben:** PASTIS, South Africa crop type, Cashew. All three in my ten, all Reliable with 8–9 papers and measured noise.

**Amara:** I dropped Cashew; it's a binary plantation mask in Benin, not crop type. CropHarvest and Fields of The World I kept. Ghana / South Sudan I kept as the regional one with a flag: one paper, 12 models, licence unverified.

**Ben:** Here's where I distrust the verdict you trusted. 19 of 43 default Reliable rows have Papers = 1, and 17 of those aren't in the inventory. Reliable means the model spread survived one lab's seed noise. It doesn't mean two labs agree. Ghana is Provisional, so you're already treating it correctly, but you were reading the badge, not the paper count.

**Amara:** I read Models and Papers first, then Verdict. PASTIS 72 and 8, South Africa 69 and 9, CropHarvest 41 and 4. Every benchmark I kept passes your "≥3 papers" rule anyway.

**Ben:** Then your list survives my filter. The one I'd argue about is CropHarvest. Under Headline = frontier it goes to 0.63, Moderate.

**Amara:** I saw that, didn't know what to do with it, and set it back.

**Ben:** Frontier asks whether the *top half* of models can be told apart. For your reviewers that's the question: can PASTIS separate croma from softcon, or only croma from a 2019 ResNet. PASTIS is 0.88 under frontier, South Africa 0.79. CropHarvest 0.63 says the good models bunch up on it.

**Amara:** So drop it?

**Ben:** Keep it, but as the "easy one" and say so. What I can't resolve is whether 0.63 is real or an artefact of the 4-model-floor; for comparisons with exactly four models the frontier equals the full score. CropHarvest has 41 models so probably real.

**Amara:** And the frontier view produced PASTIS 0.88 with interval 0.73–0.86. The point sits outside its own interval.

**Ben:** Seven of sixty rows under frontier; three under the default too. So2Sat 0.92 with 0.82–0.91. That's a bootstrap resampling 4–8 models with replacement. It's the thing a reviewer would use to dismiss the whole method, and it's on the first screen.

**Amara:** Not for me, it wasn't. The first screen for me was 6 tiles, a 7-item legend, five dropdowns, and the table below the fold. Then at my width the table cut off after Score. Verdict, the column the legend had just explained, was last and off-screen.

**Ben:** Same at 1400, and at 1280 Frontier went too. Scroll right and you lose the name column.

**Amara:** That's the owner's "column order is wrong". But I don't think it's just order. Spread, Seed noise, EDI, Dataset-specific, Info share, Self-reported: I used none of them. You used which?

**Ben:** Frontier, Seed noise, Info share. Info share turned out to be popularity: PASTIS tops it because it has 37 comparisons, and Sen1Floods11 is second at a score of 0.54. Dataset-specific moves 2–8× between ridge 10 and ridge 3. So I used three, and one of the three I'd now drop.

**Amara:** So the owner's other suspicion, "far too much information". Is it true?

**Ben:** Not quite. The popovers are the best thing on the site. The formulas are the reason I'd trust it at all. The problem isn't that the information exists, it's that the twelve diagnostics are in the default view at the same visual weight as the three numbers that decide anything.

**Amara:** The PASTIS panel: 12 statistics, then a paragraph restating the same 12. I understood Models, Papers, Spread, half of Seed noise. EDI 27.4 for PASTIS and 192 for Ghana made me think Ghana was seven times the evidence.

**Ben:** EDI 12,964 for fMoW, σ = 0.03 points. The whole top of the default ranking is rows with σ near zero: fMoW, Dynamic World, WorldClim with a spread of 0.04 points. Unit artefacts.

**Amara:** I saw Dynamic World at #7 and PASTIS at #26 and stopped trusting the rank column. I didn't know why. You do, and we agree on the fix: the top of that table is wrong even if the arithmetic is right.

**Ben:** So the suspicion is half right. Too much *on screen by default*, wrong order, and the wrong default sort. Collapse, reorder, resort. Don't delete.

**Amara:** Model ranking too. Backbone and Pretraining data in columns 3–4 of the z-score view. I used Independent z, Comparisons, Benchmarks, Papers, FT z, Frozen z. Scope only appears after you switch view, and the "How to read it" text mentions Scope while you're in the view that doesn't have it.

**Ben:** And the "How to read it" block sits below 91 rows. Different snapshots for the two views: 91 models dated 10-27, 93 dated 10-08.

**Amara:** One thing we both landed on: the "Benchmarks" row in the dataset drawer. PANGAEA, GEO-Bench-2, Galileo, TerraMind. That's the field a reviewer recognises.

**Ben:** Best single view on the site, two clicks away via an Explorer search that drops your filter. I clicked a benchmark name expecting the drawer; it navigated.

**Amara:** Same, and the footer says "the expandable detail", and the expanded header reads "undefined comp. · undefined models".

**Ben:** Seeds. Did you find how many runs?

**Amara:** Tasks page. 10 runs frozen, 5 fine-tune, label fractions 100/10/1. The only page that says how to evaluate, named "Tasks", which I nearly skipped.

**Ben:** Same page, plus the tie rule, plus a popover saying assumed replicates = 3 while drawers show 1, 2 and 4 "(assumed)". I ended with 5 seeds fine-tuned, 10 frozen, worked out from the Seed noise column myself. It should be one box.

**Amara:** One more: "Saturated". On Domains, 1.1 Cropland is "Saturated", which I read as "models can't be separated", because that's what "Weak / saturated" means on the ranking. It means "many suites cover it".

**Ben:** Which it does, and PASTIS is Reliable. Opposite words for opposite things, same word.

**Amara:** Let's write it down.

---

## (a) Five improvements, ranked

1. **Benchmark ranking table, first screen.** Columns: Benchmark (sticky) · Verdict · Score (90% CI) · Papers · Models · Frontier · Seed noise · In suites; collapse Domain, Comparisons, Spread, EDI, Dataset-specific, Info share, Self-reported behind "more diagnostics". Default sort Verdict → Papers desc → Score; renumber ranks after filtering; sticky header. First sentence: "Which published benchmarks can tell strong GeoFMs apart? Reliable = at least 80% of the gap between models survives measured seed noise; Frontier = the same test among the top half; Papers = how many labs reported it."
2. **Model ranking: one default that answers "best for my task".** Default view z-score with the Scope control visible in *both* views; columns Model · Independent z (bootstrap CI) · Comparisons · Benchmarks · Papers · FT z · Frozen z · General-vision (flag column, unticked by default) · [Backbone, Pretraining data, Self-reported z collapsed]. Capability view: θ headers carry a three-word hint from "What the axes separate". Same data snapshot for both views, "—" not "nan", "How to read it" above the table. First sentence: "Models ranked by scores on benchmarks run by other groups. Pick a Scope to restrict to your domain; under ~30 comparisons the rank is one paper's opinion."
3. **Uncertainty where decisions are made.** Interval on Independent z; recompute the Score interval when Headline switches (jackknife/BCa, or interval on log EDI) so no point sits outside its own CI; floor or flag σ < 0.1 pt so fMoW / Dynamic World / WorldClim stop topping the rank; label "Reliable (1 paper)" when Papers = 1.
4. **Explorer and drawer: decide first, diagnose second.** Verdict-badge legend inline above the list; evidence card shows Models · Papers · Score + verdict large, one sentence, then "show 9 more diagnostics"; delete the restating paragraph; move the "Benchmarks" (suite membership) row above the description; clicking a benchmark name anywhere on the site opens the drawer in place and keeps filter and URL state.
5. **Settings and protocol in one place.** Analysis settings collapsed under "Advanced: alternative scoring choices", each with a plain label ("Drop scores from a model's own paper", "Score only the top half of models"); a "Reproducibility" box on the ranking and About with 10 frozen / 5 fine-tune runs, the P(A>B) tie rule, papers' 5 or 10 seeds, and k ≈ 2(2σ/Δ)² next to the Seed noise column.

## (b) Contradictions and bugs we both hit

- Expanded row header prints "undefined comp. · undefined models".
- Score point estimates outside their own 90% interval (default: Sen4Map, So2Sat, SatlasPretrain; frontier: PASTIS, South Africa, Fields of The World, MADOS and more).
- Counts disagree across pages: Explorer 118/54, Benchmark ranking 192/57/51, Evidence map 155/104/47, Model ranking 91 vs 93 ranked with different dates; "not in inventory" never explained.
- Ranks skip (1, 2, 4, 7, 9…) under the default "Imagery tasks only" filter.
- Benchmark name click navigates to Explorer search and drops the domain filter; footer and Evidence map intro say it expands/opens the dataset.
- "Saturated" means the opposite on Domains and on Benchmark ranking.
- Replicates: popover says assumed = 3, drawers show 1 / 2 / 4 "(assumed)" and the table shows "1?".
- "13 filters" (About) vs "14 filters" (Explorer).
- Evidence map: "25 datasets shown" vs "15 datasets · 10 without these metrics"; legend swatches render as ~440 px circles; labels overprint.
- "Comparisons" counts model-rows on the Model ranking and paper tables on the Benchmark ranking (1,838 vs ~170 for agriculture).
- "nan" backbones and an annotator note inside a backbone cell; Self-report gap (i) wired to the "About General ability" popover.
- Frontier score equals full score for every exactly-4-model comparison instead of "—".

## (c) Verdict

The site answered the benchmark question for both of us and the model question for neither, and it says so only in the last paragraph of the Model ranking page. Amara left with a defensible evaluation set (PASTIS, South Africa crop type, CropHarvest as the easy one, Ghana / South Sudan flagged) and one solid negative result about DOFA; Ben left with a ten-benchmark suite and a baseline set, but with the order of the top ten models and the non-redundancy of the suite unresolved, because the site gives no uncertainty on model z and its redundancy diagnostics move with the ridge setting. What it is actually good for is the reliability and frontier scores with their popovers, the per-benchmark Papers and Models counts, the suite-membership row in the drawer, and the Tasks page protocol; those four things would let a PhD student pick benchmarks a reviewer accepts in about ten minutes if they were on the first screen. The owner's suspicion is half right: the volume is not the problem, the defaults are. The diagnostics belong behind a toggle, the Verdict and Papers columns belong first, the σ ≈ 0 rows belong off the top of the rank, and the ranking should show an interval before it shows a decimal.
