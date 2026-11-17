# Unified Equation of Interstate War (Directed-Dyad Variant) v28 Draft

Status: approved conceptual draft, not yet implemented.

v28 extends the v27.0 cost-field engine with transition-specific hazards and an
explicit economic-interdependence block. The core change is that escalation is
modeled as a ladder of directed transition hazards rather than as one generic
next-tier distribution.

The v27 engine remains the fallback member. If v28-specific inputs are absent,
the model degrades to v27-compatible scoring.

---

## 1. Core Claim

Economic integration is dual-use:

- It increases the surface area for low-tier disputes because states interact
  through more trade, market-access, financial, supply-chain, and regulatory
  channels.
- It raises the expected cost of direct military escalation because severe
  conflict threatens economic rupture.
- Asymmetric dependence creates directed coercive leverage: the less-dependent
  actor can impose economic pain at lower relative cost.

Therefore, trade should not enter the model as a single "peace through trade"
term. v28 separates economic exposure into contact, dependence, and leverage.

---

## 2. Tier System

| Tier | Label | Definition |
|---|---|---|
| T0 | Peace / No Active Conflict | No observed coercive interstate conflict. |
| T1 | Diplomatic Crisis | Threats, protests, recalls, ultimatums, coercive diplomatic friction. |
| T2 | Economic Coercion | Sanctions, embargoes, trade restrictions, financial exclusion. |
| T3 | Proxy / Indirect Military | Sustained indirect military support or proxy pressure. |
| T4 | Limited Direct Military | Attributed direct force, border clashes, strikes, limited combat. |
| T5 | Strategic War | Large-scale interstate war, strategic reach, regime-threatening or nationwide conflict. |

---

## 3. Architecture

For a directed dyad `A -> B` at current tier `k`, v28 computes:

```text
P(T_{t+1} = 0..5 | T_t = k, A, B)
```

through five stages:

```text
1. Feature construction
2. Edge-specific adjacent transition hazards
3. Skip-transition hazards
4. De-escalation and persistence hazards
5. Directed reconciliation into a dyad-level next-tier distribution
```

The principal adjacent hazards are:

```text
h_01 = P(T0 -> T1+)
h_12 = P(T1 -> T2+)
h_23 = P(T2 -> T3+)
h_34 = P(T3 -> T4+)
h_45 = P(T4 -> T5)
```

The final distribution still reports exact mass at each next tier:

```text
pi = [P(T0), P(T1), P(T2), P(T3), P(T4), P(T5)]
```

---

## 4. Feature Blocks

v28 retains the v27 structural block:

```text
current_tier
duration_at_current_tier
contiguity / distance
capability ratio
rivalry
democracy / public constraint
alliance depth
first-mover advantage
attribution
closing window
Capability/Reach gate for T5
```

**Rivalry is directed (amended November 2026).** v27 section 1.6.4 called
$\Omega$ symmetric. In v28, `Rivalry_AB` is A's rivalry toward B: the
recency-decayed history of B's militarised actions against A,

```text
Rivalry_AB(T) = min(1, sum over t <= T of w_BA(t) * exp(-0.10 * (T - t)))
```

where `w_BA(t)` weights the hostility level B directed at A in year t
(threat 0.25, display 0.50, use of force 0.75, war 1.00). A state that has
been threatened or attacked treats the other as a rival whether or not it
acted itself, so `Rivalry_AB` and `Rivalry_BA` can differ. Events through
year T are used to forecast year T + 1, and history runs from 1900. The value
lives on the actor, not on the shared dyad state. A shared `conflict_history`
(the same sum over both directions) is built alongside it and is not yet
used by the engine. Builder: `scripts/build/build_rivalry.py`.

v28 adds an economic-interdependence block built from bilateral trade data,
initially CEPII BACI for 1995-2024 coverage:

```text
exports_A_to_B
exports_B_to_A
imports_A_from_B
imports_B_from_A
total_trade_A
total_trade_B
total_imports_A
total_imports_B
total_exports_A
total_exports_B
```

Derived directed variables:

```text
trade_surface_AB
dep_A_on_B
dep_B_on_A
mutual_trade_dependence_AB
import_leverage_A_over_B
export_leverage_A_over_B
trade_leverage_A_over_B
trade_vulnerability_B_to_A
strategic_goods_dependence_B_on_A
trade_shock_AB
```

---

## 5. Economic Terms

### 5.1 Trade Surface

Trade surface measures the density of bilateral economic contact:

```text
trade_surface_AB = log(1 + exports_A_to_B + exports_B_to_A)
trade_surface_norm_AB = rank_percentile_year(trade_surface_AB)
```

