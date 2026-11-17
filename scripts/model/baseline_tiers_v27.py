"""Baseline comparisons on the v27 or v28 feature grid using shared evaluation.py."""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from evaluation import (  # noqa: E402
    HEADLINE_TARGETS,
    MIN_POSITIVES,
    RANDOM_STATE,
    TRAIN_SPLIT,
    collapse_directions,
    collapse_target_scores,
    evaluate_target_scores,
    fit_and_score_logreg_targets,
    fit_transition_rates,
    format_ci,
    load_feature_grid,
    stamp_header_lines,
    training_base_rates,
    transition_rate_scores,
    unordered_dyad_codes,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", choices=["v27", "v28"], default="v28")
    parser.add_argument("--n-boot", type=int, default=200)
    parser.add_argument("--seed", type=int, default=RANDOM_STATE)
    args = parser.parse_args()

    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    df, stats = load_feature_grid(args.grid)
    train = df[df["year"] <= TRAIN_SPLIT].copy().reset_index(drop=True)
    test = df[df["year"] > TRAIN_SPLIT].copy().reset_index(drop=True)
    train_rates = training_base_rates(train, HEADLINE_TARGETS)

    # One row per dyad-year: both baselines are scored on the canonical row,
    # the logistic one with the mean of its two directed predictions.
    pair, _ = collapse_directions(test)
    clusters = unordered_dyad_codes(pair)
    common = dict(
        train_rates=train_rates, target_names=HEADLINE_TARGETS, clusters=clusters,
        n_boot=args.n_boot, seed=args.seed,
    )
    tm_scores = transition_rate_scores(pair, fit_transition_rates(train, HEADLINE_TARGETS), HEADLINE_TARGETS)
    rows = evaluate_target_scores(pair, tm_scores, "test_1990_2014", "Transition matrix", **common)

    lr_preds = fit_and_score_logreg_targets(
        train, {"test_1990_2014": test}, HEADLINE_TARGETS, seed=args.seed, min_positives=MIN_POSITIVES
    )
    lr_scores = collapse_target_scores(test, lr_preds["test_1990_2014"], HEADLINE_TARGETS)
    rows += evaluate_target_scores(pair, lr_scores, "test_1990_2014", "LogReg(trade+struct)", **common)

    out = pd.DataFrame(rows)
    csv_path = os.path.join(OUT_ANALYSIS, f"baseline_comparison_{args.grid}.csv")
    out.to_csv(csv_path, index=False)

    lines = stamp_header_lines(
        f"TIERS {args.grid} Baseline Comparison",
        stats=stats,
        parameters_desc="Empirical transition matrix + LogisticRegression(natural, trade+struct)",
        seed=args.seed,
        extra=[
            "- **Unit of evaluation:** one row per unordered dyad-year. Rows whose label depends on a tier "
            "with no source that year are withheld.",
        ],
    )
    lines.extend([
        "| Target | Model | n_pos | n_neg | ROC AUC (95% CI) | Avg Prec | Brier | Brier Skill | Log Loss |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|",
    ])
    for r in out.itertuples(index=False):
        lines.append(
            f"| {r.target} | {r.model} | {r.n_sample_pos:,} | {r.n_sample_neg:,} | "
            f"{format_ci(r.roc_auc, r.roc_auc_ci_lo, r.roc_auc_ci_hi)} | "
            f"{r.avg_precision:.4f} | {r.brier:.5f} | {r.brier_skill:.4f} | {r.log_loss:.5f} |"
        )
    md_path = os.path.join(OUT_ANALYSIS, f"baseline_summary_{args.grid}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
