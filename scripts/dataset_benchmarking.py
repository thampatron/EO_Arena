"""Dataset-level benchmarking analysis for the GeoFM evidence table.

Follows "GeoFM Benchmark Scoring" (S. Wang, Oct 2026). The object of study is the *dataset* (under a protocol): what it
measures, how much it overlaps with other datasets, and how reproducibly it separates GeoFMs. Model vectors theta_m are
nuisance parameters here, used only to place tasks in a common capability space; nothing in this module ranks models.

Three pieces, each tied to the note:

1. Structured-loading latent-factor regression (note Eq. 9 with Eq. 11/12):
       y_mt = mu_t + lambda_t' theta_m + eta_mt,   lambda_t = sum_g B_g[x_g(t)] + u_t
   where g ranges over task metadata (dataset, protocol family, sensor, ...). Each block is ridge-shrunk toward zero, so
   the data decide how much of a task's position is shared with other tasks of the same dataset (or sensor, ...), and u_t
   keeps the task-specific remainder. Metadata explains/regularises the geometry; it does not define it in advance.

2. Leave-one-paper-out prediction of within-task orderings. Hold out every task a paper contributes, predict its model
   ordering from the dataset-level loading (and other blocks) learned from *other papers*, and score rank agreement.
   This tests, out of sample, whether "what dataset d measures" transfers across research groups. Rank metrics are
   invariant to mu_t and to the task's scale, so the test does not depend on the metric transform.

3. Cross-paper reproducibility of a dataset-protocol: where several papers report the same dataset, protocol family and
   metric on overlapping models, fit y_mp = a_p + b_m + e on those cells. Var(e) is the disagreement between independent
   implementations about the same model, an *upper bound* on single-evaluation noise sigma^2_t (it adds decoder, split
   and implementation differences to seed noise). It is labelled as such and never presented as seed noise.

Rotation-invariant summaries only (note, "Interpreting task latent factors"): dataset-dataset similarity
cos(lambda_d, lambda_e) under Cov(theta) = I, and shares of variance; never claims about individual axes.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, kendalltau


# ============================================================================ 1. structured-loading fit
@dataclass
class StructuredFit:
    K: int
    mu: np.ndarray                      # (T,)
    theta: np.ndarray                   # (M, K), Cov(theta)=I over models after whitening
    B: dict                             # group name -> (n_levels, K) block loadings
    U: np.ndarray                       # (T, K) task-specific loadings
    groups: dict                        # group name -> (T,) int level index (-1 = no level)
    obj: float = np.nan
    n_iter: int = 0
    meta: dict = field(default_factory=dict)
    scale: np.ndarray | None = None     # (T,) residual SD per task when fitted in noise units (fit_heteroskedastic)
    C: np.ndarray | None = None         # (M, P) paper x model offsets (implementation effects), if fitted
    paper_idx: np.ndarray | None = None # (T,) paper index of each task, for C

    def lam(self, include_u: bool = True) -> np.ndarray:
        L = self.U.copy() if include_u else np.zeros_like(self.U)
        for g, idx in self.groups.items():
            ok = idx >= 0
            L[ok] += self.B[g][idx[ok]]
        return L

    def predict(self) -> np.ndarray:
        """Predictions on the original (points) scale."""
        P = self.mu[None, :] + self.theta @ self.lam().T
        if self.C is not None:
            P = P + self.C[:, self.paper_idx]
        return P if self.scale is None else P * self.scale[None, :]


def board_start(Y, mask, K):
    """Start for theta: column 1 = each model's mean within-task z-score (a naive leaderboard, the general factor);
    further columns = leading singular vectors of the task-standardised residual after removing it. Without this start,
    the SVD of the zero-filled matrix can land the K=1 fit in a local optimum whose factor is not the general one."""
    M, T = Y.shape
    Z = np.zeros((M, T)); W = np.zeros((M, T))
    for t in range(T):
        o = mask[:, t]
        if o.sum() > 1:
            v = Y[o, t]; sd = v.std(ddof=1)
            if sd > 0: Z[o, t] = (v - v.mean()) / sd; W[o, t] = 1.0
    cnt = W.sum(1); g = np.where(cnt > 0, Z.sum(1) / np.maximum(cnt, 1), 0.0)
    g = (g - g.mean()) / (g.std() + 1e-12)
    cols = [g]
    if K > 1:
        lam1 = (Z * g[:, None]).sum(0) / np.maximum((W * g[:, None] ** 2).sum(0), 1e-12)
        R = np.where(W > 0, Z - g[:, None] * lam1[None, :], 0.0)
        U, S, _ = np.linalg.svd(R, full_matrices=False)
        for k in range(K - 1):
            u = U[:, k] * S[k]; cols.append(u / (u.std() + 1e-12))
    return np.column_stack(cols)


def svd_start(Y, mask, mu0, K):
    R0 = np.where(mask, Y - mu0[None, :], 0.0)
    Us, Ss, _ = np.linalg.svd(R0, full_matrices=False)
    return Us[:, :K] * Ss[:K] / np.sqrt(max(mask.mean(), 1e-3) * Y.shape[1])


def _group_parts(B, groups, T, K, skip=None):
    out = np.zeros((T, K))
    for g, idx in groups.items():
        if g == skip:
            continue
        ok = idx >= 0
        out[ok] += B[g][idx[ok]]
    return out


def fit_structured(Y, mask, K, groups: dict | None = None, ridge_u=10.0, ridge_g: dict | None = None, ridge_theta=10.0,
                   n_iter=400, tol=1e-7, seed=0, n_restarts=4, theta_init=None, task_weight=None, paper=None, ridge_pm=3.0, warm=False) -> StructuredFit:
    """Block-coordinate ridge (weighted) least squares on observed cells. Every block update solves its exact ridge
    subproblem, so the penalised objective decreases monotonically. groups=None or {} gives the free-loading model (the
    current EOArena fit). task_weight (T,) multiplies each task's squared residuals: pass 1/psi_t for the note's
    heteroskedastic residual variance (Eq. 1: eps ~ N(0, sigma_t^2)); see fit_heteroskedastic.
    paper (T,) int, optional: adds a ridge-shrunk offset c_{m,p} shared by all tasks a paper p reports for model m — the
    implementation effect of how that paper trained/evaluated m (note: 'differences in evaluation protocol' confound eta).
    Without it, such paper x model structure is absorbed by extra latent factors and inflates K."""
    groups = {g: np.asarray(v, int) for g, v in (groups or {}).items()}
    ridge_g = {g: (ridge_g or {}).get(g, 1.0) for g in groups}
    M, T = Y.shape
    w_t = np.ones(Y.shape[1]) if task_weight is None else np.asarray(task_weight, float)
    W = mask.astype(float) * w_t[None, :]
    WY = W * np.where(mask, Y, 0.0)
    nlev = {g: int(idx.max()) + 1 if (idx >= 0).any() else 0 for g, idx in groups.items()}
    rng = np.random.default_rng(seed)
    mu0 = np.array([Y[mask[:, t], t].mean() if mask[:, t].any() else 0.0 for t in range(T)])
    pidx = None if paper is None else np.asarray(paper, int)
    if pidx is not None and (pidx < 0).all():
        pidx = None                                       # no paper carries an offset
    nP = 0 if pidx is None else int(pidx.max()) + 2       # last column = 'no offset' dummy, held at 0
    if pidx is not None:
        pidx = np.where(pidx < 0, nP - 1, pidx)
    def c_update(R):
        """Exact ridge update of the paper x model offsets given residuals R (weighted, observed cells)."""
        num = np.zeros((M, nP)); den = np.zeros((M, nP))
        np.add.at(num.T, pidx, R.T); np.add.at(den.T, pidx, W.T)
        C_ = num / (den + ridge_pm); C_[:, -1] = 0.0
        return C_
    if K == 0:
        f = StructuredFit(0, mu0, np.zeros((M, 0)), {g: np.zeros((n, 0)) for g, n in nlev.items()}, np.zeros((T, 0)), groups)
        if pidx is not None:
            C = np.zeros((M, nP)); mu = mu0
            for _ in range(50):
                C = c_update(WY - W * mu[None, :])
                Ce = C[:, pidx]
                mu = np.array([((WY[:, t] - W[:, t] * Ce[:, t]).sum() / max(W[:, t].sum(), 1e-12)) for t in range(T)])
            f.mu, f.C, f.paper_idx = mu, C, pidx
        return f

    def objective(mu, th, B, U, C):
        L = U + _group_parts(B, groups, T, K)
        P = mu[None, :] + th @ L.T + (C[:, pidx] if C is not None else 0)
        pen = ridge_u * (U ** 2).sum() + ridge_theta * (th ** 2).sum() + sum(ridge_g[g] * (B[g] ** 2).sum() for g in groups)
        pen += ridge_pm * (C ** 2).sum() if C is not None else 0
        return float((((Y - P) ** 2) * W).sum() + pen)

    starts = [theta_init] if theta_init is not None else []
    if not (warm and theta_init is not None):             # warm: refine from theta_init only (later reweighting rounds)
        starts += [board_start(Y, mask, K), svd_start(Y, mask, mu0, K)]
        starts += [rng.normal(size=(M, K)) * 0.5 for _ in range(n_restarts)]
    best = None
    for th in starts:
        th = th.copy(); mu = mu0.copy(); U = np.zeros((T, K)); B = {g: np.zeros((n, K)) for g, n in nlev.items()}
        C = None if pidx is None else np.zeros((M, nP))
        prev = np.inf; it = 0
        for it in range(1, n_iter + 1):
            WYc = WY if C is None else WY - W * C[:, pidx]                       # data net of implementation offsets
            # (a) mu_t and u_t jointly, with the group parts as a fixed offset
            off = _group_parts(B, groups, T, K)
            X = np.c_[np.ones(M), th]                                            # M x (K+1)
            A = np.einsum('mt,mi,mj->tij', W, X, X) + np.diag([1e-8] + [ridge_u] * K)[None]
            rhs = np.einsum('mt,mi->ti', WYc - W * (th @ off.T), X)
            coef = np.linalg.solve(A, rhs[..., None])[..., 0]
            mu, U = coef[:, 0], coef[:, 1:]
            # (b) each group's block loadings
            G = np.einsum('mt,mi,mj->tij', W, th, th)                            # per-task Gram, T x K x K
            for g, idx in groups.items():
                if nlev[g] == 0:
                    continue
                rest = U + _group_parts(B, groups, T, K, skip=g)
                Rt = WYc - W * (mu[None, :] + th @ rest.T)                        # residual for g, observed cells
                b = Rt.T @ th                                                    # T x K
                ok = idx >= 0
                A_g = np.zeros((nlev[g], K, K)); b_g = np.zeros((nlev[g], K))
                np.add.at(A_g, idx[ok], G[ok]); np.add.at(b_g, idx[ok], b[ok])
                A_g += ridge_g[g] * np.eye(K)[None]
                B[g] = np.linalg.solve(A_g, b_g[..., None])[..., 0]
            # (c) theta
            L = U + _group_parts(B, groups, T, K)
            A2 = np.einsum('mt,ti,tj->mij', W, L, L) + ridge_theta * np.eye(K)[None]
            b2 = (WYc - W * mu[None, :]) @ L
            th = np.linalg.solve(A2, b2[..., None])[..., 0]
            # (d) paper x model offsets
            if C is not None:
                C = c_update(WY - W * (mu[None, :] + th @ L.T))
            obj = objective(mu, th, B, U, C)
            if prev - obj < tol * max(obj, 1e-12):
                break
            prev = obj
        if best is None or obj < best[0]:
            best = (obj, mu, th, B, U, it, C)
    obj, mu, th, B, U, it, C = best
    # identifiability convention: centre and whiten theta over models; push the transform into the loadings
    c = th.mean(0); mu = mu + (U + _group_parts(B, groups, T, K)) @ c; th = th - c
    Lc = np.linalg.cholesky(np.cov(th, rowvar=False).reshape(K, K) + 1e-9 * np.eye(K))
    th = th @ np.linalg.inv(Lc).T
    U = U @ Lc; B = {g: v @ Lc for g, v in B.items()}
    return StructuredFit(K, mu, th, B, U, groups, obj, it, C=C, paper_idx=pidx)


def fit_heteroskedastic(Y, mask, K, groups=None, n_rounds=3, prior_n=3.0, prior_group=None, **kw):
    """Fit with a residual variance per task, psi_t (note Eq. 1/9: each task has its own noise scale). Each task is
    divided by its current residual SD sqrt(psi_t) and the structured model is fitted in these noise units; psi_t is then
    re-estimated on the original scale, three rounds. Unlike standardising by the observed spread of the models a paper
    chose, this keeps between-model signal: |lambda_t|^2 is the shared-capability variance of task t in units of its
    residual variance (an EDI-like signal-to-residual ratio), comparable across tasks and metrics, and the ridge has
    the same meaning for every task. psi_t is the df-corrected residual mean square shrunk toward the median over tasks
    with prior_n pseudo-observations, so 4-model comparisons do not get extreme scales. NB with single reported scores
    psi_t = Psi_tt + sigma_t^2 (stable task-specific interaction plus evaluation noise, not separable: note Eq. 9).
    prior_group (T,) ints: tasks on different metric scales (points vs log-error) get separate pooled priors.
    Returns (fit, psi); fit.scale = sqrt(psi) and fit.predict() is on the original scale."""
    T = Y.shape[1]; fit = None
    n = mask.sum(0)
    grp = np.zeros(T, int) if prior_group is None else np.asarray(prior_group, int)
    sd0 = np.array([Y[mask[:, t], t].std(ddof=1) if n[t] > 1 else np.nan for t in range(T)])
    psi = np.ones(T)
    for gg in np.unique(grp):                              # start: one pooled level per metric family
        psi[grp == gg] = np.nanmedian(sd0[grp == gg]) ** 2
    th_prev = None
    for rnd_ in range(n_rounds):
        s = np.sqrt(psi)
        if rnd_ == 0 or th_prev is None:
            fit = fit_structured(np.where(mask, Y / s[None, :], 0.0), mask, K, groups, **kw)
        else:
            kw_w = {k_: v_ for k_, v_ in kw.items() if k_ not in ("theta_init", "warm")}
            fit = fit_structured(np.where(mask, Y / s[None, :], 0.0), mask, K, groups, theta_init=th_prev, warm=True, **kw_w)
        th_prev = fit.theta if K else None
        fit.scale = s
        E = np.where(mask, Y - fit.predict(), 0.0)
        dof = np.maximum(n - K - 1, 1.0)
        raw = np.maximum((E ** 2).sum(0) / dof, 1e-6)
        # hierarchical prior on log psi: shrink each task's log residual variance toward the pooled mean, with
        # prior_n pseudo-degrees of freedom; the target no longer depends on the task's own observed spread
        lr = np.log(raw); ok = n > K + 2; m0 = np.zeros(T)
        for gg in np.unique(grp):
            sel = grp == gg; o = sel & ok
            m0[sel] = np.average(lr[o], weights=dof[o]) if o.any() else lr[sel].mean()
        psi = np.exp((dof * lr + prior_n * m0) / (dof + prior_n))
    s_new = np.sqrt(psi)                                  # express the final fit in the final psi's units
    kw_w = {k_: v_ for k_, v_ in kw.items() if k_ not in ("theta_init", "warm")}
    fit = fit_structured(np.where(mask, Y / s_new[None, :], 0.0), mask, K, groups, theta_init=th_prev, warm=th_prev is not None, **kw_w); fit.scale = s_new
    return fit, psi


# ============================================================================ 2. out-of-sample tests
def _rank_scores(y, p):
    """Spearman rho and pairwise ordering accuracy (ties in y skipped) for one task."""
    if len(y) < 3 or np.ptp(y) == 0:
        return np.nan, np.nan, 0
    if np.ptp(p) == 0:
        return 0.0, 0.5, 0
    rho = spearmanr(y, p).statistic
    d_y = np.sign(y[:, None] - y[None, :]); d_p = np.sign(p[:, None] - p[None, :])
    iu = np.triu_indices(len(y), 1); keep = d_y[iu] != 0
    hit = np.where(d_p[iu][keep] == 0, 0.5, (d_y[iu][keep] == d_p[iu][keep]).astype(float))
    acc = float(hit.mean()) if keep.any() else np.nan
    return float(rho), acc, int(keep.sum())


def leave_one_paper_out(Y, mask, task_paper, K, groups, min_models=4, min_theta_tasks=3, hetero=True, anchor_splits=10, anchor_min=6, anchor_ridge=1.0, **kw):
    """For each paper: drop all its tasks, refit, predict each dropped task's model ordering from lambda = sum of its
    learned group blocks (u_t is unknown for an unseen task, so it is 0), for models that keep >= min_theta_tasks
    observed tasks elsewhere. Returns per-task rows: paper, task index, n models scored, Spearman, pairwise accuracy.
    The 'global' baseline orders models by their mean predicted score over all training tasks (a one-ranking-fits-all
    predictor), so  structured - global  is what dataset/protocol/sensor identity adds.

    ANCHORED test (does not depend on block-predicted loadings or their sign): for held-out tasks with >= anchor_min
    eligible models, split the models into halves anchor_splits times; estimate the task's loading on theta (ridge
    regression with intercept, theta from the fit without this paper) from half A and predict the order of half B
    (rho_anch); the one-ranking comparator does the same with the naive leaderboard as a 1-d predictor (rho_anch_board),
    and rho_half_board scores the plain leaderboard (sign known a priori) on the same half B: rho_anch - rho_half_board
    is a test of K-dimensional capability against a single ranking that favours the ranking. rho_anch_board re-estimates
    the leaderboard's sign from half A and is handicapped (kept for reference only)."""
    task_paper = np.asarray(task_paper)
    rows = []
    arng = np.random.default_rng(12345)
    def _anchored(Xf, y, splits):
        out = []
        for a, b in splits:
            Xa = np.c_[np.ones(len(a)), Xf[a]]
            P = np.eye(Xa.shape[1]) * anchor_ridge; P[0, 0] = 1e-8
            beta = np.linalg.solve(Xa.T @ Xa + P, Xa.T @ y[a])
            pb = np.c_[np.ones(len(b)), Xf[b]] @ beta
            r_, _, _ = _rank_scores(y[b], pb)
            if np.isfinite(r_): out.append(r_)
        return float(np.mean(out)) if out else np.nan
    for p in np.unique(task_paper):
        hold = task_paper == p
        m2 = mask.copy(); m2[:, hold] = False
        if m2[:, ~hold].sum() == 0:
            continue
        fit = fit_heteroskedastic(Y, m2, K, groups, **kw)[0] if hetero else fit_structured(Y, m2, K, groups, **kw)
        L = fit.lam(include_u=False)
        gen = (fit.mu[None, ~hold] + fit.theta @ fit.lam()[~hold].T).mean(1)   # global "general ability" score
        Z = np.full(Y.shape, np.nan)
        for t in np.where(~hold)[0]:
            o = m2[:, t]
            if o.sum() > 1 and Y[o, t].std() > 0: Z[o, t] = (Y[o, t] - Y[o, t].mean()) / Y[o, t].std(ddof=1)
        board = np.nanmean(np.where(np.isnan(Z), np.nan, Z), axis=1)        # K-independent one-ranking baseline
        ntr = m2.sum(1)
        for t in np.where(hold)[0]:
            ms = np.where(mask[:, t] & (ntr >= min_theta_tasks))[0]
            if len(ms) < min_models:
                continue
            y = Y[ms, t]
            has_group = any(groups[g][t] >= 0 and np.abs(fit.B[g][groups[g][t]]).sum() > 0 for g in groups) if groups else False
            ps = fit.theta[ms] @ L[t] if has_group else np.full(len(ms), np.nan)
            r_s, a_s, n_pairs = _rank_scores(y, ps) if has_group else (np.nan, np.nan, 0)
            r_g, a_g, _ = _rank_scores(y, gen[ms])
            r_b, a_b, _ = _rank_scores(y, np.nan_to_num(board[ms]))
            ra = rab = np.nan
            rhb = np.nan
            if len(ms) >= anchor_min and np.ptp(y) > 0 and fit.K:
                n_ = len(ms); h_ = n_ // 2; spl = []
                for _ in range(anchor_splits):
                    perm = arng.permutation(n_); spl.append((perm[:h_], perm[h_:]))
                ra = _anchored(fit.theta[ms], y, spl)
                bz = np.nan_to_num(board[ms]); bz = (bz - bz.mean()) / (bz.std() + 1e-12)
                rab = _anchored(bz[:, None], y, spl)                      # leaderboard with its sign re-estimated (handicapped)
                hb = [_rank_scores(y[b_], bz[b_])[0] for _, b_ in spl]; hb = [x_ for x_ in hb if np.isfinite(x_)]
                rhb = float(np.mean(hb)) if hb else np.nan                # plain leaderboard on the same half B (fair comparator)
            rows.append(dict(paper=p, task=int(t), n_models=len(ms), n_pairs=n_pairs, rho_struct=r_s, acc_struct=a_s, rho_global=r_g, acc_global=a_g,
                             rho_board=r_b, acc_board=a_b, rho_anch=ra, rho_anch_board=rab, rho_half_board=rhb))
    return pd.DataFrame(rows)


