#!/usr/bin/env python3
"""Build a split manifest and nested label-fraction subsets (decisions 6 and 9).

  python3 scripts/make_manifest.py manifest --root DATA --files files.csv --out manifests/<task>/train.csv
      files.csv: sample_id,relpath  (one row per file). Writes sample_id,relpath,sha256,bytes
      and prints the manifest's own SHA-256 for the task's splits.*.manifests entry.

  python3 scripts/make_manifest.py subsets --strata strata.csv --fractions 1 0.1 0.01 --runs 10 --min 10 --out manifests/<task>/subsets
      strata.csv: sample_id,stratum. For each run r, samples are shuffled within each stratum with seed r;
      a fraction f keeps the first ceil(f * n) of each stratum, so smaller fractions are nested in larger ones.
      Fractions giving fewer than --min samples are skipped and reported.
"""
import argparse, csv, hashlib, math, random, sys
from collections import defaultdict
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(a):
    root, out = Path(a.root), Path(a.out)
    rows = list(csv.DictReader(open(a.files)))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "relpath", "sha256", "bytes"])
        for r in sorted(rows, key=lambda r: (r["sample_id"], r["relpath"])):
            p = root / r["relpath"]
            w.writerow([r["sample_id"], r["relpath"], sha256(p), p.stat().st_size])
    print(f"{out}: {len({r['sample_id'] for r in rows})} samples, sha256 {sha256(out)}")


def subsets(a):
    strata = defaultdict(list)
    for r in csv.DictReader(open(a.strata)):
        strata[r["stratum"]].append(r["sample_id"])
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for run in range(a.runs):
        order = {}
        for s, ids in strata.items():
            ids = sorted(ids); random.Random(run).shuffle(ids); order[s] = ids
        for fr in a.fractions:
            keep = [i for ids in order.values() for i in ids[:math.ceil(fr * len(ids))]]
            if len(keep) < a.min:
                print(f"skip fraction {fr} run {run}: {len(keep)} < {a.min} samples"); continue
            p = out / f"frac{fr:g}-run{run}.txt"
            p.write_text("\n".join(sorted(keep)) + "\n")
    print(f"wrote subsets to {out}")


ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sp = ap.add_subparsers(dest="cmd", required=True)
m = sp.add_parser("manifest"); m.add_argument("--root", required=True); m.add_argument("--files", required=True); m.add_argument("--out", required=True)
s = sp.add_parser("subsets"); s.add_argument("--strata", required=True); s.add_argument("--fractions", type=float, nargs="+", default=[1, 0.1, 0.01])
s.add_argument("--runs", type=int, default=10); s.add_argument("--min", type=int, default=10); s.add_argument("--out", required=True)
a = ap.parse_args()
manifest(a) if a.cmd == "manifest" else subsets(a)
