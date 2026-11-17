import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import sys, json, numpy as np, pandas as pd
sys.path.insert(0,HERE); import robust_lib as R
P={x['dataset']:x for x in json.load(open(ROOT+'/data/dataset_parameters.json'))}
def labels(D,names):
    sen=np.array([R.NA.get(n,{}).get('sensor') or '' for n in names]); tt=np.array([R.NA.get(n,{}).get('task_type') or '' for n in names]); dom=np.array([str(D['domain'].get(n) or '') for n in names]); dom[dom=='nan']=''
    nb=np.array([('1 to 3' if v<=3 else '4 to 9' if v<=9 else '10 or more') if isinstance(v,(int,float)) else '' for v in [P.get(n,{}).get('n_bands') for n in names]]); return sen,tt,dom,nb
def dummies(labs): return np.column_stack([np.ones(len(labs[0]))]+[(l==v).astype(float) for l in labs for v in sorted(set(l))[1:]])
def rss(X,Dm): return ((X-Dm@np.linalg.lstsq(Dm,X,rcond=None)[0])**2).sum()
def test(Ld,lab,ctrl,rng,B=2000,additive=True):
    ok=(lab!='')&np.all([c!='' for c in ctrl],axis=0); X=Ld[ok]; l=lab[ok]; cs=[c[ok] for c in ctrl]; key=np.array(['|'.join(t) for t in zip(*cs)])
    if additive:
        r0=rss(X,dummies(cs)); stat=lambda l_: 1-rss(X,dummies(cs+[l_]))/r0
    else:
        Xc=X.copy()
        for k in set(key): Xc[key==k]-=X[key==k].mean(0)
        tot=(Xc**2).sum(); stat=lambda l_: 1-sum(((Xc[(key==k)&(l_==v)]-Xc[(key==k)&(l_==v)].mean(0))**2).sum() for k in set(key) for v in set(l_[key==k]))/tot
    o=stat(l); nul=[]
    for _ in range(B):
        p=l.copy()
        for k in set(key): i=np.where(key==k)[0]; p[i]=l[rng.permutation(i)]
        nul.append(stat(p))
    nul=np.array(nul); return round(float(o),3),round(float(nul.mean()),3),round(float((nul>=o).mean()),4)
def run(D,rng):
    f,psi=R.fit(D); names,Ld,L,w,sh=R.dataset_loadings(D,f); sen,tt,dom,nb=labels(D,names)
    return {'domain_add':test(Ld,dom,[sen,tt],rng),'domain_cell':test(Ld,dom,[sen,tt],rng,additive=False),'sensor_add':test(Ld,sen,[tt,dom],rng),'task_add':test(Ld,tt,[sen,dom],rng),'bands_add':test(Ld,nb,[sen,tt],rng),'n':len(names)}
if __name__=='__main__':
    D0=R.load(); rng=np.random.default_rng(0); out={'base':run(D0,rng)}; print('base',out['base'],flush=True)
    for p in sorted(set(D0['tp'])): out['lopo:'+p]=run(R.sub(D0,cols=D0['tp']!=p),rng); print(p,out['lopo:'+p],flush=True)
    Dv=R.load(flags=()); u=np.array([R.unit_of(m) for m in Dv['models']]); cnt=Dv['mask'].sum(1); keep=np.zeros(len(u),bool)
    for uu in set(u): i=np.where(u==uu)[0]; keep[i[np.argmax(cnt[i])]]=True
    Df=R.sub(Dv,rows=keep); Df['models']=[R.unit_of(m) for m in Df['models']]; out['one_checkpoint']=run(Df,rng); print('one_checkpoint',out['one_checkpoint'],flush=True)
    out['main_text']=run(R.load(flags=('--merge-families','--main-text-only')),rng); print('main_text',out['main_text'],flush=True)
    out['no_own_paper']=run(R.sub(D0,mask=D0['mask']&~D0['selfrep']),rng); print('no_own_paper',out['no_own_paper'],flush=True)
    for i in range(6):
        Y=D0['Y'].copy(); M=D0['mask']
        for t in range(Y.shape[1]): o=np.where(M[:,t])[0]; Y[o,t]=Y[rng.permutation(o),t]
        out[f'shuffled#{i}']=run(R.sub(D0,Y=Y),rng); print('shuffled',i,out[f'shuffled#{i}'],flush=True)
    json.dump(out,open(OUTD+'/strat_perm.json','w'),indent=1)
    L=[v for k,v in out.items() if k.startswith('lopo')]
    for key in ('domain_add','domain_cell','sensor_add','task_add','bands_add'): print(key,'LOPO share p<0.05:',round(np.mean([v[key][2]<0.05 for v in L]),2),'median p',np.median([v[key][2] for v in L]),'| shuffled share p<0.05:',np.mean([out[f'shuffled#{i}'][key][2]<0.05 for i in range(6)]))
