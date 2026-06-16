# Unified Equation of Interstate War (Dyadic Variant) v20.0

## Complete Specification with Full Context & Definitions

**Version:** 20.0 (Proxy Tier Integration)  
**Status:** Production-Ready  
**Last Updated:** May 2026

---

## PART 0: VERSION 20.0 CHANGES FROM 19.7

v20.0 integrates a new **T3 (Proxy/Indirect Military Conflict)** tier, addressing a critical gap in v19.7 regarding proxy warfare, intelligence sharing, and weapons provision to adversaries' enemies.

| Element | v19.7 | v20.0 |
|---------|-------|-------|
| **Tier Count** | 6 tiers (T0–T5) | **7 tiers (T0–T6)** |
| **Tier Structure** | T0, T1, T2, T3(Limited Direct), T4(Strategic), T5(Nuclear) | T0, T1, T2, **T3(Proxy), T4(Limited Direct), T5(Strategic), T6(Nuclear)** |
| **Proxy Warfare** | Classified as T1 or T3 ambiguously | **NEW T3: Dedicated tier for indirect military support** |
| **T3 Definition (was "Limited Military")** | Bounded direct operations; strikes, incursions | **MOVED TO T4: Bounded DIRECT operations** |
| **T4 Definition (was "Strategic War")** | Expansive conventional warfare | **MOVED TO T5: Expansive conventional warfare** |
| **T5 Definition (was "Nuclear Exchange")** | Nuclear weapons detonated | **MOVED TO T6: Nuclear weapons detonated** |
| **New Parameters** | N/A | **ProxyDensity, DeniabilityLevel, ProxyReach, SustainabilityIndex** |
| **Transition Probabilities** | 6×6 matrix | **7×7 matrix (requires recalibration)** |
| **Skip Barriers (S**)** | Calculated across 6 tiers | **Updated to 7-tier architecture** |
| **Nuclear Gatekeeper (Ω_AB)** | Gates T5 | **Gates T6** |
| **Mathematical Model** | v19.6 equations (preserved in 19.7) | **UNCHANGED**: Same U↓, U0, U↑, S**, Ω_AB structures; applied to 7-tier matrix |

**Why this matters:** Proxy warfare is increasingly central to great-power competition (US arms to Ukraine, Iran's militia networks, China's gray-zone operations). v19.7 conflated proxy support with either diplomatic crisis (T1) or direct limited war (T3), mischaracterizing escalation dynamics. Proxy conflicts persist for **years without escalating to direct war**, have **different political costs**, and have **different skip probabilities**. v20.0 corrects this structural gap.

**Backward compatibility:** Cases coded for v19.7 can be upgraded by:
1. Identifying any proxy activity and moving to new T3
2. Renumbering direct limited military to T4
3. Renumbering strategic war to T5
4. Renumbering nuclear to T6
5. Re-running transition calculations on 7×7 matrix (all equations preserved)

---

## PART 1: OVERVIEW & ARCHITECTURE

### 1.1 What This Model Does

The Unified Equation of Interstate War (UIW) v20.0 is a **dyadic probability model** for estimating next-period interstate conflict escalation probabilities. It estimates:

$$\pi_{kj}(t) = \text{Pr}(\text{next tier} = j \,|\, \text{current tier} = k, \text{all inputs at time } t)$$

Where:
- **k** = current conflict tier (T0–T6)
- **j** = next-period tier (T0–T6)
- **π_kj** = probability distribution [π₀, π₁, π₂, π₃, π₄, π₅, π₆] summing to 1

**Output interpretation:**
- π₀ = probability of peace (de-escalation)
- π_k = probability of persistence at current tier
- π_{k+1}, ..., π₆ = probabilities of escalation to higher tiers

---

### 1.2 Seven-Tier Escalation Taxonomy (v20.0 UPDATED)

