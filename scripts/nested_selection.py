#!/usr/bin/env python3
"""Nested selection of the offset option and K (backlog N1; sensitivity for D8 / D9 / D14).

The build (scripts/build_dataset_analysis.py, section 3) chooses the paper x model offset option and the number of
dimensions K among 12 configurations (3 offsets x K = 1..4) on the same block-predicted leave-one-paper-out criterion it
then reports, so the selected figures are optimistic (D14). This script estimates the gain of the *selection procedure*
without that optimism:

  for each held-out source o (outer fold):
    inner leave-one-paper-out on the other sources only (source o's comparisons removed from the matrix, so neither its
    scores, nor its contribution to the leaderboard comparator, nor its residual scales enter), for all 12 configurations;
    apply the build's rules to the inner table: offset = best of all / multi_domain / none by max over K of mean rho_struct;
    K = smallest K not credibly worse than the best (paired bootstrap over sources) -> "nested chosen K", and the inner
    argmax K -> "nested best K";
    score source o's comparisons with the selected configuration fitted on all sources but o. That outer fit is exactly
    the build's leave-one-paper-out fit for o, so the outer scores are the build's per-task rows for the selected
    configuration (recomputed here with the build's settings; checked against data/dataset_analysis.json).

Then: paired bootstrap over sources (build's paired_boot) of nested rho_struct against the plain leaderboard and against
K = 1 at the same fold's nested offset; and a cluster bootstrap of the maximum over the 12 configurations (max_bootstrap).

The matrix, fitting settings (kw(): ridge 3, n_restarts=1 plus the leaderboard-seeded and SVD starts, 200 iterations) and
selection code are the build's own: the build's prefix (inclusion to matrix, sections 0-1) is executed unchanged, and
paired_boot / choose_K_on are compiled from the build's source. Nothing is changed in the build or its outputs.

Compute (exact nesting, no subsampling): inner fold p of outer fold o needs the fit without sources {o, p}, which is also
inner fold o of outer fold p, so each unordered pair of scored sources is fitted once per configuration (fit_and_score:
the removed sources' comparisons are masked and their values zeroed; masked columns carry zero weight, so this equals
deleting them — see tests/). Sources that leave-one-paper-out cannot score are never inner folds with rows, so their
fits are skipped. 22 scored sources: (22 + 231) x 12 = 3,036 fits, about 4.1 h on 2 CPUs; fits are cached (--cache).

Usage: python3 scripts/nested_selection.py <workbook dir> [--cache DIR] [--out PATH]
Writes summary statistics only (data/dataset_analysis_nested.json); per-task rows are cached outside the repository.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1"); os.environ.setdefault("MKL_NUM_THREADS", "1")
import ast, json, pickle, sys, time, multiprocessing as mp
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dataset_benchmarking as db

BUILD = ROOT / "scripts" / "build_dataset_analysis.py"
SECTION2 = "\n# ============================================================================= 2."
SPECS = ("all", "multi_domain", "none"); PRIMARY = "rho_struct"


# ============================================================================= the build's own definitions
def _build_defs():
    """Compile SEED, KS_LOPO, paired_boot and choose_K_on from the build's source (not copies)."""
    tree = ast.parse(BUILD.read_text()); ns = {"np": np, "pd": pd}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and getattr(node.targets[0], "id", None) in ("SEED", "KS_LOPO"):
            ns[node.targets[0].id] = ast.literal_eval(node.value)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in ("paired_boot", "choose_K_on"):
            exec(compile(ast.Module([node], []), str(BUILD), "exec"), ns)
    assert all(k in ns for k in ("SEED", "KS_LOPO", "paired_boot", "choose_K_on")), "build definitions not found"
    return ns
_B = _build_defs()
SEED, KS = _B["SEED"], tuple(_B["KS_LOPO"]); paired_boot, choose_K_on = _B["paired_boot"], _B["choose_K_on"]


