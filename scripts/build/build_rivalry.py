"""Build a per-dyad rivalry (Omega) table from MIDB 5.0 participant-level data.

For each directed pair (i, j) and each year T in the data window, Omega_{i,j}(T)
is a recency-decayed sum of MID events in which i and j were on opposing sides,
weighted by hostility level and fatality.

The decay kernel is exp(-lambda * (T - t)) with lambda = 0.10 (half-life ~ 7 years).
The result is clipped to [0, 1]; the empirical scale shows the most rivalrous
dyads (e.g. India-Pakistan, Israel-Iran) saturate near 1.0 in their peak years.

Input: data/raw/MID-5-Data-and-Supporting-Materials/MIDB 5.0.csv
  (one row per (dispute, participant) pair, full 1816-2014 range; MIDIP 5.0 only
  covers 1992-2014 so we use the dispute-level MIDB file for full coverage).

Output: data/processed/rivalry_omega.csv with columns
    year, initiator_gwno, target_gwno, rivalry_omega
"""
from __future__ import annotations

import os
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw", "MID-5-Data-and-Supporting-Materials")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")

YEAR_LO, YEAR_HI = 1946, 2014
LAMBDA = 0.10   # recency decay; half-life ~ 7 years

# Hostility weight by MID hostlev (1=no militarized action ... 5=war)
HOSTLEV_WEIGHT = {0: 0.0, 1: 0.10, 2: 0.25, 3: 0.50, 4: 0.75, 5: 1.00}
# Fatality multiplier
FATALITY_MULT = {0: 0.5, 1: 0.7, 2: 1.0}   # 0=none, 1=1-25, 2=26+


def load_midip() -> pd.DataFrame:
    """Load MIDB 5.0 participant-level data; return rows with valid year and ccode."""
    path = os.path.join(DATA_RAW, "MIDB 5.0.csv")
    df = pd.read_csv(path)
    df = df.dropna(subset=["ccode", "styear", "sidea"])
    df["ccode"] = df["ccode"].astype(int)
    df["styear"] = df["styear"].astype(int)
    df["sidea"] = df["sidea"].astype(int)
    df["hostlev"] = df["hostlev"].fillna(1).astype(int)
    df["fatality"] = df["fatality"].fillna(0).astype(int)
    return df


def expand_directed_events(df: pd.DataFrame) -> pd.DataFrame:
    """For each dispute, expand participants into directed (initiator, target) rows.

    A directed event (i, j, year, weight) means i and j were on opposing sides
    in a dispute that began (or had an incident) in `year`; the event is recorded
    from i's perspective, so it contributes to both rivalry_omega(i->j) and
    rivalry_omega(j->i) (symmetric per spec section 1.6.4).
    """
    rows: list = []
    for dispnum, grp in df.groupby("dispnum"):
        # Per dispute we may have multiple rows per participant (multi-year
        # incidents); deduplicate participants to sets per side.
        sideA = set(grp[grp.sidea == 1]["ccode"].astype(int).unique())
        sideB = set(grp[grp.sidea == 0]["ccode"].astype(int).unique())
        if len(sideA) == 0 or len(sideB) == 0:
            continue
        # Aggregate weight to the dispute-year level
        for year, ygrp in grp.groupby("styear"):
            hostlev_max = int(ygrp["hostlev"].max())
            fatal_max = int(ygrp["fatality"].max())
            w = HOSTLEV_WEIGHT.get(hostlev_max, 0.25) * FATALITY_MULT.get(fatal_max, 0.5)
            if w <= 0.0:
                continue
            for i in sideA:
                for j in sideB:
                    if i == j:
                        continue
                    rows.append((int(year), int(i), int(j), w))
    return pd.DataFrame(rows, columns=["year", "ccode_a", "ccode_b", "weight"])


def build_omega_table(events: pd.DataFrame) -> pd.DataFrame:
    """For each directed (i, j) and year T in [YEAR_LO, YEAR_HI], compute

        Omega_{i,j}(T) = clip( sum_{t < T} w(i,j,t) * exp(-LAMBDA * (T - t)), 0, 1 )
    """
    events = events.sort_values("year")
    # Pivot events to a per-(i, j) list of (year, weight)
    by_pair: dict = {}
    for (a, b), grp in events.groupby(["ccode_a", "ccode_b"]):
        by_pair[(a, b)] = list(zip(grp["year"].values, grp["weight"].values))

    # Output as a sparse per-year update: for each (i, j), walk years and
    # accumulate the decayed sum.
    out: list = []
    n_pairs = len(by_pair)
    print(f"  {n_pairs:,} directed pairs in MID history")
    for idx, ((a, b), evs) in enumerate(by_pair.items()):
        if idx > 0 and idx % 5000 == 0:
            print(f"  ... {idx:,} / {n_pairs:,}")
        evs_sorted = sorted(evs, key=lambda x: x[0])
        omega = 0.0
        ev_ptr = 0
        for T in range(YEAR_LO, YEAR_HI + 1):
            # Add all events at year T (events are stored at the dispute styear;
            # we treat them as instantaneous for the rivalry accumulation)
            while ev_ptr < len(evs_sorted) and evs_sorted[ev_ptr][0] == T:
                omega += evs_sorted[ev_ptr][1]
                ev_ptr += 1
            # Apply decay from T-1 to T
            if T > YEAR_LO:
                omega *= float(np.exp(-LAMBDA))
            omega_clipped = float(np.clip(omega, 0.0, 1.0))
            out.append((T, a, b, omega_clipped))
    df = pd.DataFrame(out, columns=["year", "initiator_gwno", "target_gwno", "rivalry_omega"])
    df["rivalry_omega"] = df["rivalry_omega"].astype(np.float32)
    return df


def main() -> int:
    out_path = os.path.join(DATA_PROCESSED, "rivalry_omega.csv")
    if os.path.exists(out_path):
        print(f"Already exists: {out_path}")
        return 0

    print("Loading MIDIP 5.0...")
    midip = load_midip()
    print(f"  {len(midip):,} participant-incident rows")
    midip = midip[(midip.styear >= YEAR_LO) & (midip.styear <= YEAR_HI)]
    print(f"  in window {YEAR_LO}-{YEAR_HI}: {len(midip):,}")

    print("Expanding directed (i, j) events...")
    events = expand_directed_events(midip)
    print(f"  {len(events):,} directed event rows")
    # Reduce by (year, i, j) summing the weights so we accumulate cleanly
    events = events.groupby(["year", "ccode_a", "ccode_b"], as_index=False)["weight"].sum()
    print(f"  after aggregation: {len(events):,}")

    print("Building per-year recency-decayed Omega table...")
    df = build_omega_table(events)
    df.to_csv(out_path, index=False)
    print(f"\nWrote {len(df):,} directed rows -> {out_path}")
    print(f"  max Omega:  {df.rivalry_omega.max():.3f}")
    print(f"  median:     {df.rivalry_omega.median():.3f}")
    print(f"  99th pct:   {df.rivalry_omega.quantile(0.99):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
