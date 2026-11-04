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
w(f"1. **Datasets {'do' if tcred(di) else 'do not credibly'} carry their own GeoFM ordering across papers.** Over {cells[(True, False)]['pairs']:,} pairs of comparisons on the same dataset by different sources, orderings agree with Kendall τ = {cells[(True, False)]['mean_tau']:.2f}, against {cells[(False, False)]['mean_tau']:.2f} for different datasets across sources ({cells[(False, False)]['pairs']:,} pairs): a dataset-identity effect of {tci(di)} (cluster bootstrap over sources). It holds with each dataset as its own control ({tci(dpd)}), within the same protocol family ({tci(dpf)}) and without possible shared-codebase source pairs ({tci(dcb)}). Under a single ranking plus noise this contrast would be zero. Model-free; median {TA['median_shared_models']:.0f} shared GeoFMs per pair.")
w(f"2. **Orderings are also paper-specific.** Different datasets evaluated in the same paper agree more (τ = {cells[(False, True)]['mean_tau']:.2f}) than across papers ({cells[(False, False)]['mean_tau']:.2f}): {tci(ps)}. A paper's task suite, protocol, model set or implementation shapes its orderings; these cannot be separated with published results.")
ak1, akb, akc = g["anchored_K1_vs_board"], g["anchored_bestK_vs_board"], g["anchored_Kchosen_vs_board"]
simK = d.get("simulation_K") or []
sk = "; ".join(f"K_true = {x['K_true']} → selected {x['K_selected']} (best {x['best_K']})" for x in simK)
w(f"3. **Out of paper, more than one capability dimension {'beats' if credible(akb) and akb['mean'] > 0 else 'does not credibly beat'} a single leaderboard.** With each held-out comparison's loading estimated from half its GeoFMs and the other half predicted, the best model (K = {akb['K']}, selected among 12 configurations) differs from the naive leaderboard used the same way by {ci(akb)}; K = 1 by {ci(ak1)}. The smallest K not credibly worse than the best is {Kc}." + (f" Calibrated simulation of this rule: {sk}." if simK else ""))
seen_ = next((v for k, v in g.items() if k.startswith("dataset_seen_in_other_sources")), None)
if seen_:
    w(f"4. **The latent model does not yet turn dataset identity into out-of-paper predictions.** Predicting a held-out comparison from its dataset, protocol and sensor blocks alone, for datasets other sources report, differs from the model's own single ordering by {ci(seen_)}. Finding 1 shows the information is there; the estimated dataset loadings, from a median of 2 comparisons per dataset, are too noisy to carry it. Dataset-to-dataset similarity is therefore not published (D13).")
w(f"5. **Metadata labels {'partly organise' if sig_labels else 'do not credibly organise'} the datasets.** " + (f"{', '.join(sig_labels)} survive(s) correction for the four labels tested." if sig_labels else "Domain, subdomain, task type and sensor all fail after correction for the four labels tested."))
if rel["by_dataset_protocol"]:
    bd = rel["by_dataset_protocol"]
    w(f"6. **Where seed noise is reported, model differences mostly survive re-seeding — with wide uncertainty.** {rel['comparisons']} comparisons (≥ 6 GeoFMs, seed SDs printed for ≥ 3) across {len(bd)} dataset × protocol pairs: {rel['comparisons_lo_ge_0_8']} have a 90% lower bound ≥ 0.8 on the share of model spread that survives re-seeding (note Eq. 6), {rel['comparisons_lo_ge_0_5']} ≥ 0.5. This is reliability within one implementation.")
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
w("Possible shared-codebase source pairs (matched values within a median of 1 point): " + ("; ".join(f"{x['a']}–{x['b']} ({x['matched_cells']} cells, median |Δ| {x['median_abs_diff']})" for x in fl) if fl else "none") + ". Intervals: cluster bootstrap over sources (2,000 draws).")
w()

