# Unified Equation of Interstate War (Dyadic Variant) v19.6 — Specification

## Structured Specification

---

## 1. What v19.6 Changes From v19.5

v19.6 introduces a nested, highly restrictive **Nuclear Threshold Barrier ($\Omega_{AB}$)** that acts as a structural gatekeeper specifically for the $T3 \to T5$ (Conventional Engagement to Strategic Nuclear Exchange) destination allocation skip pathway. This mathematically isolates nuclear deployment posture, command vulnerability, and strategic doctrine from standard conventional window math, resolving the unconstrained $T3 \to T5$ skip risk identified in v19.5. All other architecture is carried forward.

| Change | v19.5 | v19.6 |
| --- | --- | --- |
| $T3 \to T5$ Skip Allocation | $S^{**} \times 1.5$ (conditional only on `anyNuke`) | $S^{**} \times 1.5 \times \Omega_{AB}$ |
| Nuclear Skip Filter | Binary indicator `anyNuke` | Tripartite product: $\Omega_{AB} = \mathbf{1}[\text{anyNuke}] \cdot \left( \Pi_{AB}^{\text{vuln}} \cdot \Lambda_{AB}^{\text{alert}} \cdot \Delta_{AB}^{\text{doct}} \right)$ |
| New Global Inputs / Weights | — | $\Pi_{AB}^{\text{vuln}}$, $\Lambda_{AB}^{\text{alert}}$, $\Delta_{AB}^{\text{doct}}$ |
| Validation Priorities | 16 Priorities | 17 Priorities (Added Nuclear Gatekeeper Validation) |

### Motivation

In v19.5, an acute conventional crisis with zero diplomatic outlets (high ORA, high $-\dot{W}$) could mathematically trigger a direct skip from $T3$ to $T5$ if the dyad possessed nuclear weapons. In reality, a sudden nuclear jump is constrained by factors independent of geopolitical urgency: whether warheads are physically mated to missiles, whether command networks are vulnerable to decapitation, and whether operational doctrine permits first use. Version 19.6 ensures that if a state's nuclear arsenal is physically disassembled ($\Lambda^{\text{alert}} = 0$) or structurally invulnerable ($\Pi^{\text{vuln}} \approx 0$), the $T3 \to T5$ skip probability collapses to zero, forcing escalation to move incrementally through $T4$ (Strategic Conventional War) first.

---

## 2–6. Unchanged From v19.5

The six-tier taxonomy (§2), exogenous current-state architecture (§3.1–3.4), aggregate transition outputs (§3.4), movement probabilities via softmax (§3.6), bilateral escalation hazard (§4), external public opinion field (§5), within-tier severity (§6), and de-escalation/persistence exits (§10) are unchanged.

---

## 3.5 Movement-Category Scores (Unchanged from v19.5)

$$\begin{aligned}
U_k^{\downarrow} &= \alpha_k^{\downarrow} + \beta_{dS} S_k + \beta_M M_{AB}^{\text{med}} + \beta_C C_{AB}^{\text{conc}} + \beta_X X_{AB}^{\text{collapse}} - \lambda_k^{\downarrow} D_k - \beta_{\text{ORA}} \cdot \text{ORA}_{AB} \\[6pt]
U_k^{0} &= \alpha_k^{0} + \rho_k D_k + \beta_F F_{AB} - \beta_M^{0} M_{AB}^{\text{med}} \\[6pt]
U_k^{\uparrow} &= \alpha_k^{\uparrow} + \beta_{uS} S_k + \beta_s S^{**}_{AB} + \sigma_k h_{AB} + \nu_k^{\text{nuke}} + \beta_{\text{haz}} \cdot h_k^{\uparrow}
\end{aligned}$$

The master transition scores maintain their structural configuration. The updated filtering behavior for nuclear dyads is handled down-stream during the destination allocation phase.

---

## 7. Skip Barrier $S^{}$ & Destination Allocation (Updated)

### 7.1 Structural Components (Unchanged)

$$S^{**}_{AB} = \left(\Phi^{FMA}_{AB}\right)^{\eta_\phi} \cdot \left(-\dot{W}_{AB}\right)^{\eta_w} \cdot \left(\text{ORA}_{AB}\right)^{\eta_r} \cdot \left(1 - \mathcal{N}_{AB}^{\eta_n}\right)$$

### 7.3 Destination Allocation Skip Bonuses (Updated)