# ============================================================================= selection (the build's rules, section 3)
def select_config(LO, specs=SPECS, Ks=KS, col=PRIMARY):
    """LO: {(spec, K): leave-one-paper-out rows}. Offset spec = highest max over K of the mean criterion (rounded to 4
    decimals, first spec on ties, as in the build); then the build's choose_K_on on that spec's rows."""
    table = {s: {K: round(float(LO[(s, K)][col].mean()), 4) for K in Ks} for s in specs}
    spec = max(specs, key=lambda s: max(table[s][K] for K in Ks))
    Kc, Kb, _, _ = choose_K_on({K: LO[(spec, K)] for K in Ks}, col)
    return {"spec": spec, "K_chosen": int(Kc), "K_best": int(Kb), "table": table}


ROW_COLS = ["paper", "task", "n_models", "rho_struct", "rho_board"]
def fit_and_score(Y, mask, tp, E, K, groups, min_models=4, min_theta_tasks=3, **kw):
    """One leave-sources-out fit: every comparison of the sources in E is removed (masked, and its values zeroed so they
    cannot be read), the structured model is fitted on the rest, and each removed comparison is scored as in
    db.leave_one_paper_out (block-predicted rho_struct; plain leaderboard rho_board from the training sources only).
    With E = {p} the rows equal leave_one_paper_out's rows for p. With E = {o, p} the rows for p are those of an inner
    leave-one-paper-out fold run without source o, and vice versa (the fit is the same: masked columns carry zero weight)."""
    tp = np.asarray(tp); hold = np.isin(tp, list(E))
    m2 = mask.copy(); m2[:, hold] = False
    Yt = np.where(m2, Y, 0.0)                                       # training values only
    fit = db.fit_heteroskedastic(Yt, m2, K, groups, **kw)[0]
    L = fit.lam(include_u=False)
    Z = np.full(Y.shape, np.nan)
    for t in np.where(~hold)[0]:
        o = m2[:, t]
        if o.sum() > 1 and Yt[o, t].std() > 0: Z[o, t] = (Yt[o, t] - Yt[o, t].mean()) / Yt[o, t].std(ddof=1)
    with np.errstate(invalid="ignore"), __import__("warnings").catch_warnings():
        __import__("warnings").simplefilter("ignore", RuntimeWarning)
        board = np.nanmean(Z, axis=1)
    ntr = m2.sum(1); rows = []
    for t in np.where(hold)[0]:
        ms = np.where(mask[:, t] & (ntr >= min_theta_tasks))[0]
        if len(ms) < min_models: continue
        y = Y[ms, t]                                                  # the scored (held-out) comparison
        has_group = any(groups[g][t] >= 0 and np.abs(fit.B[g][groups[g][t]]).sum() > 0 for g in groups) if groups else False
        r_s = db._rank_scores(y, fit.theta[ms] @ L[t])[0] if has_group else np.nan
        r_b = db._rank_scores(y, np.nan_to_num(board[ms]))[0]
        rows.append(dict(paper=tp[t], task=int(t), n_models=len(ms), rho_struct=r_s, rho_board=r_b))
    return pd.DataFrame(rows, columns=ROW_COLS)


def scored_sources(mask, tp, min_models=4, min_theta_tasks=3):
    """Sources with >= 1 comparison that leave-one-paper-out can score (depends on the observation pattern only).
    Removing a further source only lowers the training counts, so no other source is ever scored in an inner loop."""
    tp = np.asarray(tp); out = []
    for p in np.unique(tp):
        hold = tp == p; ntr = (mask & ~hold[None, :]).sum(1)
        if any((mask[:, t] & (ntr >= min_theta_tasks)).sum() >= min_models for t in np.where(hold)[0]): out.append(p)
    return out


def inner_table(pair_rows, held, sources, specs=SPECS, Ks=KS):
    """Inner leave-one-paper-out rows for outer fold `held`: source p's rows from the fit without {held, p}."""
    return {(s, K): pd.concat([pair_rows(frozenset((held, p)), s, K).query("paper == @p") for p in sources if p != held], ignore_index=True)
            for s in specs for K in Ks}


def nested_select(Y, mask, tp, held, kw_fn, specs=SPECS, Ks=KS, col=PRIMARY, pair_rows=None, sources=None):
    """Inner selection for one outer fold: offset and K chosen by inner leave-one-paper-out on the sources other than
    `held`, with the build's rules. kw_fn(spec) -> fit settings dict incl. 'groups' (the build's kw)."""
    if pair_rows is None:
        def pair_rows(E, s, K):
            k = dict(kw_fn(s)); g = k.pop("groups"); return fit_and_score(Y, mask, tp, E, K, g, **k)
    sources = scored_sources(mask, tp) if sources is None else sources
    return select_config(inner_table(pair_rows, held, sources, specs, Ks), specs, Ks, col)


