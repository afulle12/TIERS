# Unified Equation of Interstate War (Directed-Dyad Variant) v24.0

## Complete Specification with Full Context & Definitions

**Version:** 24.0 (Stochastic-Game Reframing, Cost-Landscape Engine, Modifier Axes & T3 Refinement)
**Status:** Specification Phase — Awaiting Empirical Calibration (NOT production-validated)
**Last Updated:** May 2026

---

## PART 0: VERSION 24.0 CHANGES FROM 22.0 / 23.0

v24.0 consolidates the v23.0 theoretical reframing and adds the structural finding that emerged from working through five separate "edge cases": **the model's true shape is a small number of tiers crossed with a few orthogonal modifier axes, not a longer ladder.** Sanctions-type (T2), deniable-strikes, integration-depth, and the proxy-entry threshold all turned out to be *modifiers on an axis the single ladder did not name*, rather than new rungs. v24.0 makes that structure explicit.

| Element | v22.0 | v24.0 |
|---------|-------|-------|
| **Theoretical basis** | Implicit physics analogy (energy levels) | **Explicit stochastic game; softmax re-derived as multinomial logit (discrete choice), not Boltzmann** |
| **Direction-stage engine** | Three separate indices ($E_t, D_t, S_t$) with overlapping inputs | **Single per-actor cost field $\mathcal{C}_i(j)$; movement scores are cost gradients across activation barriers** |
| **Inter-tier transitions** | Implicit; skip logic only | **Explicit activation barriers $B_{k\to j}$; $Shock_k$ supplies activation energy** |
| **Cost of war** | Absent; only $C_{peace}$ (cost of peace) | **Cost-of-war differential built into the cost field; sanctions raise the status-quo floor *and* lower war's relative cost** |
| **Strategic anticipation** | $-\dot{W}$ as a static additive | **Forward-looking term: climb to a costlier tier now to avoid a worse expected future landscape (preventive logic)** |
| **Beliefs** | Absent | **Belief term $\hat{\mathcal{C}}_i(\mathcal{C}_c)$: each actor's estimate of the other's costs. Deterrence, signaling, miscalculation live here.** |
| **Tier discreteness** | Sharp tiers; gray zone unrepresentable | **Tiers acknowledged as analyst-imposed cuts on a continuum** |
| **Gray zone** | — | **T3-High: sustained, resourced gray-zone campaign as a latched tier (one-off deniable acts are $Shock_k$, not a tier)** |
| **T3 entry threshold** | "Any arms/intel/funding to B's enemies" | **Sustained + *selective* support directed at $j$'s adversaries; indifferent-merchant case explicitly excluded** |
| **Patron commitment** | "Passive support only" | **Integration-depth modifier: a patron can be near-co-belligerent without being in direct combat** |
| **Reconciliation (§3.6)** | max/min heuristic | **Re-grounded as one-shot best-response between two cost landscapes** |
| **Composition eq., allocation/skip, hard gates, Core 13** | — | **Largely UNCHANGED; allocation machinery survives the engine swap** |

**Why this matters.** The softmax is correct — not because conflict resembles a thermal system, but because it is the multinomial logit, the canonical form for choice-under-uncertainty, derivable from utility maximization with random errors and zero physics. Relabeling the provenance stops the model defending the false-discreteness and memorylessness the electron picture smuggled in, and it surfaces the largest missing pieces: beliefs, and the modifier axes (attribution, integration, stakes, intent) that a one-dimensional ladder cannot carry.

---

## PART 1: OVERVIEW & ARCHITECTURE

### 1.1 What This Model Does

The Unified Equation of Interstate War (UIW) v24.0 is a **directed-dyad stochastic-game model** for estimating next-period interstate conflict escalation, persistence, and de-escalation. For an ordered pair $(i \rightarrow j)$ — "the prospect of $i$ escalating against $j$" — it estimates the full distribution over next-period tiers. Each actor is a forward-looking agent minimizing a per-actor cost field over a *shared* state variable (the relationship tier), under uncertainty about the other's costs.

The model is **two-stage** plus a reframed engine:

0. **Cost field (engine).** For acting agent $i$, evaluate the cost-to-occupy each reachable tier, $\mathcal{C}_i(j)$ — occupancy cost + a forward-looking strategic term + a belief coupling to the counterpart's costs.
1. **Direction stage.** Movement scores are *cost gradients* between the current tier and adjacent tiers, each penalized by an inter-tier activation barrier. Softmax → $(P_\downarrow, P_0, P_\uparrow)$.
2. **Allocation stage.** Conditional on a direction, distribute that direction's mass across reachable destination tiers via skip weights $\omega^+$ (upward, catalytic) and $\omega^-$ (downward, bimodal).

The output is the composition:

$$\pi_{kj}(t) = \text{Pr}(\text{next tier} = j \mid \text{current tier} = k, \text{ inputs at } t)$$

a vector over the ordered tier list (see §1.2) summing to 1.

**Recommended forecast interval:** 30 days. See §1.5 for the slow-variable caveat.

### 1.2 Escalation Taxonomy (REVISED — T3-High added; tiers are cuts on a continuum)

Tiers are **analyst-imposed cuts on a continuum**, not quantized states. There is no boundary condition forcing discreteness, so each cut must earn its place empirically (§6.7). v24.0 adds **T3-High** to capture the sustained gray-zone campaign that the v22 "any exchange of fire = T4" rule could not represent, while keeping it firmly distinct from one-off deniable acts (which are shocks, not a tier).

