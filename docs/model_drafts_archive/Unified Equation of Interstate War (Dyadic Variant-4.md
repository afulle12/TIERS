# Unified Equation of Interstate War (Dyadic Variant) v17.2

## Structured Specification

## 1. Purpose

v17.2 retains Alternative Objective Achievement ($\mathcal{A}_{AB}$) as the fifth multiplicative factor on the skip barrier, but implements two form changes to improve realism and estimation.

First, $\mathcal{A}_{AB}$ is no longer restricted to the discrete set $\{0, 0.33, 0.67, 1\}$. It is now continuous on $[0,1]$, allowing the model to represent partial strategic success by lower-tier tools with finer resolution.

Second, the skip barrier no longer assumes symmetric linear effects across all primitives. Each component now enters with its own nonnegative curvature parameter, allowing some forces, especially nuclear deterrence, to suppress skip pressure more sharply than others raise it.

The theoretical logic remains unchanged: a state does not skip to T3 if sub-T3 instruments are already achieving its strategic objectives, and a skip transition is most likely when decisive first-mover gains, a closing window, and blocked sequential paths coincide under weak deterrence.

## 2. Skip Barrier — Full Specification (v17.2)

$$
\boxed{
S^{**}_{AB}(t)
=
\left(\Phi^{FMA}_{AB}\right)^{\eta_\phi}
\cdot
\left(\max(0,-\dot{W}_{AB}(t))\right)^{\eta_w}
\cdot
\left(\mathcal{B}_{AB}\right)^{\eta_b}
\cdot
\left(1-\mathcal{N}_{AB}^{\,\eta_n}\right)
\cdot
\left(1-\mathcal{A}_{AB}^{\,\eta_a}\right)
}
$$

where

$$
\eta_\phi,\eta_w,\eta_b,\eta_n,\eta_a \ge 0
$$

are estimable shape parameters.

### Interpretation

- $\eta_\phi$ controls curvature of first-mover advantage.
- $\eta_w$ controls curvature of closing-window pressure.
- $\eta_b$ controls curvature of sequential path blockage.
- $\eta_n$ controls how sharply deterrence suppresses skip pressure.
- $\eta_a$ controls how sharply effective lower-tier alternatives suppress skip pressure.

### Special cases

- If all $\eta = 1$, v17.2 reduces exactly to the v17.1 functional form, except with continuous $\mathcal{A}_{AB}$.
- If $\mathcal{A}_{AB} = 1$, then $S^{**}_{AB}(t) = 0$ regardless of all other terms.
- If $\mathcal{N}_{AB} = 1$, then $S^{**}_{AB}(t) = 0$ regardless of all other terms.
- If $\max(0,-\dot{W}_{AB}(t)) = 0$, then skip pressure is zero regardless of the other terms.

All five factors remain multiplicative. Any one factor near zero still strongly suppresses skip pressure, but the exponents allow this suppression to be sharper or flatter depending on the data.

### Primitives

| Primitive | Symbol | Domain | Role |
|---|---|---:|---|
| First-mover advantage | $\Phi^{FMA}_{AB}$ | $[0,1]$ | How decisive is striking first vs. any sequential path? |
| Window velocity | $\dot{W}_{AB}(t)$ | $[-1,1]$ | Rate of change of initiator's strategic position (neg = closing) |
| Sequential path blockage | $\mathcal{B}_{AB}$ | $[0,1]$ | Does gradual escalation foreclose the skip objective? |
| Nuclear deterrence | $\mathcal{N}_{AB}$ | $[0,1]$ | Credible second-strike extended to target; suppresses skip pressure |
| Alternative achievement | $\mathcal{A}_{AB}$ | $[0,1]$ | Are sub-T3 tools currently achieving the initiator's objectives? |

### Shape parameters

| Parameter | Domain | Role |
|---|---:|---|
| $\eta_\phi$ | $[0,\infty)$ | Curvature on $\Phi^{FMA}_{AB}$ |
| $\eta_w$ | $[0,\infty)$ | Curvature on closing-window term |
| $\eta_b$ | $[0,\infty)$ | Curvature on $\mathcal{B}_{AB}$ |
| $\eta_n$ | $[0,\infty)$ | Sharpness of deterrence suppression |
| $\eta_a$ | $[0,\infty)$ | Sharpness of alternative-achievement suppression |

## 3. $\mathcal{A}_{AB}$ Coding Rule (Continuous in v17.2)

$\mathcal{A}_{AB}$ is coded on the full interval $[0,1]$ from strategic effectiveness assessment, not from tool availability.

### Anchor guidance

| Value | Meaning |
|---:|---|
| $0.00$ | No viable alternative path; objectives require military force |
| $0.10$–$0.25$ | Alternatives exist but are strategically weak |
| $0.25$–$0.50$ | Alternatives achieving limited measurable gains |
| $0.50$–$0.75$ | Alternatives substantially achieving objectives |
| $0.75$–$0.90$ | Alternatives nearly sufficient |
| $1.00$ | Alternatives fully achieving objectives; skip unnecessary |

### Coding rule

Code from observed strategic effect, not policy deployment. Sanctions imposed but not changing target behavior imply low $\mathcal{A}_{AB}$. Economic coercion, cyber disruption, proxy conflict, or political subversion producing measurable strategic concessions imply higher $\mathcal{A}_{AB}$.

### Data firewall

$\mathcal{A}_{AB}$ must be coded from strategic outcome assessments independent of $\Pi_{AB}$ (cooperation level) and $\Psi_{AB}$ (gray-zone intensity). A high $\mathcal{A}_{AB}$ requires evidence that lower-tier tools are producing the desired strategic effect, not merely that they are active.

## 4. Final Unified Equation (v17.2)

$$
\boxed{
p_{AB}(t)
=
\Lambda\!\Bigg(
\beta_0
+
\beta_r\mathcal{R}_{AB}
+
\beta_m\widetilde{M}^{*}_{AB}
+
\beta_a(2A_{AB}-1)C_{AB}
+
\beta_c\Phi^{coop}_{AB}
+
\beta_s \cdot S^{**}_{AB}(t)\cdot \widetilde{M}^{*}_{AB}
\Bigg)
}
$$

where

$$
\widetilde{M}^{*}_{AB}
=
\widetilde{M}_{AB}(1+\varphi_\xi \Xi_{AB})
$$

from v16, and $S^{**}_{AB}(t)$ is the full five-factor nonlinear skip scalar.

## 5. Calibration Reference

Illustrative only; exact values depend on estimated shape parameters.

| Dyad | $\Phi^{FMA}$ | $\max(0,-\dot{W})$ | $\mathcal{B}$ | $1-\mathcal{N}^{\eta_n}$ | $1-\mathcal{A}^{\eta_a}$ | $S^{**}$ |
|---|---:|---:|---:|---:|---:|---|
| Russia $\rightarrow$ Ukraine (Feb 2022 onset) | 0.70 | 0.60 | 0.60 | 1.00 | 1.00 | High under most plausible $\eta$ |
| Russia $\rightarrow$ Ukraine (2026 ongoing) | 0.30 | 0.20 | 0.20 | 1.00 | Depends on continuous $\mathcal{A}$ | Low |
| China $\rightarrow$ Taiwan (2026) | 0.50 | 0.40 | 0.70 | Suppressed by deterrence curvature | Suppressed by alternative-effectiveness curvature | Low-to-moderate |
| US $\rightarrow$ China (2026) | 0.30 | 0.20 | 0.40 | Near-zero under strong deterrence curvature | Further suppressed if $\mathcal{A} > 0$ | Very low |
| Japan $\rightarrow$ USA (2026) | 0.10 | 0.00 | 0.30 | Near-zero | Near-zero | $\approx 0$ |
| US-Russia (nuclear dyad) | — | — | — | Near-zero under high $\mathcal{N}$ | — | $\approx 0$ |

## 6. Change Log

### v17.2 vs v17.1

| Item | v17.1 | v17.2 |
|---|---|---|
| Alternative achievement | $\mathcal{A}_{AB} \in \{0,0.33,0.67,1\}$ | $\mathcal{A}_{AB} \in [0,1]$ |
| Skip barrier | Symmetric linear multiplicative form | Nonlinear multiplicative form with estimated exponents |
| Deterrence effect | $(1-\mathcal{N}_{AB})$ | $(1-\mathcal{N}_{AB}^{\eta_n})$ |
| Alternative suppression | $(1-\mathcal{A}_{AB})$ | $(1-\mathcal{A}_{AB}^{\eta_a})$ |
| Other skip terms | Linear | Curved via $\eta_\phi,\eta_w,\eta_b$ |
| Theoretical basis | Skip possible and necessary? | Same, but with graded necessity and asymmetric suppression |
| Backward compatibility | v17 recovers at $\mathcal{A}_{AB}=0$ everywhere | v17.1 recovers when $\eta_\phi=\eta_w=\eta_b=\eta_n=\eta_a=1$ |

---

## Structured Specification

## 1. Purpose

v17 introduced the Skip Barrier, a set of four primitives that together capture the structural conditions enabling a dyad to transition directly from peace or diplomatic tension to active war ($T0 \rightarrow T3$ or $T1 \rightarrow T3$) without traversing the intermediate militarized MID tier. v17.1 added Alternative Objective Achievement ($\mathcal{A}_{AB}$) to distinguish whether a skip is not only possible but necessary. v17.2 preserves all prior primitives but generalizes the barrier's functional form.

Conflict tiers remain discrete energy states with activation barriers between them; skip transitions occur when the direct barrier is structurally lower than the sum of sequential barriers, and when structural tension is sufficient to breach it. v17.2 keeps this logic but allows the empirical data to determine whether some primitives matter linearly, sharply, or only beyond threshold-like ranges.

## 2. Theoretical Foundation: Conflict as Energy States

Conflict tiers are discrete states $s \in \{T0, T1, T2, T3\}$ with activation barriers between them:

$$
E_{01} \le E_{12} \le E_{23}
\quad \text{(sequential barriers)}
$$

$$
E_{03} \neq E_{01}+E_{12}+E_{23}
\quad \text{(skip barrier — structurally distinct)}
$$

Skip transitions (e.g., Pearl Harbor 1941, Korea 1950, Russia-Ukraine February 2022) occur when $E_{03} < E_{12}+E_{23}$, i.e., it is structurally easier to jump directly to T3 than to escalate through intermediate states. The key insight remains that sequential escalation can destroy the conditions (surprise, decisive first strike, coercive timing) that make the skip payoff achievable. v17.2 adds the further claim that the effects of these structural conditions need not be linear or symmetric.

Dyadic entanglement: A and B share a joint conflict state $s_{AB}(t)$. Neither directed measurement ($p_{AB}$ or $p_{BA}$) alone captures the joint tension. The skip barrier adds structure to the joint state by identifying which transitions are structurally available and how strongly each prerequisite matters.

## 3. All Primitives (v15 → v17.2 cumulative)

| Primitive | Symbol | Domain | Version |
|---|---|---:|---|
| Rivalry attribute vector | $\vec{\Omega}_{AB}$ | $[0,1]^6$ | v15 |
| Scalarized rivalry | $\Omega_{AB,k}$ | $[0,1]$ | v15 |
| Alliance depth | $\Gamma_{AB,k}$ | $[0,1]$ | v15 |
| Non-alliance cooperation | $\Pi_{AB}$ | $[0,1]$ | v15 |
| Contiguity motive | $\Xi_{AB}$ | $\{0, 0.5, 1\}$ | v16 |
| First-mover advantage | $\Phi^{FMA}_{AB}$ | $[0,1]$ | v17 |
| Window velocity | $\dot{W}_{AB}(t)$ | $[-1,1]$ | v17 |
| Sequential path blockage | $\mathcal{B}_{AB}$ | $[0,1]$ | v17 |
| Nuclear/existential deterrence | $\mathcal{N}_{AB}$ | $[0,1]$ | v17 |
| Alternative objective achievement | $\mathcal{A}_{AB}$ | $[0,1]$ | v17.1, continuous in v17.2 |

## 4. Skip Barrier Primitives

### 4.1 First-Mover Advantage — $\Phi^{FMA}_{AB} \in [0,1]$

How decisive is striking first for the initiator versus any sequential escalation path?

High when: the target's primary defensive capability can be neutralized in the initial strike; surprise is geometrically achievable; target's recovery capacity is low.

Near-zero when: the target has credible second-strike capacity or rapid force regeneration that eliminates decisive first-move payoff.

### 4.2 Window Velocity — $\dot{W}_{AB}(t) \in [-1,1]$

Rate of change of the initiator's relative strategic position. Negative = window closing; positive = window opening.

Only $\max(0,-\dot{W}_{AB}(t))$ enters the skip barrier: opening windows do not generate skip pressure.

### 4.3 Sequential Path Blockage — $\mathcal{B}_{AB} \in [0,1]$

The degree to which escalating through intermediate tiers forecloses the initiator's T3 objective.

High when: each intermediate step alerts the defender, activates alliances, destroys surprise, permits mobilization, or closes the FMA window.

### 4.4 Nuclear / Existential Deterrence — $\mathcal{N}_{AB} \in [0,1]$

The credibility of second-strike deterrence extended to the target.

- $\mathcal{N}_{AB}=1$ implies fully credible second-strike protection.
- $\mathcal{N}_{AB}=0$ implies no nuclear protection.
- Intermediate values represent contested or partial deterrent credibility.

In v17.2, deterrence enters nonlinearly through $1-\mathcal{N}_{AB}^{\eta_n}$, allowing the data to determine whether deterrence has a gradual or threshold-like suppressive effect on skip transitions.

### 4.5 Alternative Objective Achievement — $\mathcal{A}_{AB} \in [0,1]$

The degree to which lower-tier tools are currently achieving the initiator's objectives.

- $\mathcal{A}_{AB}=0$ means military force remains necessary.
- $\mathcal{A}_{AB}=1$ means lower-tier tools already achieve the objective fully.

In v17.2, alternatives enter nonlinearly through $1-\mathcal{A}_{AB}^{\eta_a}$, allowing the suppressive effect of lower-tier success to be gradual or sharply thresholded.

## 5. Skip Pressure Scalar

$$
\boxed{
S^{**}_{AB}(t)
=
\left(\Phi^{FMA}_{AB}\right)^{\eta_\phi}
\cdot
\left(\max(0,-\dot{W}_{AB}(t))\right)^{\eta_w}
\cdot
\left(\mathcal{B}_{AB}\right)^{\eta_b}
\cdot
\left(1-\mathcal{N}_{AB}^{\,\eta_n}\right)
\cdot
\left(1-\mathcal{A}_{AB}^{\,\eta_a}\right)
}
$$

Multiplicative structure is preserved: all conditions must still be jointly present for skip pressure to be substantial. But the estimated exponents allow some factors to matter sharply and others more gradually. This makes the model less rigid while preserving the underlying skip logic.

$S^{**}_{AB}(t) \in [0,1]$. Practical thresholds should be empirically estimated rather than fixed a priori, because nonlinear curvature means the same raw primitive scores may imply different effective skip pressure across estimated parameterizations.

## 6. Modified Structural Motive (from v16)

$$
\widetilde{M}^{*}_{AB}
=
\widetilde{M}_{AB}\cdot(1+\varphi_\xi \Xi_{AB})
$$

where

$$
\widetilde{M}_{AB}
=
\Phi^{opp}_{AB}\exp\!\big(-\gamma_1\Phi^{sup}_{AB}-\gamma_2\Phi^{coop}_{AB}\big)
$$

from v15.

## 7. Final Unified Equation (v17.2)

$$
\boxed{
p_{AB}(t)
=
\Lambda\!\Bigg(
\underbrace{
\beta_0
+
\beta_r\mathcal{R}_{AB}
+
\beta_m\widetilde{M}^{*}_{AB}
+
\beta_a(2A_{AB}-1)C_{AB}
+
\beta_c\Phi^{coop}_{AB}
}_{\text{sequential pressure (v15/v16)}}
+
\underbrace{
\beta_s\cdot S^{**}_{AB}(t)\cdot \widetilde{M}^{*}_{AB}
}_{\text{skip amplifier (v17.2)}}
\Bigg)
}
$$

### Skip term properties

- When $S^{**}_{AB}=0$: skip term vanishes; equation reduces to v16.
- When $S^{**}_{AB}>0$: skip amplifies $\widetilde{M}^{*}_{AB}$ multiplicatively.
- $\beta_s \ge 0$.

### Suggested priors

$$
\beta_s \sim \text{HalfNormal}(0,2)
$$

$$
\eta_\phi,\eta_w,\eta_b,\eta_n,\eta_a \sim \text{HalfNormal}(0,1)
$$

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
| $\beta_s$ | Skip amplification | v17 | MLE/posterior; HalfNormal(0,2) |
| $\eta_\phi,\eta_w,\eta_b,\eta_n,\eta_a$ | Skip curvature parameters | v17.2 | MLE/posterior; HalfNormal(0,1) |

## 9. Data Firewalls

| Variable pair | Firewall requirement |
|---|---|
| $\Omega_{AB}$ vs $R_{h,AB}$ | VIF < 5; $R_h$ from realized MIDs only, $\Omega$ from structural codings |
| $\Xi_{AB}$ vs $\omega_{AB,1}$ | VIF < 5; $\Xi$ from cartographic sources only |
| $\Phi^{FMA}_{AB}$ vs $\Omega_{AB}$ | $\Phi^{FMA}$ from military balance data; not from rivalry assessments |
| $\dot{W}_{AB}$ vs $R_{h,AB}$ | $\dot{W}$ from capability trend data; not from event history |
| $\mathcal{A}_{AB}$ vs $\Pi_{AB},\Psi_{AB}$ | $\mathcal{A}$ from strategic outcomes; not from cooperation intensity or gray-zone activity counts |
| $\eta_n,\eta_a$ vs ad hoc thresholds | Estimate from data; do not hand-code functional sharpness |

## 10. Change Log

### v17.2 vs v17.1

| Item | v17.1 | v17.2 |
|---|---|---|
| Alternative achievement scale | Discrete four-point | Continuous $[0,1]$ |
| Skip barrier form | Linear multiplicative | Nonlinear multiplicative with exponents |
| Deterrence suppression | Linear | Estimated sharpness |
| Alternative suppression | Linear | Estimated sharpness |
| Threshold guidance | Fixed heuristics | Empirically estimated |
| Backward compatibility | v17 recovers at $\mathcal{A}_{AB}=0$ | v17.1 recovers when all $\eta=1$ |