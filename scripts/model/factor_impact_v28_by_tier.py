"""Univariate factor-impact backtest by current tier for TIERS v28.

For each current conflict tier, this script asks how much each single factor
explains next-year escalation, persistence, or de-escalation by itself. The
models are deliberately simple one-factor logistic regressions so the output is
interpretable as a factor screen, not as a replacement for the TIERS engine.

Writes:
  output/analysis/factor_impact_v28_by_tier.csv
  output/analysis/factor_impact_v28_by_tier_summary.md
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from evaluation import load_feature_grid

YEAR_LO, YEAR_HI = 1946, 2014
TRAIN_SPLIT = 1989
RANDOM_STATE = 42
MIN_POS = 5
MIN_NEG = 5

FACTOR_COLUMNS = [
    "contiguity_xi",
    "fma",
    "rivalry_omega",
    "d_k_years",
    "cap_a_to_b",
    "cap_b_to_a",
    "closing_window_a",
    "closing_window_b",
    "n_pub_a",
    "n_pub_b",
    "c_t_ab",
    "c_t_ba",
    "trade_surface_norm_ab",
    "dep_a_on_b",
    "dep_b_on_a",
    "mutual_trade_dependence_ab",
    "import_leverage_a_over_b",
    "export_leverage_a_over_b",
    "trade_leverage_a_over_b",
]

OUTCOMES = ["escalate", "same", "deescalate"]


def load_data() -> pd.DataFrame:
    df, _ = load_feature_grid("v28", year_lo=YEAR_LO, year_hi=YEAR_HI)
    df["tier_delta"] = df["uiw_tier_next"] - df["uiw_tier"]
    df["escalate"] = (df["tier_delta"] > 0).astype(int)
    df["same"] = (df["tier_delta"] == 0).astype(int)
    df["deescalate"] = (df["tier_delta"] < 0).astype(int)
    return df


def available_factors(df: pd.DataFrame, requested: list[str] | None) -> list[str]:
    candidates = requested or FACTOR_COLUMNS
    return [c for c in candidates if c in df.columns]


def sample_tier(df: pd.DataFrame, max_rows: int) -> pd.DataFrame:
    if max_rows <= 0 or len(df) <= max_rows:
        return df.reset_index(drop=True)
    return df.sample(max_rows, random_state=RANDOM_STATE).reset_index(drop=True)


def base_scores(y: np.ndarray) -> np.ndarray:
    p = float(np.mean(y)) if len(y) else 0.0
    return np.full(len(y), np.clip(p, 1e-9, 1.0 - 1e-9), dtype=float)


def metric_values(y: np.ndarray, p: np.ndarray) -> dict:
    n_pos = int(y.sum())
    n_neg = int(len(y) - n_pos)
    out = {
        "auc": np.nan,
        "brier": np.nan,
        "log_loss": np.nan,
        "n_pos": n_pos,
        "n_neg": n_neg,
    }
    if n_pos >= MIN_POS and n_neg >= MIN_NEG:
        p = np.clip(p, 1e-9, 1.0 - 1e-9)
        out["auc"] = float(roc_auc_score(y, p))
        out["brier"] = float(brier_score_loss(y, p))
        out["log_loss"] = float(log_loss(y, p, labels=[0, 1]))
    return out


def fit_factor(
    train: pd.DataFrame,
    test: pd.DataFrame,
    tier: int,
    outcome: str,
    factor: str,
    class_weight: str | None,
) -> dict:
    y_train = train[outcome].astype(int).to_numpy()
    y_test = test[outcome].astype(int).to_numpy()
    base_p = base_scores(y_test)
    base = metric_values(y_test, base_p)
    row = {
        "current_tier": tier,
        "outcome": outcome,
        "factor": factor,
        "rows_train": len(train),
        "rows_test": len(test),
        "n_pos_train": int(y_train.sum()),
        "n_neg_train": int(len(y_train) - y_train.sum()),
        "n_pos_test": base["n_pos"],
        "n_neg_test": base["n_neg"],
        "base_rate_train": float(np.mean(y_train)) if len(y_train) else np.nan,
        "base_rate_test": float(np.mean(y_test)) if len(y_test) else np.nan,
        "coef_std": np.nan,
        "odds_ratio_per_sd": np.nan,
        "auc": np.nan,
        "brier": np.nan,
        "log_loss": np.nan,
        "base_brier": base["brier"],
        "base_log_loss": base["log_loss"],
        "brier_delta_vs_base": np.nan,
        "log_loss_delta_vs_base": np.nan,
        "mcfadden_r2_vs_base": np.nan,
        "status": "skipped",
    }

    if row["n_pos_train"] < MIN_POS or row["n_neg_train"] < MIN_NEG:
        row["status"] = "skipped_train_sparse"
        return row
    if row["n_pos_test"] < MIN_POS or row["n_neg_test"] < MIN_NEG:
        row["status"] = "skipped_test_sparse"
        return row

    x_train = train[[factor]].apply(pd.to_numeric, errors="coerce")
    x_test = test[[factor]].apply(pd.to_numeric, errors="coerce")
    if x_train[factor].notna().sum() < MIN_POS + MIN_NEG:
        row["status"] = "skipped_factor_missing"
        return row
    if x_train[factor].nunique(dropna=True) < 2:
        row["status"] = "skipped_factor_constant"
        return row

    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(max_iter=2000, class_weight=class_weight, random_state=RANDOM_STATE),
    )
    model.fit(x_train, y_train)
    p = model.predict_proba(x_test)[:, 1]
    metrics = metric_values(y_test, p)
    coef = float(model.named_steps["logisticregression"].coef_[0][0])

    row.update({
        "coef_std": coef,
        "odds_ratio_per_sd": float(math.exp(coef)) if abs(coef) < 700 else np.nan,
        "auc": metrics["auc"],
        "brier": metrics["brier"],
        "log_loss": metrics["log_loss"],
        "brier_delta_vs_base": base["brier"] - metrics["brier"],
        "log_loss_delta_vs_base": base["log_loss"] - metrics["log_loss"],
        "mcfadden_r2_vs_base": 1.0 - (metrics["log_loss"] / base["log_loss"]),
        "status": "fit",
    })
    return row


def evaluate(
    df: pd.DataFrame,
    factors: list[str],
    max_rows_per_tier: int,
    class_weight: str | None,
) -> pd.DataFrame:
    rows: list[dict] = []
    train_all = df[df.year <= TRAIN_SPLIT].copy()
    test_all = df[df.year > TRAIN_SPLIT].copy()

    for tier in range(6):
        train = sample_tier(train_all[train_all.uiw_tier == tier].copy(), max_rows_per_tier)
        test = sample_tier(test_all[test_all.uiw_tier == tier].copy(), max_rows_per_tier)
        if train.empty or test.empty:
            continue
        print(f"T{tier}: train={len(train):,}; test={len(test):,}")
        for outcome in OUTCOMES:
            for factor in factors:
                rows.append(fit_factor(train, test, tier, outcome, factor, class_weight))
    return pd.DataFrame(rows)


def fmt(value: float, digits: int = 4) -> str:
    if pd.isna(value):
        return "NA"
    return f"{float(value):.{digits}f}"


def output_stem(tag: str | None) -> str:
    return "factor_impact_v28_by_tier" + (f"_{tag}" if tag else "")


def write_summary(out: pd.DataFrame, factors: list[str], class_weight: str | None, max_rows_per_tier: int, tag: str | None) -> None:
    lines = [
        "# v28 factor impact by current tier",
        "",
        "Each row fits one factor by itself on 1946-1989 dyad-years and evaluates on 1990-2014.",
        "Outcomes are one-vs-rest within the same current tier: escalation, persistence, and de-escalation.",
        "Impact is ranked by held-out log-loss improvement over a base-rate-only model.",
        "",
        f"Class weight: `{class_weight or 'natural'}`.",
        f"Max sampled rows per split/tier: `{max_rows_per_tier if max_rows_per_tier > 0 else 'none'}`.",
        "",
        "Factors: `" + "`, `".join(factors) + "`.",
        "",
        "## Top Factors",
        "",
    ]

    fitted = out[out.status == "fit"].copy()
    if fitted.empty:
        lines.append("No factor/outcome cells had enough train and test variation to fit.")
    else:
        for tier in sorted(fitted.current_tier.unique()):
            lines.extend([f"### T{int(tier)}", ""])
            for outcome in OUTCOMES:
                block = fitted[(fitted.current_tier == tier) & (fitted.outcome == outcome)].copy()
                if block.empty:
                    lines.extend([f"No fitted `{outcome}` models.", ""])
                    continue
                block = block.sort_values(
                    ["log_loss_delta_vs_base", "auc"],
                    ascending=[False, False],
                ).head(8)
                lines.extend([
                    f"**{outcome}**",
                    "",
                    "| Factor | AUC | Log-loss gain | Brier gain | Odds ratio / SD | Test positives | Test negatives |",
                    "|---|---:|---:|---:|---:|---:|---:|",
                ])
                for r in block.itertuples(index=False):
                    lines.append(
                        f"| {r.factor} | {fmt(r.auc)} | {fmt(r.log_loss_delta_vs_base)} | "
                        f"{fmt(r.brier_delta_vs_base)} | {fmt(r.odds_ratio_per_sd)} | "
                        f"{int(r.n_pos_test)} | {int(r.n_neg_test)} |"
                    )
                lines.append("")

    skipped = out[out.status != "fit"]
    if not skipped.empty:
        lines.extend([
            "## Skipped Cells",
            "",
            "Sparse outcomes are expected at high tiers. Counts by skip reason:",
            "",
            "| Status | Count |",
            "|---|---:|",
        ])
        for status, count in skipped.status.value_counts().items():
            lines.append(f"| {status} | {int(count)} |")
        lines.append("")

    path = os.path.join(OUT_ANALYSIS, f"{output_stem(tag)}_summary.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-rows-per-tier",
        type=int,
        default=0,
        help="Optional random row cap per split/current tier. Default 0 uses all rows.",
    )
    parser.add_argument(
        "--class-weight",
        choices=["natural", "balanced"],
        default="natural",
        help="Use natural class frequencies for calibrated probabilities, or balanced for ranking rare outcomes.",
    )
    parser.add_argument(
        "--factors",
        help="Optional comma-separated factor columns. Defaults to the v28 structural/economic factor list.",
    )
    parser.add_argument(
        "--tag",
        help="Optional output suffix, e.g. 'ucdp_interstate'.",
    )
    args = parser.parse_args()

    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    print("Loading v28 feature grid...")
    df = load_data()
    requested = [s.strip() for s in args.factors.split(",") if s.strip()] if args.factors else None
    factors = available_factors(df, requested)
    if not factors:
        raise SystemExit("No requested factor columns are present in the v28 feature grid.")

    class_weight = None if args.class_weight == "natural" else "balanced"
    print(f"Evaluating {len(factors)} factors by current tier...")
    out = evaluate(df, factors, args.max_rows_per_tier, class_weight)

    csv_path = os.path.join(OUT_ANALYSIS, f"{output_stem(args.tag)}.csv")
    out.to_csv(csv_path, index=False)
    print(f"Wrote {csv_path}")
    write_summary(out, factors, args.class_weight, args.max_rows_per_tier, args.tag)

    fitted = out[out.status == "fit"].copy()
    if not fitted.empty:
        display = fitted.sort_values(["current_tier", "outcome", "log_loss_delta_vs_base"], ascending=[True, True, False])
        print("\nTop fitted rows:")
        print(display.groupby(["current_tier", "outcome"]).head(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
