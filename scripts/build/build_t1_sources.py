"""Build the Section 2.8 T1 event union from non-MID sources.

Combines four human-coded T1 sources covering formal diplomatic and economic
coercion that MID5 omits or under-represents:

  1. EUSANCT_THREAT  (1989-2015): dyadic sanction threats not yet imposed
     (``threat_dyad == 1`` and ``sanction_dyad != 1``) from EUSANCT.
  2. TIES            (1945-2005): sanction threats not imposed in that year
     (``threat == 1``, before ``sancimpositionstartyear`` or unimposed), with
     ``TIESCorrection.txt`` patches applied and ``1000`` (EEC/EU) expanded.
  3. ICB             (1918-2022): ICB v16 crisis dyad-years with trigger
     direction recovered from ``icb2v16.csv`` (`TRIGENT`/`SOUTHV`); filtered
     in ``build_dyad_states.py`` to pair-years below T3 in our own table.
  4. DIPREP          (1960-2025): Pardee Diplomatic Representation Database
     recalls, withdrawals, severance, and expulsions (``Focus == 3``).

All sources are standardized to directed COW/GW pairs within
``data/processed/state_system.csv`` and written to
``data/processed/t1_union_events.csv`` (with out-of-system/unmapped drops in
``data/processed/t1_union_dropped.csv``).
"""
from __future__ import annotations

import os
from collections.abc import Iterable

import numpy as np
import pandas as pd
from country_names import normalize_name
from integrate_eusanct import EU_ACCESSION, extract_eusanct_dyads
from state_system import load_state_system

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
T1_DIR = os.path.join(DATA_RAW, "t1_sources")

EUSANCT_XLS = os.path.join(DATA_RAW, "EUSANCT_Dataset_Dyadic.xls")
TIES_XLS = os.path.join(T1_DIR, "TIESv4-1.xls")
ICB_DYADS_CSV = os.path.join(T1_DIR, "ICB_Dyads_v16.csv")
ICB_ACTORS_CSV = os.path.join(T1_DIR, "icb2v16.csv")
DRD_XLSX = os.path.join(
    T1_DIR, "Diplometrics_Diplomatic-Representation_1960-2025_20260924.xlsx"
)

OUT_EVENTS = os.path.join(DATA_PROCESSED, "t1_union_events.csv")
OUT_DROPPED = os.path.join(DATA_PROCESSED, "t1_union_dropped.csv")

EVENT_COLUMNS = [
    "year", "initiator", "target", "initiator_ccode", "target_ccode",
    "initiator_gwno", "target_gwno", "uiw_tier", "tier_label", "source",
    "attribution", "event_ref", "t1_basis",
]

TIER1_LABEL = "T1-Diplomatic Crisis"

# DRD names whose COW code changes across periods (resolved via state_system GWNO).
DRD_NAME_TO_GWNO = {
    "Germany": 260,  # ccode 260 (1955-1989) -> ccode 255 (1990+)
    "Yemen": 678,    # ccode 678 (pre-1990) -> ccode 679 (1990+, same GWNO 678)
}

# DRD names that differ from state_system's normalized CShapes country names.
DRD_NAME_TO_CCODE = {
    "Belarus": 370,
    "Burkina Faso": 439,
    "Cambodia": 811,
    "Congo-Brazzaville": 484,
    "Congo-Kinshasa": 490,
    "Côte d'\x92Ivoire": 437,
    "Côte d'Ivoire": 437,
    "Cote d'Ivoire": 437,
    "Czechoslovakia": 315,
    "Czech Republic": 316,
    "Gambia, The": 420,
    "Iran": 630,
    "Italy": 325,
    "Korea, Democratic People's Republic of": 731,
    "Korea, Republic of": 732,
    "Lao People's Democratic Republic": 812,
    "Macedonia": 343,
    "Madagascar": 580,
    "Myanmar": 775,
    "Romania": 360,
    "Russia": 365,
    "Serbia": 345,
    "Serbia and Montenegro": 345,
    "Sri Lanka": 780,
    "Suriname": 115,
    "Turkey": 640,
    "United States": 2,
    "Viet Nam": 816,
    "Yemen, People's Democratic Republic of": 680,
    "Yugoslavia": 345,
    "Zimbabwe": 552,
}


