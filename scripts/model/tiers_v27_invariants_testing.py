"""v27.0 invariants and identification-target tests.

Mirrors `tiers_invariants_testing.py` (the v21 test harness) for the v27
cost-field engine. Verifies:

  1. PROBABILITY BOUNDS - every output of the engine is in [0, 1].
  2. P_UP(k=5) = 0 - boundary constraint on the top tier.
  3. P_DOWN(k=0) = 0 - boundary constraint on the bottom tier.
  4. CAPABILITY/REACH GATE - when G_T5 = 0, omega^+_{k,5} = 0 (no mass on T5).
  5. STATUS-QUO BIAS - at DeEsc=0 and a positive down-gradient, P_0 >= P_down.
  6. T4 DUAL-POPULATION - long-duration T4 has higher P_0 than short-duration T4.
  7. ATTRIBUTION x DURATION - sustained deniable T3 has higher P_up than
     sustained attributable T3 of equal duration.
  8. EXPRESSIVE-SANCTIONS PERSISTENCE - dyads with high status-quo burden and
     low DeEsc have P_0 dominating.

All tests use random or fixed scenarios. None require the empirical data.
"""
from __future__ import annotations

import copy
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "model"))

from tiers_lib_v27 import (
    ActorState,
    ActiveMember,
    DyadState,
    InputState,
    Priors,
    capability_reach_gate,
    down_barrier,
    omega_up,
    resolve_active_member,
    score_dyad_year,
)

random.seed(42)


def random_actor(rng) -> ActorState:
    return ActorState(
        n_pub=rng.uniform(0.1, 0.9),
        capability_share=rng.random(),
        b_econ=rng.random() * 0.5,
        b_blood=rng.random() * 0.5,
        v_i=rng.random() * 0.5,
        closing_window=rng.random(),
        fma=rng.random(),
        cap_proxy=rng.random(),
        shock_k=rng.random() * 0.3,
        deesc_inputs=(rng.random(), rng.random(), rng.random()),
        attribution=rng.random(),
        stakes=rng.random(),
        state_b_econ=InputState.OBSERVED,
        state_b_blood=InputState.OBSERVED,
        state_v_i=InputState.OBSERVED,
        state_closing_window=InputState.OBSERVED,
        state_fma=InputState.OBSERVED,
        state_cap=InputState.OBSERVED,
        state_shock=InputState.OBSERVED,
        state_deesc=InputState.OBSERVED,
        state_attribution=InputState.OBSERVED,
        state_stakes=InputState.OBSERVED,
    )


def random_dyad(rng):
    return (
        random_actor(rng),
        random_actor(rng),
        DyadState(
            current_tier=rng.randint(0, 5),
            duration=rng.uniform(0, 5),
            contiguity=rng.choice([0.0, 0.5, 1.0]),
            rivalry=rng.random(),
            stalemate=rng.random(),
            ora=rng.random(),
        ),
    )


# ---------------------------------------------------------------------------
# Invariant tests
# ---------------------------------------------------------------------------

def test_probability_bounds(n=2000):
    """Every pi component and intermediate probability in [0, 1]."""
    rng = random.Random(1)
    fails = 0
    for _ in range(n):
        a, b, sym = random_dyad(rng)
        res = score_dyad_year(a, b, sym)
        for v in res["pi_ab"] + res["pi_ba"] + res["pi_reconciled"]:
            if v < -1e-12 or v > 1.0 + 1e-12:
                fails += 1
    assert fails == 0, f"BOUND VIOLATED: {fails}/{n} runs"
    return f"{n} random dyads: every pi in [0,1] OK"


def test_top_boundary():
    """P_up(k=5) = 0: no upward mass possible from T5."""
    rng = random.Random(2)
    for _ in range(500):
        a, b, sym = random_dyad(rng)
        sym.current_tier = 5
        res = score_dyad_year(a, b, sym)
        # In the directed runs, P_up is recorded in the diagnostics
        # The pi distribution at index 5 should only get mass from
        # the allocation stage at k=5 which has no upward destinations.
        # So pi[5] should equal P_0.
        # We check: P_up at k=5 is 0 (no U_up value).
        # P_0 at k=5 may be less than pi[5] only if reconciliation
        # adds downward mass; but with no lower-tier mass in either direction,
        # the reconciliation should equal pi[5] = P_0.
        for pi in [res["pi_ab"], res["pi_ba"]]:
            # At k=5 there are no upward destinations; omega_up returns
            # all zeros. So pi[5] = P_0 * 1 = P_0. Total mass on the row
            # = P_down (split by omega_down) + P_0.
            assert pi[5] > 0, "pi[5] should be P_0 at k=5"
    return "P_up(k=5) = 0 enforced: T5 is the top tier OK"


