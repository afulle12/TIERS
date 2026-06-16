# Unified Equation of Interstate War (Dyadic Variant) v17
*Structured Specification*

---

## 1. Purpose

v17 introduces the **Skip Barrier** — a set of four primitives that together capture the structural conditions enabling a dyad to transition directly from peace or diplomatic tension to active war (T0→T3 or T1→T3) without traversing the intermediate militarized MID tier. All v16 primitives are preserved unchanged. The skip mechanism is grounded in a quantum-mechanical analogy: conflict tiers are treated as discrete energy states with activation barriers between them; skip transitions occur when the skip barrier $E_{03}$ is structurally lower than the sum of sequential barriers, and when structural tension $\Sigma_{AB}$ is sufficient to breach it.

The skip term is multiplicative with $\widetilde{M}^*_{AB}$, ensuring skip pressure amplifies existing structural motive rather than generating war risk independently.

---

## 2. Theoretical Foundation: Conflict as Energy States

Conflict tiers are discrete states $s \in \{T0, T1, T2, T3\}$ with activation barriers between them:

$$E_{01} \leq E_{12} \leq E_{23} \quad \text{(sequential barriers)}$$

$$E_{03} \neq E_{01} + E_{12} + E_{23} \quad \text{(skip barrier — structurally distinct)}$$

**Skip transitions** (e.g., Pearl Harbor 1941, Korea 1950, Russia-Ukraine February 2022) occur when $E_{03} < E_{12} + E_{23}$ — i.e., it is structurally easier to jump directly to T3 than to escalate through intermediate states. The key insight: sequential escalation destroys the conditions (surprise, decisive first-strike) that make the skip payoff achievable. Skip is not just preferable — for some dyads under some conditions, it is the only feasible path to the initiator's objective.

**Dyadic entanglement**: A and B share a joint conflict state $s_{AB}(t)$. Neither directed measurement ($p_{AB}$ or $p_{BA}$) alone captures the joint tension. The skip barrier adds structure to the joint state by identifying which transitions are structurally available.

---

## 3. All Primitives (v15 → v17 cumulative)

| Primitive | Symbol | Domain | Version |
|---|---|---|---|
| Rivalry attribute vector | $\vec{\Omega}_{AB}$ | $[0,1]^6$ | v15 |
| Scalarized rivalry | $\Omega_{AB,k}$ | $[0,1]$ | v15 |
| Alliance depth | $\Gamma_{AB,k}$ | $[0,1]$ | v15 |
| Non-alliance cooperation | $\Pi_{AB}$ | $[0,1]$ | v15 |
| Contiguity motive | $\Xi_{AB}$ | $\{0, 0.5, 1\}$ | v16 |
| **First-mover advantage** | $\Phi^{FMA}_{AB}$ | $[0,1]$ | **v17** |
| **Window velocity** | $\dot{W}_{AB}(t)$ | $[-1,1]$ | **v17** |
| **Sequential path blockage** | $\mathcal{B}_{AB}$ | $[0,1]$ | **v17** |
| **Nuclear/existential deterrence** | $\mathcal{N}_{AB}$ | $[0,1]$ | **v17** |

---

## 4. Skip Barrier Primitives (New in v17)

### 4.1 First-Mover Advantage — $\Phi^{FMA}_{AB} \in [0,1]$

How decisive is striking first for the initiator versus any sequential escalation path?

- **High** when: the target's primary defensive capability can be neutralized in the initial strike; surprise is geometrically achievable; target's recovery capacity is low.
- **Near-zero** when: the target has credible nuclear second-strike capability (second-strike eliminates the category of decisive FMA, not just raises its cost).
- **Data source**: Military balance assessments, strike-capability evaluations, force posture analysis. Distinct from $\Omega_{AB}$ (which measures rivalry intensity, not payoff asymmetry of first strike).

### 4.2 Window Velocity — $\dot{W}_{AB}(t) \in [-1, 1]$

