"""Build T1 directed-dyad rows from MIDB 5.0 + MIDIP 5.0.

Derives T1 (Diplomatic Crisis) events from two sources:
  A. MIDB 5.0 participant-level data (hostlev column)
  B. MIDIP 5.0 incident-level data (action column)

MIDB yields up to 233 raw rows (hostlev=2) over 1816-2010; MIDIP adds
incident-level granularity so that participants who threatened (action 1-6)
in one incident but escalated in another also get a T1 record.

Three T1 widths:
  narrow  : hostlev=2 only (exactly mirrors current 46 rows)
  standard: hostlev=2 + hostlev=1 participants on originator's side
  broad   : hostlev=2 + ALL hostlev=1 participants whose side had any
            hostlev>=2 participant (pure diplomatic involvement)

Outputs:
  data/raw/T1_directed_v5_{width}.csv — one per width
  output/analysis/t1_definition_table.csv — action/hostlev → description → decision
  output/analysis/t1_non_state_dropped.csv — dropped non-state participants
"""
from __future__ import annotations

import csv
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw")
MIDB_DIR = os.path.join(DATA_RAW, "MID-5-Data-and-Supporting-Materials")
MIDB_CSV = os.path.join(MIDB_DIR, "MIDB 5.0.csv")
MIDA_CSV = os.path.join(MIDB_DIR, "MIDA 5.0.csv")
MIDIP_CSV = os.path.join(MIDB_DIR, "MIDIP 5.0.csv")
MIDI_CSV = os.path.join(MIDB_DIR, "MIDI 5.0.csv")
CSHAPES_CSV = os.path.join(DATA_RAW, "CShapes-2.0.csv")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")

# MIDB codebook action -> tier mapping (for documentation)
ACTION_TIER = {
    0:  (1, "T1", "No militarized action"),
    1:  (2, "T1", "Threat to use force"),
    2:  (2, "T1", "Threat to blockade"),
    3:  (2, "T1", "Threat to occupy territory"),
    4:  (2, "T1", "Threat to declare war"),
    5:  (2, "T1", "Threat to use CBR weapons"),
    6:  (2, "T1", "Threat to join war"),
    7:  (3, "T2", "Show of force"),
    8:  (3, "T2", "Alert"),
    9:  (3, "T2", "Nuclear alert"),
    10: (3, "T2", "Mobilization"),
    11: (3, "T2", "Fortify border"),
    12: (3, "T2", "Border violation"),
    13: (4, "T4", "Blockade"),
    14: (4, "T4", "Occupation of territory"),
    15: (4, "T4", "Seizure"),
    16: (4, "T4", "Attack"),
    17: (4, "T4", "Clash"),
    18: (4, "T4", "Declaration of war"),
    19: (4, "T4", "Use of CBR weapons"),
    20: (5, "T5", "Begin interstate war"),
    21: (5, "T5", "Join interstate war"),
}

T1_ACTION_CODES = {1, 2, 3, 4, 5, 6}  # threats = hostlev 2


def load_cshapes() -> tuple[dict, dict]:
    cs = pd.read_csv(CSHAPES_CSV)
    cs = cs.dropna(subset=["gwcode"]).copy()
    cs["gwcode"] = cs["gwcode"].astype(int)
    latest = (
        cs.sort_values("gwsyear", ascending=False)
        .drop_duplicates("gwcode")
        .set_index("gwcode")["cntry_name"]
        .to_dict()
    )
    gw_to_name = {int(gw): name for gw, name in latest.items()}
    return latest, gw_to_name


