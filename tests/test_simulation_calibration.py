"""Simulation and calibration helpers of the D16 simulation (synthetic data only; no workbook)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import dataset_benchmarking as db  # noqa: E402


def design(M=30, papers=6, tasks_per_paper=8, n_datasets=12, density=0.8, seed=0):
    """Synthetic evaluation design: each paper evaluates a random subset of models on its tasks; each dataset appears
    in two papers."""
    rng = np.random.default_rng(seed)
    T = papers * tasks_per_paper
    tp = np.repeat([f"p{i}" for i in range(papers)], tasks_per_paper)
    td = np.array([f"d{(i * 5 + k) % n_datasets}" for i in range(papers) for k in range(tasks_per_paper)])
    mask = np.zeros((M, T), bool)
    for i in range(papers):
        ms = rng.random(M) < density
        mask[np.ix_(ms, tp == f"p{i}")] = True
    return mask, td, tp


def cells(Y, mask, td, tp):
    return db.calibration_stats(Y, mask, td, tp, db.tau_pair_index(mask))


def test_tau_pairs_fast_matches_tau_pairs_with_ties():
    mask, td, tp = design()
    rng = np.random.default_rng(1)
    Y = np.where(mask, rng.integers(0, 4, mask.shape).astype(float), 0.0)       # many ties and some constant pairs
    a = db.tau_pairs(Y, mask).sort_values(["i", "j"]).reset_index(drop=True)
    b = db.tau_pairs_fast(Y, db.tau_pair_index(mask)).sort_values(["i", "j"]).reset_index(drop=True)
    assert len(a) == len(b) > 0
    assert (a[["i", "j", "n"]].values == b[["i", "j", "n"]].values).all()
    assert np.allclose(a.tau.values, b.tau.values)


def test_spearman_small_matches_rank_scores():
    rng = np.random.default_rng(2)
    for _ in range(300):
        n = int(rng.integers(3, 15)); y = rng.integers(0, 4, n).astype(float); p = rng.integers(0, 3, n).astype(float)
        a, b = db._spearman_small(y, p), db._rank_scores(y, p)[0]
        assert (np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-12


def test_board_per_task_mean_equals_scalar():
    mask, td, tp = design()
    Y, _, _ = db.simulate(mask, td, tp, 2, general_mean=0.8, seed=3)
    R = db.board_lopo_rho(Y, mask, tp, per_task=True)
    assert set(R.columns) == {"paper", "rho"} and len(R) > 0
    assert R.rho.mean() == pytest.approx(db.board_lopo_rho(Y, mask, tp))


def test_paper_effect_raises_within_source_tau():
    mask, td, tp = design()
    diff = []
    for pe in (0.0, 2.0):
        st = [cells(db.simulate(mask, td, tp, 2, snr=2.0, paper_effect=pe, general_mean=0.5, seed=s)[0], mask, td, tp) for s in range(4)]
        diff.append(np.mean([x["tau_ss_dd"] - x["tau_xs_dd"] for x in st]))
    assert diff[1] > diff[0] + 0.1


def test_general_factor_makes_naive_leaderboard_predictive():
    mask, td, tp = design()
    b = {gm: np.mean([db.board_lopo_rho(db.simulate(mask, td, tp, 2, snr=2.0, general_mean=gm, seed=s)[0], mask, tp) for s in range(4)]) for gm in (0.0, 1.0)}
    assert b[1.0] > 0.3
    assert abs(b[0.0]) < 0.15 and b[1.0] > b[0.0] + 0.25


def test_target_intervals_contain_cell_means():
    mask, td, tp = design()
    Y, _, _ = db.simulate(mask, td, tp, 2, snr=2.0, paper_effect=1.0, general_mean=0.6, seed=4)
    T = db.calibration_target_intervals(Y, mask, td, tp, B=200)
    st = cells(Y, mask, td, tp)
    for k in db.CAL_TARGETS:
        assert T[k]["value"] == pytest.approx(st[k], abs=1e-4)
        assert T[k]["ci90"][0] <= T[k]["value"] <= T[k]["ci90"][1] and T[k]["se"] > 0


def test_choose_calibration_picks_closest_and_flags_edges():
    targets = {k: {"value": 0.2, "ci90": [0.1, 0.3], "se": 0.05} for k in db.CAL_TARGETS}
    axes = ((0.0, 0.5, 1.0), (1.0, 2.0))
    res = [((a, b), {k: 0.2 + abs(a - 0.5) + 0.01 * b for k in db.CAL_TARGETS}) for a in axes[0] for b in axes[1]]
    ch = db.choose_calibration(res, targets, axes)
    assert ch["params"] == (0.5, 1.0)
    assert ch["edge_params"] == [1]                      # 0.5 is interior; 1.0 is the low edge of the second axis
    assert ch["all_inside"] and all(f["inside"] for f in ch["fit"].values())
    # a point far from one target is reported as outside
    res2 = [((0.5, 1.0), {**{k: 0.2 for k in db.CAL_TARGETS}, "tau_ss_dd": 0.5})]
    ch2 = db.choose_calibration(res2, targets, axes)
    assert not ch2["all_inside"] and not ch2["fit"]["tau_ss_dd"]["inside"] and ch2["fit"]["board"]["inside"]
    # non-finite statistics are never chosen
    res3 = res + [((0.0, 2.0), {k: np.nan for k in db.CAL_TARGETS})]
    assert db.choose_calibration(res3, targets, axes)["params"] == (0.5, 1.0)