Rate of change of the initiator's relative strategic position. Negative = window closing; positive = window opening.

- **Negative** (window closing) when: adversary is arming faster, a threatening alliance is solidifying, initiator's domestic political window is narrowing, or a military technology gap is eroding.
- **Positive** (window opening): initiator growing relatively stronger — no skip urgency.
- Only $\max(0, -\dot{W}_{AB})$ enters $S_{AB}$: opening windows contribute nothing to skip pressure.
- **Data source**: Time-series trends in relative military expenditure, alliance trajectory, economic trajectory. Distinct from $R_{h,AB}$ (realized history) and $\Omega_{AB,k}$ (current level).

### 4.3 Sequential Path Blockage — $\mathcal{B}_{AB} \in [0,1]$

The degree to which escalating through intermediate tiers forecloses the initiator's T3 objective.

- **High** when: each intermediate step alerts the defender (activating defenses and alliances), destroys surprise, allows the target to mobilize forces that close the FMA window, or politically commits third parties against the initiator.
- **Low** when: sequential escalation is feasible without degrading the final military objective; the target has poor early warning; intermediate steps don't activate alliance commitments.
- This is why skip transitions involve surprise structurally, not incidentally.

### 4.4 Nuclear / Existential Deterrence — $\mathcal{N}_{AB} \in [0,1]$

The credibility of second-strike deterrence extended to the target.

- **$\mathcal{N}_{AB} = 1$**: The target has a fully credible nuclear second-strike capability. This structurally eliminates $\Phi^{FMA}_{AB}$ by guaranteeing retaliation — and thereby drives $S_{AB} \to 0$ regardless of other conditions.
- **$\mathcal{N}_{AB} = 0$**: Target has no nuclear protection (no own weapons, no credible extended deterrence).
- **$0 < \mathcal{N}_{AB} < 1$**: Extended deterrence of contested credibility (e.g., Taiwan under US umbrella).
- **Critical distinction**: $\mathcal{N}_{AB}$ suppresses specifically the *skip* transition. It does not prevent T2→T3 sequential escalation, which is suppressed by cost calculation rather than structural elimination of FMA. This is why nuclear-armed dyads have had limited conflicts (Kargil 1999) but no confirmed T0→T3 skip transitions.

---

## 5. Skip Pressure Scalar

$$\boxed{S_{AB}(t) = \Phi^{FMA}_{AB} \cdot \max(0,\, -\dot{W}_{AB}(t)) \cdot \mathcal{B}_{AB} \cdot (1 - \mathcal{N}_{AB})}$$

**Multiplicative structure**: All four conditions must be simultaneously non-zero for skip pressure to exist. Any single factor near zero kills $S_{AB}$ regardless of the others. This sparsity is correct — skip transitions are rare events.

$S_{AB}(t) \in [0,1]$, with values above 0.15 indicating meaningful skip risk and above 0.30 indicating high skip pressure.

**Calibration examples**:

| Dyad | $\Phi^{FMA}$ | $\max(0,-\dot{W})$ | $\mathcal{B}$ | $1-\mathcal{N}$ | $S_{AB}$ |
|---|---|---|---|---|---|
| Russia→Ukraine (Feb 2022 onset) | 0.70 | 0.60 | 0.60 | 1.00 | **0.252** |
| China→Taiwan (2026) | 0.50 | 0.40 | 0.70 | 0.40 | 0.056 |
| DPRK→ROK (2026) | 0.40 | 0.30 | 0.50 | 0.15 | 0.009 |
| US→Russia (any) | — | — | — | ≈0.05 | ≈0.000 |

---

## 6. Modified Structural Motive (from v16)

$$\widetilde{M}^*_{AB} = \widetilde{M}_{AB} \cdot (1 + \varphi_\xi\,\Xi_{AB})$$

