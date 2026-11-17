"""Shared evaluation, target construction, metrics, baselines, and reporting for TIERS.

Replaces the duplicated per-script `load_data()` / `shift(-1)` logic with:
- Consecutive-year `(year + 1)` target joins (no bridging over gaps).
- Targets conditioned strictly on the starting tier.
- Weighted metrics (when sampling is used) alongside population and sample counts.
- ROC AUC, average precision, log-loss, Brier score, Brier skill vs training base rate,
  reliability tables, and unordered-dyad-clustered bootstrap confidence intervals.
- Suppression of discrimination/calibration metrics when positives < `min_positives` (20).
- Source-coverage masks: a transition is not scored for a target whose label
  could change if a tier with no source that year were filled in
  (`label_decidable`, fed by `scripts/build/source_coverage.py`).
- One row per dyad-year: the tier is shared by the two directions, so each
  dyad-year is counted once with the mean of its two directed forecasts
  (`collapse_directions`).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")

YEAR_LO = 1946
YEAR_HI = 2014
TRAIN_SPLIT = 1989
MIN_POSITIVES = 20
RANDOM_STATE = 42

HEADLINE_TARGETS = [
    "Onset, any",
    "Onset, force",
    "Onset, war",
    "Escalation",
    "De-escalation",
]

EXACT_STEP_TARGETS = [f"T{k}->T{k + 1}" for k in range(5)]
CUM_STEP_TARGETS = [f"T{k}->T{k + 1}+" for k in range(1, 4)]  # T0->T1+ == Onset, any; T4->T5+ == T4->T5
ALL_TARGETS = HEADLINE_TARGETS + EXACT_STEP_TARGETS + CUM_STEP_TARGETS

V28_STRUCTURAL_AND_TRADE_FEATURES = [
    "contiguity_xi",
    "fma",
    "rivalry_omega",
    "cap_a_to_b",
    "cap_b_to_a",
    "closing_window_a",
    "closing_window_b",
    "d_k_years",
    "attribution",
    "n_pub_a",
    "n_pub_b",
    "c_t_ab",
    "c_t_ba",
    "trade_observed_flag",
    "trade_surface_norm_ab",
    "mutual_trade_dependence_ab",
    "dep_a_on_b",
    "dep_b_on_a",
    "import_leverage_a_over_b",
    "export_leverage_a_over_b",
    "trade_leverage_a_over_b",
]


@dataclass(frozen=True)
class LoadStats:
    path: str
    sha256: str
    n_raw: int
    n_dup_keys: int
    n_joined: int
    n_dropped_no_next: int
    year_min: int
    year_max: int


def sha256_file(path: str, chunk_size: int = 1 << 20) -> str:
    """Compute SHA-256 hex digest of a file on disk."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def git_revision(cwd: str = ROOT) -> str:
    """Return `<short-sha>` or `<short-sha>-dirty` for the repo."""
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "--short=10", "HEAD"], cwd=cwd, text=True
        ).strip()
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=cwd, text=True
        ).strip()
        return f"{sha}-dirty" if dirty else sha
    except Exception:
        return "unknown"


def escalation_probability(pis: np.ndarray, current_tier: np.ndarray) -> np.ndarray:
    """Sum of next-tier probabilities strictly above `current_tier`."""
    pis = np.asarray(pis, dtype=float)
    cur = np.asarray(current_tier, dtype=int)
    tiers = np.arange(6)[None, :]
    return (pis * (tiers > cur[:, None])).sum(axis=1)


def deescalation_probability(pis: np.ndarray, current_tier: np.ndarray) -> np.ndarray:
    """Sum of next-tier probabilities strictly below `current_tier`."""
    pis = np.asarray(pis, dtype=float)
    cur = np.asarray(current_tier, dtype=int)
    tiers = np.arange(6)[None, :]
    return (pis * (tiers < cur[:, None])).sum(axis=1)


COVERAGE_CSV = os.path.join(DATA_PROCESSED, "source_coverage.csv")


def load_unobserved_by_year(path: str = COVERAGE_CSV) -> Dict[int, int]:
    """Return `{year: bitmask}`; bit `u` is set when tier `u` has no source that year.

    The file is written by `scripts/build/source_coverage.py`.
    """
    cov = pd.read_csv(path)
    cov = cov[~cov["observed"].astype(bool)]
    out: Dict[int, int] = {}
    for year, tier in zip(cov["year"].astype(int), cov["tier"].astype(int), strict=True):
        out[year] = out.get(year, 0) | (1 << tier)
    return out


def attach_coverage(df: pd.DataFrame, unobserved_by_year: Optional[Dict[int, int]] = None) -> pd.DataFrame:
    """Add `unobserved_next`: the tiers that cannot be observed in year + 1."""
    if unobserved_by_year is None:
        unobserved_by_year = load_unobserved_by_year()
    out = df.copy()
    out["unobserved_next"] = (
        (out["year"].astype(int) + 1).map(unobserved_by_year).fillna(0).astype(int)
    )
    return out


def unobserved_next_of(df: pd.DataFrame) -> Optional[np.ndarray]:
    """The frame's `unobserved_next` column, or None when coverage was not attached."""
    if "unobserved_next" in df.columns:
        return df["unobserved_next"].to_numpy(dtype=int)
    return None


