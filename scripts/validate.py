#!/usr/bin/env python3
"""Validate data/datasets.json against data/vocabulary.json, and spec/tasks/*.json against spec/task.schema.json.

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
            "geography", "size", "facets", "licence", "benchmark_suites", "sources", "footprint"]
COUNTRIES = {f["id"] for f in json.loads((ROOT / "data" / "countries.geojson").read_text(encoding="utf-8"))["features"]}
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
    fp = d.get("footprint", {})
    if fp.get("scope") not in facets["fp"]["values"]:
        errors.append(f"{where}: footprint.scope must be one of {list(facets['fp']['values'])}")
    if fp.get("scope") == "countries" and not fp.get("countries"):
        errors.append(f"{where}: footprint scope 'countries' needs a countries list (ISO 3166-1 alpha-3)")
    for c in fp.get("countries", []):
        if c not in COUNTRIES:
            errors.append(f"{where}: unknown country code '{c}' (use ISO 3166-1 alpha-3 as in data/countries.geojson)")
    if not isinstance(d.get("benchmark_suites", []), list):
        errors.append(f"{where}: benchmark_suites must be a list")

# ---- Task templates (spec/tasks/*.json) ----
import jsonschema

schema = json.loads((ROOT / "spec" / "task.schema.json").read_text(encoding="utf-8"))
protocols = {p["id"]: p for p in json.loads((ROOT / "spec" / "protocols.json").read_text(encoding="utf-8"))["protocols"]}
sensors = json.loads((ROOT / "data" / "sensor_specs.json").read_text(encoding="utf-8"))
dataset_ids = {d.get("id") for d in datasets}
task_files = sorted((ROOT / "spec" / "tasks").glob("*.json"))


def resolve(doc, pointer):
    for part in pointer.lstrip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc


for path in task_files:
    where = f"spec/tasks/{path.name}"
    t = json.loads(path.read_text(encoding="utf-8"))
    for e in jsonschema.Draft202012Validator(schema).iter_errors(t):
        errors.append(f"{where}: {'/'.join(map(str, e.absolute_path)) or '(top)'}: {e.message}")
    if t.get("id") != path.stem:
        errors.append(f"{where}: id must equal the file name")
    if t.get("dataset_id") not in dataset_ids:
        errors.append(f"{where}: dataset_id '{t.get('dataset_id')}' is not in data/datasets.json")
    inputs = t.get("inputs", {})
    for key, m in inputs.items():
        spec = sensors.get(m.get("sensor"))
        if not spec:
            errors.append(f"{where}: inputs/{key}: unknown sensor '{m.get('sensor')}'")
            continue
        names = {b["name"] for b in spec["bands"]}
        for b in m.get("bands", []):
            if "band" in b and b["band"] not in names:
                errors.append(f"{where}: inputs/{key}: band '{b['band']}' not in {m['sensor']} registry")
        stats = t.get("normalisation_stats", {}).get("per_modality", {}).get(key)
        if stats:
            for k in ("mean", "std"):
                if len(stats[k]) != len(m.get("bands", [])):
                    errors.append(f"{where}: normalisation_stats {key}.{k} has {len(stats[k])} values for {len(m['bands'])} bands")
    for key in t.get("normalisation_stats", {}).get("per_modality", {}):
        if key not in inputs:
            errors.append(f"{where}: normalisation_stats names unknown modality '{key}'")
    grid = t.get("target", {}).get("grid")
    if grid not in inputs and grid != "none":
        errors.append(f"{where}: target.grid '{grid}' is not an input modality")
    classes = t.get("target", {}).get("classes")
    if classes and [c["index"] for c in classes] != list(range(len(classes))):
        errors.append(f"{where}: class indices must run 0..n-1 in order")
    for pid in t.get("evaluation", {}).get("protocols", []):
        if pid not in protocols:
            errors.append(f"{where}: unknown protocol '{pid}'")
        elif t.get("task_type") not in protocols[pid]["task_types"]:
            errors.append(f"{where}: protocol '{pid}' does not support task type '{t.get('task_type')}'")
    for ptr in t.get("unverified", []):
        try:
            resolve(t, ptr)
        except (KeyError, IndexError, ValueError, TypeError):
            errors.append(f"{where}: unverified pointer '{ptr}' does not resolve")

if errors:
    print(f"{len(errors)} problem(s) found:\n")
    print("\n".join(errors))
    sys.exit(1)
print(f"OK: {len(datasets)} datasets, {len(facets)} filters, all values in the vocabulary; {len(task_files)} task templates valid.")