where $\widetilde{M}_{AB} = \Phi^{opp}_{AB}\exp\!\big(-\gamma_1\Phi^{sup}_{AB} - \gamma_2\Phi^{coop}_{AB}\big)$ from v15.

---

## 7. Final Unified Equation (v17)

$$\boxed{p_{AB}(t) = \Lambda\!\Bigg(\underbrace{\beta_0 + \beta_r\mathcal{R}_{AB} + \beta_m\widetilde{M}^*_{AB} + \beta_a(2A_{AB}-1)C_{AB} + \beta_c\Phi^{coop}_{AB}}_{\text{sequential pressure (v15/v16)}} + \underbrace{\beta_s \cdot S_{AB}(t) \cdot \widetilde{M}^*_{AB}}_{\text{skip amplifier (v17)}}\Bigg)}$$

**Skip term properties**:
- When $S_{AB} = 0$: skip term vanishes; equation reduces exactly to v16.
- When $S_{AB} > 0$: skip amplifies $\widetilde{M}^*_{AB}$ multiplicatively — structural motive under skip pressure.
- $\beta_s \geq 0$; suggested prior $\beta_s \sim \text{HalfNormal}(0, 2)$.
- Default operational value: $\beta_s = 2.0$.

---

## 8. All Parameters

| Parameter | Role | Version | Estimation |
|---|---|---|---|
| $\beta_0$ | Baseline log-odds | v15 | MLE/posterior |
| $\beta_m$ | Motive weight | v15 | MLE/posterior |
| $\beta_r$ | Spark weight | v15 | MLE/posterior |
| $\beta_a$ | Alignment weight | v15 | MLE/posterior |
| $\beta_c$ | Cooperation weight | v15 | MLE/posterior |
| $\gamma_1, \gamma_2$ | Motive attenuation | v15 | Co-belligerence patterns |
| $\delta$ | Spark decay rate | v15 | Survival analysis |
| $\lambda, \kappa, \nu, \rho$ | Network/alignment | v15 | MLE/posterior |
| $\boldsymbol{\theta}_k$ | Rivalry scalarization | v15 | Pre-estimated Cox |
| $\varphi_\xi$ | Contiguity amplification | v16 | MLE/posterior; HalfNormal(0,1) |
| $\beta_s$ | **Skip amplification** | **v17** | **MLE/posterior; HalfNormal(0,2)** |

---

## 9. Data Firewalls

| Variable pair | Firewall requirement |
|---|---|
| $\Omega_{AB}$ vs $R_{h,AB}$ | VIF < 5; $R_h$ from realized MIDs only, $\Omega$ from structural codings |
| $\Xi_{AB}$ vs $\omega_{AB,1}$ | VIF < 5; $\Xi$ from cartographic sources only |
| $\Phi^{FMA}_{AB}$ vs $\Omega_{AB}$ | $\Phi^{FMA}$ from military balance data; not from rivalry assessments |
| $\dot{W}_{AB}$ vs $R_{h,AB}$ | $\dot{W}$ from capability trend data; not from event history |

---

## 10. Change Log

### v17 vs v16

| Item | v16 | v17 |
|---|---|---|
| Skip barrier | Absent | $S_{AB} = \Phi^{FMA} \cdot \max(0,-\dot{W}) \cdot \mathcal{B} \cdot (1-\mathcal{N})$ |
| Final equation | Sequential pressure only | + $\beta_s \cdot S_{AB} \cdot \widetilde{M}^*_{AB}$ |
| New primitives | — | $\Phi^{FMA}, \dot{W}, \mathcal{B}, \mathcal{N}$ |
| New parameter | — | $\beta_s \geq 0$ |
| Nuclear deterrence | Not modeled | $\mathcal{N}_{AB}$ zeros skip for nuclear dyads |
| Skip vs sequential | Conflated | Structurally separated |
| Backward compatibility | v15 recovers with $\varphi_\xi=0, \Xi=0$ | v16 recovers with $\beta_s=0$ or $S_{AB}=0$ |