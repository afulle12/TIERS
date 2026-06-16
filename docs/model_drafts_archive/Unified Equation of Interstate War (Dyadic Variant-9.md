# Unified Equation of Interstate War (Dyadic Variant) v19.0 — Draft

## Structured Specification

---

## 1. What v19.0 Changes From v18.3

v19.0 is a major architectural revision incorporating six changes from our working session:

| Change | v18.3 | v19.0 |
|---|---|---|
| Conflict tiers | 4 (T0–T3) | 6 (T0–T5) |
| Escalation structure | Flat softmax over all tiers | Conditional chain: P(T_k) = P(T_k \| T_{k-1}) × ... × P(T_1) |
| Escalation agency | Directed dyad: initiator A acts on B | Bilateral: either actor can escalate unilaterally |
| De-escalation | Symmetric with escalation | Asymmetric: requires mutual agreement or capitulation |
| Skip barriers | Single S\*\* for T0→T3 | Tier-specific skip probabilities per transition type |
| Nuclear tier | T3 = war (implicit nuclear risk) | T5 = Nuclear War; T4 = State of War; nuclear shadow Θ |
| Severity | Implicit in tier assignment | Explicit within-tier severity scalar S_k ∈ [0,1] |
| Ising field coupling | σ_k = k/3 over 4 tiers | σ_k = k/5 over 6 tiers [OPEN: see §11] |

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

**T0/T1 boundary:** Most politically relevant dyads have ongoing low-level T1 friction. T1 is not an exceptional state — it is the background condition of international relations between non-allied states.

**T3/T4 boundary:** The key distinction is the bounded vs. open-ended character of the conflict, not casualty magnitude alone. A brief intense clash may exceed 1,000 deaths while remaining T3 if it resolved with defined limits (Kargil 1999). A sustained low-intensity conflict may qualify as T4 if both sides have removed operational ceilings.

**T5 structural regimes [OPEN — see §11]:**
- T5-Monopoly: nuclear use against a non-nuclear-armed adversary (1945 case)
- T5-MAD: nuclear exchange under mutual deterrence (no observed case; constrained by near-misses)

---

## 3. Conditional Chain Architecture

### 3.1 Core Structure

The model estimates the probability of each conflict tier as a product of conditional transition probabilities:

$$P(T_k \mid AB, t) = \prod_{j=1}^{k} P(T_j \mid T_{j-1}, AB, t)$$

where each conditional probability $P(T_j \mid T_{j-1})$ is estimated from tier-specific data and covariates.

This replaces the flat softmax of v18.3 with a sequential hazard model. The softmax is retained *within* each conditional transition as the link function, but each transition has its own parameter set.

### 3.2 Conditional Transition Probabilities

$$P(T_1 \mid T_0) = \sigma(\mathcal{L}_\text{base} + \tfrac{1}{5}h_{AB})$$

$$P(T_2 \mid T_1) = \sigma(\alpha_{12} + \beta_{12} \cdot S_1 + \beta_e \mathcal{E}_{AB} + \tfrac{2}{5}h_{AB})$$

$$P(T_3 \mid T_2) = \sigma(\alpha_{23} + \beta_{23} \cdot S_2 + \beta_{e2}\mathcal{E}_{AB}(1-\mathcal{A}_{AB}) + \beta_s S^{**}_{23} + \tfrac{3}{5}h_{AB})$$

$$P(T_4 \mid T_3) = \sigma(\alpha_{34} + \beta_{34} \cdot S_3 + \beta_s S^{**}_{34} \cdot \widetilde{M}^*_{AB} + \tfrac{4}{5}h_{AB})$$

$$P(T_5 \mid T_4) = \sigma(\alpha_{45} + \beta_\Theta \cdot \Theta_{AB} + \beta_N (1 - \mathcal{N}_{AB}) + h_{AB})$$

where:
- $S_k \in [0,1]$ is the within-tier severity at tier k (see §6)
- $\alpha_{jk}$ are tier-transition intercepts (all ≤ 0; empirically calibrated to base rates)
- $S^{**}_{jk}$ is the tier-specific skip barrier structure (see §7)
- $\Theta_{AB} \in [0,1]$ is the nuclear shadow intensity (see §9)
- $\mathcal{N}_{AB}$ is nuclear deterrence stability (see §9)

### 3.3 Shared Base Log-Odds (unchanged from v18.3)

$$\mathcal{L}_\text{base} = \beta_0 + \beta_m \widetilde{M}^*_{AB} + \beta_r \mathcal{R}_{AB} + \beta_a (2A_{AB}-1)C_{AB} \cdot \mathbf{1}[\Phi^{opp} > \tau_{opp}] + \beta_c \Phi^{coop}_{AB}$$

$\mathcal{L}_\text{base}$ enters fully at T1 and partially at higher tiers via the severity scalars. At T4 and T5, structural conditions become less predictive and dynamic war-phase variables dominate.

---

## 4. Bilateral Escalation Structure

### 4.1 Escalation Is Unilateral

Either actor can raise the conflict tier without the other's consent. The hazard of escalation from tier k to k+1 is:

$$h^\uparrow_k = 1 - (1 - p^A_k)(1 - p^B_k)$$

where $p^A_k$ and $p^B_k$ are actor A's and actor B's individual escalation probabilities at tier k, each estimated from that actor's structural position, costs, and resolve.

### 4.2 De-escalation Is Bilateral or Forced

De-escalation from tier k to k-1 requires either:

**(a) Negotiated settlement:** both actors willing to concede + coordination succeeds

$$h^\downarrow_k\text{(negotiated)} = p^A_\text{concede}(k) \cdot p^B_\text{concede}(k) \cdot P(\text{coordination})$$

**(b) Capitulation:** one actor's military position collapses and it accepts terms unilaterally

$$h^\downarrow_k\text{(capitulation)} = P(\text{military collapse}_A \text{ or } \text{military collapse}_B)$$

These are structurally different exit states. Negotiated settlement produces a bilateral agreement and is reversible (either party can re-escalate). Capitulation produces a victor and is more durable but often seeds future rivalry.

### 4.3 The Ratchet Implication

Because $h^\uparrow_k$ requires only one actor and $h^\downarrow_k$ requires both actors (or collapse), higher tiers are stickier than lower tiers. The model must encode this asymmetry explicitly: de-escalation parameters are not the mirror image of escalation parameters.

**Practical coding:** For each tier transition, estimate separate logistic models for:
- Escalation (either-actor trigger)
- Negotiated de-escalation (joint-actor outcome)
- Capitulation (asymmetric exit)

---

## 5. External Public Opinion Field (revised from v18.3)

$$h_{AB} = \beta_h \cdot \Psi_{AB} \cdot D_A$$

Unchanged in definition. The coupling changes with six tiers:

| Tier | σ_k | Field contribution |
|---|---:|---|
| T0 | 0 | 0 (reference) |
| T1 | 1/5 | +h_{AB}/5 |
| T2 | 2/5 | +2h_{AB}/5 |
| T3 | 3/5 | +3h_{AB}/5 |
| T4 | 4/5 | +4h_{AB}/5 |
| T5 | 1 | +h_{AB} |

**[OPEN]** Whether T5 should receive σ=1 or σ>1 given the qualitative discontinuity of nuclear use relative to conventional war. See §11, Open Question 1.

---

## 6. Within-Tier Severity Scalar S_k

Each tier has a continuous severity sub-variable $S_k \in [0,1]$ measuring how intense the conflict is *within* that tier. Severity drives the conditional transition probability to the next tier.

| Tier | Severity dimension | Low end | High end | Data source |
|---|---|---|---|---|
| S_1 | Diplomatic dispute intensity | Mild bilateral protest | Ultimatum, ambassador recall, UNSC escalation | ICBe event codes; GDELT tone Z-score; ICB intensity coding |
| S_2 | Economic coercion intensity | Targeted sectoral sanctions | Total embargo, asset freeze, financial exclusion (SWIFT) | TIES instrument coding; % bilateral trade affected |
| S_3 | Limited military action intensity | Border skirmish, single strike | Large multi-domain conventional operation | MID hostility level; SIPRI/ACLED fatality count |
| S_4 | State of war intensity | Limited war (Korea-type) | Near-total mobilization | COW battle deaths; economic mobilization ratio |
| S_5 | Nuclear exchange scale | Single tactical use | Strategic exchange | [OPEN — see §11] |

**Coding rule:** S_k is coded *within* the tier, independently of whether the tier-transition has occurred. A dyad at T2 with S_2=0.9 (near-total embargo) is in a different escalation risk position than a dyad at T2 with S_2=0.2 (partial sanctions).

---

## 7. Tier-Specific Skip Barriers

The single S\*\* of v18.3 is replaced by tier-pair-specific skip probabilities. Each skip type has distinct structural preconditions.

### 7.1 Observed Skip Types

| Skip | Historical example | Structural preconditions |
|---|---|---|
| T1 → T3 | Falklands 1982 (limited military before economic coercion) | First-mover advantage; no economic leverage available; fast operational window |
| T1 → T4 | Korea 1950; Iraq→Kuwait 1990 | Surprise invasion; initiator calculates T2 and T3 are pointless; time-sensitive opportunity |
| T2 → T4 | Japan→USA 1941; USA→Japan 1941 | Economic coercion so severe it threatens national survival; closing military window; no diplomatic off-ramp |
| T3 → T5 | [Not observed; theoretical] | Nuclear first-strike doctrine; breakdown of command-and-control; extreme existential threat |

### 7.2 Skip Barrier Functional Form

For skip from tier j to tier k (where k > j+1):

$$S^{**}_{j \to k} = \left(\Phi^{FMA}_{AB}\right)^{\eta_\phi} \cdot \left(\text{WindowClose}_{AB}\right)^{\eta_w} \cdot \left(\text{OffRampAbsence}_{AB}\right)^{\eta_r} \cdot \left(1 - \mathcal{N}_{AB}^{\eta_n}\right)$$

where **WindowClose** measures how rapidly the initiator's military advantage is eroding (e.g., US industrial ramp-up in 1941 for Japan) and **OffRampAbsence** measures the absence of diplomatic or institutional channels to resolve without escalation.

**Note:** The T2→T4 skip (Pearl Harbor type) adds a **coercion severity threshold** term: the skip probability is near zero unless $S_2 > \tau_E$ (default $\tau_E = 0.70$), encoding that only severe economic siege — not mild sanctions — provokes direct war.

---

## 8. Historical Escalation Paths (Corrected)

| Dyad | Escalation path | Skip? | Notes |
|---|---|---|---|
| USA → Japan 1941 | T2 → T4 → T5 | T2→T4 skip | US oil embargo → Pearl Harbor → atomic bombs |
| Japan → USA 1941 | T2 → T4 | T2→T4 skip | Responding to US T2; Pearl Harbor entry |
| Russia → Ukraine | T1 → T3 (2014) → T4 (2022) | None — sequential | 8 years at T3 before T4 |
| USSR ↔ USA Cuba 1962 | T2 | None | Resolved at T2; never reached T3 |
| India ↔ Pakistan Kargil 1999 | T2 → T3 | None | Sequential; nuclear ceiling held at T3 |
| India ↔ Pakistan Sindoor 2025 | T3 (re-entry) | None | Already at T3 from ongoing rivalry |
| Iraq → Kuwait 1990 | T1 → T4 | T1→T4 skip | Surprise invasion; no economic or limited phase |
| North Korea → South Korea 1950 | T1 → T4 | T1→T4 skip | Surprise invasion |
| Falklands 1982 | T1 → T3 → T4 | T1→T3 skip | Economic phase absent; limited then escalated |

---

## 9. Nuclear Shadow and T5 Structure

### 9.1 Nuclear Shadow Θ

$\Theta_{AB} \in [0,1]$ measures the degree to which nuclear use is actively in the decision calculus of either leadership, even while the dyad sits below T5.

| Value | Meaning | Calibration case |
|---|---:|---|
| 0.0 | No nuclear dimension | France–Germany |
| 0.1 | Latent capability, no discourse | India–China 2020 |
| 0.3 | Vague rhetorical references | NK–SK routine tension |
| 0.6 | Explicit doctrine-linked threats | Kargil 1999 |
| 0.8 | Credible intelligence of active consideration + doctrine change | Russia–Ukraine Oct 2022 |
| 1.0 | Deployment order given | — (never observed post-1945 under MAD) |

Θ is coded from: leadership statements linked to nuclear doctrine; intelligence assessments; third-party intervention patterns (Chinese warning to Russia in 2022 is a Θ signal); nuclear force posture changes (alert level, dispersal, readiness).

### 9.2 Nuclear Deterrence Stability N_AB

$\mathcal{N}_{AB} \in [0,1]$ measures the structural stability of mutual deterrence.

High N (stable): both sides have secure second-strike capability; command-and-control intact; no launch-on-warning pressure.

Low N (unstable): one side vulnerable to first strike; decapitation risk; short decision windows; tactical nuclear weapons in theater.

### 9.3 T5 Conditional Probability

$$P(T5 \mid T4) = \sigma\!\left(\alpha_{45} + \beta_\Theta \Theta_{AB} + \beta_N (1-\mathcal{N}_{AB}) + \beta_\Psi \Psi_{AB} \cdot D_A + \beta_\text{mono} \cdot \text{Monopoly}_{AB}\right)$$

where **Monopoly**_{AB} = 1 codes the 1945 structural regime (nuclear use against non-nuclear adversary), quarantining the only confirmed T5 case from the MAD parameter set.

---

## 10. De-escalation Exits

Three exit states from any tier k > T0:

| Exit type | Mechanism | Model representation |
|---|---|---|
| Negotiated de-escalation | Both actors agree to lower tier; ceasefire, settlement, negotiated withdrawal | Bilateral concession probability product; requires third-party mediation variable |
| Capitulation | One actor's military or political position collapses; accepts other's terms | Asymmetric collapse probability; function of military balance deterioration, domestic instability |
| Frozen conflict | Neither side escalates or de-escalates; conflict persists at current tier indefinitely | Duration dependence term; conflict trap (Hegre et al. 2017) — onset raises risk for 20+ years |

Frozen conflict is empirically common (Korea since 1953; Cyprus since 1974; various post-Soviet conflicts). The model should encode it as a third competing hazard alongside escalation and de-escalation.

---

## 11. Open Questions — What Needs to Be Finalized

The following decisions are required before v19.0 can be fully specified. Each represents a genuine theoretical or empirical choice.

---

**Open Question 1 — T5 Ising field coupling σ_5**

Current draft: σ_5 = 1 (linear with other tiers)

Alternative: σ_5 > 1 (e.g., σ_5 = 2), reflecting that the decision to use nuclear weapons is qualitatively more sensitive to public opinion / regime type than conventional war escalation.

*What needs to be decided:* Is the σ_k = k/5 linear coupling theoretically justified for T5, or does nuclear use belong to a qualitatively different decision category that warrants a non-linear coupling?

---

**Open Question 2 — T5 structural regimes**

Current draft: Monopoly_{AB} binary covariate quarantines the 1945 case.

Alternative: Treat T5-Monopoly and T5-MAD as fully separate sub-models with different parameter sets — two different equations sharing the T5 label.

*What needs to be decided:* Are these the same decision process with a covariate adjustment, or fundamentally different game-theoretic structures requiring separate equations?

---

**Open Question 3 — Severity scalar S_k coding rules**

The severity dimensions are specified in §6 but the coding thresholds need to be set precisely. Specifically:
- What is the breakpoint between S_3=low and S_3=high for limited military action? Fatality count? Geographic scope? Duration?
- How is S_4 coded for wars that are sustained but geographically bounded (e.g., Russia–Ukraine which is large but not globally mobilizing)?

*What needs to be decided:* Precise operational coding rules for each S_k, with calibration anchors analogous to the Ψ_{AB} table in v18.3.

---

**Open Question 4 — Bilateral escalation: competing hazards vs. strategic game**

Current draft: hazard of escalation = 1 - (1-p_A)(1-p_B) [competing hazards]

Alternative: Model as a sequential game where A moves, B observes and responds — closer to the IIG (Bueno de Mesquita–Lalman) architecture.

*What needs to be decided:* Competing hazards is simpler and estimable from standard data. The sequential game is theoretically richer but requires equilibrium assumptions and is harder to estimate. Which fits the model's intended use (personal forecasting tool + potential academic publication)?

---

**Open Question 5 — Skip barrier for T2→T4**

Current draft: T2→T4 skip requires S_2 > τ_E = 0.70 (severe coercion threshold).

*What needs to be decided:* Is 0.70 the right threshold, or should τ_E be estimated from data? Is the threshold multiplicative or additive with the other S^** terms? Does the closing military window (WindowClose) need its own variable independent of the existing -Ẇ term from v18.3?

---

**Open Question 6 — Frozen conflict as a third hazard**

Current draft: acknowledges frozen conflict as an exit state but does not fully specify it.

*What needs to be decided:* Does the model explicitly estimate a frozen-conflict hazard, or does duration dependence (time-since-onset variable) implicitly capture it? If explicit, what variables predict freezing vs. resolution?

---

**Open Question 7 — How L_base distributes across the conditional chain**

In v18.3, L_base entered all tiers. In the conditional chain, L_base (structural rivalry, motive, cooperation) is most relevant at T0→T1. At higher tiers, dynamic war-phase variables (military balance deterioration, domestic instability, third-party involvement) become more important.

*What needs to be decided:* Does L_base enter all tier transitions with full weight, or does its weight decay at higher tiers? A decay function (e.g., weight = e^{-λk}) would encode the idea that structural conditions matter most for conflict onset and less for war termination.

---

**Open Question 8 — Time dynamics and conflict history**

Not yet formally specified in v19.0. Needed:
- Duration spline or cubic time polynomial (Beck–Katz–Tucker 1998) for dyad-years since last MID
- Conflict trap indicator (Hegre et al. 2017: onset raises risk for 20+ years)
- Within-crisis time dynamics: how does escalation probability change as a crisis extends?

*What needs to be decided:* Which temporal variables enter which tier transitions? Does conflict history enter T1 onset only, or does it also affect conditional escalation at T2–T4?

---

## 12. Parameters Carried Forward From v18.3

| Parameter | Role | Status |
|---|---|---|
| β_0 | Baseline log-odds | Carried forward — enters T1 transition |
| β_m | Structural motive weight | Carried forward — enters T1, T2 transitions |
| β_r | Spark/rivalry weight | Carried forward — enters T1 |
| β_a | Alignment weight | Carried forward — enters T1 |
| β_c | Cooperation weight (<0) | Carried forward — enters T1 |
| β_e | Economic pressure direct weight | Carried forward — enters T2 |
| β_{e2} | Barrier erosion coefficient | Carried forward — enters T3 |
| φ_E | Blockage amplification | Carried forward — enters T3 |
| β_s | Skip amplification | Expanded to tier-specific β_s^{jk} |
| β_h | Field coupling | Carried forward; σ_k revised |
| Δ_{12}, Δ_{23} | Escalation barriers | Replaced by α_{jk} intercepts per transition |

## New Parameters (v19.0)

| Parameter | Role |
|---|---|
| α_{jk} | Intercept for tier-j → tier-k transition |
| β_{jk} | Severity weight for tier-j severity driving tier-k entry |
| S_k | Within-tier severity scalar (per-dyad input) |
| Θ_{AB} | Nuclear shadow intensity (per-dyad input) |
| N_{AB} | Nuclear deterrence stability (per-dyad input) |
| β_Θ | Nuclear shadow weight in T5 transition |
| β_N | Deterrence instability weight in T5 transition |
| η_r | Off-ramp absence exponent in skip barrier |
| τ_E | Economic coercion severity threshold for T2→T4 skip |
| Monopoly_{AB} | Binary: 1 for T5-Monopoly regime (1945 case) |

---

## 13. Validation Priorities for v19.0

Given the increased tier count and conditional chain structure:

1. **Ordinal consistency check:** Confirm P(T1) > P(T2) > P(T3) > P(T4) > P(T5) under baseline parameter assumptions across a synthetic dyad-year panel.

2. **Identification check:** Verify that each conditional transition model is separately identified — each transition must have at least one covariate that enters it but not adjacent transitions (exclusion restriction).

3. **Calibration anchors:** Each tier transition should be calibrated against at least three historical dyad cases with known tier assignment, analogous to the Ψ_{AB} table in v18.3.

4. **Skip vs. sequential rate:** The model should reproduce the empirical split — most T4 entries come via sequential T3→T4, not via T1→T4 or T2→T4 skips — as a model-fit check.

5. **Nuclear deterrence test:** Among nuclear dyads, P(T5|T4) should be substantially lower than among non-nuclear dyads at equivalent structural conditions. This tests whether N_{AB} and Θ_{AB} are doing real work.

---

*Version 19.0 Draft — Open questions marked in §11. Full specification pending resolution of Open Questions 1–8.*