| **Tier** | **Name** | **Military Activity** | **Diplomatic Status** | **Economic Instruments** | **Nuclear** | **Key Examples** |
|----------|----------|----------------------|-----------------------|--------------------------|-------------|------------------|
| **T0** | Peace | None | Normal relations | None | N/A | US–Canada 2020; most dyads |
| **T1** | Diplomatic Crisis | None | Formal friction: protests, ambassador recalls, ultimatums, public threats, UN votes | None | N/A | US–Iran 2019 (post-JCPOA withdrawal) |
| **T2** | Economic Coercion | None | Active negotiation or impasse | **Active + Credibly impactful** (sanctions, trade restrictions, financial exclusion) | N/A | Russia–Ukraine 2014 (post-Crimea); Iran sanctions 2018+ |
| **T3** | Proxy/Indirect Military | **Indirect military support**: weapons provision, intelligence sharing, training to B's enemies; no direct A→B operations | Crisis talks or covert coordination | May include sanctions | N/A | **US arming Ukrainian rebels (2014–2021); Iran militia networks; China gray-zone support to proxies** |
| **T4** | Limited Direct Military | Bounded direct operations: strikes, incursions, skirmishes; limited objectives & geographic scope | Crisis talks or broken mediation | May include sanctions | N/A | Kargil 1999; Israel–Hamas 2021 |
| **T5** | Strategic War | Expansive conventional warfare: ambitious objectives, nationwide scope, full state mobilization | War ongoing; negotiation will occur when feasible | Full mobilization likely | N/A | Ukraine–Russia 2022–2024; Gulf War 1991 |
| **T6** | Nuclear Exchange | **Nuclear weapons detonated in anger** (tactical, theater, or strategic) | Total war; surrender negotiations | Total economic mobilization | **Actual use** | Japan 1945 (Hiroshima/Nagasaki) [only historical case] |

---

### 1.3 Tier Assignment Rule (Foundational)

**Assign the HIGHEST tier fully supported by active evidence:**

