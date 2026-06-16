# Unified Equation of Interstate War (Dyadic Variant) v20.1

## Complete Specification with Full Context & Definitions

**Version:** 20.1 (Operational Tier Coding & Third-Party Formalization)  
**Status:** Production-Ready  
**Last Updated:** May 2026

---

## PART 0: VERSION 20.1 CHANGES FROM 20.0

v20.1 makes four critical structural changes addressing real-world escalation ambiguities exposed by the US-Germany 1941 case study and contemporary undeclared wars.

| Element | v20.0 | v20.1 |
|---------|-------|-------|
| **Tier Assignment** | Based on formal acknowledgment OR operational evidence | **Operational evidence ONLY**, regardless of formal declarations |
| **T3/T4 Boundary** | Ambiguous; "bounded" vs "direct" unclear for armed escort | **Single test: Are A's forces directly in combat with B's?** |
| **T3 Definition** | Proxy/indirect; includes armed escort ambiguously | **ONLY passive support**: weapons, intelligence, training, funding; A's forces NOT in combat |
| **T4 Definition** | Limited direct military | **Any direct combat between A and B forces**, including armed escort/defense, regardless of scope |
| **D_a Variable** | Democratic Accountability suppresses escalation | **REMOVED**; functions absorbed into Ψ_pub, pConcede, M_med |
| **Third-Party Modeling** | Dyadic with scattered third-party parameters | **Dyadic with formalized Third-Party Engagement Block; new ε parameter** |
| **Case Coding** | US-Germany 1941: Formal T5 (December) | **Operational T4 (October USS Reuben James); formal declaration irrelevant** |
| **Mathematical Model** | v19.6 equations (preserved in 20.0) | **UNCHANGED**: Same equations; D_a term removed where it appeared |

**Why this matters:** Real-world conflicts (US-Germany 1941, Iran-Israel pre-2024, China-Taiwan gray-zone, Pakistan-India proxy) operate at higher escalation tiers operationally than their formal/diplomatic status suggests. Coding operationally reveals true risk. The cleaner T3/T4 boundary eliminates ambiguity about armed escort, active defense, and direct combat scenarios. Removal of D_a eliminates a confounding variable that conflated institutional constraints with operational behavior. Formalized third-party parameters (ε) allow dyadic models to capture multi-party conflict dynamics without exploding into triadic complexity.

**Backward compatibility:** v20.0 cases can be upgraded by:
1. Recoding tier based on operational reality, not formal declarations
2. Removing D_a values (functions now distributed to other variables)
3. Recoding any "armed escort" or "active defense" scenarios as T4, not T3
4. Adding ε (ExternalEngagement) value for third-party military activity
5. All equations run identically; D_a coefficient simply omitted

---

## PART 1: OVERVIEW & ARCHITECTURE

### 1.1 What This Model Does

The Unified Equation of Interstate War (UIW) v20.1 is a **dyadic probability model** for estimating next-period interstate conflict escalation probabilities. It estimates:

$$\pi_{kj}(t) = \text{Pr}(\text{next tier} = j \,|\, \text{current tier} = k, \text{all inputs at time } t)$$

Where:
- **k** = current conflict tier (T0–T6), coded from **operational evidence**
- **j** = next-period tier (T0–T6)
- **π_kj** = probability distribution [π₀, π₁, π₂, π₃, π₄, π₅, π₆] summing to 1

**Key change from v20.0:** Tier assignment is now **purely operational**. Formal declarations, diplomatic status, and legal neutrality are ignored. The question is: "What is actually happening militarily?" not "What have the parties officially acknowledged?"

**Output interpretation:**
- π₀ = probability of peace (de-escalation)
- π_k = probability of persistence at current tier
- π_{k+1}, ..., π₆ = probabilities of escalation to higher tiers

---

### 1.2 Seven-Tier Escalation Taxonomy (v20.1 OPERATIONAL DEFINITIONS)

