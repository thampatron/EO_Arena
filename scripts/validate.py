#!/usr/bin/env python3
"""Validate data/datasets.json against data/vocabulary.json.

Run from the repository root:  python3 scripts/validate.py
Exits non-zero and lists every problem if any record is invalid.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
vocab = json.loads((ROOT / "data" / "vocabulary.json").read_text(encoding="utf-8"))
datasets = json.loads((ROOT / "data" / "datasets.json").read_text(encoding="utf-8"))

facets = {f["key"]: f for f in vocab["facets"]}
TAGGED = [k for k, f in facets.items() if not f.get("derived")]  # facets stored per record
REQUIRED = ["id", "name", "domain", "subdomain", "task_description", "sensors_description",
            "geography", "size", "facets", "licence", "benchmark_suites", "sources"]
MULTI_OK = {"task", "sen", "res", "ab"}  # facets that may hold several values

errors = []
seen = set()
for i, d in enumerate(datasets):
    where = f"record {i} ({d.get('id', '?')})"
    for field in REQUIRED:
        if field not in d:
            errors.append(f"{where}: missing field '{field}'")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(d.get("id", ""))):
        errors.append(f"{where}: id must be lowercase words joined by hyphens")
    if d.get("id") in seen:
        errors.append(f"{where}: duplicate id")
    seen.add(d.get("id"))
    if d.get("domain") not in facets["dom"]["values"]:
        errors.append(f"{where}: unknown domain '{d.get('domain')}'")
    if d.get("subdomain") not in facets["sub"]["values"]:
        errors.append(f"{where}: unknown subdomain '{d.get('subdomain')}'")
    tags = d.get("facets", {})
    for k in TAGGED:
        vals = tags.get(k)
        if not vals:
            errors.append(f"{where}: facet '{k}' ({facets[k]['name']}) has no value")
            continue
        if len(vals) > 1 and k not in MULTI_OK:
            errors.append(f"{where}: facet '{k}' ({facets[k]['name']}) takes one value, got {vals}")
        for v in vals:
            if v not in facets[k]["values"]:
                allowed = ", ".join(facets[k]["values"])
                errors.append(f"{where}: '{v}' is not a value of '{k}' ({facets[k]['name']}). Allowed: {allowed}")
    extra = set(tags) - set(TAGGED)
    if extra:
        errors.append(f"{where}: unknown facet keys {sorted(extra)}")
    if not d.get("sources"):
        errors.append(f"{where}: needs at least one source")
    for s in d.get("sources", []):
        if not str(s.get("url", "")).startswith(("https://", "http://")):
            errors.append(f"{where}: source '{s.get('label')}' needs an http(s) URL")
    if not isinstance(d.get("benchmark_suites", []), list):
        errors.append(f"{where}: benchmark_suites must be a list")

if errors:
    print(f"{len(errors)} problem(s) found:\n")
    print("\n".join(errors))
    sys.exit(1)
print(f"OK: {len(datasets)} datasets, {len(facets)} facets, all values in the vocabulary.")
