"""
Systematic test harness for the dyadic war model.

LEVEL 1 — Invariants (must hold for any input)
LEVEL 2 — Local sensitivity (tornado at a baseline)
LEVEL 3 — Global / Monte Carlo (joint parameter uncertainty)
LEVEL 4 — Rank-order validity (Spearman vs. expert ordering)
"""

import copy
import random
import math
from eirene_lib import State, p_init, p_direct, p_join, dyadic, PARAM_NAMES

random.seed(42)


# ============================================================================
# LEVEL 1 — INVARIANTS
# ============================================================================

def random_state(rng):
    """Random plausible state."""
    return State(
        name="rand",
        N_pub=rng.random(), beta=rng.uniform(0.005, 0.05),
        dP=rng.random(), R_d=rng.random(), A_div=rng.random(), P_v=rng.random(),
        V_p=rng.random(), V_t=rng.random(),
        C_T=rng.random(), W_v=rng.random(),
        B=rng.random(), R_h=rng.random(), I_s=rng.random(),
        I_a=rng.random(), C_p=rng.random(), I_i=rng.random(),
        C_i=rng.random(),
        C_d_sup=rng.random(), C_d_opp=rng.random(),
        E_n_sup=rng.random(), E_n_opp=rng.random(),
        S_p_sup=rng.random(), S_p_opp=rng.random(),
    )


def test_bounds():
    """All output probabilities ∈ [0,1] for any plausible input."""
    rng = random.Random(1)
    for _ in range(5000):
        A, B = random_state(rng), random_state(rng)
        W_sev = rng.random()
        r = dyadic(A, B, W_sev, W_sev)
        for k, v in r.items():
            assert 0.0 <= v <= 1.0 + 1e-12, f"BOUND VIOLATED {k}={v}"
    return "5000 random dyads: every probability in [0,1] ✓"


def test_zero_collapse():
    """Zero-everything state pair gives zero everything."""
    A = State("A0"); B = State("B0")
    # Default has C_T=0.5 and I_a=0.5,C_p=0.3,I_i=0.3 — but no motive/opp/spark
    r = dyadic(A, B)
    assert r["P_dyad"] == 0.0 and r["P_co"] == 0.0
    return "Zero motive/opportunity/spark → P_dyad = P_co = 0 ✓"


def test_path2_silent_without_war():
    """Path 2 must be 0 when neither side is in a prior war."""
    rng = random.Random(2)
    for _ in range(1000):
        A, B = random_state(rng), random_state(rng)
        r = dyadic(A, B, W_sev_A=0.0, W_sev_B=0.0)
        assert r["pjoAB"] == 0.0 and r["pjoBA"] == 0.0
        assert r["pjsAB"] == 0.0 and r["pjsBA"] == 0.0
    return "1000 dyads with W_sev=0 → all Path 2 terms = 0 ✓"


def test_npub_direction():
    """Path 1 monotone DECREASING in N_pub (peaceful public suppresses initiation)."""
    rng = random.Random(3)
    fails = 0
    trials = 1000
    for _ in range(trials):
        A, B = random_state(rng), random_state(rng)
        prev = None
        for npub in [0.0, 0.25, 0.5, 0.75, 1.0]:
            A2 = copy.deepcopy(A); A2.N_pub = npub
            p = p_direct(A2, B)
            if prev is not None and p > prev + 1e-12:
                fails += 1
                break
            prev = p
    assert fails == 0, f"{fails}/{trials} dyads non-monotone in N_pub"
    return f"P_direct strictly non-increasing in N_pub across {trials} dyads ✓"


def test_motive_monotone():
    """P_init monotone NON-DECREASING in dP, R_d, A_div, P_v individually."""
    rng = random.Random(4)
    for var in ["dP", "R_d", "A_div", "P_v"]:
        for _ in range(500):
            A, B = random_state(rng), random_state(rng)
            prev = None
            for val in [0.0, 0.25, 0.5, 0.75, 1.0]:
                A2 = copy.deepcopy(A); setattr(A2, var, val)
                p = p_init(A2, B)
                if prev is not None and p < prev - 1e-12:
                    raise AssertionError(f"non-monotone in {var}")
                prev = p
    return "P_init non-decreasing in each motive component ✓"