def _label(target_name: str, k: int, n: int) -> Optional[int]:
    """Label of one transition `k -> n` for a target, or None when `k` is not eligible."""
    mask, y, _ = extract_target(np.array([k]), np.array([n]), None, target_name)
    return int(y[0]) if mask[0] else None


def label_decidable(target_name: str, cur_tier: np.ndarray, unobserved_next: np.ndarray) -> np.ndarray:
    """True where the target's label does not depend on an unobserved tier.

    A dyad recorded at tier `n` next year may really be at an unobserved tier
    `u > n` (the highest tier wins, so an unobserved tier can only hide above
    the recorded one). A row with starting tier `k` is decidable when, for
    every unobserved `u` and every recorded `n < u`, the label of `k -> n`
    equals the label of `k -> u`. The test uses every possible `n`, not the
    row's own, so that positives and negatives are dropped together.

    Example: with T2 unobserved, "Onset, any" is undecidable (a recorded T0
    may be T2) while "Onset, force" is decidable (T0 and T2 are both below T4).

    The starting tier is taken as recorded. Before 1989 "T0" therefore means
    "no militarised or proxy conflict recorded; sanctions unknown".
    """
    cur = np.asarray(cur_tier, dtype=int)
    unobs = np.asarray(unobserved_next, dtype=int)
    out = np.ones(len(cur), dtype=bool)
    for bits in np.unique(unobs):
        if bits == 0:
            continue
        hidden = [u for u in range(1, 6) if (int(bits) >> u) & 1]
        for k in range(6):
            if _label(target_name, k, 0) is None:
                continue
            ok = all(
                _label(target_name, k, n) == _label(target_name, k, u)
                for u in hidden for n in range(u)
            )
            if not ok:
                out[(unobs == bits) & (cur == k)] = False
    return out


