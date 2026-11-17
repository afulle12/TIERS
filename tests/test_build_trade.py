"""Tests for the trade builder's symmetry guarantees (proposal section 2.7)."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "build"))

import build_trade_interdependence as bti  # noqa: E402

SHARED = ["trade_surface_ab", "trade_surface_norm_ab", "mutual_trade_dependence_ab", "trade_shock_ab"]


def _flows(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["year", "initiator_gwno", "target_gwno", "exports_a_to_b"])


def _mirror(df: pd.DataFrame) -> pd.DataFrame:
    key = ["year", "initiator_gwno", "target_gwno"]
    rev = df.rename(columns={"initiator_gwno": "target_gwno", "target_gwno": "initiator_gwno"})
    return df.merge(rev, on=key, how="left", suffixes=("", "_rev"))


def test_one_way_flow_gets_both_directions():
    # 1 exports to 2; 2 reports nothing back. 1 and 3 trade both ways.
    flow = _flows([(2000, 1, 2, 100.0), (2000, 1, 3, 50.0), (2000, 3, 1, 70.0)])
    out = bti._complete_trade_frame(flow, "BACI", "thousand_current_usd", 0)
    assert len(out) == 4
    back = out[(out.initiator_gwno == 2) & (out.target_gwno == 1)].iloc[0]
    assert back.exports_a_to_b == 0.0 and back.exports_b_to_a == 100.0
    m = _mirror(out)
    assert m["trade_source_rev"].notna().all()
    for col in ("trade_surface_ab", "mutual_trade_dependence_ab", "trade_shock_ab"):
        assert np.allclose(m[col], m[f"{col}_rev"])
    assert np.allclose(m["dep_a_on_b"], m["dep_b_on_a_rev"])
    assert np.allclose(m["exports_a_to_b"], m["exports_b_to_a_rev"])


def test_source_is_chosen_per_pair_not_per_direction():
    # BACI has only 1 -> 2 for the pair; TRADHIST has both directions.
    baci = bti._complete_trade_frame(_flows([(2000, 1, 2, 100.0)]), "BACI", "usd", bti.BACI_SOURCE_RANK)
    hist = bti._complete_trade_frame(
        _flows([(2000, 1, 2, 9.0), (2000, 2, 1, 4.0), (2000, 1, 3, 2.0)]), "TRADHIST", "gbp",
        bti.TRADHIST_SOURCE_RANK,
    )
    out = bti.combine_sources([hist, baci])
    pair = out[out.initiator_gwno.isin([1, 2]) & out.target_gwno.isin([1, 2])]
    assert set(pair.trade_source) == {"BACI"} and len(pair) == 2
    other = out[out.initiator_gwno.isin([1, 3]) & out.target_gwno.isin([1, 3])]
    assert set(other.trade_source) == {"TRADHIST"} and len(other) == 2
    m = _mirror(out)
    for col in SHARED:
        assert np.allclose(m[col], m[f"{col}_rev"])


def test_reported_totals_are_one_value_per_country():
    # TRADHIST-style totals: country 2's totals are missing where it is the origin.
    flow = pd.DataFrame({
        "year": [1950, 1950], "initiator_gwno": [1, 2], "target_gwno": [2, 1],
        "exports_a_to_b": [10.0, 5.0],
        "total_exports_a": [100.0, np.nan], "total_imports_a": [80.0, np.nan],
        "total_exports_b": [40.0, 100.0], "total_imports_b": [60.0, 80.0],
    })
    out = bti._complete_trade_frame(flow, "TRADHIST", "gbp", 1, has_totals=True)
    m = _mirror(out)
    assert np.allclose(m["total_trade_a"], m["total_trade_b_rev"])
    assert np.allclose(m["mutual_trade_dependence_ab"], m["mutual_trade_dependence_ab_rev"])
    assert (out["total_trade_a"] > 0).all()
