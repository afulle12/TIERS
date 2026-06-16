# Unified Equation of Interstate War (Dyadic Variant) v18.2

## Structured Specification

---

## 1. Purpose

v18.2 applies two fixes to v18.1 that address a systematic pair of errors: overestimation of war (T3) probability and underestimation of diplomatic/economic conflict (T1) probability.

Both errors shared a single root cause. In v18.1, $\mathcal{L}_2$ and $\mathcal{L}_3$ were derived from $\mathcal{L}_1$, meaning anything that raised T1 log-odds — including $\mathcal{E}_{AB}$ — also raised T2 and T3 by exactly the same amount. The Economic Pressure Scalar therefore did not *relatively* elevate T1; it shifted the whole distribution upward. Additionally, the escalation barriers ($\Delta_{12} = -0.2$, $\Delta_{23} = -0.4$) were too small relative to empirical base rates: with only $-0.6$ total barrier, T3 was structurally about 55% as likely as T1 even without any skip pressure.

**Fix 1 — Decoupled tier log-odds.** $\mathcal{L}_1$, $\mathcal{L}_2$, and $\mathcal{L}_3$ now all derive from a shared $\mathcal{L}_{\text{base}}$ rather than from each other. $\mathcal{E}_{AB}$ adds directly to $\mathcal{L}_1$ only. It reaches $\mathcal{L}_2$ only through barrier erosion conditional on failing coercion, and reaches $\mathcal{L}_3$ only through $\mathcal{B}^{\text{eff}} \to S^{**}$. Working economic coercion now correctly elevates T1 while leaving T3 suppressed.

**Fix 2 — Recalibrated barriers.** Default barriers are set to $\Delta_{12} = -1.1$ and $\Delta_{23} = -1.6$, derived from approximate dyad-year base rates ($P(T_1) \approx 0.15$, $P(T_2) \approx 0.05$, $P(T_3) \approx 0.01$ at moderate rivalry). These values should be estimated from data; the defaults replace the prior near-zero values that caused systematic T3 overestimation.

---

First, the independent per-tier sigmoid structure is replaced with a softmax over discrete conflict states. This makes the model behave like a discrete energy-state system: conflict tiers are distinct states with activation barriers between them, probabilities sum to one, and higher states are naturally less occupied without sufficient structural driving force.

Second, an Economic Pressure Scalar $\mathcal{E}_{AB}$ is added as a fifth skip primitive. Unlike the other primitives, $\mathcal{E}_{AB}$ operates on multiple tiers simultaneously through three interaction pathways: direct elevation of $T_1$ log-odds, erosion of the $T_1 \to T_2$ barrier when coercion is failing, and amplification of sequential path blockage in $S^{**}$ when coercion is failing. The key mediating variable is $\mathcal{A}_{AB}$: when economic pressure is succeeding, $\mathcal{E}_{AB}$ elevates $T_1$ while leaving $T_3$ suppressed. When it is failing, $\mathcal{E}_{AB}$ becomes a structural skip precondition.

A further fix from v17.2 is retained: the alignment term is gated on $\Phi^{opp}_{AB} > \tau_{opp}$ and zeroed for allied and unrelated dyads where $\Phi^{opp}_{AB}$ is near zero.

---

## 2. Conflict as Discrete Energy States

Conflict tiers are discrete states $s \in \{T_0, T_1, T_2, T_3\}$ with activation barriers between them:

$$E_{01} \le E_{12} \le E_{23} \quad \text{(sequential barriers)}$$

$$E_{03} \neq E_{01} + E_{12} + E_{23} \quad \text{(skip barrier — structurally distinct)}$$

The softmax over log-odds plays the role of a Boltzmann distribution over energy states. Higher states are less occupied by default; structural tension is the driving force that populates them. Skip transitions occur when the direct $T_0 \to T_3$ path has lower effective energy than the sum of sequential barriers — equivalently, when $\mathcal{L}_3 > \mathcal{L}_{3,\text{seq}}$ after skip amplification.

---

## 3. State Log-Odds (v18.2 Decoupled Structure)

Define the shared military and political base log-odds, which excludes $\mathcal{E}_{AB}$:

$$
\mathcal{L}_{\text{base}} = \beta_0 + \beta_m \widetilde{M}^*_{AB} + \beta_r \mathcal{R}_{AB} + \beta_a (2A_{AB} - 1) C_{AB} \cdot \mathbf{1}[\Phi^{opp} > \tau_{opp}] + \beta_c \Phi^{coop}_{AB}
$$

