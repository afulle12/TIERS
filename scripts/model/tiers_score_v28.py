"""Forward-score live interstate dyads using the TIERS v28.0 engine."""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from evaluation import escalation_probability  # noqa: E402
from tiers_lib_v28 import Priors, score_dataframe_v28  # noqa: E402

DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_FORECASTS = os.path.join(ROOT, "output", "forecasts")


def score_year(year: int, out_path: str, priors: Priors | None = None) -> pd.DataFrame:
    pq = os.path.join(DATA_PROCESSED, "dyads_with_features_v28.parquet")
    if not os.path.exists(pq):
        print(f"[ERR] missing {pq}; run scripts/build/build_features_v28.py first")
        raise SystemExit(1)
    df = pd.read_parquet(pq)
    df = df[df.year == year].copy().reset_index(drop=True)
    if df.empty:
        print(f"[ERR] no rows for year {year}")
        raise SystemExit(1)
    print(f"Year {year}: {len(df):,} live directed pairs")

    res = score_dataframe_v28(df, priors or Priors())
    pis = res["pi"]
    cur = df["uiw_tier"].fillna(0).astype(int).to_numpy()
    p_any_esc = escalation_probability(pis, cur)

    def _col(name: str, default=0.0):
        return df[name].to_numpy() if name in df.columns else np.full(len(df), default)

    out = pd.DataFrame({
        "year": year,
        "initiator": _col("initiator", ""),
        "target": _col("target", ""),
        "current_tier": cur,
        "P_T0": pis[:, 0],
        "P_T1": pis[:, 1],
        "P_T2": pis[:, 2],
        "P_T3": pis[:, 3],
        "P_T4": pis[:, 4],
        "P_T5": pis[:, 5],
        "P_any_esc": p_any_esc,
        "P_t4_plus": pis[:, 4] + pis[:, 5],
        "P_t5": pis[:, 5],
        "trade_source": df["trade_source"].fillna("NONE").to_numpy() if "trade_source" in df.columns else "NONE",
        "trade_surface_norm_ab": _col("trade_surface_norm_ab", 0.0),
        "mutual_trade_dependence_ab": _col("mutual_trade_dependence_ab", 0.0),
        "trade_leverage_a_over_b": _col("trade_leverage_a_over_b", 0.0),
        "dep_a_on_b": _col("dep_a_on_b", 0.0),
        "dep_b_on_a": _col("dep_b_on_a", 0.0),
        "contiguity_xi": _col("contiguity_xi", 0.0),
        "rivalry_omega": _col("rivalry_omega", 0.0),
        "rivalry_omega_b": _col("rivalry_omega_b", 0.0),
        "cap_a_to_b": _col("cap_a_to_b", 0.0),
        "cap_b_to_a": _col("cap_b_to_a", 0.0),
        "gate_t5": res["gate_t5"].astype(bool),
        "active_member": res["member_ab"],
    })
    out = out.sort_values("P_t5", ascending=False).reset_index(drop=True)
    out.to_csv(out_path, index=False)
    print(f"Wrote {len(out):,} directed forecasts -> {out_path}")
    print("Top 20 by P(T5):")
    cols = [
        "initiator", "target", "current_tier", "P_T5", "P_t4_plus",
        "P_any_esc", "trade_source", "mutual_trade_dependence_ab", "gate_t5",
    ]
    print(out[cols].head(20).to_string(index=False))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--out-dir", default=OUT_FORECASTS)
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    if args.year is None:
        df = pd.read_parquet(
            os.path.join(DATA_PROCESSED, "dyads_with_features_v28.parquet"), columns=["year"]
        )
        args.year = int(df["year"].max())
        print(f"Latest year in v28 grid: {args.year}")
    out_path = os.path.join(args.out_dir, f"forward_score_v28_{args.year}.csv")
    score_year(args.year, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
