# Unified Equation of Interstate War (Dyadic Variant) v21.2

## Complete Specification with Full Context & Definitions

**Version:** 21.2 (Parsimony, Cost-of-Peace, and Contagion Integration)  
**Status:** Production-Ready Prototype  
**Last Updated:** May 2026

---

## PART 0: VERSION 21.2 CHANGES FROM 21.0

v21.2 preserves the **tier taxonomy and operational assignment rule** from v21.0, but restructures the transition model around a parsimonious core set of variables and adds explicit treatment of both the **cost of peace** and **regional conflict contagion**.

| Element | v21.0 | v21.2 |
|---------|-------|-------|
| **Tier Assignment** | Operational evidence only | **UNCHANGED** |
| **Tier Taxonomy** | T0–T6 with operational T3/T4 split | **UNCHANGED** |
| **Parameter Design** | Large, overlapping input set | **Compressed to core directional and shared indices** |
| **Subjective Intent Variables** | Present (for example pConcede, A_r, P_c, Ψ) | **Removed or absorbed** |
| **Economic Opportunity Logic** | War-cost exhaustion only | **Cost of Peace added explicitly** |
| **Regional Spillover Logic** | Implicit only | **Contagion variable added explicitly** |
| **De-escalation Logic** | Broad, multi-input block | **Rebuilt around capacity and off-ramp structure** |
| **Persistence Logic** | Wide persistence block | **Rebuilt around stalemate, duration, ORA, and contagion** |
| **Shock Logic** | Multiple short-horizon inputs | **Collapsed into unified kinetic shock term** |
| **Formatting** | Prior rewrites created inconsistent markdown | **Restored full legacy section structure and clean markdown** |

**Why this matters:** v21.0 captured more of the de-escalation space than earlier versions, but it remained vulnerable to parameter bloat, multicollinearity, and analyst mind-reading. v21.2 shifts the model toward observable structural, operational, and economic realities. It also captures a key omitted mechanism: peace can itself be costly, and nearby wars can raise escalation pressure through contagion.

**What stays the same:** The seven-tier operational coding system, actor-directional structure, shared dyad structure, nuclear gatekeeping idea, and next-period probability output remain intact.

---

## PART 1: OVERVIEW & ARCHITECTURE

### 1.1 What This Model Does

The Unified Equation of Interstate War (UIW) v21.2 is a **dyadic probability model** for estimating next-period interstate conflict escalation, persistence, and de-escalation probabilities. It estimates:

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

### 1.2 Seven-Tier Escalation Taxonomy (v21.2 PRESERVED FROM 20.1/21.0)

| **Tier** | **Name** | **Military Activity** | **Operational Definition** | **Examples** |
|----------|----------|----------------------|----------------------------|--------------|
| **T0** | Peace | None | No military activity or threat thereof | US–Canada 2020; most dyads |
| **T1** | Diplomatic Crisis | None | Formal friction: protests, ambassador recalls, ultimatums, public threats, UN votes | US–Iran 2019 (post-JCPOA withdrawal) |
| **T2** | Economic Coercion | None | Active economic instruments: sanctions, trade restrictions, financial exclusion | Russia–Ukraine 2014 (post-Crimea); Iran sanctions 2018+ |
| **T3** | Proxy/Indirect Military | Passive support only | Weapons, intelligence, training, funding to B's enemies; A's forces NOT directly in combat | Iran funding Hezbollah; arms support without direct combat |
| **T4** | Limited Direct Military | Direct combat | Any direct exchange of fire between A and B forces, regardless of scope, including escort, strikes, active defense | USS *Reuben James* 1941; direct cross-border clashes |
| **T5** | Strategic War | Expansive conventional warfare | Nationwide or multi-front warfare, ambitious objectives, sustained campaigns, major mobilization | Ukraine–Russia 2022–2024; Gulf War 1991 |
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

