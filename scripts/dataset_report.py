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
w("| K | structured prediction | one ordering for all tasks |")
w("|---|---|---|")
for k, v in K["lopo_by_K"].items(): w(f"| {k} | {v['rho_struct']:.3f} | {v['rho_global']:.3f} |")
w()
w(f"Chosen **K = {K['chosen']}** ({K['criterion']}). Paired differences to the best K: " + "; ".join(f"K={k}: {ci(v)}" for k, v in K["paired_vs_best"].items()) + ".")
w()
g = d["lopo_gain_vs_one_ordering"]
w(f"Gain of the structured prediction over a single ordering: {ci(g['all'])}. Split: datasets reported by other papers {ci(g['dataset_seen_in_other_papers'])}; datasets reported only by the held-out paper (prediction from protocol and sensor alone) {ci(g['dataset_only_in_held_out_paper'])}.")
w()
w("**Held-out cells (secondary).** Pairwise ordering accuracy of held-out cells (within-paper information leaks into this criterion through c_{m,p}, so it is not used to choose K):")
w()
w("| spec | paper offset | " + " | ".join(f"K={k}" for k in sorted({r['K'] for r in K['heldout_cells']})) + " |")
w("|---|---|" + "---|" * len({r['K'] for r in K['heldout_cells']}))
rows = {}
for r in K["heldout_cells"]: rows.setdefault((r["spec"], r["paper_offset"]), {})[r["K"]] = r["pair_acc"]
for (spec, po), v in rows.items(): w(f"| {spec} | {'yes' if po else 'no'} | " + " | ".join(f"{v[k]:.3f}" if k in v else "–" for k in sorted({r['K'] for r in K['heldout_cells']})) + " |")
w()
w("**Can K be recovered on this mask?** Simulation with the real missingness pattern, a dataset-shared loading (60% of its variance), and paper × model implementation effects (0.5 noise SD):")
w()
w("| K true | SNR | K selected | dataset-similarity recovery (all / datasets in ≥ 2 papers) |")
w("|---|---|---|---|")
for s in d["simulation"]:
    rec = "–" if s["recovery_all"] is None else f"{s['recovery_all']:.2f} / {s['recovery_multi_paper_datasets']:.2f}"
    w(f"| {s['K_true']} | {s['snr']} | {s['K_selected_cv']} | {rec} |")
w()
w("With the paper × model offset, selection never over-shoots K; at low signal it under-shoots. Without the offset (earlier run) it over-selected (K_true 1 → 2, 2 → 3): implementation effects masquerade as capabilities, which is why the current site's K = 3 should not be read as three capabilities.")
w()
w("## 3. What organises the datasets")
w()
a = d["metadata_association_multi_paper"]
w("Share of variance in dataset loadings explained by each label (datasets reported by ≥ 2 papers; permutation null shuffles labels across datasets):")
w()
w("| label | R² | null mean | p |")
w("|---|---|---|---|")
for c, v in a.items(): w(f"| {c} | {v['r2']:.2f} | {v['null_mean']:.2f} | {v['p_value']:.3f} |")
w()
w(f"Dataset-to-dataset similarity is **not published**: simulated recovery of the similarity geometry on this mask stays below 0.7 (geometry_recoverable = {d['geometry_recoverable']}). The evidence supports how many dimensions there are and what label aligns with them, not which specific datasets are near-duplicates.")
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
w("Reported separation = model-count-weighted SD of reported scores within the dataset's comparisons, over each paper's own GeoFM set (note Eq. 10: not quality). Shared signal = |λ_d|², shared-capability variance in units of residual variance (residual = stable task-specific interaction + evaluation noise, not separable from single scores). Info share = Shapley share of V(A) = log det(I + Σ λ_dλ_d′) among these datasets (Eq. 8; each dataset once). LOPO ρ = mean leave-one-paper-out Spearman of its tasks (structured / one ordering).")
w()
w("| dataset | domain | papers | tasks | GeoFMs/task | reported separation (pts) | shared signal | info share (± MC SE) | LOPO ρ |")
w("|---|---|---|---|---|---|---|---|---|")
ds = [(n, x) for n, x in d["datasets"].items() if x["papers"] >= 2]
ds.sort(key=lambda t: -(t[1]["info_share_among_multi_paper"] or 0))
f = lambda v, p=2: "–" if v is None else f"{v:.{p}f}"
for n, x in ds:
    w(f"| {n} | {str(x['domain']).split('· ')[-1]} | {x['papers']} | {x['tasks']} | {x['models_per_task']:.0f} | {f(x['reported_separation_pts'],1)} | {f(x['shared_signal_to_residual'])} | {f(x['info_share_among_multi_paper'],3)} (± {f(x['info_share_mc_se'],3)}) | {f(x['lopo_rho'])} / {f(x['lopo_rho_one_ordering'])} |")
w()
n1 = sum(1 for x in d["datasets"].values() if x["papers"] < 2)
w(f"{n1} further datasets are reported by a single paper; their loadings cannot be separated from that paper's GeoFM selection and implementation, so no dataset-level quantity is reported for them.")
w()
w(f"Shared signal vs GeoFMs per comparison: Spearman {d['signal_vs_models_per_task_spearman']} (the ridge shrinks small comparisons; read signal alongside GeoFMs/task).")
w()
w("## 6. Limits and open decisions")
w()
w("- **Main-text rule loses some results.** Several papers' main-text tables are condensed versions of appendix tables that the workbook extracted instead (e.g. Galileo, SatCLIP, Prithvi-EO-2.0 GEO-Bench results). Those main-text numbers are currently lost. Decide whether to re-extract the main tables or keep appendix rows that a main table reprints.")
w("- **GEO-Bench-2 leaderboard** is excluded as not a paper's main text; `--include-leaderboard` adds it.")
w("- Uncategorised models were scoped by hand (`data/model_scope.json`); `vanilla_mae` and `convmae` are excluded because the same id is EO-pretrained in some papers and ImageNet-pretrained in others.")
w("- Geography and time blocks of Eq. 11 are not fitted: the workbook has no geography/time metadata, and the evaluation design is not crossed enough to separate them from dataset.")
w("- K is a lower bound at the signal levels seen here (simulation under-shoots at SNR ≤ 1).")
(ROOT / "docs" / "dataset-analysis.md").write_text("\n".join(L) + "\n")
print("wrote docs/dataset-analysis.md")
