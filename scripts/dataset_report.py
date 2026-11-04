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

rel = d["seed_noise_reliability"]; rep = d["reproducibility"]
seen = next((v for k, v in g.items() if k.startswith("dataset_seen_in_other_sources")), None)
unseen = next((v for k, v in g.items() if k.startswith("dataset_only_in_held_out_source")), None)
assoc = d["metadata_association_multi_source"]
sig_labels = [c for c, v in assoc.items() if min(v["full_loading"]["p_bonferroni_4_labels"], v["direction_only"]["p_bonferroni_4_labels"]) < 0.05]

w("# What existing benchmarks measure: dataset-level analysis (v2.1)")
w()
w(f"Analysis of {d['as_of']} on the GeoFM meta-analysis workbook v4, following *GeoFM Benchmark Scoring* (S. Wang, Oct 2026). Object of study: the benchmark **datasets** — what they measure, how much they overlap, whether independent groups agree on the model differences they show, and how reliably they separate GeoFMs where seed noise is reported. Model capability vectors are nuisance parameters; nothing here ranks models. Every analysis decision, with its justification and a switch to undo it, is in [`analysis-decisions.md`](analysis-decisions.md). Built by `scripts/build_dataset_analysis.py`; numbers in `data/dataset_analysis.json`.")
w()