```text
INPUT CODING
├─ Actor A variables (directional A→B)
│  ├─ Rivalry, first-mover advantage, closing window, territorial incentive
│  └─ Nuclear possession where applicable
├─ Actor B variables (directional B→A)
│  └─ Same structure, separate values
├─ Shared Dyad variables (same both directions)
│  ├─ Current tier, duration, exhaustion, stalemate, off-ramp absence
│  ├─ diplomatic capacity, cost of peace, kinetic shock
│  └─ contagion exposure and nuclear instability
└─ Third-Party / Regional variables
   └─ Mediators, neighboring conflicts, regional spillover structure

PROCESSING PIPELINE
├─ Structural Motive Computation
├─ Escalation Pressure Index (E_t)
├─ De-Escalation Capacity Index (D_t)
├─ Persistence Lock Index (S_t)
├─ Movement Probability Computation (U↓, U0, U↑ → softmax)
├─ Skip Barrier Calculation (S**)
├─ Nuclear Gatekeeper (Ω_AB)
├─ Downward Destination Allocation (ω⁻)
└─ Upward Destination Allocation (ω⁺)

OUTPUT
└─ Next-state distribution π = [π₀, π₁, π₂, π₃, π₄, π₅, π₆]
```

---

## PART 2: INPUT VARIABLES & CODING GUIDANCE

### 2.1 ACTOR-SPECIFIC VARIABLES (Directional)

These are **coded separately for A→B and B→A**. They often differ significantly.

#### **Ω (Omega) — Structural Rivalry Baseline**
- **Definition:** Inherent conflictual disposition based on long-term power competition, historical grievances, and fundamental incompatibility of interests
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Aligned or neutral interests
  - **0.2–0.4:** Competing but not hostile
  - **0.5–0.6:** Clear rivalry with intermittent friction
  - **0.7–0.9:** Deep structural antagonism
  - **1.0:** Existential enmity

#### **FMA (Φ^FMA) — First-Mover / Operational Advantage [DIRECTIONAL]**
- **Definition:** Does initiator have temporary operational advantage that degrades if it waits?
- **Range:** [0, 1]
- **CRITICAL:** Often highly asymmetric; code separately for A→B and B→A

#### **WindowClose (-Ẇ) — Closing Military Window [DIRECTIONAL]**
- **Definition:** Is military balance shifting against initiator in a way that creates now-or-never pressure?
- **Range:** [0, 1]
- **CRITICAL:** Measure military balance shift, not economic decline

#### **Xi (Ξ) — Contiguity / Territorial Gain**
- **Definition:** Is there a territorial dispute that could be resolved by the action?
- **Values:** {0, 0.5, 1}
- **Coding:**
  - **0:** No territorial dispute
  - **0.5:** Adjacent states with dispute, but conflict is not mainly about seizure
  - **1.0:** Action directly resolves territorial dispute or yields conquest

#### **HasNuke — Nuclear Weapon Possession**
- **Values:** {0, 1}
- **Definition:** Does actor possess operationally deployed nuclear weapons?
- **Impact:** Required to open T6 pathway

---

### 2.2 ECONOMIC & DE-ESCALATION VARIABLES (v21.2 UPDATED)

These variables replace large subjective blocks from earlier versions.

#### **C_peace — Cost of Peace**
- **Definition:** How economically, politically, or strategically costly is maintaining the current non-war or limited-war status quo relative to escalation?
- **Range:** [0, 1]
- **Interpretation:** Higher C_peace means peace or restraint is expensive, making escalation relatively more attractive
- **Coding Anchors:**
  - **0.0–0.1:** Peace is cheap and profitable; status quo is sustainable
  - **0.2–0.3:** Some friction from sanctions, deterrence costs, or domestic mobilization
  - **0.4–0.5:** Status quo imposes visible economic or strategic strain
  - **0.6–0.7:** Peace is materially costly and may be eroding regime or military position
  - **0.8–1.0:** Peace is seen as ruinous, humiliating, or strategically fatal

#### **W_x — War-Cost Exhaustion**
- **Definition:** Economic, military, and social fatigue from continuing the conflict at current intensity
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Continuation seen as cheap or sustainable
  - **0.2–0.3:** Costs noticeable but manageable
  - **0.4–0.5:** Strain visible in military, fiscal, or political systems
  - **0.6–0.7:** Costs materially reduce willingness to continue
  - **0.8–1.0:** Severe exhaustion and strong pressure to reduce intensity

