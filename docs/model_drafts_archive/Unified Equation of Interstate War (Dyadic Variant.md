**Unified Equation of Interstate War (Dyadic Variant) v15**  
*Structured Specification*

---

### 1. Purpose

v15 eliminates the twelve structural pathologies identified in v14: the $\epsilon/\epsilon$ degeneracy, ad hoc regularization, latent/operative conflation, forced symmetry, arbitrary constants, opaque aggregation, collinearity between rivalry and history, crisp-set discontinuities, truncating cancellation, a bifurcated base/extended form, tier blindness, and missing non-alliance cooperation channels. Every primitive is now directed, tier-sensitive, theoretically identified, and computed in a single network-aware base model.

---

### 2. Directed Tier-Sensitive Primitives

All dyadic ties are directed by default. Tiers $k \in \{1,2,3\}$ are mandatory.

| Primitive | Symbol | Domain | Interpretation |
|---|---|---|---|
| Rivalry attribute vector | $\vec{\Omega}_{AB}$ | $[0,1]^6$ | Six subcomponents: territorial, doctrinal, great-power, ideological, economic, structural MID posture. |
| Scalarized rivalry | $\Omega_{AB,k}$ | $[0,1]$ | $\Omega_{AB,k} = \Lambda\!\left( \theta_{k,0} + \sum_{m=1}^{6} \theta_{k,m}\,\omega_{AB,m} \right)$ |
| Alliance depth | $\Gamma_{AB,k}$ | $[0,1]$ | Treaty obligation + capability commitment at tier $k$. |
| Non-alliance cooperation | $\Pi_{AB}$ | $[0,1]$ | Trade density, IGO co-membership, institutional/legal integration. |

The scalarization weights $\boldsymbol{\theta}_k$ are fixed *before* onset estimation (e.g., via a reduced-form Cox regression of dispute initiation on $\vec{\omega}$). This removes the black-box aggregation of v14.

---

### 3. Historical Spark (Orthogonalized)

$R_{h,AB}(t)$ captures **realized** dispute history; $\vec{\Omega}_{AB}$ captures **structural** rivalry. They are fed by disjoint data streams.

$$R_{h,AB}(t) = \int_{-\infty}^{t} e^{-\delta\,(t-s)}\,dM_{AB}(s)$$

- $M_{AB}(s)$ is cumulative MID severity from event data.
- $\delta > 0$ is estimated via survival analysis, not fixed.
- **Data firewall:** No element of $\vec{\Omega}$ may be calibrated from the $M_{AB}$ series. Collinearity is monitored via variance-inflation factor; if $\text{VIF}(\Omega, R_h) > 5$, $\delta$ is re-estimated under an orthogonalizing penalty.

---

### 4. Fuzzy Network Weights (No Crisp Adversary Sets)

The crisp set $\mathcal{E}_A = \{X : \Omega_{AX} > 0\}$ is abolished. All network interactions are continuous.

$$\alpha_{AX} = \Lambda\!\left( \frac{\Omega_{AX,3} - \tau_\alpha}{s_\alpha} \right), \qquad \beta_{AX} = \Lambda\!\left( \frac{\Gamma_{AX,3} - \tau_\beta}{s_\beta} \right)$$

where $\Lambda$ is the logistic CDF. Adversary and ally status fade in smoothly, eliminating the v14 discontinuity.

---

### 5. Structural Potentials (Base Model = Full Network Model)

No separate “extended form” is required. The potentials are computed by summation over all states $X \neq A,B$ in the system.

**Opposition potential** (noisy-OR over indirect rivalry paths):
$$\Phi^{opp}_{AB} = 1 - (1 - \Omega_{AB,3})\exp\!\Bigg(-\sum_X \alpha_{AX}\,\Omega_{XB,3}\Bigg)$$

**Operative alliance potential** (tier-3 active commitments only):
$$\Phi^{sup,all}_{AB} = 1 - (1 - \Gamma_{AB,3})\exp\!\Bigg(-\sum_X \beta_{AX}\,\Gamma_{XB,3}\Bigg)$$

**Implicit alignment potential** (shared-adversary geometry):
$$\Phi^{sup,imp}_{AB} = 1 - \exp\!\Bigg(-\lambda\sum_X \alpha_{AX}\,\alpha_{BX}\Bigg)$$

**Non-alliance pacification**:
$$\Phi^{coop}_{AB} = \Pi_{AB}\,\exp\!\Bigg(-\sum_X \beta_{AX}\,\Omega_{XB,3}\Bigg)$$
(Cooperation is degraded when A’s allies are structurally opposed to B.)

Define total operative support:
$$\Phi^{sup}_{AB} = \Phi^{sup,all}_{AB} + \Phi^{sup,imp}_{AB}$$

---

### 6. Structural Motive (Non-Truncating)

Opposition and support **do not cancel algebraically**. The model preserves ambivalence by keeping both as separate arguments. Opposition is smoothly attenuated by support and cooperation, but never truncated to zero.

$$\widetilde{M}_{AB} = \Phi^{opp}_{AB}\exp\!\big(-\gamma_1\Phi^{sup}_{AB} - \gamma_2\Phi^{coop}_{AB}\big)$$

- $\gamma_1, \gamma_2 \geq 0$ are estimated from observed co-belligerence patterns, not fixed constants.
- If $\Phi^{opp}$ and $\Phi^{sup}$ are both high (cross-pressure), $\widetilde{M}_{AB}$ remains elevated but dampened, rather than collapsing to zero.

---

### 7. Bayesian Alignment Score

**Structural connectivity** determines whether a dyad is embedded in the network:

$$C_{AB} = 1 - \exp\!\Bigg(-\kappa\big(\Omega_{AB,3} + \Gamma_{AB,3} + \sum_X (\alpha_{AX} + \beta_{AX})\big)\Bigg)$$

If $C_{AB} < \tau_c$, the dyad is **structurally unembedded**. The model returns:
- $A_{AB} = \text{NULL}$ (mechanical missing value, not a display hack).

If $C_{AB} \geq \tau_c$, alignment is the posterior mean of a Beta-binomial estimator with prior mean $\mu_0 = 0.5$ and prior concentration $\nu > 0$:

$$A_{AB} = \frac{\Phi^{sup}_{AB} + \nu\mu_0}{\Phi^{sup}_{AB} + \Phi^{opp}_{AB} + \nu}$$

Properties:
- When both potentials are zero, $A_{AB} = 0.5$ (**neutral**, not perfectly aligned).
- When data dominate the prior, $A_{AB} \to \Phi^{sup} / (\Phi^{sup} + \Phi^{opp})$.
- No $\epsilon$ is injected; $\nu$ is an interpretable prior concentration.

---

### 8. Spark Index

$$\mathcal{R}_{AB}(t) = \ln\!\big(1 + R_{h,AB}(t)\big)\,(1 - \Phi^{coop}_{AB})^{\rho}$$

Historical spark is dampened independently by non-alliance cooperation.

---

### 9. Final Unified Equation

$$p_{AB}(t) = \Lambda\Bigg( \beta_0 + \beta_r\mathcal{R}_{AB}(t) + \beta_m\widetilde{M}_{AB} + \beta_a(2A_{AB}-1)C_{AB} + \beta_c\Phi^{coop}_{AB} \Bigg)$$

where $\Lambda$ is the logistic CDF. The alignment term $(2A_{AB}-1)C_{AB}$ is:
- **Neutralized** to $0$ for unembedded dyads ($C_{AB} \to 0$),
- **Neutral** when $A_{AB} = 0.5$,
- **Bounded** in $[-1,1]$ for embedded dyads.

All parameters $\boldsymbol{\beta}, \boldsymbol{\gamma}, \boldsymbol{\theta}, \delta, \lambda, \nu$ are jointly identified and estimated by maximum likelihood or Bayesian posterior simulation on a held-out dyadic panel.

---

### 10. Dashboard & Null-State Handling

| Condition | v14 Behavior | v15 Behavior |
|---|---|---|
| $C_{AB} < \tau_c$ | UI hack printed `—` | **Structural NULL**: $A_{AB}$ is undefined; logistic term mechanically zero. |
| $\Phi^{opp}, \Phi^{sup} > \tau_p$ | Truncated to 0 via $\max(0,\cdot)$ | **Ambivalence flag**: both values reported; motive term remains positive. |
| $\Omega_{AB} \approx R_h$ | Same data fed both channels | **Data firewall** + orthogonalizing penalty; VIF reported. |
| Asymmetry hidden | $\Omega_{AB} = \Omega_{BA}$ | Side-by-side directed reporting mandatory. |

---

### 11. Change Log from v14

| v14 Pathology | v15 Fix |
|---|---|
| $\epsilon/\epsilon = 1$ degeneracy | Beta-binomial $A_{AB}$ with prior $\mu_0 = 0.5$; structural NULL for unembedded dyads. |
| Ad hoc $\epsilon$ regularization | Replaced by interpretable prior concentration $\nu$. |
| Latent/operative conflation | Tier $k=3$ isolates operative behavior; latent ties do not enter $\Phi^{sup}$ in the onset equation. |
| Default symmetry | All primitives directed by default. |
| Arbitrary $C_b = 0.95$ | Smooth exponential attenuation with estimable $\gamma_1, \gamma_2$. |
| $\Omega$ aggregation black box | Explicit 6-vector + published logistic weights $\boldsymbol{\theta}_k$. |
| $\Omega \approx R_h$ collinearity | Data firewall: $R_h$ from realized MIDs; $\Omega$ from structural codings. |
| Crisp adversary set $\mathcal{E}_A$ | Fuzzy weights $\alpha, \beta$ via logistic CDF. |
| $\max(0,\cdot)$ truncation | Opposition and support enter as separate arguments; no algebraic cancellation. |
| Extended form required | Base model sums over all $X$ continuously; no separate extended form. |
| Tier-independent parameters | Full tier indexing $k \in \{1,2,3\}$ on all ties. |
| Missing non-alliance cooperation | New primitive $\Pi_{AB}$ and potential $\Phi^{coop}_{AB}$. |