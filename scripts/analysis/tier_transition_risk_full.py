"""Transition analysis on conflict_dyads_full.csv (T0-T5).

For each directed dyad, walk year-by-year. Each year has exactly one
observation (T0 if no conflict, else the observed tier, collapsed via
max for the rare dual-coded years). A transition is recorded for every
consecutive year pair. Escalation = tier_n+1 > tier_n, de-escalation =
tier_n+1 < tier_n.
"""
from __future__ import annotations

import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "data", "processed", "conflict_dyads_full.csv")
OUT_MATRIX = os.path.join(ROOT, "output", "analysis", "tier_transition_matrix_full.csv")
OUT_RISK = os.path.join(ROOT, "output", "analysis", "tier_risk_summary_full.csv")
OUT_DECADE = os.path.join(ROOT, "output", "analysis", "tier_risk_by_decade.csv")

TIER_ORDER = [
    "T0-No Conflict/Peace",
    "T1-Diplomatic Crisis",
    "T2-Economic/Display",
    "T3-Proxy/Indirect Military",
    "T4-Limited Military",
    "T5-Strategic War",
]
TIER_CODE = {t: i for i, t in enumerate(TIER_ORDER)}


def main() -> int:
    df = pd.read_csv(SRC, dtype={"year": int}, usecols=["year", "initiator", "target", "uiw_tier"])
    print(f"Loaded {len(df):,} rows")

    dyad_year = (
        df.groupby(["initiator", "target", "year"])["uiw_tier"]
        .max()
        .reset_index()
        .sort_values(["initiator", "target", "year"])
    )
    print(f"Distinct (dyad, year) observations: {len(dyad_year):,}")

    rows = []
    for (init, tgt), g in dyad_year.groupby(["initiator", "target"], sort=False):
        g = g.sort_values("year")
        years = g["year"].to_numpy()
        tiers = g["uiw_tier"].to_numpy()
        for i in range(len(years) - 1):
            rows.append(
                (
                    init,
                    tgt,
                    int(years[i]),
                    int(years[i + 1]),
                    int(tiers[i]),
                    int(tiers[i + 1]),
                    int(tiers[i + 1]) - int(tiers[i]),
                )
            )

    tr = pd.DataFrame(rows, columns=["initiator", "target", "y_from", "y_to", "t_from", "t_to", "delta"])
    print(f"Year-over-year transitions: {len(tr):,}")
    tr.to_csv(os.path.join(ROOT, "output", "analysis", "tier_transitions_full.csv"), index=False)

    matrix = pd.crosstab(tr["t_from"], tr["t_to"]).reindex(
        index=range(6), columns=range(6), fill_value=0
    )
    matrix.index = [f"T{i} ({TIER_ORDER[i].split('-', 1)[1]})" for i in matrix.index]
    matrix.columns = [f"T{i}" for i in matrix.columns]
    matrix.to_csv(OUT_MATRIX)
    print("\nTransition count matrix (from -> to):")
    print(matrix)

    prob = matrix.div(matrix.sum(axis=1), axis=0).fillna(0).round(4)
    print("\nTransition probability matrix (row-normalised):")
    print(prob)

    summary_rows = []
    for t in range(6):
        sub = tr[tr["t_from"] == t]
        n = len(sub)
        if n == 0:
            summary_rows.append(
                {
                    "tier_from": TIER_ORDER[t],
                    "n_transitions": 0,
                    "p_escalate": float("nan"),
                    "p_stable": float("nan"),
                    "p_deescalate": float("nan"),
                    "mean_delta": float("nan"),
                    "p_reach_T5_next_year": float("nan"),
                }
            )
            continue
        n_esc = int((sub.delta > 0).sum())
        n_stab = int((sub.delta == 0).sum())
        n_de = int((sub.delta < 0).sum())
        reach_t5 = int((sub.t_to == 5).sum())
        summary_rows.append(
            {
                "tier_from": TIER_ORDER[t],
                "n_transitions": n,
                "p_escalate": n_esc / n,
                "p_stable": n_stab / n,
                "p_deescalate": n_de / n,
                "mean_delta": float(sub.delta.mean()),
                "p_reach_T5_next_year": reach_t5 / n,
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_RISK, index=False)
    print("\nRisk summary by source tier (year-over-year):")
    print(summary.to_string(index=False))

    tr["decade"] = (tr["y_from"] // 10) * 10
    dec_rows = []
    for dec, sub in tr.groupby("decade"):
        for t in range(6):
            s2 = sub[sub["t_from"] == t]
            n = len(s2)
            if n == 0:
                continue
            dec_rows.append(
                {
                    "decade": int(dec),
                    "tier_from": TIER_ORDER[t],
                    "n_transitions": n,
                    "p_escalate": float((s2.delta > 0).mean()),
                    "p_stable": float((s2.delta == 0).mean()),
                    "p_deescalate": float((s2.delta < 0).mean()),
                }
            )
    dec_df = pd.DataFrame(dec_rows)
    dec_df.to_csv(OUT_DECADE, index=False)
    print(f"\nWrote per-decade risk to {OUT_DECADE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
