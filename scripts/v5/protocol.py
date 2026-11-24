"""Shared protocol / metric / task-key definitions for the v5 analyses (one place, so every script agrees).

The note (Wang, Oct 2026, p. 4) defines a task as a dataset-protocol combination, the protocol including the adaptation setting,
label fraction, input bands and resolution, decoder, train-test split and evaluation metric. Within one paper the analysed matrix
already keys settings that finely (paper|table|benchmark|protocol|fraction|variant|metric). Across papers we can only match on what
is coded: `xtask` = canonical dataset x input sensor x adaptation protocol x label fraction x metric x variant. Decoder and split are
not coded, so cross-paper differences inside an xtask may still contain protocol structure (stated as a limitation, not noise-free).
"""
import re

# metrics on a bounded 0-100 points scale. R^2 is NOT here: build_dataset_analysis maps regression metrics (r2 included) to
# the log-error scale (-100 ln err), so it is not points.
PTS = {'miou', 'acc', 'f1', 'acc_top1', 'iou', 'map', 'micro_f1', 'oa', 'segm_map', 'mijacc', 'bal_acc', 'weighted_f1', 'acc_avg', 'macro_f1'}

# exact synonyms only (top-1 accuracy = overall accuracy for single-label classification); F1 variants, IoU vs mIoU are NOT merged
METRIC_SYN = {'oa': 'acc', 'acc_top1': 'acc', 'acc': 'acc'}
def metric_norm(m): return METRIC_SYN.get(str(m), str(m))

# adaptation protocol: encoder fine-tuned (incl. partial and parameter-efficient: LoRA / SVF adapt the encoder), frozen encoder with a
# trained decoder, frozen encoder with a probe, prompt/embedding (PE), and non-standard evaluations that are different tasks rather
# than probes (few-shot episodes, retrieval, zero-shot, clustering).
PROTO_SYN = {'FT': 'FT', 'PFT': 'PFT', 'lora_dec': 'PEFT', 'svf_dec': 'PEFT', 'frozen_dec': 'frozen_dec', 'LP': 'LP', 'MLP': 'MLP', 'kNN': 'kNN',
             'RF': 'RF', 'frozen_xgboost': 'XGB', 'frozen_ebm': 'EBM', 'frozen': 'frozen_probe', 'frozen_best': 'frozen_probe', 'PE': 'PE',
             'few_shot_episodic': 'few_shot', 'frozen_retrieval': 'retrieval', 'zero_shot': 'zero_shot', 'kmeans_clustering': 'kmeans'}
def proto_norm(p): return PROTO_SYN.get(str(p), str(p))

def pclass(p):
    """Coarse protocol class used by the variance-components F x C term. 'other' (clustering) is excluded from the noise analyses;
    'nonstd' keeps few-shot / retrieval / zero-shot as their own class instead of lumping them with probes."""
    q = proto_norm(p)
    if q in ('FT', 'PFT', 'PEFT'): return 'ft'
    if q == 'frozen_dec': return 'dec'
    if q == 'PE': return 'pe'
    if q == 'kmeans': return 'other'
    if q in ('few_shot', 'retrieval', 'zero_shot'): return 'nonstd'
    return 'probe'

_pct = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*%\s*$')
def frac_norm(f):
    """'10.0%' -> '10%'; other labels unchanged."""
    s = str(f); m = _pct.match(s)
    if not m: return s
    x = float(m.group(1)); return (f'{x:g}') + '%'

def sensor_norm(s):
    s = str(s).strip().lower()
    return ';'.join(sorted(t.strip() for t in re.split(r'[;,+]', s) if t.strip())) if s not in ('', 'nan') else ''

def xtask(row):
    return '|'.join([str(row['canonical_dataset']), sensor_norm(row['sensor']), proto_norm(row['evaluation_protocol']),
                     frac_norm(row['train_fraction_norm']), metric_norm(row['metric_s']), str(row['variant'] or '')])