# ------------------------------------------------------------------ findings
w("## Findings")
w()
TA = d["tau_tests"]; cells = {(c_["same_dataset"], c_["same_source"]): c_ for c_ in TA["cells"]}
di, ps = TA["all"]["dataset_identity"], TA["all"]["paper_specificity"]
dpf, dcb, dpd = TA["same_protocol_family"]["dataset_identity"], TA["excluding_flagged_source_pairs"]["dataset_identity"], TA["all"]["dataset_identity_per_dataset"]
def tci(x): return f"{x['estimate']:+.2f} (90% CI {x['ci90'][0]:+.2f} to {x['ci90'][1]:+.2f})"
def tcred(x): return x["ci90"][0] > 0
RB = TA.get("robustness", {})
top_ds = list((RB.get("same_dataset_pairs_by_dataset") or {}).items())[:6]
share_top = sum(v for _, v in top_ds) / max(sum((RB.get("same_dataset_pairs_by_dataset") or {}).values()), 1)
w(f"1. **Where several groups evaluate the same dataset, its GeoFM ordering carries over — directionally robust, narrow in scope.** Same-dataset comparisons by different sources agree more (Kendall τ = {cells[(True, False)]['mean_tau']:.2f}) than different-dataset comparisons across sources ({cells[(False, False)]['mean_tau']:.2f}); under a single ranking plus noise the two would be equal." + (f" The evidence comes from {RB['source_pairs_with_same_dataset_pairs']} source pairs: {RB['positive_contrasts']} of them show a positive contrast (one-sided sign test p = {RB['sign_test_p_one_sided']:.3f}; unweighted mean {RB['unweighted_mean_contrast']:+.2f}), and leaving out any one source keeps it between {RB['leave_one_source_out_range'][0]:+.2f} and {RB['leave_one_source_out_range'][1]:+.2f}. {100*share_top:.0f}% of the same-dataset pairs come from six datasets ({', '.join(k for k, _ in top_ds)}), mostly GEO-Bench-family benchmarks, so the claim holds for widely re-evaluated benchmarks, not datasets in general. Possible shared evaluation code between sources cannot be ruled out from values alone." if RB else "") + f" Pooled estimate {tci(di)}; the interval is wide and skewed because few source pairs are informative." + (f" This estimate is conservative: pairs sharing only four GeoFMs pull it toward 0, and among pairs sharing ≥ 5 it is {RB['sensitivity_post_hoc']['min_shared_5']['pair_weighted']:+.2f} (post hoc, {RB['sensitivity_post_hoc']['min_shared_5']['source_pairs']} source pairs; §2)." if RB.get('sensitivity_post_hoc', {}).get('min_shared_5') else ""))
w(f"2. **Orderings are also paper-specific.** Different datasets evaluated in the same paper agree more (τ = {cells[(False, True)]['mean_tau']:.2f}) than across papers ({cells[(False, False)]['mean_tau']:.2f}): {tci(ps)}. A paper's task suite, protocol, model set or implementation shapes its orderings; these cannot be separated with published results.")
k1g, kbg, kcg = g["K1_vs_leaderboard"], g["bestK_vs_leaderboard"], g["Kchosen_vs_leaderboard"]
ank = g.get("anchored_bestK_vs_leaderboard_same_half")
simK = d.get("simulation_K") or []
sk = "; ".join(f"K_true = {x['K_true']} → selected {x['K_selected']} (best {x['best_K']})" for x in simK)
kv = K["paired_vs_best"]; k1best = kv.get("1") or kv.get(1)
w(f"3. **A dataset- and protocol-aware model predicts new papers' orderings better than a fixed leaderboard; whether that needs more than one dimension is suggestive only.** Predicting a held-out source from the other sources, the best structured model (K = {kbg['K']}) beats the naive leaderboard by {ci(kbg)} — but this is the best of 12 configurations scored on the same criterion; the prespecified rule's K = {Kc} gives {ci(kcg)}. Beating the leaderboard is not itself evidence of several dimensions: in simulation with a single true dimension a one-factor structured model also beats it, by learning each dataset's direction. The dimensionality test proper — K = {kbg['K']} against K = 1 within the same model — gives {('+' if -k1best['mean']>=0 else '') + format(-k1best['mean'], '.2f')} (90% CI {-k1best['ci90'][1]:+.2f} to {-k1best['ci90'][0]:+.2f}), also after selection." + (f" Anchored check: {ci(ank)}." if ank else "") + " Calibrated simulation recovers K = 1, 2, 3 under this rule, but in a world easier than the real one (higher predictability, weaker paper effects), so it does not settle the number of dimensions.")
seen_ = next((v for k, v in g.items() if k.startswith("dataset_seen_in_other_sources")), None)
if seen_:
    w(f"4. **The latent model does not yet turn dataset identity into out-of-paper predictions.** Predicting a held-out comparison from its dataset, protocol and sensor blocks alone, for datasets other sources report, differs from the model's own single ordering by {ci(seen_)}. Finding 1 shows the information exists in the raw orderings; a likely (untested) reason the model cannot use it is that each dataset's loading is estimated from few comparisons (median 2). Dataset-to-dataset similarity is therefore not published (D13).")
w(f"5. **Metadata labels {'partly organise' if sig_labels else 'do not credibly organise'} the datasets.** " + (f"{', '.join(sig_labels)} survive(s) correction for the four labels tested." if sig_labels else "Domain, subdomain, task type and sensor all fail after correction for the four labels tested." + " Domain is the label closest to the threshold: it survives correction in two sensitivity runs (main text only; no regression tasks; p ≈ 0.04), so whether domain organises datasets is unresolved rather than ruled out (§8)."))
if rel["by_dataset_protocol"]:
    bd = rel["by_dataset_protocol"]
    w(f"6. **Where seed noise is reported, model differences mostly survive re-seeding — with wide uncertainty.** {rel['comparisons']} comparisons (≥ 6 GeoFMs, seed SDs printed for ≥ 3) across {len(bd)} dataset × protocol pairs: {rel['comparisons_lo_ge_0_8']} have a 90% lower bound ≥ 0.8 on the share of model spread that survives re-seeding (note Eq. 6), {rel['comparisons_lo_ge_0_5']} ≥ 0.5; comparisons from one paper share settings and are not independent (per dataset × protocol counts in §5). This is reliability within one implementation, and rounding of printed SDs is not yet propagated.")
