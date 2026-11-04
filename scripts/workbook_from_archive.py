#!/usr/bin/env python3
"""Rebuild metaanalysis_benchmark_table_v4.xlsx from the compact archive kept in the (private) EO-Arena project.

The archive is base64( xz( tar of one CSV per workbook sheet ) ), with members named NN__<sheet>.csv in sheet order.
It is not in this repository: the workbook is unpublished. The scheduled agent team downloads it from the project.

Usage: python3 -I scripts/workbook_from_archive.py <archive.b64> <out_dir>
Writes <out_dir>/metaanalysis_benchmark_table_v4.xlsx and prints the archive's sha256 (expected value in the brief).
"""
import base64, hashlib, io, lzma, sys, tarfile
from pathlib import Path
import pandas as pd

src, out = Path(sys.argv[1]), Path(sys.argv[2])
blob = lzma.decompress(base64.b64decode(src.read_bytes()))
print("archive sha256", hashlib.sha256(blob).hexdigest())
out.mkdir(parents=True, exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(blob)) as tf, pd.ExcelWriter(out / "metaanalysis_benchmark_table_v4.xlsx", engine="openpyxl") as xw:
    for m in sorted(tf.getmembers(), key=lambda m: m.name):
        sheet = m.name.split("__", 1)[1][:-4]
        pd.read_csv(tf.extractfile(m), low_memory=False).to_excel(xw, sheet_name=sheet, index=False)
print("wrote", out / "metaanalysis_benchmark_table_v4.xlsx")
