"""Which tiers can be observed in which years (proposal section 2.5).

Each tier is read from a different dataset with its own coverage period. A
dyad-year outside a tier's coverage is *unknown* for that tier, not at peace.
The clearest case is T2: sanctions come only from EUSANCT, which starts in
1989, so before 1989 a dyad recorded at T0 or T1 may in fact have been under
sanctions.

`SOURCES` is the single declaration. Everything else is derived from it:

  data/processed/source_coverage.csv   year, tier, observed, sources, note

The evaluation module reads that file and refuses to score a transition whose
outcome label could change if an unobserved tier were filled in (see
`evaluation.label_decidable`).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_CSV = os.path.join(DATA_PROCESSED, "source_coverage.csv")

YEAR_LO, YEAR_HI = 1946, 2014


@dataclass(frozen=True)
class Source:
    name: str          # the value written to the `source` column of dyad_events.csv
    tiers: tuple       # tiers this source can place a dyad at
    first_year: int
    last_year: int
    records: str       # what the source actually records
    in_build: bool = True   # False: named in the proposal, not yet wired in


SOURCES = (
    Source("MID5", (1, 4, 5), 1816, 2014,
           "militarised threats and displays (T1), uses of force (T4), war (T5)"),
    Source("UCDP_INTERSTATE", (4,), 1946, 2025,
           "interstate armed conflict with at least 25 battle deaths in the year"),
    Source("UCDP_T3", (3,), 1946, 2025,
           "troop support to a party in an internationalised internal conflict; "
           "covert or material support is not recorded"),
    Source("EUSANCT", (2,), 1989, 2015,
           "imposed sanctions by the United States and the European Union only"),
    # Section 2.8 T1 sources (integrated via build_t1_sources.py).
    Source("EUSANCT_THREAT", (1,), 1989, 2015, "threatened sanctions not imposed in the year", in_build=True),
    Source("ICB", (1,), 1918, 2022, "international crises below T3", in_build=True),
    Source("TIES", (1,), 1945, 2005, "sanction threats not imposed in the year", in_build=True),
    Source("DIPREP", (1,), 1960, 2025, "missions withdrawn, recalled, severed, or expelled", in_build=True),
)

# A tier whose only sources record part of its definition. It is treated as
# observed (there is a source for every year) but the gap is stated wherever
# the table is printed.
PARTIAL_NOTES = {
    1: "militarised and sanction threats, non-violent crises, and recalls/expulsions; ordinary protests are not recorded",
    2: "United States and European Union senders only",
    3: "troop support only; covert and material support is not recorded",
}


def sources_for(tier: int, year: int, built_only: bool = True) -> list[str]:
    return [
        s.name for s in SOURCES
        if tier in s.tiers and s.first_year <= year <= s.last_year and (s.in_build or not built_only)
    ]


def tier_observed(tier: int, year: int) -> bool:
    """True when at least one source in the build can place a dyad at `tier` in `year`."""
    if tier == 0:
        return True
    return bool(sources_for(tier, year))


def unobserved_bitmask(year: int) -> int:
    """Bit `u` is set when tier `u` cannot be observed in `year`."""
    return sum(1 << t for t in range(1, 6) if not tier_observed(t, year))


def coverage_table(year_lo: int = YEAR_LO, year_hi: int = YEAR_HI) -> pd.DataFrame:
    rows = []
    for year in range(year_lo, year_hi + 1):
        for tier in range(1, 6):
            rows.append({
                "year": year,
                "tier": tier,
                "observed": tier_observed(tier, year),
                "sources": "+".join(sources_for(tier, year)),
                "note": PARTIAL_NOTES.get(tier, ""),
            })
    return pd.DataFrame(rows)


def coverage_spans(year_lo: int = YEAR_LO, year_hi: int = YEAR_HI) -> pd.DataFrame:
    """One row per tier and run of years with the same sources (for the docs)."""
    tab = coverage_table(year_lo, year_hi)
    rows = []
    for tier, grp in tab.groupby("tier"):
        grp = grp.sort_values("year")
        run = (grp["sources"] != grp["sources"].shift()).cumsum()
        for _, g in grp.groupby(run):
            rows.append({
                "tier": int(tier),
                "first_year": int(g["year"].min()),
                "last_year": int(g["year"].max()),
                "observed": bool(g["observed"].iloc[0]),
                "sources": g["sources"].iloc[0] or "none",
                "note": g["note"].iloc[0],
            })
    return pd.DataFrame(rows)


def main() -> int:
    tab = coverage_table()
    tab.to_csv(OUT_CSV, index=False)
    print(f"Source coverage -> {OUT_CSV} ({len(tab):,} tier-years)")
    print(coverage_spans().to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