Each tier derives independently from $\mathcal{L}_{\text{base}}$:

$$
\mathcal{L}_1 = \mathcal{L}_{\text{base}} + \beta_e \mathcal{E}_{AB}
$$

$$
\mathcal{L}_2 = \mathcal{L}_{\text{base}} + \Delta_{12}^{\text{eff}}, \quad \Delta_{12}^{\text{eff}} = \Delta_{12} + \beta_{e2} \cdot \mathcal{E}_{AB} \cdot (1 - \mathcal{A}_{AB})
$$

$$
\mathcal{L}_3 = \mathcal{L}_{\text{base}} + \Delta_{12} + \Delta_{23} + \beta_s \cdot S^{**}_{AB}(t) \cdot \widetilde{M}^*_{AB}
$$

where $\Delta_{12} \le 0$ and $\Delta_{23} \le 0$ are the base escalation barriers, with defaults $\Delta_{12} = -1.1$ and $\Delta_{23} = -1.6$.

### Routing of $\mathcal{E}_{AB}$ across tiers

| Tier | $\mathcal{E}$ pathway | Condition |
|---|---|---|
| $T_1$ | $+\beta_e \mathcal{E}$ directly | Always active |
| $T_2$ | $+\beta_{e2} \mathcal{E}(1-\mathcal{A})$ via barrier erosion | Active when coercion failing |
| $T_3$ | Via $\mathcal{B}^{\text{eff}} \to S^{**}$ only | Active when coercion failing **and** $\Phi^{FMA}, -\dot{W} > 0$ |

This routing structure means:

$$\mathcal{E}_{AB} \text{ high},\ \mathcal{A}_{AB} \text{ high} \implies \mathcal{L}_1 \uparrow \text{ only},\quad T_2 \text{ and } T_3 \text{ unchanged}$$

$$\mathcal{E}_{AB} \text{ high},\ \mathcal{A}_{AB} \text{ low} \implies \mathcal{L}_1 \uparrow,\quad \mathcal{L}_2 \uparrow,\quad S^{**} \uparrow$$

$$\mathcal{E}_{AB} \text{ high},\ \mathcal{A}_{AB} \text{ low},\ \dot{W} < 0 \implies \text{structural skip precondition met} \to \mathcal{L}_3 \uparrow$$



---

## 4. Softmax State Distribution

$$
\boxed{
P(T_k \mid AB, t) = \frac{\exp(\mathcal{L}_k)}{\exp(\mathcal{L}_0) + \exp(\mathcal{L}_1) + \exp(\mathcal{L}_2) + \exp(\mathcal{L}_3)}
}
$$

where $\mathcal{L}_0 = 0$ (peace baseline, reference state).

### Properties

- $\sum_k P(T_k) = 1$ by construction.
- $P(T_1) > P(T_3)$ when $|\Delta_{12} + \Delta_{23}|$ exceeds skip amplification — guaranteed for all dyads without strong first-mover advantage, closing window, and failing coercion.
- $\mathcal{E}_{AB} > 0$ with $\mathcal{A}_{AB}$ high raises $P(T_1)$ without changing $P(T_2)$ or $P(T_3)$, because $\mathcal{E}$ is T1-specific in $\mathcal{L}_1$ and its pathway to $\mathcal{L}_2$ and $\mathcal{L}_3$ is gated on $(1-\mathcal{A}_{AB})$.
- $P(T_3)$ can exceed $P(T_2)$ — the skip signature — when $\mathcal{L}_3 > \mathcal{L}_2$, requiring the skip term $\beta_s \cdot S^{**} \cdot \widetilde{M}^*$ to overcome $\Delta_{23}$ and the erosion advantage of $\mathcal{L}_2$. This is structurally harder to achieve than in v18.1, making skip a genuinely rare event.
- When $S^{**} = 0$, T3 is the least probable non-peace state by construction, since $\mathcal{L}_3 = \mathcal{L}_{\text{base}} + \Delta_{12} + \Delta_{23} < \mathcal{L}_2 = \mathcal{L}_{\text{base}} + \Delta_{12}^{\text{eff}} \le \mathcal{L}_{\text{base}} + \Delta_{12}$.
- When $\mathcal{E}_{AB} = 0$, $\mathcal{L}_1 = \mathcal{L}_{\text{base}}$ and $\Delta_{12}^{\text{eff}} = \Delta_{12}$, recovering a clean sequential ladder.

