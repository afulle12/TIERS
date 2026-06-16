# Unified Equation of Interstate War (Directed-Dyad Variant) v26.0

## Complete Specification with Full Context & Definitions

**Version:** 26.0 (Status-Quo-Biased Direction Stage; T3-High Folded into an Escalation-Risk Factor; Capability/Reach Gate on Strategic War; Graceful-Degradation Architecture; Nested-Model Family; Public/Private Information Layering; IHL-Anchored Strategic WMD Gate)
**Status:** Specification Phase — Awaiting Empirical Calibration (NOT production-validated)
**Last Updated:** June 2026

---

## PART 0: VERSION HISTORY

### v26.0 Changes from v25.1

v25.1 established the IHL-anchored Strategic WMD gate on top of v25.0's graceful-degradation architecture and nested-model family. v26.0 keeps all of that **unchanged in substance** and makes three targeted revisions, all motivated by a single observed pathology: **the v25.x direction stage over-weighted de-escalation in dyads that historically persisted or escalated.**

| Element | v25.1 | v26.0 |
| --- | --- | --- |
| **Direction stage / status-quo bias** | Down-barrier $B_{k\to k-1}$ a flat TBD constant; the structurally-positive down-gradient leaked over it, so falling escalation pressure read as de-escalation rather than as return-to-status-quo | **Status-quo-biased down-barrier:** $B_{k\to k-1}$ given a tier- and duration-dependent structural floor (lock-in), and de-escalation made an *earned* event via an additive **de-escalation activation term** $u_D\,DeEsc_k$ in $U^\downarrow$ — the exact mirror of $u_Z\,Shock_k$ in $U^\uparrow$. Absent enablers, the floor holds and persistence anchors. |
| **T3-High** | A separate tier on the ordered ladder (attribution-suppressed, sustained deniable campaign) | **Removed as a tier.** Ordered list collapses to T0–T6. Its distinguishing content is reconstructed as an **escalation-risk factor on the T3→T4 transition:** the interaction **Attribution × Duration**. Plain duration still raises persistence (lock-in); duration *conditional on deniability* raises the T3→T4 escalation hazard. |
| **Strategic-war feasibility** | No reachability gate on conventional war; contiguity/FMA only dampened pressure continuously | **New Capability/Reach gate $Cap_{i\to j}$ on T5.** T5 is reachable iff the dyad is contiguous OR at least one side can inflict considerable, sustainable damage on the other. T4 remains ungated (any state can land *some* attributed blow). $WMD>0 \Rightarrow Cap\ge\tau$ keeps the two gates consistent; T6 needs no separate reach gate. |
| **All other elements** | — | **UNCHANGED from v25.1** (engine, tiers T0–T6, Core 13, composition, allocation, WMD gate, degradation layer, public/private members). |

**Why these matter.**

1. **Status-quo bias.** The engine's own design note — "the global minimum is usually T0 but barriers prevent the fall" — means the down-gradient $\mathcal{C}_i(k)-\mathcal{C}_i(k-1)$ is positive almost everywhere. With the down-barrier a flat undertuned constant, the field drifted toward peace by default, and a drop in escalation pressure was mis-read as de-escalation. The fix makes the down-barrier the *mechanism* of status-quo bias: sized to absorb the typical positive down-gradient, growing with tier and dwell time, and paid down only by genuine de-escalation enablers (exhaustion, diplomatic capacity, a real off-ramp). Escalation must still be fired by $Shock_k$ and the cost gradient; de-escalation must now likewise be earned. Falling escalation pressure now returns mass to **persistence**, not to de-escalation.

2. **T3-High merge.** v25.1's §6.7 already required T3-High to beat T3-only out-of-sample "or be removed," and flagged its inter-coder reliability as poor. v26.0 removes the tier and carries its information in two variables already in the model — the attribution modifier and duration — combined as an interaction. This is more parsimonious and resolves the sign tension introduced by the new lock-in: plain duration is stabilizing, duration×deniability is escalatory.

3. **Capability/Reach gate.** Rivalry and stakes could previously drive nonzero $P_\uparrow$ into strategic war for dyads that physically cannot wage one. Capping **T5** (not T4) matches the tier definitions: landing *some* attributed blow is now nearly universal (cheap, asymmetric means — e.g. smuggled-drone strikes deep inside a far larger adversary), but *nationwide, sustained, multi-front* war has a real material floor.

---

### v25.1 Changes from v25.0

v25.0 established the graceful-degradation architecture and nested-model family. v25.1 kept all of that unchanged and replaced the binary, weapon-class **Nuclear Gate ($Nuc$)** with the consequence-defined, physics-grounded **Strategic WMD Gate ($WMD$)**, anchored to the IHL indiscriminate-weapons standard (AP I Arts. 35–36, 51(4)): a weapon clears the gate only if its effects are structurally unlimitable *and* of strategic scale. Tactical WMD use was routed explicitly as a high-magnitude $Shock_k$ within T5.

### v25.0 Changes from v24.0

v24.0 established the cost-field engine, the modifier axes, the belief term, and the T3-High tier. v25.0 kept all of that unchanged and added the structural commitment that **the model is a nested family, not a single monolith.** Every advanced term has a documented null value that reduces the model to a strictly simpler, still-valid member; missing inputs degrade the model down the family rather than breaking it. v25.0 also formalized public vs private as two coding protocols over one engine, added the COVERAGE VECTOR output, and made fail-soft the default with fail-loud configurable for high-salience variables.

---

## PART 1: OVERVIEW & ARCHITECTURE

### 1.1 What This Model Does

The Unified Equation of Interstate War (UIW) v26.0 is a **directed-dyad stochastic-game model** for estimating next-period interstate conflict escalation, persistence, and de-escalation. For an ordered pair $(i \rightarrow j)$ — "the prospect of $i$ escalating against $j$" — it estimates the full distribution over next-period tiers. Each actor is a forward-looking agent minimizing a per-actor cost field over a *shared* state variable (the relationship tier), under uncertainty about the other's costs.

The model is **two-stage** plus a reframed engine:

0. **Cost field (engine).** For acting agent $i$, evaluate the cost-to-occupy each reachable tier, $\mathcal{C}_i(j)$ — occupancy cost + a forward-looking strategic term + a belief coupling to the counterpart's costs.
1. **Direction stage.** Movement scores are *cost gradients* between the current tier and adjacent tiers, each penalized by an inter-tier activation barrier. The barriers are **status-quo-biased**: the upward barrier is overcome by the cost gradient plus $Shock_k$; the downward barrier carries a tier/duration-dependent structural floor and is paid down only by an explicit de-escalation activation signal $DeEsc_k$. Softmax → $(P_\downarrow, P_0, P_\uparrow)$.
2. **Allocation stage.** Conditional on a direction, distribute that direction's mass across reachable destination tiers via skip weights $\omega^+$ (upward, catalytic) and $\omega^-$ (downward, bimodal), subject to the hard gates (WMD on T6, Capability/Reach on T5).

The output is the composition $\pi_{kj}(t) = \text{Pr}(\text{next tier} = j \mid \text{current tier} = k, \text{ inputs at } t)$, a vector over the ordered tier list summing to 1, **accompanied by a coverage vector** (§1.9) describing how much of the machinery was actually fed.

**Recommended forecast interval:** 30 days. See §1.5 for the slow-variable caveat.

### 1.2 Escalation Taxonomy (tiers are cuts on a continuum)

Tiers are **analyst-imposed cuts on a continuum**, not quantized states. Each cut must earn its place empirically (§6.7). **As of v26.0 there is no T3-High tier** (§0); its content lives in the Attribution×Duration escalation factor (§1.6.1).

