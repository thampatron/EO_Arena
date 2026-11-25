"""Cross-study reproducibility-adjusted separation per task: a labelled Stage-1 extension of the note's Eq. 6.

Note (Wang, Oct 2026): score_t = tau2_t / (tau2_t + sigma2_t) (Eq. 6), task = dataset x protocol (p. 4), sigma2_t from repeated
evaluations of the same GeoFM on task t. Here the repeated evaluations are independent papers running the same task (xtask,
protocol.py), so the noise of one published score is sigma2_t = omega2_t (between-paper, model-specific) + sigma2_seed,t.

Model, per task t (values standardised by the task's pooled SD, so tasks on different scales can be pooled):
    y_mp = mu_pt + u_mt + e_mpt,   (fitted through its restricted likelihood: mu and u integrated out)   u_mt ~ N(0, tau_t^2),   e_mpt ~ N(0, omega_t^2 + sigma_seed,t^2 / n)
  mu_pt   paper intercept (fixed in spirit: vague prior) - a lab that shifts every model equally does not change the ordering
  y_mp    the paper's value for family m on task t (mean over that paper's settings of the task; n = number averaged)
  sigma_seed,t  printed seed SD for the task where >= 3 GeoFMs report one (build_dataset_analysis section 6), else the pooled
                median for the scale; published values are treated as single runs (n_reps = 1), the conservative choice
Partial pooling across tasks (one joint model): log tau_t = a + s_a z_t; log(omega_t / tau_t) = b + s_b w_t.
score_t = tau_t^2 / (tau_t^2 + omega_t^2 + sigma_seed,t^2); posterior median and 90% interval (note: "posterior or bootstrap
intervals should be reported"). No floors, no moment corrections, no reporter adjustment.

Eligibility: >= 2 papers, >= 3 families each reported by >= 2 papers, >= 4 families. Families seen by one paper are kept (they
inform tau_t and the paper intercepts). Copies are already removed upstream (D6), so agreement is not inflated by reprints.
Limits (stated, not hidden): decoder, split and band choice are not coded, so omega_t can still contain protocol structure
(an upper bound on implementation noise); tau_t refers to the families evaluated on the task, which papers choose.
Usage: python3 -I ml_task_score.py <long.pkl> <task_outputs_local.json> <out_local.json> <out_public.json> [--sim]
"""
import os, sys, json, numpy as np, pandas as pd
import jax, jax.numpy as jnp, numpyro, numpyro.distributions as dist
from numpyro.infer import MCMC, NUTS
numpyro.set_host_device_count(4); jax.config.update('jax_enable_x64', True)
MINP, MINR, MINF = 2, 3, 4

def prepare(L, seeds):
    L = L[(L.pclass != 'other') & ~L.shifted]
    c = L.groupby(['xtask', 'paper_key', 'family']).agg(y=('y', 'mean'), n=('y', 'size'), pts=('pts', 'first')).reset_index()
    keep = []
    for x, g in c.groupby('xtask'):
        rep = g.groupby('family').paper_key.nunique()
        if g.paper_key.nunique() >= MINP and (rep >= 2).sum() >= MINR and g.family.nunique() >= MINF: keep.append(x)
    c = c[c.xtask.isin(keep)].copy()
    pts_s = [v[0] for v in seeds.values() if v[1]]; log_s = [v[0] for v in seeds.values() if not v[1]]
    pooled = {True: float(np.median(pts_s)) if pts_s else 0.53}
    pooled[False] = float(np.median(log_s)) if log_s else pooled[True]
    T = sorted(keep); tix = {x: i for i, x in enumerate(T)}
    c['t'] = c.xtask.map(tix)
    sd = c.groupby('t').y.std(ddof=1); c['ys'] = c.y / c.t.map(sd)
    seed_sd = np.array([(seeds[x][0] if x in seeds else pooled[bool(c[c.t == i].pts.all())]) / sd[i] for i, x in enumerate(T)])
    seed_measured = np.array([x in seeds for x in T])
    c['pi'] = pd.factorize(c.xtask + '#' + c.paper_key)[0]; c['fi'] = pd.factorize(c.xtask + '#' + c.family)[0]
    return c, T, seed_sd, seed_measured

def task_blocks(c):
    """Per task: y, paper design X (intercepts), family incidence Z, n; mu_pt and u_mt are integrated out analytically, mu by
    REML (flat prior on paper intercepts), u by its normal distribution, so the sampler only sees (tau_t, omega_t) and the
    hyperparameters. This is the restricted likelihood of the per-task crossed model, pooled by a hierarchical prior."""
    B = []
    for i in range(int(c.t.max()) + 1):
        g = c[c.t == i]; X = pd.get_dummies(g.paper_key).values.astype(float); Z = pd.get_dummies(g.family).values.astype(float)
        B.append((jnp.asarray(g.ys.values), jnp.asarray(X), jnp.asarray(Z @ Z.T), jnp.asarray(g.n.values, dtype=float)))
    return B

