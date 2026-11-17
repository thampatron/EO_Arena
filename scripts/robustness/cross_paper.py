import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import sys, json, numpy as np, pandas as pd, itertools
sys.path.insert(0,HERE); import robust_lib as R
from scipy.stats import spearmanr
D=R.load(); Y,M,td,tp,pf,met,tf=D['Y'],D['mask'],D['td'],D['tp'],D['pf'],D['metric'],D['tf']; T=Y.shape[1]; rows=[]
for a,b in itertools.combinations(range(T),2):
    if td[a]!=td[b] or tp[a]==tp[b]: continue
    c=M[:,a]&M[:,b]
    if c.sum()<4: continue
    rho=spearmanr(Y[c,a],Y[c,b]).correlation; same=(pf[a]==pf[b]); samem=(met[a]==met[b]) and (tf[a]==tf[b]) and same
    rows.append(dict(dataset=td[a],pa=tp[a],pb=tp[b],n=int(c.sum()),rho=rho,same_protocol=bool(same),same_setup=bool(samem),absdiff=float(np.median(np.abs(Y[c,a]-Y[c,b]))) if samem else np.nan,sd=float((Y[c,a].std(ddof=1)+Y[c,b].std(ddof=1))/2)))
df=pd.DataFrame(rows); print(len(df), df.dataset.nunique())
def summ(d): 
    g=d.groupby(['dataset','pa','pb']).agg(rho=('rho','mean'),absdiff=('absdiff','median'),sd=('sd','mean'),n=('n','max')); return dict(paper_pairs=len(g),datasets=int(g.index.get_level_values(0).nunique()),median_rho=round(float(g.rho.median()),2),share_rho_below_0=round(float((g.rho<0).mean()),2),share_rho_above_0_5=round(float((g.rho>0.5).mean()),2),median_abs_diff_pts=round(float(g.absdiff.median()),2) if g.absdiff.notna().any() else None,median_between_geofm_sd_pts=round(float(g.sd.median()),2))
out={'all_pairs':summ(df),'same_protocol':summ(df[df.same_protocol]),'different_protocol':summ(df[~df.same_protocol]),'same_protocol_metric_trainfraction':summ(df[df.same_setup])}
# different datasets, different papers, for reference
ref=[]; rng=np.random.default_rng(0); idx=rng.choice(T,(40000,2))
for a,b in idx:
    if td[a]==td[b] or tp[a]==tp[b]: continue
    c=M[:,a]&M[:,b]
    if c.sum()>=4: ref.append(spearmanr(Y[c,a],Y[c,b]).correlation)
out['different_dataset_different_paper_median_rho']=round(float(np.nanmedian(ref)),2); out['n_ref']=len(ref)
g=df[df.same_protocol].groupby('dataset').rho.agg(['mean','size']).sort_values('mean'); out['datasets_lowest_agreement']=g.head(6).round(2).reset_index().to_dict('records'); out['datasets_highest_agreement']=g.tail(6).round(2).reset_index().to_dict('records')
# largest residuals
f,psi=R.fit(D); P=f.predict(); z=np.where(M,(Y-P)/np.sqrt(np.maximum(psi,1e-6))[None],0); i=np.argsort(-np.abs(z),axis=None)[:25]; r,c=np.unravel_index(i,z.shape)
out['share_abs_z_gt_2_5']=round(float((np.abs(z[M])>2.5).mean()),4); out['share_abs_z_gt_3']=round(float((np.abs(z[M])>3).mean()),4)
big=pd.DataFrame({'paper':tp[c],'geofm':[D['models'][k] for k in r],'dataset':td[c],'z':z[r,c].round(1)}); out['largest_residuals_by_paper']=big.paper.value_counts().head(8).to_dict()
zz=pd.DataFrame({'paper':np.repeat(tp[None],M.shape[0],0)[M],'big':(np.abs(z[M])>2.5)}); s=zz.groupby('paper').big.agg(['mean','sum','size']); out['papers_with_most_large_residuals']=s.sort_values('sum',ascending=False).head(6).round(3).reset_index().to_dict('records')
json.dump(out,open(OUTD+'/cross_paper.json','w'),indent=1); big.to_csv(OUTD+'/largest_residuals_private.csv',index=False)
for k,v in out.items(): print(k,v)
