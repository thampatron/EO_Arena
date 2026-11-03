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

    def lam(self, include_u: bool = True) -> np.ndarray:
        L = self.U.copy() if include_u else np.zeros_like(self.U)
        for g, idx in self.groups.items():
            ok = idx >= 0
            L[ok] += self.B[g][idx[ok]]
        return L

    def predict(self) -> np.ndarray:
        return self.mu[None, :] + self.theta @ self.lam().T


def _group_parts(B, groups, T, K, skip=None):
    out = np.zeros((T, K))
    for g, idx in groups.items():
        if g == skip:
            continue
        ok = idx >= 0
        out[ok] += B[g][idx[ok]]
    return out


def fit_structured(Y, mask, K, groups: dict | None = None, ridge_u=10.0, ridge_g: dict | None = None, ridge_theta=10.0,
                   n_iter=400, tol=1e-7, seed=0, n_restarts=3, theta_init=None) -> StructuredFit:
    """Block-coordinate ridge least squares on observed cells. Every block update solves its exact ridge subproblem, so the
    penalised objective decreases monotonically. groups=None or {} gives the free-loading model (current EOArena fit)."""
    groups = {g: np.asarray(v, int) for g, v in (groups or {}).items()}
    ridge_g = {g: (ridge_g or {}).get(g, 1.0) for g in groups}
    M, T = Y.shape
    W = mask.astype(float)
    WY = np.where(mask, Y, 0.0)
    nlev = {g: int(idx.max()) + 1 if (idx >= 0).any() else 0 for g, idx in groups.items()}
    rng = np.random.default_rng(seed)
    mu0 = np.array([Y[mask[:, t], t].mean() if mask[:, t].any() else 0.0 for t in range(T)])
    if K == 0:
        return StructuredFit(0, mu0, np.zeros((M, 0)), {g: np.zeros((n, 0)) for g, n in nlev.items()}, np.zeros((T, 0)), groups)

    def objective(mu, th, B, U):
        L = U + _group_parts(B, groups, T, K)
        P = mu[None, :] + th @ L.T
        pen = ridge_u * (U ** 2).sum() + ridge_theta * (th ** 2).sum() + sum(ridge_g[g] * (B[g] ** 2).sum() for g in groups)
        return float((((Y - P) ** 2) * W).sum() + pen)

    R0 = np.where(mask, Y - mu0[None, :], 0.0)
    Us, Ss, _ = np.linalg.svd(R0, full_matrices=False)
    starts = [theta_init] if theta_init is not None else [Us[:, :K] * Ss[:K] / np.sqrt(max(mask.mean(), 1e-3) * T)]
    starts += [rng.normal(size=(M, K)) * 0.5 for _ in range(n_restarts)]
    best = None
    for th in starts:
        th = th.copy(); mu = mu0.copy(); U = np.zeros((T, K)); B = {g: np.zeros((n, K)) for g, n in nlev.items()}
        prev = np.inf; it = 0
        for it in range(1, n_iter + 1):
            # (a) mu_t and u_t jointly, with the group parts as a fixed offset
            off = _group_parts(B, groups, T, K)
            X = np.c_[np.ones(M), th]                                            # M x (K+1)
            A = np.einsum('mt,mi,mj->tij', W, X, X) + np.diag([1e-8] + [ridge_u] * K)[None]
            rhs = np.einsum('mt,mi->ti', WY - W * (th @ off.T), X)
            coef = np.linalg.solve(A, rhs[..., None])[..., 0]
            mu, U = coef[:, 0], coef[:, 1:]
            # (b) each group's block loadings
            G = np.einsum('mt,mi,mj->tij', W, th, th)                            # per-task Gram, T x K x K
            for g, idx in groups.items():
                if nlev[g] == 0:
                    continue
                rest = U + _group_parts(B, groups, T, K, skip=g)
                Rt = WY - W * (mu[None, :] + th @ rest.T)                         # residual for g, observed cells
                b = Rt.T @ th                                                    # T x K
                ok = idx >= 0
                A_g = np.zeros((nlev[g], K, K)); b_g = np.zeros((nlev[g], K))
                np.add.at(A_g, idx[ok], G[ok]); np.add.at(b_g, idx[ok], b[ok])
                A_g += ridge_g[g] * np.eye(K)[None]
                B[g] = np.linalg.solve(A_g, b_g[..., None])[..., 0]
            # (c) theta
            L = U + _group_parts(B, groups, T, K)
            A2 = np.einsum('mt,ti,tj->mij', W, L, L) + ridge_theta * np.eye(K)[None]
            b2 = (WY - W * mu[None, :]) @ L
            th = np.linalg.solve(A2, b2[..., None])[..., 0]
            obj = objective(mu, th, B, U)
            if prev - obj < tol * max(obj, 1e-12):
                break
            prev = obj
        if best is None or obj < best[0]:
            best = (obj, mu, th, B, U, it)
    obj, mu, th, B, U, it = best
    # identifiability convention: centre and whiten theta over models; push the transform into the loadings
    c = th.mean(0); mu = mu + (U + _group_parts(B, groups, T, K)) @ c; th = th - c
    Lc = np.linalg.cholesky(np.cov(th, rowvar=False).reshape(K, K) + 1e-9 * np.eye(K))
    th = th @ np.linalg.inv(Lc).T
    U = U @ Lc; B = {g: v @ Lc for g, v in B.items()}
    return StructuredFit(K, mu, th, B, U, groups, obj, it)