Conditional on upward movement ($U_k^{\uparrow}$), $S^{}$ weights the second-stage allocation $\omega_{kj}^+$ toward destination tiers that require skip.

| Skip Type | Multiplier Formula | Structural Operational Focus |
| --- | --- | --- |
| $T1 \to T3$ | $S^{**} \times 2.0$ | Bypassing coercion directly into conventional skirmish |
| $T1 \to T4$ | $S^{**} \times 1.5$ | Strategic surprise invasion (e.g., Iraq $\to$ Kuwait 1990) |
| $T2 \to T4$ | $S^{**} \times 2.5$ | Severe coercion + closing window $\to$ direct strategic war (Japan 1941) |
| $T3 \to T5$ | $S^{**} \times 1.5 \times \Omega_{AB}$ | **Nuclear Threshold Gated (New):** Direct jump to nuclear exchange |

---

## 8. Nuclear Threshold Barrier $\Omega_{AB}$ (New Section)

To systematically isolate nuclear risks from conventional operational planning, the $T3 \to T5$ destination path is filtered through $\Omega_{AB} \in [0, 1]$.

$$\Omega_{AB} = \mathbf{1}[\text{anyNuke}] \cdot \left[ \Pi_{AB}^{\text{vuln}} \cdot \Lambda_{AB}^{\text{alert}} \cdot \Delta_{AB}^{\text{doct}} \right]$$

### 8.1 Component Coding Rules

**$\Pi_{AB}^{\text{vuln}}$ — Arsenal & Command Vulnerability ("Use It or Lose It" Pressure):**

* **0.01 (Low Risk):** Fully invulnerable second-strike capability (deeply submerged SSBNs, highly mobile road-launchers, hardened redundant $C^3$).
* **0.30 (Moderate Risk):** Asymmetric vulnerability; some reliance on liquid-fueled, stationary silos vulnerable to precision conventional attack.
* **0.80 (High Risk):** Small, concentrated arsenal with co-located conventional/nuclear command nodes; extreme vulnerability to a conventional decapitation strike.

**$\Lambda_{AB}^{\text{alert}}$ — Technical Deployment Posture (Physical Latency):**

* **0.00 (Immune):** De-mated/disassembled architecture. Warheads are stored in central depots away from delivery vehicles under separate civilian custody. An instantaneous skip is physically impossible.
* **0.40 (Buffered):** Weapons assembled but kept at low daily readiness; requires hours of transit or fueling sequences, creating visible operational buffers.
* **0.90 (Hair-Trigger):** Launch-on-Warning (LOW) configuration. Solid-fueled missiles are mated to warheads in active silos/SSBNs with pre-delegated launch authority.

**$\Delta_{AB}^{\text{doct}}$ — Doctrinal Credibility (Asymmetric Thresholds):**

* **0.05 (Restrained):** Credible, institutionalized No-First-Use (NFU) policy.
* **0.50 (Conditional):** Calculated ambiguity; nuclear use reserved exclusively for existential state survival threats.
* **0.95 (Asymmetric Escalation):** Explicit "Escalate to De-escalate" doctrine theater integration. Nuclear options are treated as a direct counter-weight to conventional battlefield failure.

---

## 9. Nuclear Shadow and T5 Structure (Updated for $\Omega_{AB}$ Integration)

The baseline nuclear parameters influencing the master scores remain unchanged, but the calibration behavior honors the new structural filters.

### 9.4 Calibration Anchors for $\Omega_{AB}$

| Historical/Hypothetical Dyad | $\Pi^{\text{vuln}}$ | $\Lambda^{\text{alert}}$ | $\Delta^{\text{doct}}$ | Resulting $\Omega_{AB}$ | Structural Interpretation |
| --- | --- | --- | --- | --- | --- |
| **Japan $\to$ USA, Nov 1941** | 0.00 | 0.00 | 0.00 | **0.000** | Non-nuclear dyad; $\mathbf{1}[\text{anyNuke}] = 0$. $\omega_{35}^+$ path entirely closed. |
| **India $\leftrightarrow$ Pakistan, 1999** | 0.60 | 0.05 | 0.80 | **0.024** | High doctrinal threat, but warheads were physically un-mated. Skip path highly suppressed. |
| **USA $\leftrightarrow$ USSR, Oct 1962** | 0.40 | 0.70 | 0.50 | **0.140** | Volatile silos combined with high strategic readiness cracked the gate open to tail risk. |
| **Existential Siege (Hypothetical)** | 0.80 | 0.90 | 0.95 | **0.684** | Vulnerable arsenal under hair-trigger alert facing conventional destruction. Maximum skip signature. |

