#!/usr/bin/env python3
"""Render docs/dataset-analysis.md from data/dataset_analysis.json (written by build_dataset_analysis.py)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "data" / "dataset_analysis.json").read_text())
L = []
def w(s=""): L.append(s)
def ci(x): return f"{x['mean']:+.3f} (90% CI {x['ci90'][0]:+.3f} to {x['ci90'][1]:+.3f}; {x['n_tasks']} tasks, {x['n_papers']} papers)"

o, sc, K = d["overlap"], d["scope"], d["K"]
w("# What existing benchmarks measure: dataset-level latent-factor analysis")
w()
w(f"Analysis of {d['as_of']} on the GeoFM meta-analysis workbook v4, following *GeoFM Benchmark Scoring* (S. Wang, Oct 2026). Object of study: the benchmark **datasets** — what they measure, how much they overlap, and whether independent groups agree on the model differences they show. Model capability vectors are nuisance parameters; nothing here ranks models. Built by `scripts/build_dataset_analysis.py`; numbers in `data/dataset_analysis.json`.")
w()
g0 = d["lopo_gain_vs_one_ordering"]; Kc = d["K"]["chosen"]; bk = g0.get("bestK_vs_naive_leaderboard")
lk = d["K"]["lopo_by_K"]; simL = d.get("simulation_lopo_selection", [])
def iv(x): return f"{x['mean']:+.2f} (90% CI {x['ci90'][0]:+.2f} to {x['ci90'][1]:+.2f})"
assoc_ok = [c for c, v in d["metadata_association_multi_paper"].items() if min(v["full_loading"]["p_bonferroni_4_labels"], v["direction_only"]["p_bonferroni_4_labels"]) < 0.05]
w("## Findings")
w()
credible = bk and bk["ci90"][0] > 0
w(f"1. **One leaderboard does not describe GeoFM performance{'' if credible else ' — but the evidence is weak'}.** Predicting how GeoFMs order on an unseen paper's tasks from all other papers, a one-factor model does no better than a naive leaderboard ({iv(g0['K1_vs_naive_leaderboard'])}); "
  + (f"the best multi-factor model (K = {bk['K']}) beats it by Δρ = {iv(bk)}. " if bk else "")
  + f"Out-of-paper accuracy rises with K (ρ = " + ", ".join(f"{lk[k]['rho_struct']:.2f}" for k in sorted(lk)) + f" for K = {', '.join(sorted(lk))}); the smallest K not credibly worse than the best is {Kc}, and on this mask that rule is conservative (in simulation it selects " + ", ".join(f"K = {x['K_selected_lopo']} for K_true = {x['K_true']}" for x in simL) + "). So there are at least two shared dimensions and plausibly more; the exact number is not identifiable. Even the best model predicts little of each paper's ordering (ρ ≈ " + f"{max(v['rho_struct'] for v in lk.values()):.2f}).")
w(f"2. **What a dataset measures does not carry over across papers.** For datasets that other papers also report, adding the dataset's own loading changes out-of-paper accuracy by {iv(g0['dataset_seen_in_other_papers'])}. Dataset-to-dataset similarity is not recoverable on this evidence and is not reported.")
w(f"3. **No metadata label credibly organises the datasets.** " + ("Domain, subdomain, task type and sensor all fail to explain dataset loadings beyond chance after correcting for the four labels tested." if not assoc_ok else f"Only {', '.join(assoc_ok)} survive(s) correction for the four labels tested."))
w(f"4. **No dataset's reliability can be judged from the main-text literature.** After removing reprints, no dataset version × protocol has ≥ 5 GeoFMs evaluated by two independent papers; σ²_t, EDI and the Eq. 6 score need repeated standardised runs (the replicate design).")
w()
w("## 1. Evidence base")
w()
w(f"{sc['rows_in']:,} extracted results → **{sc['rows_kept']:,}** kept. Rules, in order:")
w()
w("| Rule | Rows dropped |")
w("|---|---|")
for s in sc["dropped"]: w(f"| {s['rule']} | {s['dropped']:,} |")
w()
if sc.get("reprint_pairs"):
    w("Reprinted results (kept only in the earliest source): " + "; ".join(f"{p['later']} reprints {p['earlier']} ({p['shared_cells']} shared cells, {100*p['identical_share']:.0f}% identical)" for p in sc["reprint_pairs"]) + ".")
    w()
w("Main-text placement of every source table is in `data/table_locations.json` (file-name rule, or checked against the arXiv version); model scope in `data/model_scope.json`.")
w()
w(f"Imagery comparisons with ≥ 4 GeoFMs: **{o['models']} GeoFMs × {o['tasks']} tasks** ({o['datasets']} datasets, {o['papers']} papers), {100*o['density']:.1f}% of cells observed, median {o['models_per_task_median']:.0f} GeoFMs per comparison. {o['models_in_1_paper']} of {o['models']} GeoFMs are evaluated by a single paper and only {o['models_in_3plus_papers']} by three or more; {o['datasets_in_2plus_papers']} of {o['datasets']} datasets are reported by more than one paper. Everything below is limited by this overlap.")
w()
w("## 2. How many shared capability dimensions? (the note's one-leaderboard test)")
w()
w("Model: y_mt = μ_t + λ_t′θ_m + c_{m,p(t)} + η_mt on the points scale, each task in units of its residual SD; λ_t = dataset + protocol-family + sensor blocks + task part (Eq. 11/12 group ridge); c_{m,p} = paper × model implementation offset.")
w()
w("**Primary criterion — leave one paper out.** Drop every task a paper reports, refit, predict the order of its GeoFMs from what the rest of the literature says about those GeoFMs and about the task's dataset, protocol and sensor. Spearman ρ between predicted and reported order, averaged over held-out tasks:")
w()
w("| K | structured prediction | its own one-ordering | naive leaderboard (fixed) |")
w("|---|---|---|---|")
for k, v in K["lopo_by_K"].items(): w(f"| {k} | {v['rho_struct']:.3f} | {v['rho_global']:.3f} | {v.get('rho_board', float('nan')):.3f} |")
w()
w("The naive leaderboard orders the held-out paper's GeoFMs by their mean within-comparison z-score in all other papers: a single ranking that does not depend on K, so it is the fair one-leaderboard baseline.")
w()
w(f"Selection rule: the smallest K whose leave-one-paper-out accuracy is not credibly below the best K (paired bootstrap over papers) gives **K = {K['chosen']}**; the dataset outputs in §5 use it. Paired differences to the best K: " + "; ".join(f"K={k}: {ci(v)}" for k, v in K["paired_vs_best"].items()) + ".")
w()
g = d["lopo_gain_vs_one_ordering"]
bk_ = g.get("bestK_vs_naive_leaderboard")
w(f"**One leaderboard vs more dimensions.** Structured prediction minus the naive leaderboard: K = 1 {ci(g['K1_vs_naive_leaderboard'])}; K = {K['chosen']} {ci(g['vs_naive_leaderboard'])}" + (f"; K = {bk_['K']} (best) {ci(bk_)}." if bk_ else "."))
w()
w(f"**Does knowing the dataset help?** Gain over the K-factor model's own single ordering: datasets also reported by other papers {ci(g['dataset_seen_in_other_papers'])}; datasets reported only by the held-out paper (prediction from protocol and sensor) {ci(g['dataset_only_in_held_out_paper'])}. What a dataset 'measures', as estimated from other papers, does not carry over to a new paper's evaluation of it.")
w()
w("**Held-out cells (secondary).** Pairwise ordering accuracy of held-out cells (within-paper information leaks into this criterion through c_{m,p}, so it is not used to choose K):")
w()
w("| spec | paper offset | " + " | ".join(f"K={k}" for k in sorted({r['K'] for r in K['heldout_cells']})) + " |")
w("|---|---|" + "---|" * len({r['K'] for r in K['heldout_cells']}))
rows = {}
for r in K["heldout_cells"]: rows.setdefault((r["spec"], r["paper_offset"]), {})[r["K"]] = r["pair_acc"]
for (spec, po), v in rows.items(): w(f"| {spec} | {'yes' if po else 'no'} | " + " | ".join(f"{v[k]:.3f}" if k in v else "–" for k in sorted({r['K'] for r in K['heldout_cells']})) + " |")
w()
w("**Can K be recovered on this mask?** Simulation with the real missingness pattern, a dataset-shared loading (60% of its variance), and paper × model implementation effects (0.5 noise SD). Selection by the same leave-one-paper-out rule as the real data (SNR 1):")
w()
w("| K true | K selected (LOPO) | LOPO ρ by K |"); w("|---|---|---|")
for s_ in d.get("simulation_lopo_selection", []): w(f"| {s_['K_true']} | {s_['K_selected_lopo']} | " + ", ".join(f"K{k}: {v:.3f}" for k, v in s_["lopo_rho"].items()) + " |")
w()
w("Held-out-cell selection and geometry recovery over three signal levels:")
w()
w("| K true | SNR | K selected (held-out cells) | dataset-similarity recovery (all / datasets in ≥ 2 papers) |")
w("|---|---|---|---|")
for s_ in d["simulation"]:
    rec = "–" if s_["recovery_all"] is None else f"{s_['recovery_all']:.2f} / {s_['recovery_multi_paper_datasets']:.2f}"
    w(f"| {s_['K_true']} | {s_['snr']} | {s_['K_selected_cv']} | {rec} |")
w()
w(f"Under the same leave-one-paper-out rule the simulation selects K = 1 even when K_true is 2 or 3: with this little cross-paper overlap, extra dimensions only pay off out of paper when they are strong. That the real data keeps improving up to K = 4 is therefore evidence of more than one shared dimension; K = {K['chosen']} is a floor, not an estimate. In an earlier run without the paper × model offset, held-out selection over-selected (K_true 1 → 2, 2 → 3): implementation effects can masquerade as capabilities, so the current site's K = 3 may partly reflect implementation effects and its broader model scope.")
w()
w("## 3. What organises the datasets")
w()
a = d["metadata_association_multi_paper"]
w("Share of variance in dataset loadings explained by each label, over datasets reported by ≥ 2 papers (blank labels treated as missing; permutation null shuffles labels across datasets; p adjusted for the 4 labels tested). 'Direction only' normalises each loading to unit length: it asks what a dataset measures, not how strongly it separates GeoFMs.")
w()
w("| label | R² (full) | null | p (Bonf.) | R² (direction only) | null | p (Bonf.) | datasets |")
w("|---|---|---|---|---|---|---|---|")
for c, v in a.items():
    fl, dr = v["full_loading"], v["direction_only"]
    w(f"| {c} | {fl['r2']:.2f} | {fl['null_mean']:.2f} | {fl['p_bonferroni_4_labels']:.2f} | {dr['r2']:.2f} | {dr['null_mean']:.2f} | {dr['p_bonferroni_4_labels']:.2f} | {fl['n']} |")
w()
w("Read these as weak evidence at best: about 20 datasets, many-level labels, and loadings that do not transfer across papers (§2).")
w()
w(f"Dataset-to-dataset similarity is **not published**: simulated recovery of the similarity geometry on this mask stays below 0.7 (geometry_recoverable = {d['geometry_recoverable']}). The evidence supports a minimum number of dimensions, not which specific datasets are near-duplicates.")
w()
w("## 4. Do independent groups agree on what a dataset shows?")
w()
re_ = d["replication_evidence"]
w(f"Grouping by exact benchmark version × protocol × training fraction × metric × setting, after removing reprints: {re_['groups_with_2plus_papers']} groups are reported by ≥ 2 papers; {re_['with_3plus_shared_geofms']} share ≥ 3 GeoFMs and {re_['with_5plus_shared_geofms']} share ≥ 5. Cross-paper reproducibility (additive paper + model fit, ≥ 5 shared GeoFMs, ≥ 5 residual df) is estimable for **{len(d['reproducibility'])}** groups. Main-text literature does not contain the independent re-evaluations needed to judge any dataset's reliability; the note's σ²_t (and with it EDI and the Eq. 6 score) requires repeated standardised runs.")
w()
if re_["groups"]:
    w("| group | papers | GeoFMs in ≥ 2 papers |"); w("|---|---|---|")
    for x in re_["groups"][:10]: w(f"| {x['group'].replace(' | ', ' · ')} | {x['papers']} | {x['geofms_in_2plus_papers']} |")
    w()
w("## 5. Datasets with independent evidence (≥ 2 papers)")
w()
w("Descriptive evidence only. Reported separation = model-count-weighted SD of reported scores within the dataset's comparisons, over each paper's own GeoFM set (note Eq. 10: reported separation, not quality or discriminative power). LOPO ρ = mean leave-one-paper-out Spearman over the dataset's tasks (structured / naive leaderboard), with the number of tasks and median GeoFMs behind it. In-sample loading summaries (shared signal, Eq. 8 information share) are kept in the JSON but not shown: they do not transfer across papers (§2) and are driven by single small comparisons (e.g. RESISC45 rests on one 4-GeoFM comparison).")
w()
w("| dataset | domain | papers | comparisons | smallest comparison | reported separation (pts) | LOPO ρ: structured / leaderboard (tasks, GeoFMs) |")
w("|---|---|---|---|---|---|---|")
ds = [(n, x) for n, x in d["datasets"].items() if x["papers"] >= 2]
ds.sort(key=lambda t: (-t[1]["papers"], -t[1]["comparisons"]))
f = lambda v, p=2: "–" if v is None else f"{v:.{p}f}"
for n, x in ds:
    lo = f"{f(x['lopo_rho'])} / {f(x['lopo_rho_naive_leaderboard'])} ({x['lopo_tasks']}, {f(x['lopo_models_median'],0)})" if x["lopo_tasks"] else "–"
    w(f"| {n} | {str(x['domain']).split('· ')[-1]} | {x['papers']} | {x['comparisons']} | {x['smallest_comparison']} | {f(x['reported_separation_pts'],1)} | {lo} |")
w()
n1 = sum(1 for x in d["datasets"].values() if x["papers"] < 2)
w(f"{n1} further datasets are reported by a single paper; their loadings cannot be separated from that paper's GeoFM selection and implementation, so no dataset-level quantity is reported for them.")
w()
w("## 6. Limits and open decisions")
w()
w("- **Main-text rule loses some results.** Several papers' main-text tables are condensed versions of appendix tables that the workbook extracted instead (e.g. Galileo, SatCLIP, Prithvi-EO-2.0 GEO-Bench results). Those main-text numbers are currently lost. Decide whether to re-extract the main tables or keep appendix rows that a main table reprints.")
w("- **GEO-Bench-2 leaderboard** is excluded as not a paper's main text; `--include-leaderboard` adds it.")
w("- Uncategorised models were scoped by hand (`data/model_scope.json`); `vanilla_mae` and `convmae` are excluded because the same id is EO-pretrained in some papers and ImageNet-pretrained in others.")
w("- Geography and time blocks of Eq. 11 are not fitted: the workbook has no geography/time metadata, and the evaluation design is not crossed enough to separate them from dataset.")
w("- The number of shared dimensions is not identifiable on this evidence (≥ 2; out-of-paper accuracy still rising at K = 4).")
w("- `data/model_profiles.json` (existing build) still publishes θ as a nuisance output and `benchmarks.html` is still titled 'Benchmark ranking'; both predate this analysis.")
(ROOT / "docs" / "dataset-analysis.md").write_text("\n".join(L) + "\n")
print("wrote docs/dataset-analysis.md")