def heldout_cell_cv(Y, mask, K, groups, folds=5, min_keep=4, seed=0, hetero=True, sd_floor=0.5, **kw):
    """Held-out cell CV (as in the current pipeline) for the structured model; RMSE and within-task pairwise accuracy."""
    rng = np.random.default_rng(seed)
    cells = np.argwhere(mask); per_task = mask.sum(0)
    cand = cells[per_task[cells[:, 1]] > min_keep]; rng.shuffle(cand)
    fid = np.arange(len(cand)) % folds
    rmse, acc = [], []
    for f in range(folds):
        held = cand[fid == f]; m2 = mask.copy(); m2[held[:, 0], held[:, 1]] = False
        bad = m2.sum(0) < min_keep
        if bad.any():
            back = bad[held[:, 1]]; m2[held[back, 0], held[back, 1]] = True; held = held[~back]
        if hetero:
            fit, psi = fit_heteroskedastic(Y, m2, K, groups, seed=seed + f, **kw)
        else:
            fit = fit_structured(Y, m2, K, groups, seed=seed + f, **kw); psi = np.ones(Y.shape[1])
        P = fit.predict()
        sd_tr = np.array([Y[m2[:, t], t].std(ddof=1) if m2[:, t].sum() > 1 else np.nan for t in range(Y.shape[1])])
        sd_tr = np.maximum(sd_tr, sd_floor)                # near-tied comparisons would otherwise dominate the RMSE
        e = (Y[held[:, 0], held[:, 1]] - P[held[:, 0], held[:, 1]]) / sd_tr[held[:, 1]]
        rmse.append(float(np.sqrt(np.nanmean(e ** 2))))   # in units of the task's training-fold spread: same for every K
        df = pd.DataFrame({"t": held[:, 1], "y": Y[held[:, 0], held[:, 1]], "p": P[held[:, 0], held[:, 1]]})
        ok = tot = 0
        for _, g in df.groupby("t"):
            if len(g) < 2: continue
            dy = np.sign(g.y.values[:, None] - g.y.values[None, :]); dp = np.sign(g.p.values[:, None] - g.p.values[None, :])
            iu = np.triu_indices(len(g), 1); k = dy[iu] != 0
            ok += float(np.where(dp[iu][k] == 0, 0.5, (dy[iu][k] == dp[iu][k])).sum()); tot += int(k.sum())
        acc.append(ok / tot if tot else np.nan)
    return dict(rmse=float(np.mean(rmse)), rmse_se=float(np.std(rmse, ddof=1) / np.sqrt(folds)),
                pair_acc=float(np.nanmean(acc)), pair_acc_se=float(np.nanstd(acc, ddof=1) / np.sqrt(folds)), n_heldout=int(len(cand)))


