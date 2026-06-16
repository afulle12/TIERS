"""Back-test the Unified Equation of Interstate War against the T0-T5 dataset.

Paths:
  1. Calibrate β (beta) to match the observed P(T0 -> T1+) rate.
  2. Score each directed (initiator, target, year) with the model.
  3. ROC curves per escalation threshold.
  4. Calibration: predicted P(escalate) vs observed fraction.

Requires:
  data/processed/dyads_with_features.parquet (or .csv) — from build_features.py

Outputs:
  output/analysis/model_backtest_roc.csv
  output/analysis/model_backtest_calibration.csv
  output/charts/model_backtest_roc.png
  output/charts/model_backtest_calibration.png
  output/analysis/model_calibration_summary.md
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

YEAR_LO, YEAR_HI = 1946, 2014
TRAIN_SPLIT = 1989  # train 1946-1989, test 1990-2014

C_b = 0.95  # Betrayal penalty constant (from war_model.py)


@dataclass
class State:
    """Minimal state object for model evaluation. All params are empirical."""
    name: str
    N_pub: float = 0.9
    beta: float = 0.02
    dP: float = 0.0
    R_d: float = 0.0
    A_div: float = 0.0
    P_v: float = 0.0
    V_p: float = 0.0
    V_t: float = 0.0
    C_T: float = 0.5
    W_v: float = 0.0
    B: float = 0.0
    R_h: float = 0.0
    I_s: float = 0.0
    I_a: float = 0.5
    C_p: float = 0.3
    I_i: float = 0.3
    C_i: float = 0.5
    C_d_sup: float = 0.0
    C_d_opp: float = 0.0
    E_n_sup: float = 0.0
    E_n_opp: float = 0.0
    S_p_sup: float = 0.0
    S_p_opp: float = 0.0


def p_init(A: State, B: State, beta: float) -> float:
    """Path 1 core initiation probability A -> B (uses beta param)."""
    M = max((A.dP + A.R_d + A.A_div) / 3.0, A.P_v)
    O = max(A.V_p, A.V_t) * (1.0 - B.C_T * (1.0 - A.W_v))
    O = max(0.0, O)
    S = (A.B + A.R_h + A.I_s) / 3.0
    C_p_star = 1.0 if A.V_t > A.V_p else A.C_p
    F = 1.0 - (1.0 - A.I_a) * (1.0 - C_p_star) * (1.0 - A.I_i)
    return beta * M * O * S * F


def p_direct(A: State, B: State, beta: float) -> float:
    return (1.0 - A.N_pub) * p_init(A, B, beta)


def score_dyad(row: pd.Series, beta: float) -> float:
    """Score a directed dyad-year row: returns P_direct(A->B)."""
    # Fill missing empirical features with reasonable defaults
    n_pub_a = row.get("n_pub_a", 0.9)
    dp_a = row.get("dp_a", 0.0)
    r_d_ab = row.get("r_d_ab", 0.0)
    c_t_ab = row.get("c_t_ab", 0.5)
    c_d_sup = row.get("c_d_sup_ab", 0.0)
    c_d_opp = row.get("c_d_opp_ab", 0.0)

    A = State(
        name=str(row.get("initiator", "")),
        N_pub=n_pub_a,
        beta=beta,
        dP=min(max(dp_a, 0.05), 1.0),  # power shift dissatisfaction
        R_d=min(max(r_d_ab, 0.05), 1.0),  # revisionist demands (capability ratio proxy)
        A_div=0.0,           # diversionary (not yet empirically populated)
        P_v=0.0,             # predatory (not yet empirically populated)
        V_p=0.2,             # probing: default moderate value
        V_t=0.0,             # total war: 0 by default
        C_T=c_t_ab,          # target's defensive capability (from NMC)
        W_v=0.1,             # window of vulnerability: small default
        B=0.2,               # brinkmanship: moderate default
        R_h=0.3,             # historical rivalry: moderate default
        I_s=0.2,             # incidents/sparks: moderate default
        I_a=0.5,             # information asymmetry (neutral)
        C_p=0.3,             # commitment problem (neutral)
        I_i=0.3,             # indivisibility (neutral)
        C_i=0.5,             # intervention cost (neutral)
        C_d_sup=c_d_sup,
        C_d_opp=c_d_opp,
        E_n_sup=0.0,
        E_n_opp=0.0,
        S_p_sup=0.0,
        S_p_opp=0.0,
    )

    # State B uses the same features but from B's perspective
    n_pub_b = row.get("n_pub_b", 0.9)
    B = State(
        name=str(row.get("target", "")),
        N_pub=n_pub_b,
        beta=beta,
        C_T=c_t_ab,  # B's capability vs A (reversed)
    )

    return p_direct(A, B, beta)


def load_data() -> pd.DataFrame:
    """Load the feature grid and attach year-over-year escalation targets."""
    parquet_path = os.path.join(DATA_PROCESSED, "dyads_with_features.parquet")
    csv_path = os.path.join(DATA_PROCESSED, "dyads_with_features.csv")
    if os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)
        print(f"Loaded {parquet_path}")
    elif os.path.exists(csv_path):
        df = pd.read_csv(csv_path, dtype={"year": int})
        print(f"Loaded {csv_path}")
    else:
        print("No dyads_with_features file found. Run build_features.py first.")
        sys.exit(1)

    # Restrict to fully-covered years
    df = df[(df.year >= YEAR_LO) & (df.year <= YEAR_HI)].copy()

    # Create year-over-year targets: for each dyad, find next-year tier
    dyad_next = (
        df.sort_values("year")
        .groupby(["initiator_gwno", "target_gwno"])["uiw_tier"]
        .shift(-1)
        .rename("uiw_tier_next")
    )
    df["uiw_tier_next"] = dyad_next
    df["escalate"] = (df["uiw_tier_next"].fillna(0) > df["uiw_tier"]).astype(int)
    df["escalate_to_t1_plus"] = (df["uiw_tier"] == 0) & (df["uiw_tier_next"].fillna(0) >= 1)
    df["escalate_to_t4_plus"] = (df["uiw_tier"] <= 3) & (df["uiw_tier_next"].fillna(0) >= 4)

    # Drop rows without a next year
    df = df.dropna(subset=["uiw_tier_next"]).reset_index(drop=True)
    print(f"Data: {len(df):,} dyad-years with next-year tier ({YEAR_LO}-{YEAR_HI})")
    print(f"  T0 start years: {(df.uiw_tier == 0).sum():,}")
    print(f"  T0->T1+ esc: {df.escalate_to_t1_plus.sum():,} ({df.escalate_to_t1_plus.mean():.4%})")

    return df


def calibrate_beta(df: pd.DataFrame) -> float:
    """Grid-search beta to match the observed T0->T1+ escalation rate."""
    train = df[(df.year >= YEAR_LO) & (df.year <= TRAIN_SPLIT)].copy()
    observed = train["escalate_to_t1_plus"].mean()
    print(f"\n--- Beta calibration (train {YEAR_LO}-{TRAIN_SPLIT}) ---")
    print(f"Observed P(T0->T1+): {observed:.6f}")

    # Sample a subset for speed
    t0_train = train[train.uiw_tier == 0].sample(min(50000, (train.uiw_tier == 0).sum()),
                                                   random_state=42)
    if len(t0_train) == 0:
        print("[WARN] No T0 rows in training set; using default beta=0.02")
        return 0.02

    best_beta = 0.02
    best_err = float("inf")
    candidates = np.logspace(-4, -1, 30)
    for b in candidates:
        scores = t0_train.apply(lambda r: score_dyad(r, b), axis=1)
        predicted = scores.mean()
        err = abs(predicted - observed)
        if err < best_err:
            best_err = err
            best_beta = b
    print(f"Calibrated beta: {best_beta:.6f} (predicted P={observed:.6f}, err={best_err:.6f})")
    return best_beta


def evaluate(df: pd.DataFrame, beta: float, tag: str):
    """Score all rows, compute ROC and calibration for multiple thresholds."""
    print(f"\n--- Evaluation: {tag} ---")
    rows = []

    # Score all rows (use a sample if very large)
    n_sample = min(200000, len(df))
    sample = df.sample(n_sample, random_state=42) if len(df) > n_sample else df
    print(f"  Scoring {len(sample):,} dyad-years...")

    sample = sample.copy()
    sample["score"] = sample.apply(lambda r: score_dyad(r, beta), axis=1)

    thresholds = [
        ("T0->T1+", "escalate_to_t1_plus"),
        ("T0->T4+", "escalate_to_t4_plus"),
        ("T0->T5", "uiw_tier_next", 5),
        ("Any esc", "escalate"),
    ]

    roc_data = []
    cal_data = []

    for label, target_col, *target_val in thresholds:
        if target_val:
            y_true = (sample[target_col] == target_val[0]).astype(int)
        else:
            y_true = sample[target_col].values

        y_score = sample["score"].values

        n_pos = y_true.sum()
        n_neg = len(y_true) - n_pos
        if n_pos < 5 or n_neg < 5:
            print(f"  {label}: too few events (pos={n_pos}, neg={n_neg}), skipping")
            continue

        auc = roc_auc_score(y_true, y_score)
        brier = brier_score_loss(y_true, y_score)

        fpr, tpr, thresholds_roc = roc_curve(y_true, y_score)
        roc_data.append((label, fpr, tpr, auc, n_pos, n_neg))

        # Calibration: bin scores into deciles
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
            "tag": tag,
            "threshold": label,
            "auc": round(auc, 4),
            "brier": round(brier, 4),
            "n_pos": n_pos,
            "n_neg": n_neg,
        })
        print(f"  {label}: AUC={auc:.4f}  Brier={brier:.4f}  (pos={n_pos}, neg={n_neg})")

    roc_df = pd.DataFrame(rows)
    roc_path = os.path.join(OUT_ANALYSIS, f"model_backtest_roc_{tag}.csv")
    roc_df.to_csv(roc_path, index=False)

    return roc_data, cal_data, roc_df


def plot_roc(roc_data: list, tag: str):
    fig, ax = plt.subplots(figsize=(8, 7))
    colors = ["#d53e4f", "#fdae61", "#abdda4", "#74add1", "#fee08b"]
    for (label, fpr, tpr, auc, n_pos, n_neg), c in zip(roc_data, colors):
        ax.plot(fpr, tpr, label=f"{label} (AUC={auc:.3f}, n_pos={n_pos})", color=c, lw=2)
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title(f"Model back-test ROC: {tag}\n(beta calibrated on T0->T1+)")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out_path = os.path.join(OUT_CHARTS, f"model_backtest_roc_{tag}.png")
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"ROC chart -> {out_path}")


def plot_calibration(cal_data: list, tag: str):
    fig, ax = plt.subplots(figsize=(7, 6))
    colors = ["#d53e4f", "#fdae61", "#abdda4", "#74add1"]
    for (label, cal), c in zip(cal_data, colors):
        ax.plot(cal["pred_mean"], cal["obs_mean"], "o-", color=c, label=label, lw=1.5, ms=4)
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, label="Perfect")
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Observed fraction")
    ax.set_title(f"Model calibration: {tag}\n(beta={beta_calib:.6f})")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_xlim(0, min(1, ax.get_xlim()[1]))
    ax.set_ylim(0, min(1, ax.get_ylim()[1]))
    fig.tight_layout()
    out_path = os.path.join(OUT_CHARTS, f"model_backtest_calibration_{tag}.png")
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"Calibration chart -> {out_path}")


def write_summary(train_roc: pd.DataFrame, test_roc: pd.DataFrame, beta: float):
    lines = [
        "# Model calibration summary",
        "",
        f"Calibrated β (beta): {beta:.6f}",
        "",
        "## Training set ({YEAR_LO}-{TRAIN_SPLIT})",
        "",
        "| Threshold | AUC | Brier | n_pos | n_neg |",
        "|---|---|---|---|---|",
    ]
    for _, r in train_roc.iterrows():
        lines.append(f"| {r.threshold} | {r.auc} | {r.brier} | {r.n_pos} | {r.n_neg} |")
    lines.append("")
    lines.append(f"## Test set ({TRAIN_SPLIT+1}-{YEAR_HI})")
    lines.append("")
    lines.append("| Threshold | AUC | Brier | n_pos | n_neg |")
    lines.append("|---|---|---|---|---|")
    for _, r in test_roc.iterrows():
        lines.append(f"| {r.threshold} | {r.auc} | {r.brier} | {r.n_pos} | {r.n_neg} |")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Only Path 1 (direct initiation) is scored; Path 2 (contagion) needs `W_sev` lookup.")
    lines.append("- Many structural parameters (A_div, P_v, R_h, B, I_s, E_n, S_p) are set to defaults")
    lines.append("  because the corresponding empirical datasets have not been attached yet.")
    lines.append("- The model currently uses N_pub (from V-Dem polyarchy), dP and C_T (from COW NMC),")
    lines.append("  and alliance depth (from ATOP). These datasets must be downloaded and placed in")
    lines.append("  data/raw/ for features to be populated.")
    lines.append("- Additional data needed: rivalry history (R_h), diversionary incentives (A_div),")
    lines.append("  contiguity/distance (V_p/V_t/W_v from CShapes geometry), and ethnic kinship (E_n).")
    lines.append("")

    summary_path = os.path.join(OUT_ANALYSIS, "model_calibration_summary.md")
    with open(summary_path, "w") as f:
        f.write("\n".join(lines))
    print(f"\nSummary -> {summary_path}")


def main() -> int:
    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    os.makedirs(OUT_CHARTS, exist_ok=True)

    global beta_calib

    df = load_data()

    # Split
    train = df[df.year <= TRAIN_SPLIT].copy()
    test = df[df.year > TRAIN_SPLIT].copy()
    print(f"Train: {len(train):,}  Test: {len(test):,}")

    # Calibrate beta
    beta_calib = calibrate_beta(df)

    # Evaluate
    train_roc_data, train_cal_data, train_roc_df = evaluate(train, beta_calib, "train")
    test_roc_data, test_cal_data, test_roc_df = evaluate(test, beta_calib, "test")

    # Charts
    if train_roc_data:
        plot_roc(train_roc_data, "train")
    if test_roc_data:
        plot_roc(test_roc_data, "test")
    if train_cal_data:
        plot_calibration(train_cal_data, "train")

    # Summary
    write_summary(train_roc_df, test_roc_df, beta_calib)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    beta_calib = 0.02  # will be overwritten
    raise SystemExit(main())
