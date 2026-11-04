#!/usr/bin/env python3
"""Build data/table_locations.json: where each extracted results table sits in its paper (main text / appendix) and
whether it is an ablation study, so build_dataset_analysis.py can keep main-text benchmark comparisons only.

Inputs: a table inventory (one record per paper x LaTeX file x table label) and per-batch classifications made by
checking each table against the arXiv version of the paper (caption, numbering, section). Files whose name marks them
as appendix / supplementary / ablation sources are classified by rule without a check.

Usage: python3 scripts/make_table_locations.py <inventory.json> <loc_*.json ...>
"""
import json, re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
inv = pd.read_json(sys.argv[1])
checked = pd.concat([pd.read_json(f) for f in sys.argv[2:]], ignore_index=True).drop_duplicates(["paper", "file", "table_id"], keep="last")
checked["table_id"] = checked.table_id.astype(str)
APP = re.compile(r"append|suppl|supp|supporting|ablation|X_suppl|final_sup", re.I)

recs = []
ck = checked.set_index(["paper", "file", "table_id"])
for _, x in inv.iterrows():
    key = (x.paper, x.file, str(x.table_id))
    if x.file.startswith("results/"):
        loc, abl, how, ev = "main", False, "rule", "public leaderboard snapshot (no paper body/appendix split)"
    elif key in ck.index:                                  # a check against the arXiv version overrides the file-name rule
        c = ck.loc[key]
        c = c.iloc[0] if isinstance(c, pd.DataFrame) else c
        loc, abl, how, ev = c.location, (None if pd.isna(c.ablation) else bool(c.ablation)), "checked against arXiv", f"{c.paper_table_number or ''} — {c.section or ''}: {c.evidence or ''}"
    elif APP.search(x.file):
        loc, abl, how, ev = "appendix", bool(re.search("ablation", x.file, re.I)), "rule (not checked)", f"source file name '{x.file}'"
    else:
        loc, abl, how, ev = "unclear", None, "not checked", ""
    recs.append({"paper": x.paper, "file": x.file, "table_id": str(x.table_id), "n_rows": int(x.n_rows), "location": loc,
                 "ablation": bool(abl) if abl is not None else None, "how": how, "evidence": ev})

out = {
    "about": "Placement (main text / appendix) and ablation status of every extracted results table. build_dataset_analysis.py keeps tables with ablation == false in the main text and, unless --main-text-only, in the appendix; location == unclear is dropped.",
    # rows of one table group that sit in a supplementary section of a single-file paper (checked by line number)
    "line_overrides": [{"paper": "alphaearth", "file": "main.tex", "appendix_from_line": 956,
                        "evidence": "Supplementary heading at main.tex:956 (bibliography at 176); rows at line 1129 are an S16.2.4 weight sweep"}],
    # variant axes that change the model, pretraining or training recipe (ablations); the paper's headline setting is kept
    "ablation_axes": ["reproduction", "pretrain_band_subset", "pretrain_data_fraction", "patch_embedding_training", "masking_strategy",
                      "model_size", "channel_grouping", "init", "finetune_augmentation", "temporal_input_handling", "spectral_crop_size",
                      "pretrain_scales", "embedding_prefix_dim", "inference_window", "finetune_epochs", "decoder_config", "fusion_strategy",
                      "probe_strategy", "downstream_module", "source_table",
                      # recipe sweeps of a fixed encoder (training loss, fusion scenario): ablation-type, no headline setting known
                      "loss_function", "change_direction_subset_x_training_loss", "scenario"],
    "headline_variants": {"embedding_prefix_dim": "128", "probe_strategy": "standard_ridge", "source_table": "main_table"},
    "tables": recs,
}
(ROOT / "data" / "table_locations.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
df = pd.DataFrame(recs)
print(df.groupby(["location", "ablation"]).n_rows.agg(["count", "sum"]))
