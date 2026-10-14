"""Model ranking from the workbook: within-comparison z-scores averaged per model. Summary stats only."""
import pandas as pd, numpy as np, json, sys
X='/home/claude/viki/metaanalysis_benchmark_table_v4.xlsx'
r=pd.read_pickle('results_labelled.pkl')
r=r[(r.agreement_vs_recitation=='original')&(~r.model_id.str.contains('_abl'))&(r.is_non_foundation_baseline!=1)].copy()
r=r[r.input_kind=='eo_imagery']
r['hib']=r.higher_is_better.astype(str)=='True'; r['s']=np.where(r.hib,r.v,-r.v)
reg=pd.read_excel(X,'model_registry').drop_duplicates('model_id').set_index('model_id')
own=r[r.is_self_reported==True].groupby('model_id').paper_key.agg(set).to_dict()
# Self-reported = the paper that introduced the model (Viki's is_self_reported flag). Later releases from the same lab count as independent.
r['self2']=[p in own.get(m,set()) for m,p in zip(r.model_id,r.paper_key)]
key=['paper_key','benchmark_id','evaluation_protocol','metric','train_fraction_norm']
rows=[]
for k,g in r.groupby(key,dropna=False):
    m=g.groupby('model_id').s.mean(); 
    if len(m)<4 or m.std()==0: continue
    z=(m-m.mean())/m.std(); rk=m.rank(ascending=False)
    selfm=set(g[g.self2].model_id)
    proto=str(k[2]); pfam='fine-tuned' if proto in('FT','PFT') else 'frozen' if proto in('frozen_dec','LP','kNN','frozen','frozen_best','PE','MLP') else 'other'
    for mid in m.index:
        rows.append(dict(model_id=mid,paper=k[0],dataset=g.canonical_dataset.iat[0],domain=g.domain.iat[0],subdomain=g.subdomain.iat[0] if isinstance(g.subdomain.iat[0],str) else '',proto=pfam,z=z[mid],win=(len(m)-rk[mid])/(len(m)-1),self=mid in selfm))
C=pd.DataFrame(rows)
def agg(d):
    return pd.Series(dict(comparisons=len(d),benchmarks=d.dataset.nunique(),papers=d.paper.nunique(),mean_z=d.z.mean(),win_rate=d.win.mean()))
A=C.groupby('model_id').apply(agg)
I=C[~C.self].groupby('model_id').apply(agg).add_prefix('ind_')
S=C[C.self].groupby('model_id').apply(agg).add_prefix('self_')
F=C[(~C.self)&(C.proto=='fine-tuned')].groupby('model_id').z.mean().rename('ind_ft_z')
Z=C[(~C.self)&(C.proto=='frozen')].groupby('model_id').z.mean().rename('ind_frozen_z')
T=A.join(I,how='left').join(S,how='left').join(F).join(Z)
T['domains']=C[~C.self].groupby('model_id').domain.agg(lambda s:';'.join(sorted(set(x for x in s if isinstance(x,str)))))
for c in ['row_label','backbone','pretraining_method','pretraining_dataset','category','encoder_parameter_count','own_paper_refs']:
    T[c]=T.index.map(reg[c]) if c in reg.columns else ''
T['name']=T.index
T['ranked']=(T.ind_comparisons.fillna(0)>=10)&(T.ind_benchmarks.fillna(0)>=5)
T=T[T.ind_comparisons.fillna(0)>=1]
T=T.sort_values(['ranked','ind_mean_z'],ascending=[False,False]); T['rank']=[i+1 if rk else None for i,rk in enumerate(T.ranked)]
GEN=r'imagenet|lvd|laion|^clip|^dinov2|^dinov3_(vit|convnext)|^sam|^swin_t|^vitb_|^resnet|^convnext'
T['general_vision']=T.category.astype(str).str.contains('baseline_pretrained',case=False)|T.pretraining_dataset.astype(str).str.contains('imagenet|lvd|laion',case=False)|T.name.str.contains(GEN,case=False,regex=True)
T.loc[T.name.str.contains('sat',case=False)&T.name.str.contains('dinov3'),'general_vision']=False
cols=['rank','ranked','name','backbone','pretraining_dataset','category','encoder_parameter_count','general_vision','ind_comparisons','ind_benchmarks','ind_papers','ind_mean_z','ind_win_rate','ind_ft_z','ind_frozen_z','self_comparisons','self_mean_z','self_win_rate','comparisons','benchmarks','papers','mean_z','win_rate','domains']
out=T[cols].copy()
recs=[]
for rec in out.to_dict('records'):
    o={}
    for k,v in rec.items():
        if isinstance(v,(float,np.floating)): o[k]=None if np.isnan(v) else round(float(v),3)
        elif isinstance(v,(np.integer,)): o[k]=int(v)
        elif isinstance(v,(bool,np.bool_)): o[k]=bool(v)
        else: o[k]=None if (v is None or (isinstance(v,float) and np.isnan(v))) else (str(v) if v==v else None)
    recs.append(o)
