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
    _col_array,
    capability_reach_gate,
    reconcile_with_current,
    reconcile_with_current_batch,
    score_dataframe_v27,
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


def actor_rivalry(actor: ActorState, sym: DyadState) -> float:
    """The actor's own rivalry toward the other state, else the dyad's shared value."""
    own = getattr(actor, "rivalry", None)
    return float(sym.rivalry if own is None else own)


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
    rivalry = _clip01(actor_rivalry(actor, sym))
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
        + priors.deesc_public * _clip01(actor.n_pub) - priors.deesc_rivalry * _clip01(actor_rivalry(actor, sym))
        - priors.deesc_duration * max(0.0, sym.duration)
    )
    return _sigmoid(h)


def skip_hazard(k: int, j: int, actor: ActorState, sym: DyadState, gate_t5: bool, priors: Priors) -> float:
    if j <= k + 1:
        return 0.0
    if j == TIER_MAX and not gate_t5:
        return 0.0
    structural = _clip01(0.35 * actor_rivalry(actor, sym) + 0.25 * sym.contiguity + 0.20 * actor.cap_proxy + 0.20 * actor.closing_window)
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


def _sigmoid_batch(x: np.ndarray) -> np.ndarray:
    """Numerically stable vectorized sigmoid."""
    out = np.empty_like(x, dtype=float)
    pos = x >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    ez = np.exp(np.clip(x[~pos], -700.0, 0.0))
    out[~pos] = ez / (1.0 + ez)
    return out