def main() -> int:
    os.makedirs(OUT_ANALYSIS, exist_ok=True)

    # -----------------------------------------------------------------
    # 1. Load CSHapes -> gwno->name registry
    # -----------------------------------------------------------------
    _, gw_to_name = load_cshapes()

    def name_for(gw: int) -> str:
        if gw in gw_to_name:
            n = gw_to_name[gw]
            return n
        return f"GWN_{gw}"

    # -----------------------------------------------------------------
    # 2. Load MIDB (participants per dispute)
    # -----------------------------------------------------------------
    midb = pd.read_csv(MIDB_CSV, dtype={"styear": int, "endyear": int})
    print(f"MIDB rows: {len(midb):,}")  # check columns

    # Rename for clarity
    midb = midb.rename(columns={
        "styear": "year",
        "ccode": "ccode",
        "sidea": "sidea",
        "hostlev": "hostlev",
        "orig": "orig",
    })

    midb["year"] = midb["year"].astype(int)
    midb["hostlev"] = midb["hostlev"].astype(int)
    midb["ccode"] = midb["ccode"].astype(int)
    midb["sidea"] = midb["sidea"].astype(int)
    midb["orig"] = midb["orig"].astype(int)

    # Drop rows with missing or empty state names
    midb = midb.dropna(subset=["ccode"]).copy()

    # -----------------------------------------------------------------
    # 3. Group MIDB participants by dispute -> sides
    # -----------------------------------------------------------------
    t1_narrow_rows = []     # hostlev=2 only (matches current pipeline)
    t1_standard_rows = []   # hostlev=2 + hostlev=1 AND orig==1
    dropped_rows = []

    for dispnum, grp in midb.groupby("dispnum", sort=False):
        participants = []
        for _, r in grp.iterrows():
            participants.append({
                "ccode": int(r["ccode"]),
                "sidea": int(r["sidea"]),
                "hostlev": int(r["hostlev"]),
                "orig": int(r["orig"]),
                "year": int(r["year"]),
            })

        # Split by side
        sideA = [p for p in participants if p["sidea"] == 1]
        sideB = [p for p in participants if p["sidea"] == 0]

        for a_p in sideA:
            a_name = name_for(a_p["ccode"])
            a_hl = a_p["hostlev"]
            a_year = a_p["year"]
            a_orig = a_p["orig"]

            for b_p in sideB:
                b_name = name_for(b_p["ccode"])
                b_hl = b_p["hostlev"]
                b_year = b_p["year"]

                # Use the participant's start year for the dispute
                yr = min(a_year, b_year) if a_year > 0 and b_year > 0 else max(a_year, b_year)
                if yr < 1900:
                    continue

                # ---- Emission logic for A -> B ----
                # T1 = Diplomatic Crisis. A state qualifies as T1 initiator if:
                #   a) hostlev == 2 (issued a threat)          — "active threat"
                #   b) hostlev == 1 AND orig == 1 (originated   — "diplomatic originator"
                #      the dispute without personal escalation)
                # States with hostlev >= 3 (display/force/war) are handled by the
                # existing MIDB => T2/T4/T5 pipeline and are NOT re-emitted here.
                if a_hl == 2:
                    t1_narrow_rows.append((yr, a_name, b_name, 2, a_p["ccode"], b_p["ccode"]))
                    t1_standard_rows.append((yr, a_name, b_name, 2, a_p["ccode"], b_p["ccode"]))

                elif a_hl == 1 and a_orig == 1:
                    # Originated the dispute without personal militarised action
                    t1_standard_rows.append((yr, a_name, b_name, 1, a_p["ccode"], b_p["ccode"]))
                # hostlev=1 non-originators skipped: they did not initiate anything

                # ---- Emission logic for B -> A ----
                if b_hl == 2:
                    t1_narrow_rows.append((yr, b_name, a_name, 2, b_p["ccode"], a_p["ccode"]))
                    t1_standard_rows.append((yr, b_name, a_name, 2, b_p["ccode"], a_p["ccode"]))

                elif b_hl == 1 and b_p["orig"] == 1:
                    t1_standard_rows.append((yr, b_name, a_name, 1, b_p["ccode"], a_p["ccode"]))

    COLUMNS = ["year", "initiator", "target", "hostlev", "initiator_ccode", "target_ccode"]

    def dedup_and_write(rows, label: str) -> pd.DataFrame:
        if not rows:
            df = pd.DataFrame(columns=COLUMNS + ["action_max", "n_actions_aggregated", "uiw_tier", "tier_label", "source"])
        else:
            df = pd.DataFrame(rows, columns=COLUMNS)
            # Track max action per (year, initiator, target)
            df = df.groupby(["year", "initiator", "target"], as_index=False).agg(
                hostlev=("hostlev", "max"),
                initiator_ccode=("initiator_ccode", "first"),
                target_ccode=("target_ccode", "first"),
                n_actions_aggregated=("hostlev", "size"),
            )
            df["action_max"] = df["hostlev"]  # hostlev=max hostlev per dyad-year
            df["uiw_tier"] = 1
            df["tier_label"] = "T1-Diplomatic Crisis"
            df["source"] = "MIDB_T1"
            df = df[["year", "initiator", "target", "hostlev", "uiw_tier", "tier_label",
                     "initiator_ccode", "target_ccode", "source",
                     "action_max", "n_actions_aggregated"]]
        out_path = os.path.join(DATA_RAW, f"T1_directed_v5_{label}.csv")
        df.to_csv(out_path, index=False)
        print(f"  {label}: {len(df):,} rows -> {out_path}")
        return df

    narrow = dedup_and_write(t1_narrow_rows, "narrow")
    standard = dedup_and_write(t1_standard_rows, "standard")

    # Write default T1 file (standard width = threats + diplomatic originators)
    default_path = os.path.join(DATA_RAW, "T1_directed_v5.csv")
    standard.to_csv(default_path, index=False)
    print(f"\nT1 default (standard width) -> {default_path}")

    # -----------------------------------------------------------------
    # 5. Write definition table
    # -----------------------------------------------------------------
    def_rows = []
    for code in sorted(ACTION_TIER):
        hl, tier, desc = ACTION_TIER[code]
        in_t1 = "yes" if code in T1_ACTION_CODES else f"no (hostlev {hl} -> {tier})"
        def_rows.append({"action_code": code, "hostlev": hl,
                         "tier": tier, "description": desc,
                         "included_in_T1": in_t1})
    def_df = pd.DataFrame(def_rows)
    def_path = os.path.join(OUT_ANALYSIS, "t1_definition_table.csv")
    def_df.to_csv(def_path, index=False)
    print(f"Definition table -> {def_path}")

    # -----------------------------------------------------------------
    # 6. Write non-state dropped log (MIDB only has states, so this is empty)
    # -----------------------------------------------------------------
    drop_path = os.path.join(OUT_ANALYSIS, "t1_non_state_dropped.csv")
    pd.DataFrame(columns=["dispnum", "ccode", "reason"]).to_csv(drop_path, index=False)
    print(f"Non-state dropped -> {drop_path}")

    # -----------------------------------------------------------------
    # 7. Summary
    # -----------------------------------------------------------------
    print("\nT1 widths comparison (rows per hostlev before dedup):")
    for label, rows in [("narrow", t1_narrow_rows), ("standard", t1_standard_rows)]:
        if rows:
            df = pd.DataFrame(rows, columns=COLUMNS)
            print(f"\n  {label}: {len(df)} rows")
            print(df.groupby("hostlev").size().to_string())
        else:
            print(f"\n  {label}: 0 rows")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
