# Unified Equation of Interstate War (Directed-Dyad Variant) v22.0

## Complete Specification with Full Context & Definitions

**Version:** 22.0 (Probability Composition, Directed Dyads & Bidirectional Skip Update)
**Status:** Specification Phase — Awaiting Empirical Calibration (NOT production-validated)
**Last Updated:** May 2026

---

## PART 0: VERSION 22.0 CHANGES FROM 21.3

v22.0 does not add variables. It closes three structural gaps that prevented v21.3 from producing a well-defined output, and corrects an architectural asymmetry between escalation and de-escalation. The variable set and coding guidance are otherwise inherited unchanged from v21.3.

| Element | v21.3 | v22.0 |
|---------|-------|-------|
| **Output definition** | Claimed 7-tier vector $\pi_{kj}$, but only emitted 3 direction probabilities | **Explicit composition equation linking direction probabilities to allocation weights** |
| **Dyad type** | Unordered dyad with [DIRECTIONAL] tags that had no referent | **Directed dyad $(i \rightarrow j)$; directional variables now carry an actor subscript** |
| **Skip architecture** | Escalation skip ($S^{**}$) fed the *direction* score; de-escalation skip lived only in allocation | **Both skip functions live in the *allocation* stage; direction stage decides only up/stay/down** |
| **De-escalation shape** | Monotone exponential decay only | **Bimodal allocation permitting both negotiated step-down and collapse-to-floor** |
| **Status claim** | "Production-Ready" | **Removed. Coefficients are priors until calibrated against MID/UCDP-dyadic data** |
| **Tier taxonomy, 13-variable core, $C_{peace}$, $V_{contagion}$** | — | **UNCHANGED** |

**Why this matters:** v21.3 described a two-stage model (decide a direction, then decide how far) but never wrote the equation that multiplies the two stages into a final probability distribution. As a result the "7-tier output" was an aspiration, not a specification. v22.0 makes the two-stage structure explicit, gives the directional variables a defined referent by moving to directed dyads, and removes a hidden asymmetry whereby escalation received skip logic in two places and de-escalation in only one.

---

## PART 1: OVERVIEW & ARCHITECTURE

### 1.1 What This Model Does

The Unified Equation of Interstate War (UIW) v22.0 is a **directed-dyad probability model** for estimating next-period interstate conflict escalation, persistence, and de-escalation. For an ordered pair $(i \rightarrow j)$ — read "the prospect of $i$ escalating against $j$" — it estimates the full distribution over next-period tiers.

The model is explicitly **two-stage**:

1. **Direction stage.** Given the current tier $k$, decide the probability of moving *down*, *staying*, or moving *up*: $(P_\downarrow, P_0, P_\uparrow)$.
2. **Allocation stage.** Conditional on a direction, distribute that direction's probability mass across the reachable destination tiers using skip/allocation weights $\omega^-$ (downward) and $\omega^+$ (upward).

The final output is the composition of the two stages:

$$\pi_{kj}(t) = \text{Pr}(\text{next tier} = j \,|\, \text{current tier} = k, \text{ inputs at } t)$$

where $\pi_{kj}$ is a 7-element vector $[\pi_0, \ldots, \pi_6]$ summing to 1. The composition is defined explicitly in Part 3.4 — this is the equation that was missing in v21.3.

**Recommended forecast interval:** 30 days. See §1.5 for the caveat this interval raises for slow-moving structural variables.

---

### 1.2 Seven-Tier Escalation Taxonomy (PRESERVED)

| **Tier** | **Name** | **Military Activity** | **Operational Definition** | **Examples** |
|----------|----------|----------------------|----------------------------|--------------|
| **T0** | Peace | None | No military activity or threat thereof | US–Canada 2020 |
| **T1** | Diplomatic Crisis | None | Formal friction: protests, recalls, ultimatums, UN votes | US–Iran 2019 |
| **T2** | Economic Coercion | None | Active sanctions, trade restrictions, financial exclusion | Russia–Ukraine 2014 |
| **T3** | Proxy/Indirect Military | Passive support only | Arms, intel, training, funding to B's enemies; A not in direct combat | Iran funding Hezbollah |
| **T4** | Limited Direct Military | Direct combat | Any direct exchange of fire between A and B forces | USS *Reuben James* 1941 |
| **T5** | Strategic War | Expansive conventional | Nationwide / multi-front warfare, sustained campaigns | Ukraine–Russia 2022+ |
| **T6** | Nuclear Exchange | Nuclear weapons used | Nuclear weapons detonated in anger | Japan 1945 |

