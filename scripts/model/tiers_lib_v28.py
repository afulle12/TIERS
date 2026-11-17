"""TIERS v28.0 transition-hazard engine.

v28 keeps the v27 directed-dyad reconciliation and Capability/Reach gate, but
replaces the generic up/down direction stage with edge-specific hazards and an
explicit economic-interdependence block.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, fields
from typing import Dict, List, Optional

import numpy as np

from tiers_lib_v27 import (
    ActorState,
    DyadState,
    InputState,
    Priors as V27Priors,
    TIER_MAX,
    TIER_MIN,
    TIERS,
    capability_reach_gate,
    reconcile_with_current,
    score_dyad_year as score_dyad_year_v27,
)


@dataclass(frozen=True)
class Priors(V27Priors):
    """Uncalibrated v28 starting priors satisfying the draft sign constraints."""

    a_01: float = -2.40
    b_01_surface: float = 0.75
    b_01_rivalry: float = 1.10
    b_01_contiguity: float = 0.45
    b_01_cap_shift: float = 0.35
    b_01_mutual: float = 0.45
    b_01_public: float = 0.30

    a_12: float = -2.20
    b_12_leverage: float = 1.35
    b_12_import_lev: float = 0.70
    b_12_export_lev: float = 0.45
    b_12_surface: float = 0.35
    b_12_rivalry: float = 0.55
    b_12_public: float = 0.20
    b_12_self_cost: float = 0.90

    a_23: float = -2.85
    b_23_duration: float = 0.18
    b_23_rivalry: float = 0.85
    b_23_failed_coercion: float = 0.30
    b_23_proxy_access: float = 0.25
    b_23_mutual: float = 0.70
    b_23_public: float = 0.25

    a_34: float = -3.15
    b_34_attr_dur: float = 0.32
    b_34_rivalry: float = 0.95
    b_34_contiguity: float = 0.75
    b_34_fma: float = 0.65
    b_34_closing: float = 0.45
    b_34_mutual: float = 1.10
    b_34_trade_cost: float = 0.35
    b_34_public: float = 0.35

    a_45: float = -4.00
    b_45_reach: float = 1.45
    b_45_rivalry: float = 0.85
    b_45_fma: float = 0.45
    b_45_stakes: float = 0.75
    b_45_mobilization: float = 0.25
    b_45_mutual: float = 1.55
    b_45_public: float = 0.30

    deesc_base: float = -1.85
    deesc_diplomatic: float = 0.20
    deesc_mediation: float = 0.20
    deesc_mutual: float = 0.85
    deesc_public: float = 0.35
    deesc_rivalry: float = 0.80
    deesc_duration: float = 0.12

    persistence_base: float = 1.10
    persistence_duration: float = 0.08
    persistence_shock: float = 0.20
    persistence_deesc: float = 0.25

    skip_base: float = -3.30
    skip_structural: float = 0.85
    skip_shock: float = 0.55
    skip_fma: float = 0.45
    skip_reach: float = 0.70
    skip_mutual: float = 1.10
    lambda_skip: float = 1.15


def priors_from_mapping(values: dict) -> Priors:
    """Build v28 priors from a persisted calibration mapping."""
    allowed = {f.name for f in fields(Priors)}
    clean = {k: float(v) for k, v in values.items() if k in allowed}
    return Priors(**clean)


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


def _g(actor: ActorState, name: str, default: float = 0.0) -> float:
    value = getattr(actor, name, default)
    if value is None:
        return default
    try:
        if not np.isfinite(value):
            return default
    except TypeError:
        return default
    return float(value)


def trade_observed(actor: ActorState) -> bool:
    return getattr(actor, "state_integration", InputState.DEFAULTED) != InputState.ABSENT


def adjacent_hazard(k: int, actor: ActorState, target: ActorState, sym: DyadState, gate_t5: bool, priors: Priors) -> float:
    surface = _g(actor, "trade_surface_norm", 0.0)
    mutual = _g(actor, "mutual_trade_dependence", 0.0)
    leverage = _g(actor, "trade_leverage", 0.0)
    import_lev = _g(actor, "import_leverage", 0.0)
    export_lev = _g(actor, "export_leverage", 0.0)
    dep_self = _g(actor, "dep_on_target", 0.0)
    n_pub = _clip01(actor.n_pub)
    cap_shift = _clip01(abs(actor.capability_share - target.capability_share))
    rivalry = _clip01(sym.rivalry)
    contig = _clip01(sym.contiguity)
    duration = max(0.0, float(sym.duration))
    fma = _clip01(actor.fma)
    closing = _clip01(actor.closing_window)
    attr_dur = _clip01(actor.attribution) * duration
    stakes = _clip01(actor.stakes)

    if k == 0:
        h = (
            priors.a_01 + priors.b_01_surface * surface + priors.b_01_rivalry * rivalry
            + priors.b_01_contiguity * contig + priors.b_01_cap_shift * cap_shift
            - priors.b_01_mutual * mutual - priors.b_01_public * n_pub
        )
    elif k == 1:
        h = (
            priors.a_12 + priors.b_12_leverage * leverage
            + priors.b_12_import_lev * import_lev + priors.b_12_export_lev * export_lev
            + priors.b_12_surface * surface + priors.b_12_rivalry * rivalry
            + priors.b_12_public * n_pub - priors.b_12_self_cost * dep_self
        )
    elif k == 2:
        h = (
            priors.a_23 + priors.b_23_duration * duration + priors.b_23_rivalry * rivalry
            + priors.b_23_failed_coercion * _clip01(duration / 5.0)
            + priors.b_23_proxy_access * contig - priors.b_23_mutual * mutual
            - priors.b_23_public * n_pub
        )
    elif k == 3:
        h = (
            priors.a_34 + priors.b_34_attr_dur * attr_dur + priors.b_34_rivalry * rivalry
            + priors.b_34_contiguity * contig + priors.b_34_fma * fma
            + priors.b_34_closing * closing - priors.b_34_mutual * mutual
            - priors.b_34_trade_cost * mutual - priors.b_34_public * n_pub
        )
    elif k == 4:
        effective_trade_cost = mutual * (1.0 - stakes)
        h = (
            priors.a_45 + priors.b_45_reach * float(gate_t5) + priors.b_45_rivalry * rivalry
            + priors.b_45_fma * fma + priors.b_45_stakes * stakes
            + priors.b_45_mobilization * _clip01(duration / 5.0)
            - priors.b_45_mutual * effective_trade_cost - priors.b_45_public * n_pub
        )
        return _sigmoid(h) * float(gate_t5)
    else:
        return 0.0
    return _sigmoid(h)


def deesc_hazard(actor: ActorState, sym: DyadState, priors: Priors) -> float:
    mutual = _g(actor, "mutual_trade_dependence", 0.0)
    h = (
        priors.deesc_base + priors.deesc_diplomatic * actor.deesc_inputs[1]
        + priors.deesc_mediation * actor.deesc_inputs[2] + priors.deesc_mutual * mutual
        + priors.deesc_public * _clip01(actor.n_pub) - priors.deesc_rivalry * _clip01(sym.rivalry)
        - priors.deesc_duration * max(0.0, sym.duration)
    )
    return _sigmoid(h)


def skip_hazard(k: int, j: int, actor: ActorState, sym: DyadState, gate_t5: bool, priors: Priors) -> float:
    if j <= k + 1:
        return 0.0
    if j == TIER_MAX and not gate_t5:
        return 0.0
    structural = _clip01(0.35 * sym.rivalry + 0.25 * sym.contiguity + 0.20 * actor.cap_proxy + 0.20 * actor.closing_window)
    h = (
        priors.skip_base + priors.skip_structural * structural + priors.skip_shock * actor.shock_k
        + priors.skip_fma * actor.fma + priors.skip_reach * float(gate_t5)
        - priors.skip_mutual * _g(actor, "mutual_trade_dependence", 0.0)
    )
    return _sigmoid(h) * math.exp(-priors.lambda_skip * ((j - k) - 1))


def score_directed(actor: ActorState, target: ActorState, sym: DyadState, priors: Optional[Priors] = None) -> Dict:
    priors = priors or Priors()
    k = int(np.clip(sym.current_tier, TIER_MIN, TIER_MAX))
    gate_t5 = capability_reach_gate(sym, actor.cap_proxy, target.cap_proxy, priors)

    raw = [0.0] * (TIER_MAX + 1)
    deesc = deesc_hazard(actor, sym, priors) if k > TIER_MIN else 0.0
    adj = adjacent_hazard(k, actor, target, sym, gate_t5, priors) if k < TIER_MAX else 0.0
    skip_total = 0.0

    if k > TIER_MIN and deesc > 0.0:
        raw[k - 1] += deesc * 0.70
        raw[TIER_MIN] += deesc * 0.30
    if k < TIER_MAX:
        raw[k + 1] += adj
        for j in range(k + 2, TIER_MAX + 1):
            sj = skip_hazard(k, j, actor, sym, gate_t5, priors)
            raw[j] += sj
            skip_total += sj

    stay_logit = (
        priors.persistence_base + priors.persistence_duration * max(0.0, sym.duration)
        - priors.persistence_shock * actor.shock_k - priors.persistence_deesc * deesc
    )
    raw[k] += math.exp(stay_logit)
    total = sum(raw)
    pi = [v / total for v in raw] if total > 0 else [1.0 if j == k else 0.0 for j in TIERS]
    return {
        "pi": pi,
        "k": k,
        "P_down": sum(pi[:k]),
        "P_0": pi[k],
        "P_up": sum(pi[k + 1:]),
        "gate_t5": gate_t5,
        "active_member": "v28-trade" if trade_observed(actor) else "v28-nontrade",
        "diag": {"h_adjacent": adj, "h_deesc": deesc, "h_skip_total": skip_total},
    }


def score_dyad_year(actor_i: ActorState, actor_j: ActorState, sym: DyadState, priors: Optional[Priors] = None) -> Dict:
    priors = priors or Priors()
    if not trade_observed(actor_i) and not trade_observed(actor_j):
        return score_dyad_year_v27(actor_i, actor_j, sym, priors)
    res_ab = score_directed(actor_i, actor_j, sym, priors)
    res_ba = score_directed(actor_j, actor_i, sym, priors)
    pi_rel = reconcile_with_current(res_ab["pi"], res_ba["pi"], res_ab["k"], res_ba["k"])
    return {
        "pi_ab": res_ab["pi"],
        "pi_ba": res_ba["pi"],
        "pi_reconciled": pi_rel,
        "gate_t5": res_ab["gate_t5"],
        "member_ab": res_ab["active_member"],
        "member_ba": res_ba["active_member"],
        "k": res_ab["k"],
        "diag_ab": res_ab["diag"],
        "diag_ba": res_ba["diag"],
    }
