"""Baseline comparisons for the TIERS v27.0 backtest.

This script compares the v27 diagnostic-fallback engine against flat
statistical baselines trained on the same v27 feature grid and the same
1946-1989 / 1990-2014 temporal split used by `backtest_tiers_v27.py`.

Baselines:
  - Logistic regression, natural class weights.
  - Logistic regression, balanced class weights.
  - Random forest, balanced class weights.

The goal is not to replace the engine. It is to check whether the current
diagnostic-fallback results outperform simple models using the same structural
inputs.

Reads:
  data/processed/dyads_with_features_v27.parquet
  output/analysis/model_backtest_roc_v27_test.csv

Writes:
  output/analysis/baseline_comparison_v27.csv
  output/analysis/baseline_summary_v27.md
"""
from __future__ import annotations

import os
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")

YEAR_LO, YEAR_HI = 1946, 2014
TRAIN_SPLIT = 1989
SAMPLE_TRAIN = 200_000
SAMPLE_TEST = 200_000
RANDOM_STATE = 42

FEATURES = [
    "uiw_tier",
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
]


def load_data() -> pd.DataFrame:
    path_pq = os.path.join(DATA_PROCESSED, "dyads_with_features_v27.parquet")
    path_csv = os.path.join(DATA_PROCESSED, "dyads_with_features_v27.csv")
    if os.path.exists(path_pq):
        df = pd.read_parquet(path_pq)
    else:
        df = pd.read_csv(path_csv, dtype={"year": int})

    df = df[(df.year >= YEAR_LO) & (df.year <= YEAR_HI)].copy()
    df = df.sort_values("year")
    next_tier = df.groupby(["initiator", "target"])["uiw_tier"].shift(-1)
    df["uiw_tier_next"] = next_tier
    next_tier_filled = df["uiw_tier_next"].fillna(0)
    df["escalate"] = (next_tier_filled > df["uiw_tier"]).astype(int)
    df["escalate_to_t1_plus"] = (
        (df["uiw_tier"] == 0) & (next_tier_filled >= 1)
    ).astype(int)
    df["escalate_to_t4_plus"] = (
        (df["uiw_tier"] <= 3) & (next_tier_filled >= 4)
    ).astype(int)
    df["escalate_to_t5"] = (next_tier_filled == 5).astype(int)
    df = df.dropna(subset=["uiw_tier_next"]).reset_index(drop=True)
    return df


def sample_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = df[df.year <= TRAIN_SPLIT].copy()
    test = df[df.year > TRAIN_SPLIT].copy()
    if len(train) > SAMPLE_TRAIN:
        train = train.sample(SAMPLE_TRAIN, random_state=RANDOM_STATE)
    if len(test) > SAMPLE_TEST:
        test = test.sample(SAMPLE_TEST, random_state=RANDOM_STATE)
    return train.reset_index(drop=True), test.reset_index(drop=True)


def load_engine_test() -> pd.DataFrame:
    path = os.path.join(OUT_ANALYSIS, "model_backtest_roc_v27_test.csv")
    if not os.path.exists(path):
        return pd.DataFrame(columns=["threshold", "auc", "brier"])
    return pd.read_csv(path)


def model_specs() -> list[tuple[str, object]]:
    return [
        (
            "LogisticRegression(natural)",
            make_pipeline(
                SimpleImputer(strategy="median"),
                StandardScaler(),
                LogisticRegression(max_iter=2000, class_weight=None, random_state=RANDOM_STATE),
            ),
        ),
        (
            "LogisticRegression(balanced)",
            make_pipeline(
                SimpleImputer(strategy="median"),
                StandardScaler(),
                LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE),
            ),
        ),
        (
            "RandomForest(balanced)",
            make_pipeline(
                SimpleImputer(strategy="median"),
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=8,
                    class_weight="balanced",
                    n_jobs=-1,
                    random_state=RANDOM_STATE,
                ),
            ),
        ),
    ]


def evaluate_model(name: str, model: object, x_train, y_train, x_test, y_test) -> dict:
    model.fit(x_train, y_train)
    score = model.predict_proba(x_test)[:, 1]
    return {
        "model": name,
        "auc": round(float(roc_auc_score(y_test, score)), 4),
        "brier": round(float(brier_score_loss(y_test, score)), 4),
    }


def write_outputs(rows: list[dict], engine: pd.DataFrame) -> None:
    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    out = pd.DataFrame(rows)
    csv_path = os.path.join(OUT_ANALYSIS, "baseline_comparison_v27.csv")
    out.to_csv(csv_path, index=False)

    engine_map = {
        r.threshold: (float(r.auc), float(r.brier)) for _, r in engine.iterrows()
    }
    thresholds = list(dict.fromkeys(out["threshold"].tolist()))

    lines = [
        "# v27.0 baseline comparison",
        "",
        "Baselines use the same v27 feature grid, 1946-1989 / 1990-2014 split,",
        "and 200,000-row train/test samples as `backtest_tiers_v27.py`.",
        "",
        "Features: `" + "`, `".join(FEATURES) + "`.",
        "",
        "## Test-set comparison",
        "",
        "| Threshold | Model | AUC | Δ AUC vs engine | Brier | Δ Brier vs engine | n_pos | n_neg |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for threshold in thresholds:
        engine_auc, engine_brier = engine_map.get(threshold, (np.nan, np.nan))
        block = out[out.threshold == threshold]
        lines.append(
            f"| {threshold} | TIERS v27 diagnostic engine | {engine_auc:.4f} | 0.0000 | "
            f"{engine_brier:.4f} | 0.0000 | {int(block.n_pos.iloc[0])} | {int(block.n_neg.iloc[0])} |"
        )
        for _, r in block.iterrows():
            lines.append(
                f"| {threshold} | {r.model} | {r.auc:.4f} | {r.auc - engine_auc:+.4f} | "
                f"{r.brier:.4f} | {r.brier - engine_brier:+.4f} | {int(r.n_pos)} | {int(r.n_neg)} |"
            )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "`LogisticRegression(natural)` is the best Brier-score baseline because it",
        "preserves the observed rare-event base rates. `LogisticRegression(balanced)`",
        "and `RandomForest(balanced)` are ranking baselines: they usually improve AUC",
        "on rare events but produce probabilities that are not directly calibrated to",
        "the historical base rate.",
        "",
    ])
    md_path = os.path.join(OUT_ANALYSIS, "baseline_summary_v27.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print()
    print("Test-set comparison:")
    print(out.to_string(index=False))


def main() -> int:
    print("Loading v27 feature grid...")
    df = load_data()
    train, test = sample_split(df)
    print(f"Train sample: {len(train):,}; test sample: {len(test):,}")

    x_train = train[FEATURES].astype(float)
    x_test = test[FEATURES].astype(float)
    engine = load_engine_test()
    rows: list[dict] = []

    thresholds = [
        ("T0->T1+", "escalate_to_t1_plus"),
        ("T0->T4+", "escalate_to_t4_plus"),
        ("T0->T5", "escalate_to_t5"),
        ("Any esc", "escalate"),
    ]

    for threshold, label_col in thresholds:
        y_train = train[label_col].astype(int).values
        y_test = test[label_col].astype(int).values
        n_pos = int(y_test.sum())
        n_neg = len(y_test) - n_pos
        print(f"\n{threshold}: pos={n_pos:,}, neg={n_neg:,}")
        if n_pos < 5 or n_neg < 5:
            continue
        for name, model in model_specs():
            print(f"  fitting {name}...")
            metrics = evaluate_model(name, model, x_train, y_train, x_test, y_test)
            metrics.update({"threshold": threshold, "n_pos": n_pos, "n_neg": n_neg})
            rows.append(metrics)
            print(f"    AUC={metrics['auc']:.4f} Brier={metrics['brier']:.4f}")

    write_outputs(rows, engine)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