### 1.3 Tier Assignment Rule (Foundational, UNCHANGED)

Assign the **highest** tier fully supported by operational evidence, descending from T6. Do not mix diplomatic language with operational coding: if direct combat is active, the dyad is at least T4 even if leaders deny being at war.

### 1.4 Directed-Dyad Convention (NEW)

A "dyad" is now an **ordered pair** $(i \rightarrow j)$. To assess a relationship between states A and B, run the model **twice**: once as $(A \rightarrow B)$ and once as $(B \rightarrow A)$.

- The **current tier $k$** is shared between both directions (the operational state of the relationship is symmetric: if A and B are exchanging fire, both directions are at T4).
- **Directional variables** — $FMA$ and $-\dot{W}$ — are coded *from the perspective of the attacking actor named first*. $FMA_{A \rightarrow B}$ is A's first-mover advantage against B; this need not equal $FMA_{B \rightarrow A}$.
- **Symmetric variables** — $\Omega, \Xi, V_{contagion}, Nuc$ — take the same value in both directions.
- The two runs produce two upward-pressure profiles. The relationship's escalation risk is driven by $\max$ over the two directions; de-escalation requires both directions to step down. (See §3.6 for how the two directed runs are reconciled into a relationship-level forecast.)

This resolves the v21.3 incoherence where $FMA$ was tagged [DIRECTIONAL] in an unordered model that had no actor to attach the direction to.

### 1.5 Forecast-Interval Caveat (NEW)

Most structural inputs ($\Omega, \Xi, -\dot{W}$) move on a timescale of years, not the 30-day forecast window. Over a single period they are near-constant, so almost all *period-to-period* predictive variation comes from the fast-moving inputs: $Shock_k$, $Dip_{cap}$, and $V_{contagion}$. This is expected and acceptable for a structural model — the slow variables set the *baseline hazard*, the fast variables provide the *timing signal* — but it should be understood when interpreting why two adjacent forecasts differ. Do not expect the structural index $E_t$ to explain month-to-month movement; it explains the level around which movement occurs.

### 1.6 Model Architecture Summary

```
INPUT CODING (CORE 13, per directed dyad i->j)
├─ Path Dependency: Current Tier (X_t), Duration (D_k)
├─ Structural/Military: Rivalry (Ω), Contiguity (Ξ),
│                       First-Mover Adv (FMA_{i->j}), Closing Window (-Ẇ_{i->j})
├─ Economic: Cost of Peace (C_peace), Exhaustion (W_x)
├─ Operational/Diplomatic: Off-Ramp Absence (ORA), Stalemate (Stal_t), Dip Capacity (Dip_cap)
└─ Catalysts/Environment: Kinetic Shock (Shock_k), Nuclear Gate (Nuc),
                          Bidirectional Contagion (V_contagion)

STAGE 1 — DIRECTION
├─ Escalation Pressure Index (E_t)
├─ De-Escalation Capacity Index (D_t)
├─ Persistence Lock Index (S_t)
└─ Movement scores (U↓, U0, U↑) → softmax → (P↓, P0, P↑)

STAGE 2 — ALLOCATION
├─ Upward skip weights ω⁺ (catalytic, magnitude-of-jump)
└─ Downward skip weights ω⁻ (BIMODAL: step-down vs collapse)

COMPOSITION
└─ π_j = P↓·ω⁻_{kj} (j<k) ; P0 (j=k) ; P↑·ω⁺_{kj} (j>k)
```

---

## PART 2: INPUT VARIABLES & CODING GUIDANCE (THE CORE 13)

Inherited from v21.3 unchanged except for the two directional variables, which now carry the actor subscript of the directed dyad. Variables are bounded **[0, 1]** except $V_{contagion} \in [-1, +1]$, $X_t \in \{0,\ldots,6\}$, and $D_k \in [0, \infty)$.

### 2.1 Path Dependency
- **CurrentTier ($X_t$)** — operational reality now; anchor for path dependency. $\{0,\ldots,6\}$. Shared across both directed runs.
- **Duration ($D_k$)** — time at current tier, months/10. $[0,\infty)$.

