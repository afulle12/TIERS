"""Build directed dyad-year events from the raw MID 5.0 participant file.

Every row this script writes can be traced to a participant record in
`MIDB 5.0.csv`. It replaces the inherited MID rows in `conflict_dyads.csv`,
whose initiator and target were reversed relative to MID's side A, and it
retires `build_t1_dyads.py` (proposal section 2.0.1).

Rules
-----
1. Pairing. Within a dispute, each side-A participant is paired with each
   side-B participant, for the years in which both participants' own start
   and end years overlap.
2. Direction. A row i -> j exists only when i itself took militarised action
   (`hostlev >= 2`). Its tier comes from i's own hostility level, never the
   other side's.
3. Tier map. Threat (2) and display of force (3) are T1, use of force (4) is
   T4, war (5) is T5. No MID row is T2.
4. Coalitions. The participant file says what i did in the dispute, not whom
   it did it to. When j shares its side with other states, a force-level tier
   (T4 or T5) for i -> j therefore needs evidence that the force was aimed
   at j:
     - where the incident file (MIDIP, disputes from 1992) covers the dispute,
       i must have used force in an incident with j on the opposite side; a
       pair that shares no incident at all is not emitted;
     - otherwise j must itself have used force in the dispute.
   Without that evidence the row is capped at T1: the two confronted each
   other but there is no record that they exchanged fire. When j is alone on
   its side there is no ambiguity and i keeps its own tier.
5. Roles are columns (`mid_side_a`, `mid_originator`), not encoded in direction.
6. Both states must be members of the state system in that year.
7. No tier resolution happens here: one row per dispute, year and direction.

Known limits
------------
- `hostlev` is a participant's peak across its whole spell, so a ten-year war
  is T5 in every year of the spell.
- Before 1992 the participant file cannot say which coalition members met.
- Side A is the first side to act militarily, which is not always the aggressor.

Output: data/processed/mid_dyad_events.csv
"""
from __future__ import annotations

import os
from typing import Optional

import pandas as pd

from state_system import load_state_system

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
MID_DIR = os.path.join(DATA_RAW, "MID-5-Data-and-Supporting-Materials")
MIDB_CSV = os.path.join(MID_DIR, "MIDB 5.0.csv")
MIDIP_CSV = os.path.join(MID_DIR, "MIDIP 5.0.csv")
OUT_CSV = os.path.join(DATA_PROCESSED, "mid_dyad_events.csv")

HOSTLEV_TO_TIER = {2: 1, 3: 1, 4: 4, 5: 5}
TIER_LABELS = {
    1: "T1-Diplomatic Crisis",
    4: "T4-Limited Military",
    5: "T5-Strategic War",
}
EVENT_COLUMNS = [
    "year", "initiator_ccode", "target_ccode", "uiw_tier", "tier_label",
    "hostlev", "target_hostlev", "dispnum", "mid_side_a", "mid_originator",
    "n_participants", "pairing_basis", "source",
]


def load_midb(path: str = MIDB_CSV) -> pd.DataFrame:
    cols = ["dispnum", "stabb", "ccode", "styear", "endyear", "sidea", "hostlev", "orig"]
    df = pd.read_csv(path, usecols=cols, encoding="latin-1")
    return df.astype({c: int for c in cols if c != "stabb"})


def load_incident_pairs(path: str = MIDIP_CSV) -> tuple[dict, set]:
    """Return `(pairs, covered_disputes)` from the incident-participant file.

    `pairs` maps `(dispnum, ccode_i, ccode_j)` to the highest hostility level i
    reached in any incident where j sat on the opposite side.
    """
    cols = ["dispnum", "incidnum", "ccode", "insidea", "hostlev"]
    ip = pd.read_csv(path, usecols=cols, encoding="latin-1").astype(int)
    merged = ip.merge(ip, on=["dispnum", "incidnum"], suffixes=("_i", "_j"))
    merged = merged[merged["insidea_i"] != merged["insidea_j"]]
    top = merged.groupby(["dispnum", "ccode_i", "ccode_j"])["hostlev_i"].max()
    return top.to_dict(), set(ip["dispnum"].unique())


