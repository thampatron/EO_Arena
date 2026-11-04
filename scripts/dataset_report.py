#!/usr/bin/env python3
"""Render docs/dataset-analysis.md from data/dataset_analysis.json (v2), with a sensitivity table against
data/dataset_analysis_v1.json and any data/dataset_analysis_sens_*.json runs."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
d = json.loads((ROOT / "data" / "dataset_analysis.json").read_text())
L = []
def w(s=""): L.append(s)
def ci(x, p=2): return f"{x['mean']:+.{p}f} (90% CI {x['ci90'][0]:+.{p}f} to {x['ci90'][1]:+.{p}f})"
def credible(x): return x["ci90"][0] > 0 or x["ci90"][1] < 0
f = lambda v, p=2: "–" if v is None else f"{v:.{p}f}"

o, sc, K, off, g = d["overlap"], d["scope"], d["K"], d["offset"], d["lopo_gain"]
lt = K["lopo_by_spec_and_K"][off["chosen"]]
bestK, Kc = K["best"], K["chosen"]
ho = d["heldout_cells_within_paper"]
rel = d["seed_noise_reliability"]; rep = d["reproducibility"]
seen = next((v for k, v in g.items() if k.startswith("dataset_seen_in_other_sources")), None)
unseen = next((v for k, v in g.items() if k.startswith("dataset_only_in_held_out_source")), None)
assoc = d["metadata_association_multi_source"]
sig_labels = [c for c, v in assoc.items() if min(v["full_loading"]["p_bonferroni_4_labels"], v["direction_only"]["p_bonferroni_4_labels"]) < 0.05]

w("# What existing benchmarks measure: dataset-level latent-factor analysis (v2)")
w()
w(f"Analysis of {d['as_of']} on the GeoFM meta-analysis workbook v4, following *GeoFM Benchmark Scoring* (S. Wang, Oct 2026). Object of study: the benchmark **datasets** — what they measure, how much they overlap, whether independent groups agree on the model differences they show, and how reliably they separate GeoFMs where seed noise is reported. Model capability vectors are nuisance parameters; nothing here ranks models. Every analysis decision, with its justification and a switch to undo it, is in [`analysis-decisions.md`](analysis-decisions.md). Built by `scripts/build_dataset_analysis.py`; numbers in `data/dataset_analysis.json`.")
w()

# ------------------------------------------------------------------ findings
w("## Findings")
w()
wp = ho[str(bestK)]["pair_acc"] if str(bestK) in ho else ho["1"]["pair_acc"]; op = lt[str(bestK)]["acc_struct"]
w(f"1. **GeoFM orderings are far more consistent within a paper than across papers.** A paper's own other comparisons predict a GeoFM's held-out position with {100*wp:.0f}% pairwise accuracy (a per-paper model offset alone: {100*ho['0']['pair_acc']:.0f}%); the rest of the literature predicts a new paper's orderings with {100*op:.0f}% (Spearman ρ = {lt[str(bestK)]['rho_struct']:.2f}). Much of what a paper reports as a GeoFM's advantage is specific to that paper's model set, protocol and implementation.")
k1, kb = g["K1_vs_naive_leaderboard"], g["bestK_vs_naive_leaderboard"]
board = lt[next(iter(lt))]["rho_board"]
simK = d.get("simulation_K") or []
under = [x for x in simK if x["K_selected"] < x["K_true"]]
power = (f" Simulation on this evidence: the selection rule picks " + ", ".join(f"K = {x['K_selected']} when the truth is {x['K_true']}" for x in simK) + (", so the test cannot detect moderate structure: absence of evidence, not evidence of a single dimension." if under else ".")) if simK else ""
if credible(kb) and kb["mean"] > 0:
    w(f"2. **One leaderboard does not describe GeoFM performance.** Out of paper, the best model (K = {kb['K']}, selected) beats a naive leaderboard (ρ = {board:.2f}) by {ci(kb)}. The smallest K not credibly worse than the best is {Kc}.{power}")
else:
    w(f"2. **Out of paper, no multi-factor model beats a single ranking.** A naive leaderboard (each GeoFM's mean within-comparison z-score in the other sources) predicts a new source's orderings with ρ = {board:.2f}; the best structured model (K = {kb['K']}, selected among 12 configurations) differs by {ci(kb)}. Extra dimensions fit within papers but do not transfer across them.{power} (A one-factor structured model scores below the naive leaderboard, {ci(k1)}, because it predicts each held-out task's loading from dataset, protocol and sensor blocks whose sign can be wrong; that is a weakness of the predictor, not evidence against a single ranking.)")
if seen:
    w(f"3. **What a dataset measures {'carries over' if credible(seen) and seen['mean']>0 else 'does not measurably carry over'} across papers.** For datasets other sources also report, the dataset-structured prediction differs from the model's own single ordering by {ci(seen)}" + (f"; for datasets seen only in the held-out source (protocol and sensor carry the prediction) by {ci(unseen)}." if unseen else ".") + (" Dataset-to-dataset similarity is recoverable and reported." if d["geometry_recoverable"] else " Dataset-to-dataset similarity is not recoverable on this evidence and is not reported."))
w(f"4. **Metadata labels {'partly organise' if sig_labels else 'do not credibly organise'} the datasets.** " + (f"{', '.join(sig_labels)} survive(s) correction for the four labels tested." if sig_labels else "Domain, subdomain, task type and sensor all fail after correction for the four labels tested."))
if rel["by_dataset_protocol"]:
    bd = rel["by_dataset_protocol"]; hi = sum(1 for x in bd if x["score"] >= 0.8); lo = sum(1 for x in bd if x["score"] < 0.5)
    w(f"5. **Seed-noise reliability (note Eq. 6) is now measurable for {len(bd)} dataset × protocol pairs** ({rel['comparisons']} comparisons with seed SDs for ≥ 3 GeoFMs): {hi} have ≥ 80% of their model spread repeatable under re-seeding, {lo} have < 50%. This is reliability within one implementation, not agreement across groups.")
rs, rl = rep["strict"], rep["loose"]
w(f"6. **Independent groups rarely evaluate the same GeoFMs on the same dataset.** With appendix tables and the GEO-Bench-2 leaderboard, cross-source reproducibility is estimable for {len(rs['estimable'])} strict and {len(rl['estimable'])} loose dataset groups. Standardised re-evaluation of the same GeoFMs by different groups is the missing evidence.")
w()

# ------------------------------------------------------------------ 1 evidence
w("## 1. Evidence base")
w()
w(f"{sc['rows_in']:,} extracted results → **{sc['rows_kept']:,}** kept (configuration: " + ", ".join(f"{k}={v}" for k, v in d["config"].items()) + "). Rules in order:")
w()
w("| Rule | Rows dropped |"); w("|---|---|")
for s in sc["dropped"]: w(f"| {s['rule']} | {s['dropped']:,} |")
w()
if sc.get("reprint_pairs"):
    w("Reprinting papers (kept only in the earliest source): " + "; ".join(f"{p['later']} ← {p['earlier']} ({p['shared_cells']} cells, {100*p['identical_share']:.0f}% identical)" for p in sc["reprint_pairs"]) + ".")
    w()
w(f"Imagery comparisons with ≥ 4 GeoFMs: **{o['models']} GeoFMs × {o['tasks']} tasks** ({o['datasets']} datasets, {o['sources']} sources: papers plus the GEO-Bench-2 leaderboard), {100*o['density']:.1f}% of cells observed, median {o['models_per_task_median']:.0f} GeoFMs per comparison; {o['tasks_from_appendix']} comparisons come from appendix tables, {o['tasks_from_leaderboard']} from the leaderboard, {o['tasks_logerr']} are regression tasks. {o['models_in_1_source']} of {o['models']} GeoFMs appear in a single source, {o['models_in_3plus_sources']} in three or more; {o['datasets_in_2plus_sources']} of {o['datasets']} datasets are reported by more than one source; {o['single_domain_sources']} sources cover a single domain.")
w()

# ------------------------------------------------------------------ 2 within vs out of paper
w("## 2. Within-paper vs out-of-paper consistency")
w()
w("Held-out cells (a random fifth of results hidden and predicted from everything else, including the same paper's other comparisons) vs leave-one-paper-out (all of a source's comparisons hidden). Pairwise ordering accuracy, 50% = chance:")
w()
w("| | within paper (held-out cells) | out of paper (leave-one-paper-out) |"); w("|---|---|---|")
for k_ in sorted(ho, key=int):
    op_ = lt.get(k_, {}).get("acc_struct")
    w(f"| K = {k_}{' (paper offset only)' if k_ == '0' else ''} | {100*ho[k_]['pair_acc']:.1f}% | {'–' if op_ is None else f'{100*op_:.1f}%'} |")
w()

# ------------------------------------------------------------------ 3 one leaderboard / K / offset
w("## 3. How many shared dimensions? (the note's one-leaderboard test)")
w()
w("Model: y_mt = μ_t + λ_t′θ_m + c_{m,p(t)} + η_mt, each task in units of its residual SD (pooled prior within metric family); λ_t = dataset + protocol-family + sensor blocks + task part (Eq. 11/12 group ridge); c = paper × model implementation offset. Leave-one-paper-out Spearman ρ of predicted vs reported within-task order (naive leaderboard = mean within-comparison z-score in all other sources, a K-independent single ranking):")
w()
w("| offset | " + " | ".join(f"K={k}" for k in lt) + " | naive leaderboard |"); w("|---|" + "---|" * (len(lt) + 1))
for s, row in K["lopo_by_spec_and_K"].items():
    w(f"| {s}{' (chosen)' if s == off['chosen'] else ''} | " + " | ".join(f"{row[k]['rho_struct']:.3f}" for k in row) + f" | {row[next(iter(row))]['rho_board']:.3f} |")
w()
if off["paired_vs_chosen"]:
    w("Offset choice (D8): " + "; ".join(f"{s} (K={v['K']}) minus chosen (K={v['vs_K']}): {ci(v)}" for s, v in off["paired_vs_chosen"].items()) + ".")
    w()
w(f"K (D9): best K = {bestK}; chosen (smallest not credibly worse) K = {Kc}. Paired differences to the best: " + ("; ".join(f"K={k}: {ci(v)}" for k, v in K["paired_vs_best"].items()) or "–") + ".")
w()
w(f"Against a single ranking (naive leaderboard, ρ = {lt[next(iter(lt))]['rho_board']:.3f}): K = 1 {ci(g['K1_vs_naive_leaderboard'])}; K = {Kc} (chosen) {ci(g['K_chosen_vs_naive_leaderboard'])}; K = {kb['K']} (best, selected — optimistic) {ci(kb)}.")
w()
if d["simulation_offset"]:
    w("**What the offset costs (simulation on the real mask, true K = 2 with dataset-shared loadings, SNR 1).** Recovery = correlation of true and estimated dataset-similarity structure among datasets in ≥ 2 sources; dataset gain = how much the dataset-structured prediction beats the model's own single ordering out of paper.")
    w()
    w("| implementation effects | offset | LOPO ρ | dataset gain (seen datasets) | geometry recovery |"); w("|---|---|---|---|---|")
    for s in d["simulation_offset"]:
        w(f"| {s['paper_effect']} SD | {s['offset']} | {s['lopo_rho']:.3f} | {s['dataset_gain_seen']:+.3f} | {s['recovery_multi_source_datasets']:.2f} |")
    w()
if d["simulation_K"]:
    w("**Can leave-one-paper-out recover K?** (chosen offset, SNR 1)")
    w()
    w("| K true | K chosen by the rule | best K | LOPO ρ by K |"); w("|---|---|---|---|")
    for s in d["simulation_K"]: w(f"| {s['K_true']} | {s['K_selected']} | {s['best_K']} | " + ", ".join(f"K{k}: {v:.3f}" for k, v in s["lopo_rho"].items()) + " |")
    w()

# ------------------------------------------------------------------ 4 datasets
w("## 4. Do datasets measure different things?")
w()
if seen: w(f"Out of paper, for datasets also reported by other sources: {ci(seen)}." + (f" Datasets seen only in the held-out source: {ci(unseen)}." if unseen else ""))
w()
w("Variance in dataset loadings explained by each label, over datasets reported by ≥ 2 sources (blank labels missing; permutation null over datasets; Bonferroni over 4 labels). 'Direction only' asks what a dataset measures, not how strongly it separates GeoFMs:")
w()
w("| label | R² (full) | null | p (Bonf.) | R² (direction) | null | p (Bonf.) | datasets |"); w("|---|---|---|---|---|---|---|---|")
for c, v in assoc.items():
    a, b = v["full_loading"], v["direction_only"]
    w(f"| {c} | {a['r2']:.2f} | {a['null_mean']:.2f} | {a['p_bonferroni_4_labels']:.2f} | {b['r2']:.2f} | {b['null_mean']:.2f} | {b['p_bonferroni_4_labels']:.2f} | {a['n']} |")
w()
w("Dataset-to-dataset similarity " + ("is reported in the JSON (`nearest`) for datasets in ≥ 2 sources: simulated recovery on this mask ≥ 0.7." if d["geometry_recoverable"] else "is **not published**: simulated recovery on this mask is below 0.7."))
w()

# ------------------------------------------------------------------ 5 reliability
w("## 5. Seed-noise reliability where it is reported (note Eq. 3–6)")
w()
if rel["by_dataset_protocol"]:
    w(f"Comparisons where ≥ 3 GeoFMs report a seed SD: {rel['comparisons']}. σ = median seed SD of one evaluation (points, or log-error ×100 for regression); spread = SD of the reported scores; score = τ²/(τ²+σ²) with τ² = spread² − σ²/n_reps: the share of the comparison's model differences that survives re-seeding, for its models and implementation. 'If single runs' treats every reported value as one run (most conservative). {100*rel['n_reps_assumed_3_share']:.0f}% of comparisons do not state how many runs a reported mean averages; 3 is assumed.")
    w()
    w("| dataset | protocol | comparisons | sources | GeoFMs | σ | spread | score (range) | lowest 5% bound | if single runs |"); w("|---|---|---|---|---|---|---|---|---|---|")
    for x in sorted(rel["by_dataset_protocol"], key=lambda x: (-x["sources"], x["score"])):
        w(f"| {x['dataset']} | {x['protocol']} | {x['comparisons']} | {x['sources']} | {x['models_median']:.0f} | {x['sigma_median']:.2f} | {x['spread_median']:.2f} | {x['score']:.2f} ({x['score_min']:.2f}–{x['score_max']:.2f}) | {f(x['score_lo_min'])} | {x['score_if_single_runs']:.2f} |")
    w()
else:
    w("No comparison reports seed SDs for ≥ 3 GeoFMs in this configuration.")
    w()

# ------------------------------------------------------------------ 6 reproducibility
w("## 6. Do independent sources agree? (cross-source reproducibility)")
w()
for nm_, R in (("Strict", rs), ("Loose", rl)):
    w(f"**{nm_}** — {R['grouping']}; ≥ {R['min_shared']} GeoFMs shared, ≥ {R['min_df']} residual df: {R['groups_with_2plus_sources']} groups reported by ≥ 2 sources, {R['with_3plus_shared']} share ≥ 3 GeoFMs, {R['with_5plus_shared']} share ≥ 5; estimable: {len(R['estimable'])}.")
    w()
    if R["estimable"]:
        w("| group | sources | GeoFMs | median Kendall τ between sources | cross-source disagreement σ_xp | stable between-model SD | agreement τ²/(τ²+σ²_xp) (90% CI) |"); w("|---|---|---|---|---|---|---|")
        for x in R["estimable"]:
            w(f"| {x['group']} | {x['n_papers']} | {x['n_models']} | {x['kendall_tau_median']:.2f} | {x['sigma_xp']:.2f} | {x['tau_b']:.2f} | {x['reproducibility']:.2f} ({f(x['rep_lo'])}–{f(x['rep_hi'])}) |")
        w()
w("σ_xp is disagreement between implementations about the same GeoFM (protocol and implementation differences plus seed noise of a mean); it is not seed noise.")
w()

# ------------------------------------------------------------------ 7 datasets table
w("## 7. Datasets reported by ≥ 2 sources (descriptive)")
w()
w("Reported separation = model-count-weighted SD of reported scores within the dataset's comparisons (points-scale comparisons only), over each source's own GeoFMs (note Eq. 10: not quality). LOPO ρ = leave-one-paper-out Spearman over the dataset's comparisons at the best K (structured / naive leaderboard), with comparisons and median GeoFMs behind it.")
w()
w("| dataset | domain | sources | comparisons | smallest | reported separation | LOPO ρ: structured / leaderboard (n, GeoFMs) |"); w("|---|---|---|---|---|---|---|")
for n, x in sorted(((n, x) for n, x in d["datasets"].items() if x["sources"] >= 2), key=lambda t: (-t[1]["sources"], -t[1]["comparisons"])):
    lo_ = f"{f(x['lopo_rho'])} / {f(x['lopo_rho_naive_leaderboard'])} ({x['lopo_tasks']}, {f(x['lopo_models_median'],0)})" if x["lopo_tasks"] else "–"
    w(f"| {n} | {str(x['domain']).split('· ')[-1]} | {x['sources']} | {x['comparisons']} | {x['smallest_comparison']} | {f(x['reported_separation_pts'],1)} | {lo_} |")
w()
w(f"{sum(1 for x in d['datasets'].values() if x['sources'] < 2)} further datasets are reported by a single source; no dataset-level quantity is reported for them.")
w()

# ------------------------------------------------------------------ 8 sensitivity
w("## 8. Sensitivity: which findings depend on the analysis decisions")
w()
runs = [("v1 (main text, no leaderboard, no regression, offset all)", ROOT / "data" / "dataset_analysis_v1.json")] + \
       [(p.stem.replace("dataset_analysis_sens_", "v2 · "), p) for p in sorted((ROOT / "data").glob("dataset_analysis_sens_*.json"))] + [("**v2 (this report)**", ROOT / "data" / "dataset_analysis.json")]
def labs(a_): return ", ".join(c for c, v in a_.items() if min(v["full_loading"]["p_bonferroni_4_labels"], v["direction_only"]["p_bonferroni_4_labels"]) < 0.05) or "none"
def head(j):
    if j.get("version") == 2:
        g_ = j["lopo_gain"]; bk_ = j["K"]["best"]
        se = next((v for k, v in g_.items() if k.startswith("dataset_seen_in_other_sources")), None)
        return dict(ev=f"{j['overlap']['models']}×{j['overlap']['tasks']}, {j['overlap']['sources']} src", multi=j["overlap"]["datasets_in_2plus_sources"], K=f"{j['K']['chosen']} / {bk_}",
                    off=j["offset"]["chosen"], k1=ci(g_["K1_vs_naive_leaderboard"]), kb=ci(g_["bestK_vs_naive_leaderboard"]), seen=ci(se) if se else "–",
                    lab=labs(j["metadata_association_multi_source"]), geo="yes" if j["geometry_recoverable"] else "no", rel=str(j["seed_noise_reliability"]["comparisons"]),
                    rep=f"{len(j['reproducibility']['strict']['estimable'])} / {len(j['reproducibility']['loose']['estimable'])}")
    g_ = j["lopo_gain_vs_one_ordering"]; se = g_.get("dataset_seen_in_other_papers")
    return dict(ev=f"{j['overlap']['models']}×{j['overlap']['tasks']}, {j['overlap']['papers']} src", multi=j["overlap"]["datasets_in_2plus_papers"],
                K=f"{j['K']['chosen']} / {g_.get('bestK_vs_naive_leaderboard', {}).get('K', '–')}", off="all", k1=ci(g_["K1_vs_naive_leaderboard"]),
                kb=ci(g_["bestK_vs_naive_leaderboard"]) if "bestK_vs_naive_leaderboard" in g_ else "–", seen=ci(se) if se else "–",
                lab=labs(j["metadata_association_multi_paper"]), geo="yes" if j["geometry_recoverable"] else "no", rel="0", rep=f"{len(j['reproducibility'])} / –")
cols = [("ev", "evidence (GeoFMs × tasks)"), ("multi", "datasets in ≥ 2 sources"), ("K", "K chosen / best"), ("off", "offset"), ("k1", "K=1 vs leaderboard"), ("kb", "best K vs leaderboard"),
        ("seen", "dataset transfer (seen)"), ("lab", "labels surviving correction"), ("geo", "similarity recoverable"), ("rel", "comparisons with seed-noise score"), ("rep", "reproducibility groups (strict / loose)")]
H = [(nm_, head(json.loads(p.read_text()))) for nm_, p in runs if p.exists()]
w("| | " + " | ".join(nm_ for nm_, _ in H) + " |"); w("|---|" + "---|" * len(H))
for k_, lab in cols: w(f"| {lab} | " + " | ".join(str(h[k_]) for _, h in H) + " |")
w()

# ------------------------------------------------------------------ 9 limits
w("## 9. Limits")
w()
w("- Single reported scores: the residual mixes stable task-specific interaction with evaluation noise (note Eq. 9); seed-noise scores exist only where seed SDs are printed, and describe one implementation.")
w("- The best-K figures are selected among 12 configurations and are optimistic (D14); the leave-one-paper-out test has limited power on this evidence (§3 simulation).")
w("- In single-domain sources, domain-specific capability and implementation effects are not separable (D8).")
w("- Geography and time blocks of Eq. 11 are not fitted: no geography/time metadata, and the evaluation design is not crossed enough to separate them from dataset.")
w("- Points near the ceiling compress differences for classification benchmarks (D4).")
(ROOT / "docs" / "dataset-analysis.md").write_text("\n".join(L) + "\n")
print("wrote docs/dataset-analysis.md")