| **Tier** | **Name** | **Military Activity** | **Operational Definition** | **Examples** |
|----------|----------|----------------------|----------------------------|--------------|
| **T0** | Peace | None | No military activity or threat thereof | US–Canada 2020 |
| **T1** | Diplomatic Crisis | None | Formal friction: protests, recalls, ultimatums, UN votes | US–Iran 2019 |
| **T2** | Economic Coercion | None | Active sanctions, trade restrictions, financial exclusion | Russia–West 2014 |
| **T3** | Proxy/Indirect Military | Passive support only | *Sustained, selective* material support (arms, intel, training, funding) to $j$'s adversaries, directed at $j$; $i$ not in direct combat. See §1.7 entry condition. | Iran funding Hezbollah |
| **T3-High** | Sustained Gray-Zone Campaign | Deniable kinetic, sustained | A *resourced, directed, multi-period* campaign of deniable strikes / sabotage / cyber-with-physical-effect — attributable harm without acknowledged direct combat. A **latched** tier (min. $D_k$ + observable effort). One-off deniable acts are $Shock_k$, not this tier. | Israel–Iran shadow war; pre-2022 Donbas |
| **T4** | Limited Direct Military | Acknowledged direct combat | Open, attributed exchange of fire between $i$ and $j$ forces | USS *Reuben James* 1941 |
| **T5** | Strategic War | Expansive conventional | Nationwide / multi-front warfare, sustained campaigns | Ukraine–Russia 2022+ |
| **T6** | Nuclear Exchange | Nuclear weapons used | Nuclear weapons detonated in anger | Japan 1945 |

> **Ordered list for "adjacency":** T0, T1, T2, T3, T3-High, T4, T5, T6. T3-High sits between proxy support and acknowledged combat in *escalation* terms, but note (§1.6.1) it is high on a *different* axis (attribution-suppressed harm) and is not a clean intensity rung — its tier status is earned by *sustainment*, which converts a transient into an occupied state.

> **Note on T2 (two populations).** Economic coercion is occupied by *coercive-prelude* sanctions (live dispute, force conceivable) and *expressive/values* sanctions (punishment for internal conduct, no security stake, near-zero escalation path). The tiers do not distinguish them — the **structural variables and the stakes modifier do**. High $\Omega\Xi$ → coercive-prelude; low $\Omega$, no territorial dispute, near-zero status-quo burden *for the sanctioner* → expressive, which must show overwhelming persistence mass (§6.7).

### 1.3 Tier Assignment Rule (Foundational, UNCHANGED in spirit)

Assign the **highest** tier fully supported by operational evidence, descending from T6. Do not mix diplomatic language with operational coding. **Caveats:** (a) because tiers are cuts on a continuum, a dyad genuinely between tiers is coded at the nearest tier *and* flagged with the relevant modifier (§1.6); (b) T3 and T3-High both carry sustainment and selectivity conditions (§1.7) — meeting the surface description is not sufficient.

### 1.4 Directed-Dyad Convention (UNCHANGED from v22.0, reinterpreted)

A dyad is an **ordered pair** $(i \rightarrow j)$. Run the model twice. The current tier $k$ is shared; directional variables ($FMA$, $-\dot{W}$, integration depth, and the belief term) carry the acting actor's subscript; symmetric variables ($\Omega, \Xi, V_{contagion}, Nuc$) take the same value both ways. **Reinterpretation:** the two runs are the **two players' cost landscapes over the same state variable**. War is what happens when those landscapes disagree about where the minimum lies and no belief correction intervenes before a barrier is crossed (§3.6).

### 1.5 Forecast-Interval Caveat (UNCHANGED from v22.0)

Slow structural inputs ($\Omega, \Xi, -\dot{W}$) are near-constant over a 30-day window; period-to-period variation comes from the fast inputs ($Shock_k$, $Dip_{cap}$, $V_{contagion}$, belief updates). Slow variables set the baseline cost landscape; fast variables provide timing; shocks supply activation energy. Do not expect the structural level to explain month-to-month movement — it explains the level around which movement occurs.

### 1.6 The Modifier-Axes Structure (NEW — the recurring finding)

Working through five "edge cases" (sanctions at T2, deniable strikes, integration depth, the proxy-entry threshold, the arms-merchant exclusion) produced the same result each time: the issue was **not a missing rung but a missing axis**. The single escalation ladder measures hostility intensity between $i$ and $j$; several decision-relevant facts are *orthogonal* to that axis. v24.0 represents them as **modifiers** layered on the tier, not as additional tiers:

| Modifier axis | What it captures | Where it acts in the model | Canonical case |
|---------------|------------------|----------------------------|----------------|
| **Attribution** | How deniable the harm is | Suppresses the upward barrier $B$ (deniability lets both sides absorb harm without a forced response). Sustained → latches T3-High. | Israel–Iran shadow war |
| **Integration depth** | How bound a patron is to a client's war (kill-chain participation short of combat) | Suppresses the patron's $T3\to T4$ barrier; gates the patron's de-escalation | US–Ukraine vs Russia |
| **Stakes** | Whether the issue is existential or peripheral | Enters $V_i(\cdot)$ via $\Omega\Xi$; separates expressive from coercive-prelude T2 | Values-sanctions vs prelude |
| **Intent/selectivity** | Whether support is hostile-directed or indifferent commerce | T3 entry gate (§1.7); selectivity is the observable proxy for intent | Arms dealer selling to both sides |

The practical consequence: a tier label alone is not a state. A T3 dyad with deep integration and existential stakes behaves nothing like a T3 dyad of shallow, peripheral support — and the difference is what predicts the $T3\to T4$ transition. Coding therefore records *tier + modifier vector*.

#### 1.6.1 Why sustainment converts a modifier into a tier (T3-High)

A one-off deniable strike is an *event* — a $Shock_k$ that supplies activation energy against the underlying tier. A *sustained* deniable campaign is a *state* — an occupied posture with its own residence time and characteristic exits (escalate to attributed combat, or wind down). Sustainment is what earns T3-High its tier status: it converts transient barrier-suppression into a standing local cost-minimum that dyads park in for years (low attributable cost, real coercive value, no forced response). Below the sustainment threshold, deniable acts stay shocks; above it, they latch the tier.

