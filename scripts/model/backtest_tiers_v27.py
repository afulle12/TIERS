"""Back-test the v27.0 cost-field engine against the T0-T5 dataset.

Mirrors `backtest_tiers.py` (the v21 product-form backtest) so the v21 and
v27 numbers can be compared directly:
  - Same train/test split: train 1946-1989, test 1990-2014.
  - Same ROC + calibration outputs.

Scoring uses the v27.0 engine's reconciled dyad-level distribution. For the
ROC we use P(next_tier >= threshold) as the score and the next-year
thresholded tier as the label.

Reads:
  data/processed/dyads_with_features_v27.parquet

Writes:
  output/analysis/model_backtest_roc_v27.csv
  output/analysis/model_backtest_calibration_v27.csv
  output/charts/model_backtest_roc_v27.png
  output/charts/model_backtest_calibration_v27.png
  output/analysis/model_calibration_summary_v27.md
"""
from __future__ import annotations

import os
import sys
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.metrics import roc_auc_score, roc_curve, brier_score_loss

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
OUT_CHARTS = os.path.join(ROOT, "output", "charts")

sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))
from tiers_lib_v27 import (
    ActorState,
    DyadState,
    InputState,
    Priors,
    score_dyad_year,
    resolve_active_member,
)

YEAR_LO, YEAR_HI = 1946, 2014
TRAIN_SPLIT = 1989

# Scoring sample sizes (cap for speed; the v21 backtest used 200k)
SAMPLE_TRAIN = 200_000
SAMPLE_TEST = 200_000


