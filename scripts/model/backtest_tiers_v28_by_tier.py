"""Tier-specific backtest for TIERS v28 using shared evaluation.py.

Evaluates every eligible row per starting tier by default (or applies exact
inclusion-probability weighting when `--max-rows-per-tier` is set), breaks down
results by active engine member and trade source, and suppresses metrics when
positives < 20.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from evaluation import (  # noqa: E402
    MIN_POSITIVES,
    RANDOM_STATE,
    TRAIN_SPLIT,
    collapse_directions,
    compute_metrics,
    label_decidable,
    load_feature_grid,
    training_base_rates,
    unobserved_next_of,
    unordered_dyad_codes,
)
from tiers_lib_v28 import Priors, priors_from_mapping, score_dataframe_v28  # noqa: E402


def load_priors(path: str | None) -> Priors:
    if not path:
        return Priors()
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    return priors_from_mapping(payload.get("priors", payload))


def stratified_sample(
    df: pd.DataFrame, tier: int, max_rows: int
) -> tuple[pd.DataFrame, np.ndarray | None]:
    """Sample negatives if capped while retaining exact inclusion probabilities."""
    if max_rows <= 0 or len(df) <= max_rows:
        return df.reset_index(drop=True), None
    pos = df[df["uiw_tier_next"] >= tier + 1].copy()
    neg = df[df["uiw_tier_next"] < tier + 1].copy()
    if len(pos) >= max_rows:
        p_pos = float(max_rows) / float(len(pos))
        sampled = pos.sample(max_rows, random_state=RANDOM_STATE).reset_index(drop=True)
        return sampled, np.full(len(sampled), p_pos, dtype=float)
    n_neg_keep = min(max_rows - len(pos), len(neg))
    p_neg = float(n_neg_keep) / float(len(neg)) if len(neg) > 0 else 1.0
    neg_s = neg.sample(n_neg_keep, random_state=RANDOM_STATE)
    pos["_inc_prob"] = 1.0
    neg_s["_inc_prob"] = p_neg
    combined = pd.concat([pos, neg_s], ignore_index=True).sample(
        frac=1.0, random_state=RANDOM_STATE
    ).reset_index(drop=True)
    inc = combined.pop("_inc_prob").to_numpy(dtype=float)
    return combined, inc


def evaluate_split(
    df: pd.DataFrame,
    tag: str,
    priors: Priors,
    max_rows_per_tier: int,
    train_rates: dict[str, float],
    n_boot: int,
) -> list[dict]:
    rows: list[dict] = []
    for tier in range(5):
        sub = df[df["uiw_tier"] == tier].copy()
        if sub.empty:
            continue
        print(f"\n--- {tag} T{tier}: scoring {len(sub):,} directed rows ---")
        res = score_dataframe_v28(sub, priors)
        sub["active_member"] = res["member_ab"]
        # One row per dyad-year (mean of the two directed forecasts), then sample.
        pair, (pis_all,) = collapse_directions(sub, res["pi"])
        pair["_row"] = np.arange(len(pair))
        sample, inc = stratified_sample(pair, tier, max_rows_per_tier)
        pis = pis_all[sample["_row"].to_numpy()]
        clusters = unordered_dyad_codes(sample)

        cur_tier = sample["uiw_tier"].to_numpy(dtype=int)
        next_tier = sample["uiw_tier_next"].to_numpy(dtype=int)
        unobs = unobserved_next_of(sample)
        # (label, score, training-rate key, target name used for the coverage mask)
        variants = {
            "exact": ((next_tier == tier + 1).astype(int), pis[:, tier + 1], f"T{tier}->T{tier + 1}", f"T{tier}->T{tier + 1}"),
            "cumulative": ((next_tier >= tier + 1).astype(int), pis[:, tier + 1:].sum(axis=1), f"T{tier}->T{tier + 1}+", f"T{tier}->T{tier + 1}+"),
            "to_t5": ((next_tier == 5).astype(int), pis[:, 5], "Onset, war" if tier == 0 else f"T{tier}->T5", f"T{tier}->T5"),
        }
        trade_sources = ["ALL"] + sorted(str(s) for s in sample["trade_source"].dropna().unique())
        for source in trade_sources:
            mask = np.ones(len(sample), dtype=bool) if source == "ALL" else (sample["trade_source"].to_numpy() == source)
            if not np.any(mask):
                continue
            for variant, (y_arr, p_arr, rate_key, mask_name) in variants.items():
                ref = train_rates.get(rate_key if rate_key != "T0->T1+" else "Onset, any")
                if rate_key == "T4->T5+":
                    ref = train_rates.get("T4->T5")
                vmask = mask
                if unobs is not None:
                    vmask = mask & label_decidable(mask_name, cur_tier, unobs)
                if not np.any(vmask):
                    continue
                m = compute_metrics(
                    y_arr[vmask],
                    p_arr[vmask],
                    inclusion_prob=inc[vmask] if inc is not None else None,
                    ref_rate=ref,
                    clusters=clusters[vmask],
                    n_boot=n_boot,
                    seed=RANDOM_STATE,
                    min_positives=MIN_POSITIVES,
                )
                m.update({
                    "tag": tag,
                    "current_tier": tier,
                    "transition": f"T{tier}->T{tier + 1}",
                    "variant": variant,
                    "trade_source": source,
                })
                rows.append(m)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--priors", help="Optional calibrated priors JSON.")
    parser.add_argument("--max-rows-per-tier", type=int, default=0, help="0 = score all eligible rows.")
    parser.add_argument("--include-none", action="store_true", help="Include rows with no observed trade source.")
    parser.add_argument("--n-boot", type=int, default=100)
    parser.add_argument("--tag", default=None, help="Suffix for output filename.")
    args = parser.parse_args()

    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    df, stats = load_feature_grid("v28")
    print(f"Loaded {stats.path}: consecutive_joined={stats.n_joined:,}")
    if not args.include_none:
        df = df[df["trade_source"] != "NONE"].copy()
    priors = load_priors(args.priors)
    tag_suffix = args.tag or ("calibrated" if args.priors else "raw")

    train_full = df[df["year"] <= TRAIN_SPLIT].copy()
    train_rates = training_base_rates(train_full)

    windows = {
        "train_1946_1989": train_full,
        "test_1990_2014": df[df["year"] > TRAIN_SPLIT].copy(),
        "trade_window_1995_2014": df[(df["year"] >= 1995) & (df["year"] <= 2014)].copy(),
    }
    all_rows: list[dict] = []
    for tag, sub in windows.items():
        all_rows.extend(
            evaluate_split(sub, tag, priors, args.max_rows_per_tier, train_rates, args.n_boot)
        )
    out = pd.DataFrame(all_rows)
    path = os.path.join(OUT_ANALYSIS, f"model_backtest_v28_by_tier_{tag_suffix}.csv")
    out.to_csv(path, index=False)
    print(f"\nWrote {path}")
    cols = [
        "tag", "transition", "variant", "n_sample_pos", "n_pop_pos",
        "roc_auc", "avg_precision", "brier", "brier_skill", "log_loss",
    ]
    print(out[(out.trade_source == "ALL") & (out.variant == "cumulative")][cols].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
