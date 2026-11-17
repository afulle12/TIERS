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
    compute_metrics,
    evaluate_pis_on_split,
    extract_target,
    fit_and_score_logreg_targets,
    fit_transition_matrix,
    format_ci,
    load_feature_grid,
    score_transition_matrix,
    stamp_header_lines,
    training_base_rates,
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

    t_mat = fit_transition_matrix(
        train["uiw_tier"].to_numpy(dtype=int),
        train["uiw_tier_next"].to_numpy(dtype=int),
    )
    pis_tm_test = score_transition_matrix(t_mat, test["uiw_tier"].to_numpy(dtype=int))
    clusters_test = unordered_dyad_codes(test)

    rows = evaluate_pis_on_split(
        test, pis_tm_test, "test_1990_2014", "Transition matrix", train_rates,
        target_names=HEADLINE_TARGETS, clusters=clusters_test, n_boot=args.n_boot, seed=args.seed,
    )

    lr_preds = fit_and_score_logreg_targets(
        train, {"test_1990_2014": test}, HEADLINE_TARGETS, seed=args.seed, min_positives=MIN_POSITIVES
    )
    cur_t = test["uiw_tier"].to_numpy(dtype=int)
    nxt_t = test["uiw_tier_next"].to_numpy(dtype=int)
    for tname in HEADLINE_TARGETS:
        tmask, y_t, _ = extract_target(cur_t, nxt_t, None, tname)
        m = compute_metrics(
            y_t, lr_preds["test_1990_2014"][tname],
            ref_rate=train_rates.get(tname),
            clusters=clusters_test[tmask],
            n_boot=args.n_boot,
            seed=args.seed,
        )
        m.update({
            "split": "test_1990_2014",
            "model": "LogReg(trade+struct)",
            "subgroup_col": "ALL",
            "subgroup": "ALL",
            "target": tname,
        })
        rows.append(m)

    out = pd.DataFrame(rows)
    csv_path = os.path.join(OUT_ANALYSIS, f"baseline_comparison_{args.grid}.csv")
    out.to_csv(csv_path, index=False)

    lines = stamp_header_lines(
        f"TIERS {args.grid} Phase 1 Baseline Comparison",
        stats=stats,
        parameters_desc="Empirical transition matrix + LogisticRegression(natural, trade+struct)",
        seed=args.seed,
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
