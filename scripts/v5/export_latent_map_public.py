"""Public, anonymised data file for latent-map.html (Stage 1 latent factor model, K = 2 sensitivity fit).

Reads the internal explorer export (tasks, GeoFM families, resampling clouds) and keeps only task-level fields:
dataset, protocol, label fraction, metric, input type, task type, domain, number of GeoFMs, the task's weights on
capability 1 and 2, and its positions in the GeoFM-resampling refits. GeoFM families appear only as medians and
interquartile intervals per pretraining-imagery group (groups with at least MIN_GROUP families); no family name,
identifier or individual position is written. No score is read or written.

Anonymisation:
- per-task source keys (which encode the paper or benchmark a variant came from) are replaced by "variant k" within
  dataset x protocol x label fraction x metric;
- dataset names containing a GeoFM family name, or the leading token of a family identifier, have that name withheld;
- tasks are re-indexed in alphabetical order so the index carries no information about the internal table.
The script asserts that no model field, and no family name (whole word, case-insensitive), remains in the output.

Usage: python3 scripts/v5/export_latent_map_public.py [--src explorer/data.json] [--families core/families.csv] [--out data/latent_map_public.json]
"""
import argparse, collections, csv, json, re, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser()
ap.add_argument('--src', default='/home/claude/v5out/stage1/explorer/data.json')
ap.add_argument('--families', default='/home/claude/v5out/stage1/core/families.csv')
ap.add_argument('--out', default=str(ROOT / 'data' / 'latent_map_public.json'))
a = ap.parse_args()

MIN_GROUP = 10  # minimum families for a pretraining-imagery group to be summarised
D = json.load(open(a.src))
fam_ids = [r['family'] for r in csv.DictReader(open(a.families))]

# Names to withhold: family identifiers, their part before '|', and the leading token of multi-part identifiers
# (e.g. a method name followed by an architecture suffix). Leading tokens that are generic architecture words, or that
# are the names of pretraining datasets (kept, since dataset names are public), are not treated as model names.
GENERIC = {'resnet50', 'swint', 'factorized'}
DATASET_TOKENS = {'ssl4eo', 'spectralearth'}
names = set()
for f in fam_ids:
    base = f.split('|')[0]
    names.update({f.lower(), base.lower()})
    tok = base.split('_')[0].lower()
    if len(tok) >= 5 and tok not in GENERIC and tok not in DATASET_TOKENS:
        names.add(tok)
whole = [re.compile(r'(?<![A-Za-z0-9])' + re.escape(n) + r'(?![A-Za-z0-9])', re.I) for n in sorted(names, key=len, reverse=True)]
inner = [re.compile(re.escape(n), re.I) for n in sorted(names, key=len, reverse=True) if len(n) >= 5]  # names fused into a dataset id


def has_name(s):
    return any(p.search(s) for p in whole) or any(p.search(s) for p in inner)


def withhold(ds):
    """Dataset label with any model name removed; the descriptive remainder is kept."""
    s = ds
    for p in inner + whole:
        s = p.sub(' ', s)
    s = re.sub(r'(?i)(^|[\s_-])bench(?=[\s_-]|$)', ' ', s)          # '<name>-Bench x' -> 'x'
    s = re.sub(r'[_\s-]+', ' ', s).replace('( )', '').replace('()', '').strip(' -_,')
    s = s[:1].upper() + s[1:] if s else 'Dataset'
    return s + ' (name withheld)'


TYPE_FIELDS = ['proto', 'frac', 'metric', 'itype', 'ttype', 'dom']
ds_map = {}
for ds in sorted({t['ds'] for t in D['tasks']}):
    ds_map[ds] = withhold(ds) if has_name(ds) else ds
# keep withheld labels distinct
cnt = collections.Counter(ds_map.values())
seen = collections.Counter()
for ds in sorted(ds_map):
    v = ds_map[ds]
    if cnt[v] > 1:
        seen[v] += 1
        ds_map[ds] = v.replace(' (name withheld)', f' {chr(64 + seen[v])} (name withheld)')