def _score_directed_v28_batch(
    k: np.ndarray,
    duration: np.ndarray,
    rivalry_raw: np.ndarray,
    contig_raw: np.ndarray,
    gate_t5: np.ndarray,
    n_pub: np.ndarray,
    cap_share: np.ndarray,
    other_cap_share: np.ndarray,
    closing_raw: np.ndarray,
    fma_raw: np.ndarray,
    cap_proxy_raw: np.ndarray,
    attribution: np.ndarray,
    surface: np.ndarray,
    mutual: np.ndarray,
    dep_self: np.ndarray,
    leverage: np.ndarray,
    import_lev: np.ndarray,
    export_lev: np.ndarray,
    priors: Priors,
) -> np.ndarray:
    """Vectorized directed v28 transition-hazard distribution for arrays of length N."""
    n = len(k)
    n_pub_c = np.clip(n_pub, 0.0, 1.0)
    cap_shift = np.clip(np.abs(cap_share - other_cap_share), 0.0, 1.0)
    rivalry = np.clip(rivalry_raw, 0.0, 1.0)
    contig = np.clip(contig_raw, 0.0, 1.0)
    dur = np.maximum(0.0, duration)
    fma = np.clip(fma_raw, 0.0, 1.0)
    closing = np.clip(closing_raw, 0.0, 1.0)
    attr_dur = np.clip(attribution, 0.0, 1.0) * dur
    stakes = 0.5

    # Adjacent upward hazards (evaluated on k in 0..4)
    h0 = (
        priors.a_01 + priors.b_01_surface * surface + priors.b_01_rivalry * rivalry
        + priors.b_01_contiguity * contig + priors.b_01_cap_shift * cap_shift
        - priors.b_01_mutual * mutual - priors.b_01_public * n_pub_c
    )
    h1 = (
        priors.a_12 + priors.b_12_leverage * leverage
        + priors.b_12_import_lev * import_lev + priors.b_12_export_lev * export_lev
        + priors.b_12_surface * surface + priors.b_12_rivalry * rivalry
        + priors.b_12_public * n_pub_c - priors.b_12_self_cost * dep_self
    )
    h2 = (
        priors.a_23 + priors.b_23_duration * dur + priors.b_23_rivalry * rivalry
        + priors.b_23_failed_coercion * np.clip(dur / 5.0, 0.0, 1.0)
        + priors.b_23_proxy_access * contig - priors.b_23_mutual * mutual
        - priors.b_23_public * n_pub_c
    )
    h3 = (
        priors.a_34 + priors.b_34_attr_dur * attr_dur + priors.b_34_rivalry * rivalry
        + priors.b_34_contiguity * contig + priors.b_34_fma * fma
        + priors.b_34_closing * closing - priors.b_34_mutual * mutual
        - priors.b_34_trade_cost * mutual - priors.b_34_public * n_pub_c
    )
    effective_trade_cost = mutual * (1.0 - stakes)
    h4 = (
        priors.a_45 + priors.b_45_reach * gate_t5.astype(float) + priors.b_45_rivalry * rivalry
        + priors.b_45_fma * fma + priors.b_45_stakes * stakes
        + priors.b_45_mobilization * np.clip(dur / 5.0, 0.0, 1.0)
        - priors.b_45_mutual * effective_trade_cost - priors.b_45_public * n_pub_c
    )
    h_adj_all = np.column_stack([h0, h1, h2, h3, h4, np.zeros(n, dtype=float)])
    adj_logits = h_adj_all[np.arange(n), k]
    adj = _sigmoid_batch(adj_logits)
    adj = np.where(k == 4, adj * gate_t5.astype(float), adj)
    adj = np.where(k < TIER_MAX, adj, 0.0)

    # De-escalation hazard (deesc_inputs=(0,0,0))
    deesc_logit = (
        priors.deesc_base + priors.deesc_mutual * mutual
        + priors.deesc_public * n_pub_c - priors.deesc_rivalry * rivalry
        - priors.deesc_duration * dur
    )
    deesc = np.where(k > TIER_MIN, _sigmoid_batch(deesc_logit), 0.0)

    # Skip base hazard (matches scalar skip_hazard: structural clips weighted raw inputs)
    structural = np.clip(
        0.35 * rivalry_raw + 0.25 * contig_raw + 0.20 * cap_proxy_raw + 0.20 * closing_raw,
        0.0,
        1.0,
    )
    skip_logit = (
        priors.skip_base + priors.skip_structural * structural
        + priors.skip_fma * fma_raw + priors.skip_reach * gate_t5.astype(float)
        - priors.skip_mutual * mutual
    )
    skip_base_sig = _sigmoid_batch(skip_logit)

    raw = np.zeros((n, 6), dtype=float)
    row_idx = np.arange(n)

    # De-escalation mass into k-1 and T0
    has_deesc = (k > TIER_MIN) & (deesc > 0.0)
    if np.any(has_deesc):
        idx_d = row_idx[has_deesc]
        raw[idx_d, k[has_deesc] - 1] += deesc[has_deesc] * 0.70
        raw[idx_d, TIER_MIN] += deesc[has_deesc] * 0.30

    # Adjacent upward mass into k+1
    has_up = k < TIER_MAX
    if np.any(has_up):
        idx_u = row_idx[has_up]
        raw[idx_u, k[has_up] + 1] += adj[has_up]

    # Skip upward mass into j >= k + 2
    tiers = np.arange(TIER_MIN, TIER_MAX + 1)[None, :]
    skip_dist = tiers - k[:, None] - 1
    skip_mask = (tiers >= k[:, None] + 2) & ((tiers < TIER_MAX) | gate_t5[:, None])
    raw += np.where(
        skip_mask,
        skip_base_sig[:, None] * np.exp(-priors.lambda_skip * np.maximum(skip_dist, 0)),
        0.0,
    )

    # Persistence mass at k
    stay_logit = priors.persistence_base + priors.persistence_duration * dur - priors.persistence_deesc * deesc
    raw[row_idx, k] += np.exp(stay_logit)

    total = raw.sum(axis=1, keepdims=True)
    pi = np.where(total > 0.0, raw / np.where(total > 0.0, total, 1.0), 0.0)
    zero_tot = total[:, 0] <= 0.0
    if np.any(zero_tot):
        pi[zero_tot, k[zero_tot]] = 1.0
    return pi


