"""Outlier and influence diagnostics for published GeoFM scores (leave-one-paper-out consensus residuals).
Input: out/long.pkl from build_long.py. Writes aggregate outputs to out/."""
import os as _o
V5DIR = _o.environ.get('V5DIR', '/home/claude/v5out'); WB5 = _o.environ.get('WB5CSV', '/home/claude/wb5')

import numpy as np, pandas as pd, json, collections
from scipy import stats
rng = np.random.default_rng(0)
L = pd.read_pickle(f'{V5DIR}/long_v5.pkl')
L = L[L.evaluation_protocol != 'kmeans_clustering'].copy()
import sys
SCALE = sys.argv[1] if len(sys.argv) > 1 else 'pts'
TAG = SCALE + ('' if len(sys.argv) <= 2 else '_' + sys.argv[2])
PTS = {'miou','acc','f1','acc_top1','r2','iou','map','micro_f1','oa','segm_map','mijacc'}
L['pts'] = L.metric_s.isin(PTS)
if SCALE == 'pts':
    L = L[L.pts].copy(); L['v'] = L.y
else:
    L['v'] = L.z
L = L.reset_index(drop=True)
sys.path.insert(0,'/home/claude/repo/scripts/robustness'); import os; os.environ.setdefault('EOARENA_WORKBOOK_DIR','/home/claude/wb5x')
import robust_lib as R
# itype comes with the v5 long table
SENS = len(sys.argv) <= 2 or sys.argv[2] != 'nosensor'
L['pclass'] = L.evaluation_protocol.map(lambda p: 'ft' if p in ('FT','PFT') else 'dec' if p=='frozen_dec' else 'pe' if p=='PE' else 'probe')
LAM = 10.0 if (len(__import__("sys").argv) <= 1 or __import__("sys").argv[1] == "pts") else 3.0   # ~ (FP+FDP+e)/FD: 43/4.5 on points, 0.66/0.21 in z

def fit_additive(df):
    """z ~ setting + family + family x dataset (ridge LAM), by backfitting. Returns family effect and fxd effect dicts."""
    a = collections.defaultdict(float); b = collections.defaultdict(float); e = collections.defaultdict(float); c = pd.Series(0.0, index=df.task.unique())
    f, d, t, z, it = df.family.values, df.canonical_dataset.values, df.task.values, df.v.values, df.itype.values
    B = lambda: np.array([b[(x, y)] for x, y in zip(f, d)]); E = lambda: np.array([e[(x, y)] for x, y in zip(f, it)])
    for _ in range(30):
        r = z - c.reindex(t).values - B() - E()
        a = pd.Series(r).groupby(f).mean().to_dict(); A = np.array([a[x] for x in f])
        if SENS:
            r = z - c.reindex(t).values - A - B()
            g = pd.DataFrame({'k': list(zip(f, it)), 'r': r}).groupby('k').r.agg(['sum', 'count'])
            e = collections.defaultdict(float, (g['sum'] / (g['count'] + LAM)).to_dict())
        r = z - c.reindex(t).values - A - E()
        g = pd.DataFrame({'k': list(zip(f, d)), 'r': r}).groupby('k').r.agg(['sum', 'count'])
        b = collections.defaultdict(float, (g['sum'] / (g['count'] + LAM)).to_dict())
        r = z - A - B() - E()
        c = pd.Series(r).groupby(t).mean()
    return a, b, e

# ---- 1. leave-one-paper-out consensus prediction for every score ----
pred = np.full(len(L), np.nan); ndirect = np.zeros(len(L), int)
cellpapers = L.groupby(['family', 'canonical_dataset']).paper_key.agg(set).to_dict()
for p in L.paper_key.unique():
    tr = L[L.paper_key != p]; a, b, e = fit_additive(tr)
    ix = np.where(L.paper_key.values == p)[0]
    for i in ix:
        fam, ds = L.family.values[i], L.canonical_dataset.values[i]
        if fam in a:
            pred[i] = a[fam] + b.get((fam, ds), 0.0) + e.get((fam, L.itype.values[i]), 0.0); ndirect[i] = len(cellpapers[(fam, ds)] - {p})
L['pred'] = pred; L['n_direct'] = ndirect
ok = L.pred.notna()
# residual re-centred within setting (setting-level shifts do not matter for comparisons between families)
L.loc[ok, 'res'] = L[ok].v - L[ok].pred
L.loc[ok, 'res'] = L[ok].res - L[ok].groupby('task').res.transform('mean')
# drop settings with < 3 predicted families (residual is degenerate)
npred = L[ok].groupby('task').size(); L.loc[L.task.map(npred).fillna(0) < 3, 'res'] = np.nan
ok = L.res.notna()
print('R2 of consensus prediction for setting-centred values:', round(1 - L[ok].res.var() / (L[ok].v - L[ok].groupby('task').v.transform('mean')).var(), 3))
s_rob = 1.4826 * np.median(np.abs(L[ok].res - L[ok].res.median()))
sd_d = L[ok].groupby('canonical_dataset').res.agg(lambda r: 1.4826 * np.median(np.abs(r)) if len(r) >= 15 else np.nan)
L['s_d'] = L.canonical_dataset.map(sd_d).fillna(s_rob); L['t'] = L.res / L.s_d
print('excess kurtosis of t', round(float(stats.kurtosis(L[ok].t)), 2), '| share |t|>3:', round(float((L[ok].t.abs()>3).mean()), 4), 'normal expects 0.0027')
print(f'scores with a leave-paper-out prediction: {ok.sum()} / {len(L)}; robust residual SD {s_rob:.3f} (z units); plain SD {L[ok].res.std():.3f}')


# ---- 2. two-component scale mixture (Beath-style): core N(0,s1) + outlier N(0,s2) ----
x = L[ok].t.values; w, s1, s2 = 0.1, 1.0, 3.0
for _ in range(500):
    p1 = (1 - w) * stats.norm.pdf(x, 0, s1); p2 = w * stats.norm.pdf(x, 0, s2); q = p2 / (p1 + p2)
    w = q.mean(); s1 = np.sqrt(((1 - q) * x**2).sum() / (1 - q).sum()); s2 = np.sqrt((q * x**2).sum() / q.sum())
L.loc[ok, 'p_out'] = q
print(f'mixture: outlier share {w:.3f}, core SD {s1:.3f}, outlier SD {s2:.3f}; scores with p_out>0.5: {(q>0.5).sum()}')
# likelihood-ratio vs single normal, with parametric bootstrap
def ll1(x): return stats.norm.logpdf(x, 0, np.sqrt((x**2).mean())).sum()
def llmix(x):
    w, a, b = 0.1, x.std() * .7, x.std() * 2
    for _ in range(300):
        p1 = (1 - w) * stats.norm.pdf(x, 0, a); p2 = w * stats.norm.pdf(x, 0, b); q = p2 / (p1 + p2)
        w = q.mean(); a = np.sqrt(((1 - q) * x**2).sum() / (1 - q).sum()); b = np.sqrt((q * x**2).sum() / q.sum())
    return np.log((1 - w) * stats.norm.pdf(x, 0, a) + w * stats.norm.pdf(x, 0, b)).sum()
LR = 2 * (llmix(x) - ll1(x)); nul = [2 * (llmix(y) - ll1(y)) for y in [rng.normal(0, x.std(), len(x)) for _ in range(100)]]
print(f'LR test mixture vs normal: LR={LR:.1f}, bootstrap 99th pct of null {np.percentile(nul,99):.1f}')

# ---- 3. paper x family bias: mean residual over the paper's datasets (dataset-clustered) ----
pf = L[ok].groupby(['paper_key', 'family', 'canonical_dataset']).agg(r=('t', 'mean'), n=('res', 'size'), sr=('selfrep', 'max'), nd=('n_direct', 'max')).reset_index()
rows = []
for (p, f), g in pf.groupby(['paper_key', 'family']):
    k = len(g); m = g.r.mean()
    se = g.r.std(ddof=1) / np.sqrt(k) if k >= 3 else np.nan
    # reference SE from the global per-dataset residual SD when within-pair spread is unavailable or tiny
    se_ref = pf.r.std() / np.sqrt(k)
    rows.append(dict(paper=p, family=f, n_datasets=k, n_scores=int(g.n.sum()), bias=m, se=se, t=m / max(se if se == se else 0, se_ref),
                     self=bool(g.sr.max()), direct_datasets=int((g.nd > 0).sum())))
PF = pd.DataFrame(rows)
# permutation null for |t| over paper x family pairs: shuffle family labels within each (paper, dataset) table block
def perm_max():
    q = pf.copy(); q['family'] = q.groupby(['paper_key', 'canonical_dataset']).family.transform(lambda s: rng.permutation(s.values))
    gg = q.groupby(['paper_key', 'family']).r.agg(['mean', 'count'])
    return (gg['mean'].abs() / (pf.r.std() / np.sqrt(gg['count']))).max()
nullmax = [perm_max() for _ in range(200)]
thr = np.percentile(nullmax, 95)
PF['flag'] = (PF.t.abs() > thr) & (PF.n_datasets >= 2)
print(f'paper x family pairs: {len(PF)}; family-wise 5% threshold |t|>{thr:.2f} (max-statistic permutation); flagged {PF.flag.sum()}')
print('self-reported vs third-party mean bias:', PF.groupby('self').bias.agg(['mean', 'count']).round(3).to_dict())