def tau_pairs(Y, mask, min_shared=4):
    """Kendall tau between every pair of tasks over the GeoFMs both report (>= min_shared, non-constant)."""
    from scipy.stats import kendalltau
    T = Y.shape[1]; rows = []
    for i in range(T):
        for j in range(i + 1, T):
            sh = mask[:, i] & mask[:, j]
            if sh.sum() < min_shared: continue
            a, b = Y[sh, i], Y[sh, j]
            if np.ptp(a) == 0 or np.ptp(b) == 0: continue
            rows.append((i, j, kendalltau(a, b).statistic, int(sh.sum())))
    return pd.DataFrame(rows, columns=["i", "j", "tau", "n"])


def tau_contrasts(P, task_source, task_dataset, task_protocol, exclude_source_pairs=(), B=2000, seed=0):
    """Model-free test of dataset identity and of paper specificity from pairwise Kendall tau.
    Cell means of tau by (same/different dataset) x (same/different source); and two contrasts with 90% intervals from a
    cluster bootstrap over sources (each resampled source multiplies the weight of every pair it is part of):
      dataset_identity = tau(same dataset, different sources) - tau(different datasets, different sources): under one
        ranking plus task noise it is 0; > 0 means a dataset's model ordering carries over to other groups' evaluations.
        Also per dataset (each dataset as its own control: its cross-source same-dataset pairs vs its cross-source pairs
        with other datasets), weighted by its same-dataset pairs.
      paper_specificity = tau(different datasets, same source) - tau(different datasets, different sources).
    Computed on all pairs, on same-protocol-family pairs, and without source pairs flagged as possible shared codebases."""
    ts = np.asarray(task_source); td = np.asarray(task_dataset); tpf = np.asarray(task_protocol)
    src = sorted(set(ts)); si = {s_: k for k, s_ in enumerate(src)}
    P = P.copy()
    P["a"] = [si[ts[i]] for i in P.i]; P["b"] = [si[ts[j]] for j in P.j]
    P["same_src"] = P.a == P.b; P["same_ds"] = td[P.i.values] == td[P.j.values]; P["same_pf"] = tpf[P.i.values] == tpf[P.j.values]
    ex = {tuple(sorted(p)) for p in exclude_source_pairs}
    P["cb"] = [tuple(sorted((ts[i], ts[j]))) in ex for i, j in zip(P.i, P.j)]
    rng = np.random.default_rng(seed)
    def wmean(D, w, m):
        ww = w[D.a.values] * w[D.b.values] * m
        return np.average(D.tau.values, weights=ww) if ww.sum() > 0 else np.nan
    def c_identity(D, w):
        x = D[~D.same_src]; return wmean(x, w, x.same_ds.values) - wmean(x, w, ~x.same_ds.values)
    def c_identity_perds(D, w):
        x = D[~D.same_src]; ww = w[x.a.values] * w[x.b.values]; di = td[x.i.values]; dj = td[x.j.values]; out = []; W = []
        for d in set(di[x.same_ds.values]):
            same = x.same_ds.values & (di == d); inv = (~x.same_ds.values) & ((di == d) | (dj == d))
            if ww[same].sum() > 0 and ww[inv].sum() > 0:
                out.append(np.average(x.tau.values[same], weights=ww[same]) - np.average(x.tau.values[inv], weights=ww[inv])); W.append(ww[same].sum())
        return np.average(out, weights=W) if out else np.nan
    def c_paper(D, w):
        x = D[~D.same_ds]; return wmean(x, w, x.same_src.values) - wmean(x, w, ~x.same_src.values)
    def boot(fn, D):
        pt = fn(D, np.ones(len(src))); bs = []
        for _ in range(B):
            w = np.bincount(rng.integers(0, len(src), len(src)), minlength=len(src)).astype(float); v = fn(D, w)
            if np.isfinite(v): bs.append(v)
        return {"estimate": round(float(pt), 4), "ci90": [round(float(np.percentile(bs, 5)), 4), round(float(np.percentile(bs, 95)), 4)]}
    cells = P.groupby(["same_ds", "same_src"]).tau.agg(["mean", "size"]).reset_index()
    out = {"cells": [{"same_dataset": bool(r_.same_ds), "same_source": bool(r_.same_src), "mean_tau": round(float(r_["mean"]), 4), "pairs": int(r_["size"])} for _, r_ in cells.iterrows()],
           "median_shared_models": float(P.n.median()), "flagged_source_pairs": sorted(ex)}
    for name, D in (("all", P), ("same_protocol_family", P[P.same_pf]), ("excluding_flagged_source_pairs", P[~P.cb])):
        out[name] = {"dataset_identity": boot(c_identity, D), "dataset_identity_per_dataset": boot(c_identity_perds, D), "paper_specificity": boot(c_paper, D),
                     "cross_source_same_dataset_pairs": int((~D.same_src & D.same_ds).sum())}
    return out