| **Tier** | **Name** | **Military Activity** | **Operational Definition** | **Examples** |
|----------|----------|----------------------|-----------------------|----------|
| **T0** | Peace | None | No military activity or threat thereof | US–Canada 2020; most dyads |
| **T1** | Diplomatic Crisis | None | Formal friction: protests, ambassador recalls, ultimatums, public threats, UN votes | US–Iran 2019 (post-JCPOA withdrawal) |
| **T2** | Economic Coercion | None | Active economic instruments: sanctions, trade restrictions, financial exclusion | Russia–Ukraine 2014 (post-Crimea); Iran sanctions 2018+ |
| **T3** | Proxy/Indirect Military | **PASSIVE support only** | Weapons provision, intelligence sharing, training, funding TO B's enemies; A's forces NOT directly in combat | Iran funding Hezbollah; US providing weapons to Ukrainian rebels (pre-escort); China gray-zone militia operations |
| **T4** | Limited Direct Military | **A's forces directly in combat with B** | Any engagement where A's military forces exchange fire with B's forces, regardless of scope, objectives, or defensive posture. Includes: armed convoy escort, direct strikes, active defense of allies. | USS Reuben James sunk by German U-boat (Oct 1941); Israel–Hamas 2021; US convoy escort in Atlantic (1941) |
| **T5** | Strategic War | **Expansive conventional warfare** | Ambitious objectives, nationwide scope, full state mobilization, sustained campaigns | Ukraine–Russia 2022–2024; Gulf War 1991 |
| **T6** | Nuclear Exchange | **Nuclear weapons detonated in anger** | Nuclear weapons actually used (tactical, theater, or strategic) | Japan 1945 (Hiroshima/Nagasaki) [only historical case] |

---

### 1.3 Tier Assignment Rule (Foundational)

**OPERATIONAL ASSIGNMENT: Assign the HIGHEST tier fully supported by operational evidence, regardless of formal declaration or diplomatic acknowledgment.**

```
START: Collect all OPERATIONAL evidence
│
├─ Is nuclear detonation reported/credible?
│  └─ YES → ASSIGN T6 (STOP)
│  └─ NO → Continue
│
├─ Are A's military forces DIRECTLY in combat with B's military forces?
│  ├─ YES → Continue to T5 check (expansive scope?)
│  │  ├─ Multi-front, nationwide, full mobilization? → ASSIGN T5 (STOP)
│  │  └─ Bounded, limited scope? → ASSIGN T4 (STOP)
│  ├─ NO → Continue to T3 check
│
├─ Is A providing PASSIVE military support to B's enemies?
│  ├─ YES (weapons, intelligence, training, funding) → ASSIGN T3 (STOP)
│  └─ NO → Continue to T2 check
│
├─ Is economic coercion ACTIVE and CREDIBLY IMPACTFUL?
│  ├─ YES → ASSIGN T2 (STOP)
│  └─ NO → Continue to T1 check
│
├─ Is formal diplomatic friction present?
│  ├─ YES → ASSIGN T1 (STOP)
│  └─ NO → ASSIGN T0

END
```

**CRITICAL DISTINCTION (T3 vs T4):**
- **T3 requires:** A provides weapons/intelligence/training to B's enemies; A's own forces NOT in direct combat
- **T4 requires:** A's military forces directly exchange fire with B's forces
- **Direct combat = ANY exchange of fire**, regardless of:
  - Who initiated (defensive counts)
  - Duration (single incident counts)
  - Scope (limited naval engagement counts)
  - Stated objectives (escort mission counts if combat occurs)