| **Tier** | **Name** | **Military Activity** | **Operational Definition** | **Examples** |
| --- | --- | --- | --- | --- |
| **T0** | Peace | None | No military activity or threat thereof | US–Canada 2020 |
| **T1** | Diplomatic Crisis | None | Formal friction: protests, recalls, ultimatums, UN votes | US–Iran 2019 |
| **T2** | Economic Coercion | None | Active sanctions, trade restrictions, financial exclusion | Russia–West 2014 |
| **T3** | Proxy/Indirect Military | Passive support only | *Sustained, selective* material support to $j$'s adversaries, directed at $j$; $i$ not in direct combat. See §1.7. A *sustained, deniable* T3 campaign carries elevated T3→T4 escalation risk via the Attribution×Duration factor (§1.6.1) — it is no longer a separate tier. | Iran funding Hezbollah; Israel–Iran shadow war; pre-2022 Donbas |
| **T4** | Limited Direct Military | Acknowledged direct combat | Open, attributed exchange of fire between $i$ and $j$ forces. **Ungated for reach:** any actor able to land *some* credible attributed blow can reach T4. | USS *Reuben James* 1941; smuggled-drone strikes on an adversary's strategic targets |
| **T5** | Strategic War | Expansive conventional | Nationwide / multi-front warfare, sustained campaigns. **Reach-gated (§3.7):** reachable only if the dyad is contiguous OR at least one side can inflict considerable, sustainable damage on the other. | Ukraine–Russia 2022+ |
| **T6** | Strategic WMD Employment | Strategic-scale WMD deployed | Deliberate use of a weapon meeting **both** IHL-derived tests: (1) effects unlimitable by physical nature, regardless of aim precision; (2) effect footprint sufficient to threaten the target state's stability, territorial integrity, or national survival. The threshold is *strategic consequence*, not weapon class. Tactical/localized WMD use is a high-magnitude $Shock_k$ within T5, not T6. | Nuclear detonation on an inhabited target; engineered pandemic-scale biological release directed at a state |

> **Ordered list for "adjacency":** T0, T1, T2, T3, T4, T5, T6. Adjacency is now single steps; the v25.x T3-High slot is gone, so T3→T4 is an adjacent transition (recompute skip distances accordingly — §3.7).

> **Note on T2 (two populations).** Coercive-prelude sanctions (live dispute, force conceivable) vs expressive/values sanctions (no security stake). The tiers do not distinguish them — the **structural variables and the stakes modifier do** — and the status-quo-biased direction stage should now keep expressive-sanctions dyads in overwhelming persistence (§6.7).

> **T4/T5 boundary is a feasibility boundary as well as a magnitude boundary.** A dyad can sit at T4 (limited attributed combat) yet be unable to reach T5 because neither side can wage sustained strategic war against the other (§3.7).

> **T5/T6 boundary is consequence-defined, not weapon-class-defined.** A nuclear weapon crossing this boundary is almost automatic. A biological/chemical weapon crosses it only if the anticipated effect is of comparable scale. A large conventional strike, however devastating, remains T5. See §2.5.

### 1.3 Tier Assignment Rule

Assign the **highest** tier fully supported by operational evidence, descending from T6. Do not mix diplomatic language with operational coding. Caveats: (a) a dyad genuinely between tiers is coded at the nearest tier *and* flagged with the relevant modifier; (b) T3 carries the sustainment and selectivity entry conditions (§1.7), and a sustained deniable T3 is flagged with its Attribution and Duration values so the escalation factor (§1.6.1) is active; (c) **before assigning T5, verify the Capability/Reach gate (§3.7);** (d) WMD use must clear both IHL tests before T6 is assigned — tactical WMD use that fails either test is coded as a $Shock_k$ event at T5.

### 1.4 Directed-Dyad Convention

A dyad is an **ordered pair** $(i \rightarrow j)$. Run twice. Current tier $k$ is shared; directional variables carry the acting actor's subscript; symmetric variables take the same value both ways. The two runs are the **two players' cost landscapes over the same state variable.** War is what happens when those landscapes disagree about where the minimum lies and no belief correction intervenes before a barrier is crossed (§3.6). The Capability/Reach gate is evaluated **once at the dyad level** (it is a property of the pair) and applied to both runs (§3.7).

### 1.5 Forecast-Interval Caveat

Slow structural inputs ($\Omega, \Xi, Cap, -\dot{W}$) are near-constant over 30 days; period-to-period variation comes from fast inputs ($Shock_k$, $DeEsc_k$, $Dip_{cap}$, $V_{contagion}$, belief updates). Slow variables set the baseline landscape and the reachable-tier envelope; fast variables provide timing; shocks supply activation energy upward and de-escalation enablers supply it downward.

### 1.6 The Modifier-Axes Structure

| Modifier axis | What it captures | Where it acts | Canonical case |
| --- | --- | --- | --- |
| **Attribution** | Deniability of harm | Suppresses upward barrier $B$; **sustained (× Duration) → raises T3→T4 escalation hazard** (§1.6.1) | Israel–Iran shadow war |
| **Integration depth** | Patron entanglement short of combat | Suppresses patron's $T3\to T4$ barrier; gates patron de-escalation | US–Ukraine vs Russia |
| **Stakes** | Existential vs peripheral | Enters $V_i(\cdot)$ via $\Omega\Xi$; separates expressive from coercive-prelude T2 | Values-sanctions vs prelude |
| **Intent/selectivity** | Hostile-directed vs indifferent commerce | T3 entry gate (§1.7) | Arms dealer selling to both sides |

A tier label alone is not a state. Coding records *tier + modifier vector*.

#### 1.6.1 Attribution × Duration as an escalation-risk factor (former T3-High)

v25.x represented a sustained deniable campaign as a *separate tier* (T3-High) on the argument that sustainment converts a transient barrier-suppression into a standing local cost-minimum. v26.0 drops the tier and represents the same phenomenon as an **escalation-risk contribution to the T3→T4 transition**, built from the interaction of the attribution modifier and dwell time:

$$
\Delta\text{Esc}_{T3\to T4} = u_A \cdot \big(\text{Attribution}\cdot D_{k}\big),\qquad \text{entering } U^{\uparrow}\text{ at } k=\text{T3 (§3.2).}
$$

**The sign logic, and why it does not collide with the lock-in (§1.6.3).** Plain duration is *stabilizing* — it raises persistence ($r_D D_k$ in $U^0$) and the down-barrier floor ($b_{dur}D_k$). Duration *multiplied by deniability* is *escalatory*. A sustained, deniable campaign accumulates provocations and erodes the target's tolerance, raising the hazard of a triggering incident that tips T3→T4; a sustained but fully *attributable* low-level standoff simply locks in. Coding the effect as the interaction lets both behaviors coexist: the deniable-campaign corner escalates, the attributable-standoff corner persists.

> **Equivalence to v25.x:** at Attribution $=0$ the factor vanishes and the dyad behaves as plain T3. Calibration should test whether $u_A>0$ improves out-of-sample fit (the parsimonious replacement for the deprecated "does T3-High beat T3-only" test — §6.7).

#### 1.6.2 Tactical vs strategic WMD use — routing note (unchanged)

The $WMD$ gate governs T6 reachability. WMD use below the strategic-scale threshold is **not a tier event** — it enters as $Shock_k$. Coders must not let the presence of any WMD use silently elevate a dyad to T6 without first evaluating whether the *scale of effect* meets both IHL tests (§2.5). Battlefield CW use (Syria 2013 type), a tactical radiological device, or a small biological attack all route as $Shock_k$, not as T6 triggers.

#### 1.6.3 Status-quo bias and the role of duration (new)

The direction stage is status-quo-biased: at neutral factor values, persistence $P_0$ should dominate, and movement in either direction must be *earned*. Duration appears in **three** consistent places — it raises persistence ($U^0$), raises the down-barrier floor (lock-in, $B_{k\to k-1}$), and — only when multiplied by deniability — raises the T3→T4 escalation hazard ($U^\uparrow$). The first two are distinct channels (whether to stay vs how hard to leave *downward*) and are calibrated separately; they are not double-counting. The net effect is that a dyad whose escalation pressure falls returns to **persistence**, and a long-running conflict resists casual de-escalation unless genuine enablers appear.

