# Unified Equation of Interstate War (Dyadic Variant) v19.7

## Complete Specification with Full Context & Definitions

**Version:** 19.7 (Tier Definition Refinements)  
**Status:** Production-Ready  
**Last Updated:** May 2026

---

## PART 0: VERSION 19.7 CHANGES FROM 19.6

v19.7 refines the **tier assignment definitions** (not the mathematical model itself):

| Element | v19.6 | v19.7 |
|---------|-------|-------|
| **T2 Criterion** | "ANY economic instrument deployed" (hair-trigger) | **TWO-PART TEST:** Active deployment + Credibly impactful |
| **T3 Definition** | Bounded military; "no sustained open-ended war" | Same, but with clearer geographic/objective scope boundaries |
| **T3 ↔ T4 Boundary** | "Open-ended war with no negotiated endpoint expected" | **Scale/scope/intensity** of military engagement (not negotiation expectation) |
| **T4 Definition** | Open-ended war; implies no negotiation | Expansive-scope war; negotiation is normal end-state for BOTH T3 and T4 |
| **Mathematical Model** | v19.6 equations, all parameters | **UNCHANGED** — same U↓, U0, U↑, S**, Ω_AB, skip bonuses |
| **Impact** | Misclassifies cases like US–Mexico 1940, Gulf War endpoint | Correctly assigns tier based on actual scope/intensity; recognizes both T3 and T4 can end via negotiation |

**Why this matters:** Most interstate wars end via negotiated settlement, not total surrender. The distinction between T3 (limited military) and T4 (strategic war) is about the **SCALE/SCOPE/INTENSITY** of the military engagement, not whether negotiation is expected. This clarification prevents misclassification of important cases.

**What stays the same:** All v19.6 equations, parameters, skip barriers, nuclear gatekeeper logic, and implementation procedures remain identical. This is purely a tier definition refinement for accuracy.

---

## PART 1: OVERVIEW & ARCHITECTURE

### 1.1 What This Model Does

The Unified Equation of Interstate War (UIW) v19.7 is a **dyadic probability model** for estimating next-period interstate conflict escalation probabilities. It estimates:

$$\pi_{kj}(t) = \text{Pr}(\text{next tier} = j \,|\, \text{current tier} = k, \text{all inputs at time } t)$$

Where:
- **k** = current conflict tier (T0–T5)
- **j** = next-period tier (T0–T5)
- **π_kj** = probability distribution [π₀, π₁, π₂, π₃, π₄, π₅] summing to 1

**Output interpretation:**
- π₀ = probability of peace (de-escalation)
- π_k = probability of persistence at current tier
- π_{k+1}, ..., π₅ = probabilities of escalation to higher tiers

---

### 1.2 Six-Tier Escalation Taxonomy (v19.7 UPDATED DEFINITIONS)

| **Tier** | **Name** | **Military Activity** | **Diplomatic Status** | **Economic Instruments** | **Nuclear** | **Key Examples** |
|----------|----------|----------------------|-----------------------|--------------------------|-------------|------------------|
| **T0** | Peace | None | Normal relations | None | N/A | US–Canada 2020; most dyads |
| **T1** | Diplomatic Crisis | None | Formal friction: protests, ambassador recalls, ultimatums, public threats, UN votes | None | N/A | US–Iran 2019 (post-JCPOA withdrawal) |
| **T2** | Economic Coercion | None | Active negotiation or impasse | **Active + Credibly impactful** (see two-part test below) | N/A | Russia–Ukraine 2014 (post-Crimea); Iran sanctions 2018+ |
| **T3** | Limited Military | Bounded operations: strikes, incursions, skirmishes; limited objectives & geographic scope | Crisis talks or broken mediation | May include sanctions | N/A | Kargil 1999; Israel–Hamas 2021 |
| **T4** | Strategic War | Expansive conventional warfare: ambitious objectives, nationwide scope, full state mobilization | War ongoing; negotiation will occur when feasible | Full mobilization likely | N/A | Ukraine–Russia 2022–2024; Gulf War 1991 |
| **T5** | Nuclear Exchange | **Nuclear weapons detonated in anger** (tactical, theater, or strategic) | Total war; surrender negotiations | Total economic mobilization | **Actual use** | Japan 1945 (Hiroshima/Nagasaki) [only historical case] |

---

### 1.3 Tier Assignment Rule (Foundational)

**Assign the HIGHEST tier fully supported by active evidence:**

1. **T5 threshold:** Nuclear detonation in anger has occurred
2. **T4 threshold:** Military operations are expansive in scope (nationwide, multiple theaters, ambitious objectives, full mobilization)
3. **T3 threshold:** Military operations are ongoing, bounded in scope and intensity (limited geography, limited objectives, partial mobilization)
4. **T2 threshold:** Economic instruments pass TWO-PART TEST (active + credibly impactful)
5. **T1 threshold:** Formal diplomatic friction is occurring
6. **T0 threshold:** None of the above

**Critical:** Do NOT mix tiers. If moving between tiers, code the highest active tier.

---

### 1.4 Model Architecture Summary

