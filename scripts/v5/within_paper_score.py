"""Within-paper dataset reliability: the note's Eq. 4-6 with replicate (seed) noise, compared across datasets only inside papers.

Within one paper, sigma_t^2 is the note's own replicate variance (printed seed SDs) and the model panel, code and protocol are fixed,
so between-lab noise does not enter. Datasets are compared through a blocked (paper-as-block) model on log EDI (Eq. 4):

    log EDI_s = alpha_p(s) + beta_d(s) + gamma_c(s) + u_g(s) + e_s
    EDI_s = tau_s^2 / sigma_s^2,  tau_s^2 = max(Var_m(y) - sigma_s^2 / n_reps, 0),  sigma_s^2 = median seed variance (>= 3 models)

  s       one comparison (a paper's setting with >= 6 GeoFMs, >= 3 of them with seed SDs; build_dataset_analysis section 6)
  alpha_p paper effect (pipeline: models, code, budget), vague prior
  beta_d  dataset effect, beta_d ~ N(0, s_beta^2) (partial pooling), identified from contrasts inside papers
  gamma_c protocol class (fine-tuned vs frozen) effect
  u_g     table effect, u_g ~ N(0, s_table^2): settings from the same table are not independent
  e_s     residual, N(0, s_e^2)
log EDI is used instead of the bounded score because the score saturates near 1 within a paper (EDI floor 0.01). Shifted-distribution
settings are excluded. The result is REPEATABILITY within a fixed pipeline (lab x model effects are constant within a paper and count
as signal), the quantity a single standardised harness (Stage 2) would measure; it is not cross-lab reproducibility.
Usage: EOARENA_WORKBOOK_DIR=<xlsx dir> python3 -I within_paper_score.py <long.pkl> <out_local.json> <out_public.json> <rel_out.pkl>
"""
import os, sys, json, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'robustness')); sys.path.insert(0, os.path.join(HERE, '..'))
ARGV = list(sys.argv)
import prefix
L = pd.read_pickle(ARGV[1]); tinfo = L.drop_duplicates('task').set_index('task')[['shifted', 'sensor', 'itype', 'task_type']]
g = prefix.build(['--offset', 'none', '--skip-sim', '--merge-families'])
src = open(os.path.join(HERE, '..', 'build_dataset_analysis.py')).read()
a = src.index('# ============================================================================= 6. seed-noise'); b = src.index('REL_T = pd.DataFrame(rel_rows)') + len('REL_T = pd.DataFrame(rel_rows)')
exec(compile(src[a:b], 'section6', 'exec'), g)
R = g['REL_T'].copy(); R = R.join(tinfo, on='task'); R = R[R.shifted.fillna(False).astype(bool) == False].copy()
s2 = R.sigma ** 2; t2 = np.maximum(R.spread ** 2 - s2 / R.n_reps, 0.0)
R['edi'] = np.maximum(t2 / s2, 0.01); R['ledi'] = np.log(R.edi)
R['table'] = R.task.str.split('|').str[:2].str.join('|')
nd = R.groupby('source').dataset.nunique(); R = R[R.source.isin(nd[nd >= 2].index)].reset_index(drop=True)
if os.environ.get('PERMUTE'):   # calibration: dataset labels shuffled within each paper (no dataset signal by construction)
    rng = np.random.default_rng(int(os.environ['PERMUTE']))
    R['dataset'] = R.groupby('source').dataset.transform(lambda s: rng.permutation(s.values))
R.to_pickle(ARGV[4])

