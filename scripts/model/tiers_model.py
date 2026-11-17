"""
TIERS — Unified Equation of Interstate War, Dyadic Variant v2.1.
Implementation and scenario testing.
"""

from dataclasses import dataclass, field
from typing import Dict

C_b = 0.95  # Betrayal penalty constant


@dataclass
class State:
    """Per-state parameters. Values relate A's posture toward B (or vice versa)."""
    name: str
    # Public mobilization: 1 = peaceful, 0 = fully mobilized
    N_pub: float = 0.9
    beta: float = 0.02
    # Motive components
    dP: float = 0.0       # Power-shift dissatisfaction
    R_d: float = 0.0      # Revisionist demands
    A_div: float = 0.0    # Diversionary incentive (domestic distraction)
    P_v: float = 0.0      # Predatory/value motive
    # Opportunity components
    V_p: float = 0.0      # Probing/limited-aim value
    V_t: float = 0.0      # Total/regime-change value
    C_T: float = 0.5      # Target's defensive capability (B's, used by attacker)
    W_v: float = 0.0      # Window of vulnerability
    # Spark components
    B: float = 0.0        # Brinkmanship
    R_h: float = 0.0      # Historical rivalry
    I_s: float = 0.0      # Incidents/sparks
    # Friction components
    I_a: float = 0.5      # Information asymmetry
    C_p: float = 0.3      # Commitment problem
    I_i: float = 0.3      # Indivisibility of issue
    # Intervention cost
    C_i: float = 0.5
    # Treaty / alliance posture
    C_d_sup: float = 0.0  # Treaty depth supporting B
    C_d_opp: float = 0.0  # Treaty depth opposing B (i.e. allied to B's enemies)
    E_n_sup: float = 0.0  # Ethnic/national kinship pulling toward B
    E_n_opp: float = 0.0  # Ethnic/national kinship pulling against B
    S_p_sup: float = 0.0  # Strategic-prestige pull supporting B
    S_p_opp: float = 0.0  # Strategic-prestige pull opposing B


def p_init(A: State, B: State) -> float:
    """Path 1 core initiation probability A -> B."""
    M = max((A.dP + A.R_d + A.A_div) / 3.0, A.P_v)
    O = max(A.V_p, A.V_t) * (1.0 - B.C_T * (1.0 - A.W_v))
    O = max(0.0, O)
    S = (A.B + A.R_h + A.I_s) / 3.0
    C_p_star = 1.0 if A.V_t > A.V_p else A.C_p
    F = 1.0 - (1.0 - A.I_a) * (1.0 - C_p_star) * (1.0 - A.I_i)
    return A.beta * M * O * S * F


def p_direct(A: State, B: State) -> float:
    """A initiates direct war on B."""
    return (1.0 - A.N_pub) * p_init(A, B)


def treaty_triggers(A: State) -> Dict[str, float]:
    """Compute T_sup and T_opp using effective intervention costs with betrayal penalty."""
    delta_opp = 1.0 if A.C_d_opp > 0.5 else 0.0
    delta_sup = 1.0 if A.C_d_sup > 0.5 else 0.0
    C_i_star_sup = max(A.C_i, 1.0 - A.N_pub) + delta_opp * C_b
    C_i_star_opp = max(A.C_i, 1.0 - A.N_pub) + delta_sup * C_b
    T_sup = A.C_d_sup**2 / (A.C_d_sup**2 + C_i_star_sup**2) if (A.C_d_sup**2 + C_i_star_sup**2) > 0 else 0.0
    T_opp = A.C_d_opp**2 / (A.C_d_opp**2 + C_i_star_opp**2) if (A.C_d_opp**2 + C_i_star_opp**2) > 0 else 0.0
    return {"T_sup": T_sup, "T_opp": T_opp}