### 2.2 Structural & Military
- **Rivalry ($\Omega$)** — long-term structural enmity. [0,1]. 0=allies, 0.5=competitors, 1.0=existential. *Symmetric.*
- **Contiguity ($\Xi$)** — shared border and territorial dispute. {0, 0.5, 1}. 0=no border, 0.5=border no dispute, 1.0=active territorial dispute. *Symmetric.*
- **First-Mover Advantage ($FMA_{i \rightarrow j}$) [DIRECTIONAL]** — tactical advantage to *actor $i$* from striking $j$ first. [0,1]. *Coded per direction.*
- **Closing Window ($-\dot{W}_{i \rightarrow j}$) [DIRECTIONAL]** — adverse long-term power shift creating "now-or-never" pressure *for actor $i$*. [0,1]. *Coded per direction.*

### 2.3 Economic
- **Cost of Peace ($C_{peace}$)** — economic/internal-security burden of the status quo. [0,1]. 0–0.2 peace profitable; 0.4–0.6 costly but manageable; 0.8–1.0 ruinous. *See §6.4 on the observable-burden vs counterfactual measurement issue.*
- **Exhaustion ($W_x$)** — material/demographic/fiscal depletion from the current tier. [0,1].

### 2.4 Operational & Diplomatic
- **Off-Ramp Absence ($ORA$)** — structural lack of viable exits. [0,1].
- **Stalemate ($Stal_t$)** — inability of either side to achieve breakthrough. [0,1].
- **Diplomatic Capacity ($Dip_{cap}$)** — mediator leverage, communication channels, de-escalation signaling. [0,1].

### 2.5 Catalysts & Environment
- **Kinetic Shock ($Shock_k$)** — recent fatality/strike/mobilization spikes. [0,1].
- **Nuclear Gate ($Nuc$)** — weapon possession and arsenal instability; 0 if neither side is nuclear. [0,1]. *Symmetric.*
- **Bidirectional Contagion ($V_{contagion}$)** — regional spillover. [-1,+1]. Negative = peace contagion, positive = conflict contagion. *Symmetric.* **Lag by at least one period and instrument with distance-to-regional-conflict rather than local conflict intensity, to avoid the reflection problem (§6.3).**

---

## PART 3: MATHEMATICAL SPECIFICATION

### 3.1 Composite Indices

Computed per directed dyad (so $E_t$ differs between $(A\rightarrow B)$ and $(B\rightarrow A)$ through the directional terms). v22.0 adds the rivalry × contiguity interaction, the single most-supported structural interaction in the conflict literature.

**Escalation Pressure Index ($E_t$):**
$$E_t = \text{clip}\!\left( \alpha_1\Omega + \alpha_2\Xi + \alpha_3 FMA_{i\rightarrow j} + \alpha_4(-\dot{W}_{i\rightarrow j}) + \alpha_5 C_{peace} + \alpha_6 V_{contagion} + \alpha_7(\Omega \cdot \Xi),\; 0,\; 1 \right)$$

**De-Escalation Capacity Index ($D_t$):**
$$D_t = \text{clip}\!\left( \theta_1 W_x + \theta_2 Dip_{cap} + \theta_3(1 - C_{peace}) - \theta_4 V_{contagion},\; 0,\; 1 \right)$$

**Persistence Lock Index ($S_t$):**
$$S_t = \text{clip}\!\left( \rho_1 Stal_t + \rho_2 ORA + \rho_3 D_k + \rho_4 V_{contagion},\; 0,\; 1 \right)$$

> **Note for calibration:** the `clip` saturation creates zero-gradient regions. This is harmless while coefficients are hand-set, but once estimation begins, replace `clip(linear, 0, 1)` with a sigmoid composite $\sigma(\cdot)$ for smooth, naturally bounded indices.

### 3.2 Movement Scores (Direction Stage)

Note the change from v21.3: the escalation skip term $u_{skip}S^{**}$ has been **removed** from $U^\uparrow$. The direction stage now decides *only* up/stay/down. All skip/magnitude logic moves to the allocation stage (§3.5). This makes escalation and de-escalation symmetric: neither receives skip logic in the direction score.

**Downward Pressure:**
$$U_k^{\downarrow} = a_k^{\downarrow} + b_D D_t - b_E E_t - b_{ORA} ORA$$