# ============================================================================ 2. out-of-sample tests
def _rank_scores(y, p):
    """Spearman rho and pairwise ordering accuracy (ties in y skipped) for one task."""
    if len(y) < 3 or np.ptp(y) == 0 or np.ptp(p) == 0:
        return np.nan, np.nan, 0
    rho = spearmanr(y, p).statistic
    d_y = np.sign(y[:, None] - y[None, :]); d_p = np.sign(p[:, None] - p[None, :])
    iu = np.triu_indices(len(y), 1); keep = d_y[iu] != 0
    acc = float((d_y[iu][keep] == d_p[iu][keep]).mean()) if keep.any() else np.nan
    return float(rho), acc, int(keep.sum())


def leave_one_paper_out(Y, mask, task_paper, K, groups, min_models=4, min_theta_tasks=3, use_u=False, **kw):
    """For each paper: drop all its tasks, refit, predict each dropped task's model ordering from lambda = sum of its
    learned group blocks (u_t is unknown for an unseen task, so it is 0), for models that keep >= min_theta_tasks
    observed tasks elsewhere. Returns per-task rows: paper, task index, n models scored, Spearman, pairwise accuracy.
    The 'global' baseline orders models by their mean predicted score over all training tasks (a one-ranking-fits-all
    predictor), so  structured - global  is what dataset/protocol/sensor identity adds."""
    task_paper = np.asarray(task_paper)
    rows = []
    for p in np.unique(task_paper):
        hold = task_paper == p
        m2 = mask.copy(); m2[:, hold] = False
        if m2[:, ~hold].sum() == 0:
            continue
        fit = fit_structured(Y, m2, K, groups, **kw)
        L = fit.lam(include_u=False)
        gen = (fit.mu[None, ~hold] + fit.theta @ fit.lam()[~hold].T).mean(1)   # global "general ability" score
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
            rows.append(dict(paper=p, task=int(t), n_models=len(ms), n_pairs=n_pairs, rho_struct=r_s, acc_struct=a_s, rho_global=r_g, acc_global=a_g))
    return pd.DataFrame(rows)


def heldout_cell_cv(Y, mask, K, groups, folds=5, min_keep=4, seed=0, **kw):
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
        P = fit_structured(Y, m2, K, groups, seed=seed + f, **kw).predict()
        e = Y[held[:, 0], held[:, 1]] - P[held[:, 0], held[:, 1]]
        rmse.append(float(np.sqrt((e ** 2).mean())))
        df = pd.DataFrame({"t": held[:, 1], "y": Y[held[:, 0], held[:, 1]], "p": P[held[:, 0], held[:, 1]]})
        ok = tot = 0
        for _, g in df.groupby("t"):
            if len(g) < 2: continue
            dy = np.sign(g.y.values[:, None] - g.y.values[None, :]); dp = np.sign(g.p.values[:, None] - g.p.values[None, :])
            iu = np.triu_indices(len(g), 1); k = dy[iu] != 0
            ok += int((dy[iu][k] == dp[iu][k]).sum()); tot += int(k.sum())
        acc.append(ok / tot if tot else np.nan)
    return dict(rmse=float(np.mean(rmse)), rmse_se=float(np.std(rmse, ddof=1) / np.sqrt(folds)),
                pair_acc=float(np.nanmean(acc)), pair_acc_se=float(np.nanstd(acc, ddof=1) / np.sqrt(folds)), n_heldout=int(len(cand)))