@dataclass
class V27Calibrator:
    """Holds a single global β-equivalent scaling for the v27 engine.

    The v27 engine already has its own priors (b_0, b_tier, b_dur, u_D, u_A,
    u_Z, a_0, r_D, λ+, λ-). For a backtest, we leave the v27 priors at their
    spec defaults (the documented 'empirical priors set' values) and do NOT
    re-calibrate. Calibration is flagged as pending in the v27 spec section
    6.1; we are not pretending to do it here. The summary notes this.
    """
    priors: Priors

    def score_row(self, row: pd.Series) -> dict:
        """Build a v27 DyadState + ActorState from a v27 features row and
        return the engine's outputs (pi, gate, member).
        """
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
        # Actor A (initiator)
        n_pub_a = float(row.get("n_pub_a", 0.9))
        actor_a = ActorState(
            n_pub=n_pub_a,
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
            # All occupancy components absent -> diagnostic fallback
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
        # Actor B (target)
        n_pub_b = float(row.get("n_pub_b", 0.9))
        actor_b = ActorState(
            n_pub=n_pub_b,
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
        result = score_dyad_year(actor_a, actor_b, sym, self.priors)
        return result


def load_data() -> pd.DataFrame:
    path_pq = os.path.join(DATA_PROCESSED, "dyads_with_features_v27.parquet")
    path_csv = os.path.join(DATA_PROCESSED, "dyads_with_features_v27.csv")
    if os.path.exists(path_pq):
        df = pd.read_parquet(path_pq)
    else:
        df = pd.read_csv(path_csv, dtype={"year": int})
    df = df[(df.year >= YEAR_LO) & (df.year <= YEAR_HI)].copy()

    # Create year-over-year targets: for each dyad, find next-year tier
    df = df.sort_values("year")
    next_tier = df.groupby(["initiator", "target"])["uiw_tier"].shift(-1)
    df["uiw_tier_next"] = next_tier
    df["escalate"] = (df["uiw_tier_next"].fillna(0) > df["uiw_tier"]).astype(int)
    df["escalate_to_t1_plus"] = (df["uiw_tier"] == 0) & (df["uiw_tier_next"].fillna(0) >= 1)
    df["escalate_to_t4_plus"] = (df["uiw_tier"] <= 3) & (df["uiw_tier_next"].fillna(0) >= 4)

    df = df.dropna(subset=["uiw_tier_next"]).reset_index(drop=True)
    print(f"Data: {len(df):,} dyad-years with next-year tier ({YEAR_LO}-{YEAR_HI})")
    print(f"  T0 start years: {(df.uiw_tier == 0).sum():,}")
    print(f"  T0->T1+ esc:   {df.escalate_to_t1_plus.sum():,} ({df.escalate_to_t1_plus.mean():.4%})")
    return df


def score_distribution(row: pd.Series, cal: V27Calibrator) -> List[float]:
    """Return the v27 reconciled next-tier distribution for this row."""
    res = cal.score_row(row)
    return res["pi_reconciled"]


def evaluate(df: pd.DataFrame, cal: V27Calibrator, tag: str):
    print(f"\n--- Evaluation: {tag} ---")
    n_sample = min(200_000, len(df))
    sample = df.sample(n_sample, random_state=42) if len(df) > n_sample else df
    print(f"  Scoring {len(sample):,} dyad-years...")

    pis = np.zeros((len(sample), 6))
    for i, (_, row) in enumerate(sample.iterrows()):
        pi = score_distribution(row, cal)
        pis[i] = pi
        if (i + 1) % 25_000 == 0:
            print(f"    {i+1:,} / {len(sample):,}")

    # P(any escalation) = 1 - P(T0)
    p_any_esc = 1.0 - pis[:, 0]
    p_to_t1_plus = 1.0 - pis[:, 0]  # T0->T1+ is "any non-T0 mass"
    p_to_t4_plus = pis[:, 4] + pis[:, 5]
    p_to_t5 = pis[:, 5]

    thresholds = [
        ("T0->T1+", sample["escalate_to_t1_plus"].values, p_to_t1_plus),
        ("T0->T4+", sample["escalate_to_t4_plus"].values, p_to_t4_plus),
        ("T0->T5",  (sample["uiw_tier_next"] == 5).astype(int).values, p_to_t5),
        ("Any esc", sample["escalate"].values, p_any_esc),
    ]

    rows = []
    roc_data = []
    cal_data = []
    for label, y_true, y_score in thresholds:
        n_pos = int(y_true.sum())
        n_neg = len(y_true) - n_pos
        if n_pos < 5 or n_neg < 5:
            print(f"  {label}: too few events (pos={n_pos}, neg={n_neg}), skipping")
            continue
        auc = roc_auc_score(y_true, y_score)
        brier = brier_score_loss(y_true, y_score)
        fpr, tpr, _ = roc_curve(y_true, y_score)
        roc_data.append((label, fpr, tpr, auc, n_pos, n_neg))
        # Calibration
        bins = np.linspace(0, y_score.max() + 1e-10, 11)
        digitized = np.digitize(y_score, bins) - 1
        cal_df = pd.DataFrame({"score": y_score, "true": y_true, "bin": digitized})
        cal = cal_df.groupby("bin").agg(
            n=("true", "size"),
            pred_mean=("score", "mean"),
            obs_mean=("true", "mean"),
        ).reset_index()
        cal = cal[cal.n >= 10]
        cal_data.append((label, cal))
        rows.append({
            "tag": tag, "threshold": label, "auc": round(auc, 4),
            "brier": round(brier, 4), "n_pos": n_pos, "n_neg": n_neg,
        })
        print(f"  {label}: AUC={auc:.4f}  Brier={brier:.4f}  (pos={n_pos}, neg={n_neg})")

    roc_df = pd.DataFrame(rows)
    roc_df.to_csv(os.path.join(OUT_ANALYSIS, f"model_backtest_roc_v27_{tag}.csv"), index=False)
    return roc_data, cal_data, roc_df


def plot_roc(roc_data, tag):
    fig, ax = plt.subplots(figsize=(8, 7))
    colors = ["#d53e4f", "#fdae61", "#abdda4", "#74add1", "#fee08b"]
    for (label, fpr, tpr, auc, n_pos, n_neg), c in zip(roc_data, colors):
        ax.plot(fpr, tpr, label=f"{label} (AUC={auc:.3f}, n_pos={n_pos})", color=c, lw=2)
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(f"v27.0 cost-field engine back-test ROC: {tag}")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_path = os.path.join(OUT_CHARTS, f"model_backtest_roc_v27_{tag}.png")
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"ROC chart -> {out_path}")


def plot_calibration(cal_data, tag):
    fig, ax = plt.subplots(figsize=(7, 6))
    colors = ["#d53e4f", "#fdae61", "#abdda4", "#74add1"]
    for (label, cal), c in zip(cal_data, colors):
        ax.plot(cal["pred_mean"], cal["obs_mean"], "o-", color=c, label=label, lw=1.5, ms=4)
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Perfect")
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Observed fraction")
    ax.set_title(f"v27.0 engine calibration: {tag}")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_path = os.path.join(OUT_CHARTS, f"model_backtest_calibration_v27_{tag}.png")
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"Calibration chart -> {out_path}")


