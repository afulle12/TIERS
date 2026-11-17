"""Forward-score live interstate dyads as of a target year using the v27.0
cost-field engine.

Loads the v27 features grid and emits, for every directed pair (i, j) active
in the target year, the reconciled next-tier distribution and a missing-
coverage flag column. The forecast is a 1-year forward probability distribution
over T0-T5.

Reads:
  data/processed/dyads_with_features_v27.parquet (the v27 features grid;
  restricted to YEAR_LO=1946-2014 by construction; the structural data
  sources stop at: MIDB 2014, V-Dem 2024, NMC 2022, CShapes 2019).
  The latest year available in the v27 grid is 2014 (because MIDB does not
  extend past 2014). For a true 2026 forecast, an event-data extension
  (ICEWS / GDELT) is needed; this script reports the available maximum.

Writes:
  output/forecasts/forward_score_<year>.csv
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from tiers_lib_v27 import (
    ActorState,
    DyadState,
    InputState,
    Priors,
    score_dyad_year,
)

DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_FORECASTS = os.path.join(ROOT, "output", "forecasts")
YEAR_LO_DEFAULT = 1946


def _build_states_from_row(row: pd.Series) -> tuple:
    """Translate a v27 features row into DyadState + two ActorStates."""
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
        capability_share=float(row.get("c_t_ab", 0.5)),
        b_econ=0.0, b_blood=0.0, v_i=0.0,
        closing_window=float(row.get("closing_window_a", 0.5)),
        fma=float(row.get("fma", 0.0)),
        cap_proxy=float(row.get("cap_a_to_b", 0.0)),
        shock_k=0.0,
        deesc_inputs=(0.0, 0.0, 0.0),
        attribution=float(row.get("attribution", 0.0)),
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
        capability_share=float(row.get("c_t_ba", 0.5)),
        b_econ=0.0, b_blood=0.0, v_i=0.0,
        closing_window=float(row.get("closing_window_b", 0.5)),
        fma=float(row.get("fma", 0.0)),
        cap_proxy=float(row.get("cap_b_to_a", 0.0)),
        shock_k=0.0,
        deesc_inputs=(0.0, 0.0, 0.0),
        attribution=0.0,
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
        state_attribution=InputState.DEFAULTED,
        state_stakes=InputState.DEFAULTED,
    )
    return sym, actor_a, actor_b


def _coverage_flags(row: pd.Series) -> dict:
    """Per-variable coverage state for the audit column."""
    flags = {}
    xi = row.get("contiguity_xi", 0.0)
    # Contiguity is empirical if we have a recorded value (including 0, which
    # means 'computed-not-contiguous'). The default would be 'we don't know',
    # which we don't currently emit (CShapes covers all live dyads).
    flags["cov_contiguity"] = "empirical" if pd.notna(xi) else "default"
    flags["cov_fma"] = "empirical" if pd.notna(row.get("fma")) else "default"
    cw = row.get("closing_window_a", 0.5)
    flags["cov_closing_window"] = "empirical" if pd.notna(cw) and cw != 0.5 else "default"
    flags["cov_rivalry"] = "empirical" if row.get("rivalry_omega", 0.0) > 0 else "default"
    flags["cov_cap"] = "empirical" if pd.notna(row.get("cap_a_to_b")) else "default"
    flags["cov_attribution"] = "empirical" if row.get("attribution", 0.0) > 0 else "default"
    flags["cov_d_k"] = "empirical" if row.get("d_k_years", 0.0) > 0 else "default"
    # Always defaulted
    flags["cov_a_div"] = "defaulted"   # no empirical source attached
    flags["cov_e_n"] = "defaulted"     # no empirical source attached
    flags["cov_s_p"] = "defaulted"     # no empirical source attached
    flags["cov_cost_field"] = "absent" # diagnostic fallback active
    return flags


def score_year(year: int, priors: Priors, out_path: str) -> pd.DataFrame:
    pq = os.path.join(DATA_PROCESSED, "dyads_with_features_v27.parquet")
    if not os.path.exists(pq):
        print(f"[ERR] missing {pq}; run build_features_v27.py first")
        sys.exit(1)
    df = pd.read_parquet(pq)
    df = df[df.year == year].copy()
    if df.empty:
        print(f"[ERR] no rows for year {year}")
        sys.exit(1)
    print(f"Year {year}: {len(df):,} live directed pairs")

    rows = []
    n = len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        sym, a, b = _build_states_from_row(row)
        res = score_dyad_year(a, b, sym, priors)
        flags = _coverage_flags(row)
        out_row = {
            "year": year,
            "initiator": row["initiator"],
            "target": row["target"],
            "current_tier": int(sym.current_tier),
            "P_T0": res["pi_reconciled"][0],
            "P_T1": res["pi_reconciled"][1],
            "P_T2": res["pi_reconciled"][2],
            "P_T3": res["pi_reconciled"][3],
            "P_T4": res["pi_reconciled"][4],
            "P_T5": res["pi_reconciled"][5],
            "P_any_esc": 1.0 - res["pi_reconciled"][0],
            "P_t4_plus": res["pi_reconciled"][4] + res["pi_reconciled"][5],
            "P_t5": res["pi_reconciled"][5],
            "contiguity_xi": row.get("contiguity_xi", 0.0),
            "rivalry_omega": row.get("rivalry_omega", 0.0),
            "cap_a_to_b": row.get("cap_a_to_b", 0.0),
            "cap_b_to_a": row.get("cap_b_to_a", 0.0),
            "closing_window_a": row.get("closing_window_a", 0.5),
            "d_k_years": row.get("d_k_years", 0.0),
            "attribution": row.get("attribution", 0.0),
            "gate_t5": bool(res["gate_t5"]),
            "active_member": res["member_ab"].value,
            **flags,
        }
        rows.append(out_row)
        if (i + 1) % 50_000 == 0:
            print(f"  {i+1:,} / {n:,}")

    out = pd.DataFrame(rows)
    out = out.sort_values("P_t5", ascending=False).reset_index(drop=True)
    out.to_csv(out_path, index=False)
    print(f"\nWrote {len(out):,} directed forecasts -> {out_path}")
    print()
    print("Top 20 by P(T5) — strategic-war risk:")
    cols = ["initiator", "target", "current_tier", "P_T5", "P_t4_plus",
            "P_any_esc", "contiguity_xi", "rivalry_omega", "cap_a_to_b",
            "gate_t5", "active_member"]
    print(out[cols].head(20).to_string(index=False))
    print()
    print("Top 20 by P(T4+) — limited-or-greater-war risk:")
    print(out.sort_values("P_t4_plus", ascending=False)[cols].head(20).to_string(index=False))
    print()
    print("Top 20 by P(any escalation):")
    cols2 = ["initiator", "target", "current_tier", "P_any_esc",
             "contiguity_xi", "rivalry_omega", "cap_a_to_b", "active_member"]
    print(out.sort_values("P_any_esc", ascending=False)[cols2].head(20).to_string(index=False))
    print()
    print("Coverage summary:")
    for k in ["cov_contiguity", "cov_fma", "cov_closing_window", "cov_rivalry",
              "cov_cap", "cov_attribution", "cov_d_k", "cov_cost_field"]:
        print(f"  {k}: {out[k].value_counts().to_dict()}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None,
                        help="Forecast year (default: latest available)")
    parser.add_argument("--out-dir", default=OUT_FORECASTS)
    args = parser.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    pq = os.path.join(DATA_PROCESSED, "dyads_with_features_v27.parquet")
    if args.year is None:
        # Find the latest year in the v27 grid
        df = pd.read_parquet(pq, columns=["year"])
        args.year = int(df["year"].max())
        print(f"Latest year in v27 grid: {args.year}")

    out_path = os.path.join(args.out_dir, f"forward_score_{args.year}.csv")
    priors = Priors()
    score_year(args.year, priors, out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
