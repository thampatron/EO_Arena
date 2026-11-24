#!/usr/bin/env python3
"""Extend the hand-curated v4 mappings to workbook v5 by the same rules (docs/analysis-decisions.md D1-D7, D19).

Run once on a v5 workbook; it APPENDS entries for ids the v4 files do not cover and never changes a curated v4 entry.
Every appended entry carries "source": "v5_rule" (JSON) or mapping_source = v5_* (CSV), and every decision is listed with
its rule in data/v5_mapping_review.csv for the team to check. Inputs are workbook registries and table roles only
(no result values). Usage: python3 -I scripts/v5/extend_mappings.py <dir with metaanalysis_benchmark_table_v4.xlsx built from v5> <v4 results_long.csv>
(ids already in the v4 workbook keep their v4 treatment.)

Rules
- Table placement / ablation (D1-D3): tables not in table_locations.json take v5 `table_role`: main -> main, appendix_full_results
  -> appendix, ablation / sweep -> ablation table.
- GeoFM scope (model_scope.json): registry category in geofm_categories, or category baseline_pretrained with Earth-observation
  pretraining imagery (the v4 rule: EO corpora in, ImageNet / natural-image corpora out).
- Paper-internal baselines and reproductions (v4 excluded_uncategorised): registry row_role = baseline or variant_kind =
  retrained_method are out of scope.
- Paper-internal variants (D7): in its introducing paper, a registry variant (variant_kind ablation / sweep / replica) of
  that paper's own method.
- Family (D19): (1) v4 curated id -> its family; (2) variant_parent / supersedes chain to a curated id; (3) a curated family name
  that is a token prefix of the id, with every remaining token a size / input / resolution modifier; (4) otherwise a new family
  named by the id with size tokens removed (versions are NOT merged: v4 kept Prithvi v1 / v2 and TESSERA v1 / v2 apart).
  Pretraining imagery group from registry pretrain_input_modalities via the v5 sensors vocabulary; families with variants on
  different imagery are split by the pipeline as before.
- Canonical dataset: v5 corpus_family; reuse the v4 canonical name where the corpus already has exactly one, else the corpus
  key. input_kind from the benchmark's sensors (eo_imagery when any imaging sensor).
"""
import json, re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]; D = ROOT / "data"
X = Path(sys.argv[1]) / "metaanalysis_benchmark_table_v4.xlsx"
r = pd.read_excel(X, "results_long"); reg = pd.read_excel(X, "model_registry"); breg = pd.read_excel(X, "benchmark_registry")
sens = pd.read_excel(X, "sensors") if "sensors" in pd.ExcelFile(X).sheet_names else None
review = []

# ---------------------------------------------------------------- sensors vocabulary
SF = dict(zip(sens.sensor, sens.sensor_family)) if sens is not None else {}
def fam_of(code):
    c = str(code).strip().lower()
    if c in SF: return SF[c]
    if "sar" in c: return "sar"
    if "vhr" in c or "rgb" in c or "aerial" in c: return "optical_vhr"
    if "optical" in c or c in ("s2", "landsat", "hls", "modis"): return "optical_ms"
    return c
def pretrain_group(mods):
    if not isinstance(mods, str) or not mods.strip(): return None
    f = {fam_of(c) for c in mods.split(";")}
    sar = "sar" in f; ms = bool(f & {"optical_ms", "hyperspectral"}); vhr = bool(f & {"optical_vhr", "aerial"}) or "aerial_rgb" in mods or "naip" in mods
    if sar and (ms or vhr): return "multi-sensor (SAR + optical)"
    if ms: return "multispectral optical"
    if vhr: return "high-resolution RGB"
    if sar: return "SAR"
    return "natural" if f & {"ground_photo", "text"} and not (f - {"ground_photo", "text"}) else None
IMAGING = {"optical_ms", "optical_vhr", "sar", "aerial", "hyperspectral", "lidar", "planetary"}

# ---------------------------------------------------------------- 1. table placement
LOC = json.loads((D / "table_locations.json").read_text()); have = {(t["paper"], t["file"], t["table_id"]) for t in LOC["tables"]}
r["file"] = r.locator.astype(str).str.replace(r":(\d+|p\d+)$", "", regex=True); r["table_id"] = r.table_id.astype(str)
tabs = r.groupby(["paper_key", "file", "table_id"]).agg(role=("table_role", lambda s: s.mode().iat[0]), n=("model_id", "size")).reset_index()
ROLE = {"main": ("main", False), "appendix_full_results": ("appendix", False), "ablation": ("main", True), "sweep": ("main", True)}
add_t = 0
for p, f, t, role, n in tabs.itertuples(index=False):
    if (p, f, t) in have or role not in ROLE: continue
    loc, abl = ROLE[role]
    LOC["tables"].append({"paper": p, "file": f, "table_id": t, "n_rows": int(n), "location": loc, "ablation": abl, "how": "v5 table_role", "evidence": f"table_role={role}", "source": "v5_rule"})
    add_t += 1