def shared_codebase_pairs(Y, mask, task_source, keys, max_med_abs=1.0, min_cells=3):
    """Source pairs whose matched cells (same model and key, e.g. dataset x protocol family x fraction) differ by a median
    of <= max_med_abs: possibly the same evaluation code (not independent replications). keys: (T,) hashable per task."""
    rows = []
    for t in range(Y.shape[1]):
        for m in np.where(mask[:, t])[0]: rows.append((m, keys[t], task_source[t], Y[m, t]))
    C = pd.DataFrame(rows, columns=["m", "k", "s", "y"]).groupby(["m", "k", "s"]).y.mean().reset_index()
    M = C.merge(C, on=["m", "k"]); M = M[M.s_x < M.s_y]
    out = []
    for (a, b), x in M.groupby(["s_x", "s_y"]):
        if len(x) >= min_cells and np.median(np.abs(x.y_x - x.y_y)) <= max_med_abs: out.append((a, b, int(len(x)), round(float(np.median(np.abs(x.y_x - x.y_y))), 3)))
    return out


# ============================================================================ 3. dataset-level geometry
def dataset_loadings(fit: StructuredFit, task_dataset, mask=None):
    """Position of each dataset in capability space: the model-count-weighted mean of the FULL loadings lambda_t of its
    tasks (all metadata blocks + task part), so structured and free fits are summarised the same way. Returns
    (names, L_d, n_tasks)."""
    task_dataset = np.asarray(task_dataset)
    names = sorted(set(task_dataset) - {""})
    L = fit.lam(); w = mask.sum(0).astype(float) if mask is not None else np.ones(L.shape[0])
    Ld = np.array([np.average(L[task_dataset == n], axis=0, weights=w[task_dataset == n]) for n in names]) if fit.K else np.zeros((len(names), 0))
    return names, Ld, np.array([(task_dataset == n).sum() for n in names])


