"""Optimiser-restart sensitivity for the leave-one-paper-out K comparison (agent backlog N3; D17).

The v2.1 build fits every leave-one-paper-out fold from 3 starts (naive-leaderboard seed, SVD, 1 random; build `kw`
passes n_restarts=1). This reruns the same leave-one-paper-out, for the chosen offset spec and the given K, with more
random starts on top of the leaderboard and SVD starts, records the penalised objective reached from every start in
each fold (round 0 of the reweighting, where the build compares starts), keeps the best start per fold as the build
does, and recomputes the block-predicted contrasts with the build's paired bootstrap over sources. The 3-start run is
repeated alongside as a reproduction check of data/dataset_analysis.json. Sensitivity only: the frozen analysis and its
headline numbers are not changed. Summary statistics only are written.

Entry point: python3 scripts/build_dataset_analysis.py <workbook dir> --restarts-sens [N_RANDOM] [--restarts-sens-K 3,4]
Further seed sets (random starts drawn with seed base + fold index, so they differ across folds and from the first set),
appended to an existing output: add --restarts-sens-seeds 1000,2000 (run_seed_sets).
"""
import json
import time
import multiprocessing as mp

import numpy as np

REL_TOL = 1e-3          # a start "reaches the best optimum" if its objective is within 0.1% of the fold's lowest


def summarise_starts(objs, labels, rel_tol=REL_TOL, n_original=3, iters=None, n_iter_cap=None):
    """Spread of the objectives one fit reached from its starts. n_original: how many leading starts the v2.1 build
    uses (board, SVD, 1 random); best_in_original says whether the extra starts changed the selected fit."""
    o = np.asarray(objs, float); b = int(np.argmin(o)); lo = float(o[b])
    return {"n_starts": int(len(o)), "min": round(lo, 3), "median": round(float(np.median(o)), 3), "max": round(float(o.max()), 3),
            "rel_range": round(float((o.max() - lo) / max(abs(lo), 1e-12)), 5),
            "n_within_tol_of_best": int((o - lo <= rel_tol * max(abs(lo), 1e-12)).sum()),
            "best_start": b, "best_label": labels[b] if b < len(labels) else "", "best_in_original_starts": bool(b < n_original),
            "original_best_excess": round(float(o[:n_original].min() - lo), 3),
            "board_excess": round(float(o[labels.index("board")] - lo), 3) if "board" in labels else None,
            "starts_at_iteration_cap": None if iters is None or n_iter_cap is None else int(sum(i_ >= n_iter_cap for i_ in iters))}


def _job(args):
    lopo, Y, mask, tp, K, groups, kw = args
    fm = []
    rows = lopo(Y, mask, tp, K, groups, fold_meta=fm, **kw)
    return rows, fm


