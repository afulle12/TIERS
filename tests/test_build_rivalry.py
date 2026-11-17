"""Tests for the rivalry builder (proposal section 2.6): direction, lag, decay, window."""
from __future__ import annotations

import math
import os
import sys

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "build"))

import build_rivalry as br  # noqa: E402


def _events(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["year", "initiator_ccode", "target_ccode", "uiw_tier", "hostlev"])


def _states(codes, years) -> pd.DataFrame:
    return pd.DataFrame([(y, c) for y in years for c in codes], columns=["year", "ccode"])


def _value(table, year, i, j, col="rivalry_omega") -> float:
    row = table[(table.year == year) & (table.initiator_ccode == i) & (table.target_ccode == j)]
    return float(row[col].iloc[0]) if len(row) else 0.0


# Three events: 10 threatens 20 in 1940 (before the window), 10 uses force
# against 20 in 1950, and 20 displays force against 10 in 1952.
EVENTS = _events([
    (1940, 10, 20, 1, 2),
    (1950, 10, 20, 4, 4),
    (1952, 20, 10, 1, 3),
])
STATES = _states([10, 20, 30], range(1946, 1956))
TABLE = br.build_rivalry(EVENTS, STATES, year_lo=1946, year_hi=1955)
D = math.exp(-br.LAMBDA)


def test_direction_the_target_of_an_action_holds_the_rivalry():
    # 10 acted against 20, so in 1950 it is 20 that sees 10 as a rival.
    assert _value(TABLE, 1950, 20, 10) > 0.7
    # 10's rivalry toward 20 is still zero: 20 has done nothing yet.
    assert _value(TABLE, 1950, 10, 20) == 0.0
    # The row carries the reverse value too, for the other directed run.
    assert _value(TABLE, 1950, 10, 20, "rivalry_omega_b") == _value(TABLE, 1950, 20, 10)
    # After 20 acts in 1952, both directions are positive and still unequal.
    assert _value(TABLE, 1952, 10, 20) == pytest.approx(0.50, abs=1e-6)
    assert _value(TABLE, 1952, 20, 10) != _value(TABLE, 1952, 10, 20)


def test_lag_year_t_events_count_in_year_t_and_not_before():
    assert _value(TABLE, 1949, 20, 10) == pytest.approx(0.25 * D ** 9, abs=1e-6)   # only the 1940 threat
    assert _value(TABLE, 1950, 20, 10) == pytest.approx(0.25 * D ** 10 + 0.75, abs=1e-6)


def test_decay_follows_the_stated_kernel():
    v1950 = 0.25 * D ** 10 + 0.75
    assert _value(TABLE, 1953, 20, 10) == pytest.approx(v1950 * D ** 3, abs=1e-6)


def test_history_before_the_window_is_kept():
    assert _value(TABLE, 1946, 20, 10) == pytest.approx(0.25 * D ** 6, abs=1e-6)


def test_shared_history_and_cap():
    assert _value(TABLE, 1952, 10, 20, "conflict_history") == pytest.approx(
        min(1.0, _value(TABLE, 1952, 10, 20) + _value(TABLE, 1952, 20, 10)), abs=1e-6
    )
    war = _events([(y, 10, 20, 5, 5) for y in range(1946, 1950)])
    capped = br.build_rivalry(war, STATES, year_lo=1946, year_hi=1955)
    assert _value(capped, 1949, 20, 10) == 1.0


def test_uninvolved_state_and_non_members_have_no_row():
    assert TABLE[(TABLE.initiator_ccode == 30) | (TABLE.target_ccode == 30)].empty
    absent = br.build_rivalry(EVENTS, _states([10], range(1946, 1956)), year_lo=1946, year_hi=1955)
    assert absent.empty


def test_coalition_capped_row_counts_as_a_display():
    # Own level is war, but the builder capped the row to T1: weight of a display.
    ev = _events([(1950, 10, 20, 1, 5)])
    tab = br.build_rivalry(ev, STATES, year_lo=1946, year_hi=1955)
    assert _value(tab, 1950, 20, 10) == pytest.approx(0.50, abs=1e-6)


def test_history_follows_a_change_of_code():
    # West Germany is COW 260 until 1990 and unified Germany is COW 255 after.
    ev = _events([(1989, 100, 260, 4, 4)])
    states = pd.concat([_states([100, 260], [1989]), _states([100, 255], [1991])])
    tab = br.build_rivalry(ev, states, year_lo=1989, year_hi=1991)
    assert _value(tab, 1991, 255, 100) == pytest.approx(0.75 * D ** 2, abs=1e-6)
