"""Transition analysis: escalation vs de-escalation risk from each tier.

For each directed dyad (initiator, target), track the sequence of observed
tiers across years. When a dyad is observed in year Y at tier T and then
observed again in a later year Y' at tier T', the (T -> T') pair is a
transition. Escalation means T' > T, de-escalation means T' < T.

For dyad-years with multiple tier observations (dual-coded), we collapse
to the maximum tier observed that year (most severe reading).
"""
from __future__ import annotations

import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH = os.path.join(ROOT, "data", "processed", "conflict_dyads.csv")
OUT_CSV = os.path.join(ROOT, "output", "analysis", "tier_transition_matrix.csv")
OUT_RISK = os.path.join(ROOT, "output", "analysis", "tier_risk_summary.csv")

TIER_ORDER = [
    "T1-Diplomatic Crisis",
    "T2-Economic/Display",
    "T3-Proxy/Indirect Military",
    "T4-Limited Military",
    "T5-Strategic War",
]
TIER_IDX = {t: i + 1 for i, t in enumerate(TIER_ORDER)}


def main() -> int:
    df = pd.read_csv(CSV_PATH, dtype={"year": int})
    print(f"Loaded {len(df)} rows")

    dyad_year = (
        df.groupby(["initiator", "target", "year"])["uiw_tier"]
        .max()
        .reset_index()
        .sort_values(["initiator", "target", "year"])
    )
    print(f"Distinct (dyad, year) observations: {len(dyad_year)}")

    rows = []
    for (init, tgt), g in dyad_year.groupby(["initiator", "target"], sort=False):
        g = g.sort_values("year")
        years = g["year"].tolist()
        tiers = g["uiw_tier"].tolist()
        labels = g["tier_label"].tolist() if "tier_label" in g.columns else [None] * len(tiers)
        for i in range(1, len(years)):
            dy = years[i] - years[i - 1]
            t0, t1 = tiers[i - 1], tiers[i]
            lab0, lab1 = labels[i - 1], labels[i]
            rows.append(
                {
                    "initiator": init,
                    "target": tgt,
                    "year_from": years[i - 1],
                    "year_to": years[i],
                    "years_between": dy,
                    "tier_from": t0,
                    "tier_to": t1,
                    "tier_label_from": lab0,
                    "tier_label_to": lab1,
                    "delta": t1 - t0,
                }
            )

    tr = pd.DataFrame(rows)
    tr.to_csv(os.path.join(ROOT, "output", "analysis", "tier_transitions.csv"), index=False)
    print(f"Transitions: {len(tr)}")

    matrix = pd.crosstab(tr["tier_from"], tr["tier_to"]).reindex(
        index=range(1, 6), columns=range(1, 6), fill_value=0
    )
    matrix.index = [f"T{t} ({TIER_ORDER[t-1].split('-', 1)[1]})" for t in matrix.index]
    matrix.columns = [f"T{t}" for t in matrix.columns]
    matrix.to_csv(OUT_CSV)
    print("\nTransition count matrix (from -> to):")
    print(matrix)

    print("\nTransition probability matrix (row-normalised, from -> to):")
    prob = matrix.div(matrix.sum(axis=1), axis=0).fillna(0).round(4)
    print(prob)

    summary_rows = []
    for t in range(1, 6):
        sub = tr[tr["tier_from"] == t]
        n = len(sub)
        if n == 0:
            summary_rows.append(
                {
                    "tier_from": f"T{t} ({TIER_ORDER[t-1].split('-', 1)[1]})",
                    "n_transitions": 0,
                    "p_escalate": float("nan"),
                    "p_stable": float("nan"),
                    "p_deescalate": float("nan"),
                    "mean_delta": float("nan"),
                    "p_reach_T5_within_observations": float("nan"),
                }
            )
            continue
        n_esc = int((sub.delta > 0).sum())
        n_stab = int((sub.delta == 0).sum())
        n_de = int((sub.delta < 0).sum())
        reach_t5 = int((sub.tier_to == 5).sum())
        summary_rows.append(
            {
                "tier_from": f"T{t} ({TIER_ORDER[t-1].split('-', 1)[1]})",
                "n_transitions": n,
                "p_escalate": n_esc / n,
                "p_stable": n_stab / n,
                "p_deescalate": n_de / n,
                "mean_delta": float(sub.delta.mean()),
                "p_reach_T5_within_observations": reach_t5 / n,
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_RISK, index=False)
    print("\nRisk summary by source tier:")
    print(summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