def run(Y, mask, tp, kw, paired_boot, spec, Ks, n_random, lopo, out, nproc=2, log=print, reference=None):
    """kw(spec) -> fit keywords as in the build (groups included); paired_boot(a, b, papers) as in the build;
    lopo = dataset_benchmarking.leave_one_paper_out. reference: the build's lopo_by_spec_and_K[spec] for the check."""
    t0 = time.time()
    settings = {"v2.1 (3 starts)": 1, f"{n_random + 2} starts": n_random}
    jobs, keys = [], []
    for K in sorted(Ks, reverse=True):                      # largest jobs first (2 workers)
        for name, nr in sorted(settings.items(), key=lambda x: -x[1]):
            k = kw(spec); g = k.pop("groups"); k["n_restarts"] = nr
            jobs.append((lopo, Y, mask, tp, K, g, k)); keys.append((name, K))
    if nproc > 1:
        with mp.get_context("fork").Pool(nproc) as pool:
            res = pool.map(_job, jobs, chunksize=1)
    else:
        res = list(map(_job, jobs))
    R = dict(zip(keys, res))
    log(f"restart sensitivity: {len(jobs)} leave-one-paper-out runs in {time.time() - t0:.0f}s")
    big = f"{n_random + 2} starts"; base = "v2.1 (3 starts)"
    out_d = {"what": "optimiser-restart sensitivity of the block-predicted leave-one-paper-out K comparison (D17, backlog N3); sensitivity only",
             "offset_spec": spec, "Ks": list(Ks), "random_starts": n_random,
             "starts": f"naive-leaderboard seed + SVD + {n_random} random (seed 0; the first random start is the v2.1 one, so the v2.1 starts are a subset)",
             "objective": "penalised weighted least squares in noise units at reweighting round 0, where the build compares starts; later rounds warm-start from the selected start",
             "rel_tol": REL_TOL, "n_iter": int(kw(spec)["n_iter"]), "by_setting": {}, "folds": {}, "contrasts": {}}
    for name in settings:
        out_d["by_setting"][name] = {}
        for K in Ks:
            rows, _ = R[(name, K)]
            ent = {"rho_struct": round(float(rows.rho_struct.mean()), 4), "rho_board": round(float(rows.rho_board.mean()), 4), "n_tasks": int(len(rows)),
                   "vs_leaderboard": paired_boot(rows.rho_struct, rows.rho_board, rows.paper)}
            if reference and str(K) in reference:
                ent["reproduces_build"] = bool(abs(reference[str(K)]["rho_struct"] - ent["rho_struct"]) < 5e-4)
            out_d["by_setting"][name][str(K)] = ent
    for K in Ks:
        rows_b, fm_b = R[(big, K)]; rows_o, _ = R[(base, K)]
        cap = kw(spec)["n_iter"]
        folds = [dict(paper=str(m["paper"]), **summarise_starts(m["start_objs"], m["start_labels"], iters=m.get("start_iters"), n_iter_cap=cap)) for m in fm_b]
        a = rows_b.set_index("task").rho_struct; o = rows_o.set_index("task").rho_struct.reindex(a.index)
        changed = {str(f["paper"]) for f in folds if not f["best_in_original_starts"]}
        dr = (a - o).abs()
        rr = np.array([f["rel_range"] for f in folds]); nw = np.array([f["n_within_tol_of_best"] for f in folds])
        out_d["folds"][str(K)] = {
            "n_folds": len(folds),
            "rel_range_median": round(float(np.median(rr)), 5), "rel_range_max": round(float(rr.max()), 5),
            "abs_range_median": round(float(np.median([f["max"] - f["min"] for f in folds])), 2),
            "abs_range_max": round(float(max(f["max"] - f["min"] for f in folds)), 2),
            "starts_within_tol_median": float(np.median(nw)), "starts_within_tol_min": int(nw.min()),
            "folds_all_starts_within_tol": int((nw == folds[0]["n_starts"]).sum()),
            "folds_best_from_extra_start": len(changed),
            "folds_board_start_best": int(sum(f["best_label"] == "board" for f in folds)),
            "starts_at_iteration_cap": int(sum(f["starts_at_iteration_cap"] or 0 for f in folds)), "starts_total": int(sum(f["n_starts"] for f in folds)),
            "original_best_excess_max": round(float(max(f["original_best_excess"] for f in folds)), 3),
            "tasks_rho_changed": int((dr > 1e-9).sum()), "mean_abs_rho_change": round(float(dr.mean()), 4),
            "per_fold": folds}
    for name in settings:
        for K1, K2 in [(a_, b_) for a_ in Ks for b_ in Ks if a_ > b_]:
            A_ = R[(name, K1)][0].set_index("task"); B_ = R[(name, K2)][0].set_index("task"); j = A_.index.intersection(B_.index)
            out_d["contrasts"][f"{name}: K={K1} minus K={K2}"] = paired_boot(A_.loc[j, "rho_struct"], B_.loc[j, "rho_struct"], A_.loc[j, "paper"])
    for name in settings:                                   # the D9 K rule applied within this sensitivity (frozen rule, reported only)
        means = {K: out_d["by_setting"][name][str(K)]["rho_struct"] for K in Ks}; bk = max(means, key=means.get)
        def upper(K):                                       # upper 90% bound of (K minus best)
            c = out_d["contrasts"][f"{name}: K={max(K, bk)} minus K={min(K, bk)}"]["ci90"]
            return c[1] if K > bk else -c[0]
        cred = [K for K in Ks if K != bk and upper(K) >= 0]
        out_d["by_setting"][name]["K_rule"] = {"best": int(bk), "smallest_not_credibly_worse": int(min([bk] + cred)), "Ks_compared": list(Ks)}
    out.write_text(json.dumps(out_d, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x)) + "\n")
    log(f"wrote {out}")
    return out_d