#### **Dip_cap — Diplomatic Capacity**
- **Definition:** Combined availability of bargaining channels, mediator leverage, ceasefire monitoring, and force-separation feasibility
- **Range:** [0, 1]
- **Interpretation:** Higher Dip_cap means the dyad has real machinery for de-escalation, not just rhetorical contact
- **Coding Anchors:**
  - **0.0–0.1:** No meaningful channel, no leverage, no verifiable mechanism
  - **0.2–0.3:** Symbolic or weak channels only
  - **0.4–0.5:** Partial communication and limited third-party leverage
  - **0.6–0.7:** Repeated talks, some leverage, and partial verification/separation capacity
  - **0.8–1.0:** Strong channels, real leverage, and credible monitoring/disengagement architecture

---

### 2.3 SHARED DYAD VARIABLES (Same Both Directions)

#### **ORA — Off-Ramp Absence**
- **Definition:** How structurally blocked are diplomatic, political, or operational exits?
- **Range:** [0, 1]
- **CRITICAL:** High ORA suppresses de-escalation and increases both persistence and skip pressure

#### **D_k — Duration at Current Tier**
- **Definition:** How many months has the dyad remained at current tier?
- **Range:** [0, ∞)
- **Coding:** D_k = months / 10 for operational use

#### **CurrentTier (X_t) — Analyst-Coded Current Tier**
- **Values:** {0, 1, 2, 3, 4, 5, 6}
- **Definition:** Which tier is active right now?

#### **Θ (Theta) — Nuclear Shadow Intensity**
- **Definition:** How much are nuclear doctrine, threats, or deployment shaping the crisis?
- **Range:** [0, 1]
- **AUTO-SET:** If neither actor has nuclear weapons, Θ = 0

#### **N_stab — Deterrence Stability**
- **Definition:** How stable is the nuclear balance?
- **Range:** [0, 1]

---

### 2.4 NEW PERSISTENCE, SHOCK, AND CONTAGION BLOCKS (Shared / Operational)

#### **Stal_t — Battlefield / Operational Stalemate**
- **Definition:** Neither side has realistic breakthrough capacity at current intensity
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** One side has clear initiative
  - **0.2–0.4:** Competitive but still fluid
  - **0.5–0.6:** Stalemate emerging
  - **0.7–0.8:** Entrenched deadlock
  - **0.9–1.0:** Near-complete stalemate

#### **Shock_k — Unified Kinetic Shock**
- **Definition:** Has there been a recent cluster of events that sharply raises short-horizon escalation expectations, such as major strikes, fatality spikes, mobilization, or incursions?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** No significant recent escalation shock
  - **0.2–0.3:** Small but noticeable new military activity
  - **0.4–0.5:** Clear short-horizon escalation signal
  - **0.6–0.7:** Major strike, mobilization, or visible shock to expectations
  - **0.8–1.0:** Severe shock with strong immediate escalation pressure

#### **V_contagion — Regional Conflict Contagion**
- **Definition:** To what extent do neighboring or tightly connected conflicts create spillover pressure, imitation effects, refugee flows, weapons diffusion, or opportunistic escalation incentives for this dyad?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** No meaningful regional spillover
  - **0.2–0.3:** Some nearby instability but limited transmission into the dyad
  - **0.4–0.5:** One meaningful adjacent or network-linked conflict raises background pressure
  - **0.6–0.7:** Strong spillover from nearby wars, proxy flows, or regional destabilization
  - **0.8–1.0:** Multiple connected conflicts or severe regional breakdown create high contagion risk

---

### 2.5 NUCLEAR THRESHOLD GATEKEEPER INPUTS

#### **Π_vuln — Arsenal & Command Vulnerability**
- **Definition:** How vulnerable is nuclear arsenal to conventional first strike?
- **Range:** [0, 1]

#### **Λ_alert — Technical Deployment Posture**
- **Definition:** Are nuclear weapons physically mated and launch-ready?
- **Range:** [0, 1]

#### **Δ_doct — Doctrinal First-Use Threshold**
- **Definition:** How readily does doctrine permit nuclear use?
- **Range:** [0, 1]

#### **Ω_AB (Omega_AB) — Nuclear Threshold Barrier [COMPUTED]**