### 1.7 The T3 Entry Condition (patron vs merchant) — unchanged

"Selling weapons to $j$'s enemies" is **not sufficient** for T3. T3 requires support that is an **instrument of hostility toward $j$**, established through observables: (1) **Sustained**, (2) **Selective** (directed at $j$'s adversaries and not $j$ — selectivity is the observable proxy for intent), (3) **Targeted** at $j$'s strategic disadvantage, (4) **Corroborated** by co-moving diplomatic/economic friction. The arms dealer fails on selectivity (sells to both) and codes as not-T3 cleanly.

### 1.8 Model Architecture Summary

```
INPUT CODING (CORE 13 + belief term + modifier vector, per directed dyad i->j)
├─ Each input carries a STATE: observed | defaulted | absent   [drives degradation]
├─ Path Dependency: Current Tier (X_t ∈ {0..6}), Duration (D_k)  [dual role: persistence + lock-in + (×Attribution) escalation]
├─ Structural/Military: Rivalry (Ω), Contiguity (Ξ), First-Mover Adv (FMA), Closing Window (-Ẇ)
├─ Economic: Status-Quo Burden (per-actor), Exhaustion (W_x)
├─ Operational/Diplomatic: Off-Ramp Absence (ORA), Stalemate (Stal_t), Dip Capacity (Dip_cap)
├─ Catalysts/Environment: Kinetic Shock (Shock_k), De-escalation Enabler (DeEsc_k),
│                          Strategic WMD Gate (WMD, →T6), Capability/Reach Gate (Cap, →T5), Contagion (V_contagion)
├─ BELIEF: Ĉ_i(C_c) — estimate of counterpart cost field + uncertainty   [gated by δ]
└─ MODIFIER VECTOR: attribution (× duration → T3→T4 escalation), integration depth, stakes, intent/selectivity

ENGINE — PER-ACTOR COST FIELD  C_i(j)
├─ Occupancy cost: economic burden + blood/matériel burden − value extracted at tier j
├─ Status-quo floor; cost-of-war differential
├─ Strategic term: forward-looking (gated by γ)
└─ Belief coupling: depends on i's estimate of c's costs (gated by δ)

STAGE 1 — DIRECTION (status-quo-biased cost gradients across barriers) → softmax → (P↓, P0, P↑)
├─ U↑ = [C(k)−C(k+1)] − B_{k→k+1} + u_Z·Shock_k  (+ u_A·Attribution·D_k at k=T3)
├─ U0 = a0 + r_D·D_k
└─ U↓ = [C(k)−C(k−1)] − B_{k→k−1}(b0,b_tier,b_dur,D_k) + u_D·DeEsc_k

STAGE 2 — ALLOCATION: ω⁺ catalytic, ω⁻ bimodal
COMPOSITION: π_j = P↓·ω⁻ (j<k) ; P0 (j=k) ; P↑·ω⁺ (j>k)
HARD GATES: WMD floor (T6); Capability/Reach gate (T5)
RECONCILIATION (§3.6): one-shot best response between the two cost landscapes

DEGRADATION LAYER (§1.9)
├─ Resolve each input's state; drop or default terms accordingly
├─ Select active model member (full ↔ public ↔ myopic ↔ diagnostic-fallback)
├─ Compute confidence penalty from coverage
└─ Emit COVERAGE VECTOR alongside π
```

### 1.9 The Nested-Model Family & Graceful Degradation

The model is a **family of nested members**. Each advanced term has a **documented null value** that, when the term's inputs are absent, reduces the model to a simpler member that is itself fully valid. Degradation is *down the family*, never into undefined behavior.

#### 1.9.1 The three input states

| State | Meaning | Engine behavior |
| --- | --- | --- |
| **observed** | A real coded value (any number in range, including 0) | Used as-is |
| **defaulted** | Not coded; a documented neutral default applies | Default substituted; flagged in coverage |
| **absent** | Explicitly unobservable for this dyad | The *term* is dropped from the cost field / barrier / score set; flagged in coverage |

> **Critical: "absent" ≠ "zero."** A missing belief term is not "the counterpart's costs are zero." A missing $DeEsc_k$ is not "no de-escalation enabler exists" coded as a confident 0 — it drops the $u_D\,DeEsc_k$ term. The same applies to every advanced term.

#### 1.9.2 Documented null values (the degradation table)

| Term | Symbol | Null value when absent | Resulting member |
| --- | --- | --- | --- |
| Belief coupling | $\delta\,\Phi(\hat{\mathcal{C}}_i(\mathcal{C}_c))$ | $\delta = 0$ → term dropped | **belief-blind / public** member |
| Forward-looking | $\gamma\,\mathbb{E}[\mathcal{C}_i(\text{future})\mid j]$ | $\gamma = 0$ → term dropped | **myopic** member |
| De-escalation activation | $u_D\,DeEsc_k$ | term dropped → down-barrier floor governs alone | **floor-only de-escalation** (more status-quo-biased) |
| Attribution×Duration escalation | $u_A(\text{Attr}\cdot D_k)$ | Attribution absent → factor dropped | **plain-T3** behavior |
| Attribution modifier | suppression of upward $B$ | no suppression → barrier at default height | un-discounted transition |
| Integration depth | suppression of patron $B_{T3\to T4}$ | no suppression → default barrier | un-discounted patron transition |
| Stakes modifier | enters $V_i(\cdot)$ | falls back to $\Omega\Xi$ alone | structural-stakes-only |
| Down-barrier duration/tier floor | $b_{tier},b_{dur}$ in $B_{k\to k-1}$ | terms absent → flat $b_0$ floor | **flat-barrier** (v25.x-like) member |
| Capability/Reach | $Cap_{i\to j}$ | **high-salience: fail-loud** (§1.9.6); never silently defaulted | — |
| Intent/selectivity | T3 entry gate | gate unevaluable → see §1.9.4 | (classification fallback) |
| Cost-field occupancy components | $B^{econ}, B^{blood}, V_i$ | if any absent → fall back to deprecated $E_t/D_t/S_t$ diagnostics for that transition | **diagnostic-fallback** member |

The members form an ordered ladder of richness:

```
full model  ⊃  (drop belief, δ=0)  ⊃  public model
            ⊃  (also drop forward-looking, γ=0)  ⊃  myopic model
            ⊃  (also drop cost-field components)  ⊃  diagnostic-fallback (E_t/D_t/S_t)
```

Orthogonal reductions (do not change the member's tier on this ladder but increase status-quo bias / parsimony): dropping $u_D\,DeEsc_k$ → floor-only de-escalation; dropping the duration/tier floor → flat-barrier; dropping Attribution×Duration → plain-T3. Each ⊃ is a strict reduction. **This is testable** — see §6.9.

#### 1.9.3 Public vs private as members of the family — unchanged

- **Public member.** $\delta = 0$, modifiers at default unless an observable supports them, occupancy costs anchored to open data. Canonical degraded member; auditable on MIDs/UCDP.
- **Private member.** Belief term active with a narrowed band; occupancy costs measured; integration depth from privileged sources.
- **The divergence is an output.** Report $\|\pi^{\text{private}} - \pi^{\text{public}}\|$ as a first-class quantity (§5 step 11).

#### 1.9.4 Renormalize, don't impute — unchanged

Where a term is absent, the model **collapses to the simpler functional form** rather than guessing a placeholder. Special case — **T3 classification when intent/selectivity is absent:** the entry gate cannot be evaluated, so code the dyad at the highest tier supported *without* the proxy claim (typically T1/T2), flag the proxy question unresolved, and fail loud if the consumer requires the classification (§1.9.6).

#### 1.9.5 Confidence penalty from coverage — unchanged

$$
\text{conf} = \text{conf}_0 \cdot \prod_{t \in \text{terms}} \rho_t^{\,\mathbb{1}[t \text{ not observed}]}, \qquad \rho_t \in (0,1]
$$

The point forecast $\pi$ is still emitted; the penalty travels with it.

#### 1.9.6 Fail-soft vs fail-loud

- **Fail-soft (default, early warning / scenario comparison):** degrade down the family, emit $\pi$ + coverage + confidence penalty. Never refuse.
- **Fail-loud (configurable, decision-support claims):** for the **high-salience variables** — now $\{WMD, Cap, \text{current-tier classification}, \text{T3 entry gate}\}$ — refuse to score and demand the value rather than emit a number that quietly ran without its most important input. $Cap$ joins this set because it controls the hard gate on T5 (§3.7).

---

## PART 2: INPUT VARIABLES & CODING GUIDANCE (THE CORE 13 + ADDITIONS)

Every input carries a state ∈ {observed, defaulted, absent} (§1.9.1). Variables are bounded **[0,1]** except $V_{contagion}\in[-1,+1]$, $X_t\in\{0,1,2,3,4,5,6\}$, $D_k\in[0,\infty)$.

### 2.1 Path Dependency

- **CurrentTier ($X_t$)** — operational reality now. Shared. Range $\{0,1,2,3,4,5,6\}$ (**no T3-High**). **High-salience: fail-loud if unresolvable.**
- **Duration ($D_k$)** — time at current tier, months/10. **Dual/triple role (§1.6.3):** carries memory; raises persistence ($U^0$); raises the down-barrier floor (lock-in); and, multiplied by Attribution, raises the T3→T4 escalation hazard. Default if absent: 0 (freshly entered).

### 2.2 Structural & Military

- **Rivalry ($\Omega$)** — [0,1], symmetric. Default: regional base rate.
- **Contiguity ($\Xi$)** — {0,0.5,1}, symmetric. Almost always observable; default 0. **Also feeds the Capability/Reach gate** (contiguity is a sufficient opener of T5 — §3.7).
- **First-Mover Advantage ($FMA_{i\to j}$)** — [0,1], directional. Default 0. **Logically posterior to $Cap$:** if $Cap_{i\to j}$ cannot clear its gate, FMA is moot for the gated tier.
- **Closing Window ($-\dot{W}_{i\to j}$)** — [0,1], directional; drives the forward-looking term. If absent, $\gamma$ effectively 0 (myopic member).

### 2.3 Economic

- **Status-Quo Burden (was $C_{peace}$)** — observable burden of occupying the current tier; per-actor; [0,1]. Anchor to open data in the public member. If fully absent, fall back to diagnostic member for affected transitions.
- **Exhaustion ($W_x$)** — [0,1], symmetric. **Primary input to $DeEsc_k$** (§2.5). Default 0.

### 2.4 Operational & Diplomatic

- **Off-Ramp Absence ($ORA$)** — [0,1]. Default 0.5. $(1-ORA)$ feeds $DeEsc_k$ (off-ramp *presence* enables de-escalation).
- **Stalemate ($Stal_t$)** — [0,1]. Default 0.5.
- **Diplomatic Capacity ($Dip_{cap}$)** — [0,1]. **Input to $DeEsc_k$.** Default 0.5.

### 2.5 Catalysts, Gates & Environment

- **Kinetic Shock ($Shock_k$)** — [0,1], upward activation energy in $U^\uparrow$. Default 0. **Tactical WMD use that does not clear the $WMD$ gate is coded here** as a high-magnitude $Shock_k$, not as a T6 trigger.

- **De-escalation Enabler ($DeEsc_k$)** — [0,1], the downward mirror of $Shock_k$; supplies activation energy in $U^\downarrow$ (§3.2). Derived composite of the de-escalation enablers already in the model:
  $$
  DeEsc_k = \text{clip}\big(d_W W_x + d_{Dip}Dip_{cap} + d_{off}(1-ORA),\,0,1\big).
  $$
  This is the **direction-stage** use of these enablers — *whether* to descend. Their **allocation-stage** use (*how far* — step-down vs collapse-to-peace) remains $\kappa$ (§3.5.2). Keep the two uses distinct to avoid double-counting (§3.2 caveat). Default 0 (no enabler this period → floor-only de-escalation member).

- **Strategic WMD Gate ($WMD$)** — [0,1], symmetric. Gates **T6**. A weapon clears the gate iff it meets **both** IHL-derived tests (AP I Arts. 35–36, 51(4)):
  1. **Unlimitable effects** — effects structurally cannot be spatially/temporally bounded after employment, regardless of aim precision (ICRC standard: structurally uncontrollable, not merely uncontrolled in an instance).
  2. **Strategic-scale consequence** — expected footprint sufficient to threaten the target state's stability, territorial integrity, or national survival.

  **Coding by weapon class:** *Nuclear* → $WMD>0$ automatically for any confirmed nuclear-armed state. *Biological* → $WMD>0$ only for an assessed engineered agent capable of pandemic-/national-destabilization-scale deployment. *Chemical* → $WMD=0$ unless stockpile + delivery can produce strategic-urban-scale area casualties (almost never; battlefield CW = $Shock_k$). *Radiological* → $WMD=0$ unless credibly assessed to cause mass-area state-destabilizing contamination (almost never). Record sub-components individually; the composite takes the maximum across classes *that clear both tests*. **High-salience: fail-loud if unresolvable.** Default 0.

- **Capability/Reach Gate ($Cap_{i\to j}$)** — [0,1], **directional**. Gates **T5** (§3.7). $Cap_{i\to j}$ is the assessed capacity of $i$ to inflict **considerable, sustainable** damage on $j$'s **military *or* civilian infrastructure** (maximum over the two target classes — holding the adversary's cities at sustained risk counts even against a military one cannot defeat). The bar is *strategic-war-enabling*, not a single credible blow; a one-off interceptable strike does not clear it. Built from force projection (air/naval/missile/ground reach to $j$'s territory), geographic access (contiguity), basing/allies that extend reach, and penetration of $j$'s defenses.
  - **Threshold $\tau$:** the T5 gate opens iff (dyad) $\;\Xi\ge\xi^\* \;\lor\; Cap_{A\to B}\ge\tau \;\lor\; Cap_{B\to A}\ge\tau$ (§3.7).
  - **Dual use:** the *gate* is the threshold crossing on T5; the *raw value* additionally feeds **continuous** escalation pressure into the ungated T4 (a near-incapable microstate gets no hard T4 block but a low $P_\uparrow$ on its own).
  - **Consistency with WMD:** $WMD_i>0 \Rightarrow Cap_{i\to j}\ge\tau$ (a confirmed strategic-WMD capability *is* considerable-damage-at-range), so any T6-reachable dyad necessarily clears the T5 gate; no separate reach gate is needed on T6.
  - **High-salience: fail-loud if unresolvable.** Contiguity and gross capability are almost always observable, so genuine absence should be rare. Default: not permitted to silently default the gate; if it must, fail-loud.

- **Bidirectional Contagion ($V_{contagion}$)** — [-1,+1], symmetric, lag ≥1, instrument with distance-to-regional-conflict. Default 0.

### 2.6 Belief Term — unchanged

- **Belief about counterpart costs ($\hat{\mathcal{C}}_i(\mathcal{C}_c)$)** — directional; point estimate + confidence [0,1], **or state = absent** ($\delta=0$ → public member). A confidently *wrong* belief is the most dangerous configuration and is distinct from absence.

### 2.7 Modifier Vector

- **Attribution** [0,1] — deniability. Suppresses upward $B$ **and**, multiplied by Duration, supplies the T3→T4 escalation factor (§1.6.1). Absent → no barrier suppression *and* the escalation factor drops (plain-T3).
- **Integration depth** [0,1], directional — patron entanglement. Absent → no patron-barrier suppression.
- **Stakes** [0,1] — carried by $\Omega\Xi$. Absent → falls back to $\Omega\Xi$ alone.
- **Intent/selectivity** [0,1], directional — T3 entry gate. Absent → classification fallback (§1.9.4), possibly fail-loud.

---

## PART 3: MATHEMATICAL SPECIFICATION

### 3.0 The Cost Field (engine) — unchanged in form

For acting actor $i$ contemplating tier $j$ against counterpart $c$:

$$
\mathcal{C}_i(j) = \underbrace{\beta_1 B^{econ}_i(j) + \beta_2 B^{blood}_i(j) - \beta_3 V_i(j)}_{\text{occupancy cost at } j} + \underbrace{\gamma\, \mathbb{E}\!\left[\mathcal{C}_i(\text{future}) \mid j\right]}_{\text{strategic / forward-looking}} + \underbrace{\delta\, \Phi\!\big(\hat{\mathcal{C}}_i(\mathcal{C}_c(j))\big)}_{\text{belief coupling}}
$$

**Degradation of the engine:** belief absent → $\delta=0$; $-\dot W$ absent → $\gamma=0$; any occupancy component absent for tier $j$ → that transition falls back to $E_t/D_t/S_t$ diagnostics (§3.1). A dropped term changes the *value* of $\mathcal{C}_i(j)$ but never its existence; gradients (§3.2) and softmax (§3.3) remain valid.

**Encoded consequences:** sanctions raise $B^{econ}_i(k)$ and lower $B^{econ}_i(\text{war tiers})$; expressive sanctions keep war tiers expensive; the global minimum is usually T0 but **the status-quo-biased barriers (§3.2) prevent the fall**; modifiers act on barriers, not on $\mathcal{C}$ levels directly.

### 3.1 Composite Indices ($E_t, D_t, S_t$ — DEPRECATED to diagnostics; also the fallback member) — unchanged

**Escalation Pressure ($E_t$):** $\;\text{clip}(\alpha_1\Omega + \alpha_2\Xi + \alpha_3 FMA_{i\to j} + \alpha_4(-\dot W_{i\to j}) + \alpha_5 C_{peace} + \alpha_6 V_{contagion} + \alpha_7(\Omega\cdot\Xi),\,0,1)$
**De-Escalation Capacity ($D_t$):** $\;\text{clip}(\theta_1 W_x + \theta_2 Dip_{cap} + \theta_3(1-C_{peace}) - \theta_4 V_{contagion},\,0,1)$
**Persistence Lock ($S_t$):** $\;\text{clip}(\rho_1 Stal_t + \rho_2 ORA + \rho_3 D_k + \rho_4 V_{contagion},\,0,1)$

> The diagnostic forms let any transition degrade gracefully to a coarse, valid direction signal when the cost field cannot be built.

### 3.2 Movement Scores — Status-Quo-Biased Cost Gradients with Barriers

$$
U_k^{\uparrow} = \big[\mathcal{C}_i(k) - \mathcal{C}_i(k+1)\big] - B_{k\to k+1} + u_Z\, Shock_k \;+\; \mathbb{1}[k=\text{T3}]\;u_A\,\big(\text{Attribution}\cdot D_k\big)
$$

$$
U_k^{0} = a_k^{0} + r_D\, D_k
$$

$$
U_k^{\downarrow} = \big[\mathcal{C}_i(k) - \mathcal{C}_i(k-1)\big] - B_{k\to k-1} + u_D\, DeEsc_k
$$

with the **status-quo-biased down-barrier**

$$
B_{k\to k-1} = \text{clip}\big(b_0 + b_{tier}\cdot\text{idx}(k) + b_{dur}\cdot D_k,\;0,\;\infty\big),\qquad \text{idx}(k)\in\{0,\dots,6\}.
$$

- **The down-barrier is the mechanism of status-quo bias.** Because peace is usually the global minimum, the down-gradient $\mathcal{C}_i(k)-\mathcal{C}_i(k-1)$ is positive almost everywhere; $B_{k\to k-1}$ is sized to absorb the typical positive gradient, grows with tier (higher tiers are stickier to leave) and dwell time (lock-in), and is overcome only by genuine enablers via $u_D\,DeEsc_k$. **De-escalation is now earned, exactly as escalation is.** When escalation pressure falls, mass returns to $P_0$ (persistence), not to $P_\downarrow$.
- $B_{k\to k+1}\ge 0$ is the upward barrier; **absent modifiers leave it at default height** — absence of evidence for deniability ≠ a deniability discount.
- $Shock_k$ supplies upward activation; $DeEsc_k$ supplies downward activation; both default 0. **Tactical WMD use routes into $Shock_k$** (§1.6.2, §2.5).
- The **Attribution×Duration** term (§1.6.1) is the former-T3-High escalation factor, active only at the T3→T4 transition.

> **Note on the two duration channels.** $r_D D_k$ (in $U^0$) raises *persistence*; $b_{dur}D_k$ (in $B_{k\to k-1}$) specifically raises *resistance to de-escalation* while leaving escalation reachable. They are distinct channels and calibrated separately (§1.6.3).

> **Configurable alternative (de-escalation enablers as barrier suppression).** Equivalently, one may move the enablers from an additive $U^\downarrow$ term into a suppression of $B_{k\to k-1}$ (mirroring how the attribution/integration modifiers suppress the *upward* barrier). The two forms are near-equivalent at the margin but calibrate differently. The **canonical v26.0 form is the additive activation term** $u_D\,DeEsc_k$ (direct mirror of $u_Z\,Shock_k$); the suppression form is a documented configurable variant. (This is the one design fork left open in the v26.0 derivation; it does not affect any other element.)

> **Confounding caveat (unchanged).** If *both* a barrier and the cost levels of a transition are undetermined, the transition is under-identified; fall back to the diagnostic member for that transition rather than emit a falsely precise gradient (§1.9.4).

### 3.3 Direction Probabilities (Softmax = multinomial logit) — unchanged

$$
Z = \exp(U_k^\downarrow) + \exp(U_k^0) + \exp(U_k^\uparrow),\qquad
P_\downarrow = \frac{\exp(U_k^\downarrow)}{Z},\quad P_0 = \frac{\exp(U_k^0)}{Z},\quad P_\uparrow = \frac{\exp(U_k^\uparrow)}{Z}
$$

Boundary constraints: $P_\downarrow(k{=}0)=0$; $P_\uparrow(k{=}6)=0$; adjacency follows the ordered list T0–T6. The softmax is well-defined for any finite $U$-scores, so it survives any combination of dropped terms.

### 3.4 Composition Equation — unchanged

$$
\boxed{\;\pi_{kj} = \begin{cases} P_\downarrow \cdot \omega^-_{kj} & j < k \\[4pt] P_0 & j = k \\[4pt] P_\uparrow \cdot \omega^+_{kj} & j > k \end{cases}\;}
$$

Mass conservation holds exactly since $\sum_{j<k}\omega^-_{kj}=\sum_{j>k}\omega^+_{kj}=1$ (after the hard gates renormalize the upward set — §3.7).

### 3.5 Allocation Stage — Skip Functions

#### 3.5.1 Upward Allocation $\omega^+$

$$
\Sigma^{\uparrow}_{i\to j} = (FMA_{i\to j})^{\eta_\phi}\,(-\dot W_{i\to j})^{\eta_w}\,(ORA)^{\eta_r}\,(1 - WMD^{\eta_n})
$$

$$
\omega^+_{kj} \propto \exp\!\big[-\lambda^+_k\,(j-k-1)\,(1-\Sigma^\uparrow)\big]\cdot G^+_{kj},\qquad j>k
$$

normalized over $j>k$ **after the hard gates (§3.7) zero out unreachable destinations.** Skip distance $(j-k-1)$ is computed on the T0–T6 list (no T3-High); in particular T3→T4 is now adjacent. Absent $FMA$ or $-\dot W$ default to 0 → steep decay, mass on the adjacent tier (conservative).

> **WMD in $\Sigma^\uparrow$ (unchanged):** $(1-WMD^{\eta_n})$ suppresses skip mass toward T6 when $WMD=0$; the suppression lifts when $WMD>0$. The gate controls reachability; the skip function controls how much mass reaches T6 given upward movement.

#### 3.5.2 Downward Allocation $\omega^-$ (Bimodal) — unchanged in form

$$
\omega^-_{kj} \propto (1-\kappa)\exp\!\big[-\lambda^-_k(k-j-1)\big] + \kappa\,C_{kj},\qquad j<k
$$

$$
\kappa = \sigma\!\big(c_0 + c_W W_x + c_{Dip}Dip_{cap} - c_{Stal}Stal_t - c_{ORA}ORA\big)
$$

Step-down = local descent; collapse = a path opening over the ridge to the global minimum. **Division of labor (new):** $DeEsc_k$ in $U^\downarrow$ governs *whether* the dyad descends at all (direction stage); $\kappa$ governs *how far* it descends (allocation stage). The shared inputs ($W_x, Dip_{cap}, ORA$) appear in both by design but in non-overlapping roles.

### 3.6 Reconciling the Two Directed Runs — as a Game — unchanged

- **Escalation:** $P_\uparrow^{\text{rel}} = \max(P_\uparrow^{A\to B}, P_\uparrow^{B\to A})$ (unilaterally enforceable).
- **De-escalation:** $P_\downarrow^{\text{rel}} = \min(P_\downarrow^{A\to B}, P_\downarrow^{B\to A})$ (requires mutual consent; integration depth can make a patron the gating actor).
- **Persistence:** residual $P_0^{\text{rel}} = 1 - P_\uparrow^{\text{rel}} - P_\downarrow^{\text{rel}}$ (clip at 0, renormalize).

> The Capability/Reach gate is applied at the dyad level *before* reconciliation drives mass into T5 (the OR across directions, §3.7, is the dyad-level analogue of the escalation `max`). **Degradation note:** if one direction is fully coded and the other is sparse, reconcile with the better-covered direction and propagate the *worse* confidence penalty.

### 3.7 Hard Gates

| Gate | Rule |
| --- | --- |
| **Capability/Reach floor (T5)** | The dyad-level disjunction $\;G_{T5}=\mathbb{1}\big[\Xi\ge\xi^\* \;\lor\; Cap_{A\to B}\ge\tau \;\lor\; Cap_{B\to A}\ge\tau\big]$. If $G_{T5}=0$, set $\omega^+_{k,5}=0$ (and $\omega^+_{k,6}=0$, consistent with $WMD>0\Rightarrow Cap\ge\tau$) in **both** directed runs; renormalize the upward set over reachable destinations. T5 is unreachable for non-contiguous dyads in which neither side can inflict considerable, sustainable damage. **T4 is ungated** (any actor able to land a credible attributed blow can reach it); $Cap$ still feeds T4 as continuous pressure. High-salience: if $Cap$ unresolvable, fail-loud rather than guess the gate. |
| **WMD floor (T6)** | If $WMD=0$, set $\omega^+_{k,6}=0$; renormalize. T6 is unreachable if neither side possesses a confirmed strategic-scale WMD capability meeting both IHL tests (§2.5). Tactical WMD use does not set $WMD>0$; it enters as a high-magnitude $Shock_k$ at T5. $WMD$ is high-salience: fail-loud if unresolvable. |
| Adjacent baseline | $G^\pm$ default = 1.00. |
| Two-tier skip | Default = 0.35. |
| Three-tier skip | Default = 0.10. |
| Larger skip | Default = 0.02. |

> **Gate ordering / consistency.** Evaluate $Cap$ (T5) and $WMD$ (T6) before normalizing $\omega^+$. Because $WMD_i>0\Rightarrow Cap_{i\to j}\ge\tau$, you can never reach the incoherent state of T6 open while T5 is shut. Skip-distance defaults are unchanged in value but are now indexed on the T0–T6 list.

### 3.8 Default Operational Coefficients (PRIORS, not calibrated)

v22 priors carry over for retained terms. New families remain explicitly TBD: $\beta_{1,2,3}$, $\gamma$, $\delta$, $\Phi$ shape, barriers $B_{k\to j}$, modifier→barrier suppression, the per-term retention factors $\rho_t$, and the **new v26.0 parameters** below.

| Param | Default | Param | Default | Param | Default |
| --- | --- | --- | --- | --- | --- |
| $a^0$ | 0.20 | $r_D$ | 0.03 | $u_Z$ (upward shock) | 0.55 |
| $\lambda^+_k$ | 1.20 | $\lambda^-_k$ | 1.20 | $\alpha_7$ ($\Omega\Xi$, diag.) | 0.50 |
| $\beta_{1,2,3}$ | TBD | $\gamma$ | TBD | $\delta$ | TBD |
| $B_{k\to k+1}$ (upward) | TBD | modifier→$B$ suppression | TBD | $\kappa$ params $c_\bullet$ | TBD |
| **$b_0$** (down-barrier floor) | **TBD** | **$b_{tier}$** (tier lock-in) | **TBD** | **$b_{dur}$** (duration lock-in) | **TBD** |
| **$u_D$** (de-escalation activation) | **TBD** | **$d_W,d_{Dip},d_{off}$** ($DeEsc$ weights) | **TBD** | **$u_A$** (Attribution×Duration) | **TBD** |
| **$\tau$** (Cap threshold) | **TBD** | **$\xi^\*$** (contiguity opener) | **0.5** | $\rho_t$ (confidence retention) | TBD |
| conf$_0$ | 1.00 | — | — | — | — |

> Sign constraints to impose in calibration: $b_0,b_{tier},b_{dur},u_D,u_A\ge 0$; the down-barrier should be large enough that at neutral enablers ($DeEsc=0$) a positive down-gradient does not by itself produce $P_\downarrow>P_0$ (the status-quo-bias identification target — §6.7).

---

## PART 4: WORKED EXAMPLE (status-quo bias, merged T3, reach gate)

### 4.1 Status-quo bias at a sanctioned standoff

Sanctioned dyad $(A\rightarrow B)$ at **T2**, coercive-prelude type. Full-model cost field for actor $A$:

| Tier $j$ | $\mathcal{C}_A(j)$ | Comment |
| --- | --- | --- |
| T1  | 0.55 | conceding the dispute is costly |
| **T2 (now)** | **0.60** | sanctions absorbed; floor raised |
| T3  | 0.50 | sustained selective proxy cheaper |

Inputs: $\text{idx}(\text{T2})=2$, $D_k=0.8$ (8 months at T2), $DeEsc_k=0.1$ (little exhaustion, weak off-ramp), $Shock_k=0$.

**Down-barrier (v26.0):** $B_{T2\to T1}=b_0+b_{tier}\cdot 2+b_{dur}\cdot 0.8$. Using illustrative priors $b_0=0.15,\,b_{tier}=0.04,\,b_{dur}=0.10$: $B_{T2\to T1}=0.15+0.08+0.08=0.31$. Upward barrier $B_{T2\to T3}=0.05$. $u_D=0.40$.

$$
U^\uparrow = (0.60-0.50) - 0.05 = 0.05,\quad
U^0 = 0.20 + 0.03(0.8) = 0.224,\quad
U^\downarrow = (0.60-0.55) - 0.31 + 0.40(0.1) = -0.22
$$

Softmax → $P_\downarrow\approx0.16,\;P_0\approx0.45,\;P_\uparrow\approx0.39$.

Contrast with the v25.x flat-barrier behavior ($B_{T2\to T1}\approx0.20$, no $DeEsc$ term): there $U^\downarrow=(0.60-0.55)-0.20=-0.15$, giving $P_\downarrow\approx0.26,\,P_0\approx0.38,\,P_\uparrow\approx0.36$. **v26.0 moves ~10 points of mass off de-escalation and onto persistence**, lengthening the modelled residence time at T2 toward what sanctioned standoffs actually exhibit — the target behavior. De-escalation now requires $DeEsc_k$ to rise (exhaustion + a real off-ramp), at which point $u_D\,DeEsc_k$ pays the barrier down and $P_\downarrow$ recovers.

### 4.2 Merged-T3 escalation factor

Suppose instead the dyad sits at **T3** with a *sustained, deniable* campaign: Attribution $=0.8$, $D_k=1.5$ (15 months). With $u_A=0.12$, the T3→T4 score gains $u_A(\text{Attr}\cdot D_k)=0.12(0.8\times1.5)=0.144$ — a substantial upward push that did not exist for a fresh or fully-attributable T3. A fully attributable campaign of the same duration (Attribution $=0$) gets none of this push and instead locks in via the down-barrier (larger $b_{dur}D_k$). This reproduces the old T3-High escalation tendency without a separate tier.

### 4.3 Reach gate

Two cases for whether T5 is reachable from this dyad's upward mass:

- **Contiguous rivals** ($\Xi=1$): $G_{T5}=1$ regardless of $Cap$ — T5 reachable; $\omega^+$ may place mass on T5.
- **Non-contiguous, low-reach** ($\Xi=0$, $Cap_{A\to B}=0.2<\tau$, $Cap_{B\to A}=0.15<\tau$): $G_{T5}=0$ — set $\omega^+_{k,5}=\omega^+_{k,6}=0$ and renormalize. All upward mass that would have skipped to T5 piles onto **T4** instead. The dyad can trade sustained limited attributed strikes but cannot mount a strategic war — the correct ceiling for distant rivals with no projection.

### 4.4 WMD gate note (unchanged)

If neither actor has a confirmed strategic-scale WMD capability, $WMD=0$ → $\omega^+_{k,6}=0$. A battlefield CW strike by $A$ routes as a high-magnitude $Shock_k$ (raising $P_\uparrow$ within T5) but does not set $WMD>0$ or open T6 unless $A$ independently holds a strategic-scale WMD capability meeting both IHL tests. Note that any such capability would also satisfy $Cap\ge\tau$ (§3.7 consistency).

---

## PART 5: IMPLEMENTATION WORKFLOW

1. **Assign current tier $X_t$** (shared; range T0–T6, **no T3-High**). Apply the T3 entry condition (§1.7). If intent/selectivity is absent, use the classification fallback (§1.9.4). **Before assigning T5, evaluate the Capability/Reach gate (§3.7).** Before assigning T6, verify both IHL tests (§2.5). If $X_t$, $Cap$, or $WMD$ is unresolvable, fail-loud (§1.9.6).
2. **Code each input with its state** (observed / defaulted / absent — §1.9.1) for direction $(i\to j)$: $FMA$, $-\dot W$, belief term + uncertainty, directional modifiers (including **Attribution** for the T3→T4 factor), and $Cap_{i\to j}$. Record $WMD$ sub-components individually before computing the composite.
3. **Code symmetric variables** ($\Omega,\Xi,W_x,ORA,Stal_t,Dip_{cap},V_{contagion},WMD$), per-actor Status-Quo Burden, and $Duration$, each with a state. Compute $DeEsc_k$ from $W_x,Dip_{cap},(1-ORA)$.
4. **Resolve the active model member** from coverage (§1.9.2): full → public ($\delta=0$) → myopic ($\gamma=0$) → diagnostic-fallback; plus orthogonal reductions (floor-only de-escalation, flat-barrier, plain-T3) as the corresponding inputs drop.
5. **Build the cost field** $\mathcal{C}_i(j)$ with surviving terms; apply modifier→barrier suppression only where modifiers are observed.
6. **Stage 1 (status-quo-biased):** compute $U^\uparrow$ (with the T3 Attribution×Duration term where applicable), $U^0$, and $U^\downarrow$ with the tier/duration down-barrier and the $u_D\,DeEsc_k$ activation; softmax → $(P_\downarrow,P_0,P_\uparrow)$; boundary constraints.
7. **Stage 2:** $\Sigma^\uparrow$, $\kappa$, $\omega^+$, bimodal $\omega^-$. **Apply hard gates:** Capability/Reach gate on T5 (zero $\omega^+_{k,5}$ and $\omega^+_{k,6}$ if $G_{T5}=0$); WMD floor on T6 (zero $\omega^+_{k,6}$ if $WMD=0$); renormalize the upward set.
8. **Compose** via §3.4.
9. **Repeat for the reverse direction**; evaluate the dyad-level reach gate once and apply to both runs.
10. **Reconcile** (§3.6), propagating the worse confidence penalty.
11. **Report** the cost fields, barriers used (including the tier/duration down-barrier values), the modifier vector, the Attribution×Duration escalation contribution, $DeEsc_k$, belief gap, both directed $\pi$ vectors, the reconciled distribution, the deprecated $E_t/D_t/S_t$ diagnostics, the COVERAGE VECTOR (per-input state + active member + confidence penalty), the $Cap$ sub-assessment and gate result, the $WMD$ sub-component scores alongside the composite, and — if both public and private members were run — the divergence $\|\pi^{\text{private}}-\pi^{\text{public}}\|$ (§1.9.3).

---

## PART 6: VALIDATION, LIMITATIONS & OPEN ISSUES

### 6.1 What "Calibration" Requires Before Any Production Claim

Point estimates **and standard errors** for all coefficients — cost-field weights, $\gamma$, $\delta$, every barrier (including $b_0,b_{tier},b_{dur}$ and the upward $B_{k\to k+1}$), modifier→barrier suppression, $u_D$ and the $DeEsc$ weights, $u_A$, the $Cap$ threshold $\tau$, and the confidence-penalty retention factors $\rho_t$ — via penalized MLE or Bayesian estimation (MIDs 1990–2015; UCDP-dyadic for proxy/T3). Out-of-sample Brier / log-loss / AUROC by tier. Inter-coder reliability (belief term and integration depth expected worst; $WMD$ sub-components and **$Cap$ "considerable damage" assessments** expected high-variance). Barrier identification via shocks that "pay" the barrier — symmetrically, **down-barrier identification via observed de-escalations that follow enabler spikes ($DeEsc$)**. Until then, every coefficient is an intelligent guess.

### 6.2 Retained Limitations

Rare-event tails (T6); $V_{contagion}$ needs network analysis; multi-actor wars exceed dyadic simplification (integration depth is the dyadic compression of a triadic reality); single representative decision-maker assumed; the $Cap$ "considerable damage" threshold compresses a continuous capability spectrum into one gate.

### 6.3 Contagion Endogeneity (Manski Reflection) — unchanged

Lag ≥1 period; instrument with distance-to-regional-conflict, not local intensity.

### 6.4 Status-Quo Burden vs Cost-of-War — unchanged

Split resolved; the forward-looking term still reintroduces a counterfactual by construction. When $-\dot W$ is absent, the myopic member ($\gamma=0$) sidesteps it at the cost of preventive logic.

### 6.5 Structural Incompleteness (Regime Type) — unchanged

Still excluded; if added, must improve out-of-sample fit beyond $\Xi$.

### 6.6 The Physics Analogy — Explicit Caveat — unchanged

Good generative source, bad governing theory. The governing theory is a **Markov game with cost-shaped transition probabilities.** The status-quo-biased barriers make the analogy tighter (activation energy required in *both* directions) but the second player and agency remain essential.

### 6.7 Falsifiable Predictions

- Expressive-sanctions dyads → **overwhelming persistence mass** (the status-quo-bias fix should sharpen this relative to v25.x; if it does not, $b_0/b_{tier}/b_{dur}$ are undertuned).
- **Status-quo-bias identification.** At neutral enablers ($DeEsc=0$), a positive down-gradient should *not* by itself produce $P_\downarrow>P_0$; de-escalation rate should rise measurably only after $DeEsc$ (exhaustion + off-ramp) rises. If de-escalation is uncorrelated with enabler spikes, the down-barrier/activation structure is mis-specified.
- Sanctioned-into-a-corner dyads → elevated escalation vs comparable un-sanctioned high-stakes dyads (2014→2022 Russia–Ukraine, motivating not confirming).
- Confidently-wrong belief configurations → miscalculation-driven escalation cost fields alone miss.
- **Attribution×Duration replaces the T3-High tier test.** $u_A>0$ should improve out-of-sample fit on post-2007 sustained-deniable dyads; sustained *attributable* dyads of equal duration should show lock-in (persistence), not the escalation push. If the interaction adds nothing, set $u_A=0$ (plain-T3) — the parsimonious null.
- Deeply-integrated proxy dyads → higher $T3\to T4$ rates than shallow, controlling for $\Omega\Xi$.
- Merchant test: non-selective support → not T3, no proxy-war dynamics.
- **Reach-gate predictions.** Non-contiguous dyads with neither side clearing $\tau$ should never realize T5 and should cap at T4; their upward mass should concentrate on T4. Dyads that acquire strategic reach (new long-range capability, new basing/alliance) should show T5 become reachable at that point and not before. If T5 onsets appear in genuinely no-reach dyads, $\tau$ or the $Cap$ coding is wrong.
- **WMD-class heterogeneity** (unchanged): BW-only qualifying dyads should show a different T5→T6 skip profile than nuclear-capable dyads.
- **Tactical WMD coding test** (unchanged): historical battlefield CW cases (Syria 2013, Iraq–Kurds 1988) should code $WMD=0$ and remain ≤ T5.

### 6.8 Proper Use — unchanged

✓ Early warning, scenario comparison, sensitivity analysis. ✗ Deterministic forecasting or point certainty.

### 6.9 Validating the Degradation Architecture

- **Nesting equivalence test.** Set a richer member's extra-term inputs to null; confirm it reproduces the simpler member's $\pi$ to numerical tolerance — now including: $u_D=0$/$DeEsc=0$ → floor-only de-escalation; $b_{tier}=b_{dur}=0$ → flat-barrier (v25.x-like); Attribution $=0$ → plain-T3.
- **Public-as-anchor; degraded-vs-full divergence; confidence-penalty calibration; "absent" routing audit** — unchanged.
- **$WMD$ gate audit** — unchanged: (a) $WMD=0$ hard-zeros $\omega^+_{k,6}$; (b) tactical WMD routes exclusively to $Shock_k$; (c) sub-component record preserved.
- **$Cap$ gate audit (new).** Verify that (a) $G_{T5}=0$ hard-zeros $\omega^+_{k,5}$ *and* $\omega^+_{k,6}$ and renormalizes; (b) the gate is evaluated once at the dyad level and applied to both directed runs; (c) the disjunction is OR across contiguity and both directional $Cap$; (d) $WMD>0$ forces $Cap\ge\tau$ so T6-reachable ⇒ T5-reachable; (e) T4 is never reach-gated.
- **Status-quo-bias audit (new).** Verify that with $DeEsc=0$ and a positive down-gradient, $P_0\ge P_\downarrow$ at default priors, and that raising $DeEsc$ monotonically raises $P_\downarrow$.

---

## PART 7: APPENDIX — VARIABLE SUMMARY

| Variable | Name | Type | Range | Directional? | State-aware? | Status |
| --- | --- | --- | --- | --- | --- | --- |
| $X_t$ | Current Tier | State | {0,1,2,3,4,5,6} | shared | high-salience | **T3-High removed** |
| $D_k$ | Duration | State (memory) | [0,∞) | shared | yes | **dual/triple role (persistence, lock-in, ×Attr escalation)** |
| $\Omega$ | Rivalry | Structural | [0,1] | symmetric | yes | unchanged |
| $\Xi$ | Contiguity | Structural | {0,0.5,1} | symmetric | yes | **also feeds Cap gate** |
| $FMA_{i\to j}$ | First-Mover Adv. | Military | [0,1] | directional | yes | unchanged (posterior to Cap) |
| $-\dot W_{i\to j}$ | Closing Window | Military | [0,1] | directional | yes (γ=0 if absent) | unchanged |
| Status-Quo Burden | (was $C_{peace}$) | Economic | [0,1] | per-actor | yes | unchanged |
| $W_x$ | Exhaustion | Economic | [0,1] | symmetric | yes | **feeds $DeEsc_k$** |
| $ORA$ | Off-Ramp Absence | Diplomatic | [0,1] | symmetric | yes | **(1−ORA) feeds $DeEsc_k$** |
| $Stal_t$ | Stalemate | Operational | [0,1] | symmetric | yes | unchanged |
| $Dip_{cap}$ | Diplomatic Cap. | Diplomatic | [0,1] | symmetric | yes | **feeds $DeEsc_k$** |
| $Shock_k$ | Kinetic Shock (upward activation) | Catalyst | [0,1] | symmetric | yes | unchanged |
| $DeEsc_k$ | De-escalation Enabler (downward activation) | Catalyst | [0,1] | symmetric | yes | **new — mirror of $Shock_k$** |
| $V_{contagion}$ | Regional Contagion | Geopolitical | [-1,+1] | symmetric | yes | unchanged |
| $WMD$ | Strategic WMD Gate (→T6) — composite, clears only on both IHL tests; sub-components recorded individually | Gatekeeper | [0,1] | symmetric | high-salience | unchanged from v25.1 |
| $Cap_{i\to j}$ | Capability/Reach Gate (→T5) — capacity to inflict considerable, sustainable damage on $j$'s military or civilian infrastructure; T5 opens iff $\Xi\ge\xi^\*$ OR either $Cap\ge\tau$; $WMD>0\Rightarrow Cap\ge\tau$ | Gatekeeper | [0,1] | directional | high-salience | **new** |
| $\hat{\mathcal{C}}_i(\mathcal{C}_c)$ | Belief about counterpart costs | Strategic (agency) | est.+conf. | directional | yes (δ=0 if absent) | unchanged |
| Attribution | Modifier axis | Modifier | [0,1] | per-dyad | yes | **also × Duration → T3→T4 escalation** |
| Integration depth | Modifier axis | Modifier | [0,1] | directional | yes | unchanged |
| Stakes | Modifier axis | Modifier | [0,1] | symmetric | yes | unchanged |
| Intent/selectivity | Modifier axis (T3 gate) | Modifier | [0,1] | directional | high-salience | unchanged |
| $\mathcal{C}_i(j)$ | Per-actor cost field | Derived engine | ℝ per tier | per-actor | — | unchanged |
| $B_{k\to k+1}$ | Upward activation barrier | Derived/transition | [0,∞) | per transition | — | unchanged |
| $B_{k\to k-1}$ | Downward barrier $=b_0+b_{tier}\,\text{idx}(k)+b_{dur}D_k$ | Derived/transition | [0,∞) | per transition | — | **status-quo-biased (new floor)** |
| $u_A,u_D,b_0,b_{tier},b_{dur},\tau,\xi^\*$ | v26.0 coefficients | Calibration | per def. | — | — | **new (TBD except $\xi^\*$=0.5)** |
| input **state** | observed/defaulted/absent | Meta | {3 states} | per input | — | unchanged |
| coverage vector | active member + states + penalty | Output | — | — | — | unchanged |
| $\rho_t$ | Confidence retention factor | Calibration | (0,1] | per term | — | unchanged |

---

**Version 26.0 | Specification Phase — Awaiting Calibration | Status-Quo-Biased Direction Stage · T3-High Folded into Attribution×Duration · Capability/Reach Gate on T5 · Graceful-Degradation Architecture · Nested-Model Family · Public/Private Layering · IHL-Anchored Strategic WMD Gate | June 2026**