(D / "table_locations.json").write_text(json.dumps(LOC, indent=1, ensure_ascii=False))

# ---------------------------------------------------------------- 2. GeoFM scope and D7
S = json.loads((D / "model_scope.json").read_text()); A = json.loads((D / "model_attributes.json").read_text())
CATS = set(S["geofm_categories"]); EXTRA = set(S["geofm_uncategorised"]) | set(S.get("geofm_from_baseline_pretrained", {}))
rg = reg.drop_duplicates("model_id").set_index("model_id")
used = set(r[(r.agreement_vs_recitation == "original") & (r.exclude_from_analysis != 1)].model_id)
new_scope = {}
for m in sorted(used):
    if m in A["models"] or m in EXTRA or m not in rg.index: continue
    cat = str(rg.category.get(m, "")); grp = pretrain_group(rg.pretrain_input_modalities.get(m))
    if str(rg.row_role.get(m, "")) == "baseline" or str(rg.variant_kind.get(m, "")) == "retrained_method": continue
    if cat == "baseline_pretrained" and grp not in (None, "natural"):
        new_scope[m] = f"v5_rule: baseline_pretrained on EO imagery ({rg.pretrain_input_modalities.get(m)})"
        review.append({"kind": "scope", "id": m, "decision": "in (EO-pretrained baseline)", "rule": "baseline_pretrained + EO pretraining imagery"})
S.setdefault("geofm_from_baseline_pretrained", {}).update(new_scope)
own = r[r.is_self_reported == True].groupby("model_id").paper_key.agg(lambda s: sorted(set(s)))
piv_add = 0
for m in sorted(used):
    if m not in rg.index or str(rg.variant_kind.get(m, "")) not in ("ablation", "sweep", "replica"): continue
    for p in own.get(m, []):
        lst = S["paper_internal_variants"].setdefault(p, [])
        if m not in lst: lst.append(m); piv_add += 1; review.append({"kind": "D7", "id": m, "decision": f"paper-internal variant in {p}", "rule": f"variant_kind={rg.variant_kind.get(m)}"})
(D / "model_scope.json").write_text(json.dumps(S, indent=1, ensure_ascii=False))

# ---------------------------------------------------------------- 3. families (D19)
M = A["models"]; fams = sorted({v["family"] for v in M.values()}, key=len, reverse=True)
SIZE = re.compile(r"^(resnet\d+|wrn\d+|rn\d+|vit[stbhlg]?\d*|vit_?[stbhlg]|swin[tsblh]|base|large|small|tiny|nano|atto|huge|giant|[stblhg]|\d+m|\d+b|\d+k|\d+|x?l|xs|v?it7b|sovit\w*|convnextv2\w*)$")
MOD = re.compile(r"^(vit[stbhlg]?\d*|swin[tsblh]|base|large|small|tiny|nano|atto|huge|giant|[stblhg]|\d+m?|\d+b|ms|sar|rgb|s1|s2|sentinel|optical|multispectral|naip|temporal|nontemporal|stack|grouped|unspecified|si|mi|tl|fmow|resnet\d+|swin\w*|convnext\w*)$")
def chain(m, seen=()):
    for col in ("variant_parent", "supersedes_model_id"):
        p = rg[col].get(m) if m in rg.index else None
        if isinstance(p, str) and p and p not in seen:
            if p in M: return p
            q = chain(p, seen + (m,))
            if q: return q
    return None
def in_scope(m):
    c = str(rg.category.get(m, "")) if m in rg.index else ""
    if m in rg.index and (str(rg.row_role.get(m, "")) == "baseline" or str(rg.variant_kind.get(m, "")) == "retrained_method"):
        review.append({"kind": "scope", "id": m, "decision": "out (paper-internal baseline or reproduction)", "rule": "row_role=baseline or variant_kind=retrained_method"}); return False
    return c in CATS or m in EXTRA or m in new_scope
_ks = {}
for f in fams: _ks.setdefault("_".join([x for x in f.split("_") if not SIZE.match(x)] or f.split("_")[:1]), set()).add(f)
KSTEM = {k: next(iter(v)) for k, v in _ks.items() if len(v) == 1}
FAMPRE = {}
for v in M.values():
    if v.get("pretraining"): FAMPRE.setdefault(v["family"], []).append(v["pretraining"])