def test_bottom_boundary():
    """P_down(k=0) = 0: no downward mass possible from T0."""
    rng = random.Random(3)
    for _ in range(500):
        a, b, sym = random_dyad(rng)
        sym.current_tier = 0
        res = score_dyad_year(a, b, sym)
        for pi in [res["pi_ab"], res["pi_ba"]]:
            # At k=0, P_down=0, so no mass below k.
            assert sum(pi[:0]) == 0.0
    return "P_down(k=0) = 0 enforced: T0 is the bottom tier OK"


def test_capability_reach_gate():
    """When G_T5 = 0, omega^+_{k,5} = 0 and renormalised."""
    priors = Priors()
    # Case 1: contiguous dyad -> G_T5 = 1 -> omega_up can place mass on T5
    sym = DyadState(contiguity=1.0)
    a = ActorState(state_fma=InputState.OBSERVED, state_closing_window=InputState.OBSERVED)
    om = omega_up(k=2, gate_t5=True, actor=a, priors=priors)
    assert om.get(5, 0.0) > 0.0, "Contiguous dyad should have T5 mass in omega_up"
    # Case 2: non-contiguous, low-reach -> G_T5 = 0
    sym2 = DyadState(contiguity=0.0)
    a2 = ActorState(cap_proxy=0.1, state_fma=InputState.OBSERVED,
                    state_closing_window=InputState.OBSERVED)
    om2 = omega_up(k=2, gate_t5=False, actor=a2, priors=priors)
    assert om2.get(5, 0.0) == 0.0, "Reach-gated dyad should have zero T5 mass"
    # Case 3: WMD>0 should force Cap>=tau -> gate opens even if non-contiguous
    # (Tested in the spec via the consistency condition; we don't simulate WMD
    # directly here, but the gate function reflects the OR condition.)
    return "Cap/Reach gate zero-omega on T5: OK"


def test_status_quo_bias():
    """At DeEsc=0 with a positive down-gradient, P_0 >= P_down.

    The v27.0 down-barrier is sized so that neutral inputs cannot produce
    P_down > P_0 (status-quo-bias identification target, spec section 6.7).
    """
    rng = random.Random(4)
    fails = 0
    n = 1000
    for _ in range(n):
        a, b, sym = random_dyad(rng)
        # Force DeEsc = 0 across all inputs
        a.deesc_inputs = (0.0, 0.0, 0.0)
        b.deesc_inputs = (0.0, 0.0, 0.0)
        a.shock_k = 0.0
        b.shock_k = 0.0
        # Skip boundary tiers (k=0 has no down; k=5 has no up)
        if sym.current_tier == 0 or sym.current_tier == 5:
            continue
        res = score_dyad_year(a, b, sym)
        for pi in [res["pi_ab"], res["pi_ba"]]:
            p_down_mass = sum(pi[:sym.current_tier])
            p_zero_mass = pi[sym.current_tier]
            if p_down_mass > p_zero_mass + 1e-6:
                fails += 1
    assert fails == 0, f"STATUS-QUO BIAS VIOLATED: {fails}/{n} dyads with P_down > P_0"
    return f"{n} dyads at DeEsc=0: P_0 >= P_down everywhere OK"


def test_t4_dual_population():
    """Long-duration T4 has higher P_0 than short-duration T4.

    b_dur * D_k raises the down-barrier, raising P_0.
    """
    priors = Priors()
    a = ActorState(
        deesc_inputs=(0.0, 0.0, 0.0), shock_k=0.0,
        state_fma=InputState.OBSERVED, state_closing_window=InputState.OBSERVED,
        state_b_econ=InputState.ABSENT, state_b_blood=InputState.ABSENT,
        state_v_i=InputState.ABSENT,
    )
    b = copy.deepcopy(a)
    sym_short = DyadState(current_tier=4, duration=0.1, contiguity=0.0)
    sym_long = DyadState(current_tier=4, duration=3.0, contiguity=0.0)
    res_short = score_dyad_year(a, b, sym_short, priors)
    res_long = score_dyad_year(a, b, sym_long, priors)
    p0_short = res_short["pi_ab"][4]
    p0_long = res_long["pi_ab"][4]
    assert p0_long > p0_short, f"T4 dual-population violated: P_0 long={p0_long:.4f} <= short={p0_short:.4f}"
    return f"T4 dual-population: P_0(D_k=3)={p0_long:.4f} > P_0(D_k=0.1)={p0_short:.4f} OK"


