"""Back-test the TIERS v28.0 transition-hazard engine.

Reads `data/processed/dyads_with_features_v28.parquet` and evaluates the same
headline and adjacent-transition targets used by the v27 backtest, plus the
1995-2014 trade-enhanced window specified in the v28 draft.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from tiers_lib_v27 import ActorState, DyadState, InputState
from tiers_lib_v28 import Priors, priors_from_mapping, score_dyad_year

YEAR_LO, YEAR_HI = 1946, 2014
TRAIN_SPLIT = 1989
SAMPLE_DEFAULT = 200_000
TRANSITION_STEPS = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]


@dataclass
class V28Calibrator:
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
        # v28 directed trade terms.
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


def load_data() -> pd.DataFrame:
    pq = os.path.join(DATA_PROCESSED, "dyads_with_features_v28.parquet")
    csv = os.path.join(DATA_PROCESSED, "dyads_with_features_v28.csv")
    df = pd.read_parquet(pq) if os.path.exists(pq) else pd.read_csv(csv)
    df = df[(df.year >= YEAR_LO) & (df.year <= YEAR_HI)].copy()
    df = df.sort_values("year")
    df["uiw_tier_next"] = df.groupby(["initiator", "target"])["uiw_tier"].shift(-1)
    df["escalate"] = (df["uiw_tier_next"].fillna(0) > df["uiw_tier"]).astype(int)
    df["escalate_to_t1_plus"] = (df["uiw_tier"] == 0) & (df["uiw_tier_next"].fillna(0) >= 1)
    df["escalate_to_t4_plus"] = (df["uiw_tier"] <= 3) & (df["uiw_tier_next"].fillna(0) >= 4)
    return df.dropna(subset=["uiw_tier_next"]).reset_index(drop=True)


def score_pis(sample: pd.DataFrame, cal: V28Calibrator) -> np.ndarray:
    pis = np.zeros((len(sample), 6))
    for i, (_, row) in enumerate(sample.iterrows()):
        pis[i] = cal.score_row(row)["pi_reconciled"]
        if (i + 1) % 25_000 == 0:
            print(f"    {i + 1:,} / {len(sample):,}")
    return pis


def _metrics(label: str, y_true, y_score) -> dict:
    n_pos = int(np.sum(y_true))
    n_neg = int(len(y_true) - n_pos)
    row = {"threshold": label, "auc": np.nan, "brier": np.nan, "n_pos": n_pos, "n_neg": n_neg}
    if n_pos >= 5 and n_neg >= 5:
        row["auc"] = round(float(roc_auc_score(y_true, y_score)), 4)
        row["brier"] = round(float(brier_score_loss(y_true, y_score)), 4)
    return row


def evaluate(df: pd.DataFrame, cal: V28Calibrator, tag: str, sample_cap: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    sample = df.sample(min(sample_cap, len(df)), random_state=42) if len(df) > sample_cap else df
    print(f"\n--- {tag}: scoring {len(sample):,} rows ---")
    pis = score_pis(sample, cal)
    headline = pd.DataFrame([
        _metrics("T0->T1+", sample["escalate_to_t1_plus"].values, 1.0 - pis[:, 0]),
        _metrics("T0->T4+", sample["escalate_to_t4_plus"].values, pis[:, 4] + pis[:, 5]),
        _metrics("T0->T5", (sample["uiw_tier_next"] == 5).astype(int).values, pis[:, 5]),
        _metrics("Any esc", sample["escalate"].values, 1.0 - pis[:, 0]),
    ])
    headline.insert(0, "tag", tag)

    cur = sample["uiw_tier"].astype(int).to_numpy()
    nxt = sample["uiw_tier_next"].astype(int).to_numpy()
    rows = []
    for k, kp1 in TRANSITION_STEPS:
        mask = cur == k
        if not mask.any():
            continue
        rows.append({"tag": tag, "variant": "exact", **_metrics(f"T{k}->T{kp1}", (nxt[mask] == kp1).astype(int), pis[mask, kp1])})
        rows.append({"tag": tag, "variant": "cumulative", **_metrics(f"T{k}->T{kp1}", (nxt[mask] >= kp1).astype(int), pis[mask, kp1:].sum(axis=1))})
    perstep = pd.DataFrame(rows)
    print(headline.to_string(index=False))
    return headline, perstep


def write_summary(parts: dict[str, tuple[pd.DataFrame, pd.DataFrame]]) -> None:
    lines = [
        "# v28.0 model calibration summary",
        "",
        "v28 uses edge-specific transition hazards plus CEPII BACI/TRADHIST trade",
        "surface, directed dependence, directed leverage, and mutual-dependence",
        "terms. Priors are sign-constrained starting values; full calibration is pending.",
        "",
    ]
    for tag, (head, per) in parts.items():
        lines.extend([f"## {tag}", "", "| Threshold | AUC | Brier | n_pos | n_neg |", "|---|---:|---:|---:|---:|"])
        for r in head.itertuples(index=False):
            lines.append(f"| {r.threshold} | {r.auc} | {r.brier} | {r.n_pos} | {r.n_neg} |")
        lines.extend(["", "| Transition | Variant | AUC | Brier | n_pos | n_neg |", "|---|---|---:|---:|---:|---:|"])
        for r in per.itertuples(index=False):
            lines.append(f"| {r.threshold} | {r.variant} | {r.auc} | {r.brier} | {r.n_pos} | {r.n_neg} |")
        lines.append("")
    path = os.path.join(OUT_ANALYSIS, "model_calibration_summary_v28.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    print(f"\nSummary -> {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=SAMPLE_DEFAULT)
    parser.add_argument(
        "--priors",
        help="Optional JSON file containing calibrated v28 prior values.",
    )
    args = parser.parse_args()
    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    df = load_data()
    print(f"Data: {len(df):,} dyad-years with next-year tier")
    priors = Priors()
    if args.priors:
        with open(args.priors, "r", encoding="utf-8") as f:
            payload = json.load(f)
        priors = priors_from_mapping(payload.get("priors", payload))
        print(f"Loaded calibrated priors: {args.priors}")
    cal = V28Calibrator(priors)
    windows = {
        "train_1946_1989": df[df.year <= TRAIN_SPLIT].copy(),
        "test_1990_2014": df[df.year > TRAIN_SPLIT].copy(),
        "trade_window_1995_2014": df[(df.year >= 1995) & (df.year <= 2014)].copy(),
    }
    parts = {}
    for tag, sub in windows.items():
        head, per = evaluate(sub, cal, tag, args.sample)
        head.to_csv(os.path.join(OUT_ANALYSIS, f"model_backtest_roc_v28_{tag}.csv"), index=False)
        per.to_csv(os.path.join(OUT_ANALYSIS, f"model_backtest_roc_v28_perstep_{tag}.csv"), index=False)
        parts[tag] = (head, per)
    write_summary(parts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
