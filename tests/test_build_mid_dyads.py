"""Tests for the MID dyad-event builder (proposal section 2.0.1)."""
from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "build"))

import build_mid_dyads as bmd  # noqa: E402


def _participants(rows) -> pd.DataFrame:
    cols = ["dispnum", "stabb", "ccode", "styear", "endyear", "sidea", "hostlev", "orig"]
    return pd.DataFrame(rows, columns=cols)


def _tiers(events: pd.DataFrame) -> dict:
    return {
        (r.year, r.initiator_ccode, r.target_ccode): r.uiw_tier
        for r in events.itertuples(index=False)
    }


def test_bilateral_direction_and_years():
    # State 10 uses force for two years; state 20 takes no militarised action.
    midb = _participants([
        (1, "AAA", 10, 1950, 1951, 1, 4, 1),
        (1, "BBB", 20, 1950, 1951, 0, 1, 1),
    ])
    events, counts = bmd.expand_dyad_events(midb)
    assert _tiers(events) == {(1950, 10, 20): 4, (1951, 10, 20): 4}
    assert counts["no_action"] == 2  # the passive side emits nothing
    assert set(events["pairing_basis"]) == {"bilateral"}
    assert set(events["hostlev"]) == {4} and set(events["target_hostlev"]) == {1}


def test_coalition_needs_evidence_force_was_aimed_at_target():
    # 30 is at war with a three-state side: 40 fights, 50 uses force, 60 only displays.
    midb = _participants([
        (2, "CCC", 30, 1960, 1960, 1, 5, 1),
        (2, "DDD", 40, 1960, 1960, 0, 5, 1),
        (2, "EEE", 50, 1960, 1960, 0, 4, 0),
        (2, "FFF", 60, 1960, 1960, 0, 3, 0),
    ])
    events, counts = bmd.expand_dyad_events(midb)
    t = _tiers(events)
    assert t[(1960, 30, 40)] == 5 and t[(1960, 40, 30)] == 5
    assert t[(1960, 30, 50)] == 5      # 50 used force, so it was in the fight
    assert t[(1960, 30, 60)] == 1      # no record that 30 fired on the displayer
    assert t[(1960, 50, 30)] == 4      # 30 is alone on its side: no ambiguity
    assert t[(1960, 60, 30)] == 1
    assert counts["coalition_capped"] == 1


def test_sole_target_is_never_capped():
    # Two attackers against one state that does not resist.
    midb = _participants([
        (3, "GGG", 70, 1968, 1968, 1, 4, 1),
        (3, "HHH", 71, 1968, 1968, 1, 1, 0),
        (3, "III", 80, 1968, 1968, 0, 1, 1),
    ])
    events, _ = bmd.expand_dyad_events(midb)
    assert _tiers(events) == {(1968, 70, 80): 4}
    assert events["pairing_basis"].iloc[0] == "sole-target"


def test_late_joiner_only_overlapping_years():
    midb = _participants([
        (4, "JJJ", 90, 1960, 1965, 1, 5, 1),
        (4, "KKK", 91, 1960, 1965, 0, 5, 1),
        (4, "LLL", 92, 1963, 1964, 0, 4, 0),
    ])
    events, _ = bmd.expand_dyad_events(midb)
    years = sorted(y for (y, i, j) in _tiers(events) if (i, j) == (90, 92))
    assert years == [1963, 1964]


def test_incident_coverage_overrides_inference():
    midb = _participants([
        (5, "MMM", 100, 2000, 2000, 1, 4, 1),
        (5, "NNN", 110, 2000, 2000, 0, 4, 1),
        (5, "OOO", 120, 2000, 2000, 0, 4, 0),
        (5, "PPP", 130, 2000, 2000, 0, 4, 0),
    ])
    # 100 fired on 110, only postured at 120, and never met 130.
    pairs = {(5, 100, 110): 4, (5, 110, 100): 4, (5, 100, 120): 3, (5, 120, 100): 3}
    events, counts = bmd.expand_dyad_events(midb, pairs, {5})
    t = _tiers(events)
    assert t[(2000, 100, 110)] == 4
    assert t[(2000, 100, 120)] == 1
    assert (2000, 100, 130) not in t
    assert (2000, 130, 100) in t  # 100 is alone on its side, so 130 keeps its tier
    assert counts["no_shared_incident"] == 1


def test_no_mid_row_is_t2_or_t3():
    midb = _participants([
        (6, "QQQ", 140, 1970, 1970, 1, 3, 1),
        (6, "RRR", 150, 1970, 1970, 0, 2, 1),
    ])
    events, _ = bmd.expand_dyad_events(midb)
    assert set(events["uiw_tier"]) == {1}
    assert set(events["tier_label"]) == {"T1-Diplomatic Crisis"}


@pytest.mark.skipif(not os.path.exists(bmd.MIDB_CSV), reason="raw MID 5.0 files not present")
def test_known_wars_on_raw_mid():
    events, _ = bmd.build()
    lookup = events.groupby(["year", "initiator_ccode", "target_ccode"])["uiw_tier"].max().to_dict()
    expected = {
        (1990, 645, 690): 5,   # Iraq -> Kuwait: Iraq is MID side A at war level
        (1990, 690, 645): 4,   # Kuwait -> Iraq: Kuwait's own level is use of force
        (1948, 651, 666): 5,   # Egypt -> Israel
        (1948, 666, 651): 5,   # Israel -> Egypt
        (1982, 666, 660): 5,   # Israel -> Lebanon
        (1981, 645, 630): 5,   # Iraq -> Iran
        (1981, 630, 645): 5,   # Iran -> Iraq
        (1951, 211, 731): 5,   # Belgium -> North Korea: both at war level
        (1965, 365, 920): 1,   # Soviet Union -> New Zealand: a threat, not a war
        (1991, 645, 160): 1,   # Iraq -> Argentina: Argentina only displayed force
    }
    for key, tier in expected.items():
        assert lookup.get(key) == tier, key
    # The Soviet spell in the Vietnam War dispute ends in 1965.
    assert (1970, 365, 920) not in lookup
    assert set(events["uiw_tier"]) <= {1, 4, 5}


@pytest.mark.skipif(not os.path.exists(bmd.MIDB_CSV), reason="raw MID 5.0 files not present")
def test_every_row_matches_a_raw_participant_record():
    events, _ = bmd.build()
    midb = bmd.load_midb()
    own = set(zip(midb["dispnum"], midb["ccode"], midb["hostlev"], midb["sidea"], strict=True))
    for r in events.itertuples(index=False):
        assert (r.dispnum, r.initiator_ccode, r.hostlev, r.mid_side_a) in own
        assert r.uiw_tier <= bmd.HOSTLEV_TO_TIER[r.hostlev]
