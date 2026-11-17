import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import sys, json, numpy as np, pandas as pd, collections, copy
sys.path.insert(0,HERE); sys.path.insert(0,ROOT+'/scripts')
import prefix, dataset_benchmarking as db
RID=3.0; NA=json.load(open(ROOT+'/data/note_analysis_families.json'))['datasets']
ATT=json.load(open(ROOT+'/data/model_attributes.json'))['models']; _fp={}
for v in ATT.values(): _fp.setdefault(v['family'],set()).add(v.get('pretraining') or '')
def unit_of(m):
    v=ATT.get(m); 
    if v is None: return m
    return v['family']+('|'+(v.get('pretraining') or 'unknown') if len(_fp[v['family']])>1 else '')
def pre_of(u): return u.split('|',1)[1] if '|' in u else next(iter(_fp.get(u,{''})))
MOST_USED=json.load(open(ROOT+'/data/suite_selection_families.json'))['best_by_N']['5']['most_used_set']['datasets']
def load(flags=('--merge-families',)):
    g=prefix.build(['--offset','none','--skip-sim',*flags]); TI=g['TI']; tasks=list(g['tasks']); models=list(g['models'])
    lc=g['lc']; ti={t:i for i,t in enumerate(tasks)}; mi={m:i for i,m in enumerate(models)}; sr=np.zeros(g['mask'].shape,bool)
    for t,m,s in zip(lc.task,lc.model_id,lc.selfrep):
        if s and t in ti and m in mi: sr[mi[m],ti[t]]=True
    return dict(Y=g['Y'].copy(),mask=g['mask'].copy(),td=np.array(g['td']),tp=np.array(g['tp']),pf=TI.pf.values.copy(),G={k:np.asarray(g['G_ALL'][k]) for k in ('dataset','protocol','sensor')},FAM=np.asarray(g['FAM']),
                models=models,tasks=tasks,selfrep=sr,domain=dict(zip(TI.canonical_dataset,TI.domain)),metric=TI.metric_s.values.copy(),tf=TI.train_fraction_norm.values.copy())
def sub(D,cols=None,rows=None,Y=None,mask=None):
    D=dict(D); 
    if Y is not None: D['Y']=Y
    if mask is not None: D['mask']=mask
    rows=np.ones(len(D['models']),bool) if rows is None else rows; cols=np.ones(D['mask'].shape[1],bool) if cols is None else cols
    m=D['mask'][rows][:,cols]; kc=m.sum(0)>=4; cidx=np.where(cols)[0][kc]; ridx=np.where(rows)[0]; kr=D['mask'][ridx][:,cidx].sum(1)>=1; ridx=ridx[kr]
    out=dict(D); out['Y']=D['Y'][ridx][:,cidx]; out['mask']=D['mask'][ridx][:,cidx]; out['selfrep']=D['selfrep'][ridx][:,cidx]; out['models']=[D['models'][i] for i in ridx]; out['tasks']=[D['tasks'][i] for i in cidx]
    for k in ('td','tp','pf','FAM','metric','tf'): out[k]=D[k][cidx]
    out['G']={k:v[cidx] for k,v in D['G'].items()}; return out
def fit(D,K=2,restarts=3,seed=0):
    return db.fit_heteroskedastic(D['Y'],D['mask'],K,D['G'],seed=seed,ridge_u=RID,ridge_theta=RID,ridge_g={k:RID for k in D['G']},n_restarts=restarts,n_iter=300,tol=1e-6,prior_group=D['FAM'])
def cvK(D,Ks=(1,2,3),seeds=(0,)):
    o={}
    for K in Ks:
        rs=[db.heldout_cell_cv(D['Y'],D['mask'],K,D['G'],folds=5,seed=s,ridge_u=RID,ridge_theta=RID,ridge_g={k:RID for k in D['G']},n_restarts=2,n_iter=200,tol=1e-6,prior_group=D['FAM']) for s in seeds]
        o[K]=float(np.mean([r['pair_acc'] for r in rs])); o[f'se{K}']=float(np.mean([r['pair_acc_se'] for r in rs])/np.sqrt(len(seeds)))
    return o
def _r2(X,l): tot=((X-X.mean(0))**2).sum(); return 1-sum(((X[l==v]-X[l==v].mean(0))**2).sum() for v in set(l))/max(tot,1e-12)
def _resid(X,labs):
    Dm=np.column_stack([np.ones(len(X))]+[(l==v).astype(float) for l in labs for v in sorted(set(l))[1:]]); return X-Dm@np.linalg.lstsq(Dm,X,rcond=None)[0]
def label_test(X,lab,ctrl=(),nperm=1000,rng=None):
    rng=rng or np.random.default_rng(0); ok=lab!=''
    for c in ctrl: ok&=c!=''
    cnt=collections.Counter(lab[ok]); ok&=np.array([cnt.get(l,0)>=2 for l in lab])
    if ok.sum()<10 or len(set(lab[ok]))<2: return None
    Xr=_resid(X[ok],[c[ok] for c in ctrl]) if ctrl else X[ok]; l=lab[ok]; o=_r2(Xr,l); nul=np.array([_r2(Xr,rng.permutation(l)) for _ in range(nperm)])
    return {'r2':float(o),'chance':float(nul.mean()),'excess':float(o-nul.mean()),'p':float((nul>=o).mean())}
def dataset_loadings(D,f):
    L=f.lam(); w=D['mask'].sum(0).astype(float); _,_,Vt=np.linalg.svd(L*np.sqrt(w)[:,None],full_matrices=False); L=L@Vt.T; sh=((L*np.sqrt(w)[:,None])**2).sum(0); sh=sh/sh.sum()
    names=sorted(set(D['td'])); Ld=np.array([np.average(L[D['td']==n],axis=0,weights=np.maximum(w[D['td']==n],1e-9)) for n in names]); return names,Ld,L,w,sh