Expected effect:

```text
raises T0->T1
raises T1->T2
weakly raises low-tier friction
```

### 5.2 Directed Dependence

A's dependence on B:

```text
dep_A_on_B = (exports_A_to_B + imports_A_from_B) / total_trade_A
```

B's dependence on A:

```text
dep_B_on_A = (exports_B_to_A + imports_B_from_A) / total_trade_B
```

### 5.3 Mutual Dependence

Mutual dependence captures the shared cost of rupture:

```text
mutual_trade_dependence_AB = min(dep_A_on_B, dep_B_on_A)
```

Expected effect:

```text
suppresses T3->T4
strongly suppresses T4->T5
raises de-escalation / off-ramp pressure
```

### 5.4 Directed Trade Leverage

A has economic leverage over B when B depends more on A than A depends on B:

```text
trade_leverage_A_over_B = max(dep_B_on_A - dep_A_on_B, 0)
```

Expected effect:

```text
raises A's T1->T2 economic-coercion hazard against B
may substitute for kinetic escalation by giving A a nonmilitary coercive tool
```

### 5.5 Import and Export Leverage

Import dependence:

```text
import_dep_B_on_A = imports_B_from_A / total_imports_B
import_dep_A_on_B = imports_A_from_B / total_imports_A
```

Import leverage:

```text
import_leverage_A_over_B = max(import_dep_B_on_A - import_dep_A_on_B, 0)
```

Export dependence:

```text
export_dep_B_on_A = exports_B_to_A / total_exports_B
export_dep_A_on_B = exports_A_to_B / total_exports_A
```

Export leverage:

```text
export_leverage_A_over_B = max(export_dep_B_on_A - export_dep_A_on_B, 0)
```

Composite leverage:

```text
trade_leverage_A_over_B = max(import_leverage_A_over_B, export_leverage_A_over_B)
```

Import and export channels are kept separate because supply cutoff and market
access denial are different coercive instruments.

### 5.6 Strategic Goods Dependence

If product-level BACI aggregation is attached:

```text
strategic_goods_dependence_B_on_A = strategic_imports_B_from_A / total_strategic_imports_B
```

Strategic goods initially include:

```text
energy
food
fertilizer
critical minerals
semiconductors / advanced electronics
dual-use industrial inputs
defense-adjacent goods
```

This term can both increase coercive leverage and increase crisis pressure if a
critical supply relationship is threatened.

---

## 6. Adjacent Transition Hazards

All hazards are directed. `A -> B` can have different economic leverage than
`B -> A`.

### 6.1 T0 -> T1: Crisis Onset

Theory: trade contact, rivalry, contiguity, and capability shifts create more
points of diplomatic friction. Mutual dependence mildly suppresses onset but is
not expected to eliminate disputes.

```text
H_01 =
    a_01
  + b_01_surface * TradeSurface_AB
  + b_01_rivalry * Rivalry_AB
  + b_01_contiguity * Contiguity_AB
  + b_01_cap_shift * CapabilityShift_A
  - b_01_mutual * MutualDependence_AB
  - b_01_public * N_pub_A

h_01 = sigmoid(H_01)
```

Expected signs:

```text
b_01_surface > 0
b_01_rivalry > 0
b_01_contiguity > 0
b_01_cap_shift > 0
b_01_mutual >= 0 as a subtractive term
b_01_public > 0 as a subtractive term
```

### 6.2 T1 -> T2: Economic Coercion

Theory: sanctions and restrictions become more likely when A has asymmetric
economic leverage over B and can impose pain at lower relative cost.

```text
H_12 =
    a_12
  + b_12_leverage * TradeLeverage_A_over_B
  + b_12_import_lev * ImportLeverage_A_over_B
  + b_12_export_lev * ExportLeverage_A_over_B
  + b_12_surface * TradeSurface_AB
  + b_12_rivalry * Rivalry_AB
  + b_12_public * N_pub_A
  - b_12_self_cost * dep_A_on_B

h_12 = sigmoid(H_12)
```

Expected signs:

```text
b_12_leverage > 0
b_12_import_lev > 0
b_12_export_lev > 0
b_12_surface > 0
b_12_rivalry > 0
b_12_public >= 0
b_12_self_cost >= 0 as a subtractive term
```

### 6.3 T2 -> T3: Sanctions-to-Proxy Substitution

Theory: if economic coercion persists without resolution, actors may substitute
into indirect military pressure. Low mutual dependence and high rivalry make
substitution more likely.

