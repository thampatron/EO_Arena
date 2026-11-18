import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
"""Note Eq. 11 inside the model: lambda_t = app + geo + time + sensor + app x geo + u_t. Compare with other loading structures by held-out cells."""
import sys, json, numpy as np, pandas as pd, time
ARGV=list(sys.argv); sys.path.insert(0,HERE); import robust_lib as R, dataset_benchmarking as db
D=R.load(); td=D['td']; GT=json.load(open(ROOT+'/data/dataset_geo_time.json'))['datasets']; t0=time.time()
def lev(v): s=pd.Series(v).astype(str).replace({'':np.nan,'nan':np.nan,'None':np.nan}); return np.asarray(pd.factorize(s)[0],int)
app=np.array([str(D['domain'].get(n) or '') for n in td]); geo=np.array([GT.get(n,{}).get('geography') or '' for n in td]); per=np.array([GT.get(n,{}).get('period') or '' for n in td])
inter=np.array([f'{a}|{g_}' if a not in ('','nan') and g_ else '' for a,g_ in zip(app,geo)])
GR={'application':lev(app),'geography':lev(geo),'time':lev(per),'sensor':D['G']['sensor'],'application x geography':lev(inter),'dataset':D['G']['dataset'],'protocol':D['G']['protocol']}
print({k:(int((v>=0).sum()),int(v.max()+1)) for k,v in GR.items()},flush=True)
E11=['application','geography','time','sensor','application x geography']
SPECS={'free loadings (no structure)':[],'Eq. 11 as written':E11,'Eq. 11 + protocol':E11+['protocol'],'dataset + protocol + sensor (used so far)':['dataset','protocol','sensor'],'Eq. 11 + protocol + dataset':E11+['protocol','dataset']}
ABL={f'Eq. 11 + protocol, without {g}':[x for x in E11+['protocol'] if x!=g] for g in E11+['protocol']}
def cv(groups,K,seeds=(0,1)):
    G={g:GR[g] for g in groups}; rs=[db.heldout_cell_cv(D['Y'],D['mask'],K,G,folds=5,seed=s,ridge_u=R.RID,ridge_theta=R.RID,ridge_g={g:R.RID for g in G},n_restarts=2,n_iter=200,tol=1e-6,prior_group=D['FAM']) for s in seeds]
    return float(np.mean([r['pair_acc'] for r in rs])),float(np.mean([r['pair_acc_se'] for r in rs])/np.sqrt(len(seeds)))
def fitg(groups,K=2,Dd=None,GRd=None):
    Dd=Dd or D; GRd=GRd or GR; G={g:GRd[g] for g in groups}
    return db.fit_heteroskedastic(Dd['Y'],Dd['mask'],K,G,seed=0,ridge_u=R.RID,ridge_theta=R.RID,ridge_g={g:R.RID for g in G},n_restarts=3,n_iter=300,tol=1e-6,prior_group=Dd['FAM'])[0],G
def parts(f,G,mask):
    """Share of the (observation-weighted) squared loading carried by each part; parts are not orthogonal, so shares are of the sum of parts."""
    w=mask.sum(0).astype(float); L=f.lam(); comp={g:np.where((idx>=0)[:,None],f.B[g][np.clip(idx,0,None)],0.0) for g,idx in G.items()}; comp['task-specific remainder']=L-sum(comp.values())
    ss={g:float((w[:,None]*c**2).sum()) for g,c in comp.items()}; tot=sum(ss.values()); return {g:v/tot for g,v in ss.items()}
out={'groups':{k:{'tasks_with_label':int((v>=0).sum()),'levels':int(v.max()+1)} for k,v in GR.items()},'cv':{},'ablation':{}}
which=ARGV[1] if len(ARGV)>1 else 'all'
if which in ('all','cv'):
    for nm,gs in SPECS.items():
        for K in (1,2,3): a,se=cv(gs,K); out['cv'][f'{nm}|{K}']={'pair_acc':a,'se':se}; print(f'[{time.time()-t0:5.0f}s] {nm} K={K} {a:.4f} ± {se:.4f}',flush=True)
    json.dump(out,open(OUTD+'/eq11_cv.json','w'),indent=1)
if which in ('all','abl'):
    for nm,gs in ABL.items(): a,se=cv(gs,2); out['ablation'][nm]={'pair_acc':a,'se':se}; print(f'[{time.time()-t0:5.0f}s] {nm} {a:.4f} ± {se:.4f}',flush=True)
    json.dump(out['ablation'],open(OUTD+'/eq11_abl.json','w'),indent=1)
if which in ('all','parts'):
    res={}
    for nm in ('Eq. 11 as written','Eq. 11 + protocol'):
        f,G=fitg(SPECS[nm]); res[nm]={'full':parts(f,G,D['mask']),'leave_one_paper_out':[]}; print(nm,{k:round(v,3) for k,v in res[nm]['full'].items()},flush=True)
        for p in sorted(set(D['tp'])):
            c=D['tp']!=p; Dd=R.sub(D,cols=c); keep=np.isin(np.array(D['tasks']),Dd['tasks']); GRd={g:v[keep] for g,v in GR.items()}; f2,G2=fitg(SPECS[nm],Dd=Dd,GRd=GRd); res[nm]['leave_one_paper_out'].append(parts(f2,G2,Dd['mask']))
        lo=pd.DataFrame(res[nm]['leave_one_paper_out']); res[nm]['lopo_min']=lo.min().to_dict(); res[nm]['lopo_max']=lo.max().to_dict(); print('   range',{k:(round(lo[k].min(),3),round(lo[k].max(),3)) for k in lo},flush=True)
    json.dump(res,open(OUTD+'/eq11_parts.json','w'),indent=1)