def attach_next_year_tier(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Attach `uiw_tier_next` by joining `(initiator, target, year + 1)`.

    Never uses `shift(-1)`, so missing calendar years are not bridged.
    If the input grid contains duplicate `(year, initiator, target)` keys, the
    lookup table collapses duplicates with `.max()` so the merge remains `many_to_one`.
    Returns `(joined_df, n_dup_keys)`.
    """
    n_dup_keys = int(df.duplicated(subset=["year", "initiator", "target"]).sum())
    nxt = df[["year", "initiator", "target", "uiw_tier"]].copy()
    if n_dup_keys > 0:
        nxt = nxt.groupby(["year", "initiator", "target"], as_index=False)["uiw_tier"].max()
    nxt["year"] = nxt["year"].astype(int) - 1
    nxt = nxt.rename(columns={"uiw_tier": "uiw_tier_next"})

    out = df.merge(
        nxt,
        on=["year", "initiator", "target"],
        how="left",
        validate="many_to_one",
    )
    out = out.dropna(subset=["uiw_tier_next"]).reset_index(drop=True)
    out["uiw_tier"] = out["uiw_tier"].astype(int)
    out["uiw_tier_next"] = out["uiw_tier_next"].astype(int)
    return out, n_dup_keys


def load_feature_grid(
    grid: str = "v28",
    path: Optional[str] = None,
    year_lo: int = YEAR_LO,
    year_hi: int = YEAR_HI,
) -> Tuple[pd.DataFrame, LoadStats]:
    """Load the v28 or v27 feature grid and attach consecutive-year next tier."""
    if path is None:
        stem = f"dyads_with_features_{grid}"
        pq = os.path.join(DATA_PROCESSED, f"{stem}.parquet")
        csv = os.path.join(DATA_PROCESSED, f"{stem}.csv")
        path = pq if os.path.exists(pq) else csv

    if path.endswith(".parquet"):
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path, dtype={"year": int})

    df = df[(df["year"] >= year_lo) & (df["year"] <= year_hi)].copy()
    n_raw = len(df)
    if "trade_source" not in df.columns:
        df["trade_source"] = "NONE"
    df["trade_source"] = df["trade_source"].fillna("NONE").astype(str)

    joined, n_dup_keys = attach_next_year_tier(df)
    joined = attach_coverage(joined)
    stats = LoadStats(
        path=os.path.relpath(path, ROOT) if os.path.isabs(path) else path,
        sha256=sha256_file(path),
        n_raw=n_raw,
        n_dup_keys=n_dup_keys,
        n_joined=len(joined),
        n_dropped_no_next=n_raw - len(joined),
        year_min=int(joined["year"].min()) if len(joined) else year_lo,
        year_max=int(joined["year"].max()) if len(joined) else year_hi,
    )
    return joined, stats


def extract_target(
    cur_tier: np.ndarray,
    next_tier: np.ndarray,
    pis: Optional[np.ndarray],
    target_name: str,
    unobserved_next: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """Return `(eligible_mask, y_true_eligible, score_eligible)` for `target_name`.

    When `unobserved_next` is given (one bitmask per row, see
    `attach_coverage`), rows whose label depends on an unobserved tier are
    not eligible.
    """
    cur = np.asarray(cur_tier, dtype=int)
    nxt = np.asarray(next_tier, dtype=int)
    if unobserved_next is not None and np.any(np.asarray(unobserved_next) != 0):
        base, y_all, p_all = extract_target(cur, nxt, pis, target_name)
        sel = label_decidable(target_name, cur, unobserved_next)[base]
        mask = base.copy()
        mask[base] = sel
        return mask, y_all[sel], (p_all[sel] if p_all is not None else None)

    if target_name == "Onset, any":
        mask = cur == 0
        y = (nxt[mask] >= 1).astype(int)
        p = (1.0 - pis[mask, 0]) if pis is not None else None
    elif target_name == "Onset, force":
        mask = cur == 0
        y = (nxt[mask] >= 4).astype(int)
        p = (pis[mask, 4] + pis[mask, 5]) if pis is not None else None
    elif target_name == "Onset, war":
        mask = cur == 0
        y = (nxt[mask] == 5).astype(int)
        p = pis[mask, 5] if pis is not None else None
    elif target_name == "Escalation":
        mask = (cur >= 0) & (cur <= 4)
        y = (nxt[mask] > cur[mask]).astype(int)
        p = escalation_probability(pis[mask], cur[mask]) if pis is not None else None
    elif target_name == "De-escalation":
        mask = (cur >= 1) & (cur <= 5)
        y = (nxt[mask] < cur[mask]).astype(int)
        p = deescalation_probability(pis[mask], cur[mask]) if pis is not None else None
    elif target_name.startswith("T") and "->T" in target_name:
        lhs, rhs = target_name.split("->")
        k = int(lhs[1:])
        cum = rhs.endswith("+")
        j = int(rhs[1:-1] if cum else rhs[1:])
        mask = cur == k
        if cum:
            y = (nxt[mask] >= j).astype(int)
            p = pis[mask, j:].sum(axis=1) if pis is not None else None
        else:
            y = (nxt[mask] == j).astype(int)
            p = pis[mask, j] if pis is not None else None
    else:
        raise ValueError(f"Unknown target name: {target_name!r}")

    return mask, y, p


def unordered_dyad_codes(df: pd.DataFrame) -> np.ndarray:
    """Map each directed row `(initiator, target)` to an integer unordered-dyad cluster ID."""
    all_names = pd.Index(df["initiator"]).append(pd.Index(df["target"])).unique()
    name_to_id = {name: idx for idx, name in enumerate(all_names)}
    id_a = df["initiator"].map(name_to_id).to_numpy(dtype=np.int64)
    id_b = df["target"].map(name_to_id).to_numpy(dtype=np.int64)
    n_c = np.int64(len(all_names) + 1)
    lo = np.minimum(id_a, id_b)
    hi = np.maximum(id_a, id_b)
    pair_keys = lo * n_c + hi
    codes, _ = pd.factorize(pair_keys, sort=False)
    return codes.astype(np.int32)


def dyad_year_codes(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Return `(codes, canonical)` for a directed grid with a shared dyad tier.

    `codes` is one integer per (year, unordered pair), so the two directed rows
    of a dyad-year share a code. `canonical` marks one of the two (the row
    whose initiator sorts first), which is the row kept when each dyad-year
    is counted once.
    """
    if {"initiator_ccode", "target_ccode"}.issubset(df.columns):
        a = df["initiator_ccode"].to_numpy(dtype=np.int64)
        b = df["target_ccode"].to_numpy(dtype=np.int64)
    else:
        names = pd.Index(df["initiator"]).append(pd.Index(df["target"])).unique()
        lookup = {name: idx for idx, name in enumerate(sorted(names))}
        a = df["initiator"].map(lookup).to_numpy(dtype=np.int64)
        b = df["target"].map(lookup).to_numpy(dtype=np.int64)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    year = df["year"].to_numpy(dtype=np.int64)
    raw = (year * 100_000 + lo) * 100_000 + hi
    codes, _ = pd.factorize(raw, sort=False)
    return codes.astype(np.int64), a < b


def mean_over_directions(codes: np.ndarray, values: np.ndarray) -> np.ndarray:
    """Average `values` over the rows that share a dyad-year code.

    The result is aligned with the input rows: both directed rows of a
    dyad-year receive the mean of their two forecasts. A row whose partner is
    absent (for example after sampling) keeps its own value.
    """
    values = np.asarray(values, dtype=float)
    # Re-number the codes so a subset of rows still yields compact groups.
    _, codes = np.unique(codes, return_inverse=True)
    n_groups = int(codes.max()) + 1 if len(codes) else 0
    counts = np.bincount(codes, minlength=n_groups).astype(float)
    if values.ndim == 1:
        return (np.bincount(codes, weights=values, minlength=n_groups) / counts)[codes]
    out = np.empty_like(values)
    for j in range(values.shape[1]):
        out[:, j] = (np.bincount(codes, weights=values[:, j], minlength=n_groups) / counts)[codes]
    return out


def collapse_directions(
    df: pd.DataFrame, *arrays: Optional[np.ndarray]
) -> Tuple[pd.DataFrame, List[Optional[np.ndarray]]]:
    """Reduce a directed frame to one row per dyad-year.

    Returns the canonical rows of `df` and, for each array aligned with `df`,
    its mean over the two directions on those rows. `None` passes through.
    A row whose partner is absent (after sampling, say) keeps its own value.
    """
    codes, canon = dyad_year_codes(df)
    out: List[Optional[np.ndarray]] = []
    for arr in arrays:
        out.append(None if arr is None else mean_over_directions(codes, np.asarray(arr))[canon])
    return df[canon].reset_index(drop=True), out


def _rank_stats_sorted(
    y_sorted: np.ndarray,
    w_sorted: np.ndarray,
    tie_ends: np.ndarray,
) -> Tuple[float, float]:
    """Compute weighted ROC AUC and Average Precision on scores sorted descending.

    `tie_ends` are the exclusive end indices of each group of equal scores.
    Matches `sklearn.metrics.roc_auc_score` and `average_precision_score` with `sample_weight`.
    """
    wy = w_sorted * y_sorted
    wn = w_sorted * (1.0 - y_sorted)

    cum_tp = np.cumsum(wy)
    cum_fp = np.cumsum(wn)
    tp_at = cum_tp[tie_ends - 1]
    fp_at = cum_fp[tie_ends - 1]

    total_pos = float(tp_at[-1])
    total_neg = float(fp_at[-1])
    if total_pos <= 0.0 or total_neg <= 0.0:
        return float("nan"), float("nan")

    tpr = np.concatenate(([0.0], tp_at / total_pos))
    fpr = np.concatenate(([0.0], fp_at / total_neg))
    roc_auc = float(np.sum((fpr[1:] - fpr[:-1]) * (tpr[1:] + tpr[:-1]) * 0.5))

    # Step-function Average Precision matching sklearn's `sum((R_n - R_{n-1}) * P_n)`
    recall = tp_at / total_pos
    prev_recall = np.concatenate(([0.0], recall[:-1]))
    denom = tp_at + fp_at
    precision = np.divide(tp_at, denom, out=np.ones_like(denom, dtype=float), where=denom > 0.0)
    ap = float(np.sum((recall - prev_recall) * precision))
    return roc_auc, ap


def weighted_roc_auc(
    y: np.ndarray, p: np.ndarray, sample_weight: Optional[np.ndarray] = None
) -> float:
    y_arr = np.asarray(y, dtype=float)
    p_arr = np.asarray(p, dtype=float)
    w_arr = np.ones_like(y_arr) if sample_weight is None else np.asarray(sample_weight, dtype=float)
    order = np.argsort(-p_arr, kind="mergesort")
    p_s = p_arr[order]
    tie_ends = np.flatnonzero(np.r_[p_s[:-1] != p_s[1:], True]) + 1
    auc, _ = _rank_stats_sorted(y_arr[order], w_arr[order], tie_ends)
    return auc


def weighted_avg_precision(
    y: np.ndarray, p: np.ndarray, sample_weight: Optional[np.ndarray] = None
) -> float:
    y_arr = np.asarray(y, dtype=float)
    p_arr = np.asarray(p, dtype=float)
    w_arr = np.ones_like(y_arr) if sample_weight is None else np.asarray(sample_weight, dtype=float)
    order = np.argsort(-p_arr, kind="mergesort")
    p_s = p_arr[order]
    tie_ends = np.flatnonzero(np.r_[p_s[:-1] != p_s[1:], True]) + 1
    _, ap = _rank_stats_sorted(y_arr[order], w_arr[order], tie_ends)
    return ap


def weighted_brier_and_skill(
    y: np.ndarray,
    p: np.ndarray,
    sample_weight: Optional[np.ndarray] = None,
    ref_rate: Optional[float] = None,
) -> Tuple[float, float]:
    y_arr = np.asarray(y, dtype=float)
    p_arr = np.clip(np.asarray(p, dtype=float), 0.0, 1.0)
    w_arr = np.ones_like(y_arr) if sample_weight is None else np.asarray(sample_weight, dtype=float)
    w_sum = float(w_arr.sum())
    if w_sum <= 0.0:
        return float("nan"), float("nan")
    brier = float(np.sum(w_arr * (y_arr - p_arr) ** 2) / w_sum)
    ref = float(np.sum(w_arr * y_arr) / w_sum) if ref_rate is None else float(ref_rate)
    brier_ref = float(np.sum(w_arr * (y_arr - ref) ** 2) / w_sum)
    bss = float(1.0 - brier / brier_ref) if brier_ref > 0.0 else float("nan")
    return brier, bss


def weighted_log_loss(
    y: np.ndarray, p: np.ndarray, sample_weight: Optional[np.ndarray] = None
) -> float:
    y_arr = np.asarray(y, dtype=float)
    p_arr = np.clip(np.asarray(p, dtype=float), 1e-15, 1.0 - 1e-15)
    w_arr = np.ones_like(y_arr) if sample_weight is None else np.asarray(sample_weight, dtype=float)
    w_sum = float(w_arr.sum())
    if w_sum <= 0.0:
        return float("nan")
    losses = -(y_arr * np.log(p_arr) + (1.0 - y_arr) * np.log(1.0 - p_arr))
    return float(np.sum(w_arr * losses) / w_sum)


def _dyad_bootstrap(
    y: np.ndarray,
    p: np.ndarray,
    w: np.ndarray,
    clusters: np.ndarray,
    ref_rate: float,
    n_boot: int,
    seed: int,
) -> Dict[str, Tuple[float, float]]:
    """Fast dyad-clustered bootstrap 95% CIs using pre-sorted scores."""
    metrics_keys = ("roc_auc", "avg_precision", "brier", "brier_skill", "log_loss")
    if n_boot <= 0 or len(y) == 0:
        return {k: (float("nan"), float("nan")) for k in metrics_keys}

    # Re-index clusters to compact 0..C-1
    c_local, _ = pd.factorize(clusters, sort=False)
    n_clusters = int(c_local.max()) + 1
    if n_clusters < 2:
        return {k: (float("nan"), float("nan")) for k in metrics_keys}

    order = np.argsort(-p, kind="mergesort")
    y_s = y[order].astype(float)
    p_s = np.clip(p[order].astype(float), 1e-15, 1.0 - 1e-15)
    w_s = w[order].astype(float)
    c_s = c_local[order]
    tie_ends = np.flatnonzero(np.r_[p_s[:-1] != p_s[1:], True]) + 1

    sq_err_s = (y_s - p_s) ** 2
    sq_ref_s = (y_s - ref_rate) ** 2
    ll_s = -(y_s * np.log(p_s) + (1.0 - y_s) * np.log(1.0 - p_s))

    rng = np.random.default_rng(seed)
    probs = np.full(n_clusters, 1.0 / n_clusters)
    vals: Dict[str, List[float]] = {k: [] for k in metrics_keys}

    for _ in range(n_boot):
        mult = rng.multinomial(n_clusters, probs)
        wb = w_s * mult[c_s]
        w_sum = float(wb.sum())
        if w_sum <= 0.0:
            continue
        auc, ap = _rank_stats_sorted(y_s, wb, tie_ends)
        brier = float(np.sum(wb * sq_err_s) / w_sum)
        brier_ref = float(np.sum(wb * sq_ref_s) / w_sum)
        bss = float(1.0 - brier / brier_ref) if brier_ref > 0.0 else float("nan")
        ll = float(np.sum(wb * ll_s) / w_sum)

        vals["roc_auc"].append(auc)
        vals["avg_precision"].append(ap)
        vals["brier"].append(brier)
        vals["brier_skill"].append(bss)
        vals["log_loss"].append(ll)

    ci: Dict[str, Tuple[float, float]] = {}
    for k in metrics_keys:
        arr = np.asarray(vals[k], dtype=float)
        arr = arr[np.isfinite(arr)]
        if len(arr) >= 10:
            ci[k] = (float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5)))
        else:
            ci[k] = (float("nan"), float("nan"))
    return ci