### 1.7 The T3 Entry Condition (NEW — patron vs merchant)

"Selling weapons to $j$'s enemies" is **not sufficient** for T3. A UK arms dealer selling to *both* sides of a war is at conflict with neither. T3 requires support that is an **instrument of hostility toward $j$**, established through *observables*, not inferred motive:

1. **Sustained**, not a one-off shipment (chains the §1.6.1 sustainment logic).
2. **Selective** — directed at $j$'s adversaries and *not* $j$. Arming both sides is the merchant's signature and is logically incompatible with wanting either to win; it fails this test on pure observation. **Selectivity is the observable proxy for intent** — it restores the *link between* the hostile posture and the weapons that a mere stack of lower-tier friction cannot establish.
3. **Targeted** at $j$'s strategic disadvantage (systems/intel/training calibrated against $j$), not generic materiel that happens to reach the theater.
4. **Corroborated** by the surrounding relationship — diplomatic/economic friction (the "T1+T2" context) that *co-moves* with the arms flow over time.

> **Why not just "meets and exceeds T1+T2 + weapons"?** Because the stack tests for the *presence* of elements, not the *link between* them. A government can sit at T1+T2 with $j$ over an unrelated grievance while its firms sell $j$'s enemy weapons commercially — the stack is satisfied, but it is the merchant case the tier must exclude. Selectivity + targeting + co-movement supply the link without anyone inferring a state of mind. The arms dealer fails on selectivity (sells to both) regardless of the surrounding posture, which is exactly why he codes as not-T3 cleanly.

> **Why the skip tier does not solve the under-count.** A patron can enter directly at T3 (Cold-War proxy theaters with no prior sanctions relationship). Skip logic governs *transitions* of a dyad whose current tier is already assigned; it cannot place a dyad at T3 in the first instance. The under-count is a *classification* hole, patched by this entry condition, not by allocation.

### 1.8 Model Architecture Summary

```
INPUT CODING (CORE 13 + belief term + modifier vector, per directed dyad i->j)
├─ Path Dependency: Current Tier (X_t), Duration (D_k)   [memory — NOT in physics analogy]
├─ Structural/Military: Rivalry (Ω), Contiguity (Ξ), First-Mover Adv (FMA_{i->j}),
│                       Closing Window (-Ẇ_{i->j})
├─ Economic: Status-Quo Burden (was C_peace, per-actor), Exhaustion (W_x)
├─ Operational/Diplomatic: Off-Ramp Absence (ORA), Stalemate (Stal_t), Dip Capacity (Dip_cap)
├─ Catalysts/Environment: Kinetic Shock (Shock_k), Nuclear Gate (Nuc), Contagion (V_contagion)
├─ BELIEF (NEW): Ĉ_i(C_c) — actor i's estimate of counterpart cost field + uncertainty  [agency]
└─ MODIFIER VECTOR (NEW): attribution, integration depth, stakes, intent/selectivity (§1.6)

ENGINE — PER-ACTOR COST FIELD  C_i(j)        [replaces separate E_t / D_t / S_t]
├─ Occupancy cost: economic burden + blood/matériel burden − value extracted at tier j
├─ Status-quo floor: sanctions/severed interdependence RAISE C_i(k)
├─ Cost-of-war differential: severed interdependence LOWERS C_i(war tiers)
├─ Strategic term: forward-looking; climb now if it lowers expected future cost (−Ẇ)
└─ Belief coupling: cost depends on i's estimate of c's costs (deterrence/miscalc)

STAGE 1 — DIRECTION (cost gradients across activation barriers)
├─ Barriers B_{k→j} between tiers (ridge between valleys); modifiers suppress specific barriers
├─ U↑ ∝ [C(k) − C(k+1)] − B_{k→k+1} + shock energy
├─ U↓ ∝ [C(k) − C(k−1)] − B_{k→k−1}
├─ U0 ∝ persistence (current tier as local min; carries memory via D_k)
└─ softmax (= multinomial logit) → (P↓, P0, P↑)

STAGE 2 — ALLOCATION  (UNCHANGED from v22.0)
├─ Upward skip weights ω⁺ (catalytic, magnitude-of-jump)
└─ Downward skip weights ω⁻ (BIMODAL: step-down vs collapse = local vs global descent)

COMPOSITION  (UNCHANGED from v22.0)
└─ π_j = P↓·ω⁻_{kj} (j<k) ; P0 (j=k) ; P↑·ω⁺_{kj} (j>k)

RECONCILIATION (§3.6) — one-shot best response between the two actors' cost landscapes
```

---

## PART 2: INPUT VARIABLES & CODING GUIDANCE (THE CORE 13 + ADDITIONS)

The **Core 13** are inherited from v22.0 (ranges, directionality, symmetry). v24.0 reinterprets two, adds a belief input, and adds the modifier vector. Variables are bounded **[0,1]** except $V_{contagion}\in[-1,+1]$, $X_t\in\{0,1,2,3,\text{3H},4,5,6\}$, $D_k\in[0,\infty)$.

### 2.1 Path Dependency
- **CurrentTier ($X_t$)** — operational reality now; anchor for path dependency. Shared across both directed runs. Now includes **T3-High**.
- **Duration ($D_k$)** — time at current tier, months/10. $[0,\infty)$. Carries **memory** (no physical analog) and provides the **latch** for T3-High and the sustainment test for T3.

### 2.2 Structural & Military
- **Rivalry ($\Omega$)** — long-term structural enmity. [0,1]. *Symmetric.*
- **Contiguity ($\Xi$)** — shared border and territorial dispute. {0,0.5,1}. *Symmetric.*
- **First-Mover Advantage ($FMA_{i\to j}$) [DIRECTIONAL]** — tactical advantage to actor $i$ from striking $j$ first. [0,1].
- **Closing Window ($-\dot{W}_{i\to j}$) [DIRECTIONAL]** — adverse long-term power shift; **reinterpreted** as the driver of the cost field's forward-looking term (preventive logic), not a static escalation additive. [0,1].