# ============================================================================ 3. dataset-level geometry
def dataset_loadings(fit: StructuredFit, task_dataset, dataset_group="dataset"):
    """Position of each dataset in capability space: its block loading if the model has a dataset block, else the mean
    loading of its tasks. Returns (names, L_d, n_tasks)."""
    task_dataset = np.asarray(task_dataset)
    names = sorted(set(task_dataset) - {""})
    L = fit.lam()
    Ld = np.array([L[task_dataset == n].mean(0) for n in names])
    if dataset_group in fit.groups and fit.K:
        idx = fit.groups[dataset_group]
        for i, n in enumerate(names):
            lev = np.unique(idx[(task_dataset == n) & (idx >= 0)])
            if len(lev) == 1:
                Ld[i] = fit.B[dataset_group][lev[0]] + (fit.U[task_dataset == n].mean(0))
    return names, Ld, np.array([(task_dataset == n).sum() for n in names])


def similarity(Ld):
    """Rotation-invariant similarity of what two datasets measure: cosine of loadings under Cov(theta) = I, which equals
    the correlation of their predicted (noise-free) model scores across the evaluated GeoFM population."""
    n = np.linalg.norm(Ld, axis=1, keepdims=True)
    S = (Ld / np.maximum(n, 1e-12)) @ (Ld / np.maximum(n, 1e-12)).T
    return S


def metadata_association(Ld, labels, n_perm=2000, seed=0):
    """Share of dataset-loading variance explained by a categorical label, against a permutation null that shuffles the
    label across DATASETS (the unit of analysis). Reports observed R^2, null mean, and p-value; the excess over the null
    is what should be read, since R^2 for a many-level factor is large by chance."""
    labels = np.asarray(labels).astype(str)
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


# ============================================================================ 4. cross-paper reproducibility
def cross_paper_reproducibility(df, min_papers=2, min_shared=3, n_boot=500, seed=0):
    """df: one row per (group, paper, model) with columns group, paper, model, y — y on a common fixed scale within a
    group (same dataset, protocol family and metric). For each group with >= min_papers papers that each share
    >= min_shared models with another paper:
      - pairwise Kendall tau of model orderings between papers on their shared models (median over pairs),
      - additive fit y_mp = a_p + b_m + e on the connected cells; sigma2_xp = RSS / df_resid is the cross-implementation
        disagreement about the same model (upper bound on single-evaluation noise),
      - tau2_b = Var_m(b_m) - mean sampling variance of b_m: stable between-model variance in the group,
      - reproducibility = tau2_b / (tau2_b + sigma2_xp), the note's Eq. 6 with sigma2 replaced by its cross-paper upper
        bound, so it is a LOWER bound on the seed-noise score. Bootstrap over models gives a 90% interval."""
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
def simulate(mask, task_dataset, task_paper, K_true, snr=1.0, dataset_share=0.7, paper_effect=0.0, seed=0):
    """Synthetic table on the real missingness mask. Tasks of one dataset share a loading (dataset_share of its variance),
    plus a task-specific part; optional paper-level random offsets per (paper, model) mimic implementation effects.
    Values are standardised within task exactly as the pipeline does. Returns Y, true dataset loadings, names."""
    rng = np.random.default_rng(seed); M, T = mask.shape
    task_dataset = np.asarray(task_dataset); task_paper = np.asarray(task_paper)
    names = sorted(set(task_dataset) - {""}); di = {n: i for i, n in enumerate(names)}
    theta = rng.normal(size=(M, K_true))
    Ld = rng.normal(size=(len(names), K_true))
    L = np.array([np.sqrt(dataset_share) * Ld[di[d]] if d in di else np.zeros(K_true) for d in task_dataset]) + np.sqrt(1 - dataset_share) * rng.normal(size=(T, K_true))
    S = theta @ L.T
    sig = np.sqrt(np.var(S) / snr) if snr > 0 else 1.0
    Y = S + sig * rng.normal(size=(M, T))
    if paper_effect > 0:
        for p in np.unique(task_paper):
            Y[:, task_paper == p] += paper_effect * sig * rng.normal(size=(M, 1))
    Y = np.where(mask, Y, np.nan)
    mu = np.nanmean(Y, 0); sd = np.nanstd(Y, 0, ddof=1)
    Z = np.where(mask, (Y - mu) / np.where(sd > 0, sd, 1), 0.0)
    return Z, Ld, names


def recovery(Ld_true, Ld_hat):
    """Rotation-invariant recovery of dataset geometry: correlation between the off-diagonal entries of the true and
    estimated dataset similarity matrices."""
    iu = np.triu_indices(len(Ld_true), 1)
    return float(np.corrcoef(similarity(Ld_true)[iu], similarity(Ld_hat)[iu])[0, 1])