def compute_metrics(
    y: np.ndarray,
    p: np.ndarray,
    inclusion_prob: Optional[np.ndarray] = None,
    ref_rate: Optional[float] = None,
    clusters: Optional[np.ndarray] = None,
    n_boot: int = 200,
    seed: int = RANDOM_STATE,
    min_positives: int = MIN_POSITIVES,
) -> Dict[str, float]:
    """Compute weighted discrimination + calibration metrics with <20-positive suppression."""
    y_arr = np.asarray(y, dtype=int)
    p_arr = np.asarray(p, dtype=float)
    if inclusion_prob is None:
        w_arr = np.ones(len(y_arr), dtype=float)
    else:
        inc = np.asarray(inclusion_prob, dtype=float)
        w_arr = 1.0 / np.clip(inc, 1e-12, 1.0)

    n_sample_rows = int(len(y_arr))
    n_sample_pos = int(y_arr.sum())
    n_sample_neg = n_sample_rows - n_sample_pos
    n_pop_rows = float(w_arr.sum())
    n_pop_pos = float(w_arr[y_arr == 1].sum()) if n_sample_pos > 0 else 0.0
    n_pop_neg = float(n_pop_rows - n_pop_pos)
    base_rate = float(n_pop_pos / n_pop_rows) if n_pop_rows > 0.0 else float("nan")
    effective_ref = base_rate if ref_rate is None else float(ref_rate)

    suppressed = (n_sample_pos < min_positives) or (n_sample_neg < 1)
    out: Dict[str, float] = {
        "n_sample_rows": n_sample_rows,
        "n_sample_pos": n_sample_pos,
        "n_sample_neg": n_sample_neg,
        "n_pop_rows": round(n_pop_rows, 2),
        "n_pop_pos": round(n_pop_pos, 2),
        "n_pop_neg": round(n_pop_neg, 2),
        "base_rate": base_rate,
        "ref_rate": effective_ref,
        "suppressed": bool(suppressed),
        "roc_auc": float("nan"),
        "roc_auc_ci_lo": float("nan"),
        "roc_auc_ci_hi": float("nan"),
        "avg_precision": float("nan"),
        "avg_precision_ci_lo": float("nan"),
        "avg_precision_ci_hi": float("nan"),
        "brier": float("nan"),
        "brier_ci_lo": float("nan"),
        "brier_ci_hi": float("nan"),
        "brier_skill": float("nan"),
        "brier_skill_ci_lo": float("nan"),
        "brier_skill_ci_hi": float("nan"),
        "log_loss": float("nan"),
        "log_loss_ci_lo": float("nan"),
        "log_loss_ci_hi": float("nan"),
    }
    if suppressed:
        return out

    out["roc_auc"] = weighted_roc_auc(y_arr, p_arr, w_arr)
    out["avg_precision"] = weighted_avg_precision(y_arr, p_arr, w_arr)
    brier, bss = weighted_brier_and_skill(y_arr, p_arr, w_arr, ref_rate=effective_ref)
    out["brier"] = brier
    out["brier_skill"] = bss
    out["log_loss"] = weighted_log_loss(y_arr, p_arr, w_arr)

    if clusters is not None and n_boot > 0:
        ci = _dyad_bootstrap(
            y_arr, p_arr, w_arr, np.asarray(clusters), effective_ref, n_boot=n_boot, seed=seed
        )
        for key, (lo, hi) in ci.items():
            out[f"{key}_ci_lo"] = lo
            out[f"{key}_ci_hi"] = hi

    return out