def similarity(Ld):
    """Rotation-invariant similarity of what two datasets measure: cosine of loadings under Cov(theta) = I, which equals
    the correlation of their predicted (noise-free) model scores across the evaluated GeoFM population."""
    n = np.linalg.norm(Ld, axis=1, keepdims=True)
    S = (Ld / np.maximum(n, 1e-12)) @ (Ld / np.maximum(n, 1e-12)).T
    return S


def metadata_association(Ld, labels, n_perm=2000, seed=0, direction_only=False):
    """Share of dataset-loading variance explained by a categorical label, against a permutation null that shuffles the
    label across DATASETS (the unit of analysis). Reports observed R^2, null mean, and p-value; the excess over the null
    is what should be read, since R^2 for a many-level factor is large by chance."""
    labels = np.asarray(labels).astype(str)
    keep = ~np.isin(labels, ["", "nan", "None"])                          # missing labels are missing, not a level
    Ld = np.asarray(Ld)[keep]; labels = labels[keep]
    if direction_only:                                                    # what a dataset measures, not how strongly
        Ld = Ld / np.maximum(np.linalg.norm(Ld, axis=1, keepdims=True), 1e-12)
    def r2(lab):
        tot = ((Ld - Ld.mean(0)) ** 2).sum()
        within = sum(((Ld[lab == l] - Ld[lab == l].mean(0)) ** 2).sum() for l in np.unique(lab))
        return 1 - within / max(tot, 1e-12)
    rng = np.random.default_rng(seed)
    obs = r2(labels); null = np.array([r2(rng.permutation(labels)) for _ in range(n_perm)])
    return dict(r2=float(obs), null_mean=float(null.mean()), null_p95=float(np.percentile(null, 95)),
                excess=float(obs - null.mean()), p_value=float((1 + (null >= obs).sum()) / (1 + n_perm)), n_levels=int(len(np.unique(labels))), n=int(len(labels)))