**Persistence Pressure:**
$$U_k^{0} = a_k^{0} + r_S S_t + r_D D_k$$

**Upward Pressure:**
$$U_k^{\uparrow} = a_k^{\uparrow} + u_E E_t - u_D D_t + u_Z Shock_k$$

### 3.3 Direction Probabilities (Softmax)

$$Z = \exp(U_k^\downarrow) + \exp(U_k^0) + \exp(U_k^\uparrow)$$
$$P_\downarrow = \frac{\exp(U_k^\downarrow)}{Z}, \quad P_0 = \frac{\exp(U_k^0)}{Z}, \quad P_\uparrow = \frac{\exp(U_k^\uparrow)}{Z}$$

**Boundary constraints:**
- $P_\downarrow(k=0) = 0$ (cannot de-escalate below peace); renormalize over $\{P_0, P_\uparrow\}$.
- $P_\uparrow(k=6) = 0$ (no tier above nuclear exchange); renormalize over $\{P_\downarrow, P_0\}$.

### 3.4 Composition Equation (THE KEY ADDITION)

This is the equation v21.3 omitted. The probability of landing in tier $j$ is the direction probability multiplied by the allocation weight for that tier within the chosen direction:

$$\boxed{\;\pi_{kj} = \begin{cases} P_\downarrow \cdot \omega^-_{kj} & j < k \\[4pt] P_0 & j = k \\[4pt] P_\uparrow \cdot \omega^+_{kj} & j > k \end{cases}\;}$$

**Mass conservation.** Because $\sum_{j<k}\omega^-_{kj} = 1$ and $\sum_{j>k}\omega^+_{kj} = 1$ (each allocation distribution is internally normalized), the total mass is conserved automatically:

$$\sum_{j=0}^{6} \pi_{kj} = P_\downarrow \underbrace{\sum_{j<k}\omega^-_{kj}}_{=1} + P_0 + P_\uparrow \underbrace{\sum_{j>k}\omega^+_{kj}}_{=1} = P_\downarrow + P_0 + P_\uparrow = 1.$$

Persistence ($j=k$) is treated as a single destination and is not subdivided. This is intentional: "stay at the current tier" is one outcome, regardless of how many tiers lie above or below it.

### 3.5 Allocation Stage — Skip Functions

Both skip functions now live here. Each is a normalized distribution over the reachable tiers in its direction.

#### 3.5.1 Upward Allocation $\omega^+$ (Catalytic Skip)

Upward jumps are driven by a catalyst that can vault the dyad past adjacent tiers (e.g., a surprise attack carrying T2 → T4). The skip *propensity* (renamed from the misleading "Skip Barrier") is:

$$\Sigma^{\uparrow}_{i \rightarrow j} = \left(FMA_{i\rightarrow j}\right)^{\eta_\phi} \cdot \left(-\dot{W}_{i\rightarrow j}\right)^{\eta_w} \cdot \left(ORA\right)^{\eta_r} \cdot \left(1 - Nuc^{\eta_n}\right)$$

> **Naming fix.** v21.3 called this the "Skip Barrier" but it *adds* to skip likelihood — it is a skip *propensity*, not a barrier. High $FMA$, a closing window, and absent off-ramps all make a large jump *more* likely. The $(1 - Nuc^{\eta_n})$ factor encodes that nuclear dyads are *less* prone to conventional skip-escalation (escalation is more deliberate/deterred); when $Nuc=0$ this factor is 1, so non-nuclear dyads have the highest conventional skip propensity. This is consistent with — not contradicted by — the separate hard gate that blocks entry into T6 itself (§3.7).

The upward weights combine a distance-decay with the skip propensity. Higher $\Sigma^\uparrow$ flattens the decay, putting more mass on distant (multi-tier) jumps:

$$\omega^+_{kj} \;\propto\; \exp\!\left[-\lambda^+_k \,(j - k - 1)\,(1 - \Sigma^{\uparrow})\right] \cdot G^+_{kj}, \qquad j > k$$

where $G^+_{kj}$ is the gate anchor for the jump size (§3.7) and weights are normalized so $\sum_{j>k}\omega^+_{kj}=1$. When $\Sigma^\uparrow \to 0$, the decay is steep and nearly all mass sits on the adjacent tier $k+1$; when $\Sigma^\uparrow \to 1$, the exponent collapses toward 0 and mass spreads across distant tiers.