---

## 10. Master Unified Equation Summary (v19.6 Updated)

$$\boxed{
\pi_{kj}(t) =
\begin{cases}
P_{\downarrow}(T_k)\cdot\omega_{kj}^{-} & j < k \[4pt]
P_{0}(T_k) & j = k \[4pt]
P_{\uparrow}(T_k)\cdot\omega_{kj}^{+} & j > k
\end{cases}
}$$

$$P_{\downarrow} = \frac{\exp(U_k^\downarrow)}{Z}, \quad P_0 = \frac{\exp(U_k^0)}{Z}, \quad P_{\uparrow} = \frac{\exp(U_k^\uparrow)}{Z}, \quad Z = \exp(U_k^\downarrow)+\exp(U_k^0)+\exp(U_k^\uparrow)$$

$$U_k^{\downarrow} = \alpha_k^{\downarrow} + \beta_{dS} S_k + \beta_M M_{AB}^{\text{med}} + \beta_C C_{AB}^{\text{conc}} + \beta_X X_{AB}^{\text{collapse}} - \lambda_k^{\downarrow} D_k - \beta_{\text{ORA}} \cdot \text{ORA}_{AB}$$

$$U_k^{0} = \alpha_k^{0} + \rho_k D_k + \beta_F F_{AB} - \beta_M^{0} M_{AB}^{\text{med}}$$

$$U_k^{\uparrow} = \alpha_k^{\uparrow} + \beta_{uS} S_k + \beta_s S^{**}_{AB} + \sigma_k h_{AB} + \nu_k^{\text{nuke}} + \beta_{\text{haz}} \cdot h_k^{\uparrow}$$

$$S^{**}_{AB} = \left(\Phi^{FMA}_{AB}\right)^{\eta_\phi} \cdot \left(-\dot{W}_{AB}\right)^{\eta_w} \cdot \text{ORA}_{AB}^{\eta_r} \cdot \left(1 - \mathcal{N}_{AB}^{\eta_n}\right)$$

$$\Omega_{AB} = \mathbf{1}[\text{anyNuke}] \cdot \left[ \Pi_{AB}^{\text{vuln}} \cdot \Lambda_{AB}^{\text{alert}} \cdot \Delta_{AB}^{\text{doct}} \right]$$

---

## 13. Validation Priorities (Updated)

Priorities 1–11 (carried forward from v19.4) and 12–16 (carried forward from v19.5) remain active. The following validation priority is formally appended:

17. **Nuclear Gatekeeper Zero-Check ($\Omega_{AB}$ Boundary):** Confirm that if a nuclear dyad is coded with a disassembled posture ($\Lambda^{\text{alert}} = 0$), the value of $\Omega_{AB}$ drops immediately to 0. Run a simulation sweep across maximum conventional escalatory distress ($S^{} \to 1.0$, CurrentTier = $T3$). The destination matrix must show $\omega_{35}^+ = 0$, completely blocking a direct jump to $T5$ and routing any upward movement strictly through $T4$.

---

## 14. Practical Interpretation

In v19.6, the skip barrier workflow is completely systematized:

1. **Code conventional triggers** ($\Phi^{FMA}$, $-\dot{W}$, $\text{ORA}$) to compute the base skip barrier $S^{}$.
2. If `anyNuke` is true, **code the technical/doctrinal constraints** ($\Pi^{\text{vuln}}$, $\Lambda^{\text{alert}}$, $\Delta^{\text{doct}}$) once per dyad.
3. The system automatically balances the channels: conventional operational pressures dictate the *overall willingness to skip steps* ($S^{}$), while technical/organizational barriers dictate whether that skip can *cross the nuclear threshold* ($\Omega_{AB}$).

---

*v19.6 supersedes all previous versions. The destination allocation matrix is structurally bound by the Nuclear Threshold Gatekeeper. All baseline statistical limits and distributions carry forward intact.*

---

### 💡 Implementation Note for Your Codebase

Since you are updating this in your modeling code, remember that adding the $\Omega_{AB}$ matrix means your initialization data frames will need three new columns (`nuclear_vuln`, `nuclear_alert`, `nuclear_doct`). For non-nuclear dyads, you can safely initialize these to `0.00` since the `anyNuke` boolean flag will zero out the gatekeeper expression anyway.