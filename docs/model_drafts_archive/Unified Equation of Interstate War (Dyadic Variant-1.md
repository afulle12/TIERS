# Unified Equation of Interstate War (Dyadic Variant) v16
*Structured Specification*

---

## 1. Purpose

v16 introduces one new primitive — the **Contiguity Motive** $\Xi_{AB}$ — and modifies the Structural Motive term accordingly. All twelve structural fixes from v15 are preserved unchanged. The contiguity motive captures a distinct geographic-offensive incentive: whether A's non-contiguous territorial situation would be resolved or improved by controlling B. This primitive is directional, tier-free, and coded from cartographic sources only. It enters the model as a multiplicative amplifier on $\widetilde{M}_{AB}$, intensifying an existing structural motive rather than generating war risk independently.

---

## 2. Directed Tier-Sensitive Primitives

All dyadic ties are directed by default. Tiers $k \in \{1,2,3\}$ are mandatory.

| Primitive | Symbol | Domain | Interpretation |
|---|---|---|---|
| Rivalry attribute vector | $\vec{\Omega}_{AB}$ | $[0,1]^6$ | Six subcomponents: territorial, doctrinal, great-power, ideological, economic, structural MID posture. |
| Scalarized rivalry | $\Omega_{AB,k}$ | $[0,1]$ | $\Omega_{AB,k} = \Lambda\!\left( \theta_{k,0} + \sum_{m=1}^{6} \theta_{k,m}\,\omega_{AB,m} \right)$ |
| Alliance depth | $\Gamma_{AB,k}$ | $[0,1]$ | Treaty obligation + capability commitment at tier $k$. |
| Non-alliance cooperation | $\Pi_{AB}$ | $[0,1]$ | Trade density, IGO co-membership, institutional/legal integration. |
| **Contiguity motive** | $\Xi_{AB}$ | $\{0,\ 0.5,\ 1\}$ | **New in v16.** Whether war with B resolves A's non-contiguity problem. See Section 3. |

The scalarization weights $\boldsymbol{\theta}_k$ are fixed before onset estimation via a reduced-form Cox regression of dispute initiation on $\vec{\omega}$.

---

## 3. Contiguity Motive Primitive (New)

$\Xi_{AB}$ is a tier-free scalar capturing the geographic-offensive incentive for A to initiate against B.

$$\Xi_{AB} = \delta_{nc}(A) \cdot \xi_{gain}(A,B)$$

**Component 1 — Non-contiguity indicator:**

$$\delta_{nc}(A) \in \{0,1\}$$

Binary. $\delta_{nc}(A) = 1$ if and only if A holds non-contiguous sovereign territory at time $t$ (an exclave, an island territory separated from the main body, or territory severed by a third party). Coded from cartographic sources at time $t$.

**Component 2 — Contiguity gain score:**

$$\xi_{gain}(A,B) \in \{0,\ 0.5,\ 1\}$$

Ordinal. Conditional on $\delta_{nc}(A) = 1$, how much does controlling or removing B resolve A's non-contiguity problem?

| Value | Meaning |
|---|---|
| $0$ | War with B does not help A's contiguity problem |
| $0.5$ | War with B improves A's contiguity situation |
| $1$ | War with B fully resolves A's non-contiguity |

If $\delta_{nc}(A) = 0$, then $\Xi_{AB} = 0$ regardless of $\xi_{gain}$.

**Domain:** $\Xi_{AB} \in \{0,\ 0.5,\ 1\}$.

**Data firewall:** $\Xi_{AB}$ must be coded exclusively from geographic and cartographic sources. No element of $\vec{\Omega}$ (particularly the territorial sub-component $\omega_{AB,1}$) may share the same data stream as $\Xi_{AB}$. Collinearity is monitored via variance-inflation factor; if $\text{VIF}(\Xi, \omega_1) > 5$, the two are treated as partially conflated and the model reports this as a specification warning.

**Temporal coding:** $\Xi_{AB}$ is coded at time $t$. If A's non-contiguity is resolved during the course of a conflict (e.g., a land corridor is established), $\delta_{nc}(A)$ may transition from 1 to 0 at the subsequent observation period, reducing $\Xi_{AB}$ accordingly. Researchers should document the coding date.

**No tier indexing:** Geographic contiguity facts do not vary by conflict tier. $\Xi_{AB}$ is a single scalar applied uniformly across all tiers.

---

## 4. Historical Spark (Orthogonalized)

$R_{h,AB}(t)$ captures **realized** dispute history; $\vec{\Omega}_{AB}$ captures **structural** rivalry. They are fed by disjoint data streams.

$$R_{h,AB}(t) = \int_{-\infty}^{t} e^{-\delta\,(t-s)}\,dM_{AB}(s)$$

- $M_{AB}(s)$ is cumulative MID severity from event data.
- $\delta > 0$ is estimated via survival analysis, not fixed.
- **Data firewall:** No element of $\vec{\Omega}$ may be calibrated from the $M_{AB}$ series. If $\text{VIF}(\Omega, R_h) > 5$, $\delta$ is re-estimated under an orthogonalizing penalty.

---

## 5. Fuzzy Network Weights (No Crisp Adversary Sets)

$$\alpha_{AX} = \Lambda\!\left( \frac{\Omega_{AX,3} - \tau_\alpha}{s_\alpha} \right), \qquad \beta_{AX} = \Lambda\!\left( \frac{\Gamma_{AX,3} - \tau_\beta}{s_\beta} \right)$$

Adversary and ally status fade in smoothly via the logistic CDF $\Lambda$, eliminating crisp-set discontinuities.

---

## 6. Structural Potentials

No separate extended form is required. Potentials are computed by summation over all states $X \neq A,B$.

**Opposition potential** (noisy-OR over indirect rivalry paths):
$$\Phi^{opp}_{AB} = 1 - (1 - \Omega_{AB,3})\exp\!\Bigg(-\sum_X \alpha_{AX}\,\Omega_{XB,3}\Bigg)$$

**Operative alliance potential** (tier-3 active commitments only):
$$\Phi^{sup,all}_{AB} = 1 - (1 - \Gamma_{AB,3})\exp\!\Bigg(-\sum_X \beta_{AX}\,\Gamma_{XB,3}\Bigg)$$

**Implicit alignment potential** (shared-adversary geometry):
$$\Phi^{sup,imp}_{AB} = 1 - \exp\!\Bigg(-\lambda\sum_X \alpha_{AX}\,\alpha_{BX}\Bigg)$$

**Non-alliance pacification:**
$$\Phi^{coop}_{AB} = \Pi_{AB}\,\exp\!\Bigg(-\sum_X \beta_{AX}\,\Omega_{XB,3}\Bigg)$$

**Total operative support:**
$$\Phi^{sup}_{AB} = \Phi^{sup,all}_{AB} + \Phi^{sup,imp}_{AB}$$

---

## 7. Structural Motive (Modified in v16)

Opposition and support do not cancel algebraically. The base motive is:

$$\widetilde{M}_{AB} = \Phi^{opp}_{AB}\exp\!\big(-\gamma_1\Phi^{sup}_{AB} - \gamma_2\Phi^{coop}_{AB}\big)$$

**v16 modification — contiguity amplification:**

$$\widetilde{M}^*_{AB} = \widetilde{M}_{AB} \cdot \big(1 + \varphi_\xi\,\Xi_{AB}\big)$$

- $\varphi_\xi \geq 0$ is estimated from data. Suggested prior: $\varphi_\xi \sim \text{HalfNormal}(0, 1)$.
- When $\Xi_{AB} = 0$: $\widetilde{M}^*_{AB} = \widetilde{M}_{AB}$ — no change.
- When $\Xi_{AB} = 0.5$: $\widetilde{M}^*_{AB} = \widetilde{M}_{AB} \cdot (1 + 0.5\,\varphi_\xi)$ — partial amplification.
- When $\Xi_{AB} = 1$: $\widetilde{M}^*_{AB} = \widetilde{M}_{AB} \cdot (1 + \varphi_\xi)$ — full amplification.
- The contiguity motive cannot generate war risk from zero structural opposition: if $\Phi^{opp}_{AB} = 0$ then $\widetilde{M}_{AB} = 0$ and $\widetilde{M}^*_{AB} = 0$ for all $\Xi_{AB}$.
- $\gamma_1, \gamma_2 \geq 0$ are estimated from observed co-belligerence patterns, not fixed constants.
- Cross-pressure (high $\Phi^{opp}$ and $\Phi^{sup}$ simultaneously) is preserved: $\widetilde{M}^*_{AB}$ remains positive and elevated rather than collapsing.

---

## 8. Bayesian Alignment Score

**Structural connectivity:**

$$C_{AB} = 1 - \exp\!\Bigg(-\kappa\big(\Omega_{AB,3} + \Gamma_{AB,3} + \sum_X (\alpha_{AX} + \beta_{AX})\big)\Bigg)$$

If $C_{AB} < \tau_c$: $A_{AB} = \text{NULL}$ (structural missing value).

If $C_{AB} \geq \tau_c$:

$$A_{AB} = \frac{\Phi^{sup}_{AB} + \nu\mu_0}{\Phi^{sup}_{AB} + \Phi^{opp}_{AB} + \nu}$$

- Prior mean $\mu_0 = 0.5$, prior concentration $\nu > 0$.
- When both potentials are zero: $A_{AB} = 0.5$ (neutral).
- No $\epsilon$ injection; $\nu$ is an interpretable prior concentration.

---

## 9. Spark Index

$$\mathcal{R}_{AB}(t) = \ln\!\big(1 + R_{h,AB}(t)\big)\,(1 - \Phi^{coop}_{AB})^{\rho}$$

Historical spark is dampened independently by non-alliance cooperation.

---

## 10. Final Unified Equation

$$\boxed{p_{AB}(t) = \Lambda\Bigg( \beta_0 + \beta_r\mathcal{R}_{AB}(t) + \beta_m\widetilde{M}^*_{AB} + \beta_a(2A_{AB}-1)C_{AB} + \beta_c\Phi^{coop}_{AB} \Bigg)}$$

where $\Lambda$ is the logistic CDF and $\widetilde{M}^*_{AB} = \widetilde{M}_{AB}(1 + \varphi_\xi\,\Xi_{AB})$.

**Alignment term** $(2A_{AB}-1)C_{AB}$:
- Neutralized to $0$ for unembedded dyads ($C_{AB} \to 0$).
- Neutral when $A_{AB} = 0.5$.
- Bounded in $[-1,1]$ for embedded dyads.

All parameters $\boldsymbol{\beta}, \boldsymbol{\gamma}, \boldsymbol{\theta}, \delta, \lambda, \nu, \varphi_\xi$ are jointly identified and estimated by maximum likelihood or Bayesian posterior simulation on a held-out dyadic panel.

---

## 11. Parameter Summary

| Parameter | Role | Estimation |
|---|---|---|
| $\beta_0$ | Baseline log-odds | MLE / posterior |
| $\beta_m$ | Motive weight | MLE / posterior |
| $\beta_r$ | Spark weight | MLE / posterior |
| $\beta_a$ | Alignment weight | MLE / posterior |
| $\beta_c$ | Cooperation weight | MLE / posterior |
| $\gamma_1$ | Support attenuation on motive | Co-belligerence patterns |
| $\gamma_2$ | Cooperation attenuation on motive | Co-belligerence patterns |
| $\varphi_\xi$ | **Contiguity amplification** | **MLE / posterior; prior HalfNormal(0,1)** |
| $\delta$ | Spark decay rate | Survival analysis |
| $\lambda$ | Implicit alignment scaling | MLE / posterior |
| $\kappa$ | Network connectivity scaling | MLE / posterior |
| $\nu$ | Alignment prior concentration | MLE / posterior |
| $\rho$ | Cooperation-spark interaction | MLE / posterior |
| $\boldsymbol{\theta}_k$ | Rivalry scalarization weights | Pre-estimated Cox regression |

---

## 12. Dashboard & Null-State Handling

| Condition | v15 Behavior | v16 Behavior |
|---|---|---|
| $C_{AB} < \tau_c$ | Structural NULL | Unchanged |
| $\Phi^{opp}, \Phi^{sup} > \tau_p$ | Ambivalence flag | Unchanged |
| $\Omega_{AB} \approx R_h$ | Data firewall + VIF | Unchanged |
| Asymmetry | Side-by-side directed reporting | Unchanged |
| $\Xi_{AB} > 0$ | Not applicable | **Contiguity flag reported; $\widetilde{M}^*$ displayed alongside $\widetilde{M}$ base** |
| $\text{VIF}(\Xi, \omega_1) > 5$ | Not applicable | **Specification warning; treat as collinearity event** |

---

## 13. Change Log

### v16 vs v15

| Item | v15 | v16 |
|---|---|---|
| Contiguity motive | Absent | New primitive $\Xi_{AB} = \delta_{nc}(A)\cdot\xi_{gain}(A,B) \in \{0,0.5,1\}$ |
| Structural motive | $\widetilde{M}_{AB}$ | $\widetilde{M}^*_{AB} = \widetilde{M}_{AB}(1+\varphi_\xi\Xi_{AB})$ |
| New parameter | — | $\varphi_\xi \geq 0$, estimable, prior HalfNormal(0,1) |
| Tier indexing on $\Xi$ | — | None; geographic facts are tier-invariant |
| Data firewall | $\Omega$ vs $R_h$ | Extended: $\Xi$ vs $\omega_1$ (VIF monitored) |
| Final equation form | Unchanged | Unchanged in structure; $\widetilde{M}$ replaced by $\widetilde{M}^*$ |

### v15 vs v14 (retained)

| v14 Pathology | v15/v16 Fix |
|---|---|
| $\epsilon/\epsilon = 1$ degeneracy | Beta-binomial $A_{AB}$ with prior $\mu_0 = 0.5$; structural NULL for unembedded dyads |
| Ad hoc $\epsilon$ regularization | Replaced by interpretable prior concentration $\nu$ |
| Latent/operative conflation | Tier $k=3$ isolates operative behavior |
| Default symmetry | All primitives directed by default |
| Arbitrary $C_b = 0.95$ | Smooth exponential attenuation with estimable $\gamma_1, \gamma_2$ |
| $\Omega$ aggregation black box | Explicit 6-vector + published logistic weights $\boldsymbol{\theta}_k$ |
| $\Omega \approx R_h$ collinearity | Data firewall: $R_h$ from realized MIDs; $\Omega$ from structural codings |
| Crisp adversary set $\mathcal{E}_A$ | Fuzzy weights $\alpha, \beta$ via logistic CDF |
| $\max(0,\cdot)$ truncation | Opposition and support enter as separate arguments |
| Extended form required | Base model sums over all $X$ continuously |
| Tier-independent parameters | Full tier indexing $k \in \{1,2,3\}$ on all ties |
| Missing non-alliance cooperation | Primitive $\Pi_{AB}$ and potential $\Phi^{coop}_{AB}$ |