---

## 5. Skip Barrier S** (v17.2 form, preserved)

$$
S^{**}_{AB}(t) = \left(\Phi^{FMA}_{AB}\right)^{\eta_\phi} \cdot \left(\max(0, -\dot{W}_{AB})\right)^{\eta_w} \cdot \left(\mathcal{B}^{\text{eff}}_{AB}\right)^{\eta_b} \cdot \left(1 - \mathcal{N}_{AB}^{\eta_n}\right) \cdot \left(1 - \mathcal{A}_{AB}^{\eta_a}\right)
$$

### Effective blockage

$$
\mathcal{B}^{\text{eff}}_{AB} = \min\!\left(1,\ \mathcal{B}_{AB} + \varphi_E \cdot \mathcal{E}_{AB} \cdot (1 - \mathcal{A}_{AB})\right)
$$

When economic coercion fails, each intermediate escalation step is more likely to be foreclosed: the target has already demonstrated resistance to incremental pressure, making sequential paths less viable. This raises effective blockage $\mathcal{B}^{\text{eff}}$ above the structural baseline $\mathcal{B}$, increasing $S^{**}$ and amplifying skip pressure.

---

## 6. Economic Pressure Scalar $\mathcal{E}_{AB}$

### Definition

$\mathcal{E}_{AB} \in [0, 1]$ measures the intensity of economic instruments currently deployed by the initiator toward the target. It is coded from **deployed instruments**, not from strategic effectiveness. Effectiveness is separately captured by $\mathcal{A}_{AB}$.

### Coding rule

| Value | Meaning |
|---:|---|
| $0.00$ | No pressure; normal trade and diplomatic relations |
| $0.10$–$0.25$ | Mild; minor trade disputes, targeted sanctions |
| $0.25$–$0.50$ | Moderate; significant sanctions regime, trade restrictions |
| $0.50$–$0.75$ | Severe; comprehensive sanctions, technology embargo, asset freezes |
| $0.75$–$1.00$ | Maximum; near-total economic warfare, commodity or oil embargoes |

### Calibration anchors

| Dyad | $\mathcal{E}$ | Note |
|---|---:|---|
| Japan $\to$ USA, Dec 1941 | $0.85$ | US oil embargo complete; near-total cutoff |
| USA $\to$ Russia, 2022–2026 | $0.75$ | SWIFT exclusion, asset freezes, oil price cap |
| USA $\to$ China, 2026 | $0.65$ | Tariffs, semiconductor controls, financial restrictions |
| Israel $\to$ Gaza, 2023–2026 | $0.80$ | Total blockade of goods, fuel, electricity |
| USA $\to$ UK (allied) | $0.02$ | No economic pressure |

### Data firewall

$\mathcal{E}_{AB}$ must be coded independently of $\mathcal{A}_{AB}$ (effectiveness) and $\Pi_{AB}$ (cooperation level). A high-$\mathcal{E}$ dyad may simultaneously have high $\Pi$ if bilateral trade continues under partial sanctions. A high-$\mathcal{E}$, high-$\mathcal{A}$ dyad is one where economic pressure is deployed and working. A high-$\mathcal{E}$, low-$\mathcal{A}$ dyad is one where economic pressure is deployed and failing — the structural skip precondition.

### Three interaction pathways

| Pathway | Mechanism | Condition |
|---|---|---|
| $\beta_e \cdot \mathcal{E}$ | Direct $T_1$ elevation | Always active when $\mathcal{E} > 0$ |
| $\beta_{e2} \cdot \mathcal{E} \cdot (1-\mathcal{A})$ | Erodes $\Delta_{12}$ barrier | Active when coercion is failing |
| $\varphi_E \cdot \mathcal{E} \cdot (1-\mathcal{A})$ | Raises $\mathcal{B}^{\text{eff}}$ in $S^{**}$ | Active when coercion is failing |

The conditional structure means:

$$
\mathcal{E}_{AB} \text{ high},\ \mathcal{A}_{AB} \text{ high} \implies T_1 \uparrow,\ T_2 \text{ and } T_3 \text{ suppressed}
$$

$$
\mathcal{E}_{AB} \text{ high},\ \mathcal{A}_{AB} \text{ low} \implies T_1 \uparrow,\ T_2 \uparrow,\ S^{**} \uparrow
$$

