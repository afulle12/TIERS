# Unified Equation of Interstate War (Dyadic Variant) v21.3

## Complete Specification with Full Context & Definitions

**Version:** 21.3 (Bidirectional Contagion & Economic Opportunity Cost Update)  
**Status:** Production-Ready  
**Last Updated:** May 2026

---

## PART 0: VERSION 21.3 CHANGES FROM 20.1 & 21.0

v21.3 addresses the parameter bloat, multicollinearity, and subjective coding bias vulnerabilities identified in v21.0. Based on modern quantitative conflict forecasting principles, unobservable psychological variables have been eliminated in favor of structural, operational, and economic realities. Crucially, it introduces Bidirectional Contagion to capture both the infectious spread of war and the pacifying gravity of regional peace.

| Element | Legacy v21.0 | v21.3 (Streamlined & Bidirectional) |
|---------|-------|-------|
| **Tier Assignment** | Operational evidence only | **UNCHANGED** |
| **Tier Taxonomy** | T0–T6 with operational T3/T4 split | **UNCHANGED** |
| **Total Parameters** | ~48 heavily overlapping variables | **13 Parsimonious Core Parameters** |
| **New Economic Metric** | Missing / Subjective | **$C_{peace}$ (Cost of Peace) integrated** |
| **Contagion / Spillover** | Implicit or Missing | **$V_{contagion}$ added as Bidirectional [-1, +1]** |
| **Subjective Variables** | $pConcede, A_r, P_c, \Psi_{pub}$ | **Removed to eliminate analyst coding bias** |
| **Overlapping Signals** | $B_q, M_{lev}, C_v, F_s, Talk_t$ | **Merged into single $Dip_{cap}$ index** |
| **Composite Indices** | Bloated with subjective clips | **Parsimonious linear equations** |
| **Formatting** | Render issues in legacy spec | **Restored exact house style and all legacy sections** |

**Why this matters:** Analysts cannot read the minds of foreign leaders. Variables like "Aim Reversibility" or "Willingness to Concede" introduced massive coding bias. v21.3 focuses strictly on *structural capacity*. By introducing the **Cost of Peace** ($C_{peace}$), the model captures when the economic friction of the status quo becomes worse than war. By introducing **Regional Contagion** ($V_{contagion}$), the model mathematically accounts for the epidemiological spread of both conflict (spillover violence) and peace (economic integration).

---

## PART 1: OVERVIEW & ARCHITECTURE

### 1.1 What This Model Does

The Unified Equation of Interstate War (UIW) v21.3 is a **dyadic probability model** for estimating next-period interstate conflict escalation, persistence, and de-escalation probabilities. It estimates:

$$\pi_{kj}(t) = \text{Pr}(\text{next tier} = j \,|\, \text{current tier} = k, \text{all inputs at time } t)$$

Where:
- **k** = current conflict tier (T0–T6), coded from operational evidence
- **j** = next-period tier (T0–T6)
- **π_kj** = probability distribution [π₀, π₁, π₂, π₃, π₄, π₅, π₆] summing to 1

**Output interpretation:**
- π₀ = probability of peace or de-escalation to T0
- π_k = probability of persistence at current tier
- π_{k+1}, ..., π₆ = probabilities of escalation to higher tiers
- π_j for j < k = probabilities of downward movement from the current tier

**Recommended forecast interval:** 30 days. The model can be adapted to weekly or quarterly windows, but all calibration and coding anchors must use one interval consistently.

---

### 1.2 Seven-Tier Escalation Taxonomy (PRESERVED FROM 20.1)

| **Tier** | **Name** | **Military Activity** | **Operational Definition** | **Examples** |
|----------|----------|----------------------|----------------------------|--------------|
| **T0** | Peace | None | No military activity or threat thereof | US–Canada 2020; most dyads |
| **T1** | Diplomatic Crisis | None | Formal friction: protests, ambassador recalls, ultimatums, public threats, UN votes | US–Iran 2019 |
| **T2** | Economic Coercion | None | Active economic instruments: sanctions, trade restrictions, financial exclusion | Russia–Ukraine 2014 |
| **T3** | Proxy/Indirect Military | Passive support only | Weapons, intelligence, training, funding to B's enemies; A's forces NOT directly in combat | Iran funding Hezbollah |
| **T4** | Limited Direct Military | Direct combat | Any direct exchange of fire between A and B forces, regardless of scope | USS *Reuben James* 1941 |
| **T5** | Strategic War | Expansive conventional | Nationwide or multi-front warfare, ambitious objectives, sustained campaigns | Ukraine–Russia 2022+ |
| **T6** | Nuclear Exchange | Nuclear weapons used | Nuclear weapons detonated in anger | Japan 1945 |