rs, rl = rep["strict"], rep["loose"]
est = rs["estimable"] + [x for x in rl["estimable"] if x["group"] not in {y["group"] for y in rs["estimable"]}]
flagged = {tuple(sorted((x_["a"], x_["b"]))) for x_ in TA.get("flagged_source_pairs_detail", [])}
w(f"7. **Independent groups rarely evaluate the same GeoFMs on the same dataset and protocol.** Cross-source reproducibility is estimable for {len(rs['estimable'])} strict and {len(rl['estimable'])} loose dataset groups" + ((": " + "; ".join(f"{x['group'].split(' | ')[0]} ({x['n_papers']} sources, {x['n_models']} GeoFMs, agreement {x['reproducibility']:.2f})" for x in est) + ". Close values between sources can mean a shared evaluation codebase rather than independent replication.") if est else ".") + " Standardised re-evaluation of the same GeoFMs by different groups is the missing evidence.")
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

# ------------------------------------------------------------------ 2 tau tests
w("## 2. Model-free tests: do orderings agree across comparisons? (D15)")
w()
w(f"Kendall τ between the GeoFM orderings of every pair of comparisons sharing ≥ 4 GeoFMs (median {TA['median_shared_models']:.0f}). 0 = unrelated orderings, 1 = identical.")
w()
w("| | different source | same source |"); w("|---|---|---|")
for sd_ in (False, True):
    w(f"| {'same dataset' if sd_ else 'different dataset'} | {cells[(sd_, False)]['mean_tau']:.3f} ({cells[(sd_, False)]['pairs']:,} pairs) | {cells[(sd_, True)]['mean_tau']:.3f} ({cells[(sd_, True)]['pairs']:,} pairs) |")
w()
w("| contrast | all pairs | same protocol family | without flagged source pairs |"); w("|---|---|---|---|")
for k_, lab in (("dataset_identity", "dataset identity (same − different dataset, across sources)"), ("dataset_identity_per_dataset", "… each dataset as its own control"), ("paper_specificity", "paper specificity (same − different source, different datasets)")):
    w(f"| {lab} | {tci(TA['all'][k_])} | {tci(TA['same_protocol_family'][k_])} | {tci(TA['excluding_flagged_source_pairs'][k_])} |")
w()
fl = TA.get("flagged_source_pairs_detail", [])
if RB:
    w(f"Per source pair (cross-source pairs on the same dataset vs on different datasets): {RB['positive_contrasts']} of {RB['source_pairs_with_same_dataset_pairs']} positive, one-sided sign test p = {RB['sign_test_p_one_sided']:.3f}; leave-one-source-out range {RB['leave_one_source_out_range'][0]:+.2f} to {RB['leave_one_source_out_range'][1]:+.2f}.")
    w()
    w("| sources | same-dataset pairs | contrast | datasets |"); w("|---|---|---|---|")
    for x in RB["per_source_pair"]: w(f"| {' × '.join(x['sources'])} | {x['same_dataset_pairs']} | {x['contrast']:+.2f} | {', '.join(x['datasets'][:4])}{' …' if len(x['datasets']) > 4 else ''} |")
    w()
    SP = RB.get("sensitivity_post_hoc") or {}
    if SP:
        w("Sensitivity of the pooled contrast to pair overlap (post hoc: added after the main estimate was seen). Kendall τ over 4 shared GeoFMs is noisy and, where the shared GeoFMs are close in capability, pulled toward 0 in both cells. Weighting pairs by the inverse of τ's null variance, or requiring more shared GeoFMs, raises the contrast but rests on fewer source pairs:")
        w()
        w("| pairs sharing ≥ | same-dataset pairs | source pairs | pair-weighted | inverse-variance weighted |"); w("|---|---|---|---|---|")
        for k_, v_ in SP.items():
            w(f"| {k_.split('_')[-1]} GeoFMs | {v_['same_dataset_pairs']} | {v_['source_pairs']} | {v_['pair_weighted']:+.2f} (90% CI {v_['pair_weighted_ci90'][0]:+.2f} to {v_['pair_weighted_ci90'][1]:+.2f}) | {v_['inverse_variance']:+.2f} (90% CI {v_['inverse_variance_ci90'][0]:+.2f} to {v_['inverse_variance_ci90'][1]:+.2f}) |")
        w()
