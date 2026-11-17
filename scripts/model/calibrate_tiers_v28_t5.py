"""Calibrate v28 T5-specific risks against reconciled P(T5)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from dataclasses import asdict
from typing import Sequence

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
from tiers_lib_v28 import Priors, priors_from_mapping, score_dataframe_v28

YEAR_LO, YEAR_HI = 1946, 2014
TRAIN_SPLIT = 1989
RANDOM_STATE = 42

SKIP_KEYS = ["skip_base", "skip_structural", "skip_shock", "skip_fma", "skip_reach", "skip_mutual", "lambda_skip"]
T45_KEYS = ["a_45", "b_45_reach", "b_45_rivalry", "b_45_fma", "b_45_stakes", "b_45_mobilization", "b_45_mutual", "b_45_public"]


def load_data() -> pd.DataFrame:
    df, _ = load_feature_grid("v28", year_lo=YEAR_LO, year_hi=YEAR_HI)
    return df


def load_priors(path: str | None) -> Priors:
    if not path:
        return Priors()
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return priors_from_mapping(payload.get("priors", payload))


def with_values(base: Priors, keys: Sequence[str], beta: np.ndarray) -> Priors:
    values = asdict(base)
    values.update({k: float(v) for k, v in zip(keys, beta)})
    return priors_from_mapping(values)


def score_t5(df: pd.DataFrame, priors: Priors) -> np.ndarray:
    out = score_dataframe_v28(df, priors)["pi"][:, 5]
    return np.clip(out, 1e-9, 1.0 - 1e-9)


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    n_pos = int(y.sum())
    n_neg = int(len(y) - n_pos)
    row = {"n_pos": n_pos, "n_neg": n_neg, "auc": np.nan, "brier": np.nan, "log_loss": np.nan}
    if n_pos >= 5 and n_neg >= 5:
        row["auc"] = float(roc_auc_score(y, p))
        row["brier"] = float(brier_score_loss(y, p))
        row["log_loss"] = float(log_loss(y, p, labels=[0, 1]))
    return row


def sample_rows(df: pd.DataFrame, y: np.ndarray, neg_per_pos: int, max_rows: int) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    pos_idx = np.flatnonzero(y == 1)
    neg_idx = np.flatnonzero(y == 0)
    if len(pos_idx) == 0:
        return df.iloc[[]].copy(), np.array([], dtype=int), np.array([], dtype=float)
    rng = np.random.default_rng(RANDOM_STATE)
    n_neg = min(len(neg_idx), len(pos_idx) * neg_per_pos)
    if len(pos_idx) + n_neg > max_rows:
        n_neg = max(0, max_rows - len(pos_idx))
    keep_neg = rng.choice(neg_idx, size=n_neg, replace=False) if n_neg else np.array([], dtype=int)
    keep = np.concatenate([pos_idx, keep_neg])
    weights = np.ones(len(keep), dtype=float)
    if n_neg and len(neg_idx) > n_neg:
        weights[len(pos_idx):] = len(neg_idx) / n_neg
    return df.iloc[keep].reset_index(drop=True), y[keep], weights


def fit_block(name: str, train: pd.DataFrame, test: pd.DataFrame, base: Priors, keys: Sequence[str], neg_per_pos: int, max_rows: int, ridge: float, min_pos: int) -> tuple[Priors, dict, list[dict]]:
    y_full = (train["uiw_tier_next"] == 5).astype(int).to_numpy()
    y_test = (test["uiw_tier_next"] == 5).astype(int).to_numpy()
    if int(y_full.sum()) < min_pos:
        return base, {"block": name, "status": "skipped", "message": f"too few positives ({int(y_full.sum())} < {min_pos})", **metrics(y_full, np.zeros_like(y_full, dtype=float))}, []
    sample, y, weights = sample_rows(train, y_full, neg_per_pos, max_rows)
    prior = np.array([getattr(base, k) for k in keys], dtype=float)
    bounds = [(-10.0, 2.0)] + [(0.0, 8.0)] * (len(keys) - 1)
    if "lambda_skip" in keys:
        bounds[-1] = (0.05, 4.0)

    def objective(beta: np.ndarray) -> float:
        priors = with_values(base, keys, beta)
        p = score_t5(sample, priors)
        loss = -np.average(y * np.log(p) + (1 - y) * np.log(1 - p), weights=weights)
        return loss + ridge * float(np.sum((beta - prior) ** 2))

    res = minimize(objective, prior, method="L-BFGS-B", bounds=bounds, options={"maxiter": 120})
    fitted = with_values(base, keys, res.x)
    fit = {
        "block": name,
        "status": "fit" if res.success else "failed",
        "message": str(res.message),
        "sample_rows": len(sample),
        "sample_pos": int(y.sum()),
        "sample_neg": int(len(y) - y.sum()),
        "keys": list(keys),
        "prior": prior.tolist(),
        "coef": res.x.tolist(),
        **{f"sample_{k}": v for k, v in metrics(y, score_t5(sample, fitted)).items()},
    }
    rows = []
    for split, sub, yy in [("train_sample", sample, y), ("test", test, y_test)]:
        if sub.empty:
            continue
        for source in ["ALL"] + sorted(str(s) for s in sub["trade_source"].dropna().unique()):
            mask = np.ones(len(sub), dtype=bool) if source == "ALL" else (sub["trade_source"].to_numpy() == source)
            sub2 = sub if source == "ALL" else sub[mask]
            rows.append({"block": name, "split": split, "trade_source": source, "rows": len(sub2), **metrics(yy[mask], score_t5(sub2, fitted))})
    return fitted, fit, rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--starting-priors")
    parser.add_argument("--include-none", action="store_true")
    parser.add_argument("--targets", default="t0,t4")
    parser.add_argument("--min-pos", type=int, default=5)
    parser.add_argument("--neg-per-pos", type=int, default=100)
    parser.add_argument("--max-rows", type=int, default=8000)
    parser.add_argument("--ridge", type=float, default=0.05)
    parser.add_argument("--output-prefix", default="v28_t5")
    args = parser.parse_args()

    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    df = load_data()
    if not args.include_none:
        df = df[df.trade_source != "NONE"].copy()
    train_all = df[df.year <= TRAIN_SPLIT].copy()
    test_all = df[df.year > TRAIN_SPLIT].copy()
    priors = load_priors(args.starting_priors)
    fits = []
    rows = []
    for target in [t.strip().lower() for t in args.targets.split(",") if t.strip()]:
        if target == "t0":
            name, tier, keys = "T0->T5 engine", 0, SKIP_KEYS
        elif target == "t4":
            name, tier, keys = "T4->T5 engine", 4, T45_KEYS
        else:
            print(f"Skipping unknown target {target}")
            continue
        train = train_all[train_all.uiw_tier == tier].copy()
        test = test_all[test_all.uiw_tier == tier].copy()
        print(f"\nFitting {name}: train rows={len(train):,}; positives={(train.uiw_tier_next == 5).sum():,}")
        priors, fit, source_rows = fit_block(name, train, test, priors, keys, args.neg_per_pos, args.max_rows, args.ridge, args.min_pos)
        fits.append(fit)
        rows.extend(source_rows)
        print(f"  status={fit['status']} sample_auc={fit.get('sample_auc', np.nan):.4f} sample_brier={fit.get('sample_brier', np.nan):.4f}")

    priors_path = os.path.join(OUT_ANALYSIS, f"tiers_{args.output_prefix}_calibrated_priors.json")
    with open(priors_path, "w", encoding="utf-8") as f:
        json.dump({"metadata": {"model": "TIERS v28", "calibration_method": "T5 reconciled P(T5)", "targets": args.targets, "include_none": args.include_none}, "priors": asdict(priors), "fits": fits}, f, indent=2)
    fit_path = os.path.join(OUT_ANALYSIS, f"{args.output_prefix}_calibration_fit_summary.csv")
    pd.DataFrame([{k: v for k, v in fit.items() if k not in {"keys", "prior", "coef"}} for fit in fits]).to_csv(fit_path, index=False)
    source_path = os.path.join(OUT_ANALYSIS, f"{args.output_prefix}_calibration_source_breakdown.csv")
    pd.DataFrame(rows).to_csv(source_path, index=False)
    print(f"\nWrote {priors_path}")
    print(f"Wrote {fit_path}")
    print(f"Wrote {source_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