def reml_ll(y, X, ZZ, n, tau, om, s):
    V = tau ** 2 * ZZ + jnp.diag(om ** 2 + s ** 2 / n)
    Lc = jnp.linalg.cholesky(V); Vi_y = jax.scipy.linalg.cho_solve((Lc, True), y); Vi_X = jax.scipy.linalg.cho_solve((Lc, True), X)
    XtViX = X.T @ Vi_X; L2 = jnp.linalg.cholesky(XtViX)
    beta = jax.scipy.linalg.cho_solve((L2, True), X.T @ Vi_y); r = y - X @ beta
    return -0.5 * (2 * jnp.sum(jnp.log(jnp.diag(Lc))) + 2 * jnp.sum(jnp.log(jnp.diag(L2))) + r @ jax.scipy.linalg.cho_solve((Lc, True), r))

def model(blocks, seed_sd):
    nT = len(blocks)
    a = numpyro.sample('a', dist.Normal(0.0, 1.0)); s_a = numpyro.sample('s_a', dist.HalfNormal(1.0))
    b = numpyro.sample('b', dist.Normal(0.0, 1.5)); s_b = numpyro.sample('s_b', dist.HalfNormal(1.0))
    with numpyro.plate('tasks', nT):
        z = numpyro.sample('z', dist.Normal(0, 1)); w = numpyro.sample('w', dist.Normal(0, 1))
    log_tau = a + s_a * z; log_om = log_tau + b + s_b * w
    tau = numpyro.deterministic('tau', jnp.exp(log_tau)); om = numpyro.deterministic('omega', jnp.exp(log_om))
    numpyro.deterministic('score', tau ** 2 / (tau ** 2 + om ** 2 + seed_sd ** 2))
    numpyro.factor('reml', sum(reml_ll(*blk, tau[i], om[i], seed_sd[i]) for i, blk in enumerate(blocks)))

def fit(c, nT, seed_sd, seed=0, samples=1000):
    blocks = task_blocks(c)
    mc = MCMC(NUTS(model, target_accept_prob=0.95), num_warmup=int(os.environ.get('ML_WARM', 1000)), num_samples=samples, num_chains=int(os.environ.get('ML_CHAINS', 4)), progress_bar=False)
    mc.run(jax.random.PRNGKey(seed), blocks=blocks, seed_sd=jnp.asarray(seed_sd))
    return mc

def summarise(mc, T):
    s = mc.get_samples(); ex = mc.get_extra_fields()
    sc = np.asarray(s['score']); om = np.asarray(s['omega']); ta = np.asarray(s['tau'])
    from numpyro.diagnostics import summary
    diag = summary(mc.get_samples(group_by_chain=True), prob=0.9)
    rhat = max(float(np.nanmax(v['r_hat'])) for v in diag.values()); ess = min(float(np.nanmin(v['n_eff'])) for v in diag.values())
    div = int(np.asarray(mc.get_extra_fields()['diverging']).sum())
    per = {x: {'score': float(np.median(sc[:, i])), 'score90': [float(np.percentile(sc[:, i], 5)), float(np.percentile(sc[:, i], 95))],
               'omega_over_tau': float(np.median(om[:, i] / ta[:, i])), 'tau_std': float(np.median(ta[:, i])), 'omega_std': float(np.median(om[:, i]))} for i, x in enumerate(T)}
    hyper = {k: [float(np.percentile(np.asarray(s[k]), q)) for q in (5, 50, 95)] for k in ('a', 's_a', 'b', 's_b')}   # 5/50/95%
    return per, {'max_rhat': rhat, 'min_ess': ess, 'divergences': div, 'hyper_5_50_95': hyper}