#### 3.5.2 Downward Allocation $\omega^-$ (Bimodal: Step-Down vs Collapse)

De-escalation is **not** the mirror image of escalation. Empirically it has two distinct modes:

1. **Negotiated step-down** — the dyad eases one tier (T5 → T4): a ceasefire, partial withdrawal, tactical pause. Mass concentrates on the adjacent tier $k-1$.
2. **Collapse / capitulation** — regime change, surrender, or sudden settlement drops the dyad most of the way to the floor (T5 → T0/T1) in one period.

A single monotone exponential decay cannot represent this — it is **bimodal**, not monotone. v22.0 therefore models $\omega^-$ as a two-component mixture:

$$\omega^-_{kj} \;\propto\; \underbrace{(1 - \kappa)\,\exp\!\left[-\lambda^-_k\,(k - j - 1)\right]}_{\text{step-down mode}} \;+\; \underbrace{\kappa \, C_{kj}}_{\text{collapse mode}}, \qquad j < k$$

normalized so $\sum_{j<k}\omega^-_{kj} = 1$, where:

- $\lambda^-_k$ governs the step-down decay (large $\lambda^-_k$ → mass on $k-1$).
- $C_{kj}$ is the **collapse kernel**, placing mass on the floor tiers (default: concentrated on $j \in \{0, 1\}$, e.g. $C_{kj} = 1$ for $j \le 1$ and $0$ otherwise, then normalized within the mixture).
- $\kappa \in [0, 1]$ is the **collapse weight** — the probability that, *given* de-escalation, it takes the collapse form rather than the step-down form.

**Driving $\kappa$.** Collapse is more likely when exhaustion is extreme and off-ramps have just opened (a brittle combatant suddenly given an exit), and less likely in a grinding stalemate with no exits:

$$\kappa = \sigma\!\big(c_0 + c_W W_x + c_{Dip} Dip_{cap} - c_{Stal} Stal_t - c_{ORA} ORA\big)$$

with $\sigma$ the logistic function. Intuition: high exhaustion + high diplomatic capacity push toward a clean break to the floor; high stalemate + absent off-ramps push toward incremental step-down (if any de-escalation happens at all).

> This is the resolution to the asymmetry you flagged: v21.3 gave escalation skip logic in two places (direction score *and* allocation) and de-escalation skip logic in only one. v22.0 puts **both** skip functions in allocation, and lets de-escalation carry a shape (bimodal) appropriate to how wars actually end, rather than forcing it to mirror escalation's catalytic-jump shape.

### 3.6 Reconciling the Two Directed Runs

For a relationship between A and B, run $(A \rightarrow B)$ and $(B \rightarrow A)$. The shared current tier $k$ means both runs describe movement of the same relationship; they differ only in their directional escalation pressure. Combine:

- **Escalation:** $P_\uparrow^{\text{rel}} = \max\!\big(P_\uparrow^{A\rightarrow B},\, P_\uparrow^{B\rightarrow A}\big)$ — either party initiating escalates the relationship. Use the upward allocation $\omega^+$ of whichever direction supplied the max.
- **De-escalation:** $P_\downarrow^{\text{rel}} = \min\!\big(P_\downarrow^{A\rightarrow B},\, P_\downarrow^{B\rightarrow A}\big)$ — de-escalation requires both sides to wind down; the more committed party gates the step-down.
- **Persistence:** the residual, $P_0^{\text{rel}} = 1 - P_\uparrow^{\text{rel}} - P_\downarrow^{\text{rel}}$ (clip at 0 and renormalize if the max/min combination overshoots).

This reporting rule is a default, not a derived identity — flag it for calibration alongside the coefficients.

### 3.7 Hard Gates (Destination Constraints)

Applied during allocation, independent of the soft decay weights:

| Gate | Rule |
|------|------|
| Nuclear floor | If $Nuc = 0$, set $\omega^+_{k,6} = 0$ (T6 unreachable). Renormalize remaining upward weights. |
| Adjacent baseline | $G^{\pm}$ default gate = 1.00 for adjacent tier. |
| Two-tier skip | Default gate = 0.35. |
| Three-tier skip | Default gate = 0.10. |
| Larger skip | Default gate = 0.02. |

