"""Contracts the built data must satisfy (proposal section 2.7).

These run against the generated tables in `data/processed/` and are skipped
when those tables have not been built.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
STATES = os.path.join(PROCESSED, "dyad_states.parquet")
EVENTS = os.path.join(PROCESSED, "dyad_events.csv")
SYSTEM = os.path.join(PROCESSED, "state_system.csv")
GRID = os.path.join(PROCESSED, "dyads_with_features_v28.parquet")
KEY = ["year", "initiator_ccode", "target_ccode"]

needs_states = pytest.mark.skipif(
    not (os.path.exists(STATES) and os.path.exists(EVENTS) and os.path.exists(SYSTEM)),
    reason="dyad state tables not built",
)
needs_grid = pytest.mark.skipif(not os.path.exists(GRID), reason="v28 feature grid not built")


@pytest.fixture(scope="module")
def states() -> pd.DataFrame:
    return pd.read_parquet(STATES)


@pytest.fixture(scope="module")
def grid() -> pd.DataFrame:
    return pd.read_parquet(GRID)


def _reverse(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Each row joined to the row for the opposite direction."""
    rev = df[KEY + cols].rename(columns={
        "initiator_ccode": "target_ccode", "target_ccode": "initiator_ccode",
        **{c: f"{c}_rev" for c in cols},
    })
    return df[KEY + cols].merge(rev, on=KEY, how="left")


@needs_states
def test_one_row_per_directed_dyad_year(states):
    assert not states.duplicated(KEY).any()
    assert not states.duplicated(["year", "initiator", "target"]).any()
    assert (states["initiator_ccode"] != states["target_ccode"]).all()


@needs_states
def test_tiers_are_valid(states):
    for col in ("uiw_tier", "directed_tier", "reverse_tier"):
        assert states[col].between(0, 5).all()
    assert (states["uiw_tier"] == states[["directed_tier", "reverse_tier"]].max(axis=1)).all()


@needs_states
def test_both_states_exist_in_that_year(states):
    members = pd.read_csv(SYSTEM)
    member_keys = set(zip(members["year"], members["ccode"], strict=True))
    for col in ("initiator_ccode", "target_ccode"):
        pairs = states[["year", col]].drop_duplicates()
        assert all((y, c) in member_keys for y, c in zip(pairs["year"], pairs[col], strict=True))


@needs_states
def test_every_pair_of_members_is_present(states):
    members = pd.read_csv(SYSTEM)
    n = members[members.year.between(states.year.min(), states.year.max())].groupby("year").size()
    assert len(states) == int((n * (n - 1)).sum())


@needs_states
def test_tier_is_shared_by_both_directions(states):
    j = _reverse(states, ["uiw_tier", "d_k_years"])
    assert j["uiw_tier_rev"].notna().all()
    assert (j["uiw_tier"] == j["uiw_tier_rev"]).all()
    assert (j["d_k_years"] == j["d_k_years_rev"]).all()


@needs_states
def test_no_dyad_year_sits_below_its_highest_recorded_event(states):
    ev = pd.read_csv(EVENTS)
    ev = ev[ev.year.between(states.year.min(), states.year.max())]
    top = ev.groupby(KEY, as_index=False)["uiw_tier"].max().rename(columns={"uiw_tier": "event_tier"})
    j = states.merge(top, on=KEY, how="inner")
    assert len(j) == len(top), "an event has no row in the state table"
    assert (j["directed_tier"] == j["event_tier"]).all()
    assert (j["uiw_tier"] >= j["event_tier"]).all()


@needs_states
def test_duration_counts_years_at_current_tier(states):
    s = states.sort_values(KEY[1:] + ["year"])
    prev = s.groupby(KEY[1:])[["year", "uiw_tier", "d_k_years"]].shift(1)
    continued = (prev["year"] == s["year"] - 1) & (prev["uiw_tier"] == s["uiw_tier"])
    assert (s.loc[continued, "d_k_years"] == prev.loc[continued, "d_k_years"] + 1).all()
    assert (s.loc[~continued, "d_k_years"] == 0).all()