def test_opportunity_monotone_in_target_defense():
    """Higher C_T (target's defense) should non-increase P_init."""
    rng = random.Random(5)
    for _ in range(500):
        A, B = random_state(rng), random_state(rng)
        prev = None
        for ct in [0.0, 0.25, 0.5, 0.75, 1.0]:
            B2 = copy.deepcopy(B); B2.C_T = ct
            p = p_init(A, B2)
            if prev is not None and p > prev + 1e-12:
                raise AssertionError(f"non-monotone in C_T: {prev} -> {p}")
            prev = p
    return "P_init non-increasing in target's C_T ✓"


def test_cp_override():
    """When V_t > V_p, friction should jump because C*_p = 1."""
    A = State("A", beta=0.02, dP=0.5, R_h=0.5, I_s=0.5, V_p=0.3, C_T=0.5,
              I_a=0.2, C_p=0.0, I_i=0.0)
    B = State("B")
    A_below = copy.deepcopy(A); A_below.V_t = 0.2  # V_t < V_p, override OFF
    A_above = copy.deepcopy(A); A_above.V_t = 0.4  # V_t > V_p, override ON
    p_below = p_init(A_below, B)
    p_above = p_init(A_above, B)
    # Override forces C*_p=1 → friction term jumps to 1, raising p_init
    # Even though V_t went up only slightly, p_above should jump significantly
    assert p_above > p_below * 1.5, f"override didn't fire: {p_below} -> {p_above}"
    return f"V_t > V_p triggers C*_p=1 override (p {p_below:.5f} → {p_above:.5f}) ✓"


def test_symmetry():
    """If A and B have identical params, P_direct(A->B) = P_direct(B->A)."""
    rng = random.Random(6)
    for _ in range(500):
        A = random_state(rng)
        B = copy.deepcopy(A); B.name = "B"
        # C_T appears in opportunity using B's C_T for A's calc and vice versa,
        # so identical params must give identical directional probs
        assert abs(p_direct(A, B) - p_direct(B, A)) < 1e-12
    return "Identical-parameter dyads are perfectly symmetric ✓"


def test_treaty_betrayal_penalty():
    """Allying with B's enemies (C_d_opp > 0.5) should suppress T_sup via C_b."""
    A_clean = State("A", N_pub=0.9, C_i=0.5, C_d_sup=0.8, C_d_opp=0.0)
    A_traitor = copy.deepcopy(A_clean); A_traitor.C_d_opp = 0.6  # also allied to enemies
    from eirene_lib import treaty_triggers
    T_sup_clean, _ = treaty_triggers(A_clean)
    T_sup_traitor, _ = treaty_triggers(A_traitor)
    assert T_sup_traitor < T_sup_clean, "betrayal penalty did not suppress T_sup"
    return f"Betrayal penalty (C_b=0.95): T_sup {T_sup_clean:.3f} → {T_sup_traitor:.3f} ✓"


def run_level_1():
    print("=" * 78)
    print("LEVEL 1 — INVARIANTS")
    print("=" * 78)
    tests = [
        test_bounds,
        test_zero_collapse,
        test_path2_silent_without_war,
        test_npub_direction,
        test_motive_monotone,
        test_opportunity_monotone_in_target_defense,
        test_cp_override,
        test_symmetry,
        test_treaty_betrayal_penalty,
    ]
    for t in tests:
        try:
            msg = t()
            print(f"  {msg}")
        except AssertionError as e:
            print(f"  FAIL [{t.__name__}]: {e}")
    print()


# ============================================================================
# LEVEL 2 — LOCAL SENSITIVITY (tornado)
# ============================================================================

