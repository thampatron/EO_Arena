import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
"""Two more quantities from the note: scores relative to a fixed baseline, and the seed-based dataset score (Eq. 4-6) at family level."""
import sys, json, numpy as np, pandas as pd, collections
sys.path.insert(0,HERE); sys.path.insert(0,ROOT+'/scripts')
import prefix_base, robust_lib as R
gb=prefix_base.build(['--offset','none','--skip-sim']); lc=gb['lc'].copy(); lc['cat']=lc.model_id.map(gb['cat']).fillna(''); TIb=gb['TI']
D=R.load(); T=D['tasks']; ti={t:i for i,t in enumerate(T)}; Y,M=D['Y'],D['mask']; rng=np.random.default_rng(0); out={}
fam_pts=dict(zip(TIb.index if 'task' not in TIb else TIb.task, TIb.family)) if False else None
isreg=D['FAM'].astype(bool)
# ---------- A. baseline-relative scores
def baseline(cats):
    b=lc[lc.cat.isin(cats)&lc.task.isin(ti)].groupby('task').y.max(); return b
for nm,cats in (('supervised from scratch',['baseline_random','task_architecture']),('natural-image pretrained (ImageNet etc.)',['baseline_pretrained'])):
    b=baseline(cats); rows=[]
    for t,bv in b.items():
        j=ti[t]; o=M[:,j]; y=Y[o,j]
        if isreg[j]: gain=y-bv; sep=float(np.std(y,ddof=1))                 # log-error units: 100*ln(err_b/err)
        else:
            if bv>=99.5: continue
            gain=100*(y-bv)/(100-bv); sep=float(np.std(gain,ddof=1))          # share of the baseline's remaining error removed
        rows.append(dict(task=t,dataset=D['td'][j],paper=D['tp'][j],pf=D['pf'][j],reg=bool(isreg[j]),baseline=float(bv),n=int(o.sum()),mean_gain=float(np.mean(gain)),median_gain=float(np.median(gain)),share_beating=float(np.mean(y>bv)),best_gain=float(np.max(gain)),sep_rel=sep,sep_raw=float(np.std(y,ddof=1))))
    df=pd.DataFrame(rows); out[nm]={'tasks':len(df),'datasets':int(df.dataset.nunique()),'papers':int(df.paper.nunique()),'median_share_of_geofms_beating_baseline':round(float(df.share_beating.median()),2),
        'tasks_where_no_geofm_beats_it':int((df.share_beating==0).sum()),'tasks_where_fewer_than_half_beat_it':int((df.share_beating<0.5).sum()),'tasks_where_all_beat_it':int((df.share_beating==1).sum()),
        'median_gain_points_metrics_pct_of_baseline_error':round(float(df[~df.reg].median_gain.median()),1),'by_protocol':df.groupby('pf').share_beating.median().round(2).to_dict()}
    dd=df.groupby('dataset').agg(tasks=('task','size'),papers=('paper','nunique'),share_beating=('share_beating','mean'),median_gain=('median_gain','median')).round(2).sort_values('share_beating')
    out[nm]['datasets_where_geofms_rarely_beat_it']=dd.head(8).reset_index().to_dict('records'); out[nm]['datasets_where_geofms_always_beat_it']=dd[dd.share_beating>=0.99].index.tolist()[:15]
    # does the rescaling change the analysis? refit on these tasks, raw vs relative (points tasks only rescaled per task)
    cols=np.isin(np.array(T),df.task.values); Dr=R.sub(D,cols=cols); Yrel=Dr['Y'].copy(); bmap=b.to_dict()
    for j,t in enumerate(Dr['tasks']):
        o=Dr['mask'][:,j]; bv=bmap[t]; Yrel[o,j]=(Dr['Y'][o,j]-bv) if Dr['FAM'][j] else 100*(Dr['Y'][o,j]-bv)/(100-bv)
    fa=R.findings(Dr,nperm=300); fb=R.findings(R.sub(Dr,Y=Yrel),nperm=300,ref=(fa['_names'],fa['_Ld']))
    out[nm]['refit_raw_vs_relative']={'tasks':len(Dr['tasks']),'similarity_map_agreement':round(fb.get('map_r',np.nan),3),'pretrain_match_raw':round(fa['pretrain_match_pts'],1),'pretrain_match_relative':round(fb['pretrain_match_pts'],1),'axis2_share_raw':round(fa['axis2_share'],2),'axis2_share_relative':round(fb['axis2_share'],2),'sensor_p_raw':fa['sensor']['p'],'sensor_p_relative':fb['sensor']['p']}
    df.to_pickle(OUTD+f"/baseline_{'scratch' if 'scratch' in nm else 'pretrained'}.pkl"); print(nm,json.dumps(out[nm],indent=0)[:1900],flush=True)
