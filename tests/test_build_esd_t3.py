"""Rules for turning UCDP ESD triad-years into directed T3 events."""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "build"))

import build_esd_t3 as besd  # noqa: E402

GW = {"Government of A": 100, "Government of B": 200, "Government of S": 300}


def _row(**kw) -> dict:
    base = {
        "year": 1985, "actor_name": "Rebels", "oppo_name": "Government of A", "ext_name": "Government of S",
        "conflict_id": 1, "dyad_id": 1, "civil": 1, "ext_sup": 1, "ext_nonstate": 0, "ext_elements": 0,
        "ext_alleged": 0, "ext_coalition": 0, "ext_bothsides": 0,
        **{f"ext_{t}": 0 for t in besd.SUPPORT_TYPES},
        "ext_w": 1,
    }
    base.update(kw)
    return base


def _events(*rows: dict) -> pd.DataFrame:
    return besd.directed_support(pd.DataFrame(list(rows)), GW)[0]


def test_support_to_rebels_targets_the_government_they_fight():
    ev = _events(_row())
    assert ev[["supporter_gwno", "target_gwno"]].values.tolist() == [[300, 100]]
    assert ev["attribution"].tolist() == [0.5]


def test_support_to_a_government_against_rebels_is_not_hostile():
    assert _events(_row(actor_name="Government of A", oppo_name="Rebels")).empty


def test_support_to_a_state_at_war_targets_its_opponent():
    ev = _events(_row(actor_name="Government of B", oppo_name="Government of A", civil=0))
    assert ev[["supporter_gwno", "target_gwno"]].values.tolist() == [[300, 100]]


def test_alleged_elements_and_nonstate_support_are_dropped():
    assert _events(_row(ext_alleged=1)).empty
    assert _events(_row(ext_elements=1)).empty
    assert _events(_row(ext_nonstate=1)).empty
    assert _events(_row(ext_sup=0)).empty


def test_only_material_support_types_qualify():
    def only(t: str) -> dict:
        return _row(**{"ext_w": 0, f"ext_{t}": 1})

    for t in ("m", "i", "l", "o", "u"):
        assert _events(only(t)).empty, t
    for t in besd.MATERIAL_TYPES:
        assert len(_events(only(t))) == 1, t


def test_troops_raise_the_attribution_prior():
    assert _events(_row(ext_x=1))["attribution"].tolist() == [0.7]


def test_self_and_unmapped_pairs_are_dropped():
    assert _events(_row(ext_name="Government of A")).empty
    ev, unmapped = besd.directed_support(pd.DataFrame([_row(ext_name="Government of Z")]), GW)
    assert ev.empty and len(unmapped) == 1


def test_government_names_map_from_primary_and_secondary_sides():
    dy = pd.DataFrame({
        "side_a": ["Government of A", "Government of B"], "gwno_a": ["100", "200"],
        "side_b": ["Rebels", "Government of A"], "gwno_b": ["", "100"],
        "side_a_2nd": ["Government of S, Government of T", ""], "gwno_a_2nd": ["300, 400", ""],
        "side_b_2nd": ["", ""], "gwno_b_2nd": ["", ""],
    })
    gw = besd.government_gw_map(dy)
    assert gw["Government of A"] == 100
    assert gw["Government of T"] == 400
    assert gw["Government of East Germany"] == 265