def findings(D,cv=False,nperm=1000,seeds=(0,),ref=None):
    out={'families':len(D['models']),'tasks':len(D['tasks']),'scores':int(D['mask'].sum()),'sources':len(set(D['tp']))}
    f,psi=fit(D); names,Ld,L,w,sh=dataset_loadings(D,f); td,pf=D['td'],D['pf']; K=Ld.shape[1]
    out['axis2_share']=float(sh[1]) if K>1 else 0.0
    sen=np.array([NA.get(n,{}).get('sensor') or '' for n in names]); tt=np.array([NA.get(n,{}).get('task_type') or '' for n in names]); dom=np.array([str(D['domain'].get(n) or '') for n in names]); dom[dom=='nan']=''
    rng=np.random.default_rng(1)
    for nm,lab,ctrl in (('sensor',sen,()),('task_type',tt,()),('domain',dom,()),('sensor|rest',sen,(tt,dom)),('task_type|rest',tt,(sen,dom)),('domain|rest',dom,(sen,tt))):
        r=label_test(Ld,lab,ctrl,nperm,rng); out[nm]=r
    # imagery contrast on the axis that best separates (high-res optical + SAR) from multispectral, in units of dataset-loading sd
    hi=np.isin(sen,['high-resolution optical','SAR']); lo=sen=='multispectral'
    if hi.sum()>=3 and lo.sum()>=3 and K>1:
        d=[(Ld[hi,k].mean()-Ld[lo,k].mean())/max(Ld[:,k].std(),1e-9) for k in range(1,K)]; out['imagery_contrast_sd']=float(np.max(np.abs(d)))
    # protocol
    rat=[]; nf=0
    for n in names:
        a,b=(td==n)&(pf=='frozen'),(td==n)&(pf=='fine-tuned')
        if a.any() and b.any():
            sa,sb=np.linalg.norm(np.average(L[a],axis=0,weights=w[a])),np.linalg.norm(np.average(L[b],axis=0,weights=w[b])); rat.append((sa,sb)); nf+=sa>sb
    if rat: rat=np.array(rat); out['strength_frozen']=float(np.median(rat[:,0])); out['strength_finetuned']=float(np.median(rat[:,1])); out['frozen_higher_share']=float(nf/len(rat)); out['n_both_protocols']=len(rat)
    # suite
    nsrc=pd.Series(D['tp']).groupby(td).nunique().reindex(names).values; ms=np.where(nsrc>=2)[0]; Lm=Ld[ms]; I=np.eye(K)
    V=lambda idx: np.linalg.slogdet(I+Lm[idx].T@Lm[idx])[1] if len(idx) else 0.0
    if len(ms)>=8:
        VA=V(list(range(len(ms)))); ch=[]
        for _ in range(5): ch.append(max((i for i in range(len(ms)) if i not in ch),key=lambda i:V(ch+[i])))
        mu=[i for i,j in enumerate(ms) if names[j] in MOST_USED]; out['cov_chosen5']=float(V(ch)/VA); out['cov_mostused5']=float(V(mu)/VA) if len(mu)>=4 else None; out['chosen5']=[names[ms[i]] for i in ch]; out['n_multi']=len(ms)
        rr=np.random.default_rng(2); out['cov_random5']=float(np.mean([V(list(rr.choice(len(ms),5,replace=False)))/VA for _ in range(300)]))
    # model-free pretraining match (ranks only)
    pg=np.array([pre_of(m) for m in D['models']]); tsen=np.array([NA.get(n,{}).get('sensor') or '' for n in td]); acc=collections.defaultdict(list)
    for t in range(D['mask'].shape[1]):
        o=D['mask'][:,t]
        if o.sum()<4 or tsen[t] not in ('multispectral','high-resolution optical'): continue
        y=D['Y'][o,t]; rk=(pd.Series(y).rank().values-1)/(o.sum()-1)*100
        for G_ in ('high-resolution RGB','multispectral optical'):
            s=pg[o]==G_
            if s.any(): acc[(G_,tsen[t])].append(rk[s].mean())
    mm=lambda a,b: float(np.mean(acc[(a,b)])) if acc[(a,b)] else np.nan
    out['rank_hr_on_ms']=mm('high-resolution RGB','multispectral'); out['rank_hr_on_hr']=mm('high-resolution RGB','high-resolution optical'); out['rank_ms_on_ms']=mm('multispectral optical','multispectral'); out['rank_ms_on_hr']=mm('multispectral optical','high-resolution optical')
    out['pretrain_match_pts']=float(((out['rank_hr_on_hr']-out['rank_hr_on_ms'])+(out['rank_ms_on_ms']-out['rank_ms_on_hr']))/2)
    if ref is not None:      # agreement of the dataset similarity map with the reference fit, on shared multi-source datasets
        rn,rL=ref; common=[n for n in rn if n in names and nsrc[names.index(n)]>=2]
        if len(common)>=8:
            A=db.similarity(np.array([rL[rn.index(n)] for n in common])); B=db.similarity(np.array([Ld[names.index(n)] for n in common])); iu=np.triu_indices(len(common),1); out['map_r']=float(np.corrcoef(A[iu],B[iu])[0,1])
    if cv:
        c=cvK(D,seeds=seeds); out['acc_K1'],out['acc_K2'],out['acc_K3']=c[1],c[2],c[3]; out['gain_K2']=c[2]-c[1]; out['gain_K3']=c[3]-c[2]; out['se_K2']=c['se2']
    out['_names']=names; out['_Ld']=Ld.tolist(); return out