def k_rule(rho, contrast):
    """D9 rule on given mean rho by K; contrast(a, b) -> paired_boot of rho_a - rho_b. Returns best, chosen, tests."""
    bk = max(rho, key=rho.get); tests = {K: contrast(K, bk) for K in rho if K != bk}
    return int(bk), int(min([bk] + [K for K, t in tests.items() if t["ci90"][1] >= 0])), tests


def _set_summary(R, Ks, paired_boot, n_original, cap):
    """R: K -> (rows, fold_meta) for one seed set."""
    out = {"by_K": {}, "contrasts": {}}
    for K in Ks:
        rows, fm = R[K]
        folds = [summarise_starts(m["start_objs"], m["start_labels"], n_original=n_original, iters=m.get("start_iters"), n_iter_cap=cap) for m in fm]
        best_idx = [f["best_start"] for f in folds]; top = max(set(best_idx), key=best_idx.count)
        lr = [abs(x) for m in fm for x, i in zip(m.get("start_last_rel_change", []), m.get("start_iters", [])) if i >= cap and np.isfinite(x)]
        rr = np.array([f["rel_range"] for f in folds])
        out["by_K"][str(K)] = {"rho_struct": round(float(rows.rho_struct.mean()), 4), "rho_board": round(float(rows.rho_board.mean()), 4),
                               "vs_leaderboard": paired_boot(rows.rho_struct, rows.rho_board, rows.paper),
                               "rel_range_median": round(float(np.median(rr)), 5), "rel_range_max": round(float(rr.max()), 5),
                               "starts_within_tol_median": float(np.median([f["n_within_tol_of_best"] for f in folds])),
                               "starts_at_iteration_cap": int(sum(f["starts_at_iteration_cap"] or 0 for f in folds)), "starts_total": int(sum(f["n_starts"] for f in folds)),
                               "capped_last_rel_change_median": round(float(np.median(lr)), 7) if lr else None,
                               "most_common_best_start": {"index": int(top), "folds": int(best_idx.count(top)), "n_folds": len(folds)},
                               "folds_best_from_random_start": int(sum(f["best_label"] == "random" for f in folds))}
    def con(a, b):
        A_ = R[a][0].set_index("task"); B_ = R[b][0].set_index("task"); j = A_.index.intersection(B_.index)
        return paired_boot(A_.loc[j, "rho_struct"], B_.loc[j, "rho_struct"], A_.loc[j, "paper"])
    for a in Ks:
        for b in Ks:
            if a > b: out["contrasts"][f"K={a} minus K={b}"] = con(a, b)
    if len(Ks) == 4:
        bk, ck, _ = k_rule({K: out["by_K"][str(K)]["rho_struct"] for K in Ks}, con)
        out["K_rule"] = {"best": bk, "smallest_not_credibly_worse": ck}
    return out