import jax, jax.numpy as jnp, numpyro, numpyro.distributions as dist
from numpyro.infer import MCMC, NUTS
numpyro.set_host_device_count(2)
P, pi = np.unique(R.source, return_inverse=True); Dn, di = np.unique(R.dataset, return_inverse=True)
C, ci = np.unique(R.protocol.astype(str), return_inverse=True); G, gi = np.unique(R.table, return_inverse=True)
y = R.ledi.values
def model(y=None):
    s_beta = numpyro.sample('s_beta', dist.HalfNormal(2.0)); s_tab = numpyro.sample('s_table', dist.HalfNormal(2.0)); s_e = numpyro.sample('s_e', dist.HalfNormal(2.0))
    with numpyro.plate('papers', len(P)): alpha = numpyro.sample('alpha', dist.Normal(float(np.median(y)), 5.0))
    with numpyro.plate('datasets', len(Dn)): z = numpyro.sample('z', dist.Normal(0, 1))
    beta = numpyro.deterministic('beta', s_beta * z)
    with numpyro.plate('prot', len(C)): gam0 = numpyro.sample('gam0', dist.Normal(0, 2.0))
    gam = gam0 - gam0[0]                                    # first protocol class is the reference
    with numpyro.plate('tables', len(G)): w = numpyro.sample('w', dist.Normal(0, 1))
    mu = alpha[pi] + beta[di] + gam[ci] + s_tab * w[gi]
    numpyro.sample('y', dist.Normal(mu, s_e), obs=y)
mc = MCMC(NUTS(model, target_accept_prob=0.95), num_warmup=1500, num_samples=1500, num_chains=2, progress_bar=False)
mc.run(jax.random.PRNGKey(0), y=jnp.asarray(y))
S = mc.get_samples(); from numpyro.diagnostics import summary
dg = summary(mc.get_samples(group_by_chain=True), prob=0.9)
diag = {'max_rhat': max(float(np.nanmax(v['r_hat'])) for v in dg.values()), 'min_ess': min(float(np.nanmin(v['n_eff'])) for v in dg.values()),
        'divergences': int(np.asarray(mc.get_extra_fields()['diverging']).sum())}
q = lambda x: [float(np.percentile(x, 5)), float(np.percentile(x, 50)), float(np.percentile(x, 95))]
sb, st, se = (np.asarray(S[k]) for k in ('s_beta', 's_table', 's_e'))
beta = np.asarray(S['beta']); a_med = float(np.median(np.asarray(S['alpha'])))
# null: same model with dataset labels permuted within papers -> posterior s_beta under no dataset signal (one permutation, as calibration)
out_d = {}
sensors = R.groupby('dataset').itype.agg(lambda s: s.mode().iat[0] if s.notna().any() else '')
for j, d in enumerate(Dn):
    bj = beta[:, j]; sc = 1 / (1 + np.exp(-(a_med + bj)))
    out_d[d] = {'beta': q(bj), 'score_at_median_paper': q(sc), 'papers': int(R[R.dataset == d].source.nunique()), 'settings': int((R.dataset == d).sum()),
                'itype': str(sensors.get(d, '')), 'p_beta_gt0': float((bj > 0).mean())}
res = {'n_settings': int(len(R)), 'papers': int(len(P)), 'datasets': int(len(Dn)), 'tables': int(len(G)), 'diagnostics': diag,
       's_beta': q(sb), 's_table': q(st), 's_e': q(se), 'share_dataset': q(sb ** 2 / (sb ** 2 + st ** 2 + se ** 2)),
       'protocol_effects': {str(c): q(np.asarray(S['gam0'])[:, k] - np.asarray(S['gam0'])[:, 0]) for k, c in enumerate(C)},
       'alpha_median': a_med, 'datasets_detail': out_d,
       'datasets_ci_excludes_0': int(sum(1 for v in out_d.values() if v['beta'][0] > 0 or v['beta'][2] < 0))}
json.dump(res, open(ARGV[2], 'w'), indent=1)
pub = {k: v for k, v in res.items() if k != 'datasets_detail'}
pub['datasets_detail'] = {d: {k: v[k] for k in ('beta', 'score_at_median_paper', 'papers', 'settings')} for d, v in out_d.items()}
json.dump(pub, open(ARGV[3], 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != 'datasets_detail'}, indent=1))