1. **T6 threshold:** Nuclear detonation in anger has occurred
2. **T5 threshold:** Military operations are expansive in scope (nationwide, multiple theaters, ambitious objectives, full mobilization) AND direct (A's forces directly engaged against B)
3. **T4 threshold:** Military operations are ongoing and direct, but bounded in scope and intensity (limited geography, limited objectives, partial mobilization)
4. **T3 threshold:** Indirect military support is actively occurring (A providing weapons, intelligence, training to B's enemies) with no direct A→B operations; OR plausible deniability allows proxy operations
5. **T2 threshold:** Economic instruments pass TWO-PART TEST (active + credibly impactful); no direct or proxy military activity
6. **T1 threshold:** Formal diplomatic friction is occurring; no economic coercion, military activity (direct or proxy)
7. **T0 threshold:** None of the above

**CRITICAL DISTINCTION:**
- **T3 requires INDIRECT military activity** (support to third parties against B, not direct A→B engagement)
- **T4 requires DIRECT military activity** (A's forces actively engaged against B)
- If both proxy AND direct military are occurring simultaneously, assign **T4 or T5** (direct activity is highest tier)
- Do NOT mix tiers. If moving between tiers, code the highest active tier.

---

### 1.4 Model Architecture Summary

```
INPUT CODING
├─ Actor A variables (directional A→B)
│  ├─ Rivalry, alliances, public opinion, advantage, exit posture
│  └─ Proxy-specific: ProxyDensity_A, DeniabilityLevel_A, ProxyReach_A
├─ Actor B variables (directional B→A)
│  ├─ Same structure, separate values
│  └─ Proxy-specific: same measures, B's perspective
└─ Shared Dyad variables (same both directions)
   ├─ Severity, constraints, nuclear, current state
   └─ Proxy-specific: ProxySustainability, ProxyDetection

PROCESSING PIPELINE
├─ Structural Motive Computation (M*)
├─ Actor Escalation Chain (p₁, p₂, p₃, p₄, p₅, p₆) [now 7-tier]
├─ Movement Probability Computation (U↓, U0, U↑ → softmax)
├─ Skip Barrier Calculation (S**) [updated to 7×7]
├─ Proxy Persistence Modifier (Λ_proxy) [NEW]
├─ Nuclear Gatekeeper (Ω_AB) [now gates T6]
└─ Destination Allocation (ω⁻, ω⁺)

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

#### **Γ (Gamma) — Alliance Depth Toward Target**
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

#### **Network Centrality & Alignment Measures**

**N_deg — Network Degree Centrality**
- How many formal alliances does initiator (A) have? Higher = more central
- Range: [0, 1] (count alliances, normalize to ~15 max)
- US: N_deg ≈ 0.80; India: ≈ 0.50; Belarus: ≈ 0.20

**N_opp — Adversaries Also Opposing Target**
- Count of A's known rivals who also oppose B (shared enemies help A)
- Range: [0, 1.5] (unbounded; can exceed 1)
- Example: China vs. Taiwan: Japan, US, Australia oppose China → N_opp ≈ 1.2

**N_sup_all — Allies Supporting Target (in conflict)**
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

#### **Ψ (Psi_pub) — Domestic Public Disposition**

**CRITICAL: Code from INITIATOR's perspective ONLY**

- **Definition:** Initiator's domestic public support for military action against target
- **Range:** [-1, +1]
  - Negative = public opposes escalation
  - Zero = indifferent
  - Positive = public supports escalation
- **Coding Anchors:**
  - **-1.0 to -0.8:** Overwhelming opposition (Vietnam War, US 1969)
  - **-0.4 to -0.8:** Majority opposition; large protests
  - **-0.1 to -0.4:** Slight skepticism
  - **0.0:** Indifferent/split
  - **+0.1 to +0.4:** Slight support
  - **+0.4 to +0.8:** Majority support; nationalist fervor
  - **+0.8 to +1.0:** Overwhelming support (Israel post-Oct 7, 2023; China post-arrest of opposition figures)
- **How to Code:**
  1. Check recent polling on military action (if available)
  2. Check media sentiment in initiator's domestic media
  3. Check protest activity (large rallies for/against?)
  4. Historical analogy: Was there public support for previous conflicts?
- **CRITICAL NOTE:** This codes **initiator's** calculation. If coding Russia→Ukraine, use **Russian** public opinion (which is positive due to state control), NOT Ukrainian.

#### **D_a — Democratic Accountability**
- **Definition:** How constrained is initiator's leadership by domestic democratic institutions?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Autocracy; no domestic constraint
  - **0.2–0.4:** Hybrid/electoral autocracy; limited constraint
  - **0.5–0.6:** Weak democracy; legislature present but weak
  - **0.7–0.8:** Strong democracy; legislature has budget/war powers (US, UK, France)
  - **0.9–1.0:** Highly constrained (small parliaments, required referendums)
- **Impact:** Higher D_a suppresses escalation (domestic opposition constrains leaders)

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

#### **pConcede — Willingness to Accept De-escalation / Concession**
- **Definition:** How readily would actor accept negotiated exit or modest concessions to avoid escalation?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Completely rigid; will fight rather than concede
  - **0.2–0.4:** Low willingness; only concedes if losing badly
  - **0.5–0.6:** Moderate; willing to negotiate if offered reasonable terms
  - **0.7–0.8:** High flexibility; prefers negotiated exit
  - **0.9–1.0:** Desperate to de-escalate; will accept unfavorable terms
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
- **Examples:**
  - Iraq→Kuwait 1990: Xi = 1.0 (Iraqi territorial acquisition)
  - Russia→Ukraine 2022: Xi = 1.0 (territorial conquest)
  - US→Iraq 2003: Xi = 0 (regime change, not territory)

#### **HasNuke — Nuclear Weapon Possession**
- **Values:** {0, 1}  (binary gate)
- **Definition:** Does actor possess operationally deployed nuclear weapons?
- **Coding:**
  - **0:** Non-nuclear state
  - **1:** Declared or undeclared nuclear weapons (operationally deployed or capable)
- **CRITICAL IMPACT:** Required to open T6 pathway. If HasNuke = 0, actor cannot initiate T6.
- **Model auto-behavior:** If HasNuke = 0 for both, model forces Theta = 0 and blocks T6 entirely.

---

### 2.2 PROXY-SPECIFIC VARIABLES (NEW IN v20.0) [Directional: A→B]

These variables are **ONLY CODED when A is at T3 (Proxy/Indirect Military)** or potentially escalating TO T3. Code separately for A→B and B→A.

#### **ProxyDensity_A (ρ_proxy_A) — Proxy Network Depth**
- **Definition:** How extensive and capable is A's network of proxy forces, militias, or client actors available to conduct operations against B's interests?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** No proxy infrastructure; ad-hoc support only
  - **0.2–0.3:** Nascent network; one or two weak proxy groups
  - **0.4–0.5:** Established network; 3–5 proxy groups with some capability
  - **0.6–0.7:** Deep network; 5+ capable proxies with demonstrated operational history
  - **0.8–0.9:** Extensive empire; highly organized, professionally trained proxies (Hezbollah, IRGC-managed militias, PMPCS)
  - **0.95–1.0:** Dominant proxy superpower; multiple tiers of trained, equipped, coordinated proxies
- **Examples:**
  - Iran (2020s): ProxyDensity ≈ 0.80 (Hezbollah, Iraqi militias, Houthis, Palestinian groups, Syrian allies)
  - US (supporting Ukrainian rebels 2014–2021): ProxyDensity ≈ 0.40 (limited to Azov, Right Sector, some SBU units)
  - Russia (pre-2022): ProxyDensity ≈ 0.65 (Donbas militias, Chechen groups, Wagner)

#### **DeniabilityLevel_A (δ_A) — Plausible Deniability**
- **Definition:** How eff