# ============================================================================= bootstrap of the maximum over configurations
def max_bootstrap(diffs, B=2000, seed=SEED):
    """diffs: {config: DataFrame with columns d (per-task gain vs the leaderboard) and p (source)}.
    Cluster bootstrap over sources (one draw of sources shared by all configurations, rng = default_rng(seed), sources
    in sorted order, as in paired_boot): each configuration's mean gain is recomputed on the resampled sources and the
    maximum over configurations is taken. Returns the observed maximum and its configuration, the bootstrap
    distribution of the maximum, the same configuration's own (fixed) bootstrap distribution, and
      optimism      = mean bootstrap max - mean bootstrap of the observed-best configuration held fixed (>= 0);
      bias_of_max   = mean bootstrap max - observed max  (bootstrap bias of the max statistic); corrected = observed - bias;
      max-T interval: 90% simultaneous interval over all configurations (studentised by each configuration's bootstrap
                      SD; q = 90th percentile of max_c |m*_c - m_c| / sd_c), reported for the observed-best configuration."""
    cfgs = list(diffs)
    D = {c: diffs[c].dropna(subset=["d"]) for c in cfgs}
    srcs = sorted(set().union(*[set(D[c].p) for c in cfgs]))
    si = {s: i for i, s in enumerate(srcs)}; n = len(srcs)
    S = np.zeros((len(cfgs), n)); N = np.zeros((len(cfgs), n))
    for j, c in enumerate(cfgs):
        g = D[c].groupby("p").d.agg(["sum", "size"])
        for s, row in g.iterrows(): S[j, si[s]], N[j, si[s]] = row["sum"], row["size"]
    obs = S.sum(1) / N.sum(1)
    rng = np.random.default_rng(seed); W = np.zeros((B, n))
    for b in range(B): W[b] = np.bincount(rng.integers(0, n, n), minlength=n)
    with np.errstate(invalid="ignore", divide="ignore"): M = (W @ S.T) / (W @ N.T)          # B x configs
    bmax = np.nanmax(M, axis=1); j = int(np.argmax(obs)); fixed = M[:, j]
    sd = np.nanstd(M, axis=0, ddof=1) if B > 1 else np.zeros(len(cfgs)); sd = np.where(sd > 0, sd, np.nan)
    T = np.nanmax(np.abs(M - obs[None, :]) / sd[None, :], axis=1) if np.isfinite(sd).any() else np.zeros(B)
    q = float(np.nanpercentile(T, 90)) if np.isfinite(T).any() else 0.0
    r4 = lambda x: round(float(x), 4)
    return {"configurations": len(cfgs), "sources": n, "B": B, "observed_by_config": {str(c): r4(v) for c, v in zip(cfgs, obs)},
            "observed_max": r4(obs[j]), "observed_max_config": str(cfgs[j]),
            "bootstrap_max": {"mean": r4(np.mean(bmax)), "ci90": [r4(np.percentile(bmax, 5)), r4(np.percentile(bmax, 95))], "p_le_0": r4((bmax <= 0).mean())},
            "bootstrap_fixed_config": {"mean": r4(np.nanmean(fixed)), "ci90": [r4(np.nanpercentile(fixed, 5)), r4(np.nanpercentile(fixed, 95))], "p_le_0": r4((fixed <= 0).mean())},
            "share_draws_max_is_observed_max_config": r4(np.mean(np.nanargmax(np.where(np.isnan(M), -np.inf, M), axis=1) == j)),
            "optimism": r4(np.mean(bmax) - np.nanmean(fixed)), "bias_of_max": r4(np.mean(bmax) - obs[j]),
            "bias_corrected_max": r4(2 * obs[j] - np.mean(bmax)),
            "maxT_q90": r4(q), "maxT_ci90_for_max_config": [r4(obs[j] - q * sd[j]), r4(obs[j] + q * sd[j])] if np.isfinite(sd[j]) else None}


