Here is **v19.1 reformatted** to match the v19.0 style — standard markdown with `$`/`$$` delimiters, proper table alignment, consistent use of horizontal rules, and typographic fidelity.

---

# Unified Equation of Interstate War (Dyadic Variant) v19.1 — Draft

## Structured Specification

---

## 1. What v19.1 Changes From v19.0

v19.1 is a structural revision of v19.0 that makes the current conflict tier an explicit external input rather than something recovered from the transition equations.

| Change | v19.0 | v19.1 |
|---|---|---|
| Current tier $X_t$ | Implicitly blended into model structure | Explicit analyst-coded input |
| First question | "What tier does the model imply?" | "What tier is the dyad in right now?" |
| Model task | Tier logic + transition logic | Transition logic only |
| Main output | Conditional escalation chain | Probabilities of de-escalation, persistence, and escalation from current tier |
| Forecast structure | Tier-entry equations | State-transition equations conditional on $X_t$ |
| Persistence | Informal / embedded | Explicit stay probability |
| Tier coding | Embedded in model interpretation | Deterministic questionnaire / ruleset |
| Skip logic | Upward skip barriers only | Upward skip barriers retained; downward movement separated into negotiated vs. capitulation |

---

## 2. The Six-Tier Conflict Taxonomy

| Tier | Label | Character | Coding threshold |
|---|---|---|---|
| T0 | Absolute Peace | No conflict discourse; normal bilateral relations | Default state for all dyads |
| T1 | Diplomatic Dispute | Formal disagreement, protests, summoning of ambassadors, UN votes, legal filings | ICB crisis trigger or equivalent bilateral diplomatic friction |
| T2 | Economic Coercion | Sanctions, embargoes, asset freezes, tariff weapons deployed against the adversary | TIES coding: economic instrument deployed with coercive intent |
| T3 | Limited Military Action | Bounded military operations with defined scope, geography, or implicit ceiling; both sides maintain significant restraints | MID hostility level 4–5; discrete operation with identifiable limits |
| T4 | State of War | Sustained military conflict; operational restraints of T3 dissolved; no bounded objective; political relationship organized around the war | COW inter-state war threshold (1,000 battle deaths) or equivalent sustained mobilization |
| T5 | Nuclear War | Nuclear weapons employed against the adversary | Deployment of nuclear warhead against military or civilian target |

### Tier Notes

**T0/T1 boundary:** Most politically relevant dyads have recurring low-level T1 friction. T1 is not an exceptional state; it is often the normal background condition of rivalry.

**T3/T4 boundary:** The key distinction is bounded versus open-ended conflict, not casualty magnitude alone. A brief intense clash may remain T3 if both sides preserve ceilings; a sustained conflict may qualify as T4 even if intensity varies over time.

**T5 structural regimes [OPEN — see §11]:**
- T5-Monopoly: nuclear use against a non-nuclear adversary
- T5-MAD: nuclear use or exchange under mutual deterrence

---

## 3. Exogenous Current-State Architecture

### 3.1 Core Structure

In v19.1, the current conflict tier is an externally coded state variable:

$$X_t \in \{T0, T1, T2, T3, T4, T5\}$$

$$X_t = \Omega(Q_{AB,t}, X_{t-\Delta})$$

where:
- $Q_{AB,t}$ is the current evidence questionnaire for dyad $AB$
- $X_{t-\Delta}$ is the prior coded tier
- $\Omega(\cdot)$ is the deterministic tier-coding rule with persistence correction

The forecasting model no longer determines the current state. It takes $X_t$ as given and estimates the distribution of next-period outcomes.

### 3.2 Current-Tier Coding Rule

The current tier is assigned by highest active observed tier:

$$X_t = \max \{T_k : \text{evidence at time } t \text{ satisfies tier } k\}$$

subject to a persistence rule:

$$X_t = \max(X_t^{\text{active}}, X_t^{\text{carry}})$$

where:
- $X_t^{\text{active}}$ is the tier directly supported by current evidence
- $X_t^{\text{carry}}$ is the temporary carry-forward tier if the previous higher tier has not clearly terminated

### 3.3 Forecast Target

Given current tier $X_t = T_k$, the model estimates:

$$P(X_{t+\Delta} = T_j \mid X_t = T_k, AB, t) = \pi_{kj}(t)$$

for all $j \in \{0,1,2,3,4,5\}$, with:

$$\sum_{j=0}^{5} \pi_{kj}(t) = 1$$

This is the full next-period state distribution conditional on the current state.

### 3.4 Aggregate Transition Outputs

