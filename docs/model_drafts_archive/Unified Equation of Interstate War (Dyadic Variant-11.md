# Unified Equation of Interstate War (Dyadic Variant) v19.2 — Specification

## Structured Specification

---

## 1. What v19.2 Changes From v19.1

v19.2 makes four targeted corrections to the v19.1 draft. The state-transition architecture, tier taxonomy, and movement-category softmax structure are unchanged. The changes resolve an underdetermined nuclear initiation constraint, a parameter-identification problem in U0, a double-counting error in the nuclear terms of U↑, and an unexposed implementation coefficient.

| Change | v19.1 | v19.2 |
|---|---|---|
| Nuclear initiation constraint | Implicit — any actor could drive p(T5\|T4) > 0 | Explicit — T5 initiation requires per-actor `HasNuke` flag; non-nuclear actors have p(T5\|T4) = 0 |
| `Monopoly` coding | Manual analyst input | Auto-derived from `HasNuke` flags: Monopoly = 1 iff exactly one actor is nuclear-armed |
| β_M^0 in U0 | Hardcoded at 0.3 | Exposed as a named, tunable parameter |
| Nuclear terms in U↑ | β_Θ·Θ and β_N·(1−𝒩) entered U↑ both directly and implicitly through h_k (double-counting) | Enter U↑ once via `nuTerm_up`; h_k contribution separately weighted by exposed β_haz |
| β_haz | Hardcoded at 0.5, absent from formal equations | Exposed parameter; set to 0 for strict spec compliance |
| T5 as destination when no nukes | T5 appeared in upward allocation with positive weight from Θ·0.3 | T5 excluded from reachable destination set when `anyNuke = false` |
| Θ when no nukes | Could be coded non-zero for non-nuclear dyads | Forced to 0 when neither actor has nukes |
| Skip35 (T3→T5) | Always active if coded | Zeroed when `anyNuke = false` |
| Headline P↓/P0/P↑ | Taken from raw softmax values | Derived from normalized π distribution; P↓(T0)=0, P↑(T5)=0 enforced |

---

## 2. The Six-Tier Conflict Taxonomy

Unchanged from v19.1.

| Tier | Label | Character | Coding threshold |
|---|---|---|---|
| T0 | Absolute Peace | No conflict discourse; normal bilateral relations | Default state for all dyads |
| T1 | Diplomatic Dispute | Formal disagreement, protests, summoning of ambassadors, UN votes, legal filings | ICB crisis trigger or equivalent bilateral diplomatic friction |
| T2 | Economic Coercion | Sanctions, embargoes, asset freezes, tariff weapons deployed against the adversary | TIES coding: economic instrument deployed with coercive intent |
| T3 | Limited Military Action | Bounded military operations with defined scope, geography, or implicit ceiling | MID hostility level 4–5; discrete operation with identifiable limits |
| T4 | State of War | Sustained military conflict; operational restraints dissolved; political relationship organized around the war | COW inter-state war threshold or equivalent sustained mobilization |
| T5 | Nuclear War | Nuclear weapons employed against the adversary by a nuclear-armed state | Deployment of nuclear warhead against military or civilian target |

### T5 Structural Regimes

- **T5-Monopoly:** nuclear use against a non-nuclear adversary (`HasNuke_A = 1`, `HasNuke_B = 0`, or vice versa). `Monopoly = 1`.
- **T5-MAD:** nuclear use or exchange under mutual deterrence (`HasNuke_A = HasNuke_B = 1`). `Monopoly = 0`.
- **T5-Impossible:** neither actor nuclear-armed. `P(T5) = 0` enforced structurally. `Monopoly = 0`, `Θ = 0`.

---

## 3. Exogenous Current-State Architecture

### 3.1–3.3

Unchanged from v19.1. The current tier $X_t \in \{T0, \ldots, T5\}$ is an analyst-coded external input. The model estimates $\pi_{kj}(t) = P(X_{t+\Delta} = T_j \mid X_t = T_k, AB, t)$.

### 3.4 Aggregate Transition Outputs (Updated in v19.2)

The full distribution is collapsed into three headline probabilities **derived from the normalized $\pi$ distribution**, not from the raw softmax scores:

$$P_{\downarrow}(T_k) = \sum_{j=0}^{k-1} \pi_{kj}, \qquad P_{0}(T_k) = \pi_{kk}, \qquad P_{\uparrow}(T_k) = \sum_{j=k+1}^{5} \pi_{kj}$$

$$P_{\downarrow}(T_k) + P_{0}(T_k) + P_{\uparrow}(T_k) = 1$$

**Boundary correction (new in v19.2):** The softmax over $(U_k^\downarrow, U_k^0, U_k^\uparrow)$ may assign positive mass to the downward or upward category even at boundary tiers where no movement is structurally possible. The normalized $\pi$ distribution absorbs this correctly:

$$P_\downarrow(T_0) = 0 \quad \text{(no tiers below T0 — de-escalation is undefined at peace)}$$
$$P_\uparrow(T_5) = 0 \quad \text{(no tiers above T5 — escalation is undefined at nuclear war)}$$

Raw softmax values $(p_\downarrow^\text{raw}, p_0^\text{raw}, p_\uparrow^\text{raw})$ are retained as internal diagnostics for U-score inspection but are not the reported headline outputs. At T0, the $P_0$ label reads "REMAIN AT PEACE" rather than "STAY / FREEZE."

### 3.5 Movement-Category Scores (Updated)

$$
\begin{aligned}
U_k^{\downarrow} &= \alpha_k^{\downarrow} + \beta_{dS} S_k + \beta_M M_{AB}^{\text{med}} + \beta_C C_{AB}^{\text{conc}} + \beta_X X_{AB}^{\text{collapse}} - \lambda_k^{\downarrow} D_k \\[6pt]
U_k^{0} &= \alpha_k^{0} + \rho_k D_k + \beta_F F_{AB} - \beta_M^{0} M_{AB}^{\text{med}} \\[6pt]
U_k^{\uparrow} &= \alpha_k^{\uparrow} + \beta_{uS} S_k + \beta_s S_k^{**} + \sigma_k h_{AB} + \nu_k^{\text{nuke}} + \beta_{\text{haz}} \cdot h_k^{\uparrow}
\end{aligned}
$$

where:

$$\nu_k^{\text{nuke}} = \mathbf{1}[\text{anyNuke}] \cdot \left[ \beta_\Theta \Theta_{AB} \cdot \mathbf{1}[k \ge 4] + \beta_N(1-\mathcal{N}_{AB}) \cdot \mathbf{1}[k=4] + \beta_{\text{mono}} \cdot \text{Monopoly}_{AB} \cdot \mathbf{1}[k=5] \right]$$

**Key changes from v19.1:**

- **$\beta_M^0$** is now a distinct named parameter (mediation penalty in U0), separate from $\beta_M$ (mediation weight in U↓). In v19.1 this was hardcoded at 0.3.
- **$\nu_k^{\text{nuke}}$** consolidates all nuclear terms entering U↑ into a single gated expression. Nuclear terms previously appeared in both U↑ directly and implicitly through $h_k^{\uparrow}$ (since actor chains include nuclear terms in p5). The double-entry is resolved: nuclear terms enter U↑ once via $\nu_k^{\text{nuke}}$.
- **$\beta_{\text{haz}}$** is now an exposed parameter weighting the bilateral escalation hazard's direct contribution to U↑. Setting $\beta_{\text{haz}} = 0$ gives the strict spec equation from v19.1 §3.5. The default value (0.5) retains the implementation behavior as a calibrated extension.
- **$\mathbf{1}[\text{anyNuke}]$** gates all nuclear terms: if neither actor possesses nuclear weapons, $\nu_k^{\text{nuke}} = 0$ identically and T5 is excluded from the reachable destination set.

### 3.6–3.7

Softmax and destination-tier allocation unchanged from v19.1, with the following addition to the upward allocation:

**T5 reachability constraint:** For $j = 5$, the upward allocation weight $V_{k5}^+$ is set to $-\infty$ (effectively zero probability mass) when $\text{anyNuke} = \text{false}$. Skip35 ($T3 \to T5$) is similarly zeroed.

---

## 4. Bilateral Escalation and Asymmetric De-escalation

### 4.1 Escalation Is Unilateral

$$h_k^{\uparrow} = 1 - (1-p_k^A)(1-p_k^B)$$

where $p_k^A$ and $p_k^B$ are actor-specific escalation hazards at current tier $k$.

**v19.2 note:** The bilateral hazard now enters U↑ via the explicit $\beta_{\text{haz}} \cdot h_k^{\uparrow}$ term rather than through an implicit additive constant. Nuclear terms in the actor chains (which feed $h_k^{\uparrow}$) and in $\nu_k^{\text{nuke}}$ are no longer double-counted.

### 4.2–4.4

De-escalation exits (negotiated, capitulation, frozen conflict) unchanged from v19.1.

---

## 5. Nuclear Capability Constraint (New in v19.2)

### 5.1 Per-Actor Nuclear Flag

$$\text{HasNuke}_i \in \{0, 1\}, \quad i \in \{A, B\}$$

$\text{HasNuke}_i = 1$ if and only if actor $i$ possesses deliverable nuclear weapons at time $t$.

### 5.2 T5 Initiation Gate

An actor cannot initiate nuclear war without nuclear weapons:

$$p_k^i \Big|_{k=4} \equiv p(T5 \mid T4)^i = \begin{cases} \sigma\!\left(\alpha_{45} + \beta_\Theta \Theta_{AB} + \beta_N(1-\mathcal{N}_{AB}) + \beta_\Psi \Psi_i \cdot D_{A,i} + \beta_{\text{mono}} \cdot \text{Monopoly}_{AB} + w_5 \cdot L_{\text{base},i} + f_{5,i} \right) & \text{if } \text{HasNuke}_i = 1 \\[4pt] 0 & \text{if } \text{HasNuke}_i = 0 \end{cases}$$

A non-nuclear actor may still be the **target** of nuclear use. The constraint applies only to initiation.

### 5.3 Monopoly Auto-Derivation

$$\text{Monopoly}_{AB} = \mathbf{1}\left[\text{HasNuke}_A + \text{HasNuke}_B = 1\right]$$

Monopoly is no longer a free analyst-coded input. It is determined entirely by the HasNuke flags. This quarantines the 1945 structural regime (nuclear use against a non-nuclear adversary) from the MAD parameter set.

### 5.4 Structural Consequences by Regime

| HasNuke_A | HasNuke_B | Regime | Monopoly | T5 reachable | Θ valid |
|:---:|:---:|---|:---:|:---:|:---:|
| 0 | 0 | Non-nuclear dyad | 0 | No | No (forced 0) |
| 1 | 0 | Monopoly (A nuclear) | 1 | Yes (A only) | Yes |
| 0 | 1 | Monopoly (B nuclear) | 1 | Yes (B only) | Yes |
| 1 | 1 | MAD | 0 | Yes (both) | Yes |

### 5.5 Structural Note on Non-Nuclear Dyads

For a dyad where neither actor is nuclear-armed:
- $\Theta_{AB}$ is forced to 0 regardless of analyst input
- $\nu_k^{\text{nuke}} = 0$ for all $k$
- T5 receives zero probability mass in the destination allocation
- Skip35 ($T3 \to T5$) is structurally zeroed

---

## 6–8. Within-Tier Severity, Skip Barriers, Historical Paths

Unchanged from v19.1.

---

## 9. Nuclear Shadow and T5 Structure (Updated)

### 9.1 Nuclear Shadow $\Theta$

Unchanged definition. $\Theta_{AB} \in [0,1]$ measures active nuclear presence in the decision calculus below T5. Valid only when $\text{anyNuke} = \text{true}$.

### 9.2 Nuclear Deterrence Stability $\mathcal{N}_{AB}$

Unchanged. Valid only when $\text{anyNuke} = \text{true}$.

### 9.3 T5 Conditional Probability (Updated)

$$P(T_5 \mid T_4)^i = \text{HasNuke}_i \cdot \sigma\!\left( \alpha_{45} + \beta_\Theta \Theta_{AB} + \beta_N(1-\mathcal{N}_{AB}) + \beta_\Psi \Psi_i \cdot D_{A,i} + \beta_{\text{mono}} \cdot \text{Monopoly}_{AB} + w_5 \cdot L_{\text{base},i} + f_{5,i} \right)$$

The $\text{HasNuke}_i$ multiplicative gate replaces the v19.1 form which allowed any actor to produce non-zero $P(T5 \mid T4)$.

---

## 10. De-escalation and Persistence Exits

Unchanged from v19.1.

---

## 11. Open Questions — Updated Status

**Open Question 1 — Current-tier questionnaire:** Open.

**Open Question 2 — Persistence / hysteresis:** Open.

**Open Question 3 — Aggregate transition model:** Resolved in implementation as softmax over (U↓, U0, U↑).

**Open Question 4 — Destination allocation:** Implemented as proximity-weighted softmax with skip bonuses; all tiers allowed except T5 when `anyNuke = false`.

**Open Question 5 — Severity scalar coding rules:** Open.

**Open Question 6 — T5 structural regimes:** Partially resolved. T5-Monopoly and T5-MAD share the same equation structure with Monopoly as a covariate. The `HasNuke` gate enforces structural separation at the initiation level. Whether T5-Monopoly and T5-MAD require fully separate sub-models remains open.

**Open Question 7 — Frozen conflict:** Implemented as $P_0(T_k)$; whether this is adequate for long-duration frozen conflicts is open.

**Open Question 8 — Time horizon $\Delta$:** Open. Default interpretation is one period (quarter recommended for calibration).

**Open Question 9 (New) — β_haz identification:** The bilateral hazard $h_k^{\uparrow}$ enters U↑ via both the $\nu_k^{\text{nuke}}$ path (through actor chains that include nuclear covariates) and the direct $\beta_{\text{haz}} \cdot h_k^{\uparrow}$ term. Whether $\beta_{\text{haz}}$ should be set to zero (strict spec) or estimated from data (implementation extension) is an open calibration question. Setting $\beta_{\text{haz}} = 0$ gives the formal spec equation; the default 0.5 is a provisional calibration.

**Open Question 10 (New) — Negotiated vs. capitulation downward allocation:** The spec (§10.1/10.2) treats negotiated de-escalation and capitulation as distinct mechanisms with potentially different destination-tier weights ($\omega_{kj}^{-,\text{neg}}$ vs. $\omega_{kj}^{-,\text{cap}}$). The current implementation collapses both into a single $V_{kj}^-$ score. Separating them would require additional actor-level variables distinguishing negotiated vs. forced exit posture.

---

## 12. Parameters

### Carried Forward From v19.0/v19.1

| Parameter | Role | Status |
|---|---|---|
| $\beta_0$ | Baseline structural log-odds | Retained |
| $\beta_m$ | Structural motive weight | Retained |
| $\beta_r$ | Rivalry / spark weight | Retained |
| $\beta_a$ | Alignment weight | Retained |
| $\beta_c$ | Cooperation weight | Retained |
| $\beta_e$ | Economic pressure direct weight | Retained |
| $\beta_{e2}$ | Barrier erosion coefficient | Retained |
| $\beta_s$ | Skip amplification | Retained, tier-specific |
| $\beta_h$ | Field coupling | Retained |
| $\Theta_{AB}$ | Nuclear shadow intensity | Retained; forced 0 when anyNuke = false |
| $\mathcal{N}_{AB}$ | Deterrence stability | Retained |
| $U_k^\downarrow, U_k^0, U_k^\uparrow$ | Movement-category latent scores | Retained |
| $P_\downarrow, P_0, P_\uparrow$ | Aggregate transition probabilities | Retained |
| $\omega_{kj}^-, \omega_{kj}^+$ | Destination-tier allocation weights | Retained |
| $D_k$ | Duration at current tier | Retained |
| $M_{AB}^{\text{med}}$ | Mediation / settlement pressure | Retained |
| $C_{AB}^{\text{conc}}$ | Bilateral concession willingness | Retained |
| $X_{AB}^{\text{collapse}}$ | Collapse / capitulation risk | Retained |
| $F_{AB}$ | Frozen-conflict persistence | Retained |

### New in v19.2

| Parameter | Role | Default | Notes |
|---|---|---|---|
| $\text{HasNuke}_i$ | Per-actor nuclear capability flag | 0 | Binary; gates T5 initiation for actor $i$ |
| $\text{Monopoly}_{AB}$ | Monopoly nuclear regime | auto | Auto-derived from HasNuke flags; no longer a free input |
| $\beta_M^0$ | Mediation penalty in U0 | 0.3 | Distinct from $\beta_M$ in U↓; was hardcoded in v19.1 |
| $\nu_k^{\text{nuke}}$ | Consolidated nuclear term in U↑ | — | Replaces separate nuclearK4/nuclearK45 terms; gated on anyNuke |
| $\beta_{\text{haz}}$ | Bilateral hazard weight in U↑ | 0.5 | Implementation extension; set 0 for strict spec; open calibration question |
| $\mathbf{1}[\text{anyNuke}]$ | Dyad nuclear capability indicator | — | Derived: true iff HasNuke_A or HasNuke_B = 1 |

---

## 13. Validation Priorities (Updated)

Validation priorities from v19.1 are retained with the following additions:

8. **Nuclear initiation asymmetry check:** confirm that non-nuclear actors produce $P(T5 \mid T4) = 0$ regardless of $\Theta$ or $\mathcal{N}$ settings.

9. **Monopoly calibration check:** verify that the 1945 US→Japan case is correctly classified as Monopoly = 1 and does not contaminate MAD parameter estimates.

10. **β_haz sensitivity:** run forecasts at $\beta_{\text{haz}} \in \{0, 0.25, 0.5, 0.75\}$ to quantify sensitivity of P↑ to the hazard-in-U↑ implementation extension.

11. **β_M^0 identification:** confirm that the mediation penalty in U0 ($\beta_M^0$, suppressing persistence) is empirically distinguishable from the mediation weight in U↓ ($\beta_M$, promoting de-escalation).

---

## 14. Practical Interpretation

In v19.2, the workflow is:

1. **Code HasNuke** for each actor. This determines whether T5 is a structurally reachable outcome and auto-derives Monopoly.
2. **Code the dyad's current tier** $X_t$ from a structured questionnaire.
3. **Code within-tier severity** $S_k$, duration $D_k$, and dynamic covariates.
4. **Estimate** P↓, P0, P↑ via the softmax over movement-category scores.
5. **Allocate** across reachable destination tiers (T5 excluded if anyNuke = false).

The model remains a **state-transition forecasting system**. The v19.2 revision tightens the nuclear architecture, exposes previously hidden parameters, and eliminates a double-counting error in the escalation score.

---

*v19.2 supersedes v19.1. Changes are fully backward-compatible for non-nuclear dyads (HasNuke_A = HasNuke_B = 0) and for nuclear dyads where β_haz = 0.5 and β_M^0 = 0.3 match the implicit v19.1 defaults.*