w("Possible shared-codebase source pairs (matched values within a median of 1 point): " + ("; ".join(f"{x['a']}–{x['b']} ({x['matched_cells']} cells, median |Δ| {x['median_abs_diff']})" for x in fl) if fl else "none") + ". Intervals: cluster bootstrap over sources (2,000 draws).")
w()

# ------------------------------------------------------------------ 3 one leaderboard / K / offset
w("## 3. How many shared dimensions? (the note's one-leaderboard test)")
w()
w("Model: y_mt = μ_t + λ_t′θ_m + c_{m,p(t)} + η_mt, each task in units of its residual SD (pooled prior within metric family); λ_t = dataset + protocol-family + sensor blocks + task part (Eq. 11/12 group ridge); c = paper × model implementation offset. Leave-one-paper-out Spearman ρ of predicted vs reported within-task order (naive leaderboard = mean within-comparison z-score in all other sources, a K-independent single ranking):")
w()
w("Block-predicted (primary, D9): nothing from the held-out comparison is used; the plain leaderboard likewise. Anchored (secondary): the comparison's loading is estimated from half its GeoFMs and the other half predicted; the leaderboard is scored on the same half.")
w()
w("| offset | " + " | ".join(f"anchored K={k}" for k in lt) + " | anchored leaderboard | " + " | ".join(f"blocks K={k}" for k in lt) + " | leaderboard |"); w("|---|" + "---|" * (2 * len(lt) + 2))
for s, row in K["lopo_by_spec_and_K"].items():
    f0 = row[next(iter(row))]
    w(f"| {s}{' (chosen)' if s == off['chosen'] else ''} | " + " | ".join(f"{row[k]['rho_struct']:.3f}" for k in row) + f" | {f0['rho_board']:.3f} | " + " | ".join(f"{row[k]['rho_anch']:.3f}" for k in row) + f" | {f0['rho_half_board']:.3f} |")
w()
if off["paired_vs_chosen"]:
    w("Offset choice (D8): " + "; ".join(f"{s} (K={v['K']}) minus chosen (K={v['vs_K']}): {ci(v)}" for s, v in off["paired_vs_chosen"].items()) + ".")
    w()
w(f"K (D9): best K = {bestK}; chosen (smallest not credibly worse) K = {Kc}. Paired differences to the best: " + ("; ".join(f"K={k}: {ci(v)}" for k, v in K["paired_vs_best"].items()) or "–") + ".")
w()
w(f"Against the leaderboard: K = 1 {ci(g['K1_vs_leaderboard'])}; K = {Kc} (chosen) {ci(g['Kchosen_vs_leaderboard'])}; K = {g['bestK_vs_leaderboard']['K']} (best, selected — optimistic) {ci(g['bestK_vs_leaderboard'])}. Anchored: K = 1 {ci(g['anchored_K1_vs_leaderboard_same_half'])}; K = {g['anchored_bestK_vs_leaderboard_same_half']['K']} {ci(g['anchored_bestK_vs_leaderboard_same_half'])}.")
w()
cal = d.get("simulation_calibration") or {}
if cal:
    w(f"**Calibrated simulation (D16).** A general factor (one leaderboard) plus specific factors, dataset-shared loadings and implementation effects, fitted on a {cal['grid_size']}-point grid to the real data: targets " + ", ".join(f"{k} {v:.3f}" for k, v in cal["targets"].items()) + "; achieved " + ", ".join(f"{k} {v:.3f}" for k, v in cal["achieved"].items()) + f" with general-factor mean {cal['chosen']['general_mean']}, SNR {cal['chosen']['snr']}, dataset share {cal['chosen']['dataset_share']}, implementation effect {cal['chosen']['paper_effect']} noise SD.")
    w()