def reliability_table(
    y: np.ndarray,
    p: np.ndarray,
    inclusion_prob: Optional[np.ndarray] = None,
    n_bins: int = 10,
) -> pd.DataFrame:
    """Build a quantile-binned reliability table for rare-event calibration inspection."""
    y_arr = np.asarray(y, dtype=float)
    p_arr = np.asarray(p, dtype=float)
    w_arr = (
        np.ones(len(y_arr), dtype=float)
        if inclusion_prob is None
        else 1.0 / np.clip(np.asarray(inclusion_prob, dtype=float), 1e-12, 1.0)
    )
    if len(y_arr) == 0:
        return pd.DataFrame(
            columns=["bin", "p_lo", "p_hi", "n_rows", "n_pos", "mean_pred", "obs_rate", "abs_err"]
        )

    edges = np.unique(np.quantile(p_arr, np.linspace(0.0, 1.0, n_bins + 1)))
    if len(edges) <= 2:
        bins = np.zeros(len(y_arr), dtype=int)
        n_actual = 1
    else:
        bins = np.clip(np.searchsorted(edges[1:-1], p_arr, side="right"), 0, len(edges) - 2)
        n_actual = len(edges) - 1

    rows = []
    for b in range(n_actual):
        m = bins == b
        if not np.any(m):
            continue
        wb = w_arr[m]
        w_sum = float(wb.sum())
        mean_pred = float(np.sum(wb * p_arr[m]) / w_sum)
        obs_rate = float(np.sum(wb * y_arr[m]) / w_sum)
        rows.append({
            "bin": b,
            "p_lo": float(p_arr[m].min()),
            "p_hi": float(p_arr[m].max()),
            "n_rows": int(m.sum()),
            "n_pos": int(y_arr[m].sum()),
            "mean_pred": mean_pred,
            "obs_rate": obs_rate,
            "abs_err": abs(mean_pred - obs_rate),
        })
    return pd.DataFrame(rows)