@needs_states
def test_mid_events_never_reach_t2_or_t3():
    ev = pd.read_csv(EVENTS)
    assert set(ev.loc[ev.source == "MID5", "uiw_tier"]) <= {1, 4, 5}
    assert set(ev.loc[ev.source == "EUSANCT", "uiw_tier"]) == {2}
    assert set(ev.loc[ev.source == "UCDP_T3", "uiw_tier"]) == {3}
    esd = ev[ev.source == "UCDP_ESD"]
    assert set(esd["uiw_tier"]) <= {3}
    assert esd["year"].min() >= 1975


@needs_states
def test_t3_support_only_counts_against_the_government_it_fights():
    """A supporter of the host government is not in a T3 conflict with the host."""
    t3_raw = os.path.join(ROOT, "data", "raw", "T3_broad_v26_1.csv")
    if not os.path.exists(t3_raw):
        pytest.skip("raw UCDP T3 file not present")
    ev = pd.read_csv(EVENTS)
    ev = ev[ev.source == "UCDP_T3"]
    sys.path.insert(0, os.path.join(ROOT, "scripts", "build"))
    from state_system import cow_to_gw

    raw = pd.read_csv(t3_raw).rename(columns={"supporter_gwno": "initiator_gwno", "host_gwno": "target_gwno"})
    raw = raw.dropna(subset=["initiator_gwno", "target_gwno"])
    for col in ("initiator_gwno", "target_gwno"):  # same code repair as the builder
        raw[col] = [cow_to_gw(int(c), int(y)) for c, y in zip(raw[col], raw["year"], strict=True)]
    raw["event_ref"] = "UCDP:" + raw["conflict_id"].astype(str)
    j = ev.merge(
        raw[["year", "event_ref", "initiator_gwno", "target_gwno", "side_backed"]],
        on=["year", "event_ref", "initiator_gwno", "target_gwno"], how="left",
    )
    assert j["side_backed"].notna().all(), "a UCDP_T3 event has no source row"
    assert (j["side_backed"] == "side_b").all()


@needs_grid
def test_feature_grid_keeps_the_state_table_rows(grid, states):
    assert len(grid) == len(states)
    assert not grid.duplicated(KEY).any()


@needs_grid
def test_capability_shares_sum_to_one(grid):
    assert np.allclose(grid["c_t_ab"] + grid["c_t_ba"], 1.0)
    obs = grid[grid["cinc_observed"]]
    assert np.allclose(obs["c_t_ab"], obs["cinc_b"] / (obs["cinc_a"] + obs["cinc_b"]))
    assert grid["c_t_ab"].between(0, 1).all()


@needs_grid
def test_capability_shares_mirror_across_directions(grid):
    j = _reverse(grid, ["c_t_ab", "c_t_ba"])
    assert np.allclose(j["c_t_ab"], j["c_t_ba_rev"])


@needs_grid
def test_geography_is_symmetric(grid):
    j = _reverse(grid, ["contiguity_xi"])
    assert np.allclose(j["contiguity_xi"], j["contiguity_xi_rev"])


@needs_grid
def test_symmetric_trade_fields_match_across_directions(grid):
    cols = ["trade_surface_norm_ab", "mutual_trade_dependence_ab"]
    j = _reverse(grid, cols)
    for c in cols:
        assert np.allclose(j[c], j[f"{c}_rev"])


@needs_grid
def test_distance_is_symmetric(grid):
    j = _reverse(grid, ["distance_km"])
    assert np.allclose(j["distance_km"], j["distance_km_rev"])


@needs_grid
def test_rivalry_mirrors_across_directions(grid):
    j = _reverse(grid, ["rivalry_omega", "rivalry_omega_b"])
    assert np.allclose(j["rivalry_omega_b"], j["rivalry_omega_rev"])


@needs_states
def test_coverage_bitmask_marks_pre1989_t2_unobserved(states):
    pre = states[states["year"] < 1989]["unobserved_tiers"]
    post = states[states["year"] >= 1989]["unobserved_tiers"]
    assert (pre == (1 << 2)).all()
    assert (post == 0).all()


@needs_states
def test_t1_union_sources_contribute(states):
    ev_path = os.path.join(PROCESSED, "dyad_events.csv")
    events = pd.read_csv(ev_path, usecols=["source", "uiw_tier"])
    t1_sources = set(events.loc[events["uiw_tier"] == 1, "source"].unique())
    assert {"MID5", "EUSANCT_THREAT", "TIES", "ICB", "DIPREP"}.issubset(t1_sources)
    assert (states["uiw_tier"] == 1).sum() > 0

