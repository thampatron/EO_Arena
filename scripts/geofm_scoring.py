"""GeoFM benchmark scoring: bottom-up evaluation of benchmark tasks.

Implements the scoring note "GeoFM Benchmark Scoring" (S. Wang, Oct 2026):

  y_mt = mu_t + lambda_t' theta_m + eta_mt                      (latent-factor regression, Eq. 9)
  tau2_obs_t = Var_m(y_mt)                                       (observed model separation, Eq. 10)
  tau2_t = tau2_obs_t - sigma2_t                                 (stable between-model variance, Eq. 3)
  EDI_t = tau2_t / sigma2_t                                      (effective discriminative information, Eq. 4)
  Score_t = EDI_t / (1 + EDI_t) = tau2_t / (tau2_t + sigma2_t)   (bounded dataset score, Eq. 6)
  Unexplained_t = Psi_tt / tau2_t                                (stable variation not captured by the factors, Eq. 5)
  V(A) = log det(Sigma_theta^-1 + Lambda_A' C_A^-1 Lambda_A)     (information a portfolio gives about theta, Eq. 8)

A *task* is one dataset-evaluation-protocol bundle: here one paper's comparison table on one benchmark id,
protocol, metric and training fraction (the paper is the finest available proxy for decoder, split and
implementation, which the workbook does not record separately).  sigma2_t is the replicate-level noise of a
single evaluation; it is identified only where papers print a seed/run standard deviation (mean +/- sd).
Where they do not, the score is marked *provisional* and uses a plug-in noise estimate.

The latent factors are fit by alternating ridge least squares on the sparse model x task matrix, after
standardising each task by its observed spread (so every task contributes equally and lambda_t is in
within-task SD units).  K is chosen by held-out cell cross-validation, as in the note.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from dataclasses import dataclass, field

# ----------------------------------------------------------------------------- latent-factor fit
@dataclass
class LatentFit:
    K: int
    models: list                 # model ids (rows)
    tasks: list                  # task ids (cols)
    theta: np.ndarray            # M x K, whitened so Cov(theta) = I over models
    lam: np.ndarray              # T x K loadings, in within-task SD units
    mu: np.ndarray               # T task means (standardised units, ~0)
    r2: np.ndarray               # T share of observed within-task variance explained by lambda' theta
    resid_var: np.ndarray        # T residual variance (standardised units)
    n_iter: int = 0
    cv: dict = field(default_factory=dict)


def _objective(Y, mask, mu, lam, theta, ridge_l, ridge_t):
    pred = mu[None, :] + (theta @ lam.T if lam.shape[1] else 0)
    return float(((Y - pred) ** 2)[mask].sum() + ridge_l * (lam ** 2).sum() + ridge_t * (theta ** 2).sum())


def _als_once(Y, mask, K, ridge_l, ridge_t, n_iter, tol, theta0):
    """Alternating ridge least squares on a FIXED objective (monotone): sum_obs (y - mu_t - lam_t.theta_m)^2
    + ridge_l ||lam||^2 + ridge_t ||theta||^2.  Batched solves; no rescaling inside the loop."""
    M, T = Y.shape; W = mask.astype(float); WY = W * Y
    theta = theta0.copy(); prev = np.inf; it = 0
    Pl = np.diag([0.0] + [ridge_l] * K); Pt = ridge_t * np.eye(K)
    for it in range(1, n_iter + 1):
        X = np.c_[np.ones(M), theta]                                   # M x (K+1)
        A = np.einsum('mt,mi,mj->tij', W, X, X) + Pl                   # T x (K+1) x (K+1)
        b = np.einsum('mt,mi->ti', WY, X)
        coef = np.linalg.solve(A, b[..., None])[..., 0]
        mu = coef[:, 0]; lam = coef[:, 1:]
        R = WY - W * mu[None, :]
        A2 = np.einsum('mt,ti,tj->mij', W, lam, lam) + Pt              # M x K x K
        b2 = R @ lam
        theta = np.linalg.solve(A2, b2[..., None])[..., 0]
        obj = _objective(Y, mask, mu, lam, theta, ridge_l, ridge_t)
        if prev - obj < tol * max(obj, 1e-12): break
        prev = obj
    return mu, lam, theta, it, obj


def _als(Y: np.ndarray, mask: np.ndarray, K: int, ridge_l: float = 1.0, ridge_t: float = 1.0,
         n_iter: int = 300, seed: int = 0, tol: float = 1e-7, n_restarts: int = 4):
    """Regularised low-rank fit Y[m,t] ~ mu_t + lam_t.theta_m on observed cells.  Several starts (an SVD of
    the task-centred, zero-filled matrix plus random starts); the lowest objective is kept.  theta is then
    whitened so Cov(theta) = I over models (identifiability convention), with the scale pushed into lam."""
    M, T = Y.shape
    mu = np.array([Y[mask[:, t], t].mean() if mask[:, t].any() else 0.0 for t in range(T)])
    if K == 0:
        return mu, np.zeros((T, 0)), np.zeros((M, 0)), 0
    rng = np.random.default_rng(seed)
    R0 = np.where(mask, Y - mu[None, :], 0.0)
    U, S, _ = np.linalg.svd(R0, full_matrices=False)
    starts = [U[:, :K] * S[:K] * (mask.size / max(mask.sum(), 1)) ** 0.5]
    starts += [rng.normal(size=(M, K)) * 0.3 for _ in range(n_restarts)]
    best = None
    for th0 in starts:
        res = _als_once(Y, mask, K, ridge_l, ridge_t, n_iter, tol, th0)
        if best is None or res[4] < best[4]: best = res
    mu, lam, theta, it, _ = best
    th = theta - theta.mean(0)
    Lc = np.linalg.cholesky(np.cov(th, rowvar=False).reshape(K, K) + 1e-9 * np.eye(K))
    theta = th @ np.linalg.inv(Lc).T; lam = lam @ Lc
    return mu, lam, theta, it


def fit_latent(Y: np.ndarray, mask: np.ndarray, K: int, models, tasks, **kw) -> LatentFit:
    mu, lam, theta, it = _als(Y, mask, K, **kw)
    pred = np.broadcast_to(mu[None, :], Y.shape) + (theta @ lam.T if K else 0)
    r2 = np.zeros(len(tasks)); rv = np.zeros(len(tasks))
    for t in range(len(tasks)):
        idx = mask[:, t]; y = Y[idx, t]
        if idx.sum() < 2: r2[t] = np.nan; rv[t] = np.nan; continue
        res = y - (pred[idx, t] if K else mu[t])
        rv[t] = res.var(ddof=0)
        r2[t] = max(0.0, 1 - rv[t] / max(y.var(ddof=0), 1e-12))
    return LatentFit(K, list(models), list(tasks), theta, lam, mu, r2, rv, it)


def cross_validate_K(Y, mask, Ks=(0, 1, 2, 3, 4, 5, 6), folds=5, seed=0, min_keep=4, **kw):
    """Hold out observed cells (only from tasks that keep >= min_keep models), refit, score predictions.
    Returns per-K mean/SE of (a) RMSE in within-task SD units and (b) pairwise ranking accuracy among
    held-out cells of the same task."""
    rng = np.random.default_rng(seed)
    cells = np.argwhere(mask)
    per_task = mask.sum(0)
    # only cells whose task has slack to lose some models
    eligible = np.array([per_task[t] > min_keep for _, t in cells])
    cand = cells[eligible]; rng.shuffle(cand)
    fold_id = np.arange(len(cand)) % folds
    out = {}
    for K in Ks:
        rmse, pra = [], []
        for f in range(folds):
            held = cand[fold_id == f]
            m2 = mask.copy(); m2[held[:, 0], held[:, 1]] = False
            # guard: never drop a task below min_keep
            bad = m2.sum(0) < min_keep
            if bad.any():
                keep = ~bad[held[:, 1]]; m2[held[~keep, 0], held[~keep, 1]] = True; held = held[keep]
            mu, lam, theta, _ = _als(Y, m2, K, seed=seed + f, **kw)
            pred = np.broadcast_to(mu[None, :], Y.shape) + (theta @ lam.T if K else 0)
            err = Y[held[:, 0], held[:, 1]] - pred[held[:, 0], held[:, 1]]
            rmse.append(np.sqrt(np.mean(err ** 2)))
            # pairwise accuracy within task
            ok = tot = 0
            df = pd.DataFrame({'t': held[:, 1], 'y': Y[held[:, 0], held[:, 1]], 'p': pred[held[:, 0], held[:, 1]]})
            for _, g in df.groupby('t'):
                if len(g) < 2: continue
                y = g.y.values; p = g.p.values
                for i in range(len(g)):
                    for j in range(i + 1, len(g)):
                        if y[i] == y[j]: continue
                        tot += 1; ok += ((y[i] - y[j]) * (p[i] - p[j]) > 0)
            pra.append(ok / tot if tot else np.nan)
        rmse = np.array(rmse); pra = np.array(pra)
        out[K] = dict(rmse=float(rmse.mean()), rmse_se=float(rmse.std(ddof=1) / np.sqrt(folds)),
                      pair_acc=float(np.nanmean(pra)), pair_acc_se=float(np.nanstd(pra, ddof=1) / np.sqrt(folds)),
                      n_heldout=int(len(cand)))
    return out


def select_K(cv: dict, stability: dict | None = None, min_stability: float = 0.5) -> int:
    """Smallest K whose held-out RMSE is within one SE of the best K (one-SE rule), stepped down until the
    task geometry is stable under bootstrap resampling of models (stability[K] >= min_stability)."""
    best = min(cv, key=lambda k: cv[k]['rmse'])
    thr = cv[best]['rmse'] + cv[best]['rmse_se']
    k = next((k for k in sorted(cv) if cv[k]['rmse'] <= thr), best)
    if stability:
        while k > 0 and (stability.get(k) is None or stability[k] < min_stability): k -= 1
    return k


def geometry_stability(Y, mask, K, lam0, n_boot=20, min_models=4, seed=0, **kw):
    """Bootstrap models, refit with K factors, Procrustes-align the loadings to lam0 and correlate.
    Returns the mean correlation over bootstraps (1 = identical task geometry, 0 = unrelated)."""
    if K == 0: return 1.0
    rng = np.random.default_rng(seed); out = []
    for b in range(n_boot):
        idx = rng.integers(0, Y.shape[0], Y.shape[0]); m2 = mask[idx]; ok = m2.sum(0) >= min_models
        if ok.sum() < 10: continue
        _, lam, _, _ = _als(Y[idx][:, ok], m2[:, ok], K, seed=seed + b + 1, **kw)
        A = lam0[ok]
        U, _, Vt = np.linalg.svd(lam.T @ A); R = U @ Vt          # orthogonal Procrustes: lam R ~ A
        out.append(np.corrcoef((lam @ R).ravel(), A.ravel())[0, 1])
    return float(np.nanmean(out)) if out else None


# ----------------------------------------------------------------------------- task- and dataset-level scores
def task_scores(tau2_obs: float, sigma2: float | None):
    """Eq. 3-6 from observed single-replicate dispersion and replicate noise."""
    if sigma2 is None or not np.isfinite(sigma2) or tau2_obs is None or not np.isfinite(tau2_obs):
        return dict(tau2=None, edi=None, score=None)
    tau2 = max(tau2_obs - sigma2, 0.0)
    if sigma2 <= 0:
        return dict(tau2=tau2, edi=None, score=1.0 if tau2 > 0 else None)
    edi = tau2 / sigma2
    return dict(tau2=tau2, edi=edi, score=edi / (1 + edi))


def portfolio_information(lam: np.ndarray, c: np.ndarray, rows: np.ndarray, K: int) -> float:
    """V(A) = log det(I + Lambda_A' C_A^-1 Lambda_A), Sigma_theta = I (Eq. 8)."""
    if K == 0 or len(rows) == 0: return 0.0
    L = lam[rows]; w = 1.0 / c[rows]
    return float(np.linalg.slogdet(np.eye(K) + (L * w[:, None]).T @ L)[1])


def shapley_information(groups: dict, lam: np.ndarray, c: np.ndarray, K: int, n_perm: int = 300, seed: int = 0):
    """Monte-Carlo Shapley contribution of each group (dataset) of tasks to V(all) (Eq. 8)."""
    names = list(groups); rng = np.random.default_rng(seed)
    contrib = {n: 0.0 for n in names}
    if K == 0: return contrib
    for _ in range(n_perm):
        order = rng.permutation(len(names)); cur = np.zeros(0, dtype=int); v_prev = 0.0
        for i in order:
            cur = np.r_[cur, groups[names[i]]]
            v = portfolio_information(lam, c, cur, K)
            contrib[names[i]] += v - v_prev; v_prev = v
    return {n: v / n_perm for n, v in contrib.items()}