def baseline_state():
    """A moderately tense rivalry baseline."""
    return State(
        name="baseline_aggressor",
        N_pub=0.7, beta=0.02,
        dP=0.4, R_d=0.4, A_div=0.2, P_v=0.1,
        V_p=0.3, V_t=0.2, C_T=0.6, W_v=0.2,
        B=0.4, R_h=0.5, I_s=0.4,
        I_a=0.5, C_p=0.4, I_i=0.5,
        C_i=0.6,
        C_d_sup=0.0, C_d_opp=0.3,
        E_n_sup=0.0, E_n_opp=0.2,
        S_p_sup=0.0, S_p_opp=0.3,
    )


def tornado_sensitivity():
    """For each parameter, vary across [0,1] (or beta range), measure P_direct range."""
    A = baseline_state()
    B = baseline_state(); B.name = "baseline_target"
    base = p_direct(A, B)
    rows = []
    for var in PARAM_NAMES:
        if var == "beta":
            lo_val, hi_val = 0.005, 0.05
        else:
            lo_val, hi_val = 0.0, 1.0
        A_lo = copy.deepcopy(A); setattr(A_lo, var, lo_val)
        A_hi = copy.deepcopy(A); setattr(A_hi, var, hi_val)
        p_lo = p_direct(A_lo, B)
        p_hi = p_direct(A_hi, B)
        rng = abs(p_hi - p_lo)
        rows.append((var, p_lo, p_hi, rng))
    rows.sort(key=lambda r: -r[3])
    return base, rows


def run_level_2():
    print("=" * 78)
    print("LEVEL 2 — LOCAL SENSITIVITY (tornado on baseline rivalry)")
    print("=" * 78)
    base, rows = tornado_sensitivity()
    print(f"  Baseline P_direct = {base*100:.4f}%")
    print()
    print(f"  {'parameter':<12s} {'@low':>10s} {'@high':>10s} {'range':>10s}   bar")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10}   {'-'*40}")
    max_rng = max(r[3] for r in rows) or 1.0
    for var, lo, hi, rng in rows:
        bar = "#" * int(40 * rng / max_rng)
        print(f"  {var:<12s} {lo*100:>9.4f}% {hi*100:>9.4f}% {rng*100:>9.4f}%   {bar}")
    print()


# ============================================================================
# LEVEL 3 — GLOBAL / MONTE CARLO
# ============================================================================

def monte_carlo(n=20000):
    """Sample plausible parameter sets; report distribution of P_dyad."""
    rng = random.Random(7)
    samples = []
    for _ in range(n):
        A = random_state(rng); B = random_state(rng)
        r = dyadic(A, B, W_sev_A=rng.random(), W_sev_B=rng.random())
        samples.append(r["P_dyad"])
    samples.sort()
    pct = lambda p: samples[int(p * (n - 1))]
    return {
        "n": n,
        "mean": sum(samples) / n,
        "p50": pct(0.5),
        "p90": pct(0.9),
        "p99": pct(0.99),
        "p999": pct(0.999),
        "max": samples[-1],
        "frac_gt_1pct": sum(1 for s in samples if s > 0.01) / n,
        "frac_gt_5pct": sum(1 for s in samples if s > 0.05) / n,
    }


def run_level_3():
    print("=" * 78)
    print("LEVEL 3 — GLOBAL / MONTE CARLO (uniform priors over all parameters)")
    print("=" * 78)
    s = monte_carlo()
    print(f"  N = {s['n']:,} random dyad-years")
    print(f"  mean P_dyad      = {s['mean']*100:.3f}%")
    print(f"  median (p50)     = {s['p50']*100:.3f}%")
    print(f"  p90              = {s['p90']*100:.3f}%")
    print(f"  p99              = {s['p99']*100:.3f}%")
    print(f"  p99.9            = {s['p999']*100:.3f}%")
    print(f"  max              = {s['max']*100:.3f}%")
    print(f"  fraction > 1%    = {s['frac_gt_1pct']*100:.2f}%")
    print(f"  fraction > 5%    = {s['frac_gt_5pct']*100:.2f}%")
    print()
    print("  Empirical anchor: COW dyadic war onset rate is roughly")
    print("  0.05–0.2% per dyad-year averaged over all dyads. If this")
    print("  Monte Carlo's mean under uniform priors is much higher,")
    print("  beta needs downward calibration.")
    print()


