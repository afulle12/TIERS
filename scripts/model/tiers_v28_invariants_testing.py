"""Invariant and sign-target tests for the TIERS v28.0 engine."""
from __future__ import annotations

import copy
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from tiers_lib_v27 import ActorState, DyadState, InputState
from tiers_lib_v28 import adjacent_hazard, score_dyad_year, Priors


def actor(**kwargs) -> ActorState:
    a = ActorState(
        n_pub=0.5,
        capability_share=0.5,
        closing_window=0.5,
        fma=0.5,
        cap_proxy=0.4,
        attribution=0.2,
        stakes=0.5,
        state_integration=InputState.OBSERVED,
        state_b_econ=InputState.ABSENT,
        state_b_blood=InputState.ABSENT,
        state_v_i=InputState.ABSENT,
    )
    a.trade_surface_norm = kwargs.pop("trade_surface_norm", 0.5)
    a.dep_on_target = kwargs.pop("dep_on_target", 0.05)
    a.mutual_trade_dependence = kwargs.pop("mutual_trade_dependence", 0.05)
    a.import_leverage = kwargs.pop("import_leverage", 0.0)
    a.export_leverage = kwargs.pop("export_leverage", 0.0)
    a.trade_leverage = kwargs.pop("trade_leverage", 0.0)
    for k, v in kwargs.items():
        setattr(a, k, v)
    return a


def test_probability_bounds(n=1000):
    rng = random.Random(28)
    for _ in range(n):
        a = actor(
            trade_surface_norm=rng.random(),
            mutual_trade_dependence=rng.random() * 0.2,
            trade_leverage=rng.random() * 0.2,
            import_leverage=rng.random() * 0.2,
            export_leverage=rng.random() * 0.2,
        )
        b = copy.deepcopy(a)
        sym = DyadState(current_tier=rng.randint(0, 5), duration=rng.random() * 5, contiguity=rng.choice([0, 0.5, 1]), rivalry=rng.random())
        res = score_dyad_year(a, b, sym)
        for p in res["pi_ab"] + res["pi_ba"] + res["pi_reconciled"]:
            assert -1e-12 <= p <= 1.0 + 1e-12
        assert abs(sum(res["pi_reconciled"]) - 1.0) < 1e-9
    return f"{n} v28 random dyads: probabilities bounded and normalized"


def test_leverage_raises_t1_t2():
    priors = Priors()
    low = actor(trade_leverage=0.0, import_leverage=0.0, export_leverage=0.0)
    high = actor(trade_leverage=0.4, import_leverage=0.3, export_leverage=0.2)
    target = actor()
    sym = DyadState(current_tier=1, rivalry=0.2)
    h_low = adjacent_hazard(1, low, target, sym, True, priors)
    h_high = adjacent_hazard(1, high, target, sym, True, priors)
    assert h_high > h_low
    return f"T1->T2 leverage sign: {h_high:.4f} > {h_low:.4f}"


def test_mutual_dependence_suppresses_force():
    priors = Priors()
    low = actor(mutual_trade_dependence=0.0)
    high = actor(mutual_trade_dependence=0.3)
    target = actor()
    sym = DyadState(current_tier=3, rivalry=0.4, contiguity=1.0, duration=2.0)
    h_low = adjacent_hazard(3, low, target, sym, True, priors)
    h_high = adjacent_hazard(3, high, target, sym, True, priors)
    assert h_low > h_high
    return f"T3->T4 mutual-dependence sign: {h_low:.4f} > {h_high:.4f}"


def test_t5_gate_blocks_nonreachable():
    a = actor(cap_proxy=0.0)
    b = actor(cap_proxy=0.0)
    sym = DyadState(current_tier=4, contiguity=0.0)
    res = score_dyad_year(a, b, sym)
    assert res["pi_reconciled"][5] == 0.0
    return "Capability/Reach gate blocks T5 mass for nonreachable T4 dyads"


def main() -> int:
    tests = [
        test_probability_bounds,
        test_leverage_raises_t1_t2,
        test_mutual_dependence_suppresses_force,
        test_t5_gate_blocks_nonreachable,
    ]
    print("TIERS v28 invariant tests")
    print("=" * 60)
    for test in tests:
        print(f"PASS: {test()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
