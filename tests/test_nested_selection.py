"""Tests for scripts/nested_selection.py (backlog N1). Synthetic data only; no workbook needed."""
import sys
from pathlib import Path
import numpy as np, pandas as pd, pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dataset_benchmarking as db
import nested_selection as ns


def toy(seed=0, M=14, P=5, per=3):
    """M GeoFMs x P sources x `per` comparisons each, a general factor plus a dataset-specific one, ~60% observed."""
    rng = np.random.default_rng(seed); T = P * per
    tp = np.repeat([f"src{p}" for p in range(P)], per)
    ds = np.array([t % 4 for t in range(T)])
    th = rng.normal(size=(M, 2)); lam = np.c_[np.ones(4), rng.normal(size=4)][ds]
    Y = 50 + 5 * th @ lam.T + rng.normal(scale=2.0, size=(M, T))
    mask = rng.random((M, T)) < 0.6
    for t in range(T): mask[rng.choice(M, 6, replace=False), t] = True
    groups = {"dataset": ds}
    paper = pd.factorize(tp)[0]
    def kw_fn(spec):
        k = dict(groups=groups, ridge_u=3.0, ridge_g={"dataset": 3.0}, ridge_theta=3.0, n_restarts=1, n_iter=40, tol=1e-5, prior_group=np.zeros(T, int))
        if spec == "all": k.update(paper=paper, ridge_pm=3.0)
        return k
    return Y, mask, tp, kw_fn


def test_single_source_fit_matches_leave_one_paper_out():
    Y, mask, tp, kw_fn = toy()
    k = kw_fn("all"); g = k.pop("groups")
    L = db.leave_one_paper_out(Y, mask, tp, 2, g, **k)
    for p in np.unique(tp):
        a = ns.fit_and_score(Y, mask, tp, frozenset((p,)), 2, g, **k).set_index("task")
        b = L[L.paper == p].set_index("task")
        assert list(a.index) == list(b.index)
        np.testing.assert_allclose(a.rho_struct.values, b.rho_struct.values, atol=1e-10)
        np.testing.assert_allclose(a.rho_board.values, b.rho_board.values, atol=1e-10)


def test_inner_selection_ignores_held_out_source_values():
    Y, mask, tp, kw_fn = toy(1)
    held = "src2"; specs, Ks = ("all", "none"), (1, 2)
    base = ns.nested_select(Y, mask, tp, held, kw_fn, specs=specs, Ks=Ks)
    Y2 = Y.copy(); rng = np.random.default_rng(9)
    Y2[:, tp == held] = rng.normal(scale=100.0, size=Y2[:, tp == held].shape)   # scramble the held-out source
    pert = ns.nested_select(Y2, mask, tp, held, kw_fn, specs=specs, Ks=Ks)
    assert base == pert
    # control: scrambling a training source does change the inner table
    Y3 = Y.copy(); Y3[:, tp == "src0"] = rng.normal(scale=100.0, size=Y3[:, tp == "src0"].shape)
    assert ns.nested_select(Y3, mask, tp, held, kw_fn, specs=specs, Ks=Ks)["table"] != base["table"]


def test_pair_fit_equals_inner_fit_without_outer_source():
    """The fit without {o, p} scores p exactly as an inner fold run on the matrix with o's comparisons deleted."""
    Y, mask, tp, kw_fn = toy(2)
    k = kw_fn("none"); g = k.pop("groups"); o, p = "src1", "src3"
    keep = tp != o
    a = ns.fit_and_score(Y, mask, tp, frozenset((o, p)), 1, g, **k).query("paper == @p")
    k2 = {kk: (v[keep] if kk == "prior_group" else v) for kk, v in k.items()}
    b = ns.fit_and_score(Y[:, keep], mask[:, keep], tp[keep], frozenset((p,)), 1, {n: v[keep] for n, v in g.items()}, **k2)
    np.testing.assert_allclose(a.rho_struct.values, b.rho_struct.values, atol=1e-8)
    np.testing.assert_allclose(a.rho_board.values, b.rho_board.values, atol=1e-12)


def _rows(rng, n_src=8, per=6, shift=0.0):
    return pd.DataFrame({"paper": np.repeat([f"s{i}" for i in range(n_src)], per), "task": np.arange(n_src * per),
                         "rho_struct": rng.normal(0.2 + shift, 0.3, n_src * per)})


def test_select_config_reproduces_choose_K_on():
    rng = np.random.default_rng(3); base = _rows(rng)
    LO = {}
    for s, off in (("all", 0.0), ("multi_domain", -0.05), ("none", 0.03)):
        for K, dK in ((1, 0.0), (2, 0.06), (3, 0.08), (4, -0.02)):
            LO[(s, K)] = base.assign(rho_struct=base.rho_struct + off + dK + rng.normal(0, 0.05, len(base)))
    sel = ns.select_config(LO, specs=("all", "multi_domain", "none"), Ks=(1, 2, 3, 4))
    best_spec = max(("all", "multi_domain", "none"), key=lambda s: max(round(LO[(s, K)].rho_struct.mean(), 4) for K in (1, 2, 3, 4)))
    Kc, Kb, _, _ = ns.choose_K_on({K: LO[(best_spec, K)] for K in (1, 2, 3, 4)}, "rho_struct")
    assert (sel["spec"], sel["K_chosen"], sel["K_best"]) == (best_spec, Kc, Kb)
    assert sel["K_chosen"] <= sel["K_best"]
    # the build's rule: a K far below the best is credibly worse and cannot be chosen
    LO2 = {("none", 1): base.assign(rho_struct=base.rho_struct - 1.0), ("none", 2): base}
    assert ns.select_config(LO2, specs=("none",), Ks=(1, 2))["K_chosen"] == 2
    LO3 = {("none", 1): base, ("none", 2): base.assign(rho_struct=base.rho_struct + 1e-3 * rng.normal(size=len(base)))}
    assert ns.select_config(LO3, specs=("none",), Ks=(1, 2))["K_chosen"] == 1


def test_choose_K_on_is_the_builds_function():
    import ast
    src = (Path(ns.__file__).parent / "build_dataset_analysis.py").read_text()
    names = {n.name for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)}
    assert {"paired_boot", "choose_K_on"} <= names and ns.SEED == 0 and ns.KS == (1, 2, 3, 4)


def test_max_bootstrap_single_and_identical_configs():
    rng = np.random.default_rng(4); r = _rows(rng)
    d = pd.DataFrame({"d": r.rho_struct - 0.2, "p": r.paper})
    one = ns.max_bootstrap({"a": d}, B=300)
    assert one["optimism"] == 0 and one["bootstrap_max"] == one["bootstrap_fixed_config"]
    same = ns.max_bootstrap({"a": d, "b": d.copy(), "c": d.copy()}, B=300)
    assert same["optimism"] >= 0 and same["optimism"] == 0
    assert same["observed_max"] == one["observed_max"]
    # equal truth, independent noise: the max is optimistic
    noisy = {f"c{i}": pd.DataFrame({"d": rng.normal(0, 0.3, len(r)), "p": r.paper}) for i in range(12)}
    mb = ns.max_bootstrap(noisy, B=300)
    assert mb["optimism"] > 0 and mb["configurations"] == 12 and mb["sources"] == 8
    lo, hi = mb["maxT_ci90_for_max_config"]
    assert lo < mb["observed_max"] < hi