def expand_dyad_events(
    midb: pd.DataFrame,
    incident_pairs: Optional[dict] = None,
    covered_disputes: Optional[set] = None,
) -> tuple[pd.DataFrame, dict]:
    """Expand participant spells into directed dispute-year events.

    Returns `(events, counts)`; `counts` records what the rules removed.
    """
    incident_pairs = incident_pairs or {}
    covered_disputes = covered_disputes or set()
    counts = {"no_action": 0, "no_shared_incident": 0, "coalition_capped": 0}
    rows = []
    for dispnum, grp in midb.groupby("dispnum", sort=True):
        parts = list(grp.itertuples(index=False))
        n_states = grp["ccode"].nunique()
        side_size = grp.groupby("sidea")["ccode"].nunique().to_dict()
        covered = dispnum in covered_disputes
        for a in parts:
            tier = HOSTLEV_TO_TIER.get(a.hostlev)
            for b in parts:
                if a.sidea == b.sidea or a.ccode == b.ccode:
                    continue
                y0, y1 = max(a.styear, b.styear), min(a.endyear, b.endyear)
                if y1 < y0:
                    continue
                if tier is None:
                    counts["no_action"] += y1 - y0 + 1
                    continue
                basis = "bilateral" if n_states == 2 else "sole-target"
                row_tier = tier
                if side_size.get(b.sidea, 1) > 1:
                    if covered:
                        level = incident_pairs.get((dispnum, a.ccode, b.ccode))
                        if level is None:
                            counts["no_shared_incident"] += y1 - y0 + 1
                            continue
                        basis = "incident"
                        aimed_at_target = level >= 4
                    else:
                        basis = "coalition"
                        aimed_at_target = b.hostlev >= 4
                    if tier >= 4 and not aimed_at_target:
                        row_tier = 1
                        counts["coalition_capped"] += y1 - y0 + 1
                for year in range(y0, y1 + 1):
                    rows.append((
                        year, a.ccode, b.ccode, row_tier, TIER_LABELS[row_tier],
                        a.hostlev, b.hostlev, dispnum, a.sidea, a.orig,
                        n_states, basis, "MID5",
                    ))
    events = pd.DataFrame(rows, columns=EVENT_COLUMNS)
    # A participant can have several spells in one dispute; keep the highest
    # tier per dispute, year and direction.
    events = (
        events.sort_values(["dispnum", "year", "initiator_ccode", "target_ccode", "uiw_tier"])
        .drop_duplicates(["dispnum", "year", "initiator_ccode", "target_ccode"], keep="last")
        .reset_index(drop=True)
    )
    return events, counts


def attach_states(events: pd.DataFrame, states: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Keep events between system members and add GW numbers and names."""
    key = states[["year", "ccode", "gwno", "name"]]
    out = events.merge(
        key.rename(columns={"ccode": "initiator_ccode", "gwno": "initiator_gwno", "name": "initiator"}),
        on=["year", "initiator_ccode"], how="left",
    ).merge(
        key.rename(columns={"ccode": "target_ccode", "gwno": "target_gwno", "name": "target"}),
        on=["year", "target_ccode"], how="left",
    )
    member = out["initiator_gwno"].notna() & out["target_gwno"].notna()
    n_dropped = int((~member).sum())
    out = out[member].copy()
    out["initiator_gwno"] = out["initiator_gwno"].astype(int)
    out["target_gwno"] = out["target_gwno"].astype(int)
    cols = ["year", "initiator", "target", "initiator_gwno", "target_gwno"] + EVENT_COLUMNS[1:]
    return out[cols].sort_values(["year", "initiator", "target", "dispnum"]).reset_index(drop=True), n_dropped


def build() -> tuple[pd.DataFrame, dict]:
    midb = load_midb()
    pairs, covered = load_incident_pairs()
    events, counts = expand_dyad_events(midb, pairs, covered)
    events, n_non_member = attach_states(events, load_state_system())
    counts["non_member"] = n_non_member
    return events, counts


def main() -> int:
    events, counts = build()
    events.to_csv(OUT_CSV, index=False)
    print(f"MID dyad events -> {OUT_CSV} ({len(events):,} rows, "
          f"{events.year.min()}-{events.year.max()})")
    print("  removed by rule (dyad-years):", counts)
    print("  rows by tier:", events["uiw_tier"].value_counts().sort_index().to_dict())
    print("  rows by pairing basis:", events["pairing_basis"].value_counts().to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