### 2.3 Economic
- **Status-Quo Burden (was $C_{peace}$)** — **reinterpreted, per-actor.** Drop the uncodeable "relative to war" counterfactual (v22 §6.4). Code an *observable* burden of occupying the current tier: sanctions absorbed, lost trade, mobilization/internal-security costs already paid. Sanctions **raise** this floor; this is the mechanism by which a dyad "sanctioned into a corner" has lowered escalation resistance. [0,1].
- **Exhaustion ($W_x$)** — material/demographic/fiscal depletion from the current tier. [0,1]. *Symmetric.*

### 2.4 Operational & Diplomatic
- **Off-Ramp Absence ($ORA$)** — structural lack of viable exits. [0,1].
- **Stalemate ($Stal_t$)** — inability of either side to achieve breakthrough. [0,1].
- **Diplomatic Capacity ($Dip_{cap}$)** — mediator leverage, channels, de-escalation signaling. [0,1].

### 2.5 Catalysts & Environment
- **Kinetic Shock ($Shock_k$)** — recent fatality/strike/mobilization spikes. **Reinterpreted** as *activation energy* that pays a barrier. A one-off deniable strike enters here, not as a tier. [0,1].
- **Nuclear Gate ($Nuc$)** — weapon possession and arsenal instability; 0 if neither side is nuclear. [0,1]. *Symmetric.*
- **Bidirectional Contagion ($V_{contagion}$)** — regional spillover. [-1,+1]. Negative = peace contagion, positive = conflict contagion. *Symmetric.* **Lag ≥1 period; instrument with distance-to-regional-conflict, not local intensity, to avoid the reflection problem (§6.3).**

### 2.6 New Input — Belief Term
- **Belief about counterpart costs ($\hat{\mathcal{C}}_i(\mathcal{C}_c)$) [DIRECTIONAL]** — actor $i$'s *estimate* of counterpart $c$'s cost field, coded as a pair: a point estimate of how costly $c$ finds escalation/resistance, plus a confidence $[0,1]$. Deterrence, signaling, and **miscalculation** live here; wars frequently start in the gap between $\mathcal{C}_c$ and $\hat{\mathcal{C}}_i(\mathcal{C}_c)$. A confidently *wrong* belief (low uncertainty, large gap) is the most dangerous configuration. *Hardest input to code; flag uncertainty and let calibration discipline it (§6.1).*

### 2.7 New — Modifier Vector (per directed dyad)
Coded from observables; layered on the tier (§1.6).
- **Attribution** [0,1] — deniability of the harm. High → suppresses upward barrier; sustained → latches T3-High.
- **Integration depth** [0,1] [DIRECTIONAL] — patron's entanglement in a client's war (intelligence-sharing, targeting support, embedded personnel, integrated logistics, command coordination), *sustained*. Suppresses the patron's $T3\to T4$ barrier; gates patron de-escalation. Code from observables; the underlying reality is triadic (patron/client/target) and this is its dyadic compression (§6.2).
- **Stakes** [0,1] — existential vs peripheral; primarily carried by $\Omega\Xi$ into $V_i(\cdot)$.
- **Intent/selectivity** [0,1] [DIRECTIONAL] — observable proxy for hostile purpose: selective (one-sided) + targeted support that co-moves with the hostile posture. Gates T3 entry (§1.7).

---

## PART 3: MATHEMATICAL SPECIFICATION

### 3.0 The Cost Field (NEW engine)

For acting actor $i$ contemplating tier $j$ against counterpart $c$:

$$\mathcal{C}_i(j) = \underbrace{\beta_1 B^{econ}_i(j) + \beta_2 B^{blood}_i(j) - \beta_3 V_i(j)}_{\text{occupancy cost at } j} + \underbrace{\gamma\, \mathbb{E}\!\left[\mathcal{C}_i(\text{future}) \mid j\right]}_{\text{strategic / forward-looking}} + \underbrace{\delta\, \Phi\!\big(\hat{\mathcal{C}}_i(\mathcal{C}_c(j))\big)}_{\text{belief coupling}}$$

where $B^{econ}$ is the economic burden of occupying $j$, $B^{blood}$ the blood/matériel burden, $V_i(j)$ the value $i$ extracts at $j$ (territory, regime survival, prestige — carries $\Omega\Xi$ / stakes), $\gamma$ discounts the expected future cost conditional on $j$ (an adverse window $-\dot{W}$ raises $\mathbb{E}[\mathcal{C}_i \mid \text{stay low}]$, making a climb relatively cheaper), and $\Phi$ couples $i$'s cost to its *belief* about $c$ (believe $c$ folds cheaply → escalation looks cheap; believe $c$ fights to the death → costly).

**Encoded consequences:**
- Sanctions raise $B^{econ}_i(k)$ (floor under the status quo) *and* lower $B^{econ}_i(\text{war tiers})$ once interdependence is severed — the compounding effect a static $C_{peace}$ could not hold.
- Expressive/values sanctions: high $V_i(k)$ (sanctioner comfortable), no $V_i(\text{war})$ → war tiers stay expensive → persistence. Correctly separated from coercive-prelude.
- The global minimum is usually T0 (no blood, full commerce). The dyad does not fall there because of **barriers** (§3.2); this is why de-escalation is bimodal (§3.5.2) — collapse = a path opening over the ridge to the global min; step-down = local relaxation.
- **Modifiers act on barriers, not on $\mathcal{C}$ levels directly** (attribution and integration suppress specific $B_{k\to j}$); stakes act through $V_i(\cdot)$; intent gates whether the dyad is at T3 at all.

### 3.1 Composite Indices ($E_t, D_t, S_t$ — DEPRECATED to diagnostics)