# ============================================================================= run on the real matrix
def _load_matrix(wb):
    """Execute the build's prefix (inclusion rules to the GeoFM x task matrix, up to section 2) unchanged."""
    src = BUILD.read_text(); assert src.count(SECTION2) == 1, "build section marker not found"
    argv = sys.argv; sys.argv = [str(BUILD), str(wb)]
    ns = {"__name__": "build_prefix", "__file__": str(BUILD)}
    try: exec(compile(src.split(SECTION2)[0], str(BUILD), "exec"), ns)
    finally: sys.argv = argv
    return ns

_NS = None
def _job(a):
    s, K, E = a
    k = dict(_NS["kw"](s)); g = k.pop("groups")
    return a, fit_and_score(_NS["Y"], _NS["mask"], _NS["tp"], E, K, g, **k)

def run(jobs, cache, nproc, log):
    """Run (spec, K, E) fits in parallel, caching each one's rows (outside the repository) so a run can resume."""
    cache.mkdir(parents=True, exist_ok=True); out, todo = {}, []
    name = lambda a: cache / f"{a[0]}_K{a[1]}_{'-'.join(str(_NS['src_index'][x]) for x in sorted(a[2]))}.pkl"
    for a in jobs:
        if name(a).exists(): out[a] = pickle.loads(name(a).read_bytes())
        else: todo.append(a)
    log(f"{len(out)} fits cached, {len(todo)} to run")
    if todo:
        with mp.get_context("fork").Pool(nproc) as pool:
            for i, (a, L_) in enumerate(pool.imap_unordered(_job, todo), 1):
                name(a).write_bytes(pickle.dumps(L_)); out[a] = L_
                if i % 10 == 0 or i == len(todo): log(f"done {i}/{len(todo)} (last: {a[0]} K={a[1]} sources={len(a[2])})")
    return out