For practical forecasting, the full distribution is collapsed into three headline probabilities:

$$P_{\downarrow}(T_k) = \sum_{j=0}^{k-1} \pi_{kj}$$

$$P_{0}(T_k) = \pi_{kk}$$

$$P_{\uparrow}(T_k) = \sum_{j=k+1}^{5} \pi_{kj}$$

with:

$$P_{\downarrow}(T_k) + P_{0}(T_k) + P_{\uparrow}(T_k) = 1$$

These are the model's primary outputs:
- probability of dropping to a lower tier
- probability of staying at the current tier
- probability of escalating to a higher tier

### 3.5 Movement-Category Scores

The three movement categories are modeled with latent utility scores:

$$
\begin{aligned}
U_k^{\downarrow} &= \alpha_k^{\downarrow} + \beta_{dS} S_k + \beta_M M_{AB}^{\text{med}} + \beta_C C_{AB}^{\text{conc}} + \beta_X X_{AB}^{\text{collapse}} - \lambda_k^{\downarrow} D_k \\[4pt]
U_k^{0} &= \alpha_k^{0} + \rho_k D_k + \beta_F F_{AB} - \beta_M^{0} M_{AB}^{\text{med}} \\[4pt]
U_k^{\uparrow} &= \alpha_k^{\uparrow} + \beta_{uS} S_k + \beta_s S_k^{**} + \sigma_k h_{AB} + \beta_{\Theta}\Theta_{AB}\mathbf{1}[k \ge 4] + \beta_N(1-\mathcal{N}_{AB})\mathbf{1}[k=4]
\end{aligned}
$$

where:
- $D_k$ is duration at current tier $k$
- $M_{AB}^{\text{med}}$ is mediation or third-party settlement pressure
- $C_{AB}^{\text{conc}}$ is bilateral concession willingness
- $X_{AB}^{\text{collapse}}$ is asymmetric collapse probability
- $F_{AB}$ is frozen-conflict persistence structure
- $S_k$ is within-tier severity
- $S_k^{**}$ is the upward skip-barrier structure relevant at tier $k$

### 3.6 Aggregate Transition Probabilities

The down, stay, and up probabilities are the softmax of the three movement-category scores:

$$P_{\downarrow}(T_k) = \frac{\exp(U_k^{\downarrow})}{\exp(U_k^{\downarrow}) + \exp(U_k^{0}) + \exp(U_k^{\uparrow})}$$

$$P_{0}(T_k) = \frac{\exp(U_k^{0})}{\exp(U_k^{\downarrow}) + \exp(U_k^{0}) + \exp(U_k^{\uparrow})}$$

$$P_{\uparrow}(T_k) = \frac{\exp(U_k^{\uparrow})}{\exp(U_k^{\downarrow}) + \exp(U_k^{0}) + \exp(U_k^{\uparrow})}$$

### 3.7 Destination-Tier Allocation

Conditional on a move downward or upward, a second-stage allocation distributes probability mass across reachable tiers.

For downward movement:

$$\omega_{kj}^{-} = P(X_{t+\Delta}=T_j \mid X_t=T_k,\; X_{t+\Delta}<T_k)$$

$$\omega_{kj}^{-} = \frac{\exp(V_{kj}^{-})}{\sum_{m=0}^{k-1}\exp(V_{km}^{-})} \qquad \text{for } j<k$$

For upward movement:

$$\omega_{kj}^{+} = P(X_{t+\Delta}=T_j \mid X_t=T_k,\; X_{t+\Delta}>T_k)$$

$$\omega_{kj}^{+} = \frac{\exp(V_{kj}^{+})}{\sum_{m=k+1}^{5}\exp(V_{km}^{+})} \qquad \text{for } j>k$$

The full next-state distribution is then:

$$
\pi_{kj} =
\begin{cases}
P_{\downarrow}(T_k)\,\omega_{kj}^{-}, & j<k \\
P_{0}(T_k), & j=k \\
P_{\uparrow}(T_k)\,\omega_{kj}^{+}, & j>k
\end{cases}
$$

---

## 4. Bilateral Escalation and Asymmetric De-escalation

### 4.1 Escalation Is Unilateral

Either actor can raise the conflict tier without the other's consent. The hazard of upward movement from tier $k$ is:

$$h_k^{\uparrow} = 1 - (1-p_k^A)(1-p_k^B)$$

where $p_k^A$ and $p_k^B$ are actor-specific escalation probabilities.

This actor-level hazard informs $U_k^{\uparrow}$ and the distribution $\omega_{kj}^{+}$.

### 4.2 De-escalation Is Bilateral or Forced

