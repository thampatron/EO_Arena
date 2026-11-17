import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import sys, json, numpy as np, pandas as pd, time, multiprocessing as mp
ARGV=list(sys.argv)
sys.path.insert(0,HERE); import robust_lib as R
OUT=OUTD+'/results.jsonl'; t0=time.time()
D0=R.load(); f0,psi0=R.fit(D0); names0,Ld0,L0,w0,sh0=R.dataset_loadings(D0,f0); REF=(names0,Ld0.tolist()); REFa=(names0,[list(x) for x in Ld0])
P0=f0.predict(); A0=f0.theta@f0.lam().T
ab=np.array([np.polyfit(A0[:,t],P0[:,t],1) if A0[:,t].std()>1e-9 else (0.0,P0[:,t].mean()) for t in range(P0.shape[1])]); bt,at=ab[:,0],ab[:,1]; sd0=np.sqrt(np.maximum(psi0,1e-6))
def job(spec):
    name,grp,cv=spec['name'],spec['group'],spec.get('cv',False); rng=np.random.default_rng(spec.get('seed',0)); D=D0; Y=D0['Y']; M=D0['mask']; ref=REF
    try:
        if grp=='base': D=D0
        elif grp=='leave_one_paper_out': D=R.sub(D0,cols=D0['tp']!=spec['paper'])
        elif grp in ('corrupt_5pct','corrupt_10pct'):
            Y=Y.copy(); cells=np.argwhere(M); pick=cells[rng.choice(len(cells),int(len(cells)*(0.05 if grp=='corrupt_5pct' else 0.10)),replace=False)]
            tsd=np.array([Y[M[:,t],t].std() for t in range(Y.shape[1])]); Y[pick[:,0],pick[:,1]]+=rng.choice([-1,1],len(pick))*2.5*tsd[pick[:,1]]; D=R.sub(D0,Y=Y)
        elif grp=='shuffle_scores_within_task':
            Y=Y.copy()
            for t in range(Y.shape[1]): o=np.where(M[:,t])[0]; Y[o,t]=Y[rng.permutation(o),t]
            D=R.sub(D0,Y=Y)
        elif grp=='shuffle_geofm_identity_within_paper':
            Y=Y.copy(); M2=M.copy()
            for p in sorted(set(D0['tp'])):
                c=np.where(D0['tp']==p)[0]; r=np.where(M[:,c].any(1))[0]; pr=rng.permutation(r); Y[np.ix_(r,c)]=D0['Y'][np.ix_(pr,c)]; M2[np.ix_(r,c)]=M[np.ix_(pr,c)]
            D=R.sub(D0,Y=Y,mask=M2)
        elif grp=='ranks_instead_of_scores':
            from scipy.stats import norm; Y=Y.copy()
            for t in range(Y.shape[1]): o=M[:,t]; rk=pd.Series(Y[o,t]).rank().values; Y[o,t]=norm.ppf((rk-0.5)/o.sum())*10
            D=R.sub(D0,Y=Y)
        elif grp=='robust_refit_clipped_residuals':
            Y=Y.copy()
            for _ in range(2):
                f,psi=R.fit(R.sub(D0,Y=Y),restarts=2); P=f.predict(); z=(Y-P)/np.sqrt(np.maximum(psi,1e-6))[None]; big=M&(np.abs(z)>2.5); Y[big]=(P+np.sign(z)*2.5*np.sqrt(np.maximum(psi,1e-6))[None])[big]
            D=R.sub(D0,Y=Y); spec['n_clipped']=int(big.sum())
        elif grp=='home_benchmark_scores_dropped': D=R.sub(D0,mask=M&~D0['selfrep']); spec['n_dropped']=int((M&D0['selfrep']).sum())
        elif grp=='one_fixed_checkpoint_per_geofm':
            Dv=R.load(flags=()); u=np.array([R.unit_of(m) for m in Dv['models']]); cnt=Dv['mask'].sum(1); keep=np.zeros(len(u),bool)
            for uu in set(u): i=np.where(u==uu)[0]; keep[i[np.argmax(cnt[i])]]=True
            D=R.sub(Dv,rows=keep); D['models']=[R.unit_of(m) for m in D['models']]
        elif grp=='main_text_tables_only': D=R.load(flags=('--merge-families','--main-text-only'))
        elif grp.startswith('sim_'):
            _,_,Vt=np.linalg.svd(f0.lam()*np.sqrt(w0)[:,None],full_matrices=False); lam=f0.lam()@Vt.T; th=f0.theta@Vt.T
            if grp=='sim_one_capability_only': lam=lam.copy(); lam[:,1:]=0
            if grp=='sim_two_capabilities_labels_unrelated':
                td=D0['td']; nm=sorted(set(td)); perm=dict(zip(nm,rng.permutation(nm))); mean={n:lam[td==n].mean(0) for n in nm}; lam=np.array([mean[perm[n]] for n in td])
            P=at[None]+bt[None]*(th@lam.T); Y=P+rng.normal(size=P.shape)*sd0[None]; D=R.sub(D0,Y=Y)
            w=D0['mask'].sum(0).astype(float); ref=(names0,[list(np.average((lam)[D0['td']==n],axis=0,weights=np.maximum(w[D0['td']==n],1e-9))) for n in names0])
        o=R.findings(D,cv=cv,seeds=spec.get('seeds',(0,)),ref=ref,nperm=spec.get('nperm',1000)); o={k:v for k,v in o.items() if not k.startswith('_')}
    except Exception as e: o={'error':repr(e)}
    return {**{k:v for k,v in spec.items()},**o}
