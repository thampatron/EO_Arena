"""Row construction for the GeoFM evidence table, shared by build_evidence.py and build_dataset_analysis.py.

Verbatim from build_evidence.py (sections 1 and make_cells) so both builds apply identical inclusion rules: original
results only; ablations, non-foundation baselines and from-scratch rows dropped; printed seed SDs parsed; unit repair;
task = paper | benchmark | protocol | metric | train fraction; self-reported flag per (model, paper).
"""
import json, re
from pathlib import Path
import numpy as np, pandas as pd

MIN_MODELS = 4
ROOT = Path(__file__).resolve().parent.parent


def load(src, min_models=MIN_MODELS):
    """Returns (r, TINFO, make_cells, breg, mreg, srcs)."""
    src = Path(src); MIN_MODELS_ = min_models
    X = src / "metaanalysis_benchmark_table_v4.xlsx"
    r = pd.read_excel(X, "results_long")
    breg = pd.read_excel(X, "benchmark_registry").drop_duplicates("benchmark_id").set_index("benchmark_id")
    mreg = pd.read_excel(X, "model_registry").drop_duplicates("model_id").set_index("model_id")
    srcs = pd.read_excel(X, "sources").drop_duplicates("paper_key").set_index("paper_key")
    # title clean-up: LaTeX residue in two workbook titles
    srcs.loc[srcs.index.isin(["tessera_v2"]), "title"] = "TESSERA v2: Scaling Pixel-wise Earth Foundation Models"
    srcs.loc[srcs.index.isin(["neuco-bench"]), "title"] = srcs.loc[srcs.index.isin(["neuco-bench"]), "title"].str.replace(r"^blind\s+", "", regex=True)
    srcs.loc[srcs.index.isin(["geobench_v2_leaderboard"]), "title"] = "GEO-Bench-2 public leaderboard (Hugging Face)"
    def paper_url(ident):
        ident = str(ident or "")
        m = re.search(r"arXiv:(\d{4}\.\d{4,5})", ident)
        if m: return f"https://arxiv.org/abs/{m.group(1)}"
        m = re.search(r"https?://\S+", ident)
        return re.sub(r"@[0-9a-f]{6,40}$", "", m.group(0).rstrip(").,")) if m else None
    bmap = pd.read_csv((src / "benchmark_map.csv") if (src / "benchmark_map.csv").exists() else ROOT / "data" / "benchmark_map.csv", dtype=str).fillna("").set_index("benchmark_id")
    known = {d["id"] for d in json.loads((ROOT / "data" / "datasets.json").read_text(encoding="utf-8"))}

    r = r[(r.exclude_from_analysis != 1) & (r.agreement_vs_recitation == "original") & (~r.model_id.astype(str).str.contains("_abl"))
          & (r.is_non_foundation_baseline != 1) & (r.evaluation_protocol != "scratch")].copy()
    r["v"] = pd.to_numeric(r.result_normalized, errors="coerce"); r = r[r.v.notna()].copy()
    # replicate noise per cell: per-seed values listed in the cell, or a printed mean +/- sd, rescaled to result_normalized units
    pat = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:±|\\pm|\+/-|\$\\pm\$)\s*(\d+(?:\.\d+)?)"); pat2 = re.compile(r"(-?\d+(?:\.\d+)?)\s*\(\s*(\d+(?:\.\d+)?)\s*\)")
    pat_seeds = re.compile(r"seeds?\s+((?:\d+:\s*-?\d+(?:\.\d+)?,?\s*)+)")
    def parse(s):
        m = pat_seeds.search(s)
        if m:
            vals = np.array([float(x) for x in re.findall(r"\d+:\s*(-?\d+(?:\.\d+)?)", m.group(1))])
            if len(vals) >= 3: return float(vals.mean()), float(vals.std(ddof=1)), "seeds", len(vals)
        m = pat.search(s) or pat2.search(s)
        return (float(m.group(1)), float(m.group(2)), "printed", np.nan) if m else (np.nan, np.nan, "", np.nan)
    P = r.raw_cell.astype(str).map(parse)
    r["pm_mean"] = [p[0] for p in P]; r["pm_sd"] = [p[1] for p in P]; r["sd_kind"] = [p[2] for p in P]; r["n_seeds"] = [p[3] for p in P]
    # number of replicates behind a reported mean: the seed list's length, else the count the paper states (from its notes), else 3 (assumed)
    N_REPS = {"geobench_v2_leaderboard": 5, "earthshift": 5, "geocross-bench": 5, "melt-salt": 10, "mind": 5, "presto": 3, "prithvi_v2": 10,
              "ss_vision_transformers_for_lc": 5, "tessera_v2": 5, "agbd_eval": 3}
    N_REPS_DEFAULT = 3
    # unit repair: some workbook rows tagged percent_printed store the value as a fraction (e.g. r2 printed "67.1 ± 2.9", stored 0.671).
    # Detect by the printed number being ~100x the stored value and restore percent units (value and SD), so spread and noise are in points.
    raw_first = pd.to_numeric(r.raw_cell.astype(str).str.extract(r"(-?\d+(?:\.\d+)?)")[0], errors="coerce")
    fix = (r.scale_basis == "percent_printed") & (r.v.abs() <= 1.5) & (raw_first.abs() > 1.5) & ((raw_first / r.v.where(r.v != 0)).sub(100).abs() < 1)
    r.loc[fix, "v"] = r.loc[fix, "v"] * 100; r.loc[fix, "pm_mean"] = raw_first[fix]
    r["unit_fixed"] = fix
    r["n_reps"] = np.where(r.sd_kind == "seeds", r.n_seeds, np.where(r.sd_kind == "printed", r.paper_key.map(N_REPS).fillna(N_REPS_DEFAULT), 1.0)).astype(float)
    r["n_reps_known"] = (r.sd_kind == "seeds") | r.paper_key.isin(N_REPS)
    ratio = (r.v / r.pm_mean).where(r.pm_mean.abs() > 0); r["sd"] = r.pm_sd * ratio.where(ratio.notna(), 1.0)
    r.loc[~np.isfinite(r.sd) | (r.sd <= 0), "sd"] = np.nan; r.loc[r.sd.isna(), "n_reps"] = 1.0   # a printed "± 0.00" is below the table's precision
    r["y"] = np.where(r.higher_is_better.astype(str) == "True", r.v, -r.v)
    r["pts"] = r.scale_basis.isin(["percent_printed", "fraction_printed"])
    PF = lambda p: "fine-tuned" if p in ("FT", "PFT") else "frozen" if p in ("frozen_dec", "LP", "kNN", "frozen", "frozen_best", "PE", "MLP") else str(p)
    r["pf"] = r.evaluation_protocol.map(PF)
    for c in ["canonical_dataset", "eoarena_id", "domain", "subdomain", "input_kind"]: r[c] = r.benchmark_id.map(bmap[c]).fillna("")
    r["task"] = r.paper_key.astype(str) + "|" + r.benchmark_id.astype(str) + "|" + r.evaluation_protocol.astype(str) + "|" + r.metric.astype(str) + "|" + r.train_fraction_norm.astype(str)
    own = r[r.is_self_reported == True].groupby("model_id").paper_key.agg(set).to_dict()
    r["self"] = [p in own.get(m, set()) for m, p in zip(r.model_id, r.paper_key)]
    print(f"{len(r)} result rows ({int(r.unit_fixed.sum())} restored from fraction to percent units)")

    TINFO = r.drop_duplicates("task").set_index("task")[["paper_key", "benchmark_id", "evaluation_protocol", "pf", "metric", "train_fraction_norm", "pts",
                                                          "canonical_dataset", "eoarena_id", "domain", "subdomain", "input_kind"]]
    TINFO["task_type"] = TINFO.benchmark_id.map(breg.task_type).fillna(""); TINFO["sensor"] = TINFO.benchmark_id.map(breg.sensor).fillna("")

    def make_cells(drop_self: bool):
        rr = r[~r.self] if drop_self else r
        cell = rr.groupby(["task", "model_id"]).agg(y=("y", "mean"), sd=("sd", "mean"), n_reps=("n_reps", "max"), n_known=("n_reps_known", "max"), selfrep=("self", "max")).rename(columns={"selfrep": "self"}).reset_index()
        n = cell.groupby("task").model_id.nunique(); return cell[cell.task.isin(n[n >= MIN_MODELS_].index)].copy()
    return r, TINFO, make_cells, breg, mreg, srcs