The three v22 indices are retained as **reported diagnostics** for interpretability and back-comparison, but the direction stage no longer consumes them — it consumes cost gradients (§3.2). For reference, the v22 forms (with the $\Omega\Xi$ interaction) were:

**Escalation Pressure ($E_t$):** $\;\text{clip}(\alpha_1\Omega + \alpha_2\Xi + \alpha_3 FMA_{i\to j} + \alpha_4(-\dot W_{i\to j}) + \alpha_5 C_{peace} + \alpha_6 V_{contagion} + \alpha_7(\Omega\cdot\Xi),\,0,1)$
**De-Escalation Capacity ($D_t$):** $\;\text{clip}(\theta_1 W_x + \theta_2 Dip_{cap} + \theta_3(1-C_{peace}) - \theta_4 V_{contagion},\,0,1)$
**Persistence Lock ($S_t$):** $\;\text{clip}(\rho_1 Stal_t + \rho_2 ORA + \rho_3 D_k + \rho_4 V_{contagion},\,0,1)$

> The $\Omega\Xi$ interaction (the single most-supported structural interaction in the conflict literature) is **preserved** by entering $V_i(\cdot)$ in the cost field: high rivalry × active territorial dispute raises the value of contested tiers and lowers war's relative cost. "The issue staying small" = low $\Omega\Xi$ → war tiers carry no compensating value → persistence.

> **Calibration note (carried over):** when estimation begins, replace any residual `clip(linear,0,1)` with a sigmoid composite $\sigma(\cdot)$ for smooth, naturally bounded indices.

### 3.2 Movement Scores — Cost Gradients with Barriers (REVISED)

Note the v23→v24 change carried from v22: the escalation skip term that once lived in $U^\uparrow$ remains **removed** from the direction stage; all skip/magnitude logic is in allocation (§3.5). The direction stage now reads gradients of the cost field, each penalized by the activation barrier for crossing into the adjacent tier:

$$U_k^{\uparrow} = \big[\mathcal{C}_i(k) - \mathcal{C}_i(k+1)\big] - B_{k\to k+1} + u_Z\, Shock_k$$
$$U_k^{0} = a_k^{0} + r_D\, D_k \qquad\text{(persistence: current tier as local minimum; carries memory)}$$
$$U_k^{\downarrow} = \big[\mathcal{C}_i(k) - \mathcal{C}_i(k-1)\big] - B_{k\to k-1}$$

- $B_{k\to j}\ge 0$ is the **activation barrier** (the ridge between valleys): mobilization, the first irreversible strike, the political Rubicon. Without it the model predicts instantaneous escalation whenever a higher tier is cheaper and instantaneous collapse whenever a lower tier is cheaper — both empirically false.
- $Shock_k$ supplies **activation energy** over a ridge into a lower-cost-but-blocked tier — a more coherent role than v22's bolt-on additive.
- **Modifiers suppress specific barriers:** high attribution lowers the $\to$T3-High / upward barriers; high integration depth lowers the patron's $T3\to T4$ barrier.
- $D_k$ carries **memory** — persistence tendency grows with time-in-tier independent of cost.

### 3.3 Direction Probabilities (Softmax) — re-derived, UNCHANGED in form

$$Z = \exp(U_k^\downarrow) + \exp(U_k^0) + \exp(U_k^\uparrow)$$
$$P_\downarrow = \frac{\exp(U_k^\downarrow)}{Z},\quad P_0 = \frac{\exp(U_k^0)}{Z},\quad P_\uparrow = \frac{\exp(U_k^\uparrow)}{Z}$$

> **Provenance correction.** This is the **multinomial logit** — the choice probability of a utility-maximizing agent whose payoffs ($-U$) carry i.i.d. extreme-value noise — *not* a Boltzmann distribution. The forms are algebraically identical (which is why the physics metaphor produced workable math), but the discrete-choice reading is correct because it admits agency and an error structure that "energy levels" do not. A temperature $\tau$ on $U$ may tune decisiveness vs noise in calibration.

**Boundary constraints (UNCHANGED):**
- $P_\downarrow(k{=}0)=0$ (cannot de-escalate below peace); renormalize over $\{P_0,P_\uparrow\}$.
- $P_\uparrow(k{=}6)=0$ (no tier above nuclear); renormalize over $\{P_\downarrow,P_0\}$.
- "Adjacent" follows the ordered list T0, T1, T2, T3, T3-High, T4, T5, T6.

### 3.4 Composition Equation (THE KEY ADDITION — UNCHANGED from v22.0)

$$\boxed{\;\pi_{kj} = \begin{cases} P_\downarrow \cdot \omega^-_{kj} & j < k \\[4pt] P_0 & j = k \\[4pt] P_\uparrow \cdot \omega^+_{kj} & j > k \end{cases}\;}$$

**Mass conservation.** Since $\sum_{j<k}\omega^-_{kj}=1$ and $\sum_{j>k}\omega^+_{kj}=1$:
$$\sum_{j}\pi_{kj} = P_\downarrow\underbrace{\sum_{j<k}\omega^-_{kj}}_{=1} + P_0 + P_\uparrow\underbrace{\sum_{j>k}\omega^+_{kj}}_{=1} = P_\downarrow + P_0 + P_\uparrow = 1.$$

Persistence ($j=k$) is a single undivided destination, regardless of how many tiers lie above or below.

### 3.5 Allocation Stage — Skip Functions (UNCHANGED from v22.0, reinterpreted)

#### 3.5.1 Upward Allocation $\omega^+$ (Catalytic Skip)

Skip *propensity* (renamed from the misleading v21 "Skip Barrier" — it *adds* to skip likelihood):
$$\Sigma^{\uparrow}_{i\to j} = (FMA_{i\to j})^{\eta_\phi}\,(-\dot W_{i\to j})^{\eta_w}\,(ORA)^{\eta_r}\,(1 - Nuc^{\eta_n})$$
The $(1-Nuc^{\eta_n})$ factor encodes that nuclear dyads are *less* prone to conventional skip-escalation (deliberate/deterred); when $Nuc=0$ it is 1. Consistent with — not contradicted by — the separate hard gate blocking entry into T6 (§3.7).