De-escalation from tier $k$ to lower tiers occurs by either:

**(a) Negotiated settlement**

$$h_k^{\downarrow(\text{neg})} = p_A^{\text{concede}}(k)\cdot p_B^{\text{concede}}(k)\cdot P(\text{coordination})$$

**(b) Capitulation**

$$h_k^{\downarrow(\text{cap})} = P(\text{military collapse}_A \text{ or } \text{military collapse}_B)$$

These two processes jointly feed the down-move score $U_k^{\downarrow}$.

### 4.3 Persistence / Stickiness

Staying at the current tier is an explicit modeled outcome:

$$h_k^{0} = P(X_{t+\Delta}=T_k \mid X_t=T_k)$$

Persistence rises with duration, unresolved core issues, and frozen-conflict structure, and falls with credible settlement mechanisms or decisive battlefield changes.

### 4.4 Ratchet Implication

Because escalation requires only one actor while negotiated de-escalation requires both actors, higher tiers remain structurally sticky. v19.1 preserves this asymmetry by estimating upward, downward, and stay outcomes separately rather than treating de-escalation as the mirror image of escalation.

---

## 5. External Public Opinion Field

$$h_{AB} = \beta_h \cdot \Psi_{AB} \cdot D_A$$

This remains unchanged in definition. In v19.1, it enters the upward movement score $U_k^{\uparrow}$ through tier-specific coupling $\sigma_k$:

| Tier | $\sigma_k$ | Field contribution in upward score |
|---|---:|---|
| T0 | 0 | 0 |
| T1 | $1/5$ | $+h_{AB}/5$ |
| T2 | $2/5$ | $+2h_{AB}/5$ |
| T3 | $3/5$ | $+3h_{AB}/5$ |
| T4 | $4/5$ | $+4h_{AB}/5$ |
| T5 | $1$ | $+h_{AB}$ |

**[OPEN]** Whether T5 should retain $\sigma_5 = 1$ or receive a super-linear coefficient due to the qualitative discontinuity of nuclear use.

---

## 6. Within-Tier Severity Scalar $S_k$

Each tier has a continuous severity sub-variable $S_k \in [0,1]$ measuring how intense the conflict is within that tier.

| Tier | Severity dimension | Low end | High end | Data source |
|---|---|---|---|---|
| $S_1$ | Diplomatic dispute intensity | Mild bilateral protest | Ultimatum, ambassador recall, UNSC escalation | ICB event codes; GDELT tone Z-score; ICB intensity coding |
| $S_2$ | Economic coercion intensity | Targeted sectoral sanctions | Total embargo, asset freeze, financial exclusion | TIES instrument coding; % bilateral trade affected |
| $S_3$ | Limited military action intensity | Border skirmish, single strike | Large multi-domain conventional operation | MID hostility level; SIPRI/ACLED fatality count |
| $S_4$ | State of war intensity | Limited war | Near-total mobilization | COW battle deaths; economic mobilization ratio |
| $S_5$ | Nuclear exchange scale | Single tactical use | Strategic exchange | [OPEN] |

**Coding rule:** $S_k$ is coded within the current tier and affects transition risk from that tier. It does not determine the current tier itself.

---

## 7. Tier-Specific Skip Barriers

The skip structure is retained, but in v19.1 it affects only upward movement conditional on the current tier.

### 7.1 Observed Skip Types

| Skip | Historical example | Structural preconditions |
|---|---|---|
| T1 → T3 | Falklands 1982 | First-mover advantage; no economic leverage; fast operational window |
| T1 → T4 | Korea 1950; Iraq → Kuwait 1990 | Surprise invasion; T2 and T3 judged pointless |
| T2 → T4 | Japan → USA 1941 | Severe coercion; closing military window; no diplomatic off-ramp |
| T3 → T5 | Not observed; theoretical | Nuclear first-strike doctrine; command breakdown; existential threat |

### 7.2 Skip Barrier Functional Form

For upward skip from tier $j$ to tier $k$, where $k > j+1$:

$$S_{j \rightarrow k}^{**} = \left(\Phi_{AB}^{FMA}\right)^{\eta_{\phi}} \cdot \left(\text{WindowClose}_{AB}\right)^{\eta_w} \cdot \left(\text{OffRampAbsence}_{AB}\right)^{\eta_r} \cdot \left(1-\mathcal{N}_{AB}^{\eta_n}\right)$$

For the T2 → T4 skip, add an economic-severity gate:

$$S_{2 \rightarrow 4}^{**} = \mathbf{1}[S_2>\tau_E] \cdot \left(\Phi_{AB}^{FMA}\right)^{\eta_{\phi}} \cdot \left(\text{WindowClose}_{AB}\right)^{\eta_w} \cdot \left(\text{OffRampAbsence}_{AB}\right)^{\eta_r} \cdot \left(1-\mathcal{N}_{AB}^{\eta_n}\right)$$

where $\tau_E$ is the coercion severity threshold.

---

## 8. Historical Escalation Paths (Illustrative)

| Dyad | Escalation path | Skip? | Notes |
|---|---|---|---|
| USA → Japan 1941 | T2 → T4 → T5 | T2 → T4 skip | Oil embargo, Pearl Harbor, atomic bombs |
| Japan → USA 1941 | T2 → T4 | T2 → T4 skip | Responding to severe economic coercion |
| Russia → Ukraine | T1 → T3 (2014) → T4 (2022) | None | Prolonged T3 before T4 |
| USSR ↔ USA Cuba 1962 | T2 | None | Resolved below military action |
| India ↔ Pakistan Kargil 1999 | T2 → T3 | None | Sequential under nuclear ceiling |
| Iraq → Kuwait 1990 | T1 → T4 | T1 → T4 skip | Surprise invasion |
| North Korea → South Korea 1950 | T1 → T4 | T1 → T4 skip | Surprise invasion |
| Falklands 1982 | T1 → T3 → T4 | T1 → T3 skip | Economic phase absent |

---

## 9. Nuclear Shadow and T5 Structure

### 9.1 Nuclear Shadow $\Theta$

$$\Theta_{AB} \in [0,1]$$

measures the degree to which nuclear use is actively present in the decision calculus below T5.

| Value | Meaning | Calibration case |
|---|---:|---|
| 0.0 | No nuclear dimension | France–Germany |
| 0.1 | Latent capability, no discourse | India–China 2020 |
| 0.3 | Vague rhetorical references | NK–SK routine tension |
| 0.6 | Explicit doctrine-linked threats | Kargil 1999 |
| 0.8 | Credible intelligence of active consideration + doctrine change | Russia–Ukraine Oct 2022 |
| 1.0 | Deployment order given | No observed MAD case |

### 9.2 Nuclear Deterrence Stability $\mathcal{N}_{AB}$

$$\mathcal{N}_{AB} \in [0,1]$$

measures the structural stability of mutual deterrence.

High $\mathcal{N}$: secure second-strike capability; command-and-control intact; no launch-on-warning pressure.

Low $\mathcal{N}$: first-strike vulnerability; decapitation risk; short decision windows; tactical nuclear weapons in theater.

### 9.3 T5 Conditional Probability

$$P(T_5 \mid T_4) = \sigma\!\left( \alpha_{45} + \beta_{\Theta}\Theta_{AB} + \beta_N(1-\mathcal{N}_{AB}) + \beta_{\Psi}\Psi_{AB}\cdot D_A + \beta_{\text{mono}}\cdot \text{Monopoly}_{AB} \right)$$

where $\text{Monopoly}_{AB} = 1$ codes the 1945 structural regime (nuclear use against a non-nuclear adversary), quarantining the only confirmed T5 case from the MAD parameter set.

---

## 10. De-escalation and Persistence Exits

Three exit states from any tier $k > T0$:

| Exit type | Mechanism | Model representation |
|---|---|---|
| Negotiated de-escalation | Both actors agree to lower tier; ceasefire, settlement, negotiated withdrawal | Bilateral concession probability product; requires third-party mediation variable |
| Capitulation | One actor's military or political position collapses; accepts the other's terms | Asymmetric collapse probability; function of military balance deterioration and domestic instability |
| Frozen conflict | Neither side escalates or de-escalates; conflict persists at current tier indefinitely | Duration dependence term; conflict trap structure |

### 10.1 Negotiated De-escalation

$$P_{k \rightarrow j}^{\text{neg}} = P_{\downarrow}(T_k)\cdot \omega_{kj}^{-,\text{neg}}$$

### 10.2 Capitulation

$$P_{k \rightarrow j}^{\text{cap}} = P_{\downarrow}(T_k)\cdot \omega_{kj}^{-,\text{cap}}$$

### 10.3 Frozen Conflict

$$P_k^{\text{freeze}} = P_0(T_k)$$

Frozen conflict is therefore no longer a separate unresolved placeholder. It is the explicit persistence mass at the current tier.

---

## 11. Open Questions — What Still Needs To Be Finalized

**Open Question 1 — Current-tier questionnaire**

