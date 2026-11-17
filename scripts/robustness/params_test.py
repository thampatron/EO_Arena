import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import sys, json, numpy as np, pandas as pd, collections
sys.path.insert(0,HERE); import robust_lib as R
P={x['dataset']:x for x in json.load(open(ROOT+'/data/dataset_parameters.json'))}
D=R.load(); f,psi=R.fit(D); names,Ld,L,w,sh=R.dataset_loadings(D,f); S=np.linalg.norm(Ld,axis=1); nsrc=pd.Series(D['tp']).groupby(D['td']).nunique().reindex(names).values
def kw(s,rules,default='other'):
    if s is None: return ''
    s=str(s).lower()
    for k,v in rules:
        if any(t in s for t in k): return v
    return default
num=lambda v: v if isinstance(v,(int,float)) and v==v else None
def binned(v,edges,labels):
    v=num(v)
    if v is None: return ''
    for e,l in zip(edges,labels):
        if v<=e: return l
    return labels[-1]
F={}
F['Ground resolution']=[binned(P[n].get('gsd_m'),[3,9.99,10,1e9],['3 m or finer','3 to 10 m','10 m','coarser than 10 m']) for n in names]
F['Number of bands']=[binned(P[n].get('n_bands'),[3,9,1e9],['1 to 3','4 to 9','10 or more']) for n in names]
F['Patch size']=[binned(P[n].get('patch_size_px'),[64,128,256,1e9],['64 px or less','65 to 128','129 to 256','over 256']) for n in names]
F['Time structure']=[kw(P[n].get('temporal'),[(('time series',),'time series'),(('bi-temporal',),'bi-temporal'),(('single',),'single date')]) for n in names]
F['Number of classes']=[binned(P[n].get('n_classes'),[2,9,1e9],['2','3 to 9','10 or more']) for n in names]
F['Label source']=[kw(P[n].get('label_source'),[(('manual','expert','annotat','photo-interp','visual'),'manual annotation'),(('map product','existing','cadast','declared','inventory','census','corine','chart'),'existing map or registry'),(('in-situ','field','plot','survey','ground'),'in-situ or field'),(('lidar','model','derived','gedi','automatic','algorithm','ais'),'sensor- or model-derived'),(('crowd','osm','openstreetmap'),'crowdsourced')]) for n in names]
F['Label granularity']=[kw(P[n].get('label_granularity'),[(('pixel',),'pixel'),(('object','box'),'object'),(('point',),'point'),(('patch','tile','scene'),'patch')]) for n in names]
F['Train/test split']=[kw(P[n].get('split_type'),[(('spatial','geograph'),'spatially disjoint'),(('temporal',),'temporal'),(('random',),'random'),(('official',),'official, unspecified')]) for n in names]
F['Publication year']=[binned(P[n].get('publication_year'),[2020,2023,1e9],['2020 or earlier','2021 to 2023','2024 or later']) for n in names]
F['Training set size']=[binned(P[n].get('n_train'),[1500,10000,1e12],['1,500 or fewer','1,500 to 10,000','over 10,000']) for n in names]
F['Number of countries']=[binned(P[n].get('n_countries_or_regions'),[1,20,1e9],['1','2 to 20','over 20']) for n in names]
F['Input is precomputed embeddings']=['embeddings' if 'embedding' in str(P[n].get('band_description')).lower() else 'imagery' for n in names]
sen=np.array([R.NA.get(n,{}).get('sensor') or '' for n in names]); tt=np.array([R.NA.get(n,{}).get('task_type') or '' for n in names])
rng=np.random.default_rng(0); out=[]
def strength_test(lab):
    ok=lab!=''; c=collections.Counter(lab[ok]); ok&=np.array([c.get(l,0)>=2 for l in lab]); y=np.log(S[ok])[:,None]; l=lab[ok]
    o=R._r2(y,l); nul=np.array([R._r2(y,rng.permutation(l)) for _ in range(3000)]); return o,nul.mean(),(nul>=o).mean(),{g:(round(float(np.median(S[ok][l==g])),2),int((l==g).sum())) for g in sorted(set(l),key=lambda g:-np.median(S[ok][l==g]))}
for k,v in F.items():
    lab=np.array(v); a=R.label_test(Ld,lab,(),3000,rng); b=R.label_test(Ld,lab,(sen,tt),3000,rng); so,sc,sp,med=strength_test(lab)
    am=R.label_test(Ld[nsrc>=2],lab[nsrc>=2],(),3000,rng)
    out.append(dict(property=k,n=int((lab!='').sum()),levels=dict(collections.Counter(lab[lab!=''])),measures_r2=round(a['r2'],3),measures_chance=round(a['chance'],3),measures_p=round(a['p'],4),
                    after_sensor_task_r2=(round(b['r2'],3) if b else None),after_sensor_task_chance=(round(b['chance'],3) if b else None),after_sensor_task_p=(round(b['p'],4) if b else None),
                    multi_r2=(round(am['r2'],3) if am else None),multi_chance=(round(am['chance'],3) if am else None),multi_p=(round(am['p'],4) if am else None),
                    strength_r2=round(float(so),3),strength_chance=round(float(sc),3),strength_p=round(float(sp),4),median_strength=med))
    print(k,{x:y for x,y in out[-1].items() if x not in ('property','levels')}); print('    ',out[-1]['levels'])
json.dump(out,open(OUTD+'/params_test.json','w'),indent=1)
# continuous: spearman of gsd with axis-2 loading
from scipy.stats import spearmanr
g=np.array([num(P[n].get('gsd_m')) or np.nan for n in names]); ok=~np.isnan(g); print('spearman log gsd vs axis2',spearmanr(np.log(g[ok]),Ld[ok,1]), 'vs axis1',spearmanr(np.log(g[ok]),Ld[ok,0]).correlation,'vs strength',spearmanr(g[ok],S[ok]).correlation)
print('cross-tab sensor x gsd'); print(pd.crosstab(sen,np.array(F['Ground resolution'])))