# ============================================================================
# LEVEL 4 — RANK-ORDER VALIDITY
# ============================================================================

def make_dyads():
    """Curated dyads with expert-ordered war risk (low→high), 2024–25 priors."""
    def s(name, **kw):
        d = dict(N_pub=0.95, beta=0.02, C_T=0.7, I_a=0.3, C_p=0.2, I_i=0.2, C_i=0.6)
        d.update(kw); return State(name=name, **d)

    return [
        # rank 1 — irrelevant pair
        ("Chile-Mongolia",
         s("Chile"), s("Mongolia"), 0.0),
        # rank 2 — close allies
        ("Canada-Australia",
         s("Canada", C_d_sup=0.7, S_p_sup=0.4), s("Australia", C_d_sup=0.7, S_p_sup=0.4), 0.0),
        # rank 3 — close allies w/ tiny baseline tension
        ("UK-France",
         s("UK", R_h=0.05, V_p=0.05, C_d_sup=0.85), s("France", R_h=0.05, V_p=0.05, C_d_sup=0.85), 0.0),
        # rank 4 — allies but historic tension
        ("Greece-Turkey",
         s("Greece", N_pub=0.85, R_h=0.6, B=0.3, I_s=0.3, V_p=0.2, dP=0.2, R_d=0.3, I_i=0.6, C_d_opp=0.0),
         s("Turkey", N_pub=0.8, R_h=0.6, B=0.3, I_s=0.3, V_p=0.2, dP=0.3, R_d=0.4, I_i=0.6, C_d_opp=0.0), 0.0),
        # rank 5 — recurring rivals
        ("India-Pakistan",
         s("India", N_pub=0.8, dP=0.2, R_d=0.4, A_div=0.2, V_p=0.2, C_T=0.6, B=0.4, R_h=0.85, I_s=0.5, I_i=0.8, I_a=0.6, C_p=0.5),
         s("Pakistan", N_pub=0.75, dP=0.3, R_d=0.6, A_div=0.4, V_p=0.2, C_T=0.7, B=0.5, R_h=0.85, I_s=0.5, I_i=0.85, I_a=0.7, C_p=0.5),
         0.0),
        # rank 6 — proxy/cold war
        ("Iran-Israel",
         s("Iran", N_pub=0.65, dP=0.4, R_d=0.6, A_div=0.4, P_v=0.3, V_p=0.3, V_t=0.2, C_T=0.85, W_v=0.2, B=0.6, R_h=0.7, I_s=0.7, I_a=0.8, C_p=0.5, I_i=0.6),
         s("Israel", N_pub=0.55, dP=0.4, R_d=0.3, A_div=0.3, P_v=0.5, V_p=0.3, C_T=0.55, W_v=0.4, B=0.6, R_h=0.7, I_s=0.7, I_a=0.6, C_p=0.6, I_i=0.6),
         0.0),
        # rank 7 — armistice tension
        ("NK-SK",
         s("NK", N_pub=0.3, dP=0.5, R_d=0.8, A_div=0.5, P_v=0.4, V_p=0.3, V_t=0.5, C_T=0.85, W_v=0.2, B=0.6, R_h=0.9, I_s=0.6, I_a=0.85, C_p=0.6, I_i=0.85),
         s("SK", N_pub=0.85, R_d=0.1, V_p=0.05, C_T=0.55, B=0.2, R_h=0.9, I_s=0.4, I_a=0.7, C_p=0.4, I_i=0.85),
         0.0),
        # rank 8 — active high-intensity rivalry
        ("Russia-Ukraine 2022",
         s("Russia", N_pub=0.4, beta=0.04, dP=0.7, R_d=0.85, A_div=0.4, P_v=0.6, V_p=0.5, V_t=0.7, C_T=0.35, W_v=0.5, B=0.6, R_h=0.7, I_s=0.7, I_a=0.8, C_p=0.7, I_i=0.7),
         s("Ukraine", N_pub=0.7, R_d=0.4, B=0.3, R_h=0.7, I_s=0.5, I_a=0.6, C_p=0.5, I_i=0.7),
         0.0),
    ]


