"""Back-test the v27.0 cost-field engine using shared evaluation.py."""
from __future__ import annotations

import argparse
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
    evaluate_pis_on_split,
    format_ci,
    load_feature_grid,
    stamp_header_lines,
    training_base_rates,
    unordered_dyad_codes,
)
from tiers_lib_v27 import (  # noqa: E402
    ActorState,
    DyadState,
    InputState,
    Priors,
    score_dataframe_v27,
    score_dyad_year,
)


@dataclass
class V27Calibrator:
    """Retained scalar wrapper for single-row callers."""

    priors: Priors

    def score_row(self, row: pd.Series) -> dict:
        sym = DyadState(
            current_tier=int(row["uiw_tier"]) if pd.notna(row["uiw_tier"]) else 0,
            duration=float(row.get("d_k_years", 0.0)),
            contiguity=float(row.get("contiguity_xi", 0.0)),
            rivalry=float(row.get("rivalry_omega", 0.0)),
            stalemate=0.0,
            ora=0.0,
            state_current_tier=InputState.OBSERVED,
            state_duration=InputState.OBSERVED,
            state_contiguity=InputState.OBSERVED,
            state_rivalry=InputState.OBSERVED,
            state_stalemate=InputState.DEFAULTED,
            state_ora=InputState.DEFAULTED,
        )
        actor_a = ActorState(
            n_pub=float(row.get("n_pub_a", 0.9)),
            status_quo_burden=0.5,
            capability_share=float(row.get("c_t_ab", 0.5)),
            intent_selectivity=0.0,
            b_econ=0.0,
            b_blood=0.0,
            v_i=0.0,
            closing_window=float(row.get("closing_window_a", 0.5)),
            fma=float(row.get("fma", 0.0)),
            belief_estimate=0.0,
            belief_confidence=0.0,
            cap_proxy=float(row.get("cap_a_to_b", 0.0)),
            wmd=0.0,
            shock_k=0.0,
            deesc_inputs=(0.0, 0.0, 0.0),
            attribution=float(row.get("attribution", 0.0)),
            integration_depth=0.0,
            stakes=0.5,
            state_b_econ=InputState.ABSENT,
            state_b_blood=InputState.ABSENT,
            state_v_i=InputState.ABSENT,
            state_fma=InputState.OBSERVED,
            state_closing_window=InputState.OBSERVED,
            state_belief=InputState.ABSENT,
            state_cap=InputState.OBSERVED,
            state_shock=InputState.DEFAULTED,
            state_deesc=InputState.DEFAULTED,
            state_attribution=InputState.OBSERVED,
            state_stakes=InputState.DEFAULTED,
        )
        actor_b = ActorState(
            n_pub=float(row.get("n_pub_b", 0.9)),
            status_quo_burden=0.5,
            capability_share=float(row.get("c_t_ba", 0.5)),
            b_econ=0.0,
            b_blood=0.0,
            v_i=0.0,
            closing_window=float(row.get("closing_window_b", 0.5)),
            fma=float(row.get("fma", 0.0)),
            cap_proxy=float(row.get("cap_b_to_a", 0.0)),
            shock_k=0.0,
            deesc_inputs=(0.0, 0.0, 0.0),
            attribution=0.0,
            state_b_econ=InputState.ABSENT,
            state_b_blood=InputState.ABSENT,
            state_v_i=InputState.ABSENT,
            state_fma=InputState.OBSERVED,
            state_closing_window=InputState.OBSERVED,
            state_belief=InputState.ABSENT,
            state_cap=InputState.OBSERVED,
            state_shock=InputState.DEFAULTED,
            state_deesc=InputState.DEFAULTED,
            state_attribution=InputState.DEFAULTED,
            state_stakes=InputState.DEFAULTED,
        )
        return score_dyad_year(actor_a, actor_b, sym, self.priors)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0, help="Optional cap per split (0 = full population)")
    parser.add_argument("--n-boot", type=int, default=200)
    parser.add_argument("--seed", type=int, default=RANDOM_STATE)
    args = parser.parse_args()

    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    df, stats = load_feature_grid("v27")
    print(f"Loaded {stats.path}: consecutive_joined={stats.n_joined:,}")

    priors = Priors()
    train = df[df["year"] <= TRAIN_SPLIT].copy().reset_index(drop=True)
    test = df[df["year"] > TRAIN_SPLIT].copy().reset_index(drop=True)
    train_rates = training_base_rates(train, ALL_TARGETS)

    rows: list[dict] = []
    splits = {"train_1946_1989": train, "test_1990_2014": test}
    for split_name, sub in splits.items():
        inc = None
        if args.sample > 0 and len(sub) > args.sample:
            prob = float(args.sample) / float(len(sub))
            sub = sub.sample(args.sample, random_state=args.seed).reset_index(drop=True)
            inc = np.full(len(sub), prob, dtype=float)
        print(f"--- {split_name}: scoring {len(sub):,} rows ---")
        res = score_dataframe_v27(sub, priors)
        clusters = unordered_dyad_codes(sub)
        rows.extend(
            evaluate_pis_on_split(
                sub, res["pi"], split_name, "TIERS v27", train_rates,
                target_names=ALL_TARGETS, clusters=clusters, inclusion_prob=inc,
                n_boot=args.n_boot, seed=args.seed,
            )
        )

    out = pd.DataFrame(rows)
    csv_path = os.path.join(OUT_ANALYSIS, "model_backtest_v27_phase1_metrics.csv")
    out.to_csv(csv_path, index=False)

    lines = stamp_header_lines(
        "TIERS v27.0 Phase 1 Evaluation Report",
        stats=stats,
        parameters_desc="default v27 Priors()",
        seed=args.seed,
        extra=[
            f"- **Bootstrap:** {args.n_boot} unordered-dyad-clustered replicates; metrics suppressed below {MIN_POSITIVES} positives.",
        ],
    )
    for split_name in ("test_1990_2014", "train_1946_1989"):
        lines.extend([
            f"## {split_name}",
            "",
            "| Target | n_pos | n_neg | ROC AUC (95% CI) | Avg Prec (95% CI) | Brier | Brier Skill | Log Loss |",
            "|---|---:|---:|---|---|---:|---:|---:|",
        ])
        sub_m = out[
            (out["split"] == split_name) & (out["target"].isin(HEADLINE_TARGETS + EXACT_STEP_TARGETS))
        ]
        for r in sub_m.itertuples(index=False):
            b_s = f"{r.brier:.4f}" if np.isfinite(r.brier) else "suppressed"
            bss_s = f"{r.brier_skill:.4f}" if np.isfinite(r.brier_skill) else "suppressed"
            ll_s = f"{r.log_loss:.4f}" if np.isfinite(r.log_loss) else "suppressed"
            lines.append(
                f"| {r.target} | {r.n_sample_pos:,} | {r.n_sample_neg:,} | "
                f"{format_ci(r.roc_auc, r.roc_auc_ci_lo, r.roc_auc_ci_hi)} | "
                f"{format_ci(r.avg_precision, r.avg_precision_ci_lo, r.avg_precision_ci_hi)} | "
                f"{b_s} | {bss_s} | {ll_s} |"
            )
        lines.append("")

    md_path = os.path.join(OUT_ANALYSIS, "model_calibration_summary_v27.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {csv_path}")
    print(f"Summary -> {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
