import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import sys
def build(flags=()):
    sys.argv = ["x", WB, *flags]
    src = open(ROOT+"/scripts/build_dataset_analysis.py").read()
    src = src[:src.index("# ============================================================================= 2. model-free tests")]
    g = {"__file__": ROOT+"/scripts/build_dataset_analysis.py", "__name__": "x"}
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()): exec(compile(src, "b", "exec"), g)
    return g
