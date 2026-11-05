"""Multi-start logic of fit_structured and the optimiser-restart sensitivity (backlog N3). Synthetic data only."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dataset_benchmarking as db  # noqa: E402
import sens_restarts  # noqa: E402


def synth(M=14, T=16, K=2, n_papers=4, seed=1):
    rng = np.random.default_rng(seed)
    theta = rng.normal(size=(M, K)); lam = rng.normal(size=(T, K)) + np.r_[1.0, np.zeros(K - 1)]
    Y = 50 + 3 * theta @ lam.T + rng.normal(size=(M, T))
    mask = rng.random((M, T)) < 0.7
    mask[:6] = True                                        # every task keeps >= 6 models
    paper = np.arange(T) % n_papers
    groups = {"dataset": np.arange(T) // 2}
    return Y, mask, paper, groups


def test_multistart_records_and_keeps_lowest():
    Y, mask, _, groups = synth()
    f = db.fit_structured(Y, mask, 3, groups, n_restarts=5, n_iter=60, tol=1e-6)
    m = f.meta
    assert m["start_labels"] == ["board", "svd"] + ["random"] * 5          # leaderboard-seeded start included
    assert len(m["start_objs"]) == 7 and len(m["start_iters"]) == 7
    assert m["best_start"] == int(np.argmin(m["start_objs"]))
    assert f.obj == pytest.approx(min(m["start_objs"]))                     # the kept fit is the lowest objective


def test_more_restarts_never_worse_and_nested():
    """Random starts are drawn in sequence from one seeded generator, so the 3-start set is a prefix of the larger one."""
    Y, mask, _, groups = synth()
    a = db.fit_structured(Y, mask, 3, groups, n_restarts=1, n_iter=60, tol=1e-6)
    b = db.fit_structured(Y, mask, 3, groups, n_restarts=6, n_iter=60, tol=1e-6)
    assert b.meta["start_objs"][:3] == pytest.approx(a.meta["start_objs"])
    assert b.obj <= a.obj + 1e-9


def test_warm_start_single_and_hetero_keeps_round0():
    Y, mask, _, groups = synth()
    f, _ = db.fit_heteroskedastic(Y, mask, 2, groups, n_restarts=3, n_iter=40, tol=1e-6)
    assert f.meta["start_labels"] == ["init"]                               # final round is warm-started only
    assert f.meta["round0"]["start_labels"] == ["board", "svd", "random", "random", "random"]


def test_lopo_fold_meta():
    Y, mask, paper, groups = synth()
    fm = []
    rows = db.leave_one_paper_out(Y, mask, paper, 2, groups, fold_meta=fm, n_restarts=2, n_iter=40, tol=1e-6)
    assert len(rows) > 0
    assert sorted(m["paper"] for m in fm) == sorted(np.unique(paper))
    assert all(len(m["start_objs"]) == 4 and m["start_labels"][0] == "board" for m in fm)


def test_summarise_starts():
    s = sens_restarts.summarise_starts([10.0, 12.0, 10.005, 9.0, 9.0005], ["board", "svd", "random", "random", "random"], n_original=3)
    assert s["min"] == 9.0 and s["max"] == 12.0 and s["n_starts"] == 5
    assert s["n_within_tol_of_best"] == 2 and s["best_label"] == "random"
    assert not s["best_in_original_starts"] and s["original_best_excess"] == pytest.approx(1.0) and s["board_excess"] == pytest.approx(1.0)


def test_sensitivity_run_smoke(tmp_path):
    Y, mask, paper, groups = synth()
    def kw(spec):
        return dict(groups=groups, ridge_u=3.0, ridge_g={"dataset": 3.0}, ridge_theta=3.0, n_restarts=1, n_iter=30, tol=1e-6)
    def paired_boot(a, b, papers, B=200):
        d = pd.DataFrame({"d": np.asarray(a, float) - np.asarray(b, float), "p": papers}).dropna(); g = [x.d.values for _, x in d.groupby("p")]
        rng = np.random.default_rng(0); bs = np.array([np.concatenate([g[i] for i in rng.integers(0, len(g), len(g))]).mean() for _ in range(B)])
        return {"mean": float(d.d.mean()), "ci90": [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))]}
    out = tmp_path / "s.json"
    r = sens_restarts.run(Y, mask, paper, kw, paired_boot, "none", (1, 2), 3, db.leave_one_paper_out, out, nproc=1, log=lambda *a: None)
    assert out.exists() and set(r["by_setting"]) == {"v2.1 (3 starts)", "5 starts"}
    f = r["folds"]["2"]
    assert f["n_folds"] == 4 and f["per_fold"][0]["n_starts"] == 5
    # folds whose best start is one of the original three give identical held-out predictions
    if f["folds_best_from_extra_start"] == 0:
        assert f["tasks_rho_changed"] == 0
    assert r["by_setting"]["5 starts"]["K_rule"]["best"] in (1, 2)


def test_fold_seed_varies_random_starts():
    Y, mask, paper, groups = synth()
    a, b = [], []
    db.leave_one_paper_out(Y, mask, paper, 2, groups, fold_meta=a, n_restarts=2, n_iter=20, tol=1e-6)
    db.leave_one_paper_out(Y, mask, paper, 2, groups, fold_meta=b, fold_seed_base=100, n_restarts=2, n_iter=20, tol=1e-6)
    for m, n in zip(a, b):
        assert m["start_objs"][:2] == pytest.approx(n["start_objs"][:2])                     # board and SVD starts unchanged
    assert any(m["start_objs"][2:] != pytest.approx(n["start_objs"][2:]) for m, n in zip(a, b))
    assert all(len(m["start_last_rel_change"]) == 4 for m in b)


def test_seed_sets_smoke(tmp_path):
    Y, mask, paper, groups = synth()
    def kw(spec):
        return dict(groups=groups, ridge_u=3.0, ridge_g={"dataset": 3.0}, ridge_theta=3.0, n_restarts=1, n_iter=15, tol=1e-6)
    def paired_boot(a, b, papers, B=100):
        d = pd.DataFrame({"d": np.asarray(a, float) - np.asarray(b, float), "p": papers}).dropna(); g = [x.d.values for _, x in d.groupby("p")]
        rng = np.random.default_rng(0); bs = np.array([np.concatenate([g[i] for i in rng.integers(0, len(g), len(g))]).mean() for _ in range(B)])
        return {"mean": float(d.d.mean()), "ci90": [float(np.percentile(bs, 5)), float(np.percentile(bs, 95))]}
    out = tmp_path / "s.json"
    sens_restarts.run(Y, mask, paper, kw, paired_boot, "none", (1, 2, 3, 4), 2, db.leave_one_paper_out, out, nproc=1, log=lambda *a: None)
    d = sens_restarts.run_seed_sets(Y, mask, paper, kw, paired_boot, "none", (1, 2, 3, 4), 2, db.leave_one_paper_out, out, [7], nproc=1, log=lambda *a: None)
    assert len(d["seed_sets"]) == 2 and d["n_iter"] == 15
    assert d["seed_set_range"]["n_sets"] == 2 and len(d["seed_set_range"]["K_rule"]) == 2
    assert d["seed_sets"][1]["by_K"]["4"]["starts_total"] == 4 * 4