V4IDS = set(pd.read_csv(sys.argv[2], usecols=['model_id']).model_id) if len(sys.argv) > 2 else set()
add_m = 0
for m in sorted(used):
    if m in V4IDS: continue
    if m in M or not in_scope(m) or (m in rg.index and str(rg.row_role.get(m, "")) == "ablation"): continue
    grp = pretrain_group(rg.pretrain_input_modalities.get(m)) if m in rg.index else None
    grp = None if grp in ("natural", "SAR") and False else grp
    p = chain(m)
    if p: fam, rule = M[p]["family"], f"variant/supersedes chain -> {p}"
    else:
        tok = m.lower().split("_"); fam = None
        for f in fams:
            ft = f.split("_")
            if tok[:len(ft)] == ft and all(MOD.match(x) for x in tok[len(ft):]): fam, rule = f, f"known family prefix '{f}'"; break
            if "".join(tok).startswith(f.replace("_", "")) and f.replace("_", "") != "".join(tok[:1]) and all(MOD.match(x) for x in re.split(r"_", m.lower()[len(f.replace('_', '')) + m.lower()[:len(f) + 3].count('_'):].strip('_')) if x):
                fam, rule = f, f"known family name '{f}' (underscores ignored)"; break
        if fam is None:
            keep = [x for x in tok if not SIZE.match(x)] or tok[:1]; stem = "_".join(keep)
            if stem in KSTEM: fam, rule = KSTEM[stem], f"same stem as known family '{KSTEM[stem]}' (sizes merged)"
            else: fam, rule = stem, "new family (id without size tokens)"
    if grp in (None, "natural") and FAMPRE.get(fam):                       # imagery not stated: inherit the family's (sizes stay merged)
        grp, rule = max(set(FAMPRE[fam]), key=FAMPRE[fam].count), rule + "; pretraining inherited from family"
    pre = grp if grp in ("multispectral optical", "multi-sensor (SAR + optical)", "high-resolution RGB", "SAR") else None
    M[m] = {"family": fam, "size_tier": None, "sar_pretrained": (None if pre is None else int(pre in ("multi-sensor (SAR + optical)", "SAR"))), "pretraining": pre, "source": "v5_rule"}
    if pre: FAMPRE.setdefault(fam, []).append(pre)
    review.append({"kind": "family", "id": m, "decision": fam + (f" | {grp}" if grp else ""), "rule": rule}); add_m += 1
for m, v in M.items():
    if v.get("source") == "v5_rule" and not v.get("pretraining") and FAMPRE.get(v["family"]):
        v["pretraining"] = max(set(FAMPRE[v["family"]]), key=FAMPRE[v["family"]].count); v["sar_pretrained"] = int(v["pretraining"] in ("multi-sensor (SAR + optical)", "SAR"))
        for x in review:
            if x["kind"] == "family" and x["id"] == m: x["decision"] += f" | {v['pretraining']} (inherited)"
(D / "model_attributes.json").write_text(json.dumps(A, indent=1, ensure_ascii=False))

# ---------------------------------------------------------------- 4. canonical datasets
bm = pd.read_csv(D / "benchmark_map.csv", dtype=str).fillna("")
cf = breg.drop_duplicates("benchmark_id").set_index("benchmark_id")
bm["_corpus"] = bm.benchmark_id.map(cf.corpus_family).fillna("")
known = bm[bm._corpus != ""].groupby("_corpus").canonical_dataset.agg(lambda s: sorted(set(x for x in s if x)))
kdom = bm[bm._corpus != ""].groupby("_corpus").domain.agg(lambda s: s.mode().iat[0] if len(s.mode()) else "")
rows = []
for b in sorted(set(r.benchmark_id.dropna()) - set(bm.benchmark_id)):
    corp = str(cf.corpus_family.get(b, "") or "") if b in cf.index else ""
    codes = [c.strip() for c in str(cf.sensor.get(b, "") if b in cf.index else "").split(";") if c.strip() and c.strip() != "nan"]
    fset = {fam_of(c) for c in codes}
    kind = "eo_imagery" if fset & IMAGING else "coords_only" if fset == {"coords"} else "embedding" if "embedding" in fset else "other"
    if corp and len(known.get(corp, [])) == 1: canon, src, dom = known[corp][0], "v5_corpus_family (v4 canonical)", kdom.get(corp, "")
    elif corp: canon, src, dom = corp, "v5_corpus_family (new corpus)", ""
    else: canon, src, dom = "", "v5_unmapped", ""
    rows.append({"benchmark_id": b, "canonical_dataset": canon, "eoarena_id": "", "domain": dom, "subdomain": "", "input_kind": kind, "mapping_source": src})
    review.append({"kind": "dataset", "id": b, "decision": f"{canon} [{kind}]", "rule": src})
bm = pd.concat([bm.drop(columns="_corpus"), pd.DataFrame(rows)], ignore_index=True)
bm.to_csv(D / "benchmark_map.csv", index=False)
pd.DataFrame(review).to_csv(D / "v5_mapping_review.csv", index=False)
print(f"tables +{add_t}; EO-pretrained baselines +{len(new_scope)}; D7 variants +{piv_add}; model ids +{add_m}; benchmark ids +{len(rows)}")
print(pd.DataFrame(review).groupby(["kind", "rule"]).size().to_string())