---

### 1.3 Tier Assignment Rule (Foundational)

**Assign the HIGHEST tier fully supported by operational evidence:**

1. **T6 threshold:** Nuclear detonation in anger has occurred
2. **T5 threshold:** Direct war is expansive in scope, geography, and mobilization
3. **T4 threshold:** A's military forces directly exchange fire with B's forces
4. **T3 threshold:** A provides passive military support to B's enemies, but A's forces are not directly fighting B
5. **T2 threshold:** Active economic coercion is in force and materially relevant
6. **T1 threshold:** Formal diplomatic friction is occurring
7. **T0 threshold:** None of the above

**Critical:** Do NOT mix diplomatic language with operational coding. If direct combat is active, the dyad is at least T4 even if leaders deny being at war.

---

### 1.4 Model Architecture Summary

```
INPUT CODING (THE CORE 13 PARAMETERS)
├─ Path Dependency Variables
│  └─ Current Tier (X_t), Duration (D_k)
├─ Structural & Military Variables
│  └─ Rivalry (Ω), Contiguity (Ξ), First-Mover Adv (FMA), Closing Window (-Ẇ)
├─ Economic Drivers
│  └─ Cost of Peace (C_peace), Exhaustion (W_x)
├─ Operational & Diplomatic Variables
│  └─ Off-Ramp Absence (ORA), Stalemate (Stal_t), Diplomatic Capacity (Dip_cap)
└─ Catalysts & Geopolitical Environment
   └─ Kinetic Shock (Shock_k), Nuclear Gate (Nuc), Bidirectional Contagion (V_contagion)

PROCESSING PIPELINE
├─ Escalation Pressure Index (E_t)
├─ De-Escalation Capacity Index (D_t)
├─ Persistence Lock Index (S_t)
├─ Movement Probability Computation (U↓, U0, U↑ → softmax)
├─ Skip Barrier Calculation (S**)
├─ Downward Destination Allocation (ω⁻)
└─ Upward Destination Allocation (ω⁺)

OUTPUT
└─ Next-state distribution π = [π₀, π₁, π₂, π₃, π₄, π₅, π₆]
```

---

## PART 2: INPUT VARIABLES & CODING GUIDANCE (THE CORE 13)

Variables are strictly bounded, mostly **[0, 1]**, except for bidirectional variables.

### 2.1 Path Dependency Variables

#### **CurrentTier ($X_t$)**
- **Definition:** The operational reality on the ground right now. The anchor for all path dependency.
- **Range:** {0, 1, 2, 3, 4, 5, 6}

#### **Duration ($D_k$)**
- **Definition:** Time spent at the current tier. Calculates duration dependence (longer conflicts are harder to break out of).
- **Range:** [0, $\infty$) (Calculated as months / 10).

### 2.2 Structural & Military Drivers

#### **Rivalry ($\Omega$)**
- **Definition:** Long-term structural incompatibility and enmity. Absorbs legacy variables for alliance depth and historical sparks.
- **Range:** [0, 1]
- **Anchors:** 0.0 = Allies; 0.5 = Competitors; 1.0 = Existential enmity.

#### **Contiguity ($\Xi$)**
- **Definition:** Shared borders and the presence of territorial disputes. The primary geographic driver.
- **Values:** {0, 0.5, 1}
- **Anchors:** 0 = No shared border; 0.5 = Shared border, no dispute; 1.0 = Active territorial dispute on shared border.

#### **First-Mover Advantage ($FMA$) [DIRECTIONAL]**
- **Definition:** Tactical window where striking first offers a decisive operational advantage. 
- **Range:** [0, 1]

#### **Closing Window ($-\dot{W}$) [DIRECTIONAL]**
- **Definition:** Long-term negative shift in the balance of power creating "now-or-never" pressure to strike before weakness sets in.
- **Range:** [0, 1]

### 2.3 Economic Drivers

#### **Cost of Peace ($C_{peace}$)**
- **Definition:** The economic and internal security burden of maintaining the status quo relative to war. Replaces subjective "willingness to concede" metrics.
- **Range:** [0, 1]
- **Anchors:**
  - **0.0–0.2:** Peace is highly profitable (frictionless trade, positive GDP multiplier).
  - **0.4–0.6:** Peace is costly but manageable (moderate sanctions, elevated border security).
  - **0.8–1.0:** Peace is ruinous (devastating blockades, economic collapse due to status quo). Makes war economically rational.

