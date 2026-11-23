"""Summarise ablation_run.py output: range of each statistic per ablation group and the most influential removal.

    python ablation_summary.py        ->  prints a table, writes <EOARENA_OUT>/ablation_summary.json
"""
import os, json, collections, numpy as np
import ablation_lib as A
RS = [r for r in A.read_jobs('ablation') if not r.get('error')]
for r in RS:
    r['ratio'] = r['strength_frozen'] / r['strength_finetuned'] if r.get('strength_finetuned') else np.nan
    r['pop_minus_rand'] = (r['cov_mostused5'] - r['cov_random5']) if r.get('cov_mostused5') is not None and r.get('cov_random5') is not None else np.nan
    for k in ('sensor|rest', 'domain|rest', 'task_type|rest'):
        if isinstance(r.get(k), dict): r[k + '_p'] = r[k]['p']
    if 'acc_K2' in r: r['k2_lb'] = r['acc_K2'] - r['acc_LB']; r['k1_lb'] = r['acc_K1'] - r['acc_LB']
base = [r for r in RS if r['name'] == 'base'][0]
G = {'leave one dataset out': [r for r in RS if r['group'] == 'leave_one_dataset_out'], 'leave one family out': [r for r in RS if r['group'] == 'leave_one_family_out']}
for kind in ('datasets', 'families'):
    for fr in (0.75, 0.5): G[f'{int(fr*100)}% {kind}'] = [r for r in RS if r['group'] == 'sub_' + kind and r['frac'] == fr]
out = {}
for s in ('pretrain_match_pts', 'ratio', 'pop_minus_rand', 'cov_chosen5', 'sensor|rest_p', 'domain|rest_p', 'task_type|rest_p', 'axis2_share', 'map_r', 'acc_LB', 'acc_K1', 'acc_K2', 'k1_lb', 'k2_lb'):
    print('\n==', s, 'base', None if base.get(s) is None else round(base[s], 3)); out[s] = {'base': base.get(s)}
    for n, g in G.items():
        v = np.array([r.get(s, np.nan) if r.get(s) is not None else np.nan for r in g], float); ok = ~np.isnan(v)
        if not ok.any(): continue
        i = int(np.nanargmax(np.abs(v - (base.get(s) or 0))))
        print('  %-22s n=%3d min %.3f med %.3f max %.3f | share >0: %.2f | most influential %s -> %.3f' % (n, ok.sum(), np.nanmin(v), np.nanmedian(v), np.nanmax(v), np.mean(v[ok] > 0), g[i]['name'], v[i]))
        out[s][n] = dict(n=int(ok.sum()), min=float(np.nanmin(v)), med=float(np.nanmedian(v)), max=float(np.nanmax(v)), share_positive=float(np.mean(v[ok] > 0)), most_influential=g[i]['name'], value=float(v[i]))
loo = [r for r in RS if r['group'].startswith('leave_one')]; ch = collections.Counter(x for r in loo for x in r.get('chosen5', []))
print('\ngreedy five, frequency over', len(loo), 'single removals:', ch.most_common(10)); out['chosen5_frequency'] = dict(ch.most_common(10)); out['n_single_removals'] = len(loo)
json.dump(out, open(os.path.join(A.OUTD, 'ablation_summary.json'), 'w'), indent=1)