# ------------------------------------------------------------------ 3 one leaderboard / K / offset
w("## 3. How many shared dimensions? (the note's one-leaderboard test)")
w()
w("Model: y_mt = μ_t + λ_t′θ_m + c_{m,p(t)} + η_mt, each task in units of its residual SD (pooled prior within metric family); λ_t = dataset + protocol-family + sensor blocks + task part (Eq. 11/12 group ridge); c = paper × model implementation offset. Leave-one-paper-out Spearman ρ of predicted vs reported within-task order (naive leaderboard = mean within-comparison z-score in all other sources, a K-independent single ranking):")
w()
w("Anchored (primary, D9): a held-out comparison's loading is estimated from half its GeoFMs and the other half is predicted; the leaderboard is used the same way. Block-predicted (secondary): nothing from the held-out comparison is used.")
w()
w("| offset | " + " | ".join(f"anchored K={k}" for k in lt) + " | anchored leaderboard | " + " | ".join(f"blocks K={k}" for k in lt) + " | leaderboard |"); w("|---|" + "---|" * (2 * len(lt) + 2))
for s, row in K["lopo_by_spec_and_K"].items():
    f0 = row[next(iter(row))]
    w(f"| {s}{' (chosen)' if s == off['chosen'] else ''} | " + " | ".join(f"{row[k]['rho_anch']:.3f}" for k in row) + f" | {f0['rho_anch_board']:.3f} | " + " | ".join(f"{row[k]['rho_struct']:.3f}" for k in row) + f" | {f0['rho_board']:.3f} |")
w()
if off["paired_vs_chosen"]:
    w("Offset choice (D8): " + "; ".join(f"{s} (K={v['K']}) minus chosen (K={v['vs_K']}): {ci(v)}" for s, v in off["paired_vs_chosen"].items()) + ".")
    w()
w(f"K (D9): best K = {bestK}; chosen (smallest not credibly worse) K = {Kc}. Paired differences to the best: " + ("; ".join(f"K={k}: {ci(v)}" for k, v in K["paired_vs_best"].items()) or "–") + ".")
w()
w(f"Anchored, against the leaderboard: K = 1 {ci(g['anchored_K1_vs_board'])}; K = {Kc} (chosen) {ci(g['anchored_Kchosen_vs_board'])}; K = {g['anchored_bestK_vs_board']['K']} (best, selected — optimistic) {ci(g['anchored_bestK_vs_board'])}. Block-predicted best K against the leaderboard: {ci(g['blocks_bestK_vs_naive_leaderboard'])}.")
w()
cal = d.get("simulation_calibration") or {}
if cal:
    w(f"**Calibrated simulation (D16).** A general factor (one leaderboard) plus specific factors, dataset-shared loadings and implementation effects, fitted on a {cal['grid_size']}-point grid to the real data: targets " + ", ".join(f"{k} {v:.3f}" for k, v in cal["targets"].items()) + "; achieved " + ", ".join(f"{k} {v:.3f}" for k, v in cal["achieved"].items()) + f" with general-factor mean {cal['chosen']['general_mean']}, SNR {cal['chosen']['snr']}, dataset share {cal['chosen']['dataset_share']}, implementation effect {cal['chosen']['paper_effect']} noise SD.")
    w()
if d["simulation_K"]:
    w("| K true | K selected by the rule | best K | anchored ρ by K | anchored leaderboard | best K − leaderboard |"); w("|---|---|---|---|---|---|")
    for x in d["simulation_K"]: w(f"| {x['K_true']} | {x['K_selected']} | {x['best_K']} | " + ", ".join(f"K{k}: {v:.3f}" for k, v in x["anchored_rho"].items()) + f" | {x['board']:.3f} | {ci(x['bestK_vs_board'])} |")
    w()