# ---------- B. seed-based dataset score at family level (note Eq. 3-6)
lc['unit']=[R.unit_of(m) for m in lc.model_id]; g=lc[lc.cat.isin(['GFM_self_supervised','GFM_supervised','GFM_vlm','location_encoder','embedding_fusion',''])|True]; g=g[g.task.isin(ti)&g.unit.isin(set(D['models']))]
f,psi=R.fit(D); P=f.predict(); rows=[]
for t,c in g.groupby('task'):
    j=ti[t]; s=c[c.sd.notna()&(c.sd>0)]
    if len(s)<3: continue
    fm=c.groupby('unit').y.mean(); 
    if len(fm)<5: continue
    nrep=float(np.median(s.n_reps)) if s.n_reps.notna().any() else 1.0; nrep=nrep if nrep==nrep and nrep>0 else 1.0
    def score(units):
        y=fm.loc[units].values; ss=s[s.unit.isin(set(units))]; 
        if len(ss)<2: return np.nan,np.nan,np.nan
        s2=float(np.median(ss.sd.values**2)); t2=max(float(np.var(y,ddof=1))-s2/nrep,0.0); return (t2/(t2+s2) if t2+s2>0 else np.nan),s2,t2
    sc,s2,t2=score(list(fm.index)); bs=[score(list(rng.choice(fm.index,len(fm))))[0] for _ in range(400)]; bs=[x for x in bs if x==x]
    o=M[:,j]; resid_var=float(psi[j]); stable_unexpl=max(resid_var-s2/nrep,0.0)
    rows.append(dict(task=t,dataset=D['td'][j],paper=D['tp'][j],pf=D['pf'][j],families=int(len(fm)),with_sd=int(len(s)),n_reps=nrep,sigma=np.sqrt(s2),tau=np.sqrt(t2),edi=t2/s2 if s2>0 else np.nan,score=sc,lo=float(np.percentile(bs,5)) if bs else np.nan,hi=float(np.percentile(bs,95)) if bs else np.nan,
                     unexplained_stable_share=(stable_unexpl/t2 if t2>0 else np.nan),noise_share_of_leftover=min(s2/nrep/resid_var,1.0) if resid_var>0 else np.nan,mean=float(Y[o,j].mean()),reg=bool(isreg[j])))
S=pd.DataFrame(rows); S.to_pickle(OUTD+'/seed_scores.pkl')
out['seed_dataset_score']={'tasks':len(S),'datasets':int(S.dataset.nunique()),'papers':int(S.paper.nunique()),'papers_list':sorted(S.paper.unique().tolist()),'median_score':round(float(S.score.median()),2),'share_score_above_0_9':round(float((S.score>0.9).mean()),2),'share_score_below_0_5':round(float((S.score<0.5).mean()),2),
    'share_lower_bound_above_0_8':round(float((S.lo>0.8).mean()),2),'median_sigma_points':round(float(S[~S.reg].sigma.median()),2),'median_tau_points':round(float(S[~S.reg].tau.median()),2),
    'median_noise_share_of_leftover':round(float(S.noise_share_of_leftover.median()),3),'median_unexplained_stable_share':round(float(S.unexplained_stable_share.median()),2),'by_protocol_median_score':S.groupby('pf').score.median().round(2).to_dict()}
dd=S.groupby('dataset').agg(tasks=('task','size'),papers=('paper','nunique'),score=('score','median'),lo=('lo','median'),sigma=('sigma','median'),tau=('tau','median')).round(2).sort_values('score'); out['seed_dataset_score']['lowest']=dd.head(10).reset_index().to_dict('records'); out['seed_dataset_score']['highest']=dd.tail(8).reset_index().to_dict('records')
a=S[~S.reg].assign(bin=pd.cut(100-S[~S.reg]['mean'],[-1,5,15,30,101],labels=['mean over 95','85-95','70-85','under 70'])); out['seed_dataset_score']['by_mean_score']=a.groupby('bin',observed=True).agg(tasks=('score','size'),score=('score','median'),sigma=('sigma','median'),tau=('tau','median')).round(2).reset_index().to_dict('records')
# is the score a stable property of the dataset across papers?
m=S.groupby(['dataset','paper']).score.median().reset_index(); k=m.groupby('dataset').size(); out['seed_dataset_score']['datasets_in_2plus_papers']=int((k>=2).sum())
json.dump(out,open(OUTD+'/note_stage2_partial.json','w'),indent=1,default=str); print(json.dumps(out['seed_dataset_score'],indent=0)[:3000])
