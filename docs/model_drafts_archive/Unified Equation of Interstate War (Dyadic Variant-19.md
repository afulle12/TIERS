# Unified Equation of Interstate War (Dyadic Variant) v21.0

## Complete Specification with Full Context & Definitions

**Version:** 21.0 (De-Escalation Engine Integration)  
**Status:** Production-Ready  
**Last Updated:** May 2026

---

## PART 0: VERSION 21.0 CHANGES FROM 20.1

v21.0 preserves the **tier taxonomy and operational assignment rule** from v20.1, but revises the transition model so that de-escalation is no longer treated as a weak residual category.

| Element | v20.1 | v21.0 |
|---------|-------|-------|
| **Tier Assignment** | Operational evidence only | **UNCHANGED** |
| **Tier Taxonomy** | T0–T6 with operational T3/T4 split | **UNCHANGED** |
| **Escalation Modeling** | Escalation-rich, de-escalation thin | **Balanced three-engine transition model** |
| **De-escalation Logic** | Mostly absorbed into pConcede, M_med, and peace mass | **Formal De-Escalation Engine added** |
| **Persistence Logic** | Middle outcome in softmax | **Formal Persistence Engine clarified** |
| **New Latent Indices** | None separated | **E_t, D_t, S_t added explicitly** |
| **Downward Allocation** | Under-specified | **Explicit downward destination weights** |
| **New Inputs** | No de-escalation block | **B_q, M_lev, C_v, F_s, W_x, A_r, P_c, C_d, H_p, E_exit** |
| **Formatting** | Prior rewrite caused parser issues in some renderers | **Restored exact house style from legacy spec** |

**Why this matters:** v20.1 was strong at identifying pressure, rivalry, direct combat, and blocked exits, but it still tended to over-produce persistence or escalation when off-ramps existed but were not represented symmetrically. Real crises often become more dangerous and more negotiable at the same time. v21.0 captures this by separating upward pressure, downward capacity, and persistence lock.

**What stays the same:** The seven-tier operational coding system, actor-directional structure, shared dyad structure, third-party engagement logic, and core next-period probability output remain intact.

---

## PART 1: OVERVIEW & ARCHITECTURE

### 1.1 What This Model Does

The Unified Equation of Interstate War (UIW) v21.0 is a **dyadic probability model** for estimating next-period interstate conflict escalation, persistence, and de-escalation probabilities. It estimates:

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

### 1.2 Seven-Tier Escalation Taxonomy (v21.0 PRESERVED FROM 20.1)

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

```
INPUT CODING
├─ Actor A variables (directional A→B)
│  ├─ Rivalry, alliances, public opinion, advantage, exit posture
│  └─ New de-escalation-relevant directional inputs where applicable
├─ Actor B variables (directional B→A)
│  └─ Same structure, separate values
├─ Shared Dyad variables (same both directions)
│  ├─ Severity, constraints, current state, mediation, frozen-conflict tendency
│  └─ New de-escalation capacity and persistence-lock variables
└─ Third-Party variables
   └─ External engagement, supporting coalitions, mediator leverage

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

#### **Γ (Gamma) — Alliance Depth Toward Target**
- **Definition:** Degree to which initiator (A) has institutionalized military or political alliances supporting action against target (B)
- **Range:** [0, 1]
- **Interpretation:** Higher Γ = A is embedded in an anti-B coalition

#### **Π (Pi) — Non-Alliance Cooperation**
- **Definition:** Degree of non-security cooperation raising the opportunity cost of conflict
- **Range:** [0, 1]
- **Impact:** Higher Π suppresses escalation

#### **Rh (Rh) — Realized Historical Spark / Precedent**
- **Definition:** Do historical precedents or grievances provide a live spark for conflict escalation?
- **Range:** [0, 1]

#### **Ψ (Psi_pub) — Domestic Public Disposition Toward Escalation**
- **Definition:** Initiator's domestic public support for military escalation against the target
- **Range:** [-1, +1]
  - Negative = public opposes escalation
  - Zero = indifferent or split
  - Positive = public supports escalation
- **CRITICAL NOTE:** Code from the initiator's perspective only

#### **FMA (Φ^FMA) — First-Mover / Operational Advantage [DIRECTIONAL]**
- **Definition:** Does initiator have temporary operational advantage that degrades if it waits?
- **Range:** [0, 1]
- **CRITICAL:** Often highly asymmetric; code separately for A→B and B→A

#### **WindowClose (-Ẇ) — Closing Military Window [DIRECTIONAL]**
- **Definition:** Is military balance shifting against initiator in a way that creates now-or-never pressure?
- **Range:** [0, 1]
- **CRITICAL:** Measure military balance shift, not economic decline

#### **pConcede — Willingness to Accept De-escalation / Concession**
- **Definition:** How readily would actor accept negotiated exit or modest concessions to avoid escalation?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Completely rigid
  - **0.2–0.4:** Low willingness
  - **0.5–0.6:** Moderate willingness
  - **0.7–0.8:** High flexibility
  - **0.9–1.0:** Desperate to de-escalate

#### **pCollapse — Collapse / Capitulation Risk**
- **Definition:** How likely is actor to suddenly collapse, experience state failure, or capitulate under stress?
- **Range:** [0, 1]
- **Impact:** Higher pCollapse suppresses escalation and can promote downward movement

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

### 2.2 NEW DE-ESCALATION VARIABLES (v21.0)

These variables are designed to correct the status-quo or escalation bias present in earlier versions.

#### **B_q — Bargaining Channel Quality**
- **Definition:** Availability and seriousness of direct or indirect negotiation channels
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** No meaningful contact; rhetoric only
  - **0.2–0.3:** Indirect signaling through third parties or media
  - **0.4–0.5:** Sporadic backchannel, hotline, or exploratory contact
  - **0.6–0.7:** Repeated talks or active shuttle diplomacy
  - **0.8–1.0:** Structured negotiations with clear agenda and recognized intermediaries

#### **M_lev — Mediator Leverage**
- **Definition:** Can third parties reward, coerce, guarantee, or monitor?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** No mediator or symbolic mediator only
  - **0.2–0.3:** Can host talks but not alter incentives
  - **0.4–0.5:** Can offer limited guarantees or political cover
  - **0.6–0.7:** Can alter incentives materially or pressure parties
  - **0.8–1.0:** Can strongly reward compliance or punish violations

#### **C_v — Ceasefire Verifiability**
- **Definition:** Can restraint be monitored and violations attributed?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Violations impossible to attribute
  - **0.2–0.3:** Attribution highly contested
  - **0.4–0.5:** Partial attribution possible
  - **0.6–0.7:** Most violations attributable with confidence
  - **0.8–1.0:** Strong monitoring and verification architecture exists

#### **F_s — Force Separation Feasibility**
- **Definition:** Can forces disengage physically without exposing either side to immediate exploitation?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Forces interlocked; disengagement is dangerous
  - **0.2–0.3:** Only limited local separation possible
  - **0.4–0.5:** Some sectors can disengage
  - **0.6–0.7:** Separation feasible on most fronts
  - **0.8–1.0:** Lines can be separated quickly and safely

#### **W_x — War-Cost Exhaustion**
- **Definition:** Economic, military, and social fatigue from continuing the conflict at current intensity
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Continuation seen as cheap or sustainable
  - **0.2–0.3:** Costs noticeable but manageable
  - **0.4–0.5:** Strain visible in military, fiscal, or political systems
  - **0.6–0.7:** Costs materially reduce willingness to continue
  - **0.8–1.0:** Severe exhaustion and strong pressure to reduce intensity

#### **A_r — Aim Reversibility**
- **Definition:** Can war aims be delayed, reframed, partially banked, or symbolically satisfied?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Aims are existential or indivisible
  - **0.2–0.3:** Minimal room to reframe aims
  - **0.4–0.5:** Partial symbolic gains possible
  - **0.6–0.7:** Leaders can plausibly claim limited success while pausing
  - **0.8–1.0:** Core aims are easily deferred or partially settled

#### **P_c — Public Compromise Tolerance**
- **Definition:** Domestic willingness to accept bargaining, pauses, or negotiated restraint
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Public would punish negotiations as betrayal
  - **0.2–0.3:** Strong resistance to compromise
  - **0.4–0.5:** Public split
  - **0.6–0.7:** Negotiation politically acceptable
  - **0.8–1.0:** Strong demand for settlement or pause

#### **C_d — Command Discipline**
- **Definition:** Can leadership enforce restraint on regular forces, militias, proxies, and local commanders?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Forces or proxies largely uncontrollable
  - **0.2–0.3:** Frequent rogue action likely
  - **0.4–0.5:** Partial discipline
  - **0.6–0.7:** Most units can comply with restraint orders
  - **0.8–1.0:** Highly reliable enforcement of de-escalation orders

#### **H_p — Humanitarian Pause Pressure**
- **Definition:** International and domestic pressure for pauses, aid corridors, or temporary restraint
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Little pressure for pause
  - **0.2–0.3:** Some rhetorical pressure only
  - **0.4–0.5:** Visible humanitarian pressure
  - **0.6–0.7:** Significant political costs for refusing pause
  - **0.8–1.0:** Sustained pressure strongly favoring temporary restraint

#### **E_exit — Face-Saving Exit Availability**
- **Definition:** Is there a politically survivable narrative that allows leadership to step down without humiliation?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** De-escalation appears as naked defeat
  - **0.2–0.3:** Very limited rhetorical cover
  - **0.4–0.5:** Some reframing available
  - **0.6–0.7:** Restraint can be packaged as prudence or partial success
  - **0.8–1.0:** Clear face-saving exit exists

---

### 2.3 SHARED DYAD VARIABLES (Same Both Directions)

#### **S1, S2, S3, S4, S5, S6 — Within-Tier Severity Scalars**

These measure **intensity within a tier**. They do NOT determine the tier; they measure severity of the tier already assigned.

- **S1 (Diplomatic Severity):** intensity of T1 diplomatic friction
- **S2 (Economic Severity):** intensity of T2 coercion
- **S3 (Proxy/Indirect Severity):** intensity of T3 indirect military competition
- **S4 (Direct Limited Military Severity):** intensity of T4 direct but bounded combat
- **S5 (Strategic War Intensity):** intensity of T5 major war
- **S6 (Nuclear Exchange Scale):** scale of T6 nuclear use

#### **M_med — Mediation / Third-Party Pressure**
- **Definition:** How active and effective is third-party mediation or restraint pressure?
- **Range:** [0, 1]

#### **C_conc — Bilateral Concession Willingness**
- **Definition:** Are both parties making credible offers or moves toward de-escalation?
- **Range:** [0, 1]

#### **X_collapse — Collapse / Capitulation Risk (Bilateral)**
- **Definition:** Is either party at risk of sudden failure or capitulation?
- **Range:** [0, 1]
- **Coding:** Take the higher of the two actors' pCollapse values

#### **F_frozen — Frozen-Conflict Persistence Tendency**
- **Definition:** If conflict persists without escalating, how likely is a stable stalemate?
- **Range:** [0, 1]

#### **ORA — Off-Ramp Absence**
- **Definition:** How structurally blocked are diplomatic or negotiated exits?
- **Range:** [0, 1]
- **CRITICAL:** High ORA suppresses de-escalation and increases skip pressure

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

### 2.4 NEW DE-ESCALATION & PERSISTENCE BLOCKS (Shared / Operational)

#### **R_c — Retaliation Cycle Strength**
- **Definition:** How strongly is the dyad locked into reciprocal tit-for-tat response?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** No active retaliation cycle
  - **0.2–0.4:** Some reciprocal signaling or low-level responses
  - **0.5–0.6:** Repeated tit-for-tat behavior
  - **0.7–0.8:** Strong cyclical retaliation with limited strategic change
  - **0.9–1.0:** Near-automatic reciprocal response pattern

#### **Stal_t — Battlefield / Operational Stalemate**
- **Definition:** Neither side has realistic breakthrough capacity at current intensity
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** One side has clear initiative
  - **0.2–0.4:** Competitive but still fluid
  - **0.5–0.6:** Stalemate emerging
  - **0.7–0.8:** Entrenched deadlock
  - **0.9–1.0:** Near-complete stalemate

#### **Mob_p — Partial Mobilization Persistence**
- **Definition:** Forces are committed enough to sustain current tier, but not configured for decisive escalation
- **Range:** [0, 1]

#### **Rep_l — Reputational Lock-In**
- **Definition:** Leaders fear appearing weak if they step down, yet do not necessarily seek wider war
- **Range:** [0, 1]

#### **Proxy_eq — Proxy Equilibrium**
- **Definition:** Indirect conflict can continue at manageable cost without strong pressure either upward or downward
- **Range:** [0, 1]

#### **Talk_t — Active Talks Signal**
- **Definition:** Are direct or mediated talks active right now?
- **Range:** [0, 1]

#### **Pause_t — Pause Signal**
- **Definition:** Are humanitarian or operational pauses in effect or under serious negotiation?
- **Range:** [0, 1]

#### **Swap_t — Confidence-Building Signal**
- **Definition:** Are prisoner exchanges, bodies-for-bodies swaps, or similar reciprocal steps occurring?
- **Range:** [0, 1]

#### **Withdraw_t — Verified Pullback Signal**
- **Definition:** Are there verified local withdrawals, force thinning, or reduced contact patterns?
- **Range:** [0, 1]

#### **Fatal_t — Fatality Shock**
- **Definition:** Has there been a recent spike in fatalities relative to recent baseline?
- **Range:** [0, 1]

#### **Mobil_t — Mobilization Shock**
- **Definition:** Has visible mobilization, reserve call-up, or major deployment occurred recently?
- **Range:** [0, 1]

#### **Strike_t — Major Attack Shock**
- **Definition:** Has a major new strike or attack changed expectations upward?
- **Range:** [0, 1]

#### **Incurs_t — Incursion Shock**
- **Definition:** Has there been a territorial, naval, or airspace incursion raising acute tension?
- **Range:** [0, 1]

#### **Miscalc_t — Miscalculation / Accident Risk**
- **Definition:** Is command error, misinterpretation, or accidental escalation risk elevated?
- **Range:** [0, 1]

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

### 3.1 Master Unified Equation (v21.0)

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

### 3.3 New Latent Indices

**Escalation Pressure Index:**
$$E_t = w_E X^{esc}_t$$

**De-Escalation Capacity Index:**
$$D_t = w_D X^{deesc}_t$$

**Persistence Lock Index:**
$$S_t = w_S X^{stick}_t$$

### 3.4 Composite Definitions

**Recommended Escalation Composite:**
$$E_t = \text{clip}\left( \alpha_1\Omega + \alpha_2\Gamma + \alpha_3Rh + \alpha_4\Psi_{pub}^{+} + \alpha_5\Phi^{FMA} + \alpha_6(-\dot{W}) + \alpha_7\Xi + \alpha_8\varepsilon + \alpha_9S_k - \alpha_{10}\Pi - \alpha_{11}pConcede, 0, 1 \right)$$

**Recommended De-Escalation Composite:**
$$D_t = \text{clip}\left( \theta_1pConcede + \theta_2B_q + \theta_3M_{lev} + \theta_4C_v + \theta_5F_s + \theta_6W_x + \theta_7A_r + \theta_8P_c + \theta_9C_d + \theta_{10}H_p + \theta_{11}E_{exit}, 0, 1 \right)$$

**Recommended Persistence Composite:**
$$S_t = \text{clip}\left( \rho_1R_c + \rho_2Stal_t + \rho_3Mob_p + \rho_4Rep_l + \rho_5Proxy_{eq}, 0, 1 \right)$$

### 3.5 Context, Barrier, and Shock Terms

**De-Escalation Context:**
$$Z_t^{ctx} = 0.30\,Talk_t + 0.25\,Pause_t + 0.20\,Swap_t + 0.25\,Withdraw_t$$

**Persistence Barrier:**
$$B_t^{barrier} = 0.35\,Stal_t + 0.25\,Rep_l + 0.20\,R_c + 0.20\,Proxy_{eq}$$

**Escalation Shock:**
$$Z_t^{shock} = 0.30\,Fatal_t + 0.25\,Mobil_t + 0.20\,Strike_t + 0.15\,Incurs_t + 0.10\,Miscalc_t$$

### 3.6 Movement Scores (v21.0 UPDATED)

**U↓ (De-escalation Pressure):**
$$U_k^{\downarrow} = a_k^{\downarrow} + b_DD_t + b_M M_{AB}^{med} + b_CC_{AB}^{conc} + b_XX_{AB}^{collapse} + b_{ctx}Z_t^{ctx} - \lambda_k^{\downarrow}D_k - b_{ORA}\,ORA_{AB} - b_EE_t$$

**Interpretation:**
- Higher de-escalation capacity D_t raises downward movement
- Higher mediation, concession, and collapse risk raise downward movement
- Higher ORA suppresses downward movement
- Higher escalation pressure E_t suppresses downward movement

**U0 (Persistence / Stalemate):**
$$U_k^{0} = a_k^{0} + r_SS_t + r_DD_k + r_FF_{AB}^{frozen} + r_BB_t^{barrier} - r_MM_{AB}^{med}$$

**Interpretation:**
- Higher persistence lock S_t raises staying power
- Frozen conflicts and longer duration can stabilize current tier
- Mediation can disrupt stable persistence

**U↑ (Escalation Pressure):**
$$U_k^{\uparrow} = a_k^{\uparrow} + u_EE_t + u_SS_k + u_{skip}S_{AB}^{**} + u_ZZ_t^{shock} + \sigma_k h_{AB} + \nu_k^{nuke} - u_DD_t$$

**Interpretation:**
- Higher escalation pressure E_t raises upward movement
- Higher de-escalation capacity D_t suppresses upward movement
- Skip barrier and shock terms increase upward movement

### 3.7 Default Operational Coefficients (Prototype Use)

These are transparent defaults for hand-scored operational use before full empirical recalibration.

| Parameter | Default |
|-----------|---------|
| a↓ | -0.40 |
| a0 | 0.20 |
| a↑ | -0.35 |
| b_D | 1.30 |
| b_M | 0.40 |
| b_C | 0.35 |
| b_X | 0.30 |
| b_ctx | 0.50 |
| b_ORA | 0.80 |
| b_E | 0.80 |
| r_S | 1.10 |
| r_D | 0.03 |
| r_F | 0.40 |
| r_B | 0.60 |
| r_M | 0.30 |
| u_E | 1.35 |
| u_S | 0.50 |
| u_skip | 1.00 |
| u_Z | 0.55 |
| u_D | 0.75 |

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

**Step 2: Code Existing Directional Variables**

Code Ω, Γ, Π, Rh, Ψ, FMA, WindowClose, pConcede, pCollapse, Xi, HasNuke, and other retained variables.

**Step 3: Code New De-Escalation Variables**

Code B_q, M_lev, C_v, F_s, W_x, A_r, P_c, C_d, H_p, and E_exit.

**Step 4: Code New Persistence / Short-Horizon Variables**

Code R_c, Stal_t, Mob_p, Rep_l, Proxy_eq, Talk_t, Pause_t, Swap_t, Withdraw_t, Fatal_t, Mobil_t, Strike_t, Incurs_t, and Miscalc_t.

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
- E_t = 0.68
- D_t = 0.54
- S_t = 0.47
- Z_t^{ctx} = 0.30
- B_t^{barrier} = 0.45
- Z_t^{shock} = 0.25
- ORA = 0.70
- D_k = 0.40

Then:

$$U_4^{\downarrow} = -0.40 + 1.30(0.54) + 0.50(0.30) - 0.80(0.70) - 0.80(0.68) - 0.05(0.40)$$

$$U_4^{0} = 0.20 + 1.10(0.47) + 0.60(0.45) + 0.03(0.40)$$

$$U_4^{\uparrow} = -0.35 + 1.35(0.68) + 0.55(0.25) - 0.75(0.54) + 1.00S^{**}$$

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
> "UIW v21.0 estimates elevated escalation pressure, but also identifies meaningful de-escalation capacity due to active talks, mediator leverage, and growing war-cost exhaustion. The dyad is dangerous but not locked into pure upward movement. The main suppressors of de-escalation are high ORA and reputational lock-in."

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
✓ Keeps nuclear pathway gated  
✓ Supports scenario analysis and sensitivity testing

### 6.2 Model Limitations

❌ Rare-event tails remain hard to calibrate  
❌ Surprise attacks and leadership shocks remain difficult  
❌ Hand-coded weights are not a substitute for backtesting  
❌ Public opinion and command discipline can be hard to observe in real time  
❌ De-escalation signals may be noisy or deceptive  
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
- [ ] Code Ψ from initiator perspective only
- [ ] Keep Xi discrete: {0, 0.5, 1.0}
- [ ] If neither actor has nuclear weapons, force Θ = 0 and block T6
- [ ] Code ORA realistically: blocked exits mean high ORA, not just bad relations
- [ ] Code new de-escalation block, not just pConcede
- [ ] Code persistence block separately from escalation variables
- [ ] Use one fixed forecast interval consistently
- [ ] Check all variables for valid ranges

---

## PART 8: APPENDIX — COMPLETE VARIABLE SUMMARY TABLE

| Variable | Type | Range | Critical Notes |
|----------|------|-------|----------------|
| Ω | Actor | [0,1] | Structural rivalry |
| Γ | Actor | [0,1] | Alliance depth |
| Π | Actor | [0,1] | Cooperation cost |
| Rh | Actor | [0,1] | Historical spark |
| Ψ | Actor | [-1,+1] | Initiator public support for escalation |
| FMA | Actor | [0,1] | Directional first-mover advantage |
| WindowClose | Actor | [0,1] | Directional closing military window |
| pConcede | Actor | [0,1] | Willingness to settle |
| pCollapse | Actor | [0,1] | Collapse risk |
| Xi | Actor | {0,0.5,1} | Territorial incentive |
| HasNuke | Actor | {0,1} | Nuclear gate |
| B_q | Shared/Operational | [0,1] | Bargaining channel quality |
| M_lev | Shared/Operational | [0,1] | Mediator leverage |
| C_v | Shared/Operational | [0,1] | Ceasefire verifiability |
| F_s | Shared/Operational | [0,1] | Force separation feasibility |
| W_x | Shared/Operational | [0,1] | War-cost exhaustion |
| A_r | Shared/Operational | [0,1] | Aim reversibility |
| P_c | Shared/Operational | [0,1] | Public compromise tolerance |
| C_d | Shared/Operational | [0,1] | Command discipline |
| H_p | Shared/Operational | [0,1] | Humanitarian pause pressure |
| E_exit | Shared/Operational | [0,1] | Face-saving exit availability |
| R_c | Shared/Operational | [0,1] | Retaliation cycle strength |
| Stal_t | Shared/Operational | [0,1] | Stalemate |
| Mob_p | Shared/Operational | [0,1] | Partial mobilization persistence |
| Rep_l | Shared/Operational | [0,1] | Reputational lock-in |
| Proxy_eq | Shared/Operational | [0,1] | Proxy equilibrium |
| Talk_t, Pause_t, Swap_t, Withdraw_t | Shared/Operational | [0,1] | Downward context signals |
| Fatal_t, Mobil_t, Strike_t, Incurs_t, Miscalc_t | Shared/Operational | [0,1] | Upward shock signals |
| S1–S6 | Shared | [0,1] | Within-tier severity |
| M_med | Shared | [0,1] | Mediation effectiveness |
| C_conc | Shared | [0,1] | Bilateral concession willingness |
| X_collapse | Shared | [0,1] | Collapse risk (take max) |
| F_frozen | Shared | [0,1] | Frozen-conflict tendency |
| ORA | Shared | [0,1] | Off-ramp absence |
| D_k | Shared | [0,∞) | Duration at current tier |
| CurrentTier | Shared | {0,1,2,3,4,5,6} | Analyst-coded current tier |
| Θ | Shared | [0,1] | Nuclear salience |
| N_stab | Shared | [0,1] | Deterrence stability |
| Π_vuln | Shared | [0,1] | Arsenal vulnerability |
| Λ_alert | Shared | [0,1] | Technical readiness |
| Δ_doct | Shared | [0,1] | First-use doctrine threshold |

---

**This specification is designed to match the legacy formatting style while adding the missing de-escalation definitions and transition logic.**

**Version 21.0 | Production Ready | Last Updated May 2026**