```
INPUT CODING
├─ Actor A variables (directional A→B)
│  └─ Rivalry, alliances, public opinion, advantage, exit posture
├─ Actor B variables (directional B→A)
│  └─ Same structure, separate values
└─ Shared Dyad variables (same both directions)
   └─ Severity, constraints, nuclear, current state

PROCESSING PIPELINE
├─ Structural Motive Computation (M*)
├─ Actor Escalation Chain (p₁, p₂, p₃, p₄, p₅)
├─ Movement Probability Computation (U↓, U0, U↑ → softmax)
├─ Skip Barrier Calculation (S**)
├─ Nuclear Gatekeeper (Ω_AB) [v19.6]
└─ Destination Allocation (ω⁻, ω⁺)

OUTPUT
└─ Next-state distribution π = [π₀, π₁, π₂, π₃, π₄, π₅]
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
- **CRITICAL IMPACT:** Required to open T5 pathway. If HasNuke = 0, actor cannot initiate T5.
- **Model auto-behavior:** If HasNuke = 0 for both, model forces Theta = 0 and blocks T5 entirely.

---

### 2.2 SHARED DYAD VARIABLES (Same both directions)

#### **S1, S2, S3, S4, S5 — Within-Tier Severity Scalars**

These measure **intensity of conflict activity within each tier**. They do NOT determine tier; they measure severity OF the tier you're in.

**S₁ (Diplomatic Severity)**
- Range: [0, 1]
- Anchors: 0.1–0.2 (routine friction) → 0.5–0.65 (ambassador recalled, public ultimatum) → 0.95–1.0 (military response threatened)
- Example: US–Iran 2019: S₁ ≈ 0.65 (severe diplomatic crisis, near ultimatum stage)

**S₂ (Economic Severity)**
- Range: [0, 1]
- Anchors: 0.05–0.15 (token sanctions) → 0.5–0.65 (comprehensive sanctions, OFAC lists) → 0.95–1.0 (total embargo)
- Example: Russia sanctions post-2014: S₂ ≈ 0.70 (comprehensive but not total)

**S₃ (Limited Military Severity)**
- Range: [0, 1]
- Anchors: 0.05–0.15 (single strike) → 0.5–0.65 (month-long operations, multiple domains) → 0.95–1.0 (near-strategic war)
- Example: Israel–Hamas 2021: S₃ ≈ 0.35 (periodic airstrikes, border incidents)

**S₄ (Strategic War Intensity)**
- Range: [0, 1]
- Anchors: 0.25–0.35 (limited war, one side's homeland not engaged) → 0.75–0.85 (near-total war) → 0.95–1.0 (total war)
- Example: Ukraine–Russia 2022: S₄ ≈ 0.80 (nationwide conflict, massive mobilization)

**S₅ (Nuclear Exchange Scale)**
- Range: [0, 1]
- Anchors: 0.1–0.25 (single tactical or test detonation) → 0.65–0.80 (theater exchange) → 0.90–1.0 (strategic exchange)
- Note: You're in T5 AFTER nuclear use. S₅ codes the SCALE of that use.

#### **E — Economic Coercion Deployed**
- **Definition:** Is economic coercion (sanctions, trade restrictions, financial exclusion) actively deployed as policy instrument?
- **Range:** [0, 1]  (continuous measure of deployment intensity)
- **Coding Anchors:**
  - **0.0–0.1:** No sanctions; normal trade
  - **0.2–0.4:** Partial/threatened sanctions; some restrictions but not in force
  - **0.5–0.7:** Active moderate sanctions; OFAC lists, sectoral bans
  - **0.8–1.0:** Aggressive total sanctions; SWIFT exclusion, secondary sanctions
- **CRITICAL:** E ≥ 0.2 → triggers T2 tier. If E > 0, you're AT LEAST T2.
- **Example:** Russia–Ukraine post-2014: E ≈ 0.75

#### **A_alt — Alternative Objective Achievement**
- **Definition:** To what degree has coercer achieved objectives through means OTHER than military escalation?
- **Range:** [0, 1]
- **Coding:** 0.0 (no objectives achieved), 0.5 (half achieved), 1.0 (all objectives achieved; no need to escalate)
- **Impact:** Higher A_alt reduces pressure to escalate (already winning through coercion)

#### **M_med — Mediation / Third-Party Pressure**
- **Definition:** How active and effective is third-party mediation or international pressure to prevent escalation?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.05:** No mediation; parties isolated or rejecting
  - **0.1–0.3:** Informal attempts; weak external pressure
  - **0.4–0.5:** Active mediation by regional power; talks ongoing but tentative
  - **0.6–0.75:** Strong mediation by major power(s); structured talks; credible pressure
  - **0.8–1.0:** Intensive mediation with enforcement capacity; sanctions threatened if escalation
- **Example:** Ukraine–Russia 2022 (early): M_med ≈ 0.40 (diplomatic efforts, but Russia uninterested)

#### **C_conc — Bilateral Concession Willingness**
- **Definition:** Are both parties making concrete, credible offers or moves toward de-escalation?
- **Range:** [0, 1]
- **Coding:**
  - **0.0–0.1:** Neither side offering concessions; intransigent
  - **0.2–0.4:** One side offers; other refuses; no mutual movement
  - **0.5–0.6:** Both showing flexibility; negotiating postures established
  - **0.7–0.8:** Both making concrete offers (ceasefires, territorial adjustments, confidence-building)
  - **0.9–1.0:** Imminent agreement; major concessions exchanged
- **Example:** India–Pakistan post-2019 Balakot: C_conc ≈ 0.30 (India showed no desire to concede)

#### **X_collapse — Collapse/Capitulation Risk (Bilateral)**
- **Definition:** Is either party at risk of sudden state failure or capitulation?
- **Range:** [0, 1]
- **Coding:** Take the **higher** of the two actors' pCollapse values
- **Impact:** Higher collapse risk suppresses escalation (one side can't continue)

#### **F_frozen — Frozen-Conflict Persistence Tendency**
- **Definition:** If conflict persists without escalating, how likely is a stable stalemate (frozen conflict)?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** No tendency to freeze; escalates or de-escalates quickly
  - **0.2–0.4:** Possible stalemate; pressure toward resolution remains
  - **0.5–0.65:** Likely to freeze (geography, logistics prevent further movement)
  - **0.75–0.9:** Strong structural tendency to freeze (DMZ, superpower guarantee)
  - **0.95–1.0:** Nearly certain freeze (entrenched, status quo recognized)
- **Example:** North Korea–South Korea: F_frozen ≈ 0.95 (DMZ, superpower guarantee, 70-year stalemate)

#### **ORA — Off-Ramp Absence [CRITICAL VARIABLE]**

**This is perhaps the MOST IMPORTANT variable. It suppresses de-escalation and increases escalation via skip barrier.**

- **Definition:** How structurally blocked are diplomatic / negotiated exit options?
- **Range:** [0, 1]  (same for both directions)
- **Coding Anchors:**
  - **0.0–0.05:** Many exit channels open; mediation possible; creative compromise available
  - **0.1–0.2:** Some friction, but negotiation channels exist (UN, regional organizations)
  - **0.3–0.4:** Channels exist but damaged; talks intermittent or low-level; trust low
  - **0.5–0.65:** Major obstacles to talks; domestic politics opposes negotiation; third parties push for escalation
  - **0.75–0.85:** Negotiation nearly impossible; maximalist demands; zero-sum framing; previous talks failed
  - **0.95–1.0:** No exit possible; talks conclusively failed; parties ideologically committed to conflict
- **WHERE IT APPEARS IN MODEL (2 PLACES):**
  1. **In U↓ (de-escalation score):** U↓ −= β_ORA · ORA → high ORA suppresses de-escalation
  2. **In S\*\* (skip barrier):** S\*\* multiplied by ORA^η_r → high ORA increases skip likelihood
- **Example:**
  - Russia–Ukraine 2022: ORA ≈ 0.80 (Putin demands NATO withdrawal + regime change; Zelensky refuses talks under military pressure)
  - US–Iran 2019: ORA ≈ 0.65 (channels exist through Oman, but JCPOA collapse has damaged trust)

#### **D_k — Duration at Current Tier**
- **Definition:** How many months has dyad been at current tier (X_t)?
- **Range:** [0, ∞) but typically [0, 10] where 10 = 100+ months
- **Coding:** D_k = months / 10. If 8 months at current tier → D_k = 0.8
- **Impact:** Longer duration → attrition sets in → pressure to de-escalate or escalate (exit current state)
- **Update:** Every month, increase D_k by 0.1. Reset to 0 if tier changes.

#### **CurrentTier (X_t) — Analyst-Coded Current Conflict Tier**
- **Values:** {0, 1, 2, 3, 4, 5}
- **Definition:** Which tier is dyad **currently in** right now?
- **Assignment Rule:** Use tier taxonomy. Assign highest tier with active supporting evidence.
- **This is exogenous input.** Model predicts what happens NEXT, not where you are now.

#### **Θ (Theta) — Nuclear Shadow Intensity**
- **Definition:** How much is nuclear doctrine, threats, or deployment shaping current crisis?
- **Range:** [0, 1]  (auto-forced to 0.0 if neither actor nuclear)
- **Coding Anchors:**
  - **0.0–0.1:** Nuclear weapons not mentioned; not salient
  - **0.2–0.3:** Nuclear dimension present but downplayed (background threat)
  - **0.4–0.5:** Nuclear explicitly referenced in statements; deployment alerts issued
  - **0.6–0.75:** Nuclear threat explicit and credible; mobilization of nuclear forces
  - **0.8–0.95:** Nuclear deterrence is primary constraint; high alert postures
  - **1.0:** Crisis fundamentally about nuclear weapons (Cuba 1962)
- **Example:**
  - Russia–Ukraine 2022: Θ ≈ 0.40 (Putin makes nuclear threats; deterrent-focused, not aggressive)
  - Cuba 1962: Θ ≈ 0.95 (entire crisis centered on nuclear missiles)
- **AUTO-SET:** If neither actor HasNuke, Θ = 0.0 (forced by model)

#### **N_stab — Deterrence Stability (Nuclear)**
- **Definition:** How stable is nuclear balance? Higher = more stable second-strike capability
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.0–0.1:** Highly vulnerable; first-strike temptation maximum; "use it or lose it"
  - **0.3–0.5:** Asymmetric vulnerability; some forces at risk; some survivable leg
  - **0.7–0.85:** Reasonably stable; most forces survivable
  - **0.9–1.0:** Highly stable; robust submarine force; first strike is irrational
- **Examples:**
  - US–USSR 1962: N_stab ≈ 0.50 (vulnerable missiles; crisis partly about instability)
  - US–USSR 1975: N_stab ≈ 0.85 (robust SLBMs; mutual assured destruction)
  - India–Pakistan 1999: N_stab ≈ 0.30 (limited arsenals; vulnerable; high tension)

---

### 2.3 NUCLEAR THRESHOLD GATEKEEPER INPUTS (v19.6)

These three variables determine whether direct skip from T3→T5 is physically or doctrinally possible.

#### **Π_vuln — Arsenal & Command Vulnerability ("Use It or Lose It" Pressure)**
- **Definition:** How vulnerable is nuclear arsenal to conventional first strike?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.01 (Low Risk):** Fully survivable second-strike capability (SSBNs, mobile road-launchers, hardened C³)
  - **0.30 (Moderate Risk):** Asymmetric vulnerability; mix of vulnerable/survivable forces
  - **0.80 (High Risk):** Highly concentrated, vulnerable arsenal; easily destroyed by conventional precision strike

#### **Λ_alert — Technical Deployment Posture (Physical Latency)**
- **Definition:** Are nuclear weapons physically mated to delivery systems and ready to launch? What is technical latency?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.00 (Disassembled/De-mated):** Warheads in civilian storage, away from delivery vehicles; latency days-weeks
  - **0.40 (Low Readiness):** Assembled but not launch-ready; latency hours
  - **0.90 (Hair-Trigger/LOW posture):** Mated to delivery systems, fueled, ready; latency minutes-seconds

#### **Δ_doct — Doctrinal Credibility & First-Use Threshold**
- **Definition:** What is official nuclear doctrine? How readily would state use nuclear weapons?
- **Range:** [0, 1]
- **Coding Anchors:**
  - **0.05 (Restrained/NFU):** Institutionalized No-First-Use policy
  - **0.50 (Conditional):** Use reserved for existential survival threats; ambiguity on threshold
  - **0.95 (Asymmetric Escalation):** Explicit "Escalate to De-escalate" doctrine; nuclear treated as tactical

#### **Ω_AB (Omega_AB) — Nuclear Threshold Barrier [COMPUTED, not input]**

Formula:
$$\Omega_{AB} = \mathbf{1}[\text{HasNuke}] \cdot \left( \Pi_{\text{vuln}} \cdot \Lambda_{\text{alert}} \cdot \Delta_{\text{doct}} \right)$$

---

## PART 3: MATHEMATICAL SPECIFICATION

### 3.1 Master Unified Equation (v19.7 — unchanged from v19.6)

$$\boxed{\pi_{kj}(t) = \begin{cases}
P_{\downarrow}(T_k)\cdot\omega_{kj}^{-} & j < k \text{ (de-escalate)} \\[4pt]
P_{0}(T_k) & j = k \text{ (persist)} \\[4pt]
P_{\uparrow}(T_k)\cdot\omega_{kj}^{+} & j > k \text{ (escalate)}
\end{cases}}$$

**Constraints:**
- P↓(T₀) = 0 (can't de-escalate from peace)
- P↑(T₅) = 0 (can't escalate past nuclear)
- π₅ = 0 if neither actor nuclear (HasNuke = 0 for both)
- Σ_j π_kj = 1 (probabilities sum to 1)

### 3.2 Movement Probabilities (Softmax)

$$P_{\downarrow} = \frac{\exp(U_k^\downarrow)}{Z}, \quad P_0 = \frac{\exp(U_k^0)}{Z}, \quad P_{\uparrow} = \frac{\exp(U_k^\uparrow)}{Z}$$

$$Z = \exp(U_k^\downarrow) + \exp(U_k^0) + \exp(U_k^\uparrow)$$

### 3.3 Movement Scores

**U↓ (De-escalation Pressure):**
$$U_k^{\downarrow} = \alpha_k^{\downarrow} + \beta_{dS} S_k + \beta_M M_{AB}^{\text{med}} + \beta_C C_{AB}^{\text{conc}} + \beta_X X_{AB}^{\text{collapse}} - \lambda_k^{\downarrow} D_k - \beta_{\text{ORA}} \cdot \text{ORA}_{AB}$$

**Interpretation:**
- Higher severity S_k → more de-escalation (war fatigue)
- Higher mediation M_med → more de-escalation
- Higher concessions C_conc → more de-escalation
- Higher collapse risk X_collapse → more de-escalation (can't sustain)
- **Higher ORA → LESS de-escalation** (exits blocked; critical!)
- Longer duration D_k → more de-escalation (attrition)

**Default Parameters:** α↓ = -1.0, β_dS = -0.8, β_M = 0.7, β_C = 0.6, β_X = 0.9, β_ORA = 0.8, λ_D = 0.05

**U0 (Persistence / Stalemate):**
$$U_k^{0} = \alpha_k^{0} + \rho_k D_k + \beta_F F_{AB} - \beta_M^{0} M_{AB}^{\text{med}}$$

**Interpretation:**
- Frozen conflicts (F_frozen) more stable
- Longer duration → more stalemate (exhaustion)
- Mediation disrupts stalemate (active mediation pushes parties off fence)

**Default Parameters:** α0 = 0.5, ρ_D = 0.03, β_F = 0.5, β_M0 = 0.3

**U↑ (Escalation Pressure):**
$$U_k^{\uparrow} = \alpha_k^{\uparrow} + \beta_{uS} S_k + \beta_s S^{**}_{AB} + \sigma_k h_{AB} + \nu_k^{\text{nuke}} + \beta_{\text{haz}} \cdot h_k^{\uparrow}$$

**Interpretation:**
- Higher severity S_k → more escalation (desperation)
- **Higher skip barrier S\*\* → more escalation** (windows closing)
- Nuclear shadow → more escalation (deterrence breakdown)
- Bilateral hazard (both sides want escalation?) → more escalation

**Default Parameters:** α↑ = -1.5, β_uS = 0.8, β_s = 1.0, β_haz = 0.5

Where σ_k = k/5 (tier weighting) and h_AB = bilateral public opinion hazard

### 3.4 Skip Barrier (S**)

$$S^{**}_{AB} = \left(\Phi^{\text{FMA}}_{AB}\right)^{\eta_\phi} \cdot \left(-\dot{W}_{AB}\right)^{\eta_w} \cdot \left(\text{ORA}_{AB}\right)^{\eta_r} \cdot \left(1 - \mathcal{N}_{AB}^{\eta_n}\right)$$

**Components:**
- FMA = First-mover advantage (0–1)
- WindowClose = Closing military window (0–1)
- ORA = Off-ramp absence (0–1)
- N_stab = Deterrence stability (0–1)

**Default Exponents:** η_φ = 1.0, η_w = 1.0, η_r = 1.0, η_n = 1.0

**Interpretation:**
- All components multiplicative
- If any component = 0, then S\*\* = 0 (no skip pressure)
- If all components high, S\*\* = 1.0 (maximum skip pressure)
- **S\*\* gates whether escalation can skip tiers**

**Destination Skip Bonuses (conditional on U↑):**

| Pathway | Bonus |
|---------|-------|
| T1→T3 | S** × 2.0 |
| T1→T4 | S** × 1.5 |
| T2→T4 | S** × 2.5 |
| T3→T5 | **S** × 1.5 × Ω_AB** (v19.6 gated) |

If Ω_AB = 0, then T3→T5 bonus = 0 (skip completely blocked)

---

## PART 4: TIER DEFINITIONS (v19.7 UPDATED)

### **T0 — PEACE**

**Definition:** No active conflict instruments of any kind. Normal diplomatic, economic, and social relations.

**Assignment Rule:**
- No military operations (including exercises escalating into hostilities)
- No economic coercion in force (see T2 two-part test)
- No formal diplomatic friction (ambassadors present, no public ultimatums)
- Routine bilateral relations; disagreements handled through normal channels

---

### **T1 — DIPLOMATIC CRISIS**

**Definition:** Formal diplomatic friction without military operations or economic coercion. The dyad is in active diplomatic dispute.

**Active Instruments (any of these → T1):**
- Public protests, formal diplomatic notes, demarches
- Ambassador recalls or downgrade of diplomatic representation
- Public ultimatums or explicit threats of escalation
- UN votes, Security Council actions, or formal legal filings
- High-level public statements framing relationship as adversarial
- Suspension of joint institutions, joint meetings, or cooperative agreements

**Examples:**
- US–Iran 2019 (post-JCPOA withdrawal): T1 (intense rhetoric, ambassador tension, UN complaints)
- India–Pakistan 2019 (post-Pulwama): T1 (ambassador protests, UN complaints, public ultimatums)

---

### **T2 — ECONOMIC COERCION [v19.7 UPDATED]**

**Definition:** Active, credibly impactful economic instruments are being deployed as a coercive policy tool against the target.

**TWO-PART TEST (BOTH must be YES):**

**Part 1: ACTIVE Deployment**
- Is the economic instrument currently in force as of the coding date?
- NOT merely threatened ("we will impose sanctions if...")
- NOT reversed or walked back (e.g., sanctions lifted, embargo ended)
- NOT blocked by courts, third parties, or circumstances (e.g., sanctions law passed but injunction blocks enforcement)
- NOT circumvented to the point of ineffectiveness (e.g., embargo circumvented by barter deals, leaving no actual economic impact)

**Part 2: CREDIBLY IMPACTFUL**
- Could the instrument realistically affect the target's economy in a material way?
- NOT merely symbolic (ceremonial sanctions on low-ranking officials, token restrictions)
- NOT easily circumventable via obvious workarounds (e.g., goods transshipped through third countries with full visibility)
- Has an actual transmission mechanism from the instrument to the target's economy (trade flow disruption, financial exclusion, supply chain interruption, etc.)

**If EITHER part fails → remain at T1, even if economic instruments were previously attempted**

**Severity Within T2 (use E variable):**
- E = 0.05–0.2: Minimal sanctions (token measures) → still T2, but low severity
- E = 0.3–0.5: Moderate sanctions (sectoral restrictions, targeted asset freezes) → active T2
- E = 0.6–0.8: Comprehensive sanctions (SWIFT exclusion, broad trade restrictions) → high-severity T2
- E = 0.9–1.0: Total embargo (all commerce halted) → extreme T2

**Examples:**

✓ **Iran sanctions (2018–present):** T2
- Part 1: YES — OFAC sanctions actively enforced; firms face real penalties
- Part 2: YES — transmission is clear: sanctions → reduced oil export → currency collapse
- Verdict: T2 (High severity, E ≈ 0.75)

✓ **Russia sanctions (post-2014):** T2
- Part 1: YES — sectoral bans, asset freezes, SWIFT restrictions actively enforced
- Part 2: YES — credible impact on oil/gas, banking, defense sectors
- Verdict: T2 (High severity, E ≈ 0.70)

✗ **US–Mexico 1940:** NOT T2 (remains T1)
- Silver suspension (1938): No longer in force by 1940 → Part 1 fails
- Oil boycott (1938): Blocked by courts, circumvented via third parties → Part 1 fails
- By 1940, economic instruments had lost teeth → return to T1
- Verdict: T1 (Diplomatic friction; E ≈ 0.1)

---

### **T3 — LIMITED MILITARY [v19.7 CLARIFIED]**

**Definition:** Military operations are **bounded in scope and intensity**. Specific, limited objectives.

**Key Distinguishers from T4:**
- **Limited geographic scope:** One region or border area (NOT nationwide)
- **Limited objectives:** Seize specific territory, destroy specific asset, punish opponent (NOT regime change, NOT territorial conquest, NOT state destruction)
- **Partial mobilization:** Some forces deployed (economy NOT converted to war production)
- **Duration:** Episodic or brief (weeks to months typically)
- **Not seeking to eliminate target state** — just achieve specific political goal via military means

**Active Military Instruments (any of these → T3):**
- Airstrikes (single or sustained campaign, but bounded)
- Naval incidents, blockades, or sea control operations
- Ground incursions, skirmishes, or border raids
- Special operations, sabotage, or precision strikes

**How it ends:** Via negotiation, ceasefire, or unilateral withdrawal after objective achieved
- Kargil 1999 → negotiated Line of Control agreement
- 2021 Israel–Hamas → ceasefire agreement
- US airstrikes on Iraq (1998) → objective achieved, forces withdrawn

**Examples:**

✓ **Kargil 1999 (India–Pakistan):** T3
- Limited geography: One region (Kargil peaks)
- Limited objectives: Seize/hold territory
- Duration: ~2 months
- Ended: Via **negotiated** Line of Control agreement
- Verdict: T3

✓ **2021 Gaza (Israel–Hamas):** T3
- Limited geography: Gaza Strip
- Limited objectives: Airstrikes, punish
- Duration: ~11 days
- Ended: Via **negotiated** ceasefire
- Verdict: T3

---

### **T4 — STRATEGIC WAR [v19.7 CLARIFIED]**

**Definition:** Military operations are **expansive in scope and intensity**. Ambitious objectives requiring sustained effort and full state mobilization.

**Key Distinguishers:**
- **Large geographic scope:** Nationwide operations, multiple theaters, or protracted engagement across country
- **Ambitious objectives:** Territorial conquest, regime change, hegemonic position, or enemy state destruction (NOT just tactical goals)
- **Full/near-full national mobilization:** Economy, industry, manpower mobilized for war production
- **Duration:** Sustained/prolonged (months to years); continuous or near-continuous combat
- **Seeking decisive military victory** — forces being brought to bear to decisively defeat enemy

**How it ends:** Via negotiated settlement (when both sides agree terms) OR via military victory (when one side surrenders)
- **Both are end-state mechanisms. Negotiation is NOT the distinguishing factor.**

**Examples:**

✓ **Gulf War 1991:** T4
- Large geographic scope: Nationwide (Iraq + Kuwait)
- Ambitious objectives: Liberate Kuwait + destroy Iraqi army
- Duration: ~6 weeks intensive
- Full mobilization: Both sides mobilized
- Ended: Via **negotiated** ceasefire
- Verdict: T4 (negotiated end is normal for wars)

✓ **Ukraine–Russia 2022–2024:** T4
- Large geographic scope: Nationwide
- Ambitious objectives: Conquest/regime change
- Duration: 2+ years sustained
- Full mobilization: Both states mobilized entire economies
- Ended/will end: Via **negotiated** settlement when both agree
- Verdict: T4 (will likely end via negotiation)

---

### **T3 ↔ T4 BOUNDARY [v19.7 CLARIFIED]**

**The distinction is SCALE/SCOPE/INTENSITY of military engagement, NOT negotiation expectation.**

Both T3 and T4 wars can end via negotiated settlement. Negotiation is an end-state mechanism for BOTH tiers.

**Use this decision test:**

| Question | T3 | T4 |
|----------|----|----|
| **Geographic scope** | One region/border area | Nationwide or multiple theaters |
| **Military objectives** | Limited (seize territory, punish) | Ambitious (conquer, regime change) |
| **National mobilization** | Partial | Full/near-full |
| **Duration** | Brief/episodic (weeks–months) | Sustained (months–years) |
| **Casualties/destruction** | Thousands typical | Tens of thousands or more |

**Assignment rule:** If T4 characteristics apply → T4. If T3 characteristics apply → T3. **Negotiation is NOT part of the criterion.**

---

### **T5 — NUCLEAR EXCHANGE**

**Definition:** Nuclear weapons have been detonated in anger (not test, not accident, but deliberate use in military operations).

**Trigger (only one):**
- At least one nuclear weapon has exploded as a result of military action

**Boundary Clarification:**
- Nuclear threats, alert postures, mobilization → **stay at T4**
- **Actual detonation → T5**

**Only historical example:**
- Japan 1945 (Hiroshima/Nagasaki): T5

---

## PART 5: IMPLEMENTATION & PRACTICAL USE

### 5.1 Step-by-Step Prediction Workflow

**Step 1: Assign Current Tier (5 min)**

Use decision tree:
```
Nuclear detonation occurred in anger?
├─ YES → T5
└─ NO

