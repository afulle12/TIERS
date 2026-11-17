"""Forward-score live interstate dyads using the TIERS v28.0 engine."""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from backtest_tiers_v28 import V28Calibrator
from tiers_lib_v28 import Priors

DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_FORECASTS = os.path.join(ROOT, "output", "forecasts")


def score_year(year: int, out_path: str) -> pd.DataFrame:
    pq = os.path.join(DATA_PROCESSED, "dyads_with_features_v28.parquet")
    if not os.path.exists(pq):
        print(f"[ERR] missing {pq}; run scripts/build/build_features_v28.py first")
        raise SystemExit(1)
    df = pd.read_parquet(pq)
    df = df[df.year == year].copy()
    if df.empty:
        print(f"[ERR] no rows for year {year}")
        raise SystemExit(1)
    print(f"Year {year}: {len(df):,} live directed pairs")

    cal = V28Calibrator(Priors())
    rows = []
    for i, (_, row) in enumerate(df.iterrows()):
        res = cal.score_row(row)
        pi = res["pi_reconciled"]
        rows.append({
            "year": year,
            "initiator": row.get("initiator"),
            "target": row.get("target"),
            "current_tier": int(row.get("uiw_tier", 0)),
            "P_T0": pi[0], "P_T1": pi[1], "P_T2": pi[2],
            "P_T3": pi[3], "P_T4": pi[4], "P_T5": pi[5],
            "P_any_esc": 1.0 - pi[0],
            "P_t4_plus": pi[4] + pi[5],
            "P_t5": pi[5],
            "trade_source": row.get("trade_source", "NONE"),
            "trade_surface_norm_ab": row.get("trade_surface_norm_ab", 0.0),
            "mutual_trade_dependence_ab": row.get("mutual_trade_dependence_ab", 0.0),
            "trade_leverage_a_over_b": row.get("trade_leverage_a_over_b", 0.0),
            "dep_a_on_b": row.get("dep_a_on_b", 0.0),
            "dep_b_on_a": row.get("dep_b_on_a", 0.0),
            "contiguity_xi": row.get("contiguity_xi", 0.0),
            "rivalry_omega": row.get("rivalry_omega", 0.0),
            "cap_a_to_b": row.get("cap_a_to_b", 0.0),
            "cap_b_to_a": row.get("cap_b_to_a", 0.0),
            "gate_t5": bool(res["gate_t5"]),
            "active_member": res["member_ab"],
        })
        if (i + 1) % 50_000 == 0:
            print(f"  {i + 1:,} / {len(df):,}")

    out = pd.DataFrame(rows).sort_values("P_t5", ascending=False).reset_index(drop=True)
    out.to_csv(out_path, index=False)
    print(f"Wrote {len(out):,} directed forecasts -> {out_path}")
    print("Top 20 by P(T5):")
    cols = ["initiator", "target", "current_tier", "P_T5", "P_t4_plus", "P_any_esc", "trade_source", "mutual_trade_dependence_ab", "gate_t5"]
    print(out[cols].head(20).to_string(index=False))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--out-dir", default=OUT_FORECASTS)
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    if args.year is None:
        df = pd.read_parquet(os.path.join(DATA_PROCESSED, "dyads_with_features_v28.parquet"), columns=["year"])
        args.year = int(df["year"].max())
        print(f"Latest year in v28 grid: {args.year}")
    out_path = os.path.join(args.out_dir, f"forward_score_v28_{args.year}.csv")
    score_year(args.year, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
