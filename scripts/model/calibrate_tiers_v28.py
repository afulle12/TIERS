"""Calibrate TIERS v28 transition-hazard coefficients.

This fits sign-constrained logistic hazard blocks against the existing v28
feature grid, which already uses the combined BACI/TRADHIST trade source of
truth (`data/processed/trade_interdependence.*`). The fitted coefficients are
written as a v28 `Priors` JSON file that `backtest_tiers_v28.py --priors` can
load.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from dataclasses import asdict
from typing import Callable

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from evaluation import load_feature_grid
from tiers_lib_v28 import Priors

YEAR_LO, YEAR_HI = 1946, 2014
TRAIN_SPLIT = 1989
RANDOM_STATE = 42


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return np.where(x >= 0, 1.0 / (1.0 + np.exp(-x)), np.exp(x) / (1.0 + np.exp(x)))


def _clip01(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0).clip(0.0, 1.0)


def _num(df: pd.DataFrame, name: str, default: float = 0.0) -> pd.Series:
    if name not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[name], errors="coerce").fillna(default)


def load_data() -> pd.DataFrame:
    df, _ = load_feature_grid("v28", year_lo=YEAR_LO, year_hi=YEAR_HI)
    return df


def design_t01(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    cap_shift = (_num(df, "c_t_ab", 0.5) - _num(df, "c_t_ba", 0.5)).abs().clip(0.0, 1.0)
    x = pd.DataFrame({
        "intercept": 1.0,
        "surface": _clip01(_num(df, "trade_surface_norm_ab")),
        "rivalry": _clip01(_num(df, "rivalry_omega")),
        "contiguity": _clip01(_num(df, "contiguity_xi")),
        "cap_shift": cap_shift,
        "mutual_suppress": -_clip01(_num(df, "mutual_trade_dependence_ab")),
        "public_suppress": -_clip01(_num(df, "n_pub_a", 0.9)),
    })
    y = (df["uiw_tier_next"] >= 1).astype(int).to_numpy()
    prior = np.array([
        Priors().a_01,
        Priors().b_01_surface,
        Priors().b_01_rivalry,
        Priors().b_01_contiguity,
        Priors().b_01_cap_shift,
        Priors().b_01_mutual,
        Priors().b_01_public,
    ], dtype=float)
    return x.to_numpy(dtype=float), y, list(x.columns), prior


def design_t12(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    x = pd.DataFrame({
        "intercept": 1.0,
        "leverage": _clip01(_num(df, "trade_leverage_a_over_b")),
        "import_leverage": _clip01(_num(df, "import_leverage_a_over_b")),
        "export_leverage": _clip01(_num(df, "export_leverage_a_over_b")),
        "surface": _clip01(_num(df, "trade_surface_norm_ab")),
        "rivalry": _clip01(_num(df, "rivalry_omega")),
        "public": _clip01(_num(df, "n_pub_a", 0.9)),
        "self_cost_suppress": -_clip01(_num(df, "dep_a_on_b")),
    })
    y = (df["uiw_tier_next"] >= 2).astype(int).to_numpy()
    prior = np.array([
        Priors().a_12,
        Priors().b_12_leverage,
        Priors().b_12_import_lev,
        Priors().b_12_export_lev,
        Priors().b_12_surface,
        Priors().b_12_rivalry,
        Priors().b_12_public,
        Priors().b_12_self_cost,
    ], dtype=float)
    return x.to_numpy(dtype=float), y, list(x.columns), prior


def design_t23(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    duration = _num(df, "d_k_years").clip(lower=0.0)
    x = pd.DataFrame({
        "intercept": 1.0,
        "duration": duration,
        "rivalry": _clip01(_num(df, "rivalry_omega")),
        "failed_coercion": (duration / 5.0).clip(0.0, 1.0),
        "proxy_access": _clip01(_num(df, "contiguity_xi")),
        "mutual_suppress": -_clip01(_num(df, "mutual_trade_dependence_ab")),
        "public_suppress": -_clip01(_num(df, "n_pub_a", 0.9)),
    })
    y = (df["uiw_tier_next"] >= 3).astype(int).to_numpy()
    prior = np.array([
        Priors().a_23,
        Priors().b_23_duration,
        Priors().b_23_rivalry,
        Priors().b_23_failed_coercion,
        Priors().b_23_proxy_access,
        Priors().b_23_mutual,
        Priors().b_23_public,
    ], dtype=float)
    return x.to_numpy(dtype=float), y, list(x.columns), prior


def design_any(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str], np.ndarray]:
    cap_shift = (_num(df, "c_t_ab", 0.5) - _num(df, "c_t_ba", 0.5)).abs().clip(0.0, 1.0)
    duration = _num(df, "d_k_years").clip(lower=0.0)
    x = pd.DataFrame({
        "intercept": 1.0,
        "current_tier": _num(df, "uiw_tier") / 5.0,
        "surface": _clip01(_num(df, "trade_surface_norm_ab")),
        "leverage": _clip01(_num(df, "trade_leverage_a_over_b")),
        "rivalry": _clip01(_num(df, "rivalry_omega")),
        "contiguity": _clip01(_num(df, "contiguity_xi")),
        "cap_shift": cap_shift,
        "duration": duration,
        "mutual_suppress": -_clip01(_num(df, "mutual_trade_dependence_ab")),
        "public_suppress": -_clip01(_num(df, "n_pub_a", 0.9)),
    })
    y = (df["uiw_tier_next"] > df["uiw_tier"]).astype(int).to_numpy()
    prior = np.zeros(x.shape[1], dtype=float)
    prior[0] = -4.0
    return x.to_numpy(dtype=float), y, list(x.columns), prior


def weighted_sample(df: pd.DataFrame, label: np.ndarray, neg_per_pos: int) -> tuple[pd.DataFrame, np.ndarray]:
    pos_idx = np.flatnonzero(label == 1)
    neg_idx = np.flatnonzero(label == 0)
    if len(pos_idx) == 0 or len(neg_idx) <= len(pos_idx) * neg_per_pos:
        return df, np.ones(len(df), dtype=float)
    rng = np.random.default_rng(RANDOM_STATE)
    n_neg = min(len(neg_idx), len(pos_idx) * neg_per_pos)
    keep_neg = rng.choice(neg_idx, size=n_neg, replace=False)
    keep = np.concatenate([pos_idx, keep_neg])
    weights = np.ones(len(keep), dtype=float)
    weights[len(pos_idx):] = len(neg_idx) / n_neg
    return df.iloc[keep].reset_index(drop=True), weights


def fit_block(
    name: str,
    df: pd.DataFrame,
    design: Callable[[pd.DataFrame], tuple[np.ndarray, np.ndarray, list[str], np.ndarray]],
    neg_per_pos: int,
    ridge: float,
    min_pos: int,
) -> dict:
    x_full, y_full, feature_names, prior = design(df)
    n_pos = int(y_full.sum())
    n_neg = int(len(y_full) - n_pos)
    if n_pos < min_pos or n_neg < min_pos:
        return {"block": name, "status": "skipped", "n_pos": n_pos, "n_neg": n_neg}

    fit_df, sample_weight = weighted_sample(df, y_full, neg_per_pos)
    x, y, _, _ = design(fit_df)
    bounds = [(-12.0, 4.0)] + [(0.0, 8.0)] * (x.shape[1] - 1)
    if name == "T2->T3+":
        bounds[1] = (0.0, 1.0)
    if name == "Any escalation diagnostic":
        bounds = [(-12.0, 4.0)] + [(-8.0, 8.0)] * (x.shape[1] - 1)

    def objective(beta: np.ndarray) -> float:
        z = x @ beta
        p = np.clip(_sigmoid(z), 1e-9, 1.0 - 1e-9)
        loss = -np.average(y * np.log(p) + (1 - y) * np.log(1 - p), weights=sample_weight)
        penalty = ridge * float(np.sum((beta - prior) ** 2))
        return loss + penalty

    res = minimize(objective, prior, method="L-BFGS-B", bounds=bounds, options={"maxiter": 1000})
    beta = res.x
    p_full = np.clip(_sigmoid(x_full @ beta), 1e-9, 1.0 - 1e-9)
    out = {
        "block": name,
        "status": "fit" if res.success else "failed",
        "message": res.message,
        "n_pos": n_pos,
        "n_neg": n_neg,
        "sample_rows": len(fit_df),
        "auc": np.nan,
        "brier": float(brier_score_loss(y_full, p_full)),
        "log_loss": float(log_loss(y_full, p_full, labels=[0, 1])),
        "features": feature_names,
        "prior": prior.tolist(),
        "coef": beta.tolist(),
    }
    if n_pos >= 5 and n_neg >= 5:
        out["auc"] = float(roc_auc_score(y_full, p_full))
    return out


def metric_rows(
    block: str,
    df: pd.DataFrame,
    beta: np.ndarray,
    design: Callable[[pd.DataFrame], tuple[np.ndarray, np.ndarray, list[str], np.ndarray]],
) -> list[dict]:
    rows = []
    for source in ["ALL"] + sorted(str(s) for s in df["trade_source"].dropna().unique()):
        sub = df if source == "ALL" else df[df["trade_source"] == source]
        if sub.empty:
            continue
        x, y, _, _ = design(sub)
        p = np.clip(_sigmoid(x @ beta), 1e-9, 1.0 - 1e-9)
        n_pos = int(y.sum())
        n_neg = int(len(y) - n_pos)
        row = {
            "block": block,
            "trade_source": source,
            "rows": len(sub),
            "n_pos": n_pos,
            "n_neg": n_neg,
            "auc": np.nan,
            "brier": np.nan,
            "log_loss": np.nan,
        }
        if n_pos >= 5 and n_neg >= 5:
            row["auc"] = float(roc_auc_score(y, p))
            row["brier"] = float(brier_score_loss(y, p))
            row["log_loss"] = float(log_loss(y, p, labels=[0, 1]))
        rows.append(row)
    return rows


def apply_coefficients(priors: Priors, fits: dict[str, dict]) -> dict:
    values = asdict(priors)
    if fits.get("T0->T1+", {}).get("status") == "fit":
        b = fits["T0->T1+"]["coef"]
        keys = ["a_01", "b_01_surface", "b_01_rivalry", "b_01_contiguity", "b_01_cap_shift", "b_01_mutual", "b_01_public"]
        values.update(dict(zip(keys, b)))
    if fits.get("T1->T2+", {}).get("status") == "fit":
        b = fits["T1->T2+"]["coef"]
        keys = ["a_12", "b_12_leverage", "b_12_import_lev", "b_12_export_lev", "b_12_surface", "b_12_rivalry", "b_12_public", "b_12_self_cost"]
        values.update(dict(zip(keys, b)))
    if fits.get("T2->T3+", {}).get("status") == "fit":
        b = fits["T2->T3+"]["coef"]
        keys = ["a_23", "b_23_duration", "b_23_rivalry", "b_23_failed_coercion", "b_23_proxy_access", "b_23_mutual", "b_23_public"]
        values.update(dict(zip(keys, b)))
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-through", type=int, default=TRAIN_SPLIT)
    parser.add_argument("--neg-per-pos", type=int, default=200)
    parser.add_argument("--ridge", type=float, default=0.02)
    parser.add_argument("--min-pos", type=int, default=20)
    args = parser.parse_args()

    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    df = load_data()
    train = df[df.year <= args.train_through].copy()
    test = df[df.year > args.train_through].copy()
    print(f"Rows: all={len(df):,}; train={len(train):,}; test={len(test):,}")
    print("Train trade sources:")
    print(train["trade_source"].value_counts(dropna=False).to_string())

    blocks = {
        "T0->T1+": (train[train.uiw_tier == 0].copy(), design_t01),
        "T1->T2+": (train[train.uiw_tier == 1].copy(), design_t12),
        "T2->T3+": (train[train.uiw_tier == 2].copy(), design_t23),
        "Any escalation diagnostic": (train[train.uiw_tier < 5].copy(), design_any),
    }
    fits: dict[str, dict] = {}
    source_rows: list[dict] = []
    for name, (sub, design) in blocks.items():
        print(f"\nFitting {name}: {len(sub):,} eligible rows")
        fit = fit_block(name, sub, design, args.neg_per_pos, args.ridge, args.min_pos)
        fits[name] = fit
        print(f"  status={fit['status']} pos={fit['n_pos']:,} neg={fit['n_neg']:,}")
        if fit.get("status") == "fit":
            print(f"  train AUC={fit['auc']:.4f} Brier={fit['brier']:.4f}")
            beta = np.array(fit["coef"], dtype=float)
            train_source_rows = metric_rows(name, sub, beta, design)
            for row in train_source_rows:
                row["split"] = "train"
            source_rows.extend(train_source_rows)
            eligible_test = test[test.uiw_tier == int(name[1])].copy() if name.startswith("T") else test[test.uiw_tier < 5].copy()
            test_source_rows = metric_rows(name, eligible_test, beta, design)
            for row in test_source_rows:
                row["split"] = "test"
            source_rows.extend(test_source_rows)

    fit_rows = []
    for name, fit in fits.items():
        row = {k: v for k, v in fit.items() if k not in {"features", "prior", "coef", "message"}}
        row["message"] = str(fit.get("message", ""))
        fit_rows.append(row)

    fit_summary_path = os.path.join(OUT_ANALYSIS, "v28_calibration_fit_summary.csv")
    pd.DataFrame(fit_rows).to_csv(fit_summary_path, index=False)
    source_path = os.path.join(OUT_ANALYSIS, "v28_calibration_source_breakdown.csv")
    pd.DataFrame(source_rows).to_csv(source_path, index=False)

    calibrated = apply_coefficients(Priors(), fits)
    priors_path = os.path.join(OUT_ANALYSIS, "tiers_v28_calibrated_priors.json")
    payload = {
        "metadata": {
            "model": "TIERS v28",
            "train_year_min": YEAR_LO,
            "train_year_max": args.train_through,
            "calibration_method": "sign-constrained logistic hazard blocks with ridge shrinkage to hand priors",
            "trade_source_of_truth": "data/processed/trade_interdependence",
            "applied_blocks": [name for name, fit in fits.items() if name != "Any escalation diagnostic" and fit.get("status") == "fit"],
        },
        "priors": calibrated,
        "fits": fits,
    }
    with open(priors_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\nWrote {priors_path}")
    print(f"Wrote {fit_summary_path}")
    print(f"Wrote {source_path}")
    print("\nEvaluate with:")
    print(f"  python scripts/model/backtest_tiers_v28.py --priors {priors_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