def fit_transition_matrix(cur_train: np.ndarray, next_train: np.ndarray) -> np.ndarray:
    """Fit the 6x6 empirical tier-transition matrix from training eligible rows."""
    cur = np.asarray(cur_train, dtype=int)
    nxt = np.asarray(next_train, dtype=int)
    mat = np.zeros((6, 6), dtype=float)
    for k in range(6):
        m = cur == k
        if not np.any(m):
            mat[k, k] = 1.0
            continue
        counts = np.bincount(nxt[m], minlength=6).astype(float)
        mat[k] = counts / counts.sum()
    return mat


def score_transition_matrix(mat: np.ndarray, cur_eval: np.ndarray) -> np.ndarray:
    """Return `(N, 6)` transition-matrix probabilities for `cur_eval`."""
    return mat[np.asarray(cur_eval, dtype=int)]


def build_logistic_feature_matrix(
    df: pd.DataFrame, include_tier_dummies: bool = False
) -> np.ndarray:
    """Build numeric feature matrix including structural and v28 trade columns."""
    cols: List[np.ndarray] = []
    for col in V28_STRUCTURAL_AND_TRADE_FEATURES:
        if col == "trade_observed_flag":
            src = df["trade_source"].fillna("NONE").astype(str).to_numpy()
            cols.append((src != "NONE").astype(float))
        elif col in df.columns:
            cols.append(pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=float))
        else:
            cols.append(np.zeros(len(df), dtype=float))
    if include_tier_dummies:
        cur = df["uiw_tier"].to_numpy(dtype=int)
        for k in range(6):
            cols.append((cur == k).astype(float))
    return np.column_stack(cols)


def fit_and_score_logreg_targets(
    train_df: pd.DataFrame,
    eval_dfs: Dict[str, pd.DataFrame],
    target_names: Sequence[str],
    seed: int = RANDOM_STATE,
    min_positives: int = MIN_POSITIVES,
) -> Dict[str, Dict[str, np.ndarray]]:
    """Fit per-target binary `LogisticRegression(natural)` on eligible training rows.

    Returns `{split_name: {target_name: predicted_prob_on_eligible_rows}}`.
    """
    x_train_single = build_logistic_feature_matrix(train_df, include_tier_dummies=False)
    x_train_multi = build_logistic_feature_matrix(train_df, include_tier_dummies=True)
    eval_single = {
        k: build_logistic_feature_matrix(v, include_tier_dummies=False) for k, v in eval_dfs.items()
    }
    eval_multi = {
        k: build_logistic_feature_matrix(v, include_tier_dummies=True) for k, v in eval_dfs.items()
    }

    cur_tr = train_df["uiw_tier"].to_numpy(dtype=int)
    nxt_tr = train_df["uiw_tier_next"].to_numpy(dtype=int)
    preds: Dict[str, Dict[str, np.ndarray]] = {split: {} for split in eval_dfs}

    for tname in target_names:
        multi_tier = tname in ("Escalation", "De-escalation")
        mask_tr, y_tr, _ = extract_target(cur_tr, nxt_tr, None, tname, unobserved_next_of(train_df))
        n_pos = int(y_tr.sum())
        if n_pos < min_positives or (len(y_tr) - n_pos) < 1:
            for split, edf in eval_dfs.items():
                mask_ev, _, _ = extract_target(
                    edf["uiw_tier"].to_numpy(dtype=int),
                    edf["uiw_tier_next"].to_numpy(dtype=int),
                    None,
                    tname,
                    unobserved_next_of(edf),
                )
                preds[split][tname] = np.full(int(mask_ev.sum()), np.nan, dtype=float)
            continue

        x_tr = (x_train_multi if multi_tier else x_train_single)[mask_tr]
        pipe = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(max_iter=1000, C=1.0, random_state=seed),
        )
        pipe.fit(x_tr, y_tr)
        for split, edf in eval_dfs.items():
            mask_ev, _, _ = extract_target(
                edf["uiw_tier"].to_numpy(dtype=int),
                edf["uiw_tier_next"].to_numpy(dtype=int),
                None,
                tname,
                unobserved_next_of(edf),
            )
            x_ev = (eval_multi[split] if multi_tier else eval_single[split])[mask_ev]
            preds[split][tname] = pipe.predict_proba(x_ev)[:, 1] if len(x_ev) else np.array([], dtype=float)

    return preds