meta={"as_of":"2026-10-08","n_models_ranked":int(T.ranked.sum()),"n_models_total":int(A.shape[0]),"n_comparisons":int(len(C)),
 "method":"Each comparison is one paper's table with >= 4 models on the same benchmark, protocol, metric and train fraction (original results only; ablations and non-foundation baselines dropped). Scores are z-scored within the comparison, so paper and benchmark offsets cancel, and averaged per model. Independent = comparisons from papers that did not introduce the model (each model release is its own team; a lab's later paper counts as independent for its earlier models). Win rate = share of other models in the comparison that the model beats. Ranked by independent mean z; imagery benchmarks only. A model is ranked only with >= 10 independent comparisons on >= 5 benchmarks; others are listed unranked."}
def scope_table(sub):
    I2=sub[~sub.self].groupby('model_id').apply(agg).add_prefix('ind_')
    S2=sub[sub.self].groupby('model_id').apply(agg).add_prefix('self_')
    F2=sub[(~sub.self)&(sub.proto=='fine-tuned')].groupby('model_id').z.mean().rename('ind_ft_z')
    Z2=sub[(~sub.self)&(sub.proto=='frozen')].groupby('model_id').z.mean().rename('ind_frozen_z')
    if len(I2)==0: return []
    T2=I2.join(S2,how='outer').join(F2).join(Z2)
    T2=T2[T2.ind_comparisons.fillna(0)>=1]
    T2['ranked']=(T2.ind_comparisons>=5)&(T2.ind_benchmarks>=2)
    T2=T2.sort_values(['ranked','ind_mean_z'],ascending=[False,False]); T2['rank']=[i+1 if rk else None for i,rk in enumerate(T2.ranked)]
    out2=[]
    for mid,rec in T2.iterrows():
        o={'name':mid,'rank':None if pd.isna(rec['rank']) else int(rec['rank']),'ranked':bool(rec.ranked)}
        for c in ['ind_comparisons','ind_benchmarks','ind_papers','ind_mean_z','ind_win_rate','ind_ft_z','ind_frozen_z','self_comparisons','self_mean_z']:
            v=rec.get(c); o[c]=None if v is None or pd.isna(v) else (int(v) if c.endswith(('comparisons','benchmarks','papers')) else round(float(v),3))
        out2.append(o)
    return out2
scopes={}
C2=C[C.domain.isin(['composite','outside_taxonomy'])==False]
for d,g in C2.groupby('domain'):
    scopes['d:'+d]={'label':d,'kind':'domain','benchmarks':int(g.dataset.nunique()),'comparisons':int(len(g)),'models':scope_table(g)}
for (d,sd),g in C2[C2.subdomain!=''].groupby(['domain','subdomain']):
    scopes['s:'+sd]={'label':sd,'kind':'subdomain','domain':d,'benchmarks':int(g.dataset.nunique()),'comparisons':int(len(g)),'models':scope_table(g)}
meta["scope_rule"]="Within a domain or subdomain a model is ranked with >= 5 independent comparisons on >= 2 benchmarks."
json.dump({"meta":meta,"models":recs,"scopes":scopes},open('/home/claude/eo_arena/data/model_ranking.json','w'),indent=0)
pd.set_option('display.width',250)
print(len(recs),'ranked of',A.shape[0]); print(out[out.ranked][['rank','name','ind_comparisons','ind_benchmarks','ind_papers','ind_mean_z','ind_win_rate','self_mean_z','general_vision']].head(25).to_string(index=False))
