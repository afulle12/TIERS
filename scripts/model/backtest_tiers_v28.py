"""Back-test the TIERS v28.0 transition-hazard engine using shared evaluation.py.

Scores every eligible row in train (1946-1989), test (1990-2014), and trade
(1995-2014) windows using vectorized scoring, compares against the empirical
training-period tier-transition matrix and logistic regression with structural
+ trade features, breaks down results by active engine member and trade source,
and writes one stamped report + CSV artifacts.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from evaluation import (  # noqa: E402
    ALL_TARGETS,
    EXACT_STEP_TARGETS,
    HEADLINE_TARGETS,
    MIN_POSITIVES,
    RANDOM_STATE,
    TRAIN_SPLIT,
    collapse_directions,
    collapse_target_scores,
    evaluate_pis_on_split,
    evaluate_target_scores,
    extract_target,
    fit_and_score_logreg_targets,
    fit_transition_rates,
    format_ci,
    load_feature_grid,
    reliability_table,
    sha256_file,
    stamp_header_lines,
    training_base_rates,
    transition_rate_scores,
    unobserved_next_of,
    unordered_dyad_codes,
)
from tiers_lib_v27 import ActorState, DyadState, InputState  # noqa: E402
from tiers_lib_v28 import (  # noqa: E402
    Priors,
    priors_from_mapping,
    score_dataframe_v28,
    score_dyad_year,
)


@dataclass
class V28Calibrator:
    """Retained scalar wrapper for single-row callers."""

    priors: Priors

    def score_row(self, row: pd.Series) -> dict:
        trade_source = str(row.get("trade_source", "NONE"))
        trade_state = InputState.OBSERVED if trade_source != "NONE" else InputState.ABSENT
        sym = DyadState(
            current_tier=int(row["uiw_tier"]) if pd.notna(row["uiw_tier"]) else 0,
            duration=float(row.get("d_k_years", 0.0)),
            contiguity=float(row.get("contiguity_xi", 0.0)),
            rivalry=float(row.get("rivalry_omega", 0.0)),
            state_current_tier=InputState.OBSERVED,
            state_duration=InputState.OBSERVED,
            state_contiguity=InputState.OBSERVED,
            state_rivalry=InputState.OBSERVED,
        )
        actor_a = ActorState(
            n_pub=float(row.get("n_pub_a", 0.9)),
            capability_share=float(row.get("c_t_ab", 0.5)),
            closing_window=float(row.get("closing_window_a", 0.5)),
            fma=float(row.get("fma", 0.0)),
            cap_proxy=float(row.get("cap_a_to_b", 0.0)),
            attribution=float(row.get("attribution", 0.0)),
            stakes=0.5,
            state_b_econ=InputState.ABSENT,
            state_b_blood=InputState.ABSENT,
            state_v_i=InputState.ABSENT,
            state_fma=InputState.OBSERVED,
            state_closing_window=InputState.OBSERVED,
            state_cap=InputState.OBSERVED,
            state_attribution=InputState.OBSERVED,
            state_integration=trade_state,
        )
        actor_b = ActorState(
            n_pub=float(row.get("n_pub_b", 0.9)),
            capability_share=float(row.get("c_t_ba", 0.5)),
            closing_window=float(row.get("closing_window_b", 0.5)),
            fma=float(row.get("fma", 0.0)),
            cap_proxy=float(row.get("cap_b_to_a", 0.0)),
            attribution=0.0,
            stakes=0.5,
            state_b_econ=InputState.ABSENT,
            state_b_blood=InputState.ABSENT,
            state_v_i=InputState.ABSENT,
            state_fma=InputState.OBSERVED,
            state_closing_window=InputState.OBSERVED,
            state_cap=InputState.OBSERVED,
            state_integration=trade_state,
        )
        actor_a.rivalry = float(row.get("rivalry_omega", 0.0))
        actor_b.rivalry = float(row.get("rivalry_omega_b", row.get("rivalry_omega", 0.0)))
        actor_a.trade_surface_norm = float(row.get("trade_surface_norm_ab", 0.0))
        actor_a.dep_on_target = float(row.get("dep_a_on_b", 0.0))
        actor_a.mutual_trade_dependence = float(row.get("mutual_trade_dependence_ab", 0.0))
        actor_a.import_leverage = float(row.get("import_leverage_a_over_b", 0.0))
        actor_a.export_leverage = float(row.get("export_leverage_a_over_b", 0.0))
        actor_a.trade_leverage = float(row.get("trade_leverage_a_over_b", 0.0))

        actor_b.trade_surface_norm = float(row.get("trade_surface_norm_ab", 0.0))
        actor_b.dep_on_target = float(row.get("dep_b_on_a", 0.0))
        actor_b.mutual_trade_dependence = float(row.get("mutual_trade_dependence_ab", 0.0))
        actor_b.import_leverage = max(
            float(row.get("import_dep_a_on_b", 0.0)) - float(row.get("import_dep_b_on_a", 0.0)),
            0.0,
        )
        actor_b.export_leverage = max(
            float(row.get("export_dep_a_on_b", 0.0)) - float(row.get("export_dep_b_on_a", 0.0)),
            0.0,
        )
        actor_b.trade_leverage = max(actor_b.import_leverage, actor_b.export_leverage)
        return score_dyad_year(actor_a, actor_b, sym, self.priors)


def _subsample_with_prob(df: pd.DataFrame, sample_cap: int, seed: int) -> tuple[pd.DataFrame, np.ndarray | None]:
    if sample_cap <= 0 or len(df) <= sample_cap:
        return df, None
    prob = float(sample_cap) / float(len(df))
    sub = df.sample(sample_cap, random_state=seed).reset_index(drop=True)
    return sub, np.full(len(sub), prob, dtype=float)


def _markdown_table_for_split(df_m: pd.DataFrame, split: str, targets: list[str]) -> list[str]:
    lines = [
        f"### {split}",
        "",
        "| Target | Model | n_pos / n_pop_pos | n_neg / n_pop_neg | ROC AUC (95% CI) | Avg Prec (95% CI) | Brier (95% CI) | Brier Skill (95% CI) | Log Loss (95% CI) |",
        "|---|---|---:|---:|---|---|---|---|---|",
    ]
    sub = df_m[df_m["split"] == split]
    for tgt in targets:
        block = sub[sub["target"] == tgt]
        for r in block.itertuples(index=False):
            pos_str = (
                f"{r.n_sample_pos:,}"
                if r.n_sample_pos == r.n_pop_pos
                else f"{r.n_sample_pos:,} ({r.n_pop_pos:,.0f})"
            )
            neg_str = (
                f"{r.n_sample_neg:,}"
                if r.n_sample_neg == r.n_pop_neg
                else f"{r.n_sample_neg:,} ({r.n_pop_neg:,.0f})"
            )
            lines.append(
                f"| {r.target} | {r.model} | {pos_str} | {neg_str} | "
                f"{format_ci(r.roc_auc, r.roc_auc_ci_lo, r.roc_auc_ci_hi)} | "
                f"{format_ci(r.avg_precision, r.avg_precision_ci_lo, r.avg_precision_ci_hi)} | "
                f"{format_ci(r.brier, r.brier_ci_lo, r.brier_ci_hi)} | "
                f"{format_ci(r.brier_skill, r.brier_skill_ci_lo, r.brier_skill_ci_hi)} | "
                f"{format_ci(r.log_loss, r.log_loss_ci_lo, r.log_loss_ci_hi)} |"
            )
    lines.append("")
    return lines


def write_summary(
    metrics_df: pd.DataFrame,
    subgroups_df: pd.DataFrame,
    rel_df: pd.DataFrame,
    stats,
    priors_desc: str,
    n_boot: int,
    seed: int,
    sample_cap: int,
    window_counts: dict[str, int],
) -> str:
    extra = [
        "- **Windows (directed rows):** " + ", ".join(f"{k}={v:,}" for k, v in window_counts.items()),
        "- **Unit of evaluation:** one row per unordered dyad-year; the forecast is the mean of the two directed forecasts.",
        f"- **Sampling:** {'full population (unweighted)' if sample_cap <= 0 else f'cap={sample_cap:,} per split (weighted by 1/inclusion_prob)'}",
        f"- **Bootstrap:** {n_boot} unordered-dyad-clustered replicates; metrics suppressed below {MIN_POSITIVES} positives.",
    ]
    lines = stamp_header_lines(
        "TIERS v28.0 Evaluation Report",
        stats=stats,
        parameters_desc=priors_desc,
        seed=seed,
        extra=extra,
    )
    lines.append("## Headline Targets vs Baselines")
    lines.append("")
    for split in ("test_1990_2014", "trade_window_1995_2014", "train_1946_1989"):
        lines.extend(_markdown_table_for_split(metrics_df, split, HEADLINE_TARGETS))

    lines.append("## Rows withheld by source coverage")
    lines.append("")
    lines.append(
        "A transition is not scored for a target whose label could change if a tier with no "
        "source that year were filled in. Sanctions (T2) have no source before 1989, so a dyad "
        "recorded at T0 or T1 then may have been under sanctions."
    )
    lines.append("")
    lines.append("| Target | Split | Dyad-years scored | Withheld |")
    lines.append("|---|---|---:|---:|")
    cov = metrics_df[(metrics_df["model"] == "TIERS v28") & (metrics_df["target"].isin(HEADLINE_TARGETS))]
    for r in cov.itertuples(index=False):
        if r.n_masked_rows > 0:
            lines.append(f"| {r.target} | {r.split} | {r.n_sample_rows:,} | {r.n_masked_rows:,} |")
    lines.append("")
    lines.append(
        "Where the training window is mostly withheld, the training base rate and the baselines "
        "for that target rest on the remaining years only."
    )
    lines.append("")

    lines.append("## Adjacent Step Transitions (Test 1990–2014)")
    lines.append("")
    lines.extend(_markdown_table_for_split(metrics_df, "test_1990_2014", EXACT_STEP_TARGETS))

    lines.append("## Active Engine Member & Trade Source Breakdown (v28, Test 1990–2014)")
    lines.append("")
    lines.append(
        "| Breakdown | Group | Target | n_pos | n_neg | ROC AUC (95% CI) | Avg Prec | Brier Skill | Log Loss |"
    )
    lines.append("|---|---|---|---:|---:|---|---:|---:|---:|")
    sg_test = subgroups_df[
        (subgroups_df["split"] == "test_1990_2014")
        & (subgroups_df["target"].isin(HEADLINE_TARGETS))
    ]
    for r in sg_test.itertuples(index=False):
        ap_s = f"{r.avg_precision:.4f}" if np.isfinite(r.avg_precision) else "suppressed"
        bss_s = f"{r.brier_skill:.4f}" if np.isfinite(r.brier_skill) else "suppressed"
        ll_s = f"{r.log_loss:.4f}" if np.isfinite(r.log_loss) else "suppressed"
        lines.append(
            f"| {r.subgroup_col} | {r.subgroup} | {r.target} | {r.n_sample_pos:,} | {r.n_sample_neg:,} | "
            f"{format_ci(r.roc_auc, r.roc_auc_ci_lo, r.roc_auc_ci_hi)} | {ap_s} | {bss_s} | {ll_s} |"
        )
    lines.append("")

    lines.append("## Reliability Table (TIERS v28, Test 1990–2014)")
    lines.append("")
    lines.append("| Target | Bin | Pred Range | n_rows | n_pos | Mean Pred | Obs Rate | Abs Err |")
    lines.append("|---|---:|---|---:|---:|---:|---:|---:|")
    for r in rel_df.itertuples(index=False):
        lines.append(
            f"| {r.target} | {r.bin} | [{r.p_lo:.5f}, {r.p_hi:.5f}] | {r.n_rows:,} | {r.n_pos:,} | "
            f"{r.mean_pred:.5f} | {r.obs_rate:.5f} | {r.abs_err:.5f} |"
        )
    lines.append("")

    path = os.path.join(OUT_ANALYSIS, "model_calibration_summary_v28.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0, help="Optional cap per split (0 = full population)")
    parser.add_argument("--priors", help="Optional JSON file containing calibrated v28 prior values.")
    parser.add_argument("--n-boot", type=int, default=200, help="Dyad-clustered bootstrap replicates.")
    parser.add_argument("--seed", type=int, default=RANDOM_STATE)
    args = parser.parse_args()

    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    df, stats = load_feature_grid("v28")
    print(
        f"Loaded {stats.path}: raw={stats.n_raw:,}, consecutive_joined={stats.n_joined:,}, "
        f"dropped_terminal_or_gap={stats.n_dropped_no_next:,}"
    )

    priors = Priors()
    priors_desc = "default Priors()"
    if args.priors:
        with open(args.priors, "r", encoding="utf-8") as f:
            payload = json.load(f)
        priors = priors_from_mapping(payload.get("priors", payload))
        priors_desc = f"{args.priors} (SHA-256 {sha256_file(args.priors)[:16]}...)"

    train_full = df[df["year"] <= TRAIN_SPLIT].copy().reset_index(drop=True)
    test_full = df[df["year"] > TRAIN_SPLIT].copy().reset_index(drop=True)
    trade_full = df[(df["year"] >= 1995) & (df["year"] <= 2014)].copy().reset_index(drop=True)

    train_rates = training_base_rates(train_full, ALL_TARGETS)
    tm_rates = fit_transition_rates(train_full, ALL_TARGETS)

    splits = {
        "train_1946_1989": _subsample_with_prob(train_full, args.sample, args.seed),
        "test_1990_2014": _subsample_with_prob(test_full, args.sample, args.seed),
        "trade_window_1995_2014": _subsample_with_prob(trade_full, args.sample, args.seed),
    }
    eval_dfs = {k: v[0] for k, v in splits.items()}
    window_counts = {k: len(v[0]) for k, v in splits.items()}

    print("Fitting LogisticRegression(trade+struct, natural) baseline on train_1946_1989...")
    logreg_preds = fit_and_score_logreg_targets(
        train_full, eval_dfs, ALL_TARGETS, seed=args.seed, min_positives=MIN_POSITIVES
    )

    all_metrics: list[dict] = []
    all_subgroups: list[dict] = []
    rel_frames: list[pd.DataFrame] = []

    for split_name, (sub, inc_prob) in splits.items():
        print(f"\n--- {split_name}: scoring {len(sub):,} rows ---")
        res_v28 = score_dataframe_v28(sub, priors)
        sub = sub.copy()
        sub["active_member"] = res_v28["member_ab"]

        # The tier is shared by the dyad, so the two directed rows of a
        # dyad-year carry the same outcome. Count each dyad-year once: average
        # the two directed forecasts and keep the canonical row.
        pair, (pis_v28, inc_prob) = collapse_directions(sub, res_v28["pi"], inc_prob)
        clusters = unordered_dyad_codes(pair)
        cur = pair["uiw_tier"].to_numpy(dtype=int)
        nxt = pair["uiw_tier_next"].to_numpy(dtype=int)
        unobs = unobserved_next_of(pair)
        common = dict(
            train_rates=train_rates, clusters=clusters, inclusion_prob=inc_prob,
            n_boot=args.n_boot, seed=args.seed,
        )

        all_metrics.extend(
            evaluate_pis_on_split(pair, pis_v28, split_name, "TIERS v28", target_names=ALL_TARGETS, **common)
        )

        tm_scores = transition_rate_scores(pair, tm_rates, ALL_TARGETS)
        # Logistic predictions arrive per directed eligible row; average them
        # over the two directions in the same way as the model's.
        lr_scores = collapse_target_scores(sub, logreg_preds[split_name], ALL_TARGETS)
        all_metrics.extend(
            evaluate_target_scores(pair, tm_scores, split_name, "Transition matrix", target_names=ALL_TARGETS, **common)
        )
        all_metrics.extend(
            evaluate_target_scores(pair, lr_scores, split_name, "LogReg(trade+struct)", target_names=ALL_TARGETS, **common)
        )

        if split_name in ("test_1990_2014", "trade_window_1995_2014"):
            for sg_col in ("active_member", "trade_source"):
                rows_sg = evaluate_pis_on_split(
                    pair, pis_v28, split_name, "TIERS v28",
                    target_names=HEADLINE_TARGETS, subgroup_col=sg_col, **common,
                )
                all_subgroups.extend([r for r in rows_sg if r["subgroup"] != "ALL"])

        if split_name == "test_1990_2014":
            for tname in HEADLINE_TARGETS:
                tmask, y_t, p_t = extract_target(cur, nxt, pis_v28, tname, unobs)
                rel = reliability_table(
                    y_t, p_t, inclusion_prob=inc_prob[tmask] if inc_prob is not None else None, n_bins=10
                )
                rel.insert(0, "target", tname)
                rel_frames.append(rel)

    metrics_df = pd.DataFrame(all_metrics)
    subgroups_df = pd.DataFrame(all_subgroups)
    rel_df = pd.concat(rel_frames, ignore_index=True)

    metrics_path = os.path.join(OUT_ANALYSIS, "model_backtest_v28_phase1_metrics.csv")
    subgroups_path = os.path.join(OUT_ANALYSIS, "model_backtest_v28_phase1_subgroups.csv")
    rel_path = os.path.join(OUT_ANALYSIS, "model_backtest_v28_phase1_reliability.csv")
    metrics_df.to_csv(metrics_path, index=False)
    subgroups_df.to_csv(subgroups_path, index=False)
    rel_df.to_csv(rel_path, index=False)

    summary_path = write_summary(
        metrics_df, subgroups_df, rel_df, stats, priors_desc,
        n_boot=args.n_boot, seed=args.seed, sample_cap=args.sample, window_counts=window_counts,
    )
    print(f"\nWrote {metrics_path}")
    print(f"Wrote {subgroups_path}")
    print(f"Wrote {rel_path}")
    print(f"Summary -> {summary_path}")

    test_head = metrics_df[
        (metrics_df["split"] == "test_1990_2014") & (metrics_df["target"].isin(HEADLINE_TARGETS))
    ][["target", "model", "n_sample_pos", "n_sample_neg", "roc_auc", "avg_precision", "brier", "brier_skill", "log_loss"]]
    print("\nTest 1990-2014 Headline Comparison:")
    print(test_head.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