def training_base_rates(
    train_df: pd.DataFrame, target_names: Sequence[str] = ALL_TARGETS
) -> Dict[str, float]:
    """Compute exact training-period base rates for each target's eligible population."""
    cur = train_df["uiw_tier"].to_numpy(dtype=int)
    nxt = train_df["uiw_tier_next"].to_numpy(dtype=int)
    rates: Dict[str, float] = {}
    unobs = unobserved_next_of(train_df)
    for tname in target_names:
        _, y, _ = extract_target(cur, nxt, None, tname, unobs)
        rates[tname] = float(y.mean()) if len(y) > 0 else float("nan")
    return rates


def fit_transition_rates(
    train_df: pd.DataFrame, target_names: Sequence[str] = ALL_TARGETS
) -> Dict[str, np.ndarray]:
    """Per target, the training rate of a positive label for each starting tier.

    This is the transition-matrix baseline written per target, so that each
    target is fitted only on the training rows whose label is decidable. With
    full coverage it gives the same forecasts as `fit_transition_matrix`.
    A starting tier with no usable training rows gets the target's overall
    training rate.
    """
    cur = train_df["uiw_tier"].to_numpy(dtype=int)
    nxt = train_df["uiw_tier_next"].to_numpy(dtype=int)
    unobs = unobserved_next_of(train_df)
    out: Dict[str, np.ndarray] = {}
    for tname in target_names:
        mask, y, _ = extract_target(cur, nxt, None, tname, unobs)
        overall = float(y.mean()) if len(y) else 0.0
        rates = np.full(6, overall, dtype=float)
        cur_m = cur[mask]
        for k in range(6):
            sel = cur_m == k
            if np.any(sel):
                rates[k] = float(y[sel].mean())
        out[tname] = rates
    return out


def transition_rate_scores(
    df: pd.DataFrame, rates: Dict[str, np.ndarray], target_names: Sequence[str] = ALL_TARGETS
) -> Dict[str, np.ndarray]:
    """Scores from `fit_transition_rates`, aligned to each target's eligible rows of `df`."""
    cur = df["uiw_tier"].to_numpy(dtype=int)
    nxt = df["uiw_tier_next"].to_numpy(dtype=int)
    unobs = unobserved_next_of(df)
    out: Dict[str, np.ndarray] = {}
    for tname in target_names:
        tmask, _, _ = extract_target(cur, nxt, None, tname, unobs)
        out[tname] = rates[tname][cur[tmask]]
    return out


def collapse_target_scores(
    directed_df: pd.DataFrame, scores: Dict[str, np.ndarray], target_names: Sequence[str] = ALL_TARGETS
) -> Dict[str, np.ndarray]:
    """Average per-target scores over the two directions of each dyad-year.

    `scores[t]` is aligned to target `t`'s eligible rows of `directed_df` (as
    returned by `fit_and_score_logreg_targets`). The result is aligned to the
    eligible rows of `collapse_directions(directed_df)`. Targets whose scores
    are missing or not finite are left out.
    """
    codes, canon = dyad_year_codes(directed_df)
    cur = directed_df["uiw_tier"].to_numpy(dtype=int)
    nxt = directed_df["uiw_tier_next"].to_numpy(dtype=int)
    unobs = unobserved_next_of(directed_df)
    out: Dict[str, np.ndarray] = {}
    for tname in target_names:
        dmask, _, _ = extract_target(cur, nxt, None, tname, unobs)
        p_dir = scores.get(tname)
        if p_dir is None or len(p_dir) != int(dmask.sum()) or not len(p_dir) or not np.all(np.isfinite(p_dir)):
            continue
        out[tname] = mean_over_directions(codes[dmask], p_dir)[canon[dmask]]
    return out