The nuclear gate (blocking *entry into* T6) is logically separate from the $(1-Nuc^{\eta_n})$ term in $\Sigma^\uparrow$ (which down-weights conventional skipping *by* nuclear dyads). Both can hold simultaneously without contradiction.

### 3.8 Default Operational Coefficients (PRIORS, not calibrated)

These are informed priors that define the model's default behavior. **They have not been estimated from data and must be treated as placeholders** until fit against MID / UCDP-dyadic records (§6.1).

| Param | Default | Param | Default | Param | Default |
|-------|---------|-------|---------|-------|---------|
| $a^\downarrow$ | -0.40 | $b_D$ | 1.30 | $u_E$ | 1.35 |
| $a^0$ | 0.20 | $b_E$ | 0.80 | $u_Z$ | 0.55 |
| $a^\uparrow$ | -0.35 | $b_{ORA}$ | 0.80 | $u_D$ | 0.75 |
| $r_S$ | 1.10 | $r_D$ | 0.03 | $\alpha_7$ ($\Omega\Xi$) | 0.50 |
| $\lambda^+_k$ | 1.20 | $\lambda^-_k$ | 1.20 | $\kappa$ params $c_\bullet$ | TBD |

---

## PART 4: WORKED EXAMPLE (Direction → Allocation → Composition)

Dyad $(A \rightarrow B)$ currently at **T4**. Suppose index outputs:
$E_t = 0.68$, $D_t = 0.54$, $S_t = 0.47$, $ORA = 0.70$, $D_k = 0.40$, $Shock_k = 0.25$.

**Stage 1 — direction scores:**
$$U_4^\downarrow = -0.40 + 1.30(0.54) - 0.80(0.68) - 0.80(0.70) = -0.802$$
$$U_4^0 = 0.20 + 1.10(0.47) + 0.03(0.40) = 0.729$$
$$U_4^\uparrow = -0.35 + 1.35(0.68) - 0.75(0.54) + 0.55(0.25) = 0.298$$

Softmax → approximately $P_\downarrow = 0.13$, $P_0 = 0.59$, $P_\uparrow = 0.28$.

**Stage 2 — allocation.** Suppose $\Sigma^\uparrow = 0.30$ (moderate skip propensity). Upward decay is fairly steep, so $\omega^+$ puts roughly $\{T5: 0.80, T6: 0.20\}$ — but if $Nuc=0$, T6 is gated out and $\omega^+ = \{T5: 1.0\}$. For downward, suppose $\kappa = 0.25$ (some collapse risk): $\omega^-$ might be $\{T3: 0.55, T2: 0.20, T1: 0.15, T0: 0.10\}$ — note the non-zero mass at the floor from the collapse component, which a pure decay would have suppressed.

**Composition** (with $Nuc=0$):
$$\pi = [\,\pi_0, \pi_1, \pi_2, \pi_3, \pi_4, \pi_5, \pi_6\,]$$
$$= [\,0.13(0.10),\; 0.13(0.15),\; 0.13(0.20),\; 0.13(0.55),\; 0.59,\; 0.28(1.0),\; 0\,]$$
$$\approx [\,0.013,\; 0.020,\; 0.026,\; 0.072,\; 0.59,\; 0.28,\; 0\,]$$

Sums to 1. The dyad is most likely to persist at T4, with escalation to T5 the leading move and a small but non-negligible chance of collapse toward the floor.

---

## PART 5: IMPLEMENTATION WORKFLOW

1. **Assign current tier $X_t$** from operational evidence (shared across both directions).
2. **Choose a direction** $(i \rightarrow j)$; code $FMA_{i\rightarrow j}$ and $-\dot{W}_{i\rightarrow j}$ for that actor.
3. **Code symmetric variables** $\Omega, \Xi, C_{peace}, W_x, ORA, Stal_t, Dip_{cap}, Shock_k, Nuc, V_{contagion}$ (lagged).
4. **Compute indices** $E_t, D_t, S_t$ (including the $\Omega\Xi$ interaction).
5. **Stage 1:** movement scores → softmax → $(P_\downarrow, P_0, P_\uparrow)$, apply boundary constraints.
6. **Stage 2:** compute $\Sigma^\uparrow$ and $\kappa$; build $\omega^+$ and bimodal $\omega^-$; apply hard gates.
7. **Compose** via §3.4 to get $\pi$.
8. **Repeat for the reverse direction**, then reconcile (§3.6) for a relationship-level forecast.
9. **Report** $E_t, D_t, S_t$, both directed $\pi$ vectors, and the reconciled distribution.