if d["simulation_K"]:
    w("| K true | K selected by the rule | best K | ρ by K | leaderboard | best K − leaderboard |"); w("|---|---|---|---|---|---|")
    for x in d["simulation_K"]: w(f"| {x['K_true']} | {x['K_selected']} | {x['best_K']} | " + ", ".join(f"K{k}: {v:.3f}" for k, v in x["rho_by_K"].items()) + f" | {x['board']:.3f} | {ci(x['bestK_vs_board'])} |")
    w()
if d["simulation_offset"]:
    w("Offset options under the calibrated truth (K = 2):")
    w()
    w("| offset | ρ (K = 2) | leaderboard | dataset gain (seen datasets) | geometry recovery (≥ 2-source datasets) |"); w("|---|---|---|---|---|")
    for x in d["simulation_offset"]: w(f"| {x['offset']} | {x['rho']:.3f} | {x['board']:.3f} | {x['dataset_gain_seen']:+.3f} | {x['recovery_multi_source_datasets']:.2f} |")
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
gg_ = d.get("geometry_gate", {})
w("Dataset-to-dataset similarity " + ("is reported in the JSON (`nearest`) for datasets in ≥ 2 sources." if d["geometry_recoverable"] else
  f"is **not published** (D13): simulated recovery on this mask {'would allow it' if gg_.get('recoverable_in_simulation') else 'is too low'} (median {gg_.get('simulated_recovery_median')}), but " + ("dataset loadings do not credibly transfer across papers on the real data, so the estimated similarities would describe single papers, not datasets." if not gg_.get("dataset_loadings_transfer_out_of_paper") else "the recovery gate fails.")))
w()

# ------------------------------------------------------------------ 5 reliability
w("## 5. Seed-noise reliability where it is reported (note Eq. 3–6)")
w()
if rel["by_dataset_protocol"]:
    w(f"Comparisons where ≥ 3 GeoFMs report a seed SD: {rel['comparisons']}. σ = median seed SD of one evaluation (points, or log-error ×100 for regression); spread = SD of the reported scores; score = τ²/(τ²+σ²) with τ² = spread² − σ²/n_reps: the share of the comparison's model differences that survives re-seeding, for its models and implementation. 'If single runs' treats every reported value as one run (most conservative). {100*rel['n_reps_assumed_3_share']:.0f}% of comparisons do not state how many runs a reported mean averages; 3 is assumed. Printed SDs are floored at half their last printed digit ({rel.get('cells_sd_floored_to_print_precision', 0)} cells); comparisons need ≥ {rel.get('min_geofms', 6)} GeoFMs. Lower bounds ≥ 0.8: {rel.get('comparisons_lo_ge_0_8')} of {rel['comparisons']} comparisons; ≥ 0.5: {rel.get('comparisons_lo_ge_0_5')}.")
    w()
    w("| dataset | protocol | comparisons | sources | GeoFMs | σ | spread | score (range) | comparisons with lower bound ≥ 0.8 | lowest 5% bound | if single runs |"); w("|---|---|---|---|---|---|---|---|---|---|---|")
    for x in sorted(rel["by_dataset_protocol"], key=lambda x: (-x["sources"], x["score"])):
        w(f"| {x['dataset']} | {x['protocol']} | {x['comparisons']} | {x['sources']} | {x['models_median']:.0f} | {x['sigma_median']:.2f} | {x['spread_median']:.2f} | {x['score']:.2f} ({x['score_min']:.2f}–{x['score_max']:.2f}) | {x.get('comparisons_lo_ge_0_8', '–')} of {x['comparisons']} | {f(x['score_lo_min'])} | {x['score_if_single_runs']:.2f} |")
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
            w(f"| {x['group'].replace(' | ', ' · ')} | {x['n_papers']} | {x['n_models']} | {x['kendall_tau_median']:.2f} | {x['sigma_xp']:.2f} | {x['tau_b']:.2f} | {x['reproducibility']:.2f} ({f(x['rep_lo'])}–{f(x['rep_hi'])}) |")
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
       [(p.stem.replace("dataset_analysis_sens_", "v2 · "), p) for p in sorted((ROOT / "data").glob("dataset_analysis_sens_*.json"))] + [("**v2.1 (this report)**", ROOT / "data" / "dataset_analysis.json")]
