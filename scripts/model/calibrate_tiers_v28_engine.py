"""Calibrate TIERS v28 against reconciled engine probabilities.

The faster `calibrate_tiers_v28.py` fits standalone transition logits. This
script instead optimizes the actual reconciled probability scores emitted by
the v28 engine, matching the quantities used in `backtest_tiers_v28.py`.
"""
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

from backtest_tiers_v28 import V28Calibrator
from evaluation import load_feature_grid
from tiers_lib_v28 import Priors, priors_from_mapping

YEAR_LO, YEAR_HI = 1946, 2014
TRAIN_SPLIT = 1989
RANDOM_STATE = 42

T01_KEYS = [
    "a_01",
    "b_01_surface",
    "b_01_rivalry",
    "b_01_contiguity",
    "b_01_cap_shift",
    "b_01_mutual",
    "b_01_public",
]
T12_KEYS = [
    "a_12",
    "b_12_leverage",
    "b_12_import_lev",
    "b_12_export_lev",
    "b_12_surface",
    "b_12_rivalry",
    "b_12_public",
    "b_12_self_cost",
]
T23_KEYS = [
    "a_23",
    "b_23_duration",
    "b_23_rivalry",
    "b_23_failed_coercion",
    "b_23_proxy_access",
    "b_23_mutual",
    "b_23_public",
]
T34_KEYS = [
    "a_34",
    "b_34_attr_dur",
    "b_34_rivalry",
    "b_34_contiguity",
    "b_34_fma",
    "b_34_closing",
    "b_34_mutual",
    "b_34_trade_cost",
    "b_34_public",
]
T45_KEYS = [
    "a_45",
    "b_45_reach",
    "b_45_rivalry",
    "b_45_fma",
    "b_45_stakes",
    "b_45_mobilization",
    "b_45_mutual",
    "b_45_public",
]

TIER_BLOCKS = {
    0: ("T0->T1+ engine", T01_KEYS),
    1: ("T1->T2+ engine", T12_KEYS),
    2: ("T2->T3+ engine", T23_KEYS),
    3: ("T3->T4+ engine", T34_KEYS),
    4: ("T4->T5 engine", T45_KEYS),
}
DEFAULT_NEG_PER_POS = {0: 40, 1: 10, 2: 5, 3: 5, 4: 5}
DEFAULT_MAX_ROWS = {0: 8000, 1: 8000, 2: 8000, 3: 8000, 4: 8000}


def load_data() -> pd.DataFrame:
    df, _ = load_feature_grid("v28", year_lo=YEAR_LO, year_hi=YEAR_HI)
    return df


def load_starting_priors(path: str | None) -> Priors:
    if not path:
        return Priors()
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return priors_from_mapping(payload.get("priors", payload))


def sample_fit_rows(df: pd.DataFrame, y: np.ndarray, neg_per_pos: int, max_rows: int) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
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


def priors_with(base: Priors, keys: Sequence[str], beta: np.ndarray) -> Priors:
    values = asdict(base)
    values.update({k: float(v) for k, v in zip(keys, beta)})
    return priors_from_mapping(values)


def engine_scores(sample: pd.DataFrame, priors: Priors, score_kind: str) -> np.ndarray:
    cal = V28Calibrator(priors)
    out = np.zeros(len(sample), dtype=float)
    for i, (_, row) in enumerate(sample.iterrows()):
        pi = cal.score_row(row)["pi_reconciled"]
        if score_kind == "t0_t1_plus":
            out[i] = 1.0 - pi[0]
        elif score_kind == "t1_t2_plus":
            out[i] = pi[2] + pi[3] + pi[4] + pi[5]
        elif score_kind.startswith("tier_"):
            k = int(score_kind.split("_")[1])
            out[i] = sum(pi[k + 1:]) if k < 5 else 0.0
        elif score_kind == "any_escalation":
            k = int(row["uiw_tier"])
            out[i] = sum(pi[k + 1:]) if k < 5 else 0.0
        else:
            raise ValueError(score_kind)
    return np.clip(out, 1e-9, 1.0 - 1e-9)


def metrics(y: np.ndarray, p: np.ndarray) -> dict:
    n_pos = int(y.sum())
    n_neg = int(len(y) - n_pos)
    out = {"n_pos": n_pos, "n_neg": n_neg, "auc": np.nan, "brier": np.nan, "log_loss": np.nan}
    if n_pos >= 5 and n_neg >= 5:
        out["auc"] = float(roc_auc_score(y, p))
        out["brier"] = float(brier_score_loss(y, p))
        out["log_loss"] = float(log_loss(y, p, labels=[0, 1]))
    return out