Conventional warfare (nationwide/ambitious objectives)?
├─ YES → T4
└─ NO

Military operations ongoing (bounded)?
├─ YES → T3
└─ NO

Sanctions pass TWO-PART TEST (active + credible)?
├─ YES → T2
└─ NO

Formal diplomatic friction?
├─ YES → T1
└─ NO → T0 (Peace)
```

**Step 2: Code Variables (30 min)**

For each variable:
1. Read definition in Part 2
2. Find coding anchors
3. Check historical examples
4. Assign value with 80%+ confidence
5. Note uncertainties

**Step 3: Run Prediction (2 min)**

Python:
```python
from UIW_v19_7_Python_Implementation import UIWv197Model

model = UIWv197Model()
result = model.predict(actor_A, actor_B, shared)
```

**Step 4: Interpret Results (10 min)**

- π = [π₀, π₁, π₂, π₃, π₄, π₅]
- Risk = 1 - π₀ (non-peace probability)
- π_k = persistence probability
- Sum of π_{k+1} through π₅ = escalation probability
- Understand which variables drive result (sensitivity: vary ORA ±0.1, see output change)

### 5.2 Backtesting for Calibration

**Procedure:**

1. Gather 20–50 historical conflicts with known start dates
2. For each conflict, code inputs at 3–4 lead times (12 mo, 6 mo, 3 mo, month-of before start)
3. Run predictions; record predicted prob and actual outcome (1 = conflict occurred, 0 = no)
4. Group predictions into 10% brackets (0–10%, 10–20%, etc.)
5. For each bracket, calculate actual frequency
6. Plot predicted vs. actual; well-calibrated models fall on y=x line

**Metrics:**
- **Calibration:** Actual frequency ≈ mean predicted probability in bracket
- **Brier Score:** Mean squared error between predicted and actual (lower is better; <0.20 is good)
- **ROC-AUC:** Can model discriminate conflicts from non-conflicts? (>0.70 is good)

### 5.3 Interpretation & Reporting

**Good Report:**
> "UIW v19.7 estimates next-period escalation risk at 58% given current inputs. This reflects strong structural rivalry (Ω=0.75), closing military window (WindowClose=0.6), and blocked off-ramps (ORA=0.7). Key drivers of escalation are window closure and absent mediation. Risk is sensitive to mediation: if bilateral talks resume (M_med from 0.2 to 0.6), estimated risk drops to 38%. Model assigns <1% probability to nuclear escalation due to stable deterrence (N_stab=0.85) and de-mated nuclear posture (Λ_alert=0.05). Assumptions: CurrentTier = T2; Psi_pub reflects initiator perspective; code date = May 2026."

**Bad Report:**
> "The model predicts 73.5% war probability."  
> (Too precise; ignores uncertainty; doesn't explain drivers)

---

## PART 6: VALIDATION & LIMITATIONS

### 6.1 Model Strengths

✓ **Flags escalation risk** when structural conditions change  
✓ **Captures mediation effects** (M_med suppresses escalation)  
✓ **Models network effects** (allies, shared enemies influence outcome)  
✓ **Incorporates public opinion** (Psi_pub constrains leaders)  
✓ **Gates nuclear escalation** (structural barriers even in acute crisis)  
✓ **Quantifies trade-offs** (what happens if ORA changes?)

### 6.2 Model Limitations

❌ **Accidents & surprises:** Pearl Harbor–type attacks get low scores (hard to signal intent)  
❌ **Rare events:** Tail probabilities (90%+) have high variance; large sample needed  
❌ **Frozen conflicts:** May over-weight persistence vs. sudden escalation  
❌ **Regime change:** Model assumes actor objectives stable; revolutions change goals  
❌ **Idiosyncratic leadership:** Individual decision-makers can override structural incentives  
❌ **Asymmetric information:** Model assumes perfect information; real world has surprises

### 6.3 When NOT to Trust the Model

- **Within 2–3 weeks of conflict start:** Information unstable
- **After major shock:** New alliances, leadership, ideology invalidate inputs
- **With <10 years conflict history:** Limited pattern to learn from
- **With π > 0.95:** No event should be this extreme
- **For point predictions:** "73.5% probability" is false precision

### 6.4 Proper Use

✓ Highlight tail risks: "Model flags 65% escalation risk under current inputs"  
✓ Scenario analysis: "If talks collapse, risk rises to 80%"  
✓ Relative rankings: "Crisis A riskier than Crisis B"  
✗ Point predictions: "War will occur with 73.5% probability"  
✗ Causality: "ORA causes escalation" (only correlational)

---

## PART 7: PARAMETER REFERENCE

### Global Model Parameters (Do NOT Change Without Recalibration)

| Parameter | Default | Range | Meaning |
|-----------|---------|-------|---------|
| α↓, α0, α↑ | -1.0, 0.5, -1.5 | Scalars | Intercepts for movement scores |
| β_dS | -0.8 | [-3, 0] | Downward weight on severity |
| β_M | 0.7 | [0.5, 1.5] | Mediation weight (U↓) |
| β_M0 | 0.3 | [0.1, 0.5] | Mediation penalty (U0) |
| β_C | 0.6 | [0.3, 1.0] | Concession weight |
| β_X | 0.9 | [0.5, 1.5] | Collapse risk weight |
| β_ORA | 0.8 | [0.5, 1.5] | **Off-ramp absence weight (critical)** |
| β_s | 1.0 | [0.7, 1.5] | Skip barrier weight in U↑ |
| β_haz | 0.5 | [0.2, 1.0] | Bilateral hazard weight |
| λ_D | 0.05 | [0.01, 0.1] | Duration decay weight |
| ρ_D | 0.03 | [0.01, 0.1] | Duration persistence weight |
| β_F | 0.5 | [0.2, 1.0] | Frozen conflict weight |
| η_φ, η_w, η_r, η_n | 1.0 | [0.5, 2.0] | Skip barrier exponents |

---

## PART 8: QUICK CODING CHECKLIST

Before running prediction:

- [ ] **Assign CurrentTier** using decision tree (tier taxonomy)
- [ ] **Code FMA & WindowClose separately** for A→B and B→A (asymmetry expected)
- [ ] **Psi_pub from initiator's perspective** (domestic support for action)
- [ ] **For T2:** Apply TWO-PART TEST (active + credible) 
- [ ] **ORA realistic:** Are diplomatic exits actually blocked? (0.05 if open, 0.85 if failed)
- [ ] **If neither HasNuke = 1:** Force Theta = 0 and block T5 (model does this automatically)
- [ ] **If both HasNuke = 1:** Model auto-derives Monopoly = 0 (MAD regime)
- [ ] **All numeric variables in correct ranges** [0,1], [-1,1], etc.
- [ ] **D_k updated** (months at current tier ÷ 10)
- [ ] **Xi discrete:** Must be {0, 0.5, 1.0}, not continuous

---

## PART 9: TROUBLESHOOTING

**Model predicts 95% risk for peaceful dyad (US–Canada):**

- Check: Is Omega <0.2? Should be for peaceful dyads.
- Check: Is CurrentTier = T0? If T1+, tier assignment wrong.
- Check: Is ORA > 0.5? Shouldn't be if diplomatic channels exist.
- **Fix:** Re-assign tier or reduce Omega.

**Model predicts 85% but conflict didn't occur:**

- This is calibration data. Track many predictions.
- Make 100 predictions in "80–90%" bracket; check what % had conflict.
- If <80%, model is overconfident in tail; document for recalibration.

**FMA same for both actors:**

- **WRONG.** FMA is directional. Iraq vs. Kuwait differs from Kuwait vs. Iraq.
- A's advantage often differs greatly from B's.

**Theta = 0.5 for non-nuclear state:**

- **WRONG.** Model auto-forces Theta = 0.0 if neither HasNuke.
- Don't override this.

---

## PART 10: VERSION HISTORY

| Version | Date | Major Changes |
|---------|------|---------------|
| **19.7** | May 2026 | **TIER REFINEMENTS:** T2 two-part test (active + credible); T3↔T4 boundary based on scope/scale, not negotiation |
| **19.6** | May 2026 | **NEW:** Nuclear Threshold Gatekeeper (Ω_AB); gates T3→T5 skip |
| 19.5 | 2025 | Restored skip barrier; ORA in multiple terms |
| 19.4 | 2024 | Movement scores (U↓, U0, U↑); softmax |
| 19.0 | 2023 | Initial specification |

---

## PART 11: HOW TO CITE

**Academic:**
> Author (Year). "Unified Equation of Interstate War (Dyadic Variant) v19.7: Specification." *Journal/Report*.

**Policy brief:**
> According to the UIW v19.7 model, escalation risk from [Tier] to [Tier] is estimated at [π]% given [assumptions].

---

## APPENDIX: COMPLETE VARIABLE SUMMARY TABLE

| Variable | Type | Range | Critical Notes |
|----------|------|-------|-----------------|
| Ω | Actor | [0,1] | Structural rivalry |
| Γ | Actor | [0,1] | Alliance support |
| Π | Actor | [0,1] | Cooperation cost |
| Rh | Actor | [0,1] | Historical spark |
| N_deg, N_opp, N_sup_all, N_sup_imp, N_coop_deg | Actor | [0,1.5] | Network measures |
| Ψ | Actor | [-1,+1] | **Initiator's** public opinion |
| D_a | Actor | [0,1] | Democratic constraint |
| FMA | Actor | [0,1] | **DIRECTIONAL** first-mover |
| WindowClose | Actor | [0,1] | **DIRECTIONAL** closing window |
| pConcede | Actor | [0,1] | Willingness to settle |
| pCollapse | Actor | [0,1] | State failure risk |
| Xi | Actor | {0,0.5,1} | Territorial dispute |
| HasNuke | Actor | {0,1} | Nuclear gate |
| S1–S5 | Shared | [0,1] | Within-tier severity |
| E | Shared | [0,1] | Economic coercion |
| A_alt | Shared | [0,1] | Objectives achieved non-militarily |
| M_med | Shared | [0,1] | Mediation effectiveness |
| C_conc | Shared | [0,1] | Concession willingness |
| X_collapse | Shared | [0,1] | Collapse risk (take max) |
| F_frozen | Shared | [0,1] | Stalemate tendency |
| **ORA** | Shared | [0,1] | **CRITICAL:** Off-ramp absence |
| D_k | Shared | [0,∞) | Duration at current tier |
| CurrentTier | Shared | {0,1,2,3,4,5} | Analyst-coded current tier |
| Theta | Shared | [0,1] | Nuclear salience (auto 0 if no nukes) |
| N_stab | Shared | [0,1] | Nuclear stability |
| Pi_vuln | Shared | [0,1] | **v19.6:** Arsenal vulnerability |
| Lambda_alert | Shared | [0,1] | **v19.6:** Deployment readiness |
| Delta_doct | Shared | [0,1] | **v19.6:** Doctrinal first-use |

---

**This specification is complete and self-contained. It includes all variable definitions, coding guidance, mathematical formulas, and practical implementation procedures. Print and keep with you.**

**Version 19.7 | Production Ready | Last Updated May 2026**