def attach_by_ccode(
    ev: pd.DataFrame,
    states: pd.DataFrame,
    reason_label: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attach canonical names and GWNOs from `states` using (year, ccode).

    Drops self-dyads and rows where either actor is outside `state_system` for
    that year, returning `(kept, dropped)`.
    """
    if len(ev) == 0:
        empty = pd.DataFrame(columns=EVENT_COLUMNS)
        return empty, pd.DataFrame(columns=["year", "initiator_ccode", "target_ccode", "source", "reason"])

    s_a = states[["year", "ccode", "gwno", "name"]].rename(columns={
        "ccode": "initiator_ccode", "gwno": "initiator_gwno", "name": "initiator",
    })
    s_b = states[["year", "ccode", "gwno", "name"]].rename(columns={
        "ccode": "target_ccode", "gwno": "target_gwno", "name": "target",
    })
    m = ev.merge(s_a, on=["year", "initiator_ccode"], how="left")
    m = m.merge(s_b, on=["year", "target_ccode"], how="left")

    valid = (
        m["initiator"].notna()
        & m["target"].notna()
        & (m["initiator_ccode"] != m["target_ccode"])
    )
    kept = m.loc[valid].copy()
    kept["initiator_ccode"] = kept["initiator_ccode"].astype(int)
    kept["target_ccode"] = kept["target_ccode"].astype(int)
    kept["initiator_gwno"] = kept["initiator_gwno"].astype(int)
    kept["target_gwno"] = kept["target_gwno"].astype(int)
    kept["uiw_tier"] = 1
    kept["tier_label"] = TIER1_LABEL
    if "attribution" not in kept.columns:
        kept["attribution"] = np.nan

    dropped = m.loc[~valid, ["year", "initiator_ccode", "target_ccode", "source"]].copy()
    dropped["reason"] = reason_label
    return kept[EVENT_COLUMNS], dropped


def apply_ties_corrections(ties: pd.DataFrame) -> pd.DataFrame:
    """Apply the five official errata documented in TIESCorrection.txt."""
    out = ties.copy()
    case = pd.to_numeric(out["caseid"], errors="coerce")
    out.loc[case == 1990999901, "threat"] = 1
    out.loc[case == 1983011301, "imposition"] = 1
    if (case == 1973070501).any():
        mask = case == 1973070501
        if "startmonth" in out.columns:
            out.loc[mask, "startmonth"] = 1
        if "startday" in out.columns:
            out.loc[mask, "startday"] = 9
        if "sancimpositionstartmonth" in out.columns:
            out.loc[mask, "sancimpositionstartmonth"] = 1
        if "sancimpositionstartday" in out.columns:
            out.loc[mask, "sancimpositionstartday"] = "9"
        if "finaloutcome" in out.columns:
            out.loc[mask, "finaloutcome"] = 8
    out.loc[case == 2002041106, "endyear"] = 2004
    out.loc[case == 2002041103, "targetstate"] = 490
    return out


def _expand_sender_codes(
    codes: Iterable[int],
    year: int,
    gw_to_ccode: dict[tuple[int, int], int],
) -> list[int]:
    """Expand COW sender codes, turning 1000 (EEC/EU) into member ccodes for `year`."""
    expanded: list[int] = []
    for code in codes:
        if code == 1000:
            for gwno, acc in EU_ACCESSION.items():
                if year >= acc and (year, gwno) in gw_to_ccode:
                    expanded.append(gw_to_ccode[(year, gwno)])
        else:
            expanded.append(code)
    return sorted(set(expanded))


def extract_ties_events(
    ties: pd.DataFrame,
    states: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract non-imposed sanction-threat dyad-years from TIES v4.0."""
    df = apply_ties_corrections(ties)
    df = df[df["threat"] == 1].copy()

    gw_to_ccode = {
        (int(r.year), int(r.gwno)): int(r.ccode)
        for r in states.itertuples(index=False)
    }
    sender_cols = [c for c in ("primarysender", "sender1", "sender2", "sender3", "sender4", "sender5") if c in df.columns]

    rows: list[dict] = []
    for _, r in df.iterrows():
        if pd.isna(r["startyear"]) or pd.isna(r["targetstate"]):
            continue
        start = int(r["startyear"])
        tgt = int(r["targetstate"])
        end_raw = (
            int(r["endyear"]) if pd.notna(r["endyear"])
            else int(r["ongoingasofyear"]) if "ongoingasofyear" in df.columns and pd.notna(r["ongoingasofyear"])
            else start
        )
        end_raw = max(start, end_raw)

        if r["imposition"] == 1:
            imp_yr = pd.to_numeric(r.get("sancimpositionstartyear"), errors="coerce")
            if pd.isna(imp_yr) or int(imp_yr) <= start:
                continue
            end = min(end_raw, int(imp_yr) - 1)
        else:
            end = end_raw

        raw_senders = [int(r[c]) for c in sender_cols if pd.notna(r[c])]
        if not raw_senders:
            continue
        case_ref = f"TIES:{int(r['caseid'])}" if pd.notna(r.get("caseid")) else "TIES"
        for year in range(start, end + 1):
            for s_ccode in _expand_sender_codes(raw_senders, year, gw_to_ccode):
                rows.append({
                    "year": year,
                    "initiator_ccode": s_ccode,
                    "target_ccode": tgt,
                    "source": "TIES",
                    "event_ref": case_ref,
                    "t1_basis": "TIES sanction threat",
                })

    raw_ev = pd.DataFrame(rows)
    if len(raw_ev) > 0:
        raw_ev = raw_ev.drop_duplicates(subset=["year", "initiator_ccode", "target_ccode", "event_ref"])
    return attach_by_ccode(raw_ev, states, reason_label="TIES non-member or self")


def extract_icb_events(
    icb_dyads: pd.DataFrame,
    icb_actors: pd.DataFrame,
    states: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract directed/symmetric ICB v16 crisis dyad-years with trigger direction."""
    act = icb_actors[["crisno", "cracno", "trigent", "southv"]].drop_duplicates(["crisno", "cracno"])
    m = icb_dyads.merge(
        act.rename(columns={"trigent": "triga", "southv": "sva"}),
        left_on=["crisno", "actnuma"], right_on=["crisno", "cracno"], how="left",
    ).drop(columns=["cracno"], errors="ignore")
    m = m.merge(
        act.rename(columns={"trigent": "trigb", "southv": "svb"}),
        left_on=["crisno", "actnumb"], right_on=["crisno", "cracno"], how="left",
    ).drop(columns=["cracno"], errors="ignore")

    rows: list[dict] = []
    for r in m.itertuples(index=False):
        year = int(r.year)
        a, b = int(r.statea), int(r.stateb)
        ref = f"ICB:{int(r.crisno)}"
        a_trig = (r.trigb == a) or (r.svb == a)
        b_trig = (r.triga == b) or (r.sva == b)
        if a_trig and not b_trig:
            pairs = [(a, b)]
        elif b_trig and not a_trig:
            pairs = [(b, a)]
        else:
            pairs = [(a, b), (b, a)]
        for init_cc, tgt_cc in pairs:
            rows.append({
                "year": year,
                "initiator_ccode": init_cc,
                "target_ccode": tgt_cc,
                "source": "ICB",
                "event_ref": ref,
                "t1_basis": "ICB non-violent crisis",
            })

    raw_ev = pd.DataFrame(rows)
    if len(raw_ev) > 0:
        raw_ev = raw_ev.drop_duplicates(subset=["year", "initiator_ccode", "target_ccode", "event_ref"])
    return attach_by_ccode(raw_ev, states, reason_label="ICB non-member or self")


def _resolve_drd_name(
    name: object,
    year: int,
    yr_name_ccode: dict[tuple[int, str], int],
    valid_yr_ccodes: set[tuple[int, int]],
) -> int | None:
    if not isinstance(name, str) or not name.strip():
        return None
    s = name.strip()
    if (year, s) in yr_name_ccode:
        return yr_name_ccode[(year, s)]
    norm = normalize_name(s)
    if (year, norm) in yr_name_ccode:
        return yr_name_ccode[(year, norm)]
    cc = DRD_NAME_TO_CCODE.get(s) or DRD_NAME_TO_CCODE.get(norm)
    if cc is not None and (year, cc) in valid_yr_ccodes:
        return cc
    return None


def extract_drd_events(
    drd: pd.DataFrame,
    states: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract Focus==3 (recall/withdrawal/expulsion) events from Pardee DRD."""
    f3 = drd[drd["Focus"] == 3].copy()

    yr_name_ccode: dict[tuple[int, str], int] = {}
    gw_yr_ccode: dict[tuple[int, int], int] = {}
    valid_yr_ccodes: set[tuple[int, int]] = set()
    for r in states.itertuples(index=False):
        y, cc, gw, nm = int(r.year), int(r.ccode), int(r.gwno), str(r.name)
        valid_yr_ccodes.add((y, cc))
        yr_name_ccode[(y, nm)] = cc
        yr_name_ccode[(y, normalize_name(nm))] = cc
        gw_yr_ccode[(y, gw)] = cc
    for y in states["year"].astype(int).unique():
        for nm, gw in DRD_NAME_TO_GWNO.items():
            if (y, gw) in gw_yr_ccode:
                yr_name_ccode[(y, nm)] = gw_yr_ccode[(y, gw)]

    kept_rows: list[dict] = []
    dropped_rows: list[dict] = []
    for r in f3.itertuples(index=False):
        year = int(r.Year)
        init_cc = _resolve_drd_name(r.SendingCountry, year, yr_name_ccode, valid_yr_ccodes)
        tgt_cc = _resolve_drd_name(r.Destination, year, yr_name_ccode, valid_yr_ccodes)
        if init_cc is None or tgt_cc is None:
            dropped_rows.append({
                "year": year,
                "initiator_ccode": init_cc,
                "target_ccode": tgt_cc,
                "source": "DIPREP",
                "reason": f"DIPREP unmapped ({r.SendingCountry} -> {r.Destination})",
            })
            continue
        ef = int(r.EmbassyFocus) if pd.notna(r.EmbassyFocus) else 3
        kept_rows.append({
            "year": year,
            "initiator_ccode": init_cc,
            "target_ccode": tgt_cc,
            "source": "DIPREP",
            "event_ref": f"DRD:{year}:{ef}",
            "t1_basis": "DRD recall/expulsion",
        })

    raw_ev = pd.DataFrame(kept_rows)
    if len(raw_ev) > 0:
        raw_ev = raw_ev.drop_duplicates(subset=["year", "initiator_ccode", "target_ccode", "event_ref"])
    kept, drop_attach = attach_by_ccode(raw_ev, states, reason_label="DIPREP non-member or self")
    dropped = pd.concat([pd.DataFrame(dropped_rows), drop_attach], ignore_index=True, sort=False)
    return kept, dropped


def build_t1_union(states: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load all four Section 2.8 raw sources and return combined T1 events + drops."""
    eus_raw = pd.read_excel(EUSANCT_XLS)
    eus_t1_raw, _ = extract_eusanct_dyads(eus_raw, states, mode="threat")
    eus_t1, eus_drop = attach_by_ccode(
        eus_t1_raw[["year", "initiator_ccode", "target_ccode", "source", "event_ref", "t1_basis"]],
        states,
        reason_label="EUSANCT_THREAT non-member or outside state_system",
    )

    ties_raw = pd.read_excel(TIES_XLS, sheet_name="TIESv4.1.raw")
    ties_t1, ties_drop = extract_ties_events(ties_raw, states)

    icb_d = pd.read_csv(ICB_DYADS_CSV)
    icb_a = pd.read_csv(ICB_ACTORS_CSV)
    icb_t1, icb_drop = extract_icb_events(icb_d, icb_a, states)

    drd_raw = pd.read_excel(DRD_XLSX)
    drd_t1, drd_drop = extract_drd_events(drd_raw, states)

    events = pd.concat([eus_t1, ties_t1, icb_t1, drd_t1], ignore_index=True, sort=False)
    events = events[EVENT_COLUMNS].sort_values(
        ["year", "initiator_ccode", "target_ccode", "source"]
    ).reset_index(drop=True)
    dropped = pd.concat([eus_drop, ties_drop, icb_drop, drd_drop], ignore_index=True, sort=False)
    return events, dropped


def main() -> int:
    states = load_state_system()
    events, dropped = build_t1_union(states)
    events.to_csv(OUT_EVENTS, index=False)
    dropped.to_csv(OUT_DROPPED, index=False)
    print(f"T1 union events -> {OUT_EVENTS} ({len(events):,} directed events)")
    print("  by source:", events["source"].value_counts().to_dict())
    print(f"T1 dropped -> {OUT_DROPPED} ({len(dropped):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