def simulate_check(c, T, seed_sd, reps=int(os.environ.get('ML_SIM_REPS', 1))):
    """Simulation-based check on the real design: draw true task (tau, omega) from a spread of values, simulate data with the
    real paper/family pattern, refit, report rank correlation of true vs estimated score and 90% interval coverage."""
    from scipy.stats import spearmanr
    rng = np.random.default_rng(1); res = []
    for r in range(reps):
        nT = len(T); tau = np.exp(rng.normal(-0.3, 0.5, nT)); om = tau * np.exp(rng.normal(-0.5, 0.8, nT))
        true = tau ** 2 / (tau ** 2 + om ** 2 + seed_sd ** 2)
        mu = rng.normal(0, 1, c.pi.max() + 1); u = rng.normal(0, 1, c.fi.max() + 1) * tau[c.drop_duplicates('fi').sort_values('fi').t.values]
        y = mu[c.pi.values] + u[c.fi.values] + rng.normal(0, 1, len(c)) * np.sqrt(om[c.t.values] ** 2 + seed_sd[c.t.values] ** 2 / c.n.values)
        cc = c.assign(ys=y); mc = fit(cc, nT, seed_sd, seed=r + 10, samples=500); per, _ = summarise(mc, T)
        est = np.array([per[x]['score'] for x in T]); lo = np.array([per[x]['score90'][0] for x in T]); hi = np.array([per[x]['score90'][1] for x in T])
        res.append({'true_sd_log_ratio': 0.8, 'est_s_b_5_50_95': _['hyper_5_50_95']['s_b'], 'spearman_true_vs_est': float(spearmanr(true, est).statistic), 'coverage90': float(((true >= lo) & (true <= hi)).mean()),
                    'mean_abs_err': float(np.abs(true - est).mean()), 'median_width90': float(np.median(hi - lo))})
    return res

if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    L = pd.read_pickle(sys.argv[1]); TO = json.load(open(sys.argv[2]))['tasks']
    seeds = {x: (v['eq6_within_implementation']['seed_sd_median'], v['scale'] == 'points') for x, v in TO.items() if 'eq6_within_implementation' in v}
    c, T, seed_sd, seed_meas = prepare(L, seeds)
    if '--sim-only' in sys.argv:
        json.dump(simulate_check(c, T, seed_sd), open(sys.argv[4] + '.sim.json', 'w'), indent=1, default=float); sys.exit()
    mc = fit(c, len(T), seed_sd); per, diag = summarise(mc, T)
    # cross-check: the repo's per-group additive estimator (no pooling) on the same tasks
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    import dataset_benchmarking as db
    xp = db.cross_paper_reproducibility(c.rename(columns={'xtask': 'group', 'paper_key': 'paper', 'family': 'model'})[['group', 'paper', 'model', 'y']], min_shared=3, min_df=3)
    xp = pd.DataFrame(xp) if not isinstance(xp, pd.DataFrame) else xp
    task_sd = c.groupby('t').y.std(ddof=1)
    for i, x in enumerate(T):   # back to the task's own units (metric points or log-error units) for plotting
        per[x]['tau_units'] = per[x]['tau_std'] * float(task_sd[i]); per[x]['omega_units'] = per[x]['omega_std'] * float(task_sd[i])
        per[x]['seed_units'] = float(seed_sd[i] * task_sd[i])
    for i, x in enumerate(T):
        g = c[c.t == i]; per[x].update({'dataset': x.split('|')[0], 'papers': int(g.paper_key.nunique()), 'families': int(g.family.nunique()),
                                         'replicated_families': int((g.groupby('family').paper_key.nunique() >= 2).sum()), 'seed_sd_measured': bool(seed_meas[i])})
    S = pd.DataFrame(per).T
    out = {'model': 'joint multilevel, NUTS 4x1000', 'diagnostics': diag, 'tasks': per}
    pub = {'n_tasks': len(T), 'n_datasets': int(S.dataset.nunique()), 'diagnostics': diag,
           'score_median': float(S.score.astype(float).median()), 'score_iqr': [float(S.score.astype(float).quantile(.25)), float(S.score.astype(float).quantile(.75))],
           'share_lo90_ge_0_5': float((S.score90.map(lambda v: v[0]) >= 0.5).mean()), 'median_width90': float(S.score90.map(lambda v: v[1] - v[0]).median()),
           'omega_over_tau_median': float(S.omega_over_tau.astype(float).median())}
    if len(xp) and 'reproducibility' in xp:
        m = S.join(xp.set_index('group')[['reproducibility']], how='inner')
        from scipy.stats import spearmanr
        pub['crosscheck_additive_unpooled'] = {'n': int(len(m)), 'median_additive': float(m.reproducibility.median()), 'median_multilevel_same_tasks': float(m.score.astype(float).median()),
                                               'spearman': float(spearmanr(m.score.astype(float), m.reproducibility).statistic) if len(m) > 3 else None}
    if '--sim' in sys.argv: pub['simulation_check'] = simulate_check(c, T, seed_sd)
    json.dump(out, open(sys.argv[3], 'w'), indent=1, default=float); json.dump(pub, open(sys.argv[4], 'w'), indent=1, default=float)
    print(json.dumps(pub, indent=1, default=float))