def run_seed_sets(Y, mask, tp, kw, paired_boot, spec, Ks, n_random, lopo, out, bases, nproc=2, log=print):
    """Rerun the n_random-start leave-one-paper-out with random starts drawn from seed base + fold index for each base,
    and append a 'seed_sets' section to the existing output of run() (which used seed 0 in every fold)."""
    d = json.loads(out.read_text()); cap = int(kw(spec)["n_iter"]); d["n_iter"] = cap
    big = f"{n_random + 2} starts"
    sets = d.get("seed_sets") or []
    if not sets:                                           # set 0 = the run() result, summarised in the same form
        s0 = {"label": "seed 0 in every fold (first run)", "by_K": {}}
        for K in Ks:
            b, f = d["by_setting"][big][str(K)], d["folds"][str(K)]
            bi = [x["best_start"] for x in f["per_fold"]]; top = max(set(bi), key=bi.count)
            s0["by_K"][str(K)] = {"rho_struct": b["rho_struct"], "rho_board": b["rho_board"], "vs_leaderboard": b["vs_leaderboard"],
                                  "rel_range_median": f["rel_range_median"], "rel_range_max": f["rel_range_max"], "starts_within_tol_median": f["starts_within_tol_median"],
                                  "starts_at_iteration_cap": f["starts_at_iteration_cap"], "starts_total": f["starts_total"], "capped_last_rel_change_median": None,
                                  "most_common_best_start": {"index": int(top), "folds": int(bi.count(top)), "n_folds": len(bi)},
                                  "folds_best_from_random_start": int(sum(x["best_label"] == "random" for x in f["per_fold"]))}
        s0["contrasts"] = {k.split(": ", 1)[1]: v for k, v in d["contrasts"].items() if k.startswith(big + ":")}
        if "K_rule" in d["by_setting"][big]:
            s0["K_rule"] = {k: v for k, v in d["by_setting"][big]["K_rule"].items() if k != "Ks_compared"}
        sets.append(s0)
    d["seed_sets"] = sets
    for base in bases:
        t0 = time.time(); jobs = []
        for K in sorted(Ks, reverse=True):
            k = kw(spec); g = k.pop("groups"); k["n_restarts"] = n_random; k["fold_seed_base"] = int(base)
            jobs.append((lopo, Y, mask, tp, K, g, k))
        if nproc > 1:
            with mp.get_context("fork").Pool(nproc) as pool:
                res = pool.map(_job, jobs, chunksize=1)
        else:
            res = list(map(_job, jobs))
        R = dict(zip(sorted(Ks, reverse=True), res))
        s_ = {"label": f"seed {base} + fold index", **_set_summary(R, Ks, paired_boot, 2, cap)}
        sets = [x for x in sets if x["label"] != s_["label"]] + [s_]
        log(f"seed set {base}: {time.time() - t0:.0f}s", {K: s_["by_K"][str(K)]["rho_struct"] for K in Ks}, s_.get("K_rule"), s_["contrasts"].get("K=4 minus K=3"))
        d["seed_sets"] = sets
        out.write_text(json.dumps(d, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x)) + "\n")
    if len(sets) > 1 and "4" in sets[0]["by_K"] and "3" in sets[0]["by_K"]:
        c = [x["contrasts"]["K=4 minus K=3"] for x in sets]
        d["seed_set_range"] = {"n_sets": len(sets),
                               "K4_minus_K3_mean": [min(x["mean"] for x in c), max(x["mean"] for x in c)],
                               "K4_minus_K3_ci_upper": [min(x["ci90"][1] for x in c), max(x["ci90"][1] for x in c)],
                               "K4_minus_K3_credibly_negative_in": int(sum(x["ci90"][1] < 0 for x in c)),
                               "rho_by_K": {K: [min(x["by_K"][K]["rho_struct"] for x in sets), max(x["by_K"][K]["rho_struct"] for x in sets)] for K in sets[0]["by_K"]},
                               "K_rule": [x.get("K_rule") for x in sets]}
    out.write_text(json.dumps(d, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x)) + "\n")
    log(f"wrote {out}")
    return d