def p_join(A: State, side: str, W_sev: float) -> float:
    """Path 2: A joins an existing war on B's side ('sup') or against B ('opp')."""
    T = treaty_triggers(A)
    if side == "sup":
        T_x, E_n, S_p = T["T_sup"], A.E_n_sup, A.S_p_sup
    else:
        T_x, E_n, S_p = T["T_opp"], A.E_n_opp, A.S_p_opp
    pull = 1.0 - A.N_pub
    return 1.0 - (1.0 - T_x) \
                * (1.0 - E_n * W_sev * pull) \
                * (1.0 - S_p * W_sev * pull)


def dyadic_results(A: State, B: State, W_sev_A: float = 0.0, W_sev_B: float = 0.0) -> Dict[str, float]:
    """
    W_sev_A = severity of an ongoing war B is already in (relevant when computing A joining B)
    W_sev_B = severity of an ongoing war A is already in (relevant when computing B joining A)
    If neither side is in a prior war, set both to 0 and Path 2 collapses to 0.
    """
    pdAB = p_direct(A, B)
    pdBA = p_direct(B, A)
    pjoAB_opp = p_join(A, "opp", W_sev_A) if W_sev_A > 0 else 0.0
    pjoBA_opp = p_join(B, "opp", W_sev_B) if W_sev_B > 0 else 0.0
    pjsAB_sup = p_join(A, "sup", W_sev_A) if W_sev_A > 0 else 0.0
    pjsBA_sup = p_join(B, "sup", W_sev_B) if W_sev_B > 0 else 0.0

    P_dyad = 1.0 - (1 - pdAB) * (1 - pdBA) * (1 - pjoAB_opp) * (1 - pjoBA_opp)
    P_co = 1.0 - (1 - pjsAB_sup) * (1 - pjsBA_sup)

    return {
        "P_direct(A->B)": pdAB,
        "P_direct(B->A)": pdBA,
        "P_join_opp(A->B)": pjoAB_opp,
        "P_join_opp(B->A)": pjoBA_opp,
        "P_join_sup(A->B)": pjsAB_sup,
        "P_join_sup(B->A)": pjsBA_sup,
        "P_dyadic_war": P_dyad,
        "P_co_belligerent": P_co,
    }


def fmt_pct(p: float) -> str:
    if p < 1e-6:
        return f"{p:.2e}"
    return f"{p*100:.4f}%"


def report(label: str, A: State, B: State, W_sev_A=0.0, W_sev_B=0.0, note=""):
    print("=" * 78)
    print(f"SCENARIO: {label}")
    print(f"  {A.name}  vs.  {B.name}")
    if note:
        print(f"  Context: {note}")
    if W_sev_A > 0 or W_sev_B > 0:
        print(f"  Pre-existing war severity affecting A's join calc: {W_sev_A}")
        print(f"  Pre-existing war severity affecting B's join calc: {W_sev_B}")
    print("-" * 78)
    r = dyadic_results(A, B, W_sev_A, W_sev_B)
    for k, v in r.items():
        print(f"    {k:<22s} = {fmt_pct(v)}")
    return r


# ============================================================================
# SCENARIOS
# ============================================================================

# ---------- 1. UK – France 2026 (mutual close allies, peaceful) -------------
uk_fr_A = State(
    name="UK (vs France)",
    N_pub=0.95, beta=0.02,
    dP=0.05, R_d=0.0, A_div=0.0, P_v=0.0,
    V_p=0.05, V_t=0.0, C_T=0.85, W_v=0.0,
    B=0.0, R_h=0.05, I_s=0.0,
    I_a=0.1, C_p=0.05, I_i=0.0,
    C_i=0.7,
    C_d_sup=0.85, C_d_opp=0.0,
    E_n_sup=0.4, E_n_opp=0.0,
    S_p_sup=0.5, S_p_opp=0.0,
)
uk_fr_B = State(
    name="France (vs UK)",
    N_pub=0.95, beta=0.02,
    dP=0.05, R_d=0.0, A_div=0.0, P_v=0.0,
    V_p=0.05, V_t=0.0, C_T=0.85, W_v=0.0,
    B=0.0, R_h=0.05, I_s=0.0,
    I_a=0.1, C_p=0.05, I_i=0.0,
    C_i=0.7,
    C_d_sup=0.85, C_d_opp=0.0,
    E_n_sup=0.4, E_n_opp=0.0,
    S_p_sup=0.5, S_p_opp=0.0,
)