def evaluate_target_scores(
    df: pd.DataFrame,
    scores: Dict[str, np.ndarray],
    split_name: str,
    model_name: str,
    train_rates: Dict[str, float],
    target_names: Sequence[str] = ALL_TARGETS,
    clusters: Optional[np.ndarray] = None,
    inclusion_prob: Optional[np.ndarray] = None,
    n_boot: int = 200,
    seed: int = RANDOM_STATE,
    min_positives: int = MIN_POSITIVES,
) -> List[Dict]:
    """Evaluate per-target probabilities that are aligned to each target's eligible rows.

    A target whose scores are missing, the wrong length or not finite is
    reported with counts only.
    """
    cur = df["uiw_tier"].to_numpy(dtype=int)
    nxt = df["uiw_tier_next"].to_numpy(dtype=int)
    unobs = unobserved_next_of(df)
    if clusters is None and {"initiator", "target"}.issubset(df.columns):
        clusters = unordered_dyad_codes(df)
    rows: List[Dict] = []
    for tname in target_names:
        base, _, _ = extract_target(cur, nxt, None, tname)
        tmask, y, _ = extract_target(cur, nxt, None, tname, unobs)
        if len(y) == 0:
            continue
        p = scores.get(tname)
        usable = p is not None and len(p) == len(y) and bool(np.all(np.isfinite(p)))
        inc = inclusion_prob[tmask] if inclusion_prob is not None else None
        if usable:
            m = compute_metrics(
                y, p, inclusion_prob=inc, ref_rate=train_rates.get(tname),
                clusters=clusters[tmask] if clusters is not None else None,
                n_boot=n_boot, seed=seed, min_positives=min_positives,
            )
        else:
            m = compute_metrics(
                y, np.zeros(len(y), dtype=float), inclusion_prob=inc,
                ref_rate=train_rates.get(tname), clusters=None, n_boot=0,
                min_positives=len(y) + 1,
            )
        m.update({
            "split": split_name, "model": model_name, "subgroup_col": "ALL",
            "subgroup": "ALL", "target": tname,
            "n_masked_rows": int(base.sum() - tmask.sum()),
        })
        rows.append(m)
    return rows


def evaluate_pis_on_split(
    df: pd.DataFrame,
    pis: np.ndarray,
    split_name: str,
    model_name: str,
    train_rates: Dict[str, float],
    target_names: Sequence[str] = ALL_TARGETS,
    clusters: Optional[np.ndarray] = None,
    inclusion_prob: Optional[np.ndarray] = None,
    n_boot: int = 200,
    seed: int = RANDOM_STATE,
    min_positives: int = MIN_POSITIVES,
    subgroup_col: Optional[str] = None,
    subgroup_values: Optional[Iterable[str]] = None,
) -> List[Dict]:
    """Evaluate a `(N, 6)` next-tier distribution matrix across targets (and optional subgroups)."""
    cur = df["uiw_tier"].to_numpy(dtype=int)
    nxt = df["uiw_tier_next"].to_numpy(dtype=int)
    unobs = unobserved_next_of(df)
    if clusters is None and {"initiator", "target"}.issubset(df.columns):
        clusters = unordered_dyad_codes(df)

    groups: List[Tuple[str, np.ndarray]] = [("ALL", np.ones(len(df), dtype=bool))]
    if subgroup_col is not None and subgroup_col in df.columns:
        vals = (
            list(subgroup_values)
            if subgroup_values is not None
            else sorted(str(v) for v in df[subgroup_col].dropna().unique())
        )
        col_vals = df[subgroup_col].astype(str).to_numpy()
        for val in vals:
            groups.append((val, col_vals == val))

    rows: List[Dict] = []
    for gname, gmask in groups:
        if not np.any(gmask):
            continue
        cur_g = cur[gmask]
        nxt_g = nxt[gmask]
        pis_g = pis[gmask]
        cl_g = clusters[gmask] if clusters is not None else None
        inc_g = inclusion_prob[gmask] if inclusion_prob is not None else None
        unobs_g = unobs[gmask] if unobs is not None else None
        for tname in target_names:
            base, _, _ = extract_target(cur_g, nxt_g, None, tname)
            tmask, y, p = extract_target(cur_g, nxt_g, pis_g, tname, unobs_g)
            if len(y) == 0:
                continue
            m = compute_metrics(
                y,
                p,
                inclusion_prob=inc_g[tmask] if inc_g is not None else None,
                ref_rate=train_rates.get(tname),
                clusters=cl_g[tmask] if cl_g is not None else None,
                n_boot=n_boot,
                seed=seed,
                min_positives=min_positives,
            )
            m.update({
                "split": split_name,
                "model": model_name,
                "subgroup_col": subgroup_col or "ALL",
                "subgroup": gname,
                "target": tname,
                "n_masked_rows": int(base.sum() - tmask.sum()),
            })
            rows.append(m)
    return rows


def format_ci(val: float, lo: float, hi: float, digits: int = 4) -> str:
    if not np.isfinite(val):
        return "suppressed (<20 pos)"
    if np.isfinite(lo) and np.isfinite(hi):
        return f"{val:.{digits}f} [{lo:.{digits}f}, {hi:.{digits}f}]"
    return f"{val:.{digits}f}"


def stamp_header_lines(
    title: str,
    stats: LoadStats,
    parameters_desc: str,
    seed: int,
    extra: Optional[Sequence[str]] = None,
) -> List[str]:
    """Generate a reproducible run header stamped with commit, grid hash, params, counts, seed."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines = [
        f"# {title}",
        "",
        f"- **Generated (UTC):** {now}",
        f"- **Git commit:** `{git_revision()}`",
        f"- **Feature grid:** `{stats.path}` (SHA-256 `{stats.sha256[:16]}...`)",
        f"- **Row counts:** raw={stats.n_raw:,} ({stats.year_min}–{stats.year_max}), "
        f"dup_keys={stats.n_dup_keys:,}, consecutive_joined={stats.n_joined:,}, "
        f"dropped_terminal_or_gap={stats.n_dropped_no_next:,}",
        f"- **Parameters:** {parameters_desc}",
        f"- **Random seed:** {seed}",
    ]
    if extra:
        lines.extend(extra)
    lines.append("")
    return lines
