"""Held-out test of three ways to incorporate paper- and model-wide lab errors in the note's latent-factor model (Eq. 9):
  base      the pipeline as frozen (no lab term);
  weighted  precision weights from the heteroscedastic lab-effects model: w_i = (e + lab) / (e + lab * m_pf), m_pf = exp(a_p + b_f)
            (lab_effects.py; z-scale REML components) -- the inverse-variance weighting of a location-scale model;
  offset    a ridge-shrunk paper x family offset c_{m,p} shared by all tasks a paper reports for a family (fit_structured's
            existing `paper` option: the 'implementation effect' term);
  both      weights and offsets.
Evaluation is the pipeline's own: 5-fold held-out cells, within-task pairwise ranking accuracy, fold seeds 0-2, on ALL held-out
cells (unweighted), so weighting cannot game the metric. Usage: python3 -I heldout_lab.py <long.pkl> <w_lab.pkl> <vc.json> <out.json>
"""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'robustness')); sys.path.insert(0, os.path.join(HERE, '..'))
import robust_lib as R, ablation_lib as A, dataset_benchmarking as db
ARGS = list(sys.argv)                                   # prefix.build rewrites sys.argv
L = pd.read_pickle(ARGS[1]); w = pd.read_pickle(ARGS[2]); vc = json.load(open(ARGS[3]))['z']
D = R.load(); mi = {m: i for i, m in enumerate(D['models'])}
mult = np.ones(D['mask'].shape)
Lw = L.loc[w.index].assign(m=w.values)
for f, j, m in zip(Lw.family, Lw.j, Lw.m): mult[mi[f], j] = m
lab, e = vc['lab'], vc['e']; W = (e + lab) / (e + lab * mult)
pidx = pd.factorize(np.asarray(D['tp']))[0]
def cv(K, seeds=(0, 1, 2), **extra):
    rs = [db.heldout_cell_cv(D['Y'], D['mask'], K, D['G'], folds=5, seed=s, ridge_u=R.RID, ridge_theta=R.RID, ridge_g={k: R.RID for k in D['G']},
                             n_restarts=2, n_iter=200, tol=1e-6, prior_group=D['FAM'], **extra) for s in seeds]
    return {'acc': float(np.mean([r['pair_acc'] for r in rs])), 'by_seed': [float(r['pair_acc']) for r in rs], 'se': float(np.mean([r['pair_acc_se'] for r in rs]) / np.sqrt(len(seeds)))}
out = {'weights': {'min': float(W[D['mask']].min()), 'p10': float(np.percentile(W[D['mask']], 10)), 'median': float(np.median(W[D['mask']])), 'max': float(W[D['mask']].max())}}
out['base'] = A.held_out(D, seeds=(0, 1, 2)); print('base', out['base'], flush=True)
for K in (1, 2):
    out[f'weighted_K{K}'] = cv(K, cell_weight=W); print(f'weighted K{K}', out[f'weighted_K{K}'], flush=True)
out['offset_K2'] = cv(2, paper=pidx); print('offset K2', out['offset_K2'], flush=True)
out['both_K2'] = cv(2, paper=pidx, cell_weight=W); print('both K2', out['both_K2'], flush=True)
json.dump(out, open(ARGS[4], 'w'), indent=1)