# ---------- 2. Russia – Ukraine on the eve of 2022 invasion ------------------
ru_ua_A = State(
    name="Russia (vs Ukraine)",
    N_pub=0.4, beta=0.04,
    dP=0.7, R_d=0.85, A_div=0.4, P_v=0.6,
    V_p=0.5, V_t=0.7, C_T=0.35, W_v=0.5,
    B=0.6, R_h=0.7, I_s=0.7,
    I_a=0.8, C_p=0.7, I_i=0.7,
    C_i=0.5,
    C_d_sup=0.0, C_d_opp=0.7,
    E_n_sup=0.0, E_n_opp=0.3,
    S_p_sup=0.0, S_p_opp=0.6,
)
ru_ua_B = State(
    name="Ukraine (vs Russia)",
    N_pub=0.7, beta=0.02,
    dP=0.0, R_d=0.4, A_div=0.0, P_v=0.0,
    V_p=0.0, V_t=0.0, C_T=0.7, W_v=0.0,
    B=0.3, R_h=0.7, I_s=0.5,
    I_a=0.6, C_p=0.5, I_i=0.7,
    C_i=0.6,
    C_d_sup=0.0, C_d_opp=0.8,
    E_n_sup=0.0, E_n_opp=0.4,
    S_p_sup=0.0, S_p_opp=0.4,
)

# ---------- 3. Chile – Mongolia (no contact, no relevance) -------------------
cl_mn_A = State(
    name="Chile (vs Mongolia)",
    N_pub=0.98, beta=0.02,
    dP=0.0, R_d=0.0, A_div=0.0, P_v=0.0,
    V_p=0.0, V_t=0.0, C_T=0.5, W_v=0.0,
    B=0.0, R_h=0.0, I_s=0.0,
    I_a=0.5, C_p=0.0, I_i=0.0,
    C_i=0.95,
    C_d_sup=0.0, C_d_opp=0.0,
    E_n_sup=0.0, E_n_opp=0.0,
    S_p_sup=0.0, S_p_opp=0.0,
)
cl_mn_B = State(
    name="Mongolia (vs Chile)",
    N_pub=0.98, beta=0.02,
    dP=0.0, R_d=0.0, A_div=0.0, P_v=0.0,
    V_p=0.0, V_t=0.0, C_T=0.5, W_v=0.0,
    B=0.0, R_h=0.0, I_s=0.0,
    I_a=0.5, C_p=0.0, I_i=0.0,
    C_i=0.95,
    C_d_sup=0.0, C_d_opp=0.0,
    E_n_sup=0.0, E_n_opp=0.0,
    S_p_sup=0.0, S_p_opp=0.0,
)

# ---------- 4. India – Pakistan (rivals, recurrent crises, nuclear) ----------
in_pk_A = State(
    name="India (vs Pakistan)",
    N_pub=0.8, beta=0.02,
    dP=0.2, R_d=0.4, A_div=0.2, P_v=0.0,
    V_p=0.2, V_t=0.0, C_T=0.6, W_v=0.1,
    B=0.4, R_h=0.85, I_s=0.5,
    I_a=0.6, C_p=0.5, I_i=0.8,
    C_i=0.7,
    C_d_sup=0.0, C_d_opp=0.5,
    E_n_sup=0.0, E_n_opp=0.3,
    S_p_sup=0.0, S_p_opp=0.4,
)
in_pk_B = State(
    name="Pakistan (vs India)",
    N_pub=0.75, beta=0.02,
    dP=0.3, R_d=0.6, A_div=0.4, P_v=0.0,
    V_p=0.2, V_t=0.0, C_T=0.7, W_v=0.1,
    B=0.5, R_h=0.85, I_s=0.5,
    I_a=0.7, C_p=0.5, I_i=0.85,
    C_i=0.7,
    C_d_sup=0.0, C_d_opp=0.5,
    E_n_sup=0.0, E_n_opp=0.3,
    S_p_sup=0.0, S_p_opp=0.4,
)

