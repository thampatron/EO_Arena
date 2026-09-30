#!/usr/bin/env python3
"""Export the taxonomy as STAC (one Collection per dataset) and Croissant (one JSON-LD per dataset).

Run from the repository root:  python3 scripts/export.py
Outputs go to export/stac/ and export/croissant/. These are metadata records: they describe the
datasets and their EOArena tags and point to the providers; they do not redistribute any data.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = json.loads((ROOT / "data/datasets.json").read_text(encoding="utf-8"))
V = {f["key"]: f for f in json.loads((ROOT / "data/vocabulary.json").read_text(encoding="utf-8"))["facets"]}
T = json.loads((ROOT / "data/tasks.json").read_text(encoding="utf-8"))
SPEC = json.loads((ROOT / "data/sensor_specs.json").read_text(encoding="utf-8"))
GEO = json.loads((ROOT / "data/countries.geojson").read_text(encoding="utf-8"))
SITE = "https://thampatron.github.io/EO_Arena/"

SPDX = {"CC BY 4.0": "CC-BY-4.0", "CC BY-SA 4.0": "CC-BY-SA-4.0", "CC BY-NC 4.0": "CC-BY-NC-4.0",
        "CC BY-NC-SA 4.0": "CC-BY-NC-SA-4.0", "CC0": "CC0-1.0", "MIT": "MIT", "Apache-2.0": "Apache-2.0",
        "CDLA-Permissive-1.0": "CDLA-Permissive-1.0", "CDLA-Permissive-2.0": "CDLA-Permissive-2.0",
        "GPL-3.0": "GPL-3.0-only", "CC BY-SA 3.0": "CC-BY-SA-3.0"}

def spdx(lic):
    for k, v in SPDX.items():
        if re.fullmatch(re.escape(k) + r"(\s*\(.*\))?", lic.strip()):
            return v
    return "other"

def bounds(coords, acc):
    if isinstance(coords[0], (int, float)):
        acc[0] = min(acc[0], coords[0]); acc[1] = min(acc[1], coords[1])
        acc[2] = max(acc[2], coords[0]); acc[3] = max(acc[3], coords[1])
    else:
        for c in coords:
            bounds(c, acc)

BOX = {}
for f in GEO["features"]:
    acc = [180, 90, -180, -90]; bounds(f["geometry"]["coordinates"], acc); BOX[f["id"]] = acc

def bbox(d):
    cs = d["footprint"].get("countries")
    if not cs:
        return [[-180, -90, 180, 90]]
    return [BOX[c] for c in cs]  # one box per country; first box is the union below

def union(boxes):
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]

def label(k, v):
    return V[k]["values"].get(v, v)

def keywords(d):
    kw = [d["domain"].split(" · ")[-1], d["subdomain"]]
    for k in ("task", "tmp", "sen", "res", "p"):
        kw += [label(k, v) for v in d["facets"][k]]
    return sorted(set(kw))

def clean(s):
    return re.sub(r"&gt;", ">", re.sub(r"&lt;", "<", s))

def description(d):
    return clean(f"{d['task_description']}. Inputs: {d['sensors_description']}. Geography: {d['geography']}. Size: {d['size']}. Licence as stated by the provider: {d['licence']}.")

tasks_by_ds = {}
for t in T:
    tasks_by_ds.setdefault(t["dataset_id"], []).append(t)

def eo_bands(tasks):
    out, seen = [], set()
    for t in tasks:
        for s in t["input"]["sensors"]:
            for b in s["bands"]:
                if "center_wavelength_um" in b and b["name"] not in seen:
                    seen.add(b["name"])
                    out.append({"name": b["name"], "common_name": b["common_name"], "center_wavelength": b["center_wavelength_um"], "full_width_half_max": b["fwhm_um"]})
    return out

# ---------- STAC
stac = ROOT / "export/stac"; (stac / "collections").mkdir(parents=True, exist_ok=True)
catalog = {"type": "Catalog", "stac_version": "1.0.0", "id": "eoarena-taxonomy", "title": "EOArena task taxonomy",
           "description": "Metadata-only catalogue of labelled Earth observation datasets, tagged with the EOArena taxonomy facets.",
           "links": [{"rel": "root", "href": "./catalog.json", "type": "application/json"},
                     {"rel": "self", "href": "./catalog.json", "type": "application/json"},
                     {"rel": "about", "href": SITE, "type": "text/html"}]}
for d in D:
    boxes = bbox(d)
    ts = tasks_by_ds.get(d["id"], [])
    col = {"type": "Collection", "stac_version": "1.0.0", "id": d["id"], "title": clean(d["name"]),
           "description": description(d), "license": spdx(d["licence"]), "keywords": keywords(d),
           "extent": {"spatial": {"bbox": [union(boxes)] + (boxes if len(boxes) > 1 else [])}, "temporal": {"interval": [[None, None]]}},
           "summaries": {"eoarena:facets": d["facets"], "eoarena:footprint": d["footprint"]},
           "links": [{"rel": "root", "href": "../catalog.json", "type": "application/json"},
                     {"rel": "parent", "href": "../catalog.json", "type": "application/json"},
                     {"rel": "self", "href": f"./{d['id']}.json", "type": "application/json"}]
                    + [{"rel": "describedby" if i == 0 else "related", "href": s["url"], "title": s["label"], "type": "text/html"} for i, s in enumerate(d["sources"])]}
    if d["benchmark_suites"]:
        col["summaries"]["eoarena:benchmark_suites"] = d["benchmark_suites"]
    bands = eo_bands(ts)
    if bands:
        col["stac_extensions"] = ["https://stac-extensions.github.io/eo/v1.1.0/schema.json"]
        col["summaries"]["eo:bands"] = bands
    if ts:
        col["summaries"]["eoarena:tasks"] = [t["id"] for t in ts]
    (stac / "collections" / f"{d['id']}.json").write_text(json.dumps(col, indent=1, ensure_ascii=False), encoding="utf-8")
    catalog["links"].append({"rel": "child", "href": f"./collections/{d['id']}.json", "type": "application/json", "title": clean(d["name"])})
(stac / "catalog.json").write_text(json.dumps(catalog, indent=1, ensure_ascii=False), encoding="utf-8")

# ---------- Croissant (metadata-level, Croissant 1.0)
CTX = {"@language": "en", "@vocab": "https://schema.org/", "citeAs": "cr:citeAs", "column": "cr:column",
       "conformsTo": "dct:conformsTo", "cr": "http://mlcommons.org/croissant/", "rai": "http://mlcommons.org/croissant/RAI/",
       "data": {"@id": "cr:data", "@type": "@json"}, "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
       "dct": "http://purl.org/dc/terms/", "examples": {"@id": "cr:examples", "@type": "@json"}, "extract": "cr:extract",
       "field": "cr:field", "fileProperty": "cr:fileProperty", "fileObject": "cr:fileObject", "fileSet": "cr:fileSet",
       "format": "cr:format", "includes": "cr:includes", "isLiveDataset": "cr:isLiveDataset", "jsonPath": "cr:jsonPath",
       "key": "cr:key", "md5": "cr:md5", "parentField": "cr:parentField", "path": "cr:path", "recordSet": "cr:recordSet",
       "references": "cr:references", "regex": "cr:regex", "repeated": "cr:repeated", "replace": "cr:replace",
       "sc": "https://schema.org/", "separator": "cr:separator", "source": "cr:source", "subField": "cr:subField",
       "transform": "cr:transform", "samplingRate": "cr:samplingRate", "equivalentProperty": "cr:equivalentProperty"}
LIC_URL = {"CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/", "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
           "CC-BY-NC-4.0": "https://creativecommons.org/licenses/by-nc/4.0/", "CC-BY-NC-SA-4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
           "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/", "MIT": "https://opensource.org/license/mit",
           "Apache-2.0": "https://www.apache.org/licenses/LICENSE-2.0", "CDLA-Permissive-1.0": "https://cdla.dev/permissive-1-0/",
           "CDLA-Permissive-2.0": "https://cdla.dev/permissive-2-0/", "GPL-3.0-only": "https://www.gnu.org/licenses/gpl-3.0.html",
           "CC-BY-SA-3.0": "https://creativecommons.org/licenses/by-sa/3.0/"}
cro = ROOT / "export/croissant"; cro.mkdir(parents=True, exist_ok=True)
for d in D:
    s = spdx(d["licence"])
    doc = {"@context": CTX, "@type": "sc:Dataset", "conformsTo": "http://mlcommons.org/croissant/1.0",
           "name": clean(d["name"]), "description": description(d), "url": d["sources"][0]["url"],
           "license": LIC_URL.get(s, clean(d["licence"])), "keywords": keywords(d),
           "sameAs": [x["url"] for x in d["sources"][1:]],
           "isAccessibleForFree": d["facets"]["tier"][0] in ("open", "reg", "nc")}
    (cro / f"{d['id']}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"STAC: {len(D)} collections in export/stac; Croissant: {len(D)} files in export/croissant")