---

## PART 6: VALIDATION, LIMITATIONS & OPEN ISSUES

### 6.1 What "Calibration" Requires Before Any Production Claim
- Point estimates **and standard errors** for all coefficients via penalized MLE or Bayesian estimation on a training set (e.g. 1990–2015 MIDs).
- **Out-of-sample** Brier score, log-loss, and AUROC/AUPR by tier, with special attention to rare tiers (T5, T6). The two-stage architecture is retained precisely because it borrows strength across the direction decision and handles class imbalance better than a flat 7-way multinomial would.
- **Inter-coder reliability** (Krippendorff's $\alpha$ / Cohen's $\kappa$) for all 13 inputs coded by independent analysts from identical raw material.

Until these exist, every coefficient in §3.8 is an intelligent guess. Run the model against 1990–2020 out-of-sample MIDs and let the data decide whether $u_E$ is really 1.35.

### 6.2 Retained Limitations
- Rare-event tails (T6) remain hard to calibrate.
- $V_{contagion}$ requires regional network analysis to score well.
- Multi-actor wars exceed a dyadic (even directed-dyadic) simplification.

### 6.3 Contagion Endogeneity (Manski Reflection)
$V_{contagion}$ risks circularity: a dyad's own war inflates regional violence, which then feeds back as "contagion" raising the dyad's escalation probability. Mitigation: lag $V_{contagion}$ at least one period and instrument it with geographic distance to regional conflict rather than local conflict intensity. Unaddressed, it manufactures false precision.

### 6.4 $C_{peace}$ Measurement
The "burden of the status quo *relative to war*" framing embeds a counterfactual that two analysts will score differently, and is near-impossible to code without hindsight at low tiers. Recommended decomposition: code an observable **Status-Quo Burden** (sanctions, lost trade, mobilization costs already paid) and drop the "relative to war" wording from the coding instruction.

### 6.5 Structural Incompleteness (Regime Type)
The model deliberately excludes regime type. Note that the joint-democracy / "democratic peace" finding is **contested** — a substantial literature argues it is largely absorbed by territorial disputes and regional instability, which this model already captures through $\Xi$ and $V_{contagion}$. If regime type is added later, add it as a *testable* term and check whether it improves out-of-sample fit *beyond* $\Xi$, rather than assuming it must.

### 6.6 Proper Use
✓ Early warning, scenario comparison, sensitivity analysis.
✗ Deterministic forecasting or claims of point certainty.

---

## PART 7: APPENDIX — VARIABLE SUMMARY

| Variable | Name | Type | Range | Directional? |
|----------|------|------|-------|--------------|
| $X_t$ | Current Tier | State | {0,…,6} | shared |
| $D_k$ | Duration | State | [0,∞) | shared |
| $\Omega$ | Rivalry | Structural | [0,1] | symmetric |
| $\Xi$ | Contiguity | Structural | {0,0.5,1} | symmetric |
| $FMA_{i\rightarrow j}$ | First-Mover Adv. | Military | [0,1] | **directional** |
| $-\dot{W}_{i\rightarrow j}$ | Closing Window | Military | [0,1] | **directional** |
| $C_{peace}$ | Cost of Peace | Economic | [0,1] | symmetric |
| $W_x$ | Exhaustion | Economic | [0,1] | symmetric |
| $ORA$ | Off-Ramp Absence | Diplomatic | [0,1] | symmetric |
| $Stal_t$ | Stalemate | Operational | [0,1] | symmetric |
| $Dip_{cap}$ | Diplomatic Cap. | Diplomatic | [0,1] | symmetric |
| $Shock_k$ | Kinetic Shock | Catalyst | [0,1] | symmetric |
| $V_{contagion}$ | Regional Contagion | Geopolitical | [-1,+1] | symmetric |
| $Nuc$ | Nuclear Gate | Gatekeeper | [0,1] | symmetric |

**Version 22.0 | Specification Phase — Awaiting Calibration | Probability Composition, Directed Dyads & Bidirectional Skip | May 2026**
