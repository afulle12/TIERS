"""Unit tests for the Section 2.8 T1 event builders and EUSANCT threat fix."""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "build"))

import build_t1_sources as bt1  # noqa: E402
import integrate_eusanct as ie  # noqa: E402


def _mock_states() -> pd.DataFrame:
    rows = []
    for y in (1988, 1989, 1990, 1991, 1992):
        rows.extend([
            (y, 2, "USA", 2, "United States of America"),
            (y, 200, "UKG", 200, "United Kingdom"),
            (y, 220, "FRN", 220, "France"),
            (y, 260 if y < 1990 else 255, "GFR" if y < 1990 else "GMY", 260, "German Federal Republic"),
            (y, 437, "CDI", 437, "Cote D'Ivoire"),
            (y, 645, "IRQ", 645, "Iraq"),
            (y, 700, "AFG", 700, "Afghanistan"),
            (y, 775, "MYA", 775, "Myanmar (Burma)"),
        ])
    return pd.DataFrame(rows, columns=["year", "ccode", "stateabb", "gwno", "name"])


def test_eusanct_separates_dyadic_threats_from_sanctions():
    states = _mock_states()
    eus = pd.DataFrame([
        # Case-level sanction==1 because US imposed, but EU only threatened in 1991
        {"caseid": "1990052201", "sender": "EU", "ccodecow": 775, "cname": "Myanmar", "year": 1991,
         "threat": 1, "threat_dyad": 1, "sanction": 1, "sanction_dyad": 0},
        # EU actually imposed in 1992
        {"caseid": "1990052201", "sender": "EU", "ccodecow": 775, "cname": "Myanmar", "year": 1992,
         "threat": 1, "threat_dyad": 1, "sanction": 1, "sanction_dyad": 1},
        # UN must be dropped
        {"caseid": "1990052201", "sender": "UN", "ccodecow": 775, "cname": "Myanmar", "year": 1991,
         "threat": 1, "threat_dyad": 1, "sanction": 1, "sanction_dyad": 1},
    ])
    t2, _ = ie.extract_eusanct_dyads(eus, states, mode="sanction")
    t1, _ = ie.extract_eusanct_dyads(eus, states, mode="threat")

    assert set(t2["year"]) == {1992}
    assert set(t1["year"]) == {1991}
    assert set(t1["target_ccode"]) == {775}
    assert {200, 220, 255}.issubset(set(t1["initiator_ccode"]))


def test_ties_corrections_non_imposed_years_and_eu_expansion():
    states = _mock_states()
    ties = pd.DataFrame([
        # Case 1990999901 gets threat=1 from TIESCorrection.txt; imposed in 1991 -> T1 in 1990 only
        {"caseid": 1990999901, "startyear": 1990, "endyear": 1992, "ongoingasofyear": None,
         "primarysender": 1000, "sender1": 1000, "sender2": None, "targetstate": 645,
         "threat": 0, "imposition": 1, "sancimpositionstartyear": 1991},
        # Case 2002041103 gets targetstate=490 -> outside mock states -> dropped cleanly
        {"caseid": 2002041103, "startyear": 1990, "endyear": 1990, "ongoingasofyear": None,
         "primarysender": 2, "sender1": 2, "sender2": None, "targetstate": None,
         "threat": 1, "imposition": 0, "sancimpositionstartyear": None},
        # Imposed in same startyear -> not a threat-only year
        {"caseid": 9999999991, "startyear": 1990, "endyear": 1991, "ongoingasofyear": None,
         "primarysender": 2, "sender1": 2, "sender2": None, "targetstate": 700,
         "threat": 1, "imposition": 1, "sancimpositionstartyear": 1990},
        # Unimposed threat using sender1 when primarysender is NaN
        {"caseid": 9999999992, "startyear": 1989, "endyear": 1990, "ongoingasofyear": None,
         "primarysender": None, "sender1": 2, "sender2": 200, "targetstate": 700,
         "threat": 1, "imposition": 0, "sancimpositionstartyear": None},
    ])
    ev, dropped = bt1.extract_ties_events(ties, states)
    keys = set(zip(ev["year"], ev["initiator_ccode"], ev["target_ccode"], ev["event_ref"], strict=True))

    # EU (1000) in 1990 includes UK (200), France (220), and unified Germany (255)
    assert (1990, 200, 645, "TIES:1990999901") in keys
    assert (1990, 255, 645, "TIES:1990999901") in keys
    assert (1991, 200, 645, "TIES:1990999901") not in keys  # imposed in 1991

    # Same-year imposition excluded
    assert "TIES:9999999991" not in set(ev["event_ref"])

    # Null primarysender still expands sender1 & sender2 across 1989-1990
    assert (1989, 2, 700, "TIES:9999999992") in keys
    assert (1990, 200, 700, "TIES:9999999992") in keys
    assert len(dropped) >= 1


def test_icb_direction_recovery_and_fallback_symmetry():
    states = _mock_states()
    icb_d = pd.DataFrame([
        # Side B triggered by Side A -> directed A -> B only
        {"crisno": 100, "year": 1990, "statea": 2, "actnuma": 1, "stateb": 645, "actnumb": 2},
        # Non-state trigger 996 / non-crisis 9999 -> both directions emitted
        {"crisno": 101, "year": 1991, "statea": 200, "actnuma": 1, "stateb": 700, "actnumb": 9999},
    ])
    icb_a = pd.DataFrame([
        {"crisno": 100, "cracno": 1, "trigent": 996, "southv": 996},
        {"crisno": 100, "cracno": 2, "trigent": 2, "southv": 2},
        {"crisno": 101, "cracno": 1, "trigent": 996, "southv": 996},
    ])
    ev, _ = bt1.extract_icb_events(icb_d, icb_a, states)
    pairs = set(zip(ev["year"], ev["initiator_ccode"], ev["target_ccode"], ev["event_ref"], strict=True))
    assert pairs == {
        (1990, 2, 645, "ICB:100"),
        (1991, 200, 700, "ICB:101"),
        (1991, 700, 200, "ICB:101"),
    }


def test_drd_focus3_and_country_name_crosswalk():
    states = _mock_states()
    drd = pd.DataFrame([
        # Focus != 3 ignored
        {"Year": 1989, "SendingCountry": "France", "Destination": "United States", "Focus": 1, "EmbassyFocus": 61, "LOR": 1.0},
        # Germany resolves 260 in 1989 and 255 in 1990; Windows-1252 apostrophe in Cote d'Ivoire resolves 437
        {"Year": 1989, "SendingCountry": "Germany", "Destination": "Côte d'\x92Ivoire", "Focus": 3, "EmbassyFocus": 63, "LOR": 0.0},
        {"Year": 1990, "SendingCountry": "Germany", "Destination": "Myanmar", "Focus": 3, "EmbassyFocus": 13, "LOR": 0.0},
        # Microstate dropped cleanly
        {"Year": 1990, "SendingCountry": "Nauru", "Destination": "France", "Focus": 3, "EmbassyFocus": 63, "LOR": 0.0},
    ])
    ev, dropped = bt1.extract_drd_events(drd, states)
    pairs = set(zip(ev["year"], ev["initiator_ccode"], ev["target_ccode"], strict=True))
    assert pairs == {(1989, 260, 437), (1990, 255, 775)}
    assert len(dropped) == 1
    assert "Nauru" in dropped["reason"].iloc[0]