#### **Exhaustion ($W_x$)**
- **Definition:** Material, demographic, and fiscal depletion caused by the current conflict tier. High exhaustion forces de-escalation regardless of political intent.
- **Range:** [0, 1]

### 2.4 Operational & Diplomatic Constraints

#### **Off-Ramp Absence ($ORA$)**
- **Definition:** Structural lack of politically or physically viable exits. High $ORA$ ensures persistence even if exhaustion is high. Absorbs reputational lock-in.
- **Range:** [0, 1]

#### **Stalemate ($Stal_t$)**
- **Definition:** The physical inability for either side to achieve a kinetic breakthrough. Anchors the conflict in persistence.
- **Range:** [0, 1]

#### **Diplomatic Capacity ($Dip_{cap}$)**
- **Definition:** A unified index of mediator leverage, verifiable communication channels, and active de-escalation signaling. 
- **Range:** [0, 1]

### 2.5 Catalysts & Geopolitical Environment

#### **Kinetic Shock ($Shock_k$)**
- **Definition:** Recent sudden spikes in fatalities, strikes, or mobilizations that act as an immediate escalation catalyst. Absorbs legacy variables like Fatal_t and Strike_t.
- **Range:** [0, 1]

#### **Nuclear Gate ($Nuc$)**
- **Definition:** Binary weapon possession and arsenal instability. (If neither side possesses nuclear weapons, $Nuc = 0$). Computed from $\Pi_{vuln}$, $\Lambda_{alert}$, and $\Delta_{doct}$ (Arsenal vulnerability, alert posture, and doctrine threshold).
- **Range:** [0, 1]

#### **$V_{contagion}$ — Bidirectional Regional Contagion (NEW)**
- **Definition:** The spillover effect of the surrounding geopolitical environment. Measures whether neighboring states are exporting instability and violence, or exporting economic integration and successful diplomatic resolution.
- **Range:** **[-1, +1]**
- **Coding Anchors:**
  - **-1.0 to -0.7 (Strong Peace Contagion):** Region is rapidly integrating economically; highly successful peaceful resolutions nearby create strong demonstration effects.
  - **-0.6 to -0.2 (Moderate Peace Contagion):** Stable neighbors actively investing in regional architecture and trade.
  - **-0.1 to +0.1 (Neutral):** Dyad is geographically isolated from regional trends, or trends are mixed.
  - **+0.2 to +0.6 (Moderate Conflict Contagion):** Active conflict nearby causing border friction or refugee flows.
  - **+0.7 to +1.0 (Strong Conflict Contagion):** Multiple borders at war, regional state collapse, massive weapon proliferation.

---

## PART 3: MATHEMATICAL SPECIFICATION

### 3.1 Composite Indices (Parsimonious Linear Formulation)

**Escalation Pressure Index ($E_t$):**
Driven by structural rivalry, territorial disputes, military advantages, an expensive peace, and conflict contagion. (A negative $V_{contagion}$ *reduces* escalation pressure).
$$E_t = \text{clip}\left( \alpha_1\Omega + \alpha_2\Xi + \alpha_3FMA + \alpha_4(-\dot{W}) + \alpha_5C_{peace} + \alpha_6V_{contagion}, 0, 1 \right)$$

**De-Escalation Capacity Index ($D_t$):**
Driven by material exhaustion, diplomatic channels, the profitability of peace, and peace contagion. (Subtracting a negative $V_{contagion}$ *adds* to de-escalation capacity).
$$D_t = \text{clip}\left( \theta_1W_x + \theta_2Dip_{cap} + \theta_3(1 - C_{peace}) - \theta_4V_{contagion}, 0, 1 \right)$$

**Persistence Lock Index ($S_t$):**
Driven by physical stalemates, duration, lack of exits, and conflict contagion. (Regional peace breaks stalemates; regional war entrenches them).
$$S_t = \text{clip}\left( \rho_1Stal_t + \rho_2ORA + \rho_3D_k + \rho_4V_{contagion}, 0, 1 \right)$$

### 3.2 Movement Scores (Simplified)

The scores representing pressure to de-escalate ($U^\downarrow$), persist ($U^0$), or escalate ($U^\uparrow$).

**Downward Pressure:**
$$U_k^{\downarrow} = a_k^{\downarrow} + b_D D_t - b_E E_t - b_{ORA} ORA$$