Formula:
$$\Omega_{AB} = \mathbf{1}[\text{HasNuke}] \cdot \left( \Pi_{\text{vuln}} \cdot \Lambda_{\text{alert}} \cdot \Delta_{\text{doct}} \right)$$

---

## PART 3: MATHEMATICAL SPECIFICATION

### 3.1 Master Unified Equation (v21.2)

$$\boxed{\pi_{kj}(t) = \begin{cases}
P_{\downarrow}(T_k)\cdot\omega_{kj}^{-} & j < k \text{ (de-escalate)} \\
P_{0}(T_k) & j = k \text{ (persist)} \\
P_{\uparrow}(T_k)\cdot\omega_{kj}^{+} & j > k \text{ (escalate)}
\end{cases}}$$

**Constraints:**
- P↓(T₀) = 0
- P↑(T₆) = 0
- π₆ = 0 if neither actor has nuclear weapons
- Σ_j π_kj = 1

### 3.2 Movement Probabilities (Softmax)

$$P_{\downarrow} = \frac{\exp(U_k^\downarrow)}{Z}, \quad P_0 = \frac{\exp(U_k^0)}{Z}, \quad P_{\uparrow} = \frac{\exp(U_k^\uparrow)}{Z}$$

$$Z = \exp(U_k^\downarrow) + \exp(U_k^0) + \exp(U_k^\uparrow)$$

### 3.3 Latent Indices

**Escalation Pressure Index:**
$$E_t = w_E X^{esc}_t$$

**De-Escalation Capacity Index:**
$$D_t = w_D X^{deesc}_t$$

**Persistence Lock Index:**
$$S_t = w_S X^{stick}_t$$

### 3.4 Composite Definitions

**Recommended Escalation Composite:**
$$E_t = \text{clip}\left( \alpha_1\Omega + \alpha_2\Phi^{FMA} + \alpha_3(-\dot{W}) + \alpha_4\Xi + \alpha_5C_{peace} + \alpha_6V_{contagion}, 0, 1 \right)$$

**Recommended De-Escalation Composite:**
$$D_t = \text{clip}\left( \theta_1W_x + \theta_2Dip_{cap} + \theta_3(1-C_{peace}), 0, 1 \right)$$

**Recommended Persistence Composite:**
$$S_t = \text{clip}\left( \rho_1Stal_t + \rho_2ORA + \rho_3D_k + \rho_4V_{contagion}, 0, 1 \right)$$

### 3.5 Context, Barrier, and Shock Terms

**De-Escalation Context:**
$$Z_t^{ctx} = Dip_{cap}$$

**Persistence Barrier:**
$$B_t^{barrier} = 0.45\,Stal_t + 0.35\,ORA + 0.20\,V_{contagion}$$

**Escalation Shock:**
$$Z_t^{shock} = Shock_k$$

### 3.6 Movement Scores (v21.2 UPDATED)

**U↓ (De-escalation Pressure):**
$$U_k^{\downarrow} = a_k^{\downarrow} + b_DD_t + b_{ctx}Z_t^{ctx} - \lambda_k^{\downarrow}D_k - b_{ORA}\,ORA - b_EE_t$$

**Interpretation:**
- Higher de-escalation capacity D_t raises downward movement
- Higher diplomatic capacity raises downward movement
- Higher ORA suppresses downward movement
- Higher escalation pressure E_t suppresses downward movement

**U0 (Persistence / Stalemate):**
$$U_k^{0} = a_k^{0} + r_SS_t + r_DD_k + r_BB_t^{barrier}$$

**Interpretation:**
- Higher persistence lock S_t raises staying power
- Longer duration can stabilize current tier
- Stalemate, off-ramp absence, and contagion reinforce persistence

**U↑ (Escalation Pressure):**
$$U_k^{\uparrow} = a_k^{\uparrow} + u_EE_t + u_{skip}S_{AB}^{**} + u_ZZ_t^{shock} + \sigma_k h_{AB} + \nu_k^{nuke} - u_DD_t$$

**Interpretation:**
- Higher escalation pressure E_t raises upward movement
- Higher de-escalation capacity D_t suppresses upward movement
- Skip pressure and kinetic shocks increase upward movement
- Nuclear and hostility modifiers remain available if separately specified