# ---------- 5. USA – UK as co-belligerents while UK is in a major war --------
us_uk_A = State(
    name="USA (vs UK)",
    N_pub=0.9, beta=0.02,
    dP=0.0, R_d=0.0, A_div=0.0, P_v=0.0,
    V_p=0.0, V_t=0.0, C_T=0.85, W_v=0.0,
    B=0.0, R_h=0.0, I_s=0.0,
    I_a=0.05, C_p=0.0, I_i=0.0,
    C_i=0.5,
    C_d_sup=0.95, C_d_opp=0.0,   # NATO + special relationship
    E_n_sup=0.5, E_n_opp=0.0,
    S_p_sup=0.7, S_p_opp=0.0,
)
us_uk_B = State(
    name="UK (vs USA)",
    N_pub=0.9, beta=0.02,
    dP=0.0, R_d=0.0, A_div=0.0, P_v=0.0,
    V_p=0.0, V_t=0.0, C_T=0.9, W_v=0.0,
    B=0.0, R_h=0.0, I_s=0.0,
    I_a=0.05, C_p=0.0, I_i=0.0,
    C_i=0.5,
    C_d_sup=0.95, C_d_opp=0.0,
    E_n_sup=0.5, E_n_opp=0.0,
    S_p_sup=0.7, S_p_opp=0.0,
)

# ---------- 6. Iran – Israel (hostile, indirect war, brinkmanship) ----------
ir_il_A = State(
    name="Iran (vs Israel)",
    N_pub=0.65, beta=0.02,
    dP=0.4, R_d=0.6, A_div=0.4, P_v=0.3,
    V_p=0.3, V_t=0.2, C_T=0.85, W_v=0.2,
    B=0.6, R_h=0.7, I_s=0.7,
    I_a=0.8, C_p=0.5, I_i=0.6,
    C_i=0.6,
    C_d_sup=0.0, C_d_opp=0.5,
    E_n_sup=0.0, E_n_opp=0.4,
    S_p_sup=0.0, S_p_opp=0.6,
)
ir_il_B = State(
    name="Israel (vs Iran)",
    N_pub=0.55, beta=0.02,
    dP=0.4, R_d=0.3, A_div=0.3, P_v=0.5,
    V_p=0.3, V_t=0.0, C_T=0.55, W_v=0.4,
    B=0.6, R_h=0.7, I_s=0.7,
    I_a=0.6, C_p=0.6, I_i=0.6,
    C_i=0.55,
    C_d_sup=0.0, C_d_opp=0.6,
    E_n_sup=0.0, E_n_opp=0.4,
    S_p_sup=0.0, S_p_opp=0.6,
)

# ---------- 7. Canada – Australia (distant allies, peaceful) -----------------
ca_au_A = State(
    name="Canada (vs Australia)",
    N_pub=0.97, beta=0.02,
    dP=0.0, R_d=0.0, A_div=0.0, P_v=0.0,
    V_p=0.0, V_t=0.0, C_T=0.7, W_v=0.0,
    B=0.0, R_h=0.0, I_s=0.0,
    I_a=0.05, C_p=0.0, I_i=0.0,
    C_i=0.7,
    C_d_sup=0.7, C_d_opp=0.0,    # Five Eyes / Commonwealth
    E_n_sup=0.5, E_n_opp=0.0,
    S_p_sup=0.4, S_p_opp=0.0,
)
ca_au_B = State(
    name="Australia (vs Canada)",
    N_pub=0.97, beta=0.02,
    dP=0.0, R_d=0.0, A_div=0.0, P_v=0.0,
    V_p=0.0, V_t=0.0, C_T=0.7, W_v=0.0,
    B=0.0, R_h=0.0, I_s=0.0,
    I_a=0.05, C_p=0.0, I_i=0.0,
    C_i=0.7,
    C_d_sup=0.7, C_d_opp=0.0,
    E_n_sup=0.5, E_n_opp=0.0,
    S_p_sup=0.4, S_p_opp=0.0,
)