if d["simulation_offset"]:
    w("Offset options under the calibrated truth (K = 2):")
    w()
    w("| offset | anchored ρ | anchored leaderboard | block-predicted dataset gain (seen datasets) | geometry recovery (≥ 2-source datasets) |"); w("|---|---|---|---|---|")
    for x in d["simulation_offset"]: w(f"| {x['offset']} | {x['anchored_rho']:.3f} | {x['anchored_board']:.3f} | {x['dataset_gain_seen']:+.3f} | {x['recovery_multi_source_datasets']:.2f} |")
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
       [(p.stem.replace("dataset_analysis_sens_", "v2 · "), p) for p in sorted((ROOT / "data").glob("dataset_analysis_sens_*.json"))] + [("**v2 (this report)**", ROOT / "data" / "dataset_analysis.json")]
def labs(a_): return ", ".join(c for c, v in a_.items() if min(v["full_loading"]["p_bonferroni_4_labels"], v["direction_only"]["p_bonferroni_4_labels"]) < 0.05) or "none"
def head(j):
    if j.get("version") == 2:
        g_ = j["lopo_gain"]; bk_ = j["K"]["best"]
        se = next((v for k, v in g_.items() if k.startswith("dataset_seen_in_other_sources")), None)
        k1_ = g_.get("anchored_K1_vs_board", g_.get("K1_vs_naive_leaderboard")); kb_ = g_.get("anchored_bestK_vs_board", g_.get("bestK_vs_naive_leaderboard"))
        ta_ = j.get("tau_tests", {}).get("all", {}).get("dataset_identity")
        return dict(ev=f"{j['overlap']['models']}×{j['overlap']['tasks']}, {j['overlap']['sources']} src", multi=j["overlap"]["datasets_in_2plus_sources"], K=f"{j['K']['chosen']} / {bk_}",
                    off=j["offset"]["chosen"], k1=ci(k1_), kb=ci(kb_), seen=ci(se) if se else "–", tau=tci(ta_) if ta_ else "–",
                    lab=labs(j["metadata_association_multi_source"]), geo="yes" if j["geometry_recoverable"] else "no", rel=str(j["seed_noise_reliability"]["comparisons"]),
                    rep=f"{len(j['reproducibility']['strict']['estimable'])} / {len(j['reproducibility']['loose']['estimable'])}")
    g_ = j["lopo_gain_vs_one_ordering"]; se = g_.get("dataset_seen_in_other_papers")
    return dict(ev=f"{j['overlap']['models']}×{j['overlap']['tasks']}, {j['overlap']['papers']} src", multi=j["overlap"]["datasets_in_2plus_papers"],
                K=f"{j['K']['chosen']} / {g_.get('bestK_vs_naive_leaderboard', {}).get('K', '–')}", off="all", k1=ci(g_["K1_vs_naive_leaderboard"]),
                kb=ci(g_["bestK_vs_naive_leaderboard"]) if "bestK_vs_naive_leaderboard" in g_ else "–", seen=ci(se) if se else "–",
                lab=labs(j["metadata_association_multi_paper"]), geo="yes" if j["geometry_recoverable"] else "no", rel="0", rep=f"{len(j['reproducibility'])} / –", tau="–")
cols = [("ev", "evidence (GeoFMs × tasks)"), ("multi", "datasets in ≥ 2 sources"), ("tau", "dataset identity, model-free τ (v2.1+)"), ("K", "K chosen / best"), ("off", "offset"), ("k1", "K=1 vs leaderboard (v1/v2: block-predicted; v2.1: anchored)"), ("kb", "best K vs leaderboard (same)"),
        ("seen", "dataset transfer (seen)"), ("lab", "labels surviving correction"), ("geo", "similarity recoverable"), ("rel", "comparisons with seed-noise score"), ("rep", "reproducibility groups (strict / loose)")]
H = [(nm_, head(json.loads(p.read_text()))) for nm_, p in runs if p.exists()]
w("| | " + " | ".join(nm_ for nm_, _ in H) + " |"); w("|---|" + "---|" * len(H))
for k_, lab in cols: w(f"| {lab} | " + " | ".join(str(h[k_]) for _, h in H) + " |")
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