def main(argv):
    global _NS
    wb = Path(argv[1]); cache = Path(argv[argv.index("--cache") + 1]) if "--cache" in argv else Path(__import__("tempfile").gettempdir()) / "eoarena_nested_cache"
    out_path = Path(argv[argv.index("--out") + 1]) if "--out" in argv else ROOT / "data" / "dataset_analysis_nested.json"
    t0 = time.time(); log = lambda *a: print(f"[{time.time()-t0:6.0f}s]", *a, flush=True)
    _NS = _load_matrix(wb); tp, mask = _NS["tp"], _NS["mask"]
    _NS["src_index"] = {s: i for i, s in enumerate(sorted(set(tp)))}
    assert _NS["OFFSET"] == "select" and _NS["WITH_LB"] and _NS["WITH_REG"] and not _NS["MAIN_ONLY"], "main configuration only"
    nproc = _NS["NPROC"]
    folds = scored_sources(mask, tp)
    singles = [frozenset((o,)) for o in folds]
    pairs = [frozenset((a_, b_)) for i, a_ in enumerate(folds) for b_ in folds[i + 1:]]
    log(f"{len(folds)} outer folds; {len(singles)} single and {len(pairs)} pair fits per configuration")
    jobs = [(s, K, E) for K in sorted(KS, reverse=True) for s in SPECS for E in singles + pairs]
    R = run(jobs, cache, nproc, log)
    pair_rows = lambda E, s, K: R[(s, K, E)]
    # outer rows: E = {o} is the build's leave-one-paper-out fold for o
    LO = {(s, K): pd.concat([R[(s, K, E)] for E in singles], ignore_index=True) for s in SPECS for K in KS}
    ref = json.loads((ROOT / "data" / "dataset_analysis.json").read_text())["K"]["lopo_by_spec_and_K"]
    check = {s: {K: round(float(LO[(s, K)][PRIMARY].mean()), 4) for K in KS} for s in SPECS}
    reproduces = all(abs(check[s][K] - ref[s][str(K)][PRIMARY]) < 5e-4 and abs(round(float(LO[(s, K)].rho_board.mean()), 4) - ref[s][str(K)]["rho_board"]) < 5e-4
                     for s in SPECS for K in KS)
    log("reproduces the build's leave-one-paper-out table:", reproduces, check)
    full_sel = select_config(LO)
    # outer folds: sources with at least one scored held-out comparison
    per_fold, nc, nb, k1c, k1b = [], [], [], [], []
    for o in folds:
        sel = select_config(inner_table(pair_rows, o, folds))
        rows = lambda s, K: LO[(s, K)][LO[(s, K)].paper == o].set_index("task")
        rc, rb_, r1 = rows(sel["spec"], sel["K_chosen"]), rows(sel["spec"], sel["K_best"]), rows(sel["spec"], 1)
        nc.append(rc.assign(task=rc.index)); nb.append(rb_.assign(task=rb_.index))
        k1c.append(r1.loc[rc.index, PRIMARY].values); k1b.append(r1.loc[rb_.index, PRIMARY].values)
        per_fold.append({"source": o, "offset": sel["spec"], "K_chosen": sel["K_chosen"], "K_best": sel["K_best"], "comparisons_scored": int(len(rc))})
    NC, NB = pd.concat(nc), pd.concat(nb)
    nested = {"chosen_K_vs_leaderboard": paired_boot(NC[PRIMARY], NC.rho_board, NC.paper),
              "best_K_vs_leaderboard": paired_boot(NB[PRIMARY], NB.rho_board, NB.paper),
              "chosen_K_vs_K1": paired_boot(NC[PRIMARY], np.concatenate(k1c), NC.paper),
              "best_K_vs_K1": paired_boot(NB[PRIMARY], np.concatenate(k1b), NB.paper)}
    counts = lambda key: {str(v): int(sum(f[key] == v for f in per_fold)) for v in sorted({f[key] for f in per_fold}, key=str)}
    pf = pd.DataFrame(per_fold)
    # bootstrap of the maximum over the 12 configurations (gain vs leaderboard, block-predicted)
    diffs = {f"{s}|K={K}": pd.DataFrame({"d": LO[(s, K)][PRIMARY] - LO[(s, K)].rho_board, "p": LO[(s, K)].paper}) for s in SPECS for K in KS}
    MB = max_bootstrap(diffs, B=2000, seed=SEED)
    out = {"version": 1, "as_of": time.strftime("%Y-%m-%d"), "item": "N1 nested selection (sensitivity for D8/D9/D14; frozen decisions unchanged)",
           "design": {"outer": "leave-one-source-out over the sources with >= 1 scored held-out comparison",
                      "inner": "leave-one-paper-out over the remaining sources with the outer source's comparisons removed (exact nesting, no reduction); the fit without sources {o, p} is computed once and serves inner fold p of outer o and inner fold o of outer p",
                      "selection": "build rules: offset = highest max-over-K mean rho_struct; K = smallest not credibly worse than the best (paired bootstrap over inner sources); best K = inner argmax",
                      "fit_settings": "build kw(): ridge 3 (blocks, task part, theta, paper x model offset), n_restarts=1 + leaderboard-seeded + SVD starts, n_iter 200, tol 1e-6, heteroskedastic, family priors",
                      "criterion": "rho_struct (block-predicted) vs rho_board (plain leaderboard from the training sources)",
                      "bootstrap": "paired_boot from the build: cluster bootstrap over outer sources, 2000 draws, seed 0",
                      "K1_comparator": "K = 1 at the same fold's nested offset, same held-out comparisons"},
           "reproduces_build_lopo_table": reproduces, "full_data_selection": {k_: full_sel[k_] for k_ in ("spec", "K_chosen", "K_best")},
           "outer_folds": len(folds), "per_fold": per_fold,
           "fold_counts": {"offset": counts("offset"), "K_chosen": counts("K_chosen"), "K_best": counts("K_best"),
                           "offset_x_K_chosen": {f"{a}|K={b}": int(n) for (a, b), n in pf.groupby(["offset", "K_chosen"]).size().items()},
                           "same_as_full_data_selection": int(sum((f["offset"], f["K_chosen"]) == (full_sel["spec"], full_sel["K_chosen"]) for f in per_fold))},
           "nested": nested, "max_over_configurations": MB, "fits": len(jobs), "runtime_s_this_invocation": round(time.time() - t0), "runtime_note": "fits are cached outside the repository; the uncached run took about 4.1 h on 2 CPUs"}
    out_path.write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    log("nested", nested); log("max bootstrap", MB); log(f"wrote {out_path}")


if __name__ == "__main__":
    main(sys.argv)
