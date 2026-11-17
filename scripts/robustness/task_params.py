import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import sys, json, numpy as np, pandas as pd
sys.path.insert(0,HERE); import robust_lib as R
D=R.load(); f,psi=R.fit(D); P=f.predict(); Y,M=D['Y'],D['mask']; T=Y.shape[1]
rows=[]
for t in range(T):
    o=M[:,t]; y=Y[o,t]; p=P[o,t]; n=o.sum(); ev=p.var(ddof=1); rv=((y-p)**2).sum()/max(n-1,1)
    rows.append(dict(task=D['tasks'][t],dataset=D['td'][t],paper=D['tp'][t],pf=D['pf'][t],metric=D['metric'][t],tf=D['tf'][t],n=int(n),mean=float(y.mean()),sd=float(y.std(ddof=1)),snr=float(ev/max(rv,1e-6)),expl=float(ev/max(ev+rv,1e-9)),selfshare=float(D['selfrep'][o,t].mean())))
df=pd.DataFrame(rows); df['sensor']=[R.NA.get(n,{}).get('sensor') or 'unknown' for n in df.dataset]; df['task_type']=[R.NA.get(n,{}).get('task_type') or 'unknown' for n in df.dataset]
acc=df.metric.isin(['miou','acc','acc_top1','f1','map','iou','oa','micro_f1','segm_map','mijacc']); df['acc_like']=acc
df['headroom']=np.where(acc,100-df['mean'],np.nan); df['lowdata']=df.tf.isin(['1%','5%','10%','20%']); df['fulldata']=df.tf.isin(['100%','unspecified'])
df['logsnr']=np.log(df.snr.clip(1e-3)); df['logsd']=np.log(df.sd.clip(1e-2))
print(df[['n','mean','sd','snr','expl','headroom']].describe().round(2).T)
def boot(fn,B=1000,seed=0):
    rng=np.random.default_rng(seed); ps=df.paper.unique(); est=fn(df); bs=[]
    for _ in range(B):
        s=pd.concat([df[df.paper==p] for p in rng.choice(ps,len(ps))]); 
        try: bs.append(fn(s))
        except Exception: pass
    bs=np.array(bs,float); return round(float(est),3),[round(float(x),3) for x in np.nanpercentile(bs,[5,95])]
out={}
# paired within dataset+paper contrasts
def paired(col,a,b,y):
    def fn(d):
        g=d.groupby(['dataset','paper',col])[y].mean().unstack(col); g=g.dropna(subset=[a,b]); return (g[a]-g[b]).mean()
    return fn
def npairs(col,a,b):
    g=df.groupby(['dataset','paper',col]).logsnr.mean().unstack(col).dropna(subset=[a,b]); return len(g)
for y in ('logsnr','logsd','expl'):
    out[f'frozen_minus_finetuned_{y}']=boot(paired('pf','frozen','fine-tuned',y))+ (npairs('pf','frozen','fine-tuned'),)
    out[f'lowdata_minus_full_{y}']=boot(paired('lowdata',True,False,y))+(npairs('lowdata',True,False),)
# saturation: Spearman of headroom with snr / sd among accuracy-like tasks
from scipy.stats import spearmanr
a=df[df.acc_like]
for y in ('snr','sd','expl'): out[f'spearman_headroom_{y}']=boot(lambda d,y=y: spearmanr(d[d.acc_like].headroom,d[d.acc_like][y]).correlation)
out['spearman_nmodels_snr']=boot(lambda d: spearmanr(d.n,d.snr).correlation); out['spearman_selfshare_snr']=boot(lambda d: spearmanr(d.selfshare,d.snr).correlation)
# headroom bins
a=a.assign(bin=pd.cut(a.headroom,[-1,5,15,30,50,101],labels=['mean > 95','85-95','70-85','50-70','< 50']))
out['by_mean_score']=a.groupby('bin',observed=True).agg(tasks=('snr','size'),median_sd_pts=('sd','median'),median_snr=('snr','median'),median_explained=('expl','median')).round(2).reset_index().to_dict('records')
for c in ('pf','task_type','sensor','metric','lowdata'):
    out['by_'+c]=df.groupby(c).agg(tasks=('snr','size'),median_sd=('sd','median'),median_snr=('snr','median'),median_explained=('expl','median')).round(2).reset_index().to_dict('records')
json.dump(out,open(OUTD+'/task_params.json','w'),indent=1,default=str); df.to_pickle(OUTD+'/task_params.pkl')
for k,v in out.items(): print(k, v if not isinstance(v,list) or not isinstance(v[0],dict) else ''); [print('    ',r) for r in v if isinstance(v,list) and isinstance(v[0],dict)]
