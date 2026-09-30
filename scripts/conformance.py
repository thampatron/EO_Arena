#!/usr/bin/env python3
"""Check real samples against a task template (decision 9).

  python3 scripts/conformance.py spec/tasks/<task>.json SAMPLE.npz [SAMPLE.npz ...]

Expects samples in the EOArena delivery format, one .npz per sample:
  <mod>        (T, C, H, W) array in the stored dtype
  <mod>_valid  (T, H, W) bool, true = valid
  <mod>_dates  (T,) ISO 8601 strings            if acquisition_time is per-step
  lon, lat     scalars in EPSG:4326              if location is not 'none'
  target       per the target kind
Converting each dataset into this format is a separate, per-dataset step.
"""
import json, sys
import numpy as np

RANGES = {"toa_reflectance": (-0.2, 2.0), "surface_reflectance": (-0.2, 2.0), "sigma0_backscatter": (-60, 40), "gamma0_backscatter": (-60, 40)}


def check(task, path):
    errs, z = [], np.load(path, allow_pickle=False)
    meta = task["sample_metadata"]
    for key, m in task["inputs"].items():
        if key not in z:
            if m.get("required", True):
                errs.append(f"missing required modality {key}")
            continue
        x, r, T = z[key], m["raster"], m["time"]["steps"]
        size = m["grid"]["size_px"]; H, W = (size, size) if isinstance(size, int) else size
        if x.ndim != 4 or x.shape[1:] != (len(m["bands"]), H, W) or x.shape[0] != T:
            errs.append(f"{key}: shape {x.shape}, expected ({T}, {len(m['bands'])}, {H}, {W})")
            continue
        if str(x.dtype) != r["stored_dtype"]:
            errs.append(f"{key}: dtype {x.dtype}, template says {r['stored_dtype']}")
        v = z.get(f"{key}_valid")
        if v is None or v.dtype != bool or v.shape != (x.shape[0],) + x.shape[2:]:
            errs.append(f"{key}: needs a boolean {key}_valid mask of shape (T, H, W)"); continue
        nd = r["nodata"]
        if nd is not None:
            hit = np.isnan(x) if nd == "NaN" else (x == nd)
            if (hit.any(axis=1) & v).any():
                errs.append(f"{key}: nodata pixels are marked valid")
        spectral = [i for i, b in enumerate(m["bands"]) if "band" in b]
        lo_hi = RANGES.get(m.get("quantity"))
        if lo_hi and r["scale"] is not None and spectral and v.any():
            phys = x[:, spectral].astype("float64") * r["scale"] + (r["offset"] or 0)
            vals = np.moveaxis(phys, 1, -1)[v]
            vals = vals[np.isfinite(vals)]
            if vals.size and (np.percentile(vals, 1) < lo_hi[0] or np.percentile(vals, 99) > lo_hi[1]):
                errs.append(f"{key}: physical values outside {lo_hi} for {m['quantity']}; check scale, offset and unit")
        if meta["acquisition_time"] == "per-step":
            d = z.get(f"{key}_dates")
            if d is None or len(d) != x.shape[0]:
                errs.append(f"{key}: needs {key}_dates with one ISO date per step")
    if meta["location"] != "none":
        if "lon" not in z or "lat" not in z or not (-180 <= float(z["lon"]) <= 180 and -90 <= float(z["lat"]) <= 90):
            errs.append("needs lon and lat in EPSG:4326")
    t, tg = task["target"], z.get("target")
    if tg is None:
        errs.append("missing target")
    elif t.get("classes"):
        allowed = {c["index"] for c in t["classes"]} | ({t["ignore_index"]} if t.get("ignore_index") is not None else set())
        bad = set(np.unique(tg).tolist()) - allowed
        if bad:
            errs.append(f"target has values outside the class list: {sorted(bad)[:5]}")
    return errs


task = json.load(open(sys.argv[1]))
failed = 0
for p in sys.argv[2:]:
    e = check(task, p)
    failed += bool(e)
    print(f"{p}: " + ("OK" if not e else "\n  " + "\n  ".join(e)))
sys.exit(1 if failed else 0)