if __name__=='__main__':
    S=[{'name':'base','group':'base','cv':True,'seeds':(0,1,2)}]
    S+=[{'name':g,'group':g,'cv':True} for g in ('ranks_instead_of_scores','robust_refit_clipped_residuals','home_benchmark_scores_dropped','one_fixed_checkpoint_per_geofm','main_text_tables_only')]
    S+=[{'name':f'{g}#{i}','group':g,'cv':True,'seed':i} for g in ('shuffle_scores_within_task','shuffle_geofm_identity_within_paper') for i in range(4)]
    S+=[{'name':f'{g}#{i}','group':g,'cv':i<4,'seed':i} for g in ('sim_truth_as_fitted','sim_one_capability_only','sim_two_capabilities_labels_unrelated') for i in range(16)]
    S+=[{'name':f'lopo:{p}','group':'leave_one_paper_out','paper':p} for p in sorted(set(D0['tp']))]
    S+=[{'name':f'{g}#{i}','group':g,'seed':i} for g in ('corrupt_5pct','corrupt_10pct') for i in range(6)]
    if '--quick' in ARGV: OUT=OUT+'.quick'; S=[s for s in S if s['name'] in ('lopo:'+sorted(set(D0['tp']))[0],'sim_one_capability_only#5','shuffle_geofm_identity_within_paper#0','one_fixed_checkpoint_per_geofm')]; [s.update(cv=False,nperm=100) for s in S]
    done=set()
    try: done={json.loads(l)['name'] for l in open(OUT)}
    except FileNotFoundError: pass
    S=[s for s in S if s['name'] not in done]; print('jobs',len(S),flush=True)
    sh=[int(x) for x in ARGV[ARGV.index('--shard')+1].split('/')] if '--shard' in ARGV else [0,1]; S=S[sh[0]::sh[1]]; print('shard jobs',len(S),flush=True)
    with open(OUT,'a') as fh:
        for s_ in S:
            r=job(s_); fh.write(json.dumps(r,default=float)+'\n'); fh.flush(); print(f"[{time.time()-t0:5.0f}s]",r['name'],r.get('error') or {k:round(v,3) for k,v in r.items() if isinstance(v,float)},flush=True)