**Persistence Pressure:**
$$U_k^{0} = a_k^{0} + r_S S_t + r_D D_k$$

**Upward Pressure:**
$$U_k^{\uparrow} = a_k^{\uparrow} + u_E E_t - u_D D_t + u_Z Shock_k + u_{skip}S^{**}$$

### 3.3 Master Unified Equation (Softmax)

The final probabilities for next-period conflict states are calculated via a standard softmax function:

$$Z = \exp(U_k^\downarrow) + \exp(U_k^0) + \exp(U_k^\uparrow)$$

$$P_{\downarrow} = \frac{\exp(U_k^\downarrow)}{Z}, \quad P_0 = \frac{\exp(U_k^0)}{Z}, \quad P_{\uparrow} = \frac{\exp(U_k^\uparrow)}{Z}$$

**Constraints:**
- $P_{\downarrow}(T_0) = 0$
- $P_{\uparrow}(T_6) = 0$
- If $Nuc = 0$, probability of moving to T6 during destination allocation is strictly 0.

### 3.4 Default Operational Coefficients (For Calibration)

| Parameter | Default | Parameter | Default |
|-----------|---------|-----------|---------|
| a↓ | -0.40 | r_S | 1.10 |
| a0 | 0.20 | r_D | 0.03 |
| a↑ | -0.35 | u_E | 1.35 |
| b_D | 1.30 | u_Z | 0.55 |
| b_E | 0.80 | u_D | 0.75 |
| b_ORA | 0.80 | u_skip | 1.00 |

### 3.5 Skip Barrier (S**) 

$$S^{**}_{AB} = \left(\Phi^{\text{FMA}}_{AB}\right)^{\eta_\phi} \cdot \left(-\dot{W}_{AB}\right)^{\eta_w} \cdot \left(\text{ORA}_{AB}\right)^{\eta_r} \cdot \left(1 - Nuc^{\eta_n}\right)$$

*If first-mover advantage is weak, window not closing, or off-ramps are open, skip pressure falls sharply.*

---

## PART 4: DOWNWARD & UPWARD DESTINATION ALLOCATION

### 4.1 Downward Allocation

If the dyad moves downward from tier k, assign:
$$\omega_{kj}^{-}(t) = \Pr(\text{destination}=j \,|\, \text{downward move from } k), \quad j<k$$

With:
$$\sum_{j=0}^{k-1}\omega_{kj}^{-}(t)=1$$

**Default Principle:** Most downward moves should be local, not instant collapse to peace.
**Suggested default weighting rule:**
$$\omega_{kj}^{-} \propto \exp\left[-\lambda_k^{-}(k-j-1)\right] \cdot G_{kj}^{-}$$

### 4.2 Upward Allocation

If the dyad moves upward from tier k, assign:
$$\omega_{kj}^{+}(t) = \Pr(\text{destination}=j \,|\, \text{upward move from } k), \quad j>k$$

With:
$$\sum_{j=k+1}^{6}\omega_{kj}^{+}(t)=1$$

**Suggested default weighting rule:**
$$\omega_{kj}^{+} \propto \exp\left[-\lambda_k^{+}(j-k-1)\right] \cdot G_{kj}^{+}$$

### 4.3 Default Gate Anchors & Boundary Guidance

| Skip Size | Default Gate | Boundary Guidance |
|-----------|--------------|-------------------|
| Adjacent tier | 1.00 | T5 de-escalates first to T4 |
| Two-tier skip | 0.35 | T4 de-escalates first to T3 or T2 |
| Three-tier skip | 0.10 | T3 de-escalates first to T2 or T1 |
| Larger skip | 0.02 | T6 downward movement means reduced active intensity |

---

## PART 5: IMPLEMENTATION & PRACTICAL USE

### 5.1 Step-by-Step Prediction Workflow

**Step 1: Assign Current Tier ($X_t$)**
Use the operational decision tree from Part 1.

**Step 2: Code Structural/Directional Variables**
Code $\Omega$, $\Xi$, $FMA$, and $-\dot{W}$. 

**Step 3: Code Economic Drivers**
Evaluate $C_{peace}$ (GDP drag vs profitability) and $W_x$ (Material exhaustion).

**Step 4: Code Operational Constraints & Shocks**
Score $ORA$, $Stal_t$, $Dip_{cap}$, $Shock_k$, and Bidirectional $V_{contagion}$ [-1, +1].