def write_summary(train_roc, test_roc):
    lines = [
        "# v27.0 model calibration summary",
        "",
        "Empirical priors from the v27.0 spec section 3.8 are used at their",
        "default values (b_0=0.15, b_tier=0.04, b_dur=0.10, u_D=0.40, u_A=0.12,",
        "u_Z=0.55, a_0=0.20, r_D=0.03, λ+=λ-=1.20, τ=0.40, ξ*=0.5).",
        "Full MLE / Bayesian calibration is pending per spec section 6.1.",
        "",
        "## Training set (1946-1989)",
        "",
        "| Threshold | AUC | Brier | n_pos | n_neg |",
        "|---|---|---|---|---|",
    ]
    for _, r in train_roc.iterrows():
        lines.append(
            f"| {r.threshold} | {r.auc} | {r.brier} | {r.n_pos} | {r.n_neg} |"
        )
    lines.append("")
    lines.append("## Test set (1990-2014)")
    lines.append("")
    lines.append("| Threshold | AUC | Brier | n_pos | n_neg |")
    lines.append("|---|---|---|---|---|")
    for _, r in test_roc.iterrows():
        lines.append(
            f"| {r.threshold} | {r.auc} | {r.brier} | {r.n_pos} | {r.n_neg} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Cost-field occupancy components (B^econ, B^blood, V_i) are")
    lines.append("  ABSENT in the backtest -> the engine runs in **diagnostic-fallback**")
    lines.append("  member for every row (spec section 1.9.2 / 3.1). Calibration")
    lines.append("  of the cost-field weights β_{1,2,3} is TBD in the spec.")
    lines.append("- Capability/Reach gate, Attribution×Duration T3->T4 factor,")
    lines.append("  status-quo-biased down-barrier, and public member are all active.")
    lines.append("- All structural inputs (Xi, FMA, -W_dot, Ω, D_k, Cap) are empirical")
    lines.append("  except A_div, E_n, S_p which are documented as defaulted.")
    lines.append("- Compare with `model_calibration_summary.md` (v21 product-form).")
    lines.append("")
    path = os.path.join(OUT_ANALYSIS, "model_calibration_summary_v27.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"\nSummary -> {path}")


def main():
    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    os.makedirs(OUT_CHARTS, exist_ok=True)
    priors = Priors()
    cal = V27Calibrator(priors=priors)

    df = load_data()
    train = df[df.year <= TRAIN_SPLIT].copy()
    test = df[df.year > TRAIN_SPLIT].copy()
    print(f"Train: {len(train):,}  Test: {len(test):,}")

    train_roc_data, train_cal_data, train_roc_df = evaluate(train, cal, "train")
    test_roc_data, test_cal_data, test_roc_df = evaluate(test, cal, "test")

    if train_roc_data:
        plot_roc(train_roc_data, "train")
    if test_roc_data:
        plot_roc(test_roc_data, "test")
    if train_cal_data:
        plot_calibration(train_cal_data, "train")
    write_summary(train_roc_df, test_roc_df)
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