Weights combine distance-decay with skip propensity:
$$\omega^+_{kj} \propto \exp\!\big[-\lambda^+_k\,(j-k-1)\,(1-\Sigma^\uparrow)\big]\cdot G^+_{kj},\qquad j>k$$
normalized so $\sum_{j>k}\omega^+_{kj}=1$. $\Sigma^\uparrow\to0$ → steep decay, mass on $k+1$; $\Sigma^\uparrow\to1$ → mass spreads to distant tiers. **Reinterpretation:** $\Sigma^\uparrow$ is the degree to which one catalyst flattens several barriers on a multi-tier path at once.

#### 3.5.2 Downward Allocation $\omega^-$ (Bimodal: Step-Down vs Collapse)

De-escalation is **not** the mirror of escalation; it is bimodal:
$$\omega^-_{kj} \propto \underbrace{(1-\kappa)\exp\!\big[-\lambda^-_k(k-j-1)\big]}_{\text{step-down mode}} + \underbrace{\kappa\,C_{kj}}_{\text{collapse mode}},\qquad j<k$$
normalized so $\sum_{j<k}\omega^-_{kj}=1$, where $\lambda^-_k$ governs step-down decay, $C_{kj}$ is the collapse kernel (mass on floor tiers $j\in\{0,1\}$), and the collapse weight is
$$\kappa = \sigma\!\big(c_0 + c_W W_x + c_{Dip}Dip_{cap} - c_{Stal}Stal_t - c_{ORA}ORA\big).$$

> **Reinterpretation (payoff of the cost-field framing):** step-down = **local descent** of the cost field; collapse = **a path opening over the ridge to the global minimum** (regime change/surrender removes the barriers between the current tier and the floor). v22 needed bimodality empirically; v24 derives *why* it must exist.

### 3.6 Reconciling the Two Directed Runs — as a Game (REVISED)

The two directed runs are the two players' cost landscapes over the shared tier $k$. The relationship's next move is the **one-shot best-response** between them; the v22 max/min rule is retained as the default *reporting* approximation:

- **Escalation:** $P_\uparrow^{\text{rel}} = \max(P_\uparrow^{A\to B}, P_\uparrow^{B\to A})$ — either actor finding a higher tier cheaper can climb; use the $\omega^+$ of the maximizing direction. *(Escalation is unilaterally enforceable.)*
- **De-escalation:** $P_\downarrow^{\text{rel}} = \min(P_\downarrow^{A\to B}, P_\downarrow^{B\to A})$ — winding down requires *both* landscapes to favor it; the more committed actor gates the step-down. *(De-escalation requires mutual consent — and integration depth can be what makes a patron the gating actor.)*
- **Persistence:** residual $P_0^{\text{rel}} = 1 - P_\uparrow^{\text{rel}} - P_\downarrow^{\text{rel}}$ (clip at 0, renormalize on overshoot).

> War is the configuration where the two landscapes' minima sit at different tiers and neither belief term corrects the disagreement before a barrier is crossed. This reporting rule is a default approximation to a true equilibrium computation; flag it for calibration alongside the coefficients and the belief term.

### 3.7 Hard Gates (Destination Constraints — UNCHANGED from v22.0)

| Gate | Rule |
|------|------|
| Nuclear floor | If $Nuc=0$, set $\omega^+_{k,6}=0$ (T6 unreachable); renormalize remaining upward weights. |
| Adjacent baseline | $G^\pm$ default gate = 1.00 for the adjacent tier (per the ordered list incl. T3-High). |
| Two-tier skip | Default gate = 0.35. |
| Three-tier skip | Default gate = 0.10. |
| Larger skip | Default gate = 0.02. |

The nuclear gate (blocking *entry into* T6) is logically separate from the $(1-Nuc^{\eta_n})$ term in $\Sigma^\uparrow$ (down-weighting conventional skipping *by* nuclear dyads). Both can hold simultaneously.

### 3.8 Default Operational Coefficients (PRIORS, not calibrated)

v22 priors carry over for retained terms. **New families are explicitly TBD and must not be treated as defaults:** cost-field weights $\beta_{1,2,3}$, discount $\gamma$, belief coupling $\delta$ and the shape of $\Phi$, the activation barriers $B_{k\to j}$ (one per ordered-adjacent transition), and the modifier→barrier suppression coefficients. The model now has *more* free parameters than v22 — the price of fidelity.

| Param | Default | Param | Default | Param | Default |
|-------|---------|-------|---------|-------|---------|
| $a^0$ | 0.20 | $r_D$ | 0.03 | $u_Z$ | 0.55 |
| $\lambda^+_k$ | 1.20 | $\lambda^-_k$ | 1.20 | $\alpha_7$ ($\Omega\Xi$, diag.) | 0.50 |
| $\beta_{1,2,3}$ | TBD | $\gamma$ | TBD | $\delta$ | TBD |
| $B_{k\to j}$ | TBD | modifier→$B$ suppression | TBD | $\kappa$ params $c_\bullet$ | TBD |

---

## PART 4: WORKED EXAMPLE (Cost Field → Gradient → Composition)

Sanctioned dyad $(A\rightarrow B)$ at **T2**, coercive-prelude type (high stakes). Illustrative cost-field values for actor $A$ (lower = cheaper to occupy):

| Tier $j$ | $\mathcal{C}_A(j)$ | Comment |
|----------|--------------------|---------|
| T1 | 0.55 | de-escalating concedes the dispute; costly in lost leverage |
| **T2 (now)** | **0.60** | sanctions absorbed; status-quo floor raised — staying is expensive |
| T3 | 0.50 | sustained, selective proxy pressure cheaper than open sanctions stalemate |
| T3-High | 0.48 | sustained deniable campaign: low attributable cost, real pressure |