**EXAMPLES OF TIER ASSIGNMENT:**
- US escorting British convoys, U-boats fire, US Navy fires back → **T4** (direct combat, even if defensive)
- US providing weapons to Ukrainian rebels, no US troops engaged → **T3**
- Iran funding Hezbollah, Hezbollah fires on Israel, Iran not directly involved → **T3**
- Israel strikes Iranian targets directly → **T4** (direct combat between A and B forces)
- Israel provides air cover to rebels fighting Iranian forces → **T4** (A's forces directly in combat)

---

### 1.4 Model Architecture Summary

```
INPUT CODING
├─ Actor A variables (directional A→B)
│  ├─ Rivalry, alliances, public opinion, advantage, exit posture
│  ├─ NOTE: D_a (Democratic Accountability) REMOVED
│  └─ Proxy-specific: ProxyDensity, DeniabilityLevel, ProxyReach, SustainabilityIndex
├─ Actor B variables (directional B→A)
│  ├─ Same structure as A, separate values
│  └─ Proxy-specific: same measures, B's perspective
├─ Third-Party Engagement Block (NEW in v20.1)
│  ├─ ε (ExternalEngagement): aggregate third-party military activity
│  ├─ N_sup_all: allies supporting B against A
│  ├─ N_opp: A's rivals who also oppose B
│  └─ Γ: A's alliance depth
└─ Shared Dyad variables (same both directions)
   ├─ Severity, constraints, economic coercion, current state
   └─ Proxy-specific: ProxyDetection, ProxySustainability

PROCESSING PIPELINE
├─ Structural Motive Computation (M*) [UNCHANGED]
├─ Actor Escalation Chain (p₁, p₂, p₃, p₄, p₅, p₆) [UNCHANGED]
├─ Movement Probability Computation (U↓, U0, U↑ → softmax) [UNCHANGED]
├─ Third-Party Engagement Adjustment (ε multiplier) [NEW]
├─ Skip Barrier Calculation (S**) [updated for operational coding]
├─ Proxy Persistence Modifier (Λ_proxy) [UNCHANGED]
├─ Nuclear Gatekeeper (Ω_AB) [now gates T6, UNCHANGED]
└─ Destination Allocation (ω⁻, ω⁺) [UNCHANGED]

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
  - **0.0–0.1:** Aligned or neutral interests (US–Japan, UK–Canada)
  - **0.2–0.4:** Competing but not hostile (US–China pre-2010, Brazil–Argentina)
  - **0.5–0.6:** Clear rivalry with intermittent friction (India–Pakistan normal years)
  - **0.7–0.9:** Deep structural antagonism (Israel–Iran, Russia–NATO)
  - **1.0:** Existential enmity (rare; reserve for wars already underway)
- **How to Code:**
  1. Do the states have **incompatible vital interests** (territory, ideology, hegemony)? If yes → +0.3
  2. Is there **long history of conflict or proxy competition**? If yes → +0.2
  3. Are they competing for **same regional hegemony**? If yes → +0.2
  4. Sum weighted components; cap at 1.0
- **Examples:**
  - Iraq–Kuwait 1990: Ω = 0.70 (oil disputes + power competition)
  - India–Pakistan: Ω = 0.75 (Kashmir, nuclear competition, historical wars)
  - Russia–Ukraine: Ω = 0.80 (existential; sphere of influence)

#### **Γ (Gamma) — Alliance Depth Toward Target** [Part of Third-Party Engagement Block]
- **Definition:** Degree to which initiator (A) has institutionalized military/political alliances supporting action against target (B)
- **Range:** [0, 1]
- **Interpretation:** Higher Γ = A embedded in anti-B coalition
- **Coding Anchors:**
  - **0.0:** Isolated; no allies
  - **0.2–0.3:** Loose diplomatic support; no alliance treaty
  - **0.4–0.5:** One major ally with shared interests vs. B
  - **0.6–0.8:** Formal alliance structure against B (NATO vs. Russia; SEATO-era vs. USSR)
  - **0.9–1.0:** Deeply embedded in coordinated anti-B coalition
- **Examples:**
  - US preparing action vs. Iran (2019): Γ = 0.70 (Saudi Arabia, UAE, Israel aligned)
  - India preparing action vs. Pakistan (2019): Γ = 0.40 (US/Japan rhetorical support, no formal commitment)

#### **Π (Pi) — Non-Alliance Cooperation**
- **Definition:** Degree of **non-security cooperation** (trade, joint institutions, cultural ties) raising opportunity cost of conflict
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Minimal trade or contact
  - **0.2–0.4:** Trade <5% of GDP; few joint institutions
  - **0.5–0.6:** Moderate trade 5–10%; some institutional cooperation
  - **0.7–0.8:** Significant trade 10–20%; joint regional bodies (pre-Brexit EU, MERCOSUR)
  - **0.9–1.0:** Deep integration >20% trade; currency union or supranational institutions
- **Impact:** Higher Π suppresses escalation (opportunity cost makes conflict costly)

#### **Rh (Rh) — Realized Historical Spark / Precedent**
- **Definition:** Do historical precedents or grievances provide a "spark" for conflict escalation?
- **Range:** [0, 1]
- **Coding:** Log(1 + count of previous militarized disputes in last 50 years) / 2, or historiographical assessment
- **Examples:**
  - India–Pakistan (1971 war fresh memory): Rh = 0.70
  - Japan–USA 1941 (Pearl Harbor planned on historical expansion): Rh = 0.50

#### **Network Centrality & Alignment Measures** [Part of Third-Party Engagement Block]

**N_deg — Network Degree Centrality**
- How many formal alliances does initiator (A) have? Higher = more central
- Range: [0, 1] (count alliances, normalize to ~15 max)
- US: N_deg ≈ 0.80; India: ≈ 0.50; Belarus: ≈ 0.20

**N_opp — Adversaries Also Opposing Target** [THIRD-PARTY PARAMETER]
- Count of A's known rivals who also oppose B (shared enemies help A)
- Range: [0, 1.5] (unbounded; can exceed 1)
- Example: China vs. Taiwan: Japan, US, Australia oppose China → N_opp ≈ 1.2

**N_sup_all — Allies Supporting Target (in conflict)** [THIRD-PARTY PARAMETER]
- If A initiates vs. B, how many states would openly support B?
- Range: [0, 1.5]
- Example: Russia vs. Ukraine (2022): EU, NATO, Japan support Ukraine → N_sup_all ≈ 1.2

**N_sup_imp — Shared Enemies**
- Enemies that both A and B oppose (cooperation constraint)
- Range: [0, 1.5]
- Example: India–US (pre-2022): Both oppose China → N_sup_imp ≈ 0.80

**N_coop_deg — A's Allies Opposing A's Action**
- A's formal allies that would NOT support A vs. B
- Range: [0, 1.5]
- Example: Turkey vs. Greece in NATO: NATO allies constrain Turkish action → N_coop_deg ≈ 0.80

#### **Ψ (Psi_pub) — Domestic Public Disposition** [EXPANDED in v20.1]

**CRITICAL: Code from INITIATOR's perspective ONLY**

- **Definition:** Initiator's domestic public support for military action against target; NOW INCLUDES institutional constraint effects previously in D_a
- **Range:** [-1, +1]
  - Negative = public opposes escalation
  - Zero = indifferent
  - Positive = public supports escalation
- **Coding Anchors:**
  - **-1.0 to -0.8:** Overwhelming opposition; strong institutional barriers (Vietnam War, US 1969)
  - **-0.4 to -0.8:** Majority opposition; large protests; institutional resistance likely
  - **-0.1 to -0.4:** Slight skepticism; some institutional friction
  - **0.0:** Indifferent/split; neutral institutional context
  - **+0.1 to +0.4:** Slight support; permissive institutional context
  - **+0.4 to +0.8:** Majority support; strong institutional enablement (nationalist fervor)
  - **+0.8 to +1.0:** Overwhelming support; no institutional barriers (Israel post-Oct 7, 2023)
- **How to Code:**
  1. Check recent polling on military action (if available)
  2. Check media sentiment in initiator's domestic media
  3. Check protest activity and political debate intensity
  4. **NEW in v20.1:** Also assess institutional/legal constraints. Democracy with strong legislature → factor into the negative direction. Autocracy → neutral or positive institutional context.
  5. Historical analogy: Was there public support for previous conflicts?
- **CRITICAL NOTE:** This codes **initiator's** calculation. If coding Russia→Ukraine, use **Russian** public opinion (which is positive due to state control), NOT Ukrainian. Ψ_pub is about A's domestic readiness, not B's.
- **NEW in v20.1:** Ψ_pub now absorbs the institutional constraint function previously in D_a. If Ψ_pub is strongly negative due to democratic opposition and legislative barriers, that is now coded directly into Ψ_pub as a negative value.

#### **FMA (Φ^FMA) — First-Mover / Operational Advantage [DIRECTIONAL]**

**CRITICAL: Often asymmetric. Code separately for A→B and B→A.**

- **Definition:** Does initiator (A) have temporary operational advantage that degrades if A waits?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** No advantage; symmetric or A at disadvantage
  - **0.2–0.3:** Modest advantage (better recent training, slightly more troops)
  - **0.4–0.5:** Meaningful advantage (technological edge, surprise deployment, force concentration)
  - **0.6–0.7:** Substantial advantage (major maneuver underway, intelligence windfall, target's defenses damaged)
  - **0.8–0.9:** Near-complete surprise (target unprepared; A has overwhelming local superiority)
  - **0.95–1.0:** Asymmetric dominance; target cannot respond (Pearl Harbor scenario; extremely rare)
- **Examples:**
  - Iraq→Kuwait 1990: FMA = 0.85 (total surprise; Kuwait <10k troops vs. Iraq 100k+)
  - Kuwait→Iraq 1990: FMA = 0.15 (conventionally outmatched)
  - Russia→Ukraine 2022: FMA = 0.60 (surprise, but Ukraine mobilized faster than expected)

#### **WindowClose (-Ẇ) — Closing Military Window [DIRECTIONAL]**

**CRITICAL: Measure military balance shift, NOT economic decline.**

- **Definition:** Is balance of military power shifting against initiator in a way that creates "now or never" pressure?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Window wide open or expanding for A
  - **0.2–0.3:** Slow deterioration (A losing 2–3% military power annually)
  - **0.4–0.5:** Clear trend (A losing ~5% annually; visible in public defense spending)
  - **0.6–0.7:** Rapid erosion (A losing 10%+ annually; B rapidly rearming; alliances shifting)
  - **0.8–0.9:** Acute urgency (A's window closing in 12–24 months; B's shift imminent)
  - **0.95–1.0:** Crisis urgency (window closing in months; "now or never")
- **Examples:**
  - Japan 1941 (Japan→US): WindowClose = 0.85 (US rearmament visible; Japan felt compelled to act)
  - Germany 1939 (Germany→Poland): WindowClose = 0.70 (Soviet rearmament visible; Western alliances shifting)
  - Russia 2022 (Russia→Ukraine): WindowClose = 0.50 (Russia fears NATO encroachment, but no imminent military collapse of Russia itself)
- **CAUTION:** Do NOT confuse with economic decline. This is purely military balance.

#### **pConcede — Willingness to Accept De-escalation / Concession** [EXPANDED in v20.1]

- **Definition:** How readily would actor accept negotiated exit or modest concessions to avoid escalation; NOW INCLUDES institutional constraint effects
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Completely rigid; will fight rather than concede; can escalate without constraint
  - **0.2–0.4:** Low willingness; only concedes if losing badly
  - **0.5–0.6:** Moderate; willing to negotiate if offered reasonable terms
  - **0.7–0.8:** High flexibility; prefers negotiated exit; institutional/public constraints favor negotiation
  - **0.9–1.0:** Desperate to de-escalate; will accept unfavorable terms; strong institutional/public opposition to military action
- **NEW in v20.1:** pConcede now partially captures democratic constraint effects. A democracy under strong public opposition to escalation will have high pConcede. An autocracy can have low pConcede regardless of public opinion.
- **Example:** Ukraine 2022 (early, before military turnaround): pConcede ≈ 0.70 (willing to negotiate to stop invasion); Japan 1941: pConcede ≈ 0.05 (perceived existential stakes)

#### **pCollapse — Collapse / Capitulation Risk**
- **Definition:** How likely is actor to suddenly collapse, experience state failure, or capitulate under stress?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.05:** Stable state; no collapse risk
  - **0.1–0.2:** Some fragility (weak institutions, economic stress)
  - **0.3–0.5:** Moderate risk (recent civil unrest, weak central authority)
  - **0.6–0.8:** High risk (ongoing civil war, humanitarian collapse)
  - **0.9–1.0:** Imminent state failure (capital under siege, armed groups control territory)
- **Impact:** Higher pCollapse suppresses escalation (target can't sustain conflict)

#### **Xi (Ξ) — Contiguity / Territorial Gain**
- **Definition:** Is there a territorial dispute that could be resolved by the action? Does initiator gain concrete geographic gains?
- **Values:** {0, 0.5, 1}  (discrete, not continuous)
- **Coding:**
  - **0:** No territorial dispute; non-adjacent states or no land-border issue
  - **0.5:** Adjacent states with disputed border, but conflict is NOT about territorial seizure
  - **1.0:** Action directly resolves territorial dispute or results in conquest
- 