**Step 5: Compute Indices & Softmax**
Calculate $E_t, D_t, S_t$, run through movement equations $U$, and generate next-tier vector.

### 5.2 Worked Skeleton Example

Suppose a dyad is currently at T4.
Assume normalized index outputs:
- $E_t = 0.68$ (High pressure)
- $D_t = 0.54$ (Moderate capacity)
- $S_t = 0.47$ (Moderate persistence)
- $ORA = 0.70$
- $D_k = 0.40$
- $Shock_k = 0.25$
- $S^{**} = 0.30$

Then:
$$U_4^{\downarrow} = -0.40 + 1.30(0.54) - 0.80(0.68) - 0.80(0.70) = -0.802$$
$$U_4^{0} = 0.20 + 1.10(0.47) + 0.03(0.40) = 0.729$$
$$U_4^{\uparrow} = -0.35 + 1.35(0.68) - 0.75(0.54) + 0.55(0.25) + 1.00(0.30) = 0.600$$

Converting to probabilities (Softmax): The model will heavily weight $P_0$ (Persistence) and $P_\uparrow$ (Escalation) due to the high ORA and Escalation Pressure suppressing downward capacity.

### 5.3 Dashboard Outputs & Interpretation

Each forecast should report $E_t$, $D_t$, $S_t$, and the full $\pi$ distribution.

**Good Report:**
> "UIW v21.3 estimates elevated escalation pressure due to high structural rivalry and an expensive status quo ($C_{peace}$). However, strong regional peace contagion (negative $V_{contagion}$) is generating gravity toward de-escalation capacity. The dyad is currently stalemated, with the primary barrier to de-escalation being the absence of political off-ramps ($ORA$)."

---

## PART 6: VALIDATION & LIMITATIONS

### 6.1 Model Strengths
✓ Captures escalation pressure structurally without relying on mind-reading.
✓ Evaluates the *Cost of Peace*, solving the gap where status-quo bias ignored ruinous non-war states.
✓ Directly measures Geopolitical Contagion (both spillover violence and contagious peace).
✓ Highly parsimonious (13 parameters down from 48).

### 6.2 Model Limitations
❌ Rare-event tails (T6) remain hard to calibrate.
❌ Bidirectional contagion requires sophisticated regional network analysis to score properly.
❌ Multi-actor wars still exceed a purely dyadic simplification.

### 6.3 Proper Use
✓ Early warning, Scenario comparison, Sensitivity analysis.
✗ Deterministic forecasting or claims of exact point certainty.

---

## PART 7: QUICK CODING CHECKLIST

- [ ] Assign $X_t$ using operational evidence only (no diplomatic rhetoric).
- [ ] Keep $\Xi$ discrete: {0, 0.5, 1.0}.
- [ ] Score $C_{peace}$ economically (Sanctions, blockades, FDI).
- [ ] Score $V_{contagion}$ bidirectionally [-1, 1]. Positive for regional war; negative for regional peace.
- [ ] If neither actor has nuclear weapons, force $Nuc = 0$ and block T6.
- [ ] Use one fixed forecast interval consistently (e.g., 30 days).

---

## PART 8: APPENDIX — COMPLETE VARIABLE SUMMARY TABLE

| Variable | Name | Type | Range |
|----------|------|------|-------|
| $X_t$ | Current Tier | State | {0,1,2,3,4,5,6} |
| $D_k$ | Duration | State | [0, $\infty$) |
| $\Omega$ | Rivalry | Structural | [0, 1] |
| $\Xi$ | Contiguity | Structural | {0, 0.5, 1} |
| $FMA$ | First-Mover Adv. | Military | [0, 1] |
| $-\dot{W}$ | Closing Window | Military | [0, 1] |
| $C_{peace}$ | Cost of Peace | Economic | [0, 1] |
| $W_x$ | Exhaustion | Economic | [0, 1] |
| $ORA$ | Off-Ramp Absence| Diplomatic | [0, 1] |
| $Stal_t$ | Stalemate | Operational | [0, 1] |
| $Dip_{cap}$ | Diplomatic Cap. | Diplomatic | [0, 1] |
| $Shock_k$ | Kinetic Shock | Catalyst | [0, 1] |
| **$V_{contagion}$**| **Regional Contagion**| **Geopolitical** | **[-1, +1]** |
| $Nuc$ | Nuclear Gate | Gatekeeper | [0, 1] |

**Version 21.3 | Production Ready | Bidirectional Contagion & Parsimony Update | Last Updated May 2026**