# ---- 4. paper-level: concordance with consensus and noise ----
pp = []
for p, g in L[ok].groupby('paper_key'):
    rhos = [stats.spearmanr(h.z, h.pred).statistic for _, h in g.groupby('task') if len(h) >= 4 and h.pred.std() > 0]
    rhos = [r for r in rhos if r == r]
    pp.append(dict(paper=p, scores=len(g), settings=g.task.nunique(), datasets=g.canonical_dataset.nunique(),
                   rho_med=np.median(rhos) if rhos else np.nan, n_rho=len(rhos), res_sd=1.4826 * np.median(np.abs(g.res)),
                   share_t3=(g.t.abs() > 3).mean(), exp_outliers=g.p_out.sum(), share_out=g.p_out.mean(),
                   direct_share=(g.n_direct > 0).mean()))
PP = pd.DataFrame(pp).sort_values('share_out', ascending=False)

# ---- 5. non-circular validation: flag on half the datasets, test on the other half ----
def between_paper_var(df):
    """moment estimate: setting-centred z, averaged per family x dataset x paper; mean between-paper variance in cells with >= 2 papers"""
    d = df.copy(); d['zc'] = d.z - d.groupby('task').z.transform('mean')
    c = d.groupby(['family', 'canonical_dataset', 'paper_key']).zc.mean().reset_index()
    v = c.groupby(['family', 'canonical_dataset']).zc.agg(['var', 'count']); v = v[v['count'] >= 2]
    return v['var'].mean(), len(v)
def cross_rho(df):
    """median Spearman between two papers' family means on the same dataset (>= 4 shared families)"""
    d = df.copy(); d['zc'] = d.z - d.groupby('task').z.transform('mean')
    c = d.groupby(['canonical_dataset', 'paper_key', 'family']).zc.mean()
    out = []
    for ds, g in c.groupby(level=0):
        ps = g.index.get_level_values(1).unique()
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                a, b = g.xs(ps[i], level=1).droplevel(0), g.xs(ps[j], level=1).droplevel(0); sh = a.index.intersection(b.index)
                if len(sh) >= 4: out.append(stats.spearmanr(a[sh], b[sh]).statistic)
    return np.median(out) if out else np.nan, len(out)
dsets = L.canonical_dataset.unique(); val = []
for rep in range(20):
    A = set(rng.choice(dsets, len(dsets) // 2, replace=False))
    LA = L[L.canonical_dataset.isin(A) & L.t.notna()]; LB = L[~L.canonical_dataset.isin(A)]
    g = LA.groupby(['paper_key', 'family', 'canonical_dataset']).t.mean().reset_index()
    bb = g.groupby(['paper_key', 'family']).t.agg(['mean', 'count']); bb['tt'] = bb['mean'] / (g.t.std() / np.sqrt(bb['count']))
    fl = set(bb[(bb.tt.abs() > 2.5) & (bb['count'] >= 2)].index)
    keyB = list(zip(LB.paper_key, LB.family)); inB = {k for k in keyB}
    flB = fl & inB
    if not flB: continue
    base_v, _ = between_paper_var(LB); base_r, _ = cross_rho(LB)
    drop = LB[[k not in flB for k in keyB]]; dv, nc = between_paper_var(drop); dr, npairs = cross_rho(drop)
    # random control: drop the same number of random (paper, family) pairs among those that appear in B
    rv, rr = [], []
    pool = sorted(inB)
    for _ in range(8):
        rs = set(map(tuple, np.array(pool, dtype=object)[rng.choice(len(pool), len(flB), replace=False)]))
        dd = LB[[k not in rs for k in keyB]]; rv.append(between_paper_var(dd)[0]); rr.append(cross_rho(dd)[0])
    val.append(dict(rep=rep, n_flag=len(flB), base_var=base_v, flag_var=dv, rand_var=np.mean(rv), base_rho=base_r, flag_rho=dr, rand_rho=np.nanmean(rr), pairs=npairs))
V = pd.DataFrame(val)
print('validation reps', len(V)); print(V.describe().round(3).T[['mean', '25%', '50%', '75%']])
print('share of reps where flagged removal beats random on variance:', (V.flag_var < V.rand_var).mean().round(2), ' on rho:', (V.flag_rho > V.rand_rho).mean().round(2))

L.to_pickle(f'{V5DIR}/long_res_{TAG}.pkl'); PF.to_pickle(f'{V5DIR}/paper_family_{TAG}.pkl'); PP.to_pickle(f'{V5DIR}/paper_{TAG}.pkl'); V.to_pickle(f'{V5DIR}/validation_{TAG}.pkl')
json.dump(dict(s_rob=s_rob, mix=dict(w=w, s1=s1, s2=s2), LR=LR, thr=thr), open(f'{V5DIR}/summary_{TAG}.json', 'w'), indent=1, default=float)
