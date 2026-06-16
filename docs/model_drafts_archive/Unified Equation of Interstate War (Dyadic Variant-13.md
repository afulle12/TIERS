# Unified Equation of Interstate War (Dyadic Variant) v19.5 — Specification

## Structured Specification

---

## 1. What v19.5 Changes From v19.4

v19.5 makes two substantive changes. The first restores the skip barrier $S^{**}$ to its structural component form from v18.3/v19.0, replacing the opaque scalar diagnostics that had collapsed it in v19.1. The second adds OffRampAbsence as a direct suppressor of $U_k^\downarrow$, giving blocked diplomatic exits a mechanistic effect on de-escalation probability. All other architecture is unchanged.

| Change | v19.4 | v19.5 |
|---|---|---|
| Skip barrier inputs | Opaque scalars K23, K34, Skip13/14/24/35 | Structural components: FMA, WindowClose, OffRampAbsence |
| $S^{**}$ computation | Analyst-coded scalar per tier pair | Computed: $(\Phi^{FMA})^{\eta_\phi} \cdot (-\dot{W})^{\eta_w} \cdot \text{ORA}^{\eta_r} \cdot (1-\mathcal{N}^{\eta_n})$ |
| Destination allocation skip bonuses | Skip13/14/24/35 scalars | $S^{**}$ with tier-pair multipliers |
| $U_k^\downarrow$ | No exit-availability term | $-\beta_{\text{ORA}} \cdot \text{ORA}$ added — high ORA suppresses de-escalation |
| New global parameters | — | $\eta_\phi, \eta_w, \eta_r, \eta_n, \beta_{\text{ORA}}$ |
| Removed inputs | K23, K34, Skip13, Skip14, Skip24, Skip35 | — |

### Motivation

The collapse of $S^{**}$ into opaque scalars in v19.1 lost the ability to code the structural preconditions of skip transitions independently. For the Japan→USA November 1941 case, the three components carry distinct theoretical content:

- **WindowClose** ($-\dot{W}$): Japan's military window was closing as US industrial production accelerated. This is separable from first-mover capability and separable from the absence of diplomatic exits.
- **FMA** ($\Phi^{FMA}$): Operational surprise capability at Pearl Harbor.
- **OffRampAbsence** (ORA): The Hull-Nomura talks had effectively terminated. This is also a direct suppressor of de-escalation — when no institutional exit exists, the probability of negotiated withdrawal collapses independently of the willingness to concede.

Without restoring these components, the model cannot distinguish a dyad with a closing military window and open diplomatic channels (high WindowClose, low ORA) from one with no window but no exit (low WindowClose, high ORA). The two structural configurations have very different escalation dynamics.

---

## 2–5. Unchanged From v19.4

The six-tier taxonomy (§2), exogenous current-state architecture (§3.1–3.4), aggregate transition outputs (§3.4), and movement probabilities via softmax (§3.6) are unchanged. The bilateral escalation hazard (§4), external public opinion field (§5), within-tier severity (§6), nuclear shadow and T5 structure (§9), de-escalation and persistence exits (§10), and open questions (§11) are unchanged from v19.4.

---

## 3.5 Movement-Category Scores (Updated)

$$
\begin{aligned}
U_k^{\downarrow} &= \alpha_k^{\downarrow} + \beta_{dS} S_k + \beta_M M_{AB}^{\text{med}} + \beta_C C_{AB}^{\text{conc}} + \beta_X X_{AB}^{\text{collapse}} - \lambda_k^{\downarrow} D_k - \beta_{\text{ORA}} \cdot \text{ORA}_{AB} \\[6pt]
U_k^{0} &= \alpha_k^{0} + \rho_k D_k + \beta_F F_{AB} - \beta_M^{0} M_{AB}^{\text{med}} \\[6pt]
U_k^{\uparrow} &= \alpha_k^{\uparrow} + \beta_{uS} S_k + \beta_s S^{**}_{AB} + \sigma_k h_{AB} + \nu_k^{\text{nuke}} + \beta_{\text{haz}} \cdot h_k^{\uparrow}
\end{aligned}
$$

**Change from v19.4:** $U_k^\downarrow$ now includes $-\beta_{\text{ORA}} \cdot \text{ORA}_{AB}$. When diplomatic and institutional exits are absent (ORA $\to 1$), the de-escalation score is suppressed regardless of concession willingness or mediation pressure. This encodes the structural unavailability of exit pathways independently of actor-level willingness to use them.

**Interpretation of the ORA term:** $M_{AB}^{\text{med}}$ and $C_{AB}^{\text{conc}}$ capture whether actors *want* to de-escalate. ORA captures whether the *mechanisms for de-escalation exist*. A dyad can have high concession willingness and no functional exit — the model now distinguishes these.

The $\beta_s S^{**}_{AB}$ term in $U_k^{\uparrow}$ replaces the previous $\beta_s \cdot \text{skipContrib}$ (which drew from opaque K23/K34 scalars). $S^{**}_{AB}$ is now computed from structural components as specified in §7.

---

## 7. Skip Barrier $S^{**}$ (Restored — v18.3 Form with v19.0 Naming)

### 7.1 Structural Components

$$S^{**}_{AB} = \left(\Phi^{FMA}_{AB}\right)^{\eta_\phi} \cdot \left(-\dot{W}_{AB}\right)^{\eta_w} \cdot \left(\text{ORA}_{AB}\right)^{\eta_r} \cdot \left(1 - \mathcal{N}_{AB}^{\eta_n}\right)$$

where all base inputs are in $[0,1]$ and all exponents are $\geq 0$.

| Component | Symbol | Role | Range |
|---|---|---|---|
| First-mover / operational surprise | $\Phi^{FMA}_{AB}$ | Initiator's ability to seize initiative before the target can respond | $[0,1]$ |
| Closing military window | $-\dot{W}_{AB}$ | Rate at which the initiator's relative military advantage is deteriorating | $[0,1]$ |
| Off-ramp absence | $\text{ORA}_{AB}$ | Degree to which diplomatic, institutional, or third-party exit mechanisms are unavailable | $[0,1]$ |
| Deterrence instability | $1 - \mathcal{N}_{AB}^{\eta_n}$ | Reduced deterrence stability raises skip probability (shared with nuclear architecture) | — |

**Key property:** $S^{**}_{AB} = 0$ when any single component is zero. A dyad with no closing window ($-\dot{W} = 0$) has zero skip probability regardless of FMA or ORA. A dyad with functioning exit mechanisms ($\text{ORA} \approx 0$) has near-zero skip probability regardless of military urgency. All four conditions must be present for skip to become structurally probable.

### 7.2 Component Coding Rules

**$\Phi^{FMA}_{AB}$ — First-mover advantage:**

| Value | Meaning | Example |
|---:|---|---|
| 0.05 | No meaningful first-mover advantage; target can respond at equivalent speed | Most dyads |
| 0.30 | Modest initiative advantage; initiator can act faster but target has warning | Falklands 1982 |
| 0.60 | Significant surprise/operational initiative | Surprise mobilization scenarios |
| 0.80 | Strong operational surprise; target's defensive response meaningfully degraded | Iraq→Kuwait 1990 |
| 0.90 | Near-complete operational surprise; target cannot reorient | Japan→Pearl Harbor 1941 |

**$-\dot{W}_{AB}$ — Closing military window:**

| Value | Meaning | Example |
|---:|---|---|
| 0.00 | No closing window; military balance stable or improving for initiator | Most peacetime dyads |
| 0.20 | Slow erosion; initiator expects modest relative decline over 3–5 years | |
| 0.50 | Clear deteriorating trend; initiator expects significant disadvantage within 2 years | |
| 0.70 | Rapidly closing; initiator expects parity loss within 12 months | |
| 0.85 | Acute closure; initiator faces near-term military irrelevance if it waits | Japan Nov 1941 (US industrial ramp-up) |

**$\text{ORA}_{AB}$ — Off-ramp absence:**

| Value | Meaning | Example |
|---:|---|---|
| 0.05 | Multiple functioning exit channels; active negotiation, credible third-party mediation | Most crises |
| 0.25 | Some friction but talks ongoing; off-ramps exist but are degraded | |
| 0.50 | Key channels failing; talks stalled; mediation efforts collapsing | |
| 0.75 | Most exit channels closed; only one or two marginal options remain | |
| 0.90 | No functional exit; talks terminated; no credible mediator; institutional channels exhausted | Japan→USA Nov 1941 (Hull-Nomura dead) |

**Note on ORA double role:** ORA enters both $S^{**}$ (raising skip probability) and $U_k^\downarrow$ (suppressing de-escalation score). These are not redundant: the $S^{**}$ effect raises $P_\uparrow$ by amplifying U↑; the U↓ effect simultaneously compresses $P_\downarrow$. The two channels operate additively on $P_\uparrow - P_\downarrow$.

### 7.3 Destination Allocation Skip Bonuses

Conditional on upward movement, $S^{**}$ weights the second-stage allocation $\omega_{kj}^+$ toward destination tiers that require skip. Each skip type has a tier-pair multiplier reflecting its empirical frequency:

| Skip | Multiplier | Historical basis |
|---|---|---|
| $T1 \to T3$ | $S^{**} \times 2.0$ | Falklands 1982; fast conventional escalation bypassing coercion |
| $T1 \to T4$ | $S^{**} \times 1.5$ | Korea 1950; Iraq→Kuwait 1990; surprise invasion |
| $T2 \to T4$ | $S^{**} \times 2.5$ | Japan→USA 1941; severe coercion + closing window → direct war |
| $T3 \to T5$ | $S^{**} \times 1.5$ (anyNuke only) | No observed case; structural theoretical path |

The $T2 \to T4$ multiplier is highest because this skip type requires the combination of severe economic siege ($S_2$ near ceiling), a closing operational window, and absent diplomatic exit — precisely the conditions encoded in $S^{**}$ at maximum values.

### 7.4 Calibration Anchors

| Dyad | FMA | $-\dot{W}$ | ORA | $S^{**}$ (at unit exponents) | Note |
|---|---:|---:|---:|---:|---|
| Japan→USA, Nov 1941 | 0.90 | 0.85 | 0.90 | 0.689 | Pearl Harbor case; maximum skip signature |
| Iraq→Kuwait, Aug 1990 | 0.80 | 0.10 | 0.70 | 0.056 | Strong FMA; window minor; off-ramps limited |
| Falklands 1982 | 0.60 | 0.20 | 0.55 | 0.066 | Moderate FMA; some window; off-ramps collapsing |
| Russia→Ukraine, 2022 | 0.40 | 0.30 | 0.70 | 0.084 | Moderate initiative; modest window; Minsk dead |
| India→Pakistan, Kargil 1999 | 0.30 | 0.10 | 0.40 | 0.012 | Limited FMA; no real window; back-channels open |
| USA→China, 2026 (T2) | 0.10 | 0.20 | 0.30 | 0.006 | Low skip preconditions; channels functioning |

$\mathcal{N}$ is absorbed into the deterrence term $(1 - \mathcal{N}^{\eta_n})$; for non-nuclear dyads $\mathcal{N} = 0$ and this term equals 1 (no deterrent suppression of skip). For Kargil 1999 with $\mathcal{N} \approx 0.60$: the term becomes $(1 - 0.6) = 0.4$, further suppressing skip.

---

## 10. Unified Equation Summary (Updated)

The master equation and movement probabilities are unchanged from v19.4 §10. The updated components:

$$\boxed{
\pi_{kj}(t) =
\begin{cases}
P_{\downarrow}(T_k)\cdot\omega_{kj}^{-} & j < k \\[4pt]
P_{0}(T_k) & j = k \\[4pt]
P_{\uparrow}(T_k)\cdot\omega_{kj}^{+} & j > k
\end{cases}
}$$

$$P_{\downarrow} = \frac{\exp(U_k^\downarrow)}{Z}, \quad P_0 = \frac{\exp(U_k^0)}{Z}, \quad P_{\uparrow} = \frac{\exp(U_k^\uparrow)}{Z}, \quad Z = \exp(U_k^\downarrow)+\exp(U_k^0)+\exp(U_k^\uparrow)$$

$$U_k^{\downarrow} = \alpha_k^{\downarrow} + \beta_{dS} S_k + \beta_M M_{AB}^{\text{med}} + \beta_C C_{AB}^{\text{conc}} + \beta_X X_{AB}^{\text{collapse}} - \lambda_k^{\downarrow} D_k - \beta_{\text{ORA}} \cdot \text{ORA}_{AB}$$

$$U_k^{0} = \alpha_k^{0} + \rho_k D_k + \beta_F F_{AB} - \beta_M^{0} M_{AB}^{\text{med}}$$

$$U_k^{\uparrow} = \alpha_k^{\uparrow} + \beta_{uS} S_k + \beta_s S^{**}_{AB} + \sigma_k h_{AB} + \nu_k^{\text{nuke}} + \beta_{\text{haz}} \cdot h_k^{\uparrow}$$

$$\nu_k^{\text{nuke}} = \mathbf{1}[\text{anyNuke}]\cdot\Bigl[\beta_{\Theta}\Theta_{AB}\cdot\mathbf{1}[k\ge 4] + \beta_N(1-\mathcal{N}_{AB})\cdot\mathbf{1}[k=4] + \beta_{\text{mono}}\cdot\text{Monopoly}_{AB}\cdot\mathbf{1}[k=5]\Bigr]$$

$$h_k^{\uparrow} = 1-(1-p_k^A)(1-p_k^B), \quad p_4^i = \text{HasNuke}_i \cdot \sigma\!\left(\alpha_{45} + \beta_{\Theta}\Theta_{AB} + \beta_N(1-\mathcal{N}_{AB}) + \cdots\right)$$

$$S^{**}_{AB} = \left(\Phi^{FMA}_{AB}\right)^{\eta_\phi} \cdot \left(-\dot{W}_{AB}\right)^{\eta_w} \cdot \text{ORA}_{AB}^{\eta_r} \cdot \left(1 - \mathcal{N}_{AB}^{\eta_n}\right)$$

$$h_{AB} = \beta_h \cdot \Psi_{AB} \cdot D_A, \quad \sigma_k = k/5$$

$$\mathcal{L}_{\text{base}} = \beta_0 + \beta_m\widetilde{M}^*_{AB} + \beta_r\mathcal{R}_{AB} + \beta_a(2A_{AB}-1)C_{AB}\cdot\mathbf{1}[\Phi^{opp}>\tau_{opp}] + \beta_c\Phi^{coop}_{AB}$$

$$\widetilde{M}^*_{AB} = \widetilde{M}_{AB}(1+\varphi_\xi\Xi_{AB}), \quad \widetilde{M}_{AB} = \Phi^{opp}_{AB}\exp\!\left(-\gamma_1\Phi^{sup}_{AB} - \gamma_2\Phi^{coop}_{AB}\right)$$

$$\text{Monopoly}_{AB} = \mathbf{1}\!\left[\text{HasNuke}_A + \text{HasNuke}_B = 1\right]$$

**Boundary constraints:** $P_\downarrow(T_0) = 0$; $P_\uparrow(T_5) = 0$; $\omega_{k5}^+ = 0$ when anyNuke $=$ false.

---

## 12. Parameters

### Carried Forward From v19.4

All parameters in v19.4 §12 are retained. The following are updated or newly exposed:

### New in v19.5

| Parameter | Role | Default | Notes |
|---|---|---|---|
| $\Phi^{FMA}_{AB}$ | First-mover / operational surprise advantage | 0.10 | Per-dyad input; see §7.2 coding rules |
| $-\dot{W}_{AB}$ | Military balance deterioration rate — closing window | 0.00 | Per-dyad input; 0 = no closing window |
| $\text{ORA}_{AB}$ | Off-ramp absence — diplomatic/institutional exit unavailability | 0.30 | Per-dyad input; also enters $U_k^\downarrow$ |
| $\eta_\phi$ | FMA exponent in $S^{**}$ | 1.0 | HalfNormal(0,1); $>1$ makes FMA a prerequisite rather than a factor |
| $\eta_w$ | WindowClose exponent in $S^{**}$ | 1.0 | HalfNormal(0,1) |
| $\eta_r$ | ORA exponent in $S^{**}$ | 1.0 | HalfNormal(0,1) |
| $\eta_n$ | $\mathcal{N}_{AB}$ exponent in $S^{**}$ | 1.0 | HalfNormal(0,1) |
| $\beta_{\text{ORA}}$ | ORA suppression weight in $U_k^\downarrow$ | 0.80 | HalfNormal(0,1); controls how strongly blocked exits reduce de-escalation probability |

### Removed in v19.5

| Removed | Replaced by |
|---|---|
| K23 (skip scalar into T3) | $S^{**}_{AB}$ computed from components |
| K34 (skip scalar into T4) | $S^{**}_{AB}$ computed from components |
| Skip13 (T1→T3 diagnostic) | $S^{**} \times 2.0$ in destination allocation |
| Skip14 (T1→T4 diagnostic) | $S^{**} \times 1.5$ in destination allocation |
| Skip24 (T2→T4 diagnostic) | $S^{**} \times 2.5$ in destination allocation |
| Skip35 (T3→T5 diagnostic) | $S^{**} \times 1.5$ in destination allocation (anyNuke only) |

---

## 13. Validation Priorities (Updated)

Priorities from v19.4 §13 are retained. The following are added:

12. **S\*\* zero-component check:** confirm that $S^{**} = 0$ when any single component is zero (any of FMA, WindowClose, ORA equals 0, or $\mathcal{N} = 1$). No skip should be structurally possible if the operational window is not closing.

13. **ORA double-channel check:** verify that high ORA simultaneously suppresses $P_\downarrow$ (via $U_k^\downarrow$ term) and raises $P_\uparrow$ (via $S^{**}$ in $U_k^\uparrow$). The gap $P_\uparrow - P_\downarrow$ should widen monotonically as ORA increases, holding all else constant.

14. **Japan 1941 calibration:** at FMA=0.90, WindowClose=0.85, ORA=0.90, $\mathcal{N}=0$, $S_2=0.90$, $E=0.90$, CurrentTier=T2: the model should produce $P_\uparrow \gg P_\downarrow$ and the T2→T4 destination weight should dominate the upward allocation. This is the clearest skip signature in the calibration dataset.

15. **Kargil 1999 nuclear ceiling check:** at moderate FMA (0.30), low WindowClose (0.10), moderate ORA (0.40), and $\mathcal{N}=0.60$: $S^{**} \approx 0.012$, which should produce negligible skip bonus. Escalation probability from T3 should remain low and the destination allocation should not favor T5.

16. **Component exponent sensitivity:** run $S^{**}$ at $\eta_\phi = \eta_w = \eta_r = \eta_n \in \{0.5, 1.0, 2.0\}$. At $\eta > 1$, each component becomes a near-prerequisite (the product falls faster when any component is below 1). This controls whether $S^{**}$ behaves additively (low $\eta$) or as a conjunction of conditions (high $\eta$).

---

## 14. Practical Interpretation

In v19.5, the skip barrier coding workflow is:

1. **Code HasNuke** and CurrentTier as before.
2. **Code $\Phi^{FMA}$:** does the initiator have genuine first-mover or operational surprise capability against this target right now?
3. **Code $-\dot{W}$:** is the initiator's military position deteriorating relative to the target? How fast?
4. **Code ORA:** are diplomatic, institutional, or third-party exit mechanisms available and functioning? ORA = 1 - (fraction of exit channels that remain open and credible).
5. **$S^{**}$ computes automatically.** It feeds both $U_k^\uparrow$ (via $\beta_s S^{**}$) and the tier-specific destination allocation skip bonuses.
6. **ORA also suppresses $U_k^\downarrow$** via $-\beta_{\text{ORA}} \cdot \text{ORA}$. This does not require separate coding — ORA is coded once and enters both channels.

The three components are independently coded. A dyad can have high FMA and high ORA but no closing window (low WindowClose) — producing near-zero skip probability despite operational capability and blocked exits. All three conditions must co-occur for the Pearl Harbor skip pattern to emerge.

---

*v19.5 supersedes v19.4. The unified equation §10 is updated for $U_k^\downarrow$ and $S^{**}$. All other equations and architectural decisions from v19.4 are unchanged and carry forward without modification.*