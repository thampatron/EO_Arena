import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import sys, json, numpy as np, collections, time
sys.path.insert(0,HERE); sys.path.insert(0,ROOT+'/scripts')
import prefix, dataset_benchmarking as db
g=prefix.build(['--offset','none','--skip-sim','--merge-families']); Y,mask,td,TI,models=g['Y'],g['mask'],np.array(g['td']),g['TI'],list(g['models'])
att=json.load(open(ROOT+'/data/model_attributes.json'))['models']; fp={}
for v in att.values(): fp.setdefault(v['family'],set()).add(v.get('pretraining') or '')
pg=np.array([m.split('|',1)[1] if '|' in m else next(iter(fp.get(m,{''}))) for m in models]); print(collections.Counter(pg))
dmeta=TI.groupby('canonical_dataset').agg(domain=('domain','first'),subdomain=('subdomain','first'),task_type=('task_type','first'),sensor=('sensor','first'))
rng=np.random.default_rng(0); RID=3.0; NA=json.load(open(ROOT+'/data/note_analysis_families.json'))['datasets']
def r2(X,l): tot=((X-X.mean(0))**2).sum(); return 1-sum(((X[l==v]-X[l==v].mean(0))**2).sum() for v in set(l))/tot
def resid(X,labs):
    D=np.column_stack([np.ones(len(X))]+[(l==v).astype(float) for l in labs for v in sorted(set(l))[1:]]); return X-D@np.linalg.lstsq(D,X,rcond=None)[0]
def test(X,lab,ctrl=()):
    ok=(lab!='')&np.all([c!='' for c in ctrl],axis=0) if ctrl else lab!=''
    c=collections.Counter(lab[ok]); ok&=np.array([c.get(l,0)>=2 for l in lab])
    if ok.sum()<8 or len(set(lab[ok]))<2: return None
    Xr=resid(X[ok],[c_[ok] for c_ in ctrl]) if ctrl else X[ok]; l=lab[ok]; o=r2(Xr,l); nul=np.array([r2(Xr,rng.permutation(l)) for _ in range(3000)])
    return {'r2':round(float(o),3),'chance':round(float(nul.mean()),3),'p':round(float((nul>=o).mean()),4),'n':int(ok.sum()),'levels':len(set(l))}
out={}
for name,sel,spec in [('all GeoFMs, sensor part kept',np.ones(len(models),bool),('dataset','protocol','sensor')),('all GeoFMs',np.ones(len(models),bool),('dataset','protocol'))]+[(G_,pg==G_,('dataset','protocol')) for G_ in ('multi-sensor (SAR + optical)','multispectral optical','high-resolution RGB')]:
    t0=time.time(); Ys=Y[sel]; ms=mask[sel]; cols=ms.sum(0)>=4;
    if cols.sum()<20: out[name]={'geofm_families':int(sel.sum()),'tasks_with_4plus':int(cols.sum()),'tasks_with_3plus':int((ms.sum(0)>=3).sum())}; print(name,out[name]); continue
    rows=ms[:,cols].sum(1)>=1; Ys=Ys[rows][:,cols]; ms=ms[rows][:,cols]; tds=td[cols]
    G={k:g['G_ALL'][k][cols] for k in spec}
    f=db.fit_heteroskedastic(Ys,ms,2,G,seed=0,ridge_u=RID,ridge_theta=RID,ridge_g={k:RID for k in G},n_restarts=3,n_iter=300,tol=1e-6,prior_group=g['FAM'][cols])[0]
    L=f.lam(); w=ms.sum(0).astype(float); _,_,Vt=np.linalg.svd(L*np.sqrt(w)[:,None],full_matrices=False); L=L@Vt.T; sh=((L*np.sqrt(w)[:,None])**2).sum(0); sh=sh/sh.sum()
    names=sorted(set(tds)); Ld=np.array([np.average(L[tds==n],axis=0,weights=np.maximum(w[tds==n],1e-9)) for n in names]); sg=np.sign(Ld[:,0].mean()) or 1; Ld[:,0]*=sg
    lab={k:np.array([str(x) if x==x and x else '' for x in dmeta.reindex(names)[k]]) for k in ('sensor','task_type','domain','subdomain')}
    for k in ('sensor','task_type'): lab[k]=np.array([NA.get(n,{}).get(k) or '' for n in names])
    o={'geofm_families':int(rows.sum()),'tasks':int(cols.sum()),'datasets':len(names),'scores':int(ms.sum()),'axis_share':[round(float(x),3) for x in sh]}
    for k in lab: o[k]=test(Ld,lab[k])
    o['domain | sensor, task type']=test(Ld,lab['domain'],(lab['sensor'],lab['task_type'])); o['subdomain | sensor, task type']=test(Ld,lab['subdomain'],(lab['sensor'],lab['task_type']))
    o['sensor | task type, domain']=test(Ld,lab['sensor'],(lab['task_type'],lab['domain'])); o['task type | sensor, domain']=test(Ld,lab['task_type'],(lab['sensor'],lab['domain']))
    i=np.argsort(Ld[:,1]); o['axis2_low']=[names[j] for j in i[:5]]; o['axis2_high']=[names[j] for j in i[-5:][::-1]]
    o['axis2_mean_by_sensor']={s:round(float(Ld[lab['sensor']==s,1].mean()),2) for s in sorted(set(lab['sensor'])) if s}
    out[name]=o; print(f"\n=== {name}  ({time.time()-t0:.0f}s)"); [print('  ',k,v) for k,v in o.items()]
json.dump(out,open(OUTD+'/pretrain_strata.json','w'),indent=1)