def spearman(x, y):
    """Spearman rho between two sequences."""
    def ranks(z):
        idx = sorted(range(len(z)), key=lambda i: z[i])
        r = [0] * len(z)
        for rk, i in enumerate(idx, 1):
            r[i] = rk
        return r
    rx, ry = ranks(x), ranks(y)
    n = len(x)
    num = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    return 1 - 6 * num / (n * (n ** 2 - 1))


def run_level_4():
    print("=" * 78)
    print("LEVEL 4 — RANK-ORDER VALIDITY (model rank vs. expert rank)")
    print("=" * 78)
    dyads = make_dyads()
    expert_rank = list(range(1, len(dyads) + 1))  # already in expert-ordered list
    model_p = [dyadic(A, B)["P_dyad"] for (_, A, B, _) in dyads]
    print(f"  {'expert':>6s}  {'dyad':<22s} {'P_dyad/yr':>12s}")
    for i, (name, A, B, _) in enumerate(dyads):
        print(f"  {expert_rank[i]:>6d}  {name:<22s} {model_p[i]*100:>11.4f}%")
    rho = spearman(expert_rank, model_p)
    print()
    print(f"  Spearman rho (expert order vs. model output) = {rho:+.3f}")
    print(f"  (rho = +1.000 means model perfectly recovers expert ordering)")
    print()


# ============================================================================
# LEVEL 5 sketch
# ============================================================================

def level_5_notes():
    print("=" * 78)
    print("LEVEL 5 — PREDICTIVE CALIBRATION (sketch — needs historical data)")
    print("=" * 78)
    notes = """
  Required inputs:
    • COW MID dataset, 1816–2014 (or successors): 200,000+ dyad-years,
      labelled with war onset / no onset.
    • Per-dyad-year coding of all 23 model parameters. Many can be
      proxied from existing scholarly indices (e.g. CINC for capability,
      Polity V for regime type, ICOW for territorial claims, ATOP for
      treaty depth, COW Trade for opportunity costs).

  Procedure:
    1. Time-split: fit beta and any free hyperparameters on 1816–1945,
       freeze, then evaluate 1946–2014 out-of-sample.
    2. Compute Brier score for annual war-onset prediction.
       Compare against three baselines:
         (a) climatology (constant base rate),
         (b) logistic regression on standard COW covariates,
         (c) Bremer (1992) dangerous-dyad model.
    3. Reliability diagram: bin predicted probabilities into deciles,
       plot empirical onset frequency in each bin. A well-calibrated
       model lies on the 45-degree line.
    4. Discrimination: ROC-AUC for war/no-war classification.
    5. Subset analysis: does the model calibrate equally well for
       major-power vs. minor-power dyads, contiguous vs. non-contiguous,
       Cold War vs. post-Cold War? Heterogeneity here points to
       unmodelled structural variables.

  Likely failure modes to watch for:
    • Beta is one global constant in the spec, but real war hazard varies
      by era and dyad type. Expect calibration to suggest era-specific
      or dyad-class-specific betas.
    • Path 2's W_sev as a single scalar may be too crude; intensity,
      geographic proximity, and ideological character of the ongoing
      war probably need decomposition.
    • The C_p override (V_t > V_p ⇒ C*_p = 1) is a hard step. A soft
      sigmoid version may calibrate better.
"""
    print(notes)


# ============================================================================
if __name__ == "__main__":
    print("\n" + "#" * 78)
    print("# DYADIC WAR MODEL — SYSTEMATIC TEST SUITE")
    print("#" * 78 + "\n")
    run_level_1()
    run_level_2()
    run_level_3()
    run_level_4()
    level_5_notes()