### 3.7 Default Operational Coefficients (Prototype Use)

These are transparent defaults for hand-scored operational use before full empirical recalibration.

| Parameter | Default |
|-----------|---------|
| a↓ | -0.40 |
| a0 | 0.20 |
| a↑ | -0.35 |
| b_D | 1.20 |
| b_ctx | 0.40 |
| b_ORA | 0.90 |
| b_E | 0.85 |
| r_S | 1.05 |
| r_D | 0.03 |
| r_B | 0.55 |
| u_E | 1.30 |
| u_skip | 0.95 |
| u_Z | 0.60 |
| u_D | 0.80 |

### 3.8 Skip Barrier (S**)

$$S^{**}_{AB} = \left(\Phi^{\text{FMA}}_{AB}\right)^{\eta_\phi} \cdot \left(-\dot{W}_{AB}\right)^{\eta_w} \cdot \left(\text{ORA}_{AB}\right)^{\eta_r} \cdot \left(1 - \mathcal{N}_{AB}^{\eta_n}\right)$$

**Interpretation:**
- If first-mover advantage is weak, window not closing, or off-ramps are open, skip pressure falls sharply
- If all are high, skip risk rises
- Strong de-escalation capacity does NOT directly erase S**, but it suppresses U↑ and boosts U↓ elsewhere in the model

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

### 4.3 Default Gate Anchors

| Skip Size | Default Gate |
|-----------|--------------|
| Adjacent tier | 1.00 |
| Two-tier skip | 0.35 |
| Three-tier skip | 0.10 |
| Larger skip | 0.02 |

### 4.4 Boundary Guidance

- T5 usually de-escalates first to T4, not to T1 or T0
- T4 usually de-escalates first to T3 or T2
- T3 usually de-escalates first to T2 or T1
- T2 usually de-escalates first to T1
- T1 usually de-escalates first to T0
- T6 downward movement means reduced active intensity after nuclear use, not instant peace

---

## PART 5: IMPLEMENTATION & PRACTICAL USE

### 5.1 Step-by-Step Prediction Workflow

**Step 1: Assign Current Tier**

Use the operational decision tree from Part 1.

**Step 2: Code Directional Structural Variables**

Code Ω, FMA, WindowClose, Xi, and HasNuke separately where directional coding matters.

**Step 3: Code Shared Economic and Diplomatic Variables**

Code C_peace, W_x, Dip_cap, and ORA.

**Step 4: Code Shared Persistence, Shock, and Contagion Variables**

Code Stal_t, Shock_k, V_contagion, D_k, Θ, N_stab, Π_vuln, Λ_alert, and Δ_doct.

**Step 5: Compute Composite Indices**

Calculate E_t, D_t, S_t, Z_t^{ctx}, B_t^{barrier}, and Z_t^{shock}.

**Step 6: Compute Movement Scores**

Calculate U↓, U0, and U↑.

**Step 7: Softmax Movement Probabilities**

Convert U↓, U0, and U↑ into P↓, P0, and P↑.

**Step 8: Allocate Destinations**

Apply downward and upward destination weights to generate the full π vector.

### 5.2 Worked Skeleton Example

Suppose a dyad is currently at T4.

Assume:
- E_t = 0.71
- D_t = 0.42
- S_t = 0.63
- Z_t^{ctx} = 0.40
- B_t^{barrier} = 0.58
- Z_t^{shock} = 0.35
- ORA = 0.75
- D_k = 0.40

Then:

$$U_4^{\downarrow} = -0.40 + 1.20(0.42) + 0.40(0.40) - 0.90(0.75) - 0.85(0.71) - 0.05(0.40)$$

$$U_4^{0} = 0.20 + 1.05(0.63) + 0.55(0.58) + 0.03(0.40)$$

$$U_4^{\uparrow} = -0.35 + 1.30(0.71) + 0.60(0.35) - 0.80(0.42) + 0.95S^{**}$$

Then softmax these three values and allocate destination weights.

### 5.3 Dashboard Outputs

Each forecast should report:
- **Escalation Pressure:** E_t
- **De-Escalation Capacity:** D_t
- **Persistence Lock:** S_t
- **Movement probabilities:** P↓, P0, P↑
- **Full next-tier vector:** π = [π₀, π₁, π₂, π₃, π₄, π₅, π₆]