Barriers (illustrative): $B_{T2\to T3}=0.05$, $B_{T2\to T1}=0.20$ (conceding is politically hard).

**Stage 1 — gradients:**
$$U^\uparrow = [\mathcal{C}_A(2)-\mathcal{C}_A(3)] - B_{2\to3} + u_Z Shock_k = (0.60-0.50) - 0.05 + 0.55(0.20) = 0.16$$
$$U^\downarrow = [\mathcal{C}_A(2)-\mathcal{C}_A(1)] - B_{2\to1} = (0.60-0.55) - 0.20 = -0.15$$
$$U^0 = a_2^0 + r_D D_k = 0.20 + 0.03(0.50) = 0.215$$

Softmax → approximately $P_\downarrow=0.26$, $P_0=0.38$, $P_\uparrow=0.36$. The raised status-quo floor and the cheaper proxy/gray-zone tiers tilt this dyad toward escalation pressure — but persistence still leads, because the climb still costs and de-escalation is barred by the political cost of conceding.

**Contrast — expressive/values sanctions** (same tier, low stakes): high $V_A(\text{T2})$ → $\mathcal{C}_A(2)\approx0.15$; war tiers carry no compensating value → $\mathcal{C}_A(\text{T3}+)\gg\mathcal{C}_A(2)$. Gradients point down/flat, barriers irrelevant, dyad parks at persistence. The two T2 populations v22 conflated are now separated.

**Stage 2 — allocation** (illustrative, for a dyad at T4): $\Sigma^\uparrow=0.30$ → $\omega^+\approx\{T5:0.80,T6:0.20\}$, gated to $\{T5:1.0\}$ if $Nuc=0$. With $\kappa=0.25$: $\omega^-\approx\{T3\text{H}:0.55, T3:0.20, T2:0.15, \text{floor}:0.10\}$ — non-zero floor mass from the collapse component.

**Composition** then proceeds exactly per §3.4. As in v22, a T4 dyad with $Nuc=0$ yields a vector most-likely to persist at T4, with escalation to T5 the leading move and a small collapse-toward-floor mass.

---

## PART 5: IMPLEMENTATION WORKFLOW

1. **Assign current tier $X_t$** from operational evidence (shared). Apply the T3 entry condition (§1.7) and the T3-High sustainment latch (§1.6.1); use modifiers, not new tiers, for off-axis facts.
2. **Choose a direction** $(i\rightarrow j)$; code $FMA_{i\to j}$, $-\dot W_{i\to j}$, the **belief term** $\hat{\mathcal{C}}_i(\mathcal{C}_c)$ + uncertainty, and the **directional modifiers** (integration depth, intent/selectivity).
3. **Code symmetric variables** $\Omega, \Xi, W_x, ORA, Stal_t, Dip_{cap}, Shock_k, Nuc, V_{contagion}$ (lagged), and the **per-actor Status-Quo Burden** (replacing the old $C_{peace}$ counterfactual).
4. **Build the cost field** $\mathcal{C}_i(j)$ (occupancy + strategic + belief coupling); apply modifier→barrier suppression.
5. **Stage 1:** cost-gradient movement scores with activation barriers → softmax → $(P_\downarrow,P_0,P_\uparrow)$; apply boundary constraints.
6. **Stage 2:** compute $\Sigma^\uparrow$ and $\kappa$; build $\omega^+$ and bimodal $\omega^-$; apply hard gates.
7. **Compose** via §3.4 to get $\pi$.
8. **Repeat for the reverse direction**, then reconcile (§3.6) as a best-response between the two cost landscapes.
9. **Report** the cost fields $\mathcal{C}_A(\cdot),\mathcal{C}_B(\cdot)$, barriers used, the modifier vector, the belief gap $|\mathcal{C}_c - \hat{\mathcal{C}}_i(\mathcal{C}_c)|$, both directed $\pi$ vectors, the reconciled distribution, and (for compatibility) the deprecated $E_t,D_t,S_t$ diagnostics.

---

## PART 6: VALIDATION, LIMITATIONS & OPEN ISSUES

### 6.1 What "Calibration" Requires Before Any Production Claim
- Point estimates **and standard errors** for all coefficients — now including cost-field weights, discount $\gamma$, belief coupling $\delta$, **every activation barrier $B_{k\to j}$**, and the modifier→barrier suppression terms — via penalized MLE or Bayesian estimation on a training set (MIDs 1990–2015; UCDP-dyadic for proxy / T3-High).
- **Out-of-sample** Brier score, log-loss, AUROC/AUPR by tier, with special attention to rare tiers (T5, T6) and **T3-High** (does the gray-zone cut earn its place, or merely split T3's mass without improving fit?).
- **Inter-coder reliability** (Krippendorff's $\alpha$ / Cohen's $\kappa$) for all inputs — expecting the **belief term** and **integration depth** to score worst, possibly reduced to coarse ordinals until better data exists.
- **Barrier identification:** barriers and cost levels are partially confounded (a high barrier and a high destination cost both suppress a transition). Separate them by exploiting transitions where shocks are observed to "pay" the barrier.
- Until these exist, every coefficient is an intelligent guess. Run against 1990–2020 out-of-sample MIDs and let the data decide whether $u_Z$ is really 0.55.

### 6.2 Retained Limitations
- Rare-event tails (T6) remain hard to calibrate.
- $V_{contagion}$ requires regional network analysis to score well.
- Multi-actor wars exceed a dyadic (even directed-dyadic) simplification. **Integration depth is the dyadic model's compression of an inherently triadic (patron/client/target) reality** — a reasonable approximation, but labeled as one.
- The belief term assumes a single representative decision-maker per actor; coalition/domestic politics that split the cost field are not represented.

### 6.3 Contagion Endogeneity (Manski Reflection)
$V_{contagion}$ risks circularity: a dyad's own war inflates regional violence, which feeds back as "contagion." Mitigation: lag ≥1 period and instrument with geographic distance to regional conflict, not local intensity. Unaddressed, it manufactures false precision.

### 6.4 Status-Quo Burden vs Cost-of-War (was $C_{peace}$ Measurement)
v22's $C_{peace}$ smuggled an uncodeable war-counterfactual. v24 splits it: an observable **Status-Quo Burden** feeds $\mathcal{C}_i(k)$, while the cost of war is an explicit, separate occupancy cost at the war tiers. The remaining hard problem is that the **forward-looking term** $\mathbb{E}[\mathcal{C}_i(\text{future})\mid j]$ reintroduces a counterfactual by construction — the price of representing preventive logic. Code it as a coarse "is the trend adverse?" signal driven by $-\dot W$, not a precise expectation.

### 6.5 Structural Incompleteness (Regime Type)
Regime type is still excluded; the democratic-peace finding is **contested** and substantially absorbed by $\Xi$ and $V_{contagion}$. If added, add it as a *testable* term that must improve out-of-sample fit *beyond* $\Xi$, rather than assuming it must.

### 6.6 The Physics Analogy — Explicit Caveat (NEW)
The physics metaphor (energy levels, Boltzmann) was a good **generative** source — it produced the softmax, the landscape, and the barriers, all general optimization-under-uncertainty machinery. It is a bad **governing** theory, because conflict has three properties physics lacks: **memory** ($D_k$, path dependence), **agency** (forward-looking action, $-\dot W$, the strategic term, beliefs), and **a second player** (two coupled cost fields, §3.6). Wherever the model still feels like it is fighting its framework, suspect a leftover physical assumption. The governing theory is a **Markov game with cost-shaped transition probabilities**, not quantum mechanics.

### 6.7 Falsifiable Predictions the Model Now Commits To (NEW)
- **Expressive-sanctions dyads** (low $\Omega\Xi$, sanctioner-comfortable) must show overwhelming persistence mass. If priors don't, priors are wrong.
- **Sanctioned-into-a-corner dyads** (high $\Omega\Xi$, high Status-Quo Burden, severed interdependence) should show *elevated* escalation vs comparable un-sanctioned high-stakes dyads. The 2014→2022 Russia–Ukraine progression is the motivating (not confirming) case.
- **Confidently-wrong belief configurations** (low uncertainty, large $|\mathcal{C}_c - \hat{\mathcal{C}}_i(\mathcal{C}_c)|$) should predict miscalculation-driven escalation the cost fields alone would not.
- **T3-High** should improve out-of-sample fit over a T3-only model on post-2007 dyads, or be removed.
- **Deeply-integrated proxy dyads** should show materially higher $T3\to T4$ transition rates than shallow ones, controlling for $\Omega\Xi$.
- **The merchant test:** dyads where support is *non-selective* (arms to both sides) should *not* code as T3 and should not show proxy-war transition dynamics.

### 6.8 Proper Use
✓ Early warning, scenario comparison, sensitivity analysis.
✗ Deterministic forecasting or claims of point certainty.

---

## PART 7: APPENDIX — VARIABLE SUMMARY

| Variable | Name | Type | Range | Directional? | Status |
|----------|------|------|-------|--------------|--------|
| $X_t$ | Current Tier | State | {0,1,2,3,3H,4,5,6} | shared | revised (T3-High) |
| $D_k$ | Duration | State (memory) | [0,∞) | shared | unchanged; latches T3-High |
| $\Omega$ | Rivalry | Structural | [0,1] | symmetric | unchanged |
| $\Xi$ | Contiguity | Structural | {0,0.5,1} | symmetric | unchanged |
| $FMA_{i\to j}$ | First-Mover Adv. | Military | [0,1] | directional | unchanged |
| $-\dot W_{i\to j}$ | Closing Window | Military | [0,1] | directional | reinterpreted (strategic term) |
| Status-Quo Burden | (was $C_{peace}$) | Economic | [0,1] | per-actor | revised |
| $W_x$ | Exhaustion | Economic | [0,1] | symmetric | unchanged |
| $ORA$ | Off-Ramp Absence | Diplomatic | [0,1] | symmetric | unchanged |
| $Stal_t$ | Stalemate | Operational | [0,1] | symmetric | unchanged |
| $Dip_{cap}$ | Diplomatic Cap. | Diplomatic | [0,1] | symmetric | unchanged |
| $Shock_k$ | Kinetic Shock | Catalyst (activation energy) | [0,1] | symmetric | reinterpreted |
| $V_{contagion}$ | Regional Contagion | Geopolitical | [-1,+1] | symmetric | unchanged |
| $Nuc$ | Nuclear Gate | Gatekeeper | [0,1] | symmetric | unchanged |
| $\hat{\mathcal{C}}_i(\mathcal{C}_c)$ | Belief about counterpart costs | Strategic (agency) | est.+conf. | directional | **NEW** |
| Attribution | Modifier axis | Modifier | [0,1] | per-dyad | **NEW** |
| Integration depth | Modifier axis | Modifier | [0,1] | directional | **NEW** |
| Stakes | Modifier axis (via $\Omega\Xi$) | Modifier | [0,1] | symmetric | **NEW (named)** |
| Intent/selectivity | Modifier axis (T3 gate) | Modifier | [0,1] | directional | **NEW** |
| $\mathcal{C}_i(j)$ | Per-actor cost field | Derived engine | ℝ per tier | per-actor | **NEW** |
| $B_{k\to j}$ | Activation barrier | Derived/transition | [0,∞) | per transition | **NEW** |

**Version 24.0 | Specification Phase — Awaiting Calibration | Stochastic-Game Reframing, Cost-Landscape Engine, Modifier Axes & T3 Refinement | May 2026**