def labs(a_): return ", ".join(c for c, v in a_.items() if min(v["full_loading"]["p_bonferroni_4_labels"], v["direction_only"]["p_bonferroni_4_labels"]) < 0.05) or "none"
def head(j):
    if j.get("version") == 2:
        g_ = j["lopo_gain"]; bk_ = j["K"]["best"]
        se = next((v for k, v in g_.items() if k.startswith("dataset_seen_in_other_sources")), None)
        k1_ = g_.get("K1_vs_leaderboard", g_.get("K1_vs_naive_leaderboard")); kb_ = g_.get("bestK_vs_leaderboard", g_.get("bestK_vs_naive_leaderboard"))
        ta_ = j.get("tau_tests", {}).get("all", {}).get("dataset_identity")
        kc_ = g_.get("Kchosen_vs_leaderboard"); pv_ = j["K"].get("paired_vs_best") or {}; p1_ = pv_.get("1") or pv_.get(1)
        dim_ = "–" if not p1_ or bk_ == 1 else f"{-p1_['mean']:+.2f} (90% CI {-p1_['ci90'][1]:+.2f} to {-p1_['ci90'][0]:+.2f})"
        gg_ = j.get("geometry_gate") or {}
        geo_ = (("not run" if gg_.get("simulated_recovery_median") is None else ("yes" if gg_.get("recoverable_in_simulation") else "no")) + " / " + ("yes" if gg_.get("dataset_loadings_transfer_out_of_paper") else "no")) if gg_ else ("yes" if j["geometry_recoverable"] else "no")
        return dict(ev=f"{j['overlap']['models']}×{j['overlap']['tasks']}, {j['overlap']['sources']} src", multi=j["overlap"]["datasets_in_2plus_sources"], K=f"{j['K']['chosen']} / {bk_}",
                    off=j["offset"]["chosen"], k1=ci(k1_), kc=ci(kc_) if kc_ else "–", kb=ci(kb_), dim=dim_, seen=ci(se) if se else "–", tau=tci(ta_) if ta_ else "–", tsp=(lambda r_: f"{r_['positive_contrasts']}/{r_['source_pairs_with_same_dataset_pairs']} (p = {r_['sign_test_p_one_sided']:.2f})" if r_ else "–")(j.get("tau_tests", {}).get("robustness")),
                    lab=labs(j["metadata_association_multi_source"]), geo=geo_, rel=str(j["seed_noise_reliability"]["comparisons"]),
                    rep=f"{len(j['reproducibility']['strict']['estimable'])} / {len(j['reproducibility']['loose']['estimable'])}")
    g_ = j["lopo_gain_vs_one_ordering"]; se = g_.get("dataset_seen_in_other_papers")
    return dict(ev=f"{j['overlap']['models']}×{j['overlap']['tasks']}, {j['overlap']['papers']} src", multi=j["overlap"]["datasets_in_2plus_papers"],
                K=f"{j['K']['chosen']} / {g_.get('bestK_vs_naive_leaderboard', {}).get('K', '–')}", off="all", k1=ci(g_["K1_vs_naive_leaderboard"]),
                kb=ci(g_["bestK_vs_naive_leaderboard"]) if "bestK_vs_naive_leaderboard" in g_ else "–", seen=ci(se) if se else "–",
                lab=labs(j["metadata_association_multi_paper"]), geo="yes" if j["geometry_recoverable"] else "no", rel="0", rep=f"{len(j['reproducibility'])} / –", tau="–", kc="–", dim="–", tsp="–")
