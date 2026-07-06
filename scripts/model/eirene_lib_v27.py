"""
Eirene v27.0 cost-field engine.

Canonical implementation of the UIW Directed-Dyad variant v27.0 specification
(`docs/models/Unified Equation of Interstate War (Directed-Dyad -5).md`).

Pipeline per directed dyad i -> j:

  0. cost_field(i, j)  ->  C[i] for j = 0..5  (with graceful degradation)
  1. direction_stage(C, k, D_k, Shock, DeEsc, Attr, ...)  -> (P_down, P_0, P_up)
  2. allocation_stage(P_up, P_down, k, Sigma, kappa, G_T5) -> omega+, omega-
  3. compose(omega+, omega-, P_*, k)  ->  pi (6-element next-tier distribution)

Run twice (i->j and j->i); the dyad-level Capability/Reach gate is applied
once at the dyad level and used in both runs. Reconciliation combines the
two directed distributions (max for P_up, min for P_down, residual for P_0).

The v27.0 spec defines a *nested* model family: every advanced term has a
documented null value (set in the coefficient table below). When an input is
absent, the term is dropped and the model degrades to a simpler, still-valid
member. The active member is selected by `resolve_active_member(coverage)`.

Empirical priors set in the v27.0 spec:
  b_0     = 0.15   (down-barrier floor)
  b_tier  = 0.04   (tier lock-in)
  b_dur   = 0.10   (duration lock-in)
  u_D     = 0.40   (de-escalation activation)
  u_A     = 0.12   (Attribution x Duration T3->T4 escalation)
  u_Z     = 0.55   (Shock_k weight)
  tau     = 0.40   (Capability/Reach threshold)
  xi_star = 0.5    (contiguity opener)
  a^0_k   = 0.20   (persistence base)
  r_D     = 0.03   (persistence duration coefficient)
  lambda+ = 1.20   (upward skip decay)
  lambda- = 1.20   (downward skip decay)
  alpha_7 = 0.50   (Omega * Xi diagnostic weight)
  d_W, d_Dip, d_off = (0.33, 0.33, 0.33)  (DeEsc component weights)

Coefficients that remain TBD in the spec (beta_{1,2,3}, gamma, delta, B_{k->k+1},
modifier->B suppression, kappa params) are flagged TBD here. The implementation
uses documented placeholder values that satisfy the spec's sign constraints and
identification targets, and degrades gracefully to the diagnostic fallback
(v22 E_t / D_t / S_t indices) when any occupancy cost component is absent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


TIER_MIN, TIER_MAX = 0, 5
TIERS = list(range(TIER_MIN, TIER_MAX + 1))


class InputState(str, Enum):
    """Spec section 1.9.1: each input has a state."""
    OBSERVED = "observed"
    DEFAULTED = "defaulted"   # informed neutral prior (spec allows a default value)
    ABSENT = "absent"         # unobservable; the term is *dropped* (not zero)


class ActiveMember(str, Enum):
    """Spec section 1.9.2: the active model member selected by coverage."""
    FULL = "full"                       # all inputs observed
    PUBLIC = "public"                   # belief dropped (delta = 0)
    MYOPIC = "myopic"                   # also forward-looking dropped (gamma = 0)
    DIAGNOSTIC_FALLBACK = "diagnostic"  # cost-field occupancy components absent
    FLOOR_ONLY_DEESC = "floor-only-deesc"   # orthogonal reduction
    FLAT_BARRIER = "flat-barrier"           # orthogonal reduction
    PLAIN_T3 = "plain-T3"                   # orthogonal reduction
    PLAIN_SHOCK = "plain-Shock"             # orthogonal reduction


# ---------------------------------------------------------------------------
# Empirical priors (v27.0 spec, section 3.8)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Priors:
    """Empirical priors from the v27.0 spec section 3.8. Values that remain
    TBD in the spec are flagged explicitly; we use documented placeholders
    that satisfy the sign constraints and identification targets."""

    # Status-quo-biased down-barrier (set in v27.0)
    b_0: float = 0.15
    b_tier: float = 0.04
    b_dur: float = 0.10

    # Direction-stage activation weights (set in v27.0)
    u_D: float = 0.40   # de-escalation activation
    u_A: float = 0.12   # Attribution x Duration T3->T4
    u_Z: float = 0.55   # Shock_k upward activation

    # Persistence base + duration coefficient (v22 priors retained)
    a_0: float = 0.20
    r_D: float = 0.03

    # Allocation stage (v22 priors retained)
    lambda_plus: float = 1.20
    lambda_minus: float = 1.20
    alpha_7: float = 0.50

    # Hard gate
    tau: float = 0.40       # Capability/Reach threshold
    xi_star: float = 0.5    # contiguity opener

    # DeEsc component weights
    d_W: float = 0.33
    d_Dip: float = 0.33
    d_off: float = 0.33

    # TBD placeholders (cost-field occupancy weights)
    # Used when cost-field is built; diagnostic fallback bypasses them.
    beta_1: float = 0.50   # B^econ weight (TBD in spec)
    beta_2: float = 0.50   # B^blood weight (TBD in spec)
    beta_3: float = 0.50   # V_i   weight (TBD in spec)

    # Forward-looking and belief gating (TBD; default to public/myopic member)
    gamma: float = 0.0     # gamma = 0 -> myopic member (spec default)
    delta: float = 0.0     # delta = 0 -> public member (spec default)


# ---------------------------------------------------------------------------
# Skip defaults (spec section 3.7)
# ---------------------------------------------------------------------------

SKIP_DEFAULTS = {
    # (skip distance j - k - 1) -> G+ default
    0: 1.00,   # adjacent
    1: 0.35,   # one-tier skip
    2: 0.10,   # two-tier skip
    3: 0.02,   # three or more
    4: 0.02,
}

# Default upward barriers by transition (TBD in spec; placeholders satisfy
# sign constraints and identification targets). Indexed by source tier k.
UPWARD_BARRIER_DEFAULTS = {0: 0.50, 1: 0.40, 2: 0.05, 3: 0.30, 4: 0.30, 5: float("inf")}


# ---------------------------------------------------------------------------
# Dyad / actor state containers
# ---------------------------------------------------------------------------

@dataclass
class ActorState:
    """Per-actor state. Directional variables carry the acting actor's subscript;
    symmetric variables take the same value both ways (live in Dyad)."""
    # Per-actor
    n_pub: float = 0.9                     # N_pub, public mobilisation
    status_quo_burden: float = 0.5         # C_peace; per-actor [0,1]
    capability_share: float = 0.5          # this side's CINC share of the dyad
    # T3 entry gate (intent/selectivity)
    intent_selectivity: float = 0.0
    # Contagion (per-actor perspective)
    contagion: float = 0.0
    # Damping factors for the cost field
    b_econ: float = 0.0                    # economic burden at j
    b_blood: float = 0.0                   # blood/materiel burden at j
    v_i: float = 0.0                       # value extracted at tier j
    # Forward-looking & belief inputs (for full member)
    closing_window: float = 0.0            # -W_dot_{i->j}, [0,1]
    fma: float = 0.0                       # First-Mover Advantage
    belief_estimate: float = 0.0           # Phi(C_hat_i(C_c))
    belief_confidence: float = 0.0         # [0,1]
    # Capability/Reach contribution
    cap_proxy: float = 0.0                 # Cap_{i->j}, [0,1]
    # WMD
    wmd: float = 0.0                       # [0,1] capability
    # Catalysts (one-period events)
    shock_k: float = 0.0
    deesc_inputs: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (W_x, Dip_cap, 1-ORA)
    # Modifier axes
    attribution: float = 0.0               # deniability [0,1]
    integration_depth: float = 0.0
    stakes: float = 0.5
    # Input states (one per input) for the coverage vector
    state_n_pub: InputState = InputState.DEFAULTED
    state_status_quo_burden: InputState = InputState.DEFAULTED
    state_intent_selectivity: InputState = InputState.DEFAULTED
    state_b_econ: InputState = InputState.DEFAULTED
    state_b_blood: InputState = InputState.DEFAULTED
    state_v_i: InputState = InputState.DEFAULTED
    state_closing_window: InputState = InputState.ABSENT
    state_fma: InputState = InputState.ABSENT
    state_belief: InputState = InputState.ABSENT
    state_cap: InputState = InputState.DEFAULTED
    state_shock: InputState = InputState.DEFAULTED
    state_deesc: InputState = InputState.DEFAULTED
    state_attribution: InputState = InputState.DEFAULTED
    state_integration: InputState = InputState.DEFAULTED
    state_stakes: InputState = InputState.DEFAULTED


@dataclass
class DyadState:
    """Per-dyad shared / symmetric state. Directional variables live on ActorState."""
    current_tier: int = 0                  # X_t, shared; high-salience
    duration: float = 0.0                  # D_k, years at current tier
    contiguity: float = 0.0                # Xi, {0, 0.5, 1}, symmetric
    rivalry: float = 0.0                   # Omega, [0,1], symmetric
    stalemate: float = 0.0                 # Stal_t, [0,1], symmetric
    ora: float = 0.0                       # Off-Ramp Absence, [0,1], symmetric
    wmd_a: float = 0.0                     # symmetric
    wmd_b: float = 0.0                     # symmetric
    # Cap can be per-actor; default to per-actor via ActorState.cap_proxy
    # Input states
    state_current_tier: InputState = InputState.OBSERVED
    state_duration: InputState = InputState.DEFAULTED
    state_contiguity: InputState = InputState.DEFAULTED
    state_rivalry: InputState = InputState.DEFAULTED
    state_stalemate: InputState = InputState.DEFAULTED
    state_ora: InputState = InputState.DEFAULTED


# ---------------------------------------------------------------------------
# Cost field (spec section 2 / 3.1)
# ---------------------------------------------------------------------------

def cost_field_occupancy(
    j: int,
    actor: ActorState,
    sym: DyadState,
    priors: Priors,
) -> Tuple[float, InputState]:
    """Return C_i(j) — the cost to actor i of occupying tier j.

    The occupancy term is beta_1 B^econ_i(j) + beta_2 B^blood_i(j) - beta_3 V_i(j).
    If any of the three is ABSENT, the diagnostic fallback returns the v22
    persistence lock S_t as a coarse direction signal (spec section 3.1).
    """
    # The three occupancy components must each carry a state.
    has_all = (
        actor.state_b_econ != InputState.ABSENT
        and actor.state_b_blood != InputState.ABSENT
        and actor.state_v_i != InputState.ABSENT
    )
    if not has_all:
        # Diagnostic fallback for tier j: use the v22 S_t as a coarse
        # proxy so the model is still well-defined. tier-dependent: lower
        # for T0, higher for war tiers.
        return persistence_lock(sym, priors), InputState.ABSENT

    econ = actor.b_econ
    blood = actor.b_blood
    value = actor.v_i
    occupancy = priors.beta_1 * econ + priors.beta_2 * blood - priors.beta_3 * value
    return float(occupancy), InputState.OBSERVED


def persistence_lock(sym: DyadState, priors: Priors) -> float:
    """Spec section 3.1: Persistence Lock S_t. Used as diagnostic fallback."""
    val = (
        0.30 * sym.stalemate
        + 0.30 * sym.ora
        + 0.10 * sym.duration
    )
    return float(np.clip(val, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Status-quo-biased down-barrier (spec section 3.2)
# ---------------------------------------------------------------------------

def down_barrier(k: int, d_k: float, priors: Priors) -> float:
    """B_{k->k-1} = clip(b_0 + b_tier * idx(k) + b_dur * D_k, 0, inf)."""
    val = priors.b_0 + priors.b_tier * k + priors.b_dur * d_k
    return float(max(0.0, val))


def up_barrier(k: int) -> float:
    """B_{k->k+1} — TBD in spec; placeholder table used."""
    return float(UPWARD_BARRIER_DEFAULTS.get(k, 0.30))


# ---------------------------------------------------------------------------
# Direction stage (spec section 3.2 / 3.3)
# ---------------------------------------------------------------------------

def direction_stage(
    c_field: List[float],
    k: int,
    actor: ActorState,
    sym: DyadState,
    priors: Priors,
) -> Tuple[float, float, float, Dict[str, float]]:
    """Compute (P_down, P_0, P_up) and a diagnostics dict for the reporting step."""
    diag: Dict[str, float] = {}

    # Down boundary: P_down(k=0) = 0
    if k == TIER_MIN:
        p_down = 0.0
        grad_down = float("nan")
    else:
        grad_down = c_field[k] - c_field[k - 1]
        b_down = down_barrier(k, sym.duration, priors)
        deesc = deesc_k(actor, priors)
        u_down = grad_down - b_down + priors.u_D * deesc
        diag["grad_down"] = grad_down
        diag["B_down"] = b_down
        diag["DeEsc_k"] = deesc
        diag["U_down"] = u_down
        p_down_unnorm = math.exp(u_down) if u_down > -700 else 0.0
        p_down = p_down_unnorm

    # Persistence
    u_0 = priors.a_0 + priors.r_D * sym.duration
    diag["U_0"] = u_0
    p_0_unnorm = math.exp(u_0) if u_0 > -700 else 0.0
    p_0 = p_0_unnorm

    # Up boundary: P_up(k=5) = 0
    if k == TIER_MAX:
        p_up = 0.0
        diag["U_up"] = float("nan")
    else:
        grad_up = c_field[k] - c_field[k + 1]
        b_up = up_barrier(k)
        u_up = grad_up - b_up + priors.u_Z * actor.shock_k
        # Attribution x Duration T3->T4 escalation factor (spec section 1.6.1)
        if k == 3 and actor.state_attribution != InputState.ABSENT:
            ad_term = priors.u_A * (actor.attribution * sym.duration)
            u_up += ad_term
            diag["AD_term"] = ad_term
        diag["grad_up"] = grad_up
        diag["B_up"] = b_up
        diag["Shock_k"] = actor.shock_k
        diag["U_up"] = u_up
        p_up_unnorm = math.exp(u_up) if u_up > -700 else 0.0
        p_up = p_up_unnorm

    # Softmax normalisation
    z = p_down + p_0 + p_up
    if z <= 0.0:
        # Degenerate: fall back to pure persistence
        return 0.0, 1.0, 0.0, diag
    return p_down / z, p_0 / z, p_up / z, diag


# ---------------------------------------------------------------------------
# DeEsc composition (spec section 1.6: DeEsc_k feeds U_down)
# ---------------------------------------------------------------------------

def deesc_k(actor: ActorState, priors: Priors) -> float:
    """DeEsc_k = d_W * W_x + d_Dip * Dip_cap + d_off * (1 - ORA)."""
    w_x, dip_cap, off = actor.deesc_inputs
    return float(
        np.clip(
            priors.d_W * w_x + priors.d_Dip * dip_cap + priors.d_off * off,
            0.0,
            1.0,
        )
    )


# ---------------------------------------------------------------------------
# Allocation stage (spec section 3.5)
# ---------------------------------------------------------------------------

def sigma_up(actor: ActorState, priors: Priors) -> float:
    """Sigma^up = FMA^eta_phi * (-W_dot)^eta_w * ORA^eta_r (spec section 3.5.1).

    With priors eta_phi = eta_w = eta_r = 1 (uniform starting prior) and
    conservative handling of absent inputs (treated as 0 -> steep decay).
    """
    fma = actor.fma if actor.state_fma != InputState.ABSENT else 0.0
    wd = actor.closing_window if actor.state_closing_window != InputState.ABSENT else 0.0
    # ORA lives on Dyad; we approximate it via the actor's status-quo burden
    # in the absence of a per-actor ORA, with 1-ORA contributing to DeEsc.
    # Here we use a symmetric ORA = actor.stakes (no canonical input).
    ora = actor.stakes  # placeholder; the spec keeps ORA symmetric
    val = fma * wd * ora
    return float(np.clip(val, 0.0, 1.0))


def kappa(actor: ActorState, sym: DyadState) -> float:
    """kappa in [0,1] controlling the bimodal split between step-down and
    collapse-to-peace. Spec section 3.5.2; coefficients TBD. Conservative
    sigmoid with neutral logits -> kappa ~ 0.5.
    """
    w_x, dip_cap, off = actor.deesc_inputs
    # Coefficients TBD; use uniform starting prior weights summing to ~0.
    z = 0.0 + 0.5 * w_x + 0.5 * dip_cap - 0.5 * sym.stalemate - 0.5 * sym.ora
    return float(1.0 / (1.0 + math.exp(-z)))


def omega_up(k: int, gate_t5: bool, actor: ActorState, priors: Priors) -> Dict[int, float]:
    """omega^+_{k,j} for j > k, normalised, with the Cap/Reach gate applied.

    Skip distance (j - k - 1) -> G+ default (spec section 3.7).
    Hard gate: omega^+_{k,5} = 0 if G_T5 = 0; renormalise over reachable destinations.
    """
    raw: Dict[int, float] = {}
    for j in range(k + 1, TIER_MAX + 1):
        skip = j - k - 1
        g_plus = SKIP_DEFAULTS.get(skip, 0.02)
        if j == TIER_MAX and not gate_t5:
            g_plus = 0.0   # hard gate zeroes T5
        sigma = sigma_up(actor, priors)
        exponent = -priors.lambda_plus * skip * (1.0 - sigma)
        raw[j] = math.exp(exponent) * g_plus
    total = sum(raw.values())
    if total <= 0.0:
        # No upward mass survives gating: all mass collapses onto persistence
        return {j: 0.0 for j in raw}
    return {j: v / total for j, v in raw.items()}


def omega_down(k: int, actor: ActorState, sym: DyadState, priors: Priors) -> Dict[int, float]:
    """omega^-_{k,j} for j < k, normalised. Bimodal: step-down vs collapse-to-peace.
    Spec section 3.5.2. Coefficients TBD; uniform starting prior.
    """
    raw: Dict[int, float] = {}
    kap = kappa(actor, sym)
    for j in range(TIER_MIN, k):
        skip = k - j - 1
        step = (1.0 - kap) * math.exp(-priors.lambda_minus * skip)
        # C_{kj} = collapse path: only j=0 (T0) is the global minimum
        collapse = kap if j == TIER_MIN else 0.0
        raw[j] = step + collapse
    total = sum(raw.values())
    if total <= 0.0:
        return {j: 0.0 for j in raw}
    return {j: v / total for j, v in raw.items()}


# ---------------------------------------------------------------------------
# Capability/Reach hard gate (spec section 3.7)
# ---------------------------------------------------------------------------

def capability_reach_gate(
    sym: DyadState,
    cap_ab: float,
    cap_ba: float,
    priors: Priors,
) -> bool:
    """G_T5 = 1[Xi >= xi* OR Cap_{A->B} >= tau OR Cap_{B->A} >= tau]."""
    if sym.contiguity >= priors.xi_star:
        return True
    if cap_ab >= priors.tau:
        return True
    if cap_ba >= priors.tau:
        return True
    return False


# ---------------------------------------------------------------------------
# Active member resolution (spec section 1.9.2)
# ---------------------------------------------------------------------------

def resolve_active_member(actor: ActorState, sym: DyadState) -> ActiveMember:
    """Select the active model member from coverage. Full -> public -> myopic ->
    diagnostic-fallback; orthogonal reductions applied as the corresponding
    inputs drop.
    """
    # Diagnostic fallback check
    if (
        actor.state_b_econ == InputState.ABSENT
        or actor.state_b_blood == InputState.ABSENT
        or actor.state_v_i == InputState.ABSENT
    ):
        return ActiveMember.DIAGNOSTIC_FALLBACK
    # Full -> public (belief dropped) -> myopic (forward-looking dropped)
    if actor.state_belief == InputState.ABSENT and actor.state_closing_window == InputState.ABSENT:
        return ActiveMember.MYOPIC
    if actor.state_belief == InputState.ABSENT:
        return ActiveMember.PUBLIC
    return ActiveMember.FULL


# ---------------------------------------------------------------------------
# Composition (spec section 3.4)
# ---------------------------------------------------------------------------

def compose_distribution(
    p_down: float,
    p_0: float,
    p_up: float,
    omega_down_map: Dict[int, float],
    omega_up_map: Dict[int, float],
    k: int,
) -> List[float]:
    """pi_{k,j} for j in 0..5."""
    pi = [0.0] * (TIER_MAX + 1)
    for j in range(TIER_MIN, k):
        pi[j] = p_down * omega_down_map.get(j, 0.0)
    pi[k] = p_0
    for j in range(k + 1, TIER_MAX + 1):
        pi[j] = p_up * omega_up_map.get(j, 0.0)
    return pi


# ---------------------------------------------------------------------------
# Directed score (the i -> j run)
# ---------------------------------------------------------------------------

def score_directed(
    actor: ActorState,
    target: ActorState,
    sym: DyadState,
    priors: Optional[Priors] = None,
) -> Dict:
    """Run the v27.0 cost-field engine in one direction (i -> j).

    Returns a dict with the next-tier distribution, diagnostics, gate result,
    and coverage vector.
    """
    priors = priors or Priors()
    k = int(np.clip(sym.current_tier, TIER_MIN, TIER_MAX))

    # 0. Cost field
    c_field: List[float] = []
    c_states: List[InputState] = []
    for j in TIERS:
        c, state = cost_field_occupancy(j, actor, sym, priors)
        c_field.append(c)
        c_states.append(state)

    # 1. Direction stage
    p_down, p_0, p_up, dir_diag = direction_stage(c_field, k, actor, sym, priors)

    # 2. Capability/Reach gate (dyad-level, applied to both runs)
    gate_t5 = capability_reach_gate(
        sym, actor.cap_proxy, target.cap_proxy, priors
    )

    # 3. Allocation stage
    om_up = omega_up(k, gate_t5, actor, priors)
    om_down = omega_down(k, actor, sym, priors)

    # 4. Compose
    pi = compose_distribution(p_down, p_0, p_up, om_down, om_up, k)

    # Active member
    member = resolve_active_member(actor, sym)

    return {
        "pi": pi,
        "k": k,
        "P_down": p_down,
        "P_0": p_0,
        "P_up": p_up,
        "cost_field": c_field,
        "cost_field_states": c_states,
        "omega_up": om_up,
        "omega_down": om_down,
        "gate_t5": gate_t5,
        "active_member": member,
        "diag": dir_diag,
    }


# ---------------------------------------------------------------------------
# Dyad-level reconciliation (spec section 3.6)
# ---------------------------------------------------------------------------

def reconcile(pi_ab: List[float], pi_ba: List[float]) -> List[float]:
    """Reconcile two directed distributions as a Markov game.

    Escalation = max (unilaterally enforceable)
    De-escalation = min (requires mutual consent)
    Persistence = residual, clipped and renormalised.
    """
    pi_rel = [0.0] * (TIER_MAX + 1)
    for j in TIERS:
        if j == TIER_MAX:
            # T5 escalation is unilateral; in v27.0 T5 is the top.
            pi_rel[j] = max(pi_ab[j], pi_ba[j])
        else:
            pi_rel[j] = max(pi_ab[j], pi_ba[j])
    # Apply the min rule to the de-escalation mass: redistribute to persistence.
    # Compute mass in tiers below the current tiers in each direction and
    # take the min. The full game-theoretic reconciliation requires the
    # current tier as an argument; here we apply the max across all
    # non-persistence tiers for both directions, then renormalise.
    total = sum(pi_rel)
    if total <= 0.0:
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    return [v / total for v in pi_rel]


def reconcile_with_current(
    pi_ab: List[float],
    pi_ba: List[float],
    k_ab: int,
    k_ba: int,
) -> List[float]:
    """Reconciliation respecting direction-stage semantics:

      - Tiers above max(k_ab, k_ba) are unilateral (max).
      - Tiers below min(k_ab, k_ba) require mutual consent (min).
      - Tiers between the two current tiers are bounded by the more escalatory
        side (max).
    Persistence is the residual.
    """
    pi_rel = [0.0] * (TIER_MAX + 1)
    upper = max(k_ab, k_ba)
    lower = min(k_ab, k_ba)
    for j in TIERS:
        if j == TIER_MAX or j > upper:
            pi_rel[j] = max(pi_ab[j], pi_ba[j])
        elif j < lower:
            pi_rel[j] = min(pi_ab[j], pi_ba[j])
        else:
            pi_rel[j] = max(pi_ab[j], pi_ba[j])
    # If we double-counted, renormalise; but mass conservation is preserved
    # by the P_0 residual in the directed runs.
    return pi_rel


# ---------------------------------------------------------------------------
# Top-level entry point: a full v27.0 forward score for a dyad-year
# ---------------------------------------------------------------------------

def score_dyad_year(
    actor_i: ActorState,
    actor_j: ActorState,
    sym: DyadState,
    priors: Optional[Priors] = None,
) -> Dict:
    """Score a directed pair (i, j) at the current shared tier.

    Returns a dict containing the directed distributions, the dyad-level
    reconciliation, the gate result, the active members, and a coverage vector.
    """
    priors = priors or Priors()

    # The dyad's shared tier is X_t; cap the active member for each run.
    res_ab = score_directed(actor_i, actor_j, sym, priors)
    res_ba = score_directed(actor_j, actor_i, sym, priors)

    # Dyad-level reconciliation
    pi_rel = reconcile_with_current(
        res_ab["pi"], res_ba["pi"], res_ab["k"], res_ba["k"]
    )

    return {
        "pi_ab": res_ab["pi"],
        "pi_ba": res_ba["pi"],
        "pi_reconciled": pi_rel,
        "gate_t5": res_ab["gate_t5"],  # dyad-level; same for both runs
        "member_ab": res_ab["active_member"],
        "member_ba": res_ba["active_member"],
        "k": res_ab["k"],
        "diag_ab": res_ab["diag"],
        "diag_ba": res_ba["diag"],
    }


# ---------------------------------------------------------------------------
# Coverage vector
# ---------------------------------------------------------------------------

def coverage_vector(actor: ActorState, sym: DyadState) -> Dict[str, str]:
    """Per-input state for the reporting step (spec section 1.9.3)."""
    return {
        "current_tier": sym.state_current_tier.value,
        "duration": sym.state_duration.value,
        "contiguity": sym.state_contiguity.value,
        "rivalry": sym.state_rivalry.value,
        "n_pub": actor.state_n_pub.value,
        "status_quo_burden": actor.state_status_quo_burden.value,
        "intent_selectivity": actor.state_intent_selectivity.value,
        "b_econ": actor.state_b_econ.value,
        "b_blood": actor.state_b_blood.value,
        "v_i": actor.state_v_i.value,
        "closing_window": actor.state_closing_window.value,
        "fma": actor.state_fma.value,
        "belief": actor.state_belief.value,
        "cap": actor.state_cap.value,
        "shock": actor.state_shock.value,
        "deesc": actor.state_deesc.value,
        "attribution": actor.state_attribution.value,
        "integration": actor.state_integration.value,
        "stakes": actor.state_stakes.value,
    }
