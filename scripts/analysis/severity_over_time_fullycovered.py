"""Severity-over-time chart: count of unique (initiator, target) dyads per year,
classified at their MAX tier reached (T1-T5, T0 excluded).

Years are restricted to where all source datasets (MIDB, EUSANCT, UCDP,
CShapes) are simultaneously active (1946-2014, the FULLY_COVERED_YEARS
defined in scripts/analysis/v26_tier_following_filtered.py). This removes
the two main skews in the original chart:
  - pre-1946: no T3 (UCDP did not exist)
  - post-2014: only T3 is recorded (MIDB has ended)

Metric: for each (year, initiator, target), collapse multiple events down
to the dyad's MAXIMUM tier that year. E.g. if US->Iran had a T2 sanction
and a T4 military engagement in 2014, it counts as 1 T4 dyad for 2014, not
1 T2 + 1 T4. This makes the chart robust against a single sender doing
many things with the same target (T2 sanctions piling on a T4 conflict
are absorbed into the T4 bar). The total height of the stack is the count
of unique conflict-touching dyads that year.

Series are NORMALIZED by the number of directed dyads possible per year
(n_countries * (n_countries - 1)) from
data/processed/countries_by_year.csv (CShapes). Y-axis: unique max-tier
dyad-years per 10,000 directed dyads possible.

Inputs : data/processed/conflict_dyads_combined.csv  (MIDB + EUSANCT T2 + UCDP T3)
         data/processed/countries_by_year.csv       (CShapes -> year -> [countries])
Output : output/charts/severity_over_time_fullycovered.png
         output/analysis/yearly_counts_fullycovered.csv
         output/analysis/dyad_year_tiers_fullycovered.csv  (per-dyad-year detail)
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_PATH = os.path.join(ROOT, "data", "processed", "conflict_dyads_combined.csv")
COUNTRIES_PATH = os.path.join(ROOT, "data", "processed", "countries_by_year.csv")
CHARTS = os.path.join(ROOT, "output", "charts")
ANALYSIS = os.path.join(ROOT, "output", "analysis")
PER = 10_000  # events per 10,000 directed dyads

TIER_ORDER = [
    "T1-Diplomatic Crisis",
    "T2-Economic/Display",
    "T3-Proxy/Indirect Military",
    "T4-Limited Military",
    "T5-Strategic War",
]
TIER_SHORT = {t: t.split("-")[0] for t in TIER_ORDER}

LO, HI = 1946, 2014


def main() -> int:
    os.makedirs(CHARTS, exist_ok=True)
    os.makedirs(ANALYSIS, exist_ok=True)

    df = pd.read_csv(CSV_PATH, usecols=["year", "initiator", "target", "tier_label", "source"], dtype={"year": int})
    print(f"Loaded {len(df):,} rows from conflict_dyads_combined.csv")

    df = df[(df.year >= LO) & (df.year <= HI)]
    print(f"Restricted to fully-covered years {LO}-{HI}: {len(df):,} rows")

    # Collapse each (year, initiator, target) to its MAXIMUM tier reached that
    # year. A T2 sanction and a T4 military event between the same pair in
    # the same year become a single T4 dyad-year (T4 absorbs T2).
    n_raw = len(df)
    df = df.drop_duplicates(subset=["year", "initiator", "target", "tier_label"])
    print(f"After de-duplicating (year, initiator, target, tier_label): {len(df):,} "
          f"(dropped {n_raw - len(df):,})")
    df["tier_code"] = df["tier_label"].map({t: int(t.split("-")[0][1:]) for t in TIER_ORDER})

    # Per-dyad-year detail table: every unique (year, initiator, target) that
    # touches the dataset in the fully-covered window, with its max tier and a
    # breakdown of which tiers and sources contributed. Useful for manual QA.
    TIER_CODE_TO_LABEL = {1: "T1-Diplomatic Crisis", 2: "T2-Economic/Display",
                          3: "T3-Proxy/Indirect Military", 4: "T4-Limited Military",
                          5: "T5-Strategic War"}
    TIER_CODE_TO_SHORT = {c: TIER_SHORT[TIER_CODE_TO_LABEL[c]] for c in (1, 2, 3, 4, 5)}

    agg = df.groupby(["year", "initiator", "target"]).agg(
        n_events=("tier_code", "size"),
        max_tier=("tier_code", "max"),
        tiers=("tier_code", lambda s: ",".join(sorted({TIER_CODE_TO_SHORT[c] for c in s}))),
        sources=("source", lambda s: ",".join(sorted(set(s)))),
    ).reset_index()
    agg["max_tier_label"] = agg["max_tier"].map(TIER_CODE_TO_LABEL)
    agg = agg[["year", "initiator", "target", "max_tier", "max_tier_label",
               "n_events", "tiers", "sources"]]
    agg = agg.sort_values(["year", "initiator", "target"]).reset_index(drop=True)

    out_dyads = os.path.join(ANALYSIS, "dyad_year_tiers_fullycovered.csv")
    agg.to_csv(out_dyads, index=False)
    print(f"Wrote per-dyad-year detail -> {out_dyads} ({len(agg):,} rows)")

    max_tier = agg[["year", "initiator", "target", "max_tier"]]
    print(f"Unique (year, initiator, target) dyad-years after taking max tier: {len(max_tier):,}")

    yearly = (
        max_tier.groupby(["year", "max_tier"]).size().unstack(fill_value=0)
        .reindex(columns=[1, 2, 3, 4, 5], fill_value=0)
        .sort_index()
    )
    yearly.columns = [f"T{c}-..." for c in yearly.columns]
    rename = {1: "T1-Diplomatic Crisis", 2: "T2-Economic/Display",
              3: "T3-Proxy/Indirect Military", 4: "T4-Limited Military",
              5: "T5-Strategic War"}
    yearly = yearly.rename(columns={f"T{c}-...": rename[c] for c in (1, 2, 3, 4, 5)})
    for t in TIER_ORDER:
        if t not in yearly.columns:
            yearly[t] = 0
    yearly["total"] = yearly[TIER_ORDER].sum(axis=1)
    yearly["T4_T5_share"] = (
        yearly["T4-Limited Military"] + yearly["T5-Strategic War"]
    ) / yearly["total"].replace(0, pd.NA)

    # System size: directed dyads possible per year from CShapes country list.
    cy = pd.read_csv(COUNTRIES_PATH)
    cy["n_countries"] = cy["countries"].str.split(";").str.len()
    cy = cy[(cy.year >= LO) & (cy.year <= HI)].set_index("year")
    dyads_possible = (cy["n_countries"] * (cy["n_countries"] - 1)).rename("dyads_possible")
    yearly = yearly.join(dyads_possible, how="left")
    print(f"System size: {yearly['dyads_possible'].min():,} - {yearly['dyads_possible'].max():,} "
          f"directed dyads possible per year ({cy['n_countries'].min()}-{cy['n_countries'].max()} countries)")

    # Normalize: max-tier dyad-years per 10,000 directed dyads possible.
    rate_cols = [f"{t}_rate" for t in TIER_ORDER]
    for t, rc in zip(TIER_ORDER, rate_cols):
        yearly[rc] = yearly[t] / yearly["dyads_possible"] * PER
    yearly["total_rate"] = yearly["total"] / yearly["dyads_possible"] * PER
    yearly["T4_T5_share_rate"] = (
        yearly["T4-Limited Military_rate"] + yearly["T5-Strategic War_rate"]
    ) / yearly["total_rate"].replace(0, pd.NA)

    out_csv = os.path.join(ANALYSIS, "yearly_counts_fullycovered.csv")
    yearly.to_csv(out_csv)
    print(f"Wrote {out_csv}")

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.stackplot(
        yearly.index,
        [yearly[rc] for rc in rate_cols],
        labels=[TIER_SHORT[t] for t in TIER_ORDER],
        alpha=0.85,
    )
    ax.set_title(
        f"Conflict-touching dyads per year, classified at their MAX tier\n"
        f"Fully-covered years only ({LO}-{HI}: MIDB, EUSANCT, UCDP, CShapes all active)\n"
        f"Normalized: max-tier dyad-years per {PER:,} directed dyads possible (CShapes system size)"
    )
    ax.set_xlabel("Year")
    ax.set_ylabel(f"Max-tier dyad-years per {PER:,} directed dyads possible")
    ax.legend(loc="upper left", ncol=4, fontsize=9)
    ax.set_xlim(LO, HI)
    ax.grid(True, axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()

    out_png = os.path.join(CHARTS, "severity_over_time_fullycovered.png")
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    print(f"Wrote {out_png}")

    print(f"\nSummary (year : max-tier dyad-years per {PER:,} dyads possible):")
    print(yearly["total_rate"].round(2).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