cols = [("ev", "evidence (GeoFMs × tasks)"), ("multi", "datasets in ≥ 2 sources"), ("tau", "dataset identity, model-free τ (v2.1+)"), ("tsp", "τ: source pairs with positive contrast (sign test)"), ("K", "K chosen / best"), ("off", "offset"), ("k1", "K=1 vs leaderboard (block-predicted)"), ("kc", "chosen K vs leaderboard"), ("kb", "best K vs leaderboard (selected)"), ("dim", "best K minus K=1 (dimensionality, selected)"),
        ("seen", "dataset transfer (seen)"), ("lab", "labels surviving correction"), ("geo", "similarity gate: recoverable in simulation / loadings transfer"), ("rel", "comparisons with seed-noise score"), ("rep", "reproducibility groups (strict / loose)")]
H = [(nm_, head(json.loads(p.read_text()))) for nm_, p in runs if p.exists()]
w("| | " + " | ".join(nm_ for nm_, _ in H) + " |"); w("|---|" + "---|" * len(H))
for k_, lab in cols: w(f"| {lab} | " + " | ".join(str(h[k_]) for _, h in H) + " |")
w()
_J = [json.loads(p.read_text()) for _, p in runs if p.exists() and json.loads(p.read_text()).get("version") == 2]
def _dim(j):
    pv = j["K"].get("paired_vs_best") or {}; p1 = pv.get("1") or pv.get(1)
    return None if not p1 else (-p1["mean"], -p1["ci90"][1])
_d = [x for x in map(_dim, _J) if x]; _tau = [j["tau_tests"]["all"]["dataset_identity"] for j in _J]
_kc = [j["lopo_gain"].get("Kchosen_vs_leaderboard") for j in _J]
w(f"Across the {len(_J)} v2-code runs: the τ dataset-identity contrast is positive with a 90% interval above 0 in {sum(t['ci90'][0] > 0 for t in _tau)}; best K beats K = 1 with an interval above 0 in {sum(lo > 0 for _, lo in _d)} of {len(_d)} (range {min(m for m, _ in _d):+.2f} to {max(m for m, _ in _d):+.2f}; selected, so optimistic); the prespecified chosen K beats the leaderboard with an interval above 0 in {sum(1 for k in _kc if k and k['ci90'][0] > 0)}. Runs on main text only have the largest effects but rest on 4 source pairs for the τ test (D1).")
w()

# ------------------------------------------------------------------ 9 limits
w("## 9. Limits")
w()
w("- Single reported scores: the residual mixes stable task-specific interaction with evaluation noise (note Eq. 9); seed-noise scores exist only where seed SDs are printed, and describe one implementation.")
w("- The best-K figures are selected among 12 configurations and are optimistic (D14).")
w("- τ contrasts rest on a median of 4–5 shared GeoFMs per pair and on which GeoFMs happen to be shared; shared evaluation codebases can only be flagged from close values, not identified.")
w("- In single-domain sources, domain-specific capability and implementation effects are not separable (D8).")
w("- Geography and time blocks of Eq. 11 are not fitted: no geography/time metadata, and the evaluation design is not crossed enough to separate them from dataset.")
w("- Points near the ceiling compress differences for classification benchmarks (D4).")
w("- Seed-noise scores come only from papers that print seed SDs, which may be the more careful ones; a printed SD below 0.1 point (e.g. fMoW) makes the score close to 1 by construction.")
(ROOT / "docs" / "dataset-analysis.md").write_text("\n".join(L) + "\n")
print("wrote docs/dataset-analysis.md")
