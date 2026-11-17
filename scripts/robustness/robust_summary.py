import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import json, numpy as np, pandas as pd, collections
R=[json.loads(l) for l in open(OUTD+'/results.jsonl')]; err=[r['name'] for r in R if r.get('error')]; print(len(R),'errors',err)
R=[r for r in R if not r.get('error')]; base=next(r for r in R if r['name']=='base')
def flat(r):
    o={k:v for k,v in r.items() if isinstance(v,(int,float)) and not isinstance(v,bool)}
    for k in ('sensor','task_type','domain','sensor|rest','task_type|rest','domain|rest'):
        if isinstance(r.get(k),dict): o[k+'_excess']=r[k]['excess']; o[k+'_p']=r[k]['p']
    return o
df=pd.DataFrame([{**flat(r),'name':r['name'],'group':r['group'],'paper':r.get('paper')} for r in R]); b=df[df.name=='base'].iloc[0]
cols=['acc_K1','acc_K2','gain_K2','gain_K3','axis2_share','imagery_contrast_sd','pretrain_match_pts','sensor_excess','sensor_p','task_type_excess','task_type_p','domain_excess','domain_p','sensor|rest_p','task_type|rest_p','domain|rest_p','strength_frozen','strength_finetuned','frozen_higher_share','cov_chosen5','cov_mostused5','cov_random5','map_r','families','tasks','scores']
pd.set_option('display.width',260); pd.set_option('display.max_columns',40)
print('BASE'); print(b[cols].round(3).to_dict()); print('base chosen5',base['chosen5'])
single=df[df.group.isin(['ranks_instead_of_scores','robust_refit_clipped_residuals','home_benchmark_scores_dropped','one_fixed_checkpoint_per_geofm','main_text_tables_only'])].set_index('group')
print(single[cols].round(3).T.to_string())
for r in R:
    if r['group'] in single.index: print(r['group'], r.get('chosen5'), r.get('n_dropped'), r.get('n_clipped'))
for g in ('shuffle_scores_within_task','shuffle_geofm_identity_within_paper','corrupt_5pct','corrupt_10pct','sim_truth_as_fitted','sim_one_capability_only','sim_two_capabilities_labels_unrelated'):
    d=df[df.group==g]; print('\n',g,len(d)); print(d[[c for c in cols if c in d]].agg(['mean','min','max']).round(3).T.to_string())
    print('   share p<0.05:',{c:round(float((d[c]<0.05).mean()),2) for c in ('sensor_p','task_type_p','domain_p','sensor|rest_p','task_type|rest_p','domain|rest_p')}, 'share gain_K2 > 2se:', round(float((d.gain_K2>2*d.se_K2).mean()),2) if 'se_K2' in d and d.gain_K2.notna().any() else None, 'n cv',int(d.gain_K2.notna().sum()) if 'gain_K2' in d else 0)
L=df[df.group=='leave_one_paper_out']; print('\nLOPO',len(L)); print(L[[c for c in cols if c in L and c not in ('acc_K1','acc_K2','gain_K2','gain_K3')]].agg(['min','median','max']).round(3).T.to_string())
print('   share p<0.05:',{c:round(float((L[c]<0.05).mean()),2) for c in ('sensor_p','task_type_p','domain_p','sensor|rest_p','task_type|rest_p','domain|rest_p')})
for c,lo in (('imagery_contrast_sd',True),('pretrain_match_pts',True),('sensor_excess',True),('domain_excess',True),('strength_frozen',True),('cov_mostused5',False),('map_r',True)):
    i=L[c].idxmin() if lo else L[c].idxmax(); print('   most influential for',c,':',L.loc[i,'paper'],round(L.loc[i,c],3),'| tasks left',L.loc[i,'tasks'])
ch=collections.Counter(x for r in R if r['group']=='leave_one_paper_out' for x in r.get('chosen5',[])); print('   chosen5 frequency over LOPO:',ch.most_common(10))
ratio=(L.strength_frozen/L.strength_finetuned); print('   frozen/ft ratio range',ratio.min().round(2),ratio.max().round(2),'chosen/mostused min',(L.cov_chosen5/L.cov_mostused5).min().round(2))
df.to_pickle(OUTD+'/summary.pkl')