What exact yes/no items determine $Q_{AB,t}$?  
Needed: operational coding rules, tie-breakers, and explicit termination criteria.

**Open Question 2 — Persistence / hysteresis**

How long does a higher tier persist after kinetic or coercive activity pauses?  
Needed: downgrade lags by tier.

**Open Question 3 — Aggregate transition model**

Should the movement categories be estimated via:
- softmax over down / stay / up,
- competing hazards,
- or nested logits?

**Open Question 4 — Destination allocation**

Should $\omega_{kj}^{-}$ and $\omega_{kj}^{+}$ allow all tiers, or only adjacent tiers plus explicitly coded skip paths?

**Open Question 5 — Severity scalar coding rules**

How should $S_3$, $S_4$, and $S_5$ be anchored empirically?  
Needed: calibration tables analogous to prior $\Psi_{AB}$ anchors.

**Open Question 6 — T5 structural regimes**

Should T5-Monopoly and T5-MAD remain a shared equation with a covariate adjustment, or become separate sub-models?

**Open Question 7 — Frozen conflict**

Is persistence adequately modeled as $P_0(T_k)$, or does frozen conflict require a distinct latent regime?

**Open Question 8 — Time horizon**

What should $\Delta$ be by default:
- 1 week,
- 1 month,
- or 1 quarter?

---

## 12. Parameters Carried Forward From v19.0

| Parameter | Role | Status |
|---|---|---|
| $\beta_0$ | Baseline structural log-odds | Retained in background covariates |
| $\beta_m$ | Structural motive weight | Retained |
| $\beta_r$ | Rivalry / spark weight | Retained |
| $\beta_a$ | Alignment weight | Retained |
| $\beta_c$ | Cooperation weight | Retained |
| $\beta_e$ | Economic pressure direct weight | Retained |
| $\beta_{e2}$ | Barrier erosion coefficient | Retained |
| $\beta_s$ | Skip amplification | Retained, tier-specific |
| $\beta_h$ | Field coupling | Retained |
| $\Theta_{AB}$ | Nuclear shadow intensity | Retained |
| $\mathcal{N}_{AB}$ | Deterrence stability | Retained |

## New Parameters in v19.1

| Parameter | Role |
|---|---|
| $\Omega(\cdot)$ | Current-tier coding function |
| $U_k^{\downarrow}, U_k^{0}, U_k^{\uparrow}$ | Movement-category latent scores |
| $P_{\downarrow}, P_0, P_{\uparrow}$ | Aggregate transition probabilities |
| $\omega_{kj}^{-}, \omega_{kj}^{+}$ | Destination-tier allocation weights |
| $D_k$ | Duration at current tier |
| $M_{AB}^{\text{med}}$ | Mediation or third-party settlement pressure |
| $C_{AB}^{\text{conc}}$ | Bilateral concession willingness |
| $X_{AB}^{\text{collapse}}$ | Collapse or capitulation risk |
| $F_{AB}$ | Frozen-conflict persistence structure |
| $X_t^{\text{carry}}$ | Persistence carry-forward tier |

---

## 13. Validation Priorities for v19.1

Given the revised architecture:

1. **State-coding reliability check:** verify that different coders assign the same $X_t$ to the same dyad under the questionnaire.
2. **Transition consistency check:** confirm that the predicted next-state probabilities sum to 1 for every current tier.
3. **Ordinal sanity check:** under baseline conditions, escalation probabilities should decline at higher tiers unless crisis-specific covariates sharply increase them.
4. **Persistence calibration:** confirm that T3 and T4 exhibit greater stay probability than T1 and T2.
5. **Skip realism check:** most T4 entries should still come through T3 rather than direct T1 → T4 or T2 → T4 skips.
6. **Nuclear deterrence test:** among nuclear dyads, T4 → T5 probability should remain extremely low absent high $\Theta$ and low $\mathcal{N}$.
7. **Backtesting:** compare predicted move directions against historical dyad-month or dyad-week episodes.

---

## 14. Practical Interpretation

In v19.1, the workflow is:

1. Code the dyad's current tier $X_t$ from a structured questionnaire.
2. Code within-tier severity $S_k$, duration $D_k$, and dynamic covariates.
3. Estimate probability of de-escalation, staying, and escalation.
4. Allocate those probabilities across concrete destination tiers.

The model therefore becomes a **state-transition forecasting system** rather than a system that both identifies and forecasts the present state.

---

All LaTeX delimiters now use `$` for inline and `$$` for display math, consistent with v19.0. Table column alignment, horizontal rules (`---`), bold, and list formatting have been preserved from the v19.0 specification.