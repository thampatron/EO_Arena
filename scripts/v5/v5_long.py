"""Long table of the analysed matrix (family x setting scores) with setting metadata, within-setting z and rank.
Shared by the v5 noise analyses. Run with EOARENA_WORKBOOK_DIR set; writes a local pickle (scores stay local, never committed)."""
import os, sys, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'robustness')); sys.path.insert(0, os.path.join(HERE, '..'))
import robust_lib as R, prefix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from protocol import PTS, pclass, proto_norm, frac_norm, metric_norm, sensor_norm, xtask   # shared definitions (R^2 is not points)
SHIFTED = {'no_overlap', 'superset', 'ood_test'}
def build(out):
    g = prefix.build(['--offset', 'none', '--skip-sim', '--merge-families'])
    TI = g['TI'].reset_index(drop=True); Y, M = g['Y'], g['mask']; fams = list(g['models']); tasks = list(g['tasks'])
    D = R.load(); assert D['tasks'] == tasks and D['models'] == fams
    rows = []
    for j in range(len(tasks)):
        idx = np.where(M[:, j])[0]; y = Y[idx, j]; sd = y.std(ddof=1)
        z = (y - y.mean()) / sd if sd > 0 else np.zeros_like(y); rk = (pd.Series(y).rank().values - 1) / max(len(y) - 1, 1) * 100
        for k, i in enumerate(idx): rows.append((fams[i], j, y[k], z[k], rk[k], len(idx), bool(D['selfrep'][i, j])))
    L = pd.DataFrame(rows, columns=['family', 'j', 'y', 'z', 'rank', 'n_fam', 'selfrep'])
    meta = TI.assign(j=range(len(TI)))[['j', 'paper_key', 'benchmark_id', 'evaluation_protocol', 'pf', 'metric_s', 'train_fraction_norm', 'canonical_dataset', 'sensor', 'task_type', 'is_leaderboard', 'variant', 'location']]
    L = L.merge(meta, on='j'); L['task'] = L.j.map(dict(enumerate(tasks)))
    L['pts'] = L.metric_s.isin(PTS); L['pclass'] = L.evaluation_protocol.map(pclass); L['shifted'] = L.variant.isin(SHIFTED)
    L['proto'] = L.evaluation_protocol.map(proto_norm); L['frac'] = L.train_fraction_norm.map(frac_norm); L['metric_n'] = L.metric_s.map(metric_norm)
    L['xtask'] = L.apply(xtask, axis=1)   # cross-paper task key (note p. 4), see protocol.py
    # input type per dataset: the note analysis's own rule (build_note_analysis.norm_sensor, mode over the dataset's settings)
    def norm_sensor(s):
        s = str(s).lower()
        if s in ('', 'nan'): return ''
        sar = 's1' in s or 'sar' in s; opt = any(k in s for k in ('s2', 'landsat', 'hls', 'modis', 's3'))
        hr = any(k in s for k in ('aerial', 'rgb', 'planet', 'naip', 'worldview', 'vhr', 'maxar', 'spot', 'google_earth', 'google_static', 'web_map', 'gaofen', 'jilin', 'skysat', 'pleiades', 'geoeye', 'quickbird', 'ikonos', 'superview'))
        return 'SAR + optical' if sar and opt else 'SAR' if sar else 'multispectral' if opt else 'high-resolution optical' if hr else 'other'
    it = L.drop_duplicates('j').assign(ns=lambda d: d.sensor.map(norm_sensor)).groupby('canonical_dataset').ns.agg(lambda s: s.mode().iat[0])
    L['itype'] = L.canonical_dataset.map(it).replace('', 'other')
    L.to_pickle(out); return L
if __name__ == '__main__':
    L = build(sys.argv[1]); print(L.shape, L.paper_key.nunique(), 'papers', L.canonical_dataset.nunique(), 'datasets', L.family.nunique(), 'families')