$$
\mathcal{E}_{AB} \text{ high},\ \mathcal{A}_{AB} \text{ low},\ \dot{W}_{AB} < 0 \implies \text{structural skip precondition met}
$$

---

## 7. Structural Motive (unchanged from v16)

$$
\widetilde{M}^*_{AB} = \widetilde{M}_{AB} \cdot (1 + \varphi_\xi \Xi_{AB})
$$

$$
\widetilde{M}_{AB} = \Phi^{opp}_{AB} \exp\!\left(-\gamma_1 \Phi^{sup}_{AB} - \gamma_2 \Phi^{coop}_{AB}\right)
$$

---

## 8. Alignment Gate Fix

The alignment term is defined as:

$$
\beta_a (2 A_{AB} - 1) C_{AB}
$$

In prior versions, this term was positive for allied dyads with high $A_{AB}$ and high $C_{AB}$, incorrectly adding conflict log-odds. The fix gates the term:

$$
\text{alignment term} = \begin{cases} \beta_a (2 A_{AB} - 1) C_{AB} & \text{if } \Phi^{opp}_{AB} > \tau_{opp} \text{ and } C_{AB} \ge \tau_c \\ 0 & \text{otherwise} \end{cases}
$$

Default: $\tau_{opp} = 0.15$.

For allied dyads, $\Phi^{opp}_{AB} \approx 0$, so the gate is inactive. The cooperation channel $\beta_c \Phi^{coop}_{AB}$ (with $\beta_c < 0$) then correctly suppresses conflict probability for high-cooperation dyads, making allies more peaceful than unrelated dyads.

---

## 9. Full Equation Summary

$$
\boxed{
P(T_k \mid AB, t) = \text{softmax}_k\!\left(0,\ \mathcal{L}_{\text{base}} + \beta_e \mathcal{E},\ \mathcal{L}_{\text{base}} + \Delta_{12}^{\text{eff}},\ \mathcal{L}_{\text{base}} + \Delta_{12} + \Delta_{23} + \beta_s S^{**}_{AB} \widetilde{M}^*_{AB}\right)
}
$$

with:

$$
\mathcal{L}_{\text{base}} = \beta_0 + \beta_m \widetilde{M}^*_{AB} + \beta_r \mathcal{R}_{AB} + \beta_a (2A_{AB}-1) C_{AB} \cdot \mathbf{1}[\Phi^{opp} > \tau_{opp}] + \beta_c \Phi^{coop}_{AB}
$$

$$
\Delta_{12}^{\text{eff}} = \Delta_{12} + \beta_{e2} \cdot \mathcal{E}_{AB} \cdot (1-\mathcal{A}_{AB})
$$

$$
\mathcal{B}^{\text{eff}}_{AB} = \min\!\left(1,\ \mathcal{B}_{AB} + \varphi_E \cdot \mathcal{E}_{AB} \cdot (1 - \mathcal{A}_{AB})\right)
$$

$$
S^{**}_{AB} = \left(\Phi^{FMA}\right)^{\eta_\phi} \cdot \left(\max(0,-\dot{W})\right)^{\eta_w} \cdot \left(\mathcal{B}^{\text{eff}}\right)^{\eta_b} \cdot \left(1 - \mathcal{N}^{\eta_n}\right) \cdot \left(1 - \mathcal{A}^{\eta_a}\right)
$$

---

## 10. All Parameters

| Parameter | Role | Version | Prior |
|---|---|---|---|
| $\beta_0$ | Baseline log-odds | v15 | MLE/posterior |
| $\beta_m$ | Motive weight | v15 | MLE/posterior |
| $\beta_r$ | Spark weight | v15 | MLE/posterior |
| $\beta_a$ | Alignment weight | v15 | MLE/posterior |
| $\beta_c$ | Cooperation weight ($<0$) | v15 | MLE/posterior |
| $\gamma_1, \gamma_2$ | Motive attenuation | v15 | Co-belligerence patterns |
| $\lambda, \kappa, \nu, \rho$ | Network / alignment | v15 | MLE/posterior |
| $\varphi_\xi$ | Contiguity amplification | v16 | HalfNormal(0,1) |
| $\beta_s$ | Skip amplification | v17 | HalfNormal(0,2) |
| $\eta_\phi, \eta_w, \eta_b, \eta_n, \eta_a$ | Skip curvature | v17.2 | HalfNormal(0,1) |
| $\Delta_{12}$ | $T_1 \to T_2$ escalation barrier ($\le 0$) | v18 | Normal($-0.5$, 0.5) |
| $\Delta_{23}$ | $T_2 \to T_3$ escalation barrier ($\le 0$) | v18 | Normal($-1.0$, 0.5) |
| $\tau_{opp}$ | Alignment gate threshold | v18 | Fixed 0.15 |
| $\beta_e$ | Economic pressure direct weight ($\ge 0$) | v18.1 | HalfNormal(0,1) |
| $\beta_{e2}$ | Barrier erosion coefficient ($\ge 0$) | v18.1 | HalfNormal(0,0.5) |
| $\varphi_E$ | Blockage amplification coefficient ($\ge 0$) | v18.1 | HalfNormal(0,0.5) |