def communality_by_dataset(Y, mask, fit: StructuredFit, task_dataset):
    """For each dataset, share of within-task model variance captured by the shared factors (pooled over its tasks).
    Diagnostic, not a penalty (note Eq. 5): low values mean the dataset's model differences are not explained by the
    capabilities the rest of the evidence measures — a distinct capability, implementation effects, or noise."""
    P = fit.predict(); task_dataset = np.asarray(task_dataset); out = {}
    for n in sorted(set(task_dataset) - {""}):
        num = den = 0.0
        for t in np.where(task_dataset == n)[0]:
            o = mask[:, t]
            if o.sum() < 3: continue
            y = Y[o, t]; e = y - P[o, t]
            num += ((y - y.mean()) ** 2).sum() - (e ** 2).sum(); den += ((y - y.mean()) ** 2).sum()
        out[n] = float(np.clip(num / den, 0, 1)) if den > 0 else np.nan
    return out


def dataset_shapley(Ld, n_perm=500, seed=0):
    """Redundancy-adjusted contribution of each dataset to the information a suite gives about shared capabilities
    (note Eq. 8), with one entry per DATASET (its tasks pooled, so a dataset reported in 15 comparisons is not counted 15
    times): V(A) = log det(I + sum_{d in A} lambda_d lambda_d'), lambda_d in residual-SD units, Sigma_theta = I.
    Monte-Carlo Shapley over random orderings; returns (mean contribution, Monte-Carlo SE) per dataset."""
    rng = np.random.default_rng(seed); D, K = Ld.shape
    if K == 0: return np.zeros(D), np.zeros(D)
    C = np.zeros((n_perm, D))
    for b in range(n_perm):
        Mx = np.eye(K); prev = 0.0
        for d in rng.permutation(D):
            Mx = Mx + np.outer(Ld[d], Ld[d]); v = np.linalg.slogdet(Mx)[1]; C[b, d] = v - prev; prev = v
    return C.mean(0), C.std(0, ddof=1) / np.sqrt(n_perm)


# ============================================================================ 4. cross-paper reproducibility
def cross_paper_reproducibility(df, min_papers=2, min_shared=5, min_df=5, n_boot=500, seed=0):
    """df: one row per (group, paper, model) with columns group, paper, model, y — y on a common fixed scale within a
    group (same dataset, protocol family and metric). For each group with >= min_papers papers that each share
    >= min_shared models with another paper:
      - pairwise Kendall tau of model orderings between papers on their shared models (median over pairs),
      - additive fit y_mp = a_p + b_m + e on the connected cells; sigma2_xp = RSS / df_resid is the CROSS-IMPLEMENTATION
        DISAGREEMENT about the same model: implementation/protocol differences plus seed noise of a (mean of n seeds)
        published value. It is not seed noise, and it is not in general an upper bound on sigma2_t (a mean of n seeds
        carries sigma2_t / n),
      - tau2_b = Var_m(b_m) - mean sampling variance of b_m: stable between-model variance in the group,
      - reproducibility = tau2_b / (tau2_b + sigma2_xp): the share of between-model variance that independent groups
        agree on (Eq. 6 form, with cross-implementation disagreement in place of seed noise). Requires >= min_shared
        models seen by >= 2 papers and df_resid >= min_df. Bootstrap over models gives a 90% interval. Input must be free
        of reprinted (recited) values, which would count as perfect agreement."""
    rng = np.random.default_rng(seed); out = []
    for gname, g in df.groupby("group"):
        papers = g.paper.unique()
        if len(papers) < min_papers: continue
        sets = {p: set(g.model[g.paper == p]) for p in papers}
        taus = []
        for i, p in enumerate(papers):
            for q in papers[i + 1:]:
                sh = sorted(sets[p] & sets[q])
                if len(sh) >= min_shared:
                    a = g[g.paper == p].set_index("model").y.reindex(sh); b = g[g.paper == q].set_index("model").y.reindex(sh)
                    if a.nunique() > 1 and b.nunique() > 1: taus.append(kendalltau(a, b).statistic)
        keep_models = g.model.value_counts(); keep_models = keep_models[keep_models >= 2].index
        h = g[g.model.isin(keep_models)]
        if len(taus) == 0 or h.paper.nunique() < 2 or len(keep_models) < min_shared:
            continue
        def additive(h):
            P = sorted(h.paper.unique()); Ms = sorted(h.model.unique())
            pi = {p: i for i, p in enumerate(P)}; mi = {m: i for i, m in enumerate(Ms)}
            X = np.zeros((len(h), len(P) + len(Ms) - 1)); yv = h.y.values
            for r, (p, m) in enumerate(zip(h.paper, h.model)):
                X[r, pi[p]] = 1
                if mi[m] > 0: X[r, len(P) + mi[m] - 1] = 1
            coef, *_ = np.linalg.lstsq(X, yv, rcond=None); res = yv - X @ coef
            dfr = len(yv) - np.linalg.matrix_rank(X)
            if dfr <= 0: return None
            s2 = float((res ** 2).sum() / dfr)
            bm = np.r_[0.0, coef[len(P):]]
            n_m = h.model.map(h.model.value_counts()).groupby(h.model).first().reindex(Ms).values
            tau2 = max(float(np.var(bm, ddof=1) - s2 * np.mean(1.0 / n_m)), 0.0)
            return s2, tau2, dfr
        a = additive(h)
        if a is None: continue
        s2, tau2, dfr = a
        if dfr < min_df: continue
        boots = []
        Ms = np.array(sorted(h.model.unique()))
        for _ in range(n_boot):
            pick = rng.choice(Ms, len(Ms)); parts = []
            for k, m in enumerate(pick):
                x = h[h.model == m].copy(); x["model"] = f"{m}#{k}"; parts.append(x)
            bb = additive(pd.concat(parts))
            if bb and (bb[1] + bb[0]) > 0: boots.append(bb[1] / (bb[1] + bb[0]))
        rep = tau2 / (tau2 + s2) if (tau2 + s2) > 0 else np.nan
        out.append(dict(group=gname, n_papers=int(h.paper.nunique()), n_models=int(len(Ms)), n_cells=int(len(h)), df_resid=int(dfr),
                        kendall_tau_median=float(np.median(taus)), n_paper_pairs=len(taus), sigma_xp=float(np.sqrt(s2)), tau_b=float(np.sqrt(tau2)),
                        reproducibility=float(rep), rep_lo=float(np.percentile(boots, 5)) if boots else np.nan, rep_hi=float(np.percentile(boots, 95)) if boots else np.nan))
    return pd.DataFrame(out)


