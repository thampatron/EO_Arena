import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import sys, json, numpy as np, collections
sys.path.insert(0,HERE); sys.path.insert(0,ROOT+'/scripts')
import prefix
g=prefix.build(['--offset','none','--skip-sim','--merge-families']); TI=g['TI']
na=json.load(open(ROOT+'/data/note_analysis_families.json')); ds=na['datasets']; names=list(ds)
dm=TI.groupby('canonical_dataset').agg(domain=('domain','first'),subdomain=('subdomain','first')).reindex(names)
L=np.array([ds[n]['loading'] for n in names]); src=np.array([ds[n]['sources'] for n in names])
dom=np.array([str(x) if x==x and x else '' for x in dm.domain]); sub=np.array([str(x) if x==x and x else '' for x in dm.subdomain])
sen=np.array([ds[n].get('sensor') or '' for n in names]); tt=np.array([ds[n].get('task_type') or '' for n in names])
rng=np.random.default_rng(0)
def r2(X,lab):
    tot=((X-X.mean(0))**2).sum(); w=sum(((X[lab==g_]-X[lab==g_].mean(0))**2).sum() for g_ in set(lab)); return 1-w/tot
def keep2(lab, ok):
    c=collections.Counter(lab[ok]); return ok & np.array([c.get(l,0)>=2 for l in lab])
out={}
# 1 subdomain beyond domain: shuffle subdomain labels within domain
ok=keep2(sub,(sub!='')&(dom!='')); X=L[ok]; s=sub[ok]; d=dom[ok]
o=r2(X,s); od=r2(X,d); nul=[]
for _ in range(4000):
    p=s.copy()
    for dd in set(d): i=np.where(d==dd)[0]; p[i]=s[rng.permutation(i)]
    nul.append(r2(X,p))
out['subdomain_within_domain']={'n':int(ok.sum()),'levels':len(set(s)),'r2_subdomain':round(o,3),'r2_domain_same_datasets':round(od,3),'null_mean_within_domain':round(float(np.mean(nul)),3),'p':round(float(np.mean(np.array(nul)>=o)),4)}
okm=keep2(sub,(sub!='')&(dom!='')&(src>=2)); X=L[okm]; s=sub[okm]; d=dom[okm]; o=r2(X,s); nul=[]
for _ in range(4000):
    p=s.copy()
    for dd in set(d): i=np.where(d==dd)[0]; p[i]=s[rng.permutation(i)]
    nul.append(r2(X,p))
out['subdomain_within_domain_multi']={'n':int(okm.sum()),'levels':len(set(s)),'r2_subdomain':round(o,3),'r2_domain':round(r2(X,d),3),'null_mean_within_domain':round(float(np.mean(nul)),3),'p':round(float(np.mean(np.array(nul)>=o)),4)}
# 2 after removing sensor and task type
def resid(X,labs):
    D=np.column_stack([np.ones(len(X))]+[(l==v).astype(float) for l in labs for v in sorted(set(l))[1:]]); return X-D@np.linalg.lstsq(D,X,rcond=None)[0]
for nm,lab in (('domain',dom),('subdomain',sub),('sensor',sen),('task_type',tt)):
    others=[x for k,x in (('sensor',sen),('task_type',tt),('domain',dom)) if k!=nm and not (nm=='subdomain' and k=='domain')]
    ok=keep2(lab,(lab!='')&(sen!='')&(tt!='')&(dom!='')); X=resid(L[ok],[o_[ok] for o_ in others]); l=lab[ok]; o=r2(X,l); nul=[r2(X,rng.permutation(l)) for _ in range(3000)]
    out['partial_'+nm]={'controls':[k for k,x in (('sensor',sen),('task_type',tt),('domain',dom)) if k!=nm and not (nm=='subdomain' and k=='domain')],'n':int(ok.sum()),'levels':len(set(l)),'r2':round(o,3),'null_mean':round(float(np.mean(nul)),3),'p':round(float(np.mean(np.array(nul)>=o)),4)}
# 3 per subdomain tightness: mean distance to centroid vs random groups of same size
ok=keep2(sub,sub!=''); rows=[]
Xall=L[ok]; sall=sub[ok]
for sd in sorted(set(sall)):
    i=np.where(sall==sd)[0]; n=len(i); disp=np.sqrt(((Xall[i]-Xall[i].mean(0))**2).sum(1)).mean()
    nul=[np.sqrt(((Xall[j]-Xall[j].mean(0))**2).sum(1)).mean() for j in (rng.choice(len(Xall),n,replace=False) for _ in range(3000))]
    rows.append({'subdomain':sd,'domain':dom[ok][i][0],'n':n,'multi_source':int((src[ok][i]>=2).sum()),'centroid':[round(float(x),2) for x in Xall[i].mean(0)],'spread':round(float(disp),2),'spread_random':round(float(np.mean(nul)),2),'p_tighter':round(float(np.mean(np.array(nul)<=disp)),3)})
out['per_subdomain']=sorted(rows,key=lambda r:r['p_tighter'])
out['points']=[{'dataset':n,'x':float(L[i,0]),'y':float(L[i,1]),'domain':dom[i],'subdomain':sub[i],'sensor':sen[i],'task_type':tt[i],'sources':int(src[i])} for i,n in enumerate(names)]
json.dump(out,open(OUTD+'/subdomain_explore.json','w'),indent=1)
for k,v in out.items():
    if k=='points': continue
    if k=='per_subdomain':
        for r in v: print(r)
    else: print(k,v)