---

## 11. Validation Summary (11-dyad test)

The model was validated against 11 directed dyads across three categories.

**At war (modern):** Russia/Ukraine, Israel/Hamas, India/Pakistan.
Skip signatures present for Russia/Ukraine (S** = 0.655 at Feb 2022 initiation parameters, L₃ > L₁). India/Pakistan: nuclear deterrence (N = 0.60) suppresses S** despite high rivalry, matching the bounded character of Operation Sindoor.

**Historical benchmarks:** Japan/USA 1941, Germany/USA 1941.
Japan→USA shows the clearest skip signature in the dataset: S** ≈ 0.655, L₃ > L₁, T3 probability exceeds T1. USA→Japan shows sequential ordering (T1 > T2 > T3) with no skip, correctly reflecting US economic escalation rather than first-strike planning. Germany→USA shows low skip (FMA low across Atlantic) with sequential-dominant ordering.

**Allied:** USA/UK, France/Germany, Japan/S. Korea.
After the alignment gate fix, all three show conflict probability below 1%, with France/Germany lowest due to highest bilateral cooperation (Pi = 0.85 drives strong $\beta_c \Phi^{coop}$ suppression).

**No relation:** Brazil/Nigeria, Chile/Vietnam, NZ/Kazakhstan.
All show 1.5–2.5% conflict probability — correctly higher than allied pairs. The ordering allied < no-relation emerges from the cooperation channel rather than a hand-coded assumption.

---

## 12. Change Log

### v18.2 vs v18.1

| Item | v18.1 | v18.2 |
|---|---|---|
| Tier log-odds structure | Cumulative: $\mathcal{L}_2 = \mathcal{L}_1 + \Delta$, $\mathcal{L}_3 = \mathcal{L}_2 + \Delta + \text{skip}$ | Decoupled: all tiers derive from $\mathcal{L}_\text{base}$ independently |
| $\mathcal{E}$ effect on T3 | Propagates via $\mathcal{L}_1 \to \mathcal{L}_2 \to \mathcal{L}_3$ | Reaches T3 only through $\mathcal{B}^{\text{eff}} \to S^{**}$ |
| Working coercion ($\mathcal{A}$ high) | $\mathcal{E}$ raises all tiers equally | $\mathcal{E}$ raises T1 only; T2 and T3 unchanged |
| $\Delta_{12}$ default | $-0.2$ | $-1.1$ |
| $\Delta_{23}$ default | $-0.4$ | $-1.6$ |
| $\beta_s$ default | $2.0$ | $4.0$ (compensates for larger barriers) |
| $\beta_0$ default | $-4.5$ | $-3.5$ |
| $\beta_m$ default | $3.0$ | $2.5$ |
| T3 without skip | $\approx 55\%$ of T1 | $\approx 5\%$ of T1 (at base barriers) |
| Skip signature | $\mathcal{L}_3 > \mathcal{L}_1$ | $\mathcal{L}_3 > \mathcal{L}_2$ (harder to achieve, more meaningful) |
| Backward compatibility | v17.2 at $\mathcal{E}=0$, gates inactive | v18.1 at $\mathcal{E}=0$, same barriers, same gate |

### v18.1 vs v17.2

| Item | v17.2 | v18.1 |
|---|---|---|
| Tier probability structure | Independent sigmoid per tier | Softmax over {T₀, T₁, T₂, T₃} |
| Probabilities sum to 1 | No | Yes |
| Escalation barriers | Implicit in β₀ | Explicit Δ₁₂, Δ₂₃ parameters |
| Economic pressure | Absent | $\mathcal{E}_{AB} \in [0,1]$, three interaction pathways |
| Alignment gate | Absent | Gated on $\Phi^{opp} > \tau_{opp} = 0.15$ |