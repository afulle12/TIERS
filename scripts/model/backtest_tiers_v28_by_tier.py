"""Tier-specific backtest for TIERS v28.

Unlike the headline backtest, this evaluates rows separately by current tier so
each hazard block is judged on the state where it is active.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from backtest_tiers_v28 import V28Calibrator
from tiers_lib_v28 import Priors, priors_from_mapping

YEAR_LO, YEAR_HI = 1946, 2014
TRAIN_SPLIT = 1989
RANDOM_STATE = 42


def load_data() -> pd.DataFrame:
    pq = os.path.join(DATA_PROCESSED, "dyads_with_features_v28.parquet")
    csv = os.path.join(DATA_PROCESSED, "dyads_with_features_v28.csv")
    df = pd.read_parquet(pq) if os.path.exists(pq) else pd.read_csv(csv)
    df = df[(df.year >= YEAR_LO) & (df.year <= YEAR_HI)].copy()
    df = df.sort_values("year")
    df["uiw_tier_next"] = df.groupby(["initiator", "target"])["uiw_tier"].shift(-1)
    df = df.dropna(subset=["uiw_tier_next"]).reset_index(drop=True)
    df["uiw_tier"] = df["uiw_tier"].astype(int)
    df["uiw_tier_next"] = df["uiw_tier_next"].astype(int)
    if "trade_source" not in df.columns:
        df["trade_source"] = "NONE"
    df["trade_source"] = df["trade_source"].fillna("NONE")
    return df


def load_priors(path: str | None) -> Priors:
    if not path:
        return Priors()
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return priors_from_mapping(payload.get("priors", payload))


def stratified_sample(df: pd.DataFrame, tier: int, max_rows: int) -> pd.DataFrame:
    if max_rows <= 0 or len(df) <= max_rows:
        return df
    pos = df[df.uiw_tier_next >= tier + 1]
    neg = df[df.uiw_tier_next < tier + 1]
    if len(pos) >= max_rows:
        return pos.sample(max_rows, random_state=RANDOM_STATE).sort_index().reset_index(drop=True)
    n_neg = max_rows - len(pos)
    neg = neg.sample(min(n_neg, len(neg)), random_state=RANDOM_STATE)
    return pd.concat([pos, neg], ignore_index=True).sample(frac=1.0, random_state=RANDOM_STATE).reset_index(drop=True)


def score_rows(sample: pd.DataFrame, priors: Priors) -> np.ndarray:
    cal = V28Calibrator(priors)
    pis = np.zeros((len(sample), 6), dtype=float)
    for i, (_, row) in enumerate(sample.iterrows()):
        pis[i] = cal.score_row(row)["pi_reconciled"]
        if (i + 1) % 25_000 == 0:
            print(f"    {i + 1:,} / {len(sample):,}")
    return pis


def metric_row(tag: str, tier: int, variant: str, source: str, y: np.ndarray, p: np.ndarray) -> dict:
    n_pos = int(y.sum())
    n_neg = int(len(y) - n_pos)
    row = {
        "tag": tag,
        "current_tier": tier,
        "transition": f"T{tier}->T{tier + 1}" if tier < 5 else "T5",
        "variant": variant,
        "trade_source": source,
        "rows": len(y),
        "n_pos": n_pos,
        "n_neg": n_neg,
        "auc": np.nan,
        "brier": np.nan,
        "log_loss": np.nan,
    }
    if n_pos >= 5 and n_neg >= 5:
        p = np.clip(p, 1e-9, 1.0 - 1e-9)
        row["auc"] = float(roc_auc_score(y, p))
        row["brier"] = float(brier_score_loss(y, p))
        row["log_loss"] = float(log_loss(y, p, labels=[0, 1]))
    return row


def evaluate_split(df: pd.DataFrame, tag: str, priors: Priors, max_rows_per_tier: int) -> list[dict]:
    rows: list[dict] = []
    for tier in range(5):
        sub = df[df.uiw_tier == tier].copy()
        if sub.empty:
            continue
        sample = stratified_sample(sub, tier, max_rows_per_tier)
        print(f"\n--- {tag} T{tier}: scoring {len(sample):,} rows ({len(sub):,} eligible) ---")
        pis = score_rows(sample, priors)
        next_tier = sample["uiw_tier_next"].to_numpy()
        exact_y = (next_tier == tier + 1).astype(int)
        cum_y = (next_tier >= tier + 1).astype(int)
        t5_y = (next_tier == 5).astype(int)
        exact_p = pis[:, tier + 1]
        cum_p = pis[:, tier + 1:].sum(axis=1)
        t5_p = pis[:, 5]
        for source in ["ALL"] + sorted(str(s) for s in sample["trade_source"].dropna().unique()):
            mask = np.ones(len(sample), dtype=bool) if source == "ALL" else (sample["trade_source"].to_numpy() == source)
            rows.append(metric_row(tag, tier, "exact", source, exact_y[mask], exact_p[mask]))
            rows.append(metric_row(tag, tier, "cumulative", source, cum_y[mask], cum_p[mask]))
            rows.append(metric_row(tag, tier, "to_t5", source, t5_y[mask], t5_p[mask]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--priors", help="Optional calibrated priors JSON.")
    parser.add_argument("--max-rows-per-tier", type=int, default=50_000)
    parser.add_argument("--include-none", action="store_true", help="Include rows with no observed trade source.")
    parser.add_argument("--tag", default=None, help="Suffix for output filename.")
    args = parser.parse_args()

    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    df = load_data()
    if not args.include_none:
        df = df[df.trade_source != "NONE"].copy()
    priors = load_priors(args.priors)
    tag_suffix = args.tag or ("calibrated" if args.priors else "raw")

    windows = {
        "train_1946_1989": df[df.year <= TRAIN_SPLIT].copy(),
        "test_1990_2014": df[df.year > TRAIN_SPLIT].copy(),
        "trade_window_1995_2014": df[(df.year >= 1995) & (df.year <= 2014)].copy(),
    }
    all_rows: list[dict] = []
    for tag, sub in windows.items():
        all_rows.extend(evaluate_split(sub, tag, priors, args.max_rows_per_tier))
    out = pd.DataFrame(all_rows)
    path = os.path.join(OUT_ANALYSIS, f"model_backtest_v28_by_tier_{tag_suffix}.csv")
    out.to_csv(path, index=False)
    print(f"\nWrote {path}")
    print(out[(out.trade_source == "ALL") & (out.variant == "cumulative")].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