def score_dataframe_v28(df, priors: Optional[Priors] = None) -> Dict[str, np.ndarray]:
    """Vectorized v28.0 scoring over a feature DataFrame, matching `V28Calibrator.score_row`."""
    priors = priors or Priors()
    n = len(df)
    k = np.clip(_col_array(df, "uiw_tier", 0, dtype=int), TIER_MIN, TIER_MAX)
    duration = _col_array(df, "d_k_years", 0.0, dtype=float)
    contig_raw = _col_array(df, "contiguity_xi", 0.0, dtype=float)
    # Rivalry is directed: `rivalry_omega` is the initiator's toward the
    # target and `rivalry_omega_b` the target's toward the initiator. A frame
    # without the second column is scored with the same value both ways.
    rivalry_raw = _col_array(df, "rivalry_omega", 0.0, dtype=float)
    rivalry_raw_b = (
        _col_array(df, "rivalry_omega_b", 0.0, dtype=float) if "rivalry_omega_b" in df.columns else rivalry_raw
    )
    fma_raw = _col_array(df, "fma", 0.0, dtype=float)
    cap_ab = _col_array(df, "cap_a_to_b", 0.0, dtype=float)
    cap_ba = _col_array(df, "cap_b_to_a", 0.0, dtype=float)
    cw_a = _col_array(df, "closing_window_a", 0.5, dtype=float)
    cw_b = _col_array(df, "closing_window_b", 0.5, dtype=float)
    n_pub_a = _col_array(df, "n_pub_a", 0.9, dtype=float)
    n_pub_b = _col_array(df, "n_pub_b", 0.9, dtype=float)
    c_t_ab = _col_array(df, "c_t_ab", 0.5, dtype=float)
    c_t_ba = _col_array(df, "c_t_ba", 0.5, dtype=float)
    attr = _col_array(df, "attribution", 0.0, dtype=float)

    surface = _col_array(df, "trade_surface_norm_ab", 0.0, dtype=float)
    mutual = _col_array(df, "mutual_trade_dependence_ab", 0.0, dtype=float)
    dep_ab = _col_array(df, "dep_a_on_b", 0.0, dtype=float)
    dep_ba = _col_array(df, "dep_b_on_a", 0.0, dtype=float)
    imp_lev_ab = _col_array(df, "import_leverage_a_over_b", 0.0, dtype=float)
    exp_lev_ab = _col_array(df, "export_leverage_a_over_b", 0.0, dtype=float)
    tr_lev_ab = _col_array(df, "trade_leverage_a_over_b", 0.0, dtype=float)

    imp_dep_ab = _col_array(df, "import_dep_a_on_b", 0.0, dtype=float)
    imp_dep_ba = _col_array(df, "import_dep_b_on_a", 0.0, dtype=float)
    exp_dep_ab = _col_array(df, "export_dep_a_on_b", 0.0, dtype=float)
    exp_dep_ba = _col_array(df, "export_dep_b_on_a", 0.0, dtype=float)
    imp_lev_ba = np.maximum(imp_dep_ab - imp_dep_ba, 0.0)
    exp_lev_ba = np.maximum(exp_dep_ab - exp_dep_ba, 0.0)
    tr_lev_ba = np.maximum(imp_lev_ba, exp_lev_ba)

    if "trade_source" in df.columns:
        trade_src = df["trade_source"].fillna("NONE").astype(str).to_numpy()
    else:
        trade_src = np.full(n, "NONE", dtype=object)
    trade_obs = trade_src != "NONE"

    gate_t5 = (contig_raw >= priors.xi_star) | (cap_ab >= priors.tau) | (cap_ba >= priors.tau)

    pi_ab = np.zeros((n, 6), dtype=float)
    pi_ba = np.zeros((n, 6), dtype=float)
    pi_rel = np.zeros((n, 6), dtype=float)
    member = np.empty(n, dtype=object)

    if np.any(trade_obs):
        m = trade_obs
        pi_ab_t = _score_directed_v28_batch(
            k[m], duration[m], rivalry_raw[m], contig_raw[m], gate_t5[m],
            n_pub_a[m], c_t_ab[m], c_t_ba[m], cw_a[m], fma_raw[m], cap_ab[m], attr[m],
            surface[m], mutual[m], dep_ab[m], tr_lev_ab[m], imp_lev_ab[m], exp_lev_ab[m],
            priors,
        )
        pi_ba_t = _score_directed_v28_batch(
            k[m], duration[m], rivalry_raw_b[m], contig_raw[m], gate_t5[m],
            n_pub_b[m], c_t_ba[m], c_t_ab[m], cw_b[m], fma_raw[m], cap_ba[m], np.zeros(m.sum()),
            surface[m], mutual[m], dep_ba[m], tr_lev_ba[m], imp_lev_ba[m], exp_lev_ba[m],
            priors,
        )
        pi_ab[m] = pi_ab_t
        pi_ba[m] = pi_ba_t
        pi_rel[m] = reconcile_with_current_batch(pi_ab_t, pi_ba_t, k[m])
        member[m] = "v28-trade"

    if np.any(~trade_obs):
        nm = ~trade_obs
        v27_res = score_dataframe_v27(df.iloc[nm], priors)
        pi_ab[nm] = v27_res["pi_ab"]
        pi_ba[nm] = v27_res["pi_ba"]
        pi_rel[nm] = v27_res["pi"]
        member[nm] = v27_res["member_ab"]

    return {
        "pi": pi_rel,
        "pi_ab": pi_ab,
        "pi_ba": pi_ba,
        "gate_t5": gate_t5,
        "member_ab": member,
        "member_ba": member,
        "k": k,
    }

