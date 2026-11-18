import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import sys, contextlib, io
def build(flags=(), extra_cats=("baseline_random","task_architecture","baseline_pretrained","classical_baseline","feature_baseline","trivial_baseline")):
    """Same build as prefix.build but keeps baseline rows (so each task can carry its supervised baseline)."""
    sys.argv = ["x", WB, *flags]
    src = open(ROOT+"/scripts/build_dataset_analysis.py").read()
    src = src[:src.index("# ============================================================================= 2. model-free tests")]
    a = 'keep(r.is_geofm, "not a GeoFM (baseline / task architecture / uncategorised)")'; assert a in src
    src = src.replace(a, f'keep(r.is_geofm | r.category.isin({set(extra_cats)!r}), "not a GeoFM or kept baseline")')
    g = {"__file__": ROOT+"/scripts/build_dataset_analysis.py", "__name__": "x"}
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, "b", "exec"), g)
    return g