def parse_tier_ints(spec: str | None, default: dict[int, int]) -> dict[int, int]:
    out = dict(default)
    if not spec:
        return out
    for part in spec.split(","):
        if not part.strip():
            continue
        k, v = part.split(":", 1)
        out[int(k.strip())] = int(v.strip())
    return out


def fit_engine_block(
    name: str,
    train: pd.DataFrame,
    test: pd.DataFrame,
    base_priors: Priors,
    keys: Sequence[str],
    tier: int,
    neg_per_pos: int,
    max_rows: int,
    ridge: float,
) -> tuple[Priors, dict, list[dict]]:
    y_train_full = (train["uiw_tier_next"] >= tier + 1).astype(int).to_numpy()
    y_test = (test["uiw_tier_next"] >= tier + 1).astype(int).to_numpy()
    score_kind = f"tier_{tier}_plus"

    sample, y_sample, weights = sample_fit_rows(train, y_train_full, neg_per_pos, max_rows)
    prior_beta = np.array([getattr(base_priors, k) for k in keys], dtype=float)
    if len(sample) == 0 or int(y_sample.sum()) < 5:
        return base_priors, {"block": name, "status": "skipped", "n_pos": int(y_train_full.sum()), "n_neg": int(len(y_train_full) - y_train_full.sum())}, []

    bounds = [(-8.0, 2.0)] + [(0.0, 6.0)] * (len(keys) - 1)
    if tier == 2:
        bounds[1] = (0.0, 1.0)

    def objective(beta: np.ndarray) -> float:
        priors = priors_with(base_priors, keys, beta)
        p = engine_scores(sample, priors, score_kind)
        loss = -np.average(y_sample * np.log(p) + (1 - y_sample) * np.log(1 - p), weights=weights)
        return loss + ridge * float(np.sum((beta - prior_beta) ** 2))

    res = minimize(objective, prior_beta, method="L-BFGS-B", bounds=bounds, options={"maxiter": 120})
    fitted_priors = priors_with(base_priors, keys, res.x)
    train_score = engine_scores(sample, fitted_priors, score_kind)
    test_score = engine_scores(test, fitted_priors, score_kind) if len(test) else np.array([], dtype=float)
    fit = {
        "block": name,
        "status": "fit" if res.success else "failed",
        "message": str(res.message),
        "sample_rows": len(sample),
        "sample_pos": int(y_sample.sum()),
        "sample_neg": int(len(y_sample) - y_sample.sum()),
        "objective": float(res.fun),
        "keys": list(keys),
        "prior": prior_beta.tolist(),
        "coef": res.x.tolist(),
        **{f"sample_{k}": v for k, v in metrics(y_sample, train_score).items()},
    }

    source_rows = []
    for split, sub, y in [("train_sample", sample, y_sample), ("test", test, y_test)]:
        if sub.empty:
            continue
        for source in ["ALL"] + sorted(str(s) for s in sub["trade_source"].dropna().unique()):
            sub2 = sub if source == "ALL" else sub[sub["trade_source"] == source]
            if sub2.empty:
                continue
            if split == "train_sample":
                mask = np.ones(len(sub2), dtype=bool) if source == "ALL" else (sub["trade_source"].to_numpy() == source)
                yy = y if source == "ALL" else y[mask]
            else:
                mask = np.ones(len(sub2), dtype=bool) if source == "ALL" else (sub["trade_source"].to_numpy() == source)
                yy = y if source == "ALL" else y[mask]
            pp = engine_scores(sub2, fitted_priors, score_kind)
            row = {"block": name, "split": split, "trade_source": source, "rows": len(sub2), **metrics(yy, pp)}
            source_rows.append(row)
    return fitted_priors, fit, source_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--starting-priors", help="Optional priors JSON to start from.")
    parser.add_argument("--train-through", type=int, default=TRAIN_SPLIT)
    parser.add_argument(
        "--tier-neg-per-pos",
        default="0:40,1:10,2:5,3:5,4:5",
        help="Comma-separated tier:negative-per-positive sampling ratios.",
    )
    parser.add_argument(
        "--tier-max-rows",
        default="0:8000,1:8000,2:8000,3:8000,4:8000",
        help="Comma-separated tier:max sampled fitting rows.",
    )
    parser.add_argument("--ridge", type=float, default=0.03)
    parser.add_argument("--min-pos", type=int, default=20)
    parser.add_argument("--tiers", default="0,1,2,3,4", help="Comma-separated current tiers to fit.")
    parser.add_argument("--output-prefix", default="v28_engine", help="Prefix for output artifact filenames.")
    parser.add_argument("--include-none", action="store_true", help="Include rows with no observed trade. These mostly use the v27 fallback.")
    args = parser.parse_args()

    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    df = load_data()
    if not args.include_none:
        df = df[df.trade_source != "NONE"].copy()
    train_all = df[df.year <= args.train_through].copy()
    test_all = df[df.year > args.train_through].copy()
    priors = load_starting_priors(args.starting_priors)
    neg_per_pos_by_tier = parse_tier_ints(args.tier_neg_per_pos, DEFAULT_NEG_PER_POS)
    max_rows_by_tier = parse_tier_ints(args.tier_max_rows, DEFAULT_MAX_ROWS)
    tiers = [int(t.strip()) for t in args.tiers.split(",") if t.strip()]

    print(f"Rows: train={len(train_all):,}; test={len(test_all):,}; include_none={args.include_none}")
    print("Train trade sources:")
    print(train_all["trade_source"].value_counts(dropna=False).to_string())

    fits = []
    source_rows = []

    for tier in tiers:
        if tier not in TIER_BLOCKS:
            print(f"\nSkipping unsupported tier {tier}")
            continue
        name, keys = TIER_BLOCKS[tier]
        train = train_all[train_all.uiw_tier == tier].copy()
        test = test_all[test_all.uiw_tier == tier].copy()
        n_pos = int((train["uiw_tier_next"] >= tier + 1).sum())
        print(f"\nEngine-fitting {name} on {len(train):,} train rows; positives={n_pos:,}")
        if n_pos < args.min_pos:
            fit = {
                "block": name,
                "status": "skipped",
                "message": f"fewer than --min-pos positives ({n_pos} < {args.min_pos})",
                "sample_rows": 0,
                "sample_pos": n_pos,
                "sample_neg": int(len(train) - n_pos),
            }
            fits.append(fit)
            print(f"  status=skipped reason={fit['message']}")
            continue
        priors, fit, rows = fit_engine_block(
            name,
            train,
            test,
            priors,
            keys,
            tier,
            neg_per_pos_by_tier.get(tier, DEFAULT_NEG_PER_POS[tier]),
            max_rows_by_tier.get(tier, DEFAULT_MAX_ROWS[tier]),
            args.ridge,
        )
        fits.append(fit)
        source_rows.extend(rows)
        print(f"  status={fit['status']} sample_auc={fit.get('sample_auc', np.nan):.4f} sample_brier={fit.get('sample_brier', np.nan):.4f}")

    priors_path = os.path.join(OUT_ANALYSIS, f"tiers_{args.output_prefix}_calibrated_priors.json")
    payload = {
        "metadata": {
            "model": "TIERS v28",
            "calibration_method": "reconciled-engine-probability optimization",
            "train_year_min": YEAR_LO,
            "train_year_max": args.train_through,
            "include_none": args.include_none,
            "tier_neg_per_pos": neg_per_pos_by_tier,
            "tier_max_rows": max_rows_by_tier,
            "ridge": args.ridge,
            "starting_priors": args.starting_priors,
            "trade_source_of_truth": "data/processed/trade_interdependence",
        },
        "priors": asdict(priors),
        "fits": fits,
    }
    with open(priors_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    fit_path = os.path.join(OUT_ANALYSIS, f"{args.output_prefix}_calibration_fit_summary.csv")
    pd.DataFrame([{k: v for k, v in fit.items() if k not in {"keys", "prior", "coef"}} for fit in fits]).to_csv(fit_path, index=False)
    source_path = os.path.join(OUT_ANALYSIS, f"{args.output_prefix}_calibration_source_breakdown.csv")
    pd.DataFrame(source_rows).to_csv(source_path, index=False)
    print(f"\nWrote {priors_path}")
    print(f"Wrote {fit_path}")
    print(f"Wrote {source_path}")
    print("\nEvaluate with:")
    print(f"  .venv/bin/python scripts/model/backtest_tiers_v28.py --priors {priors_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