# ---------- 8. North Korea – South Korea (frozen war, treaty enmity) --------
nk_sk_A = State(
    name="North Korea (vs South Korea)",
    N_pub=0.3, beta=0.02,
    dP=0.5, R_d=0.8, A_div=0.5, P_v=0.4,
    V_p=0.3, V_t=0.5, C_T=0.85, W_v=0.2,
    B=0.6, R_h=0.9, I_s=0.6,
    I_a=0.85, C_p=0.6, I_i=0.85,
    C_i=0.6,
    C_d_sup=0.0, C_d_opp=0.6,
    E_n_sup=0.3, E_n_opp=0.0,    # Korean kinship complicates
    S_p_sup=0.0, S_p_opp=0.5,
)
nk_sk_B = State(
    name="South Korea (vs North Korea)",
    N_pub=0.85, beta=0.02,
    dP=0.0, R_d=0.1, A_div=0.0, P_v=0.0,
    V_p=0.05, V_t=0.0, C_T=0.55, W_v=0.0,
    B=0.2, R_h=0.9, I_s=0.4,
    I_a=0.7, C_p=0.4, I_i=0.85,
    C_i=0.65,
    C_d_sup=0.0, C_d_opp=0.5,
    E_n_sup=0.3, E_n_opp=0.0,
    S_p_sup=0.0, S_p_opp=0.4,
)


# ============================================================================
# RUN
# ============================================================================
print("\n" + "#" * 78)
print("# TIERS v2.1 — SCENARIO TEST RUN")
print("# Probabilities are annualized (365-day) hazards under frozen fundamentals.")
print("#" * 78 + "\n")

report("UK – France (close allies, peace)", uk_fr_A, uk_fr_B,
       note="NATO allies, no live war, near-zero hostility, deep mutual treaties.")
print()

report("Russia – Ukraine (Feb 2022 conditions)", ru_ua_A, ru_ua_B,
       note="Russia: high motive, low N_pub from mobilization, V_t > V_p so C_p* = 1.")
print()

report("Chile – Mongolia (no relation)", cl_mn_A, cl_mn_B,
       note="No motive, no opportunity, no spark, no treaties — control case.")
print()

report("India – Pakistan (rivals)", in_pk_A, in_pk_B,
       note="Recurrent crises, nuclear deterrence, indivisible Kashmir.")
print()

# Path 2 demonstration: A and B are close allies; B is fighting a major war.
# Set W_sev_A to the severity of the war B is in (so A might join to support B).
report("USA – UK (UK in a major war, severity 0.7)",
       us_uk_A, us_uk_B, W_sev_A=0.7, W_sev_B=0.0,
       note="Demonstrates Path 2 supportive contagion via deep treaty (T_sup).")
print()

report("Iran – Israel (cold war / proxy era)", ir_il_A, ir_il_B,
       note="High brinkmanship, mutual revisionism, indirect strikes already common.")
print()

report("Canada – Australia (distant allies, peace)", ca_au_A, ca_au_B,
       note="Allies but no shared border or live conflict; geography drives O ~ 0.")
print()

report("North Korea – South Korea (armistice tension)", nk_sk_A, nk_sk_B,
       note="Frozen 1953 conflict, deep mutual hostility, indivisible legitimacy.")
print()

# ============================================================================
# Sensitivity probe: holding everything else fixed, sweep N_pub for Russia
# ============================================================================
print("=" * 78)
print("SENSITIVITY PROBE — Russia's N_pub vs. P_direct(Russia -> Ukraine)")
print("(Lower N_pub = more mobilized public = higher initiation probability)")
print("-" * 78)
import copy
for npub in [1.0, 0.9, 0.7, 0.5, 0.3, 0.1, 0.0]:
    A2 = copy.deepcopy(ru_ua_A)
    A2.N_pub = npub
    p = p_direct(A2, ru_ua_B)
    bar = "#" * int(p * 1000)
    print(f"  N_pub={npub:>4.2f}  P_direct = {fmt_pct(p):>12s}  {bar}")
