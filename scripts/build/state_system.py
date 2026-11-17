"""State-system membership: which states exist in which year.

The dyad-year grid must contain only pairs of states that existed (proposal
section 2.2). Membership here is the Correlates of War state system, read from
the country-years present in NMC v7.0, restricted to states that also have a
territorial unit in CShapes 2.0 for that year. The CShapes restriction drops
the COW microstates (Andorra, Monaco, Nauru, ...), for which the pipeline has
no geography, which matches the usual Gleditsch-Ward practice.

Two code systems are carried on every row, because the sources disagree:

  ccode  Correlates of War code  -> NMC, MID, V-Dem `COWcode`, ATOP
  gwno   Gleditsch-Ward number   -> CShapes, UCDP, the contiguity, rivalry and
                                    trade tables

They are equal for almost every state. The exceptions are listed in
`COW_TO_GW_OVERRIDES` with the years they apply.

Outputs:
  data/processed/state_system.csv          year, ccode, gwno, name
  output/analysis/state_system_dropped.csv COW member-years with no CShapes unit
"""
from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd

from country_names import normalize_name

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
NMC_CSV = os.path.join(DATA_RAW, "NMC-70-abridged.csv")
CSHAPES_CSV = os.path.join(DATA_RAW, "CShapes-2.0.csv")
OUT_CSV = os.path.join(DATA_PROCESSED, "state_system.csv")
DROPPED_CSV = os.path.join(OUT_ANALYSIS, "state_system_dropped.csv")

YEAR_LO, YEAR_HI = 1900, 2014

# (cow ccode, first year, last year, gw number). COW gives the successor state
# a new or continuing code where Gleditsch-Ward does the opposite.
COW_TO_GW_OVERRIDES = [
    (255, 1990, 9999, 260),  # unified Germany: COW 255, GW keeps 260
    (679, 1990, 9999, 678),  # unified Yemen: COW 679, GW keeps 678
    (345, 2007, 9999, 340),  # Serbia after Montenegro's exit: COW keeps 345, GW 340
    (345, 0, 1917, 340),     # Serbia before Yugoslavia: COW 345, GW 340
]


def cow_to_gw(ccode: int, year: int) -> int:
    """Map a COW code to the Gleditsch-Ward number used by CShapes in `year`."""
    for cow, y0, y1, gw in COW_TO_GW_OVERRIDES:
        if ccode == cow and y0 <= year <= y1:
            return gw
    return int(ccode)


def _cshapes_units() -> pd.DataFrame:
    cs = pd.read_csv(CSHAPES_CSV, usecols=["cntry_name", "gwcode", "gwsyear", "gweyear"])
    cs = cs.dropna(subset=["gwcode"]).copy()
    cs["gwcode"] = cs["gwcode"].astype(int)
    return cs


def build_state_system(year_lo: int = YEAR_LO, year_hi: int = YEAR_HI) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return `(members, dropped)` for COW member-years in the window."""
    nmc = pd.read_csv(NMC_CSV, usecols=["stateabb", "ccode", "year"])
    nmc = nmc[(nmc.year >= year_lo) & (nmc.year <= year_hi)].copy()
    nmc["ccode"] = nmc["ccode"].astype(int)
    nmc["year"] = nmc["year"].astype(int)
    nmc["gwno"] = [cow_to_gw(c, y) for c, y in zip(nmc["ccode"], nmc["year"], strict=True)]

    cs = _cshapes_units()
    span = cs.groupby("gwcode").agg(gw_start=("gwsyear", "min"), gw_end=("gweyear", "max"))
    latest_name = (
        cs.sort_values("gwsyear", ascending=False)
        .drop_duplicates("gwcode")
        .set_index("gwcode")["cntry_name"]
        .map(normalize_name)
    )
    nmc = nmc.merge(span, left_on="gwno", right_index=True, how="left")
    has_unit = nmc["gw_start"].notna() & (nmc["year"] >= nmc["gw_start"]) & (nmc["year"] <= nmc["gw_end"])

    dropped = nmc.loc[~has_unit, ["year", "ccode", "stateabb", "gwno"]].copy()
    members = nmc.loc[has_unit, ["year", "ccode", "stateabb", "gwno"]].copy()
    members["name"] = members["gwno"].map(latest_name)

    # Two COW codes can map to one GW number in a hand-over year (1990: German
    # Federal Republic and unified Germany; Yemen Arab Republic and Yemen).
    # Keep the successor, which is the one reached through an override.
    members["via_override"] = members["ccode"] != members["gwno"]
    members = (
        members.sort_values(["year", "gwno", "via_override"])
        .drop_duplicates(["year", "gwno"], keep="last")
        .drop(columns="via_override")
        .sort_values(["year", "ccode"])
        .reset_index(drop=True)
    )
    if members.duplicated(["year", "ccode"]).any() or members.duplicated(["year", "name"]).any():
        raise ValueError("state_system: a state appears twice in one year")
    return members, dropped


@lru_cache(maxsize=1)
def load_state_system() -> pd.DataFrame:
    """Load `state_system.csv`, building it first if it is missing."""
    if not os.path.exists(OUT_CSV):
        main()
    return pd.read_csv(OUT_CSV)


def main() -> int:
    members, dropped = build_state_system()
    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    members.to_csv(OUT_CSV, index=False)
    dropped.to_csv(DROPPED_CSV, index=False)
    per_year = members.groupby("year").size()
    print(f"State system {YEAR_LO}-{YEAR_HI}: {len(members):,} member-years, "
          f"{members.ccode.nunique()} states -> {OUT_CSV}")
    print(f"  members in 1946: {per_year.get(1946, 0)}, 1990: {per_year.get(1990, 0)}, "
          f"2014: {per_year.get(2014, 0)}")
    print(f"  dropped (no CShapes unit): {len(dropped):,} member-years, "
          f"{dropped.stateabb.nunique()} states: {sorted(dropped.stateabb.unique())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