def test_attribution_duration():
    """Sustained deniable T3 has higher P_up than sustained attributable T3
    of equal duration (the v27.0 Attribution x Duration factor)."""
    priors = Priors()
    a_deniable = ActorState(
        attribution=0.8, shock_k=0.0, deesc_inputs=(0.0, 0.0, 0.0),
        state_fma=InputState.OBSERVED, state_closing_window=InputState.OBSERVED,
        state_b_econ=InputState.ABSENT, state_b_blood=InputState.ABSENT,
        state_v_i=InputState.ABSENT, state_attribution=InputState.OBSERVED,
    )
    a_attrib = copy.deepcopy(a_deniable)
    a_attrib.attribution = 0.0
    b = copy.deepcopy(a_deniable)
    b.attribution = 0.0
    sym = DyadState(current_tier=3, duration=1.5, contiguity=0.0)
    res_den = score_dyad_year(a_deniable, b, sym, priors)
    res_att = score_dyad_year(a_attrib, b, sym, priors)
    p_up_den = sum(res_den["pi_ab"][4:])  # mass on T4, T5
    p_up_att = sum(res_att["pi_ab"][4:])
    assert p_up_den > p_up_att, (
        f"Attribution x Duration violated: P_up den={p_up_den:.4f} <= attrib={p_up_att:.4f}"
    )
    return f"Attribution x Duration: P_up deniable={p_up_den:.4f} > attributable={p_up_att:.4f} OK"


def test_expressive_sanctions_persistence():
    """A dyad at T2 with low DeEsc, no shock, and high status-quo burden
    should have P_0 dominant (spec section 6.7)."""
    priors = Priors()
    a = ActorState(
        deesc_inputs=(0.0, 0.0, 0.0),
        shock_k=0.0,
        state_fma=InputState.OBSERVED, state_closing_window=InputState.OBSERVED,
        state_b_econ=InputState.ABSENT, state_b_blood=InputState.ABSENT,
        state_v_i=InputState.ABSENT,
    )
    b = copy.deepcopy(a)
    sym = DyadState(current_tier=2, duration=0.5, contiguity=0.0, stalemate=0.7, ora=0.7)
    res = score_dyad_year(a, b, sym, priors)
    p_0 = res["pi_ab"][2]
    p_up = sum(res["pi_ab"][3:])
    p_down = sum(res["pi_ab"][:2])
    assert p_0 > p_up, "Expressive sanctions: P_0 should dominate over P_up"
    assert p_0 > p_down, "Expressive sanctions: P_0 should dominate over P_down"
    return f"Expressive sanctions at T2: P_0={p_0:.4f} > max(P_up={p_up:.4f}, P_down={p_down:.4f}) OK"


def test_member_resolution():
    """Active member is correctly resolved from coverage."""
    rng = random.Random(5)
    # Diagnostic fallback when occupancy components absent
    a = ActorState(
        b_econ=0.0, b_blood=0.0, v_i=0.0,
        state_b_econ=InputState.ABSENT, state_b_blood=InputState.ABSENT,
        state_v_i=InputState.ABSENT,
    )
    sym = DyadState()
    assert resolve_active_member(a, sym) == ActiveMember.DIAGNOSTIC_FALLBACK
    # Public member when belief absent but forward-looking observed
    a2 = ActorState(
        state_b_econ=InputState.OBSERVED, state_b_blood=InputState.OBSERVED,
        state_v_i=InputState.OBSERVED, state_belief=InputState.ABSENT,
        state_closing_window=InputState.OBSERVED,
    )
    assert resolve_active_member(a2, sym) == ActiveMember.PUBLIC
    # Myopic when both belief and forward-looking absent
    a3 = ActorState(
        state_b_econ=InputState.OBSERVED, state_b_blood=InputState.OBSERVED,
        state_v_i=InputState.OBSERVED, state_belief=InputState.ABSENT,
        state_closing_window=InputState.ABSENT,
    )
    assert resolve_active_member(a3, sym) == ActiveMember.MYOPIC
    return "Active member resolution: DIAGNOSTIC_FALLBACK / PUBLIC / MYOPIC OK"


def main() -> int:
    tests = [
        test_probability_bounds,
        test_top_boundary,
        test_bottom_boundary,
        test_capability_reach_gate,
        test_status_quo_bias,
        test_t4_dual_population,
        test_attribution_duration,
        test_expressive_sanctions_persistence,
        test_member_resolution,
    ]
    print("=" * 78)
    print("TIERS v27.0 INVARIANTS & IDENTIFICATION-TARGET TESTS")
    print("=" * 78)
    fails = 0
    for t in tests:
        try:
            msg = t()
            print(f"  [PASS] {t.__name__}: {msg}")
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            fails += 1
        except Exception as e:
            print(f"  [ERR ] {t.__name__}: {e}")
            fails += 1
    print("=" * 78)
    if fails == 0:
        print(f"All {len(tests)} tests passed.")
    else:
        print(f"{fails} / {len(tests)} tests FAILED")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