```text
H_23 =
    a_23
  + b_23_t2_duration * Duration_T2
  + b_23_rivalry * Rivalry_AB
  + b_23_failed_coercion * CoercionPersistence_AB
  + b_23_proxy_access * ProxyOpportunity_AB
  - b_23_mutual * MutualDependence_AB
  - b_23_public * N_pub_A

h_23 = sigmoid(H_23)
```

Expected signs:

```text
b_23_t2_duration > 0
b_23_rivalry > 0
b_23_failed_coercion > 0
b_23_proxy_access > 0
b_23_mutual >= 0 as a subtractive term
b_23_public >= 0 as a subtractive term
```

### 6.4 T3 -> T4: Direct Military Escalation

Theory: direct escalation is more likely when proxy conflict is durable,
attribution is high, and geography or capability makes direct engagement
feasible. Mutual dependence suppresses direct force because it threatens
economic rupture.

```text
H_34 =
    a_34
  + b_34_attr_dur * Attribution_AB * Duration_T3
  + b_34_rivalry * Rivalry_AB
  + b_34_contiguity * Contiguity_AB
  + b_34_fma * FirstMoverAdvantage_A
  + b_34_closing * ClosingWindow_A
  - b_34_mutual * MutualDependence_AB
  - b_34_trade_cost * StrategicGoodsDependence_AB
  - b_34_public * N_pub_A

h_34 = sigmoid(H_34)
```

Expected signs:

```text
b_34_attr_dur > 0
b_34_rivalry > 0
b_34_contiguity > 0
b_34_fma > 0
b_34_closing > 0
b_34_mutual >= 0 as a subtractive term
b_34_trade_cost >= 0 as a subtractive term
b_34_public >= 0 as a subtractive term
```

### 6.5 T4 -> T5: Strategic War

Theory: strategic war requires reach and extreme stakes. Economic dependence
strongly suppresses escalation, but cannot fully block it when existential or
regime-survival stakes dominate.

```text
H_45 =
    a_45
  + b_45_reach * CapabilityReachGate_AB
  + b_45_rivalry * Rivalry_AB
  + b_45_fma * FirstMoverAdvantage_A
  + b_45_stakes * ExistentialStakes_A
  + b_45_mobilization * MobilizationDepth_A
  - b_45_mutual * EffectiveTradeCost_AB
  - b_45_public * N_pub_A

h_45_raw = sigmoid(H_45)
h_45 = h_45_raw * CapabilityReachGate_AB
```

The economic-cost term is capped by existential override:

```text
EffectiveTradeCost_AB = MutualDependence_AB * (1 - ExistentialOverride_A)
ExistentialOverride_A in [0, 1]
```

---

## 7. Skip Transitions

v28 explicitly models skip escalation rather than forcing all escalation through
adjacent rungs.

Candidate skip hazards:

```text
j_02 = T0 -> T2+
j_03 = T0 -> T3+
j_04 = T0 -> T4+
j_05 = T0 -> T5
j_13 = T1 -> T3+
j_14 = T1 -> T4+
j_15 = T1 -> T5
j_24 = T2 -> T4+
j_25 = T2 -> T5
j_35 = T3 -> T5
```

General form:

```text
J_km =
    s_km
  + l_structural * StructuralPressure_AB
  + l_shock * Shock_k
  + l_fma * FirstMoverAdvantage_A
  + l_reach * CapabilityReachGate_AB
  - l_mutual * MutualDependence_AB

j_km = sigmoid(J_km) * skip_decay(k, m)
skip_decay(k, m) = exp(-lambda_skip * ((m - k) - 1))
```

Large jumps are possible but penalized unless structural pressure is high.

---

## 8. De-Escalation and Persistence

v28 preserves the v27 status-quo bias. De-escalation must be earned through
off-ramps, mediation, exhaustion, or mutual economic pressure.

For current tier `k`:

```text
D_k =
    d_0
  + d_diplomatic * DiplomaticOffRamp_AB
  + d_mediation * Mediation_AB
  + d_mutual * MutualDependence_AB
  + d_public * N_pub_A
  - d_rivalry * Rivalry_AB
  - d_duration * Duration_k
```

Expected signs:

```text
MutualDependence raises de-escalation / settlement pressure.
Rivalry and duration suppress de-escalation.
```

Persistence remains duration-dependent:

```text
P_stay_k = base_persistence_k + duration_lock_in_k - shock_pressure - deesc_pressure
```

---

## 9. Composition Into Next-Tier Distribution

For current tier `k`, v28 allocates raw mass across:

```text
de-escalation
persistence
adjacent escalation
skip escalation
```

Then normalizes:

```text
pi_t = P(T_{t+1} = t), t in {0,1,2,3,4,5}
```

Example from current T2:

```text
raw_T0 = deescalate_to_T0
raw_T1 = deescalate_to_T1
raw_T2 = persistence_T2
raw_T3 = h_23 exact mass
raw_T4 = j_24 skip mass
raw_T5 = j_25 skip mass

pi = normalize(raw_T0..raw_T5)
```

---

## 10. Exact and Cumulative Outputs

v28 reports both adjacent exact and cumulative movement:

```text
P_exact(Tk -> T{k+1}) = pi[k+1]
P_cumulative(Tk -> T{k+1}+) = sum(pi[k+1:])
```

These are separate evaluation targets. Exact movement asks whether the model can
predict the next rung; cumulative movement asks whether the model can predict
movement to that rung or beyond.

---

## 11. Directed Reconciliation

Each actor scores a directed distribution:

```text
pi_A_over_B
pi_B_over_A
```

The dyad-level output follows v27 reconciliation logic:

```text
Upward mass: max(A_up, B_up)
Downward mass: min(A_down, B_down)
Persistence: residual mass
```

Economic leverage remains directed:

```text
TradeLeverage_A_over_B != TradeLeverage_B_over_A
```

This is essential because A may have sanction leverage over B even when the
dyad-level conflict tier is shared.

---

## 12. Data Pipeline Requirements

New build step:

```bash
python scripts/build/build_trade_interdependence.py
```

Expected output:

```text
data/processed/trade_interdependence_baci.csv
```

Required columns:

```text
year
initiator
target
exports_a_to_b
exports_b_to_a
imports_a_from_b
imports_b_from_a
total_trade_a
total_trade_b
dep_a_on_b
dep_b_on_a
mutual_trade_dependence
trade_surface
import_leverage_a_over_b
export_leverage_a_over_b
trade_leverage_a_over_b
strategic_goods_dependence_b_on_a
```

Then:

```bash
python scripts/build/build_features_v28.py
```

will join these fields to the v28 feature grid.

---

## 13. Backtest Plan

v28 should be evaluated in two windows.

Full historical fallback window:

```text
1946-2014
```

Trade-enhanced window:

```text
1995-2014
```

The trade-enhanced window uses BACI. The full window uses v27-compatible
features where trade data are unavailable. This avoids pretending BACI covers
the Cold War period before 1995.

Required metrics:

```text
Headline thresholds:
T0 -> T1+
T0 -> T4+
T0 -> T5
Any escalation

Adjacent exact transitions:
T0 -> T1
T1 -> T2
T2 -> T3
T3 -> T4
T4 -> T5

Adjacent cumulative transitions:
T0 -> T1+
T1 -> T2+
T2 -> T3+
T3 -> T4+
T4 -> T5

Skip transitions:
T0 -> T4+
T1 -> T4+
T2 -> T4+
T3 -> T5

Multi-year windows:
1-year
3-year
5-year
```

Upper-tier adjacent transitions are too sparse under one-year exact labels, so
3-year and 5-year windows are required diagnostics for T3->T4 and T4->T5.

---

## 14. Fallback Logic

If trade data are absent:

```text
TradeSurface = neutral default
MutualDependence = neutral default
TradeLeverage = neutral default
```

Then v28 degrades to:

```text
v27 diagnostic fallback + edge-specific non-trade hazards
```

If all v28-specific features are absent:

```text
v28 output = v27 output
```

This preserves graceful degradation.

---

## 15. Implementation Phases

### v28.0

Implement:

```text
edge-specific hazards
BACI aggregate trade features
trade surface
mutual dependence
directed leverage
1995-2014 trade-enhanced backtest
```

Primary expected improvements:

```text
T1 -> T2
T2 -> T3 cumulative
Any escalation
interpretability of economic-coercion forecasts
```

### v28.1

Implement:

```text
product-level strategic-goods dependence
substitutability / concentration metrics
trade shock features
multi-year rare-transition evaluation
```

---

## 16. Summary

v28 extends the v27 cost-field engine with transition-specific hazards and an
explicit economic-interdependence block. Trade is modeled as dual-use: it
increases the surface area for low-tier conflict and economic coercion, while
mutual dependence raises the cost of direct military escalation. Directed trade
leverage raises the probability of T1->T2 economic coercion, whereas mutual
dependence suppresses T3->T4 and T4->T5 unless overridden by existential stakes
or strategic reach.
