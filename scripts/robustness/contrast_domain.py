import os as _os, sys as _sys
HERE = _os.path.dirname(_os.path.abspath(__file__)); ROOT = _os.path.dirname(_os.path.dirname(HERE))
WB = _os.environ.get("EOARENA_WORKBOOK_DIR", "")            # directory holding the workbook CSVs (not in this repo)
OUTD = _os.environ.get("EOARENA_OUT", _os.path.join(ROOT, "data", "robustness")); _os.makedirs(OUTD, exist_ok=True)
import sys, json, numpy as np, pandas as pd, collections
sys.path.insert(0,HERE); import robust_lib as R
D=R.load(); Y,M,td=D['Y'],D['mask'],D['td']; pg=np.array([R.pre_of(m) for m in D['models']]); rows=[]
for t in range(Y.shape[1]):
    o=M[:,t]; rk=(pd.Series(Y[o,t]).rank().values-1)/(o.sum()-1)*100; a=pg[o]=='high-resolution RGB'; b=pg[o]=='multispectral optical'
    if a.any() and b.any(): rows.append((td[t],rk[a].mean()-rk[b].mean()))
df=pd.DataFrame(rows,columns=['dataset','contrast']).groupby('dataset').contrast.agg(['mean','size']).reset_index()
df['sensor']=[R.NA.get(n,{}).get('sensor') or '' for n in df.dataset]; df['task']=[R.NA.get(n,{}).get('task_type') or '' for n in df.dataset]; df['domain']=[str(D['domain'].get(n) or '') for n in df.dataset]; df=df[(df.sensor!='')&(df.domain!='')&(df.domain!='nan')]
print(len(df),'datasets with both pretraining groups'); rng=np.random.default_rng(0); y=df['mean'].values
def dm(labs): return np.column_stack([np.ones(len(y))]+[(l==v).astype(float) for l in labs for v in sorted(set(l))[1:]])
def rss(Dm): return ((y-Dm@np.linalg.lstsq(Dm,y,rcond=None)[0])**2).sum()
def test(lab,ctrl,B=5000):
    key=np.array(['|'.join(t) for t in zip(*ctrl)]) if ctrl else np.array(['']*len(y)); r0=rss(dm(ctrl)) if ctrl else ((y-y.mean())**2).sum(); st=lambda l: 1-rss(dm(ctrl+[l]))/r0; o=st(lab); nul=[]
    for _ in range(B):
        p=lab.copy()
        for k in set(key): i=np.where(key==k)[0]; p[i]=lab[rng.permutation(i)]
        nul.append(st(p))
    nul=np.array(nul); return round(float(o),3),round(float(nul.mean()),3),round(float((nul>=o).mean()),4)
s,d,t=df.sensor.values,df.domain.values,df.task.values
print('sensor alone',test(s,[])); print('domain alone',test(d,[])); print('sensor | domain',test(s,[d])); print('domain | sensor',test(d,[s])); print('sensor | domain, task',test(s,[d,t])); print('domain | sensor, task',test(d,[s,t]))
print(df.groupby('sensor')['mean'].agg(['mean','size']).round(1)); print(df.groupby('domain')['mean'].agg(['mean','size']).round(1))
print(pd.crosstab(df.domain.str[:24],df.sensor))