# variant number within dataset x protocol x fraction x metric, ordered by the internal key (key itself not written)
by_cell = collections.defaultdict(list)
for t in D['tasks']:
    by_cell[(t['ds'], t['proto'], t['frac'], t['metric'])].append(t)
var = {}
for cell, ts in by_cell.items():
    subs = sorted({t['sub'] for t in ts})
    for t in ts:
        var[id(t)] = f'variant {subs.index(t["sub"]) + 1}' if len(subs) > 1 else ''

rows = []
for t in D['tasks']:
    rows.append({'ds': ds_map[t['ds']], **{k: t[k] for k in TYPE_FIELDS}, 'var': var[id(t)], 'n': t['n'],
                 'x': t['x'], 'y': t['y'], 'b': t['b'], 'c1': t['c1'], 'r1': t['r1']})
rows.sort(key=lambda r: (r['ds'].lower(), r['proto'], r['frac'], r['metric'], r['var'], r['itype']))
for i, r in enumerate(rows):
    r['i'] = i

# GeoFM families: aggregate only, by pretraining imagery (from data/model_attributes.json via the internal export)
g = collections.defaultdict(list)
for m in D['models']:
    g[m['img']].append(m['y'])


def q(v, p):
    v = sorted(v); k = (len(v) - 1) * p; lo = int(k); hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


groups = [{'group': k, 'n': len(v), 'median': round(statistics.median(v), 3), 'q25': round(q(v, .25), 3), 'q75': round(q(v, .75), 3)}
          for k, v in sorted(g.items(), key=lambda kv: -len(kv[1])) if len(v) >= MIN_GROUP]
omitted = sorted(k for k, v in g.items() if len(v) < MIN_GROUP)

out = {
    'about': 'EOArena Stage 1 latent map (provisional). Task weights on capabilities 1 and 2 from the K = 2 sensitivity fit '
             'of the latent factor model (hierarchical loadings, ridge 10); K_final = 1 is the primary result. b: task '
             'positions in refits with GeoFM families resampled, aligned to the full fit. No scores, no model names.',
    'n_boot': D['n_boot'],
    'boot_min_geofms': 9,
    'family_groups': {'min_families': MIN_GROUP, 'axis': 'capability 2', 'groups': groups, 'omitted': omitted},
    'tasks': rows,
}

# ---- confidentiality checks -------------------------------------------------------------------------------------
ALLOWED_TASK = {'i', 'ds', 'proto', 'frac', 'metric', 'var', 'itype', 'ttype', 'dom', 'n', 'x', 'y', 'b', 'c1', 'r1'}
assert set(out) == {'about', 'n_boot', 'boot_min_geofms', 'family_groups', 'tasks'}
assert all(set(r) == ALLOWED_TASK for r in rows), 'unexpected task field'
assert all(set(gr) == {'group', 'n', 'median', 'q25', 'q75'} and gr['n'] >= MIN_GROUP for gr in groups)
strings = []
def walk(o):
    if isinstance(o, dict):
        for k, v in o.items(): strings.append(str(k)); walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
    elif isinstance(o, str):
        strings.append(o)
walk(out)
leaks = sorted({s for s in strings if has_name(s)})
assert not leaks, f'model names remain: {leaks}'
assert not any(k in ('models', 'name', 'sub', 'obj', 'img') for k in strings), 'model field remains'

json.dump(out, open(a.out, 'w'), separators=(',', ':'), ensure_ascii=False)
withheld = sorted(v for k, v in ds_map.items() if k != v)
print(f'{len(rows)} tasks, {sum(1 for r in rows if r["b"])} with resampling clouds, {len(groups)} family groups '
      f'(omitted: {omitted}); {len(withheld)} dataset names withheld -> {a.out}')
