"""H1: labs that err do so on several models (paper-level error-proneness). H2: errors are model-specific (family-level implementation difficulty).
Uses leave-one-paper-out residuals t (points metrics, robust SD units) from diagnostics.py. Tests whether paper and family variance traits
estimated on half the datasets predict squared deviations on the other half (non-circular)."""
import os as _o
V5DIR = _o.environ.get('V5DIR', '/home/claude/v5out'); WB5 = _o.environ.get('WB5CSV', '/home/claude/wb5')

import sys, os, numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, '/home/claude/repo/scripts/robustness'); sys.path.insert(0, '/home/claude/repo/scripts')
os.environ.setdefault('EOARENA_WORKBOOK_DIR', '/home/claude/wb5x')
rng = np.random.default_rng(0); pd.set_option('display.width', 220)
L = pd.read_pickle(f'{V5DIR}/long_res_pts.pkl'); L = L[L.t.notna()].copy()
L['shifted'] = L.variant.isin({'no_overlap', 'superset', 'ood_test'})
C = L.groupby(['paper_key', 'family', 'canonical_dataset']).agg(r=('t', 'mean'), sr=('selfrep', 'max'), shifted=('shifted', 'max'), n=('t', 'size')).reset_index()
C['r2'] = C.r ** 2
T = C[~C.sr & ~C.shifted].copy()          # third-party, in-distribution: where implementation errors would live
print('third-party in-distribution paper x family x dataset cells:', len(T), '| papers', T.paper_key.nunique(), '| families', T.family.nunique())

# ---- descriptive: share of variance in log r2 due to paper and family (crossed random effects via moments) ----
def trait(df, key):
    g = df.groupby(key).r2.agg(['mean', 'size']); return g
P = trait(T, 'paper_key'); F = trait(T, 'family')
print('\nmean squared deviation by paper (third-party, >=10 cells):'); print(P[P['size'] >= 10].sort_values('mean', ascending=False).round(2).T.to_string())
print('\nmean squared deviation by family (third-party, >=10 cells):'); print(F[F['size'] >= 10].sort_values('mean', ascending=False).round(2).T.to_string())

# ---- split-half prediction test ----
def run(T, reps=200):
    ds = T.canonical_dataset.unique(); out = []
    for _ in range(reps):
        A = set(rng.choice(ds, len(ds) // 2, replace=False)); a, b = T[T.canonical_dataset.isin(A)], T[~T.canonical_dataset.isin(A)]
        g = a.r2.mean()
        pp = a.groupby('paper_key').r2.agg(['sum', 'size']); ff = a.groupby('family').r2.agg(['sum', 'size'])
        k = 3.0  # shrink traits towards the grand mean (pseudo-count 3 cells)
        ptr = (pp['sum'] + k * g) / (pp['size'] + k) / g; ftr = (ff['sum'] + k * g) / (ff['size'] + k) / g
        b = b.assign(pt=b.paper_key.map(ptr).fillna(1.0), ft=b.family.map(ftr).fillna(1.0))
        b['both'] = b.pt * b.ft
        res = {}
        for col in ['pt', 'ft', 'both']:
            res[col] = stats.spearmanr(b[col], b.r2).statistic
            # null: permute the trait across the cells' paper (or family) labels
        perm_p = b.paper_key.map(dict(zip(ptr.index, rng.permutation(ptr.values)))).fillna(1.0)
        perm_f = b.family.map(dict(zip(ftr.index, rng.permutation(ftr.values)))).fillna(1.0)
        res['null_pt'] = stats.spearmanr(perm_p, b.r2).statistic; res['null_ft'] = stats.spearmanr(perm_f, b.r2).statistic
        # top-decile capture: share of B's gross deviations (|r|>3) that fall in the top 20% predicted-risk cells
        thr = b.both.quantile(0.8); gross = b.r.abs() > 3
        res['capture_top20'] = (gross & (b.both >= thr)).sum() / max(gross.sum(), 1); res['n_gross'] = gross.sum()
        out.append(res)
    return pd.DataFrame(out)
R_ = run(T)
s = R_.describe(percentiles=[.05, .5, .95]).T[['mean', '5%', '50%', '95%']].round(3); print('\nsplit-half (200 random dataset halves), Spearman(predicted risk, squared deviation on held-out datasets):'); print(s.to_string())
print('P(paper trait beats its permutation null) %.2f | P(family trait beats null) %.2f' % ((R_.pt > R_.null_pt).mean(), (R_.ft > R_.null_ft).mean()))

# ---- H2 mechanism: does family implementation difficulty follow model architecture/input complexity (v5 registry)? ----
import robust_lib as R
reg = pd.read_csv(f'{WB5}/model_registry.csv', low_memory=False)
reg['family'] = reg.model_id.map(lambda m: R.unit_of(m) if hasattr(R, 'unit_of') else m)
cols = ['encoder_topology', 'input_modality_scope', 'temporal_fusion_stage', 'pretrain_input_modalities']
fam = reg.groupby('family')[cols].agg(lambda s: s.dropna().mode().iloc[0] if s.dropna().size else np.nan)
fam['n_pretrain_mod'] = fam.pretrain_input_modalities.map(lambda s: len(str(s).split(';')) if isinstance(s, str) else np.nan)
FF = F[F['size'] >= 8].join(fam, how='left')
print('\nfamily difficulty (third-party mean squared deviation) by registry attribute (families with >= 8 cells):')
for c in ['encoder_topology', 'input_modality_scope', 'temporal_fusion_stage']:
    print(' ', c, FF.groupby(c)['mean'].agg(['mean', 'size']).round(2).to_dict('index'))
ok = FF.n_pretrain_mod.notna(); print('  spearman(n pretraining input modalities, difficulty) = %.2f (p %.2f, %d families)' % (*stats.spearmanr(FF[ok].n_pretrain_mod, FF[ok]['mean']), ok.sum()))
# direction: are third-party deviations negative for hard families? (errors push scores down)
FD = T.groupby('family').r.agg(['mean', 'size']); FD = FD[FD['size'] >= 8].join(F['mean'].rename('msd'))
print('  spearman(family difficulty, mean signed third-party deviation) = %.2f (p %.2f)' % stats.spearmanr(FD.msd, FD['mean']))
R_.to_pickle(f'{V5DIR}/lab_hypotheses_split.pkl'); FF.to_pickle(f'{V5DIR}/family_difficulty.pkl'); P.to_pickle(f'{V5DIR}/paper_proneness.pkl')