### 5.4 Interpretation & Reporting

**Good Report:**
> "UIW v21.2 estimates elevated escalation pressure due to rivalry, expensive peace, and regional contagion, but still identifies some downward capacity through exhaustion and diplomatic structure. The dyad is dangerous, and the main suppressor of de-escalation is high off-ramp absence."

**Bad Report:**
> "The model predicts war with 73.5% certainty."  
> (Too precise; collapses the tier distribution into one misleading headline)

---

## PART 6: VALIDATION & LIMITATIONS

### 6.1 Model Strengths

✓ Captures escalation pressure explicitly  
✓ Preserves operational tier realism  
✓ Represents de-escalation as a real process  
✓ Distinguishes persistence traps from true cooling  
✓ Adds cost-of-peace logic  
✓ Adds regional contagion logic  
✓ Keeps nuclear pathway gated  
✓ Supports scenario analysis and sensitivity testing

### 6.2 Model Limitations

❌ Rare-event tails remain hard to calibrate  
❌ Surprise attacks and leadership shocks remain difficult  
❌ Hand-coded weights are not a substitute for backtesting  
❌ Cost of peace can still be difficult to observe in real time  
❌ Contagion effects may be nonlinear and region-specific  
❌ Multi-actor wars still exceed a purely dyadic simplification

### 6.3 Proper Use

✓ Early warning  
✓ Scenario comparison  
✓ Sensitivity analysis  
✓ Structured expert judgment  
✗ Deterministic forecasting  
✗ Claims of exact point certainty

---

## PART 7: QUICK CODING CHECKLIST

Before running prediction:

- [ ] Assign CurrentTier using operational evidence only
- [ ] Code FMA and WindowClose separately by direction
- [ ] Keep Xi discrete: {0, 0.5, 1.0}
- [ ] Code C_peace as a relative cost-of-restraint measure, not as public emotion
- [ ] Code Dip_cap from real channels, leverage, and verification capacity
- [ ] Code Shock_k as a unified short-horizon escalation signal
- [ ] Code V_contagion from neighboring or network-linked conflict spillover
- [ ] If neither actor has nuclear weapons, force Θ = 0 and block T6
- [ ] Code ORA realistically: blocked exits mean high ORA, not just bad relations
- [ ] Use one fixed forecast interval consistently
- [ ] Check all variables for valid ranges

---

## PART 8: APPENDIX — COMPLETE VARIABLE SUMMARY TABLE

| Variable | Type | Range | Critical Notes |
|----------|------|-------|----------------|
| Ω | Actor | [0,1] | Structural rivalry |
| FMA | Actor | [0,1] | Directional first-mover advantage |
| WindowClose | Actor | [0,1] | Directional closing military window |
| Xi | Actor | {0,0.5,1} | Territorial incentive |
| HasNuke | Actor | {0,1} | Nuclear gate |
| C_peace | Shared/Operational | [0,1] | Relative costliness of peace/restraint |
| W_x | Shared/Operational | [0,1] | War-cost exhaustion |
| Dip_cap | Shared/Operational | [0,1] | Channel, leverage, verification, separation capacity |
| ORA | Shared | [0,1] | Off-ramp absence |
| D_k | Shared | [0,∞) | Duration at current tier |
| CurrentTier | Shared | {0,1,2,3,4,5,6} | Analyst-coded current tier |
| Stal_t | Shared/Operational | [0,1] | Stalemate |
| Shock_k | Shared/Operational | [0,1] | Unified escalation shock |
| V_contagion | Shared/Operational | [0,1] | Regional conflict spillover |
| Θ | Shared | [0,1] | Nuclear salience |
| N_stab | Shared | [0,1] | Deterrence stability |
| Π_vuln | Shared | [0,1] | Arsenal vulnerability |
| Λ_alert | Shared | [0,1] | Technical readiness |
| Δ_doct | Shared | [0,1] | First-use doctrine threshold |

---

**This specification is designed to match the legacy formatting style while replacing low-value or redundant variables with a streamlined structure centered on observable conflict drivers.**

**Version 21.2 | Production-Ready Prototype | Last Updated May 2026**