# ============================================================================ 5. simulation under a given mask
def simulate(mask, task_dataset, task_paper, K_true, snr=1.0, dataset_share=0.7, paper_effect=0.0, general_mean=0.0, seed=0):
    """Synthetic table on the real missingness mask, on a points-like scale. Factor 1 is a GENERAL factor when
    general_mean > 0: every task's loading on it has mean general_mean (a single leaderboard exists); further factors are
    specific (mean-zero loadings). Tasks of one dataset share their loading (dataset_share of its variance) plus a task
    part; tasks get their own level and spread; snr = specific-plus-general signal variance / noise variance per task;
    paper_effect adds a (paper, model) offset in noise SDs. K_true = 1 with general_mean > 0 is 'one leaderboard'.
    Returns Y (0 where unobserved), true dataset loadings, dataset names."""
    rng = np.random.default_rng(seed); M, T = mask.shape
    task_dataset = np.asarray(task_dataset); task_paper = np.asarray(task_paper)
    names = sorted(set(task_dataset) - {""}); di = {n: i for i, n in enumerate(names)}
    theta = rng.normal(size=(M, K_true))
    Ld = rng.normal(size=(len(names), K_true)) / np.sqrt(K_true)
    L = np.array([np.sqrt(dataset_share) * Ld[di[d]] if d in di else np.zeros(K_true) for d in task_dataset]) \
        + np.sqrt(1 - dataset_share) * rng.normal(size=(T, K_true)) / np.sqrt(K_true)
    L[:, 0] += general_mean
    Ld = Ld.copy(); Ld[:, 0] += general_mean / np.sqrt(dataset_share)
    scale = np.exp(rng.normal(np.log(4.0), 0.5, size=T)); level = rng.normal(60, 15, size=T)
    S = theta @ L.T
    noise_sd = np.sqrt(np.mean(S ** 2) / snr)
    E = noise_sd * rng.normal(size=(M, T))
    if paper_effect > 0:
        for p in np.unique(task_paper):
            E[:, task_paper == p] += paper_effect * noise_sd * rng.normal(size=(M, 1))
    Y = level[None, :] + scale[None, :] * (S + E)
    return np.where(mask, Y, 0.0), Ld, names


def board_lopo_rho(Y, mask, task_paper, min_models=4):
    """Leave-one-paper-out Spearman of the naive leaderboard alone (no fitting): for calibrating simulations."""
    task_paper = np.asarray(task_paper); out = []
    Z = np.full(Y.shape, np.nan)
    for t in range(Y.shape[1]):
        o = mask[:, t]
        if o.sum() > 1 and Y[o, t].std() > 0: Z[o, t] = (Y[o, t] - Y[o, t].mean()) / Y[o, t].std(ddof=1)
    for p in np.unique(task_paper):
        hold = task_paper == p; Zp = Z.copy(); Zp[:, hold] = np.nan
        board = np.nanmean(Zp, axis=1); ntr = (~np.isnan(Zp)).sum(1)
        for t in np.where(hold)[0]:
            ms = np.where(mask[:, t] & (ntr >= 3))[0]
            if len(ms) >= min_models and np.ptp(Y[ms, t]) > 0:
                r_, _, _ = _rank_scores(Y[ms, t], np.nan_to_num(board[ms]))
                if np.isfinite(r_): out.append(r_)
    return float(np.mean(out)) if out else np.nan


def recovery(Ld_true, Ld_hat):
    """Rotation-invariant recovery of dataset geometry: correlation between the off-diagonal entries of the true and
    estimated dataset similarity matrices."""
    iu = np.triu_indices(len(Ld_true), 1)
    return float(np.corrcoef(similarity(Ld_true)[iu], similarity(Ld_hat)[iu])[0, 1])
