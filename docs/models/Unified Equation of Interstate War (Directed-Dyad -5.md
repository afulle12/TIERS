# Unified Equation of Interstate War (Directed-Dyad Variant) v27.0

## Complete Specification with Full Context & Definitions

**Version:** 27.0 (T6 Collapsed; WMD Reformed as Shock_k Severity Modulator; Empirical Priors from v26.1 Transition Matrix; EUSANCT Threat Data Added to T1; T4 Dual-Population Characterised)
**Status:** Specification & Initial Calibration Phase — Empirical priors set from ~4.4M-observation transition matrix; full MLE/Bayesian calibration pending
**Last Updated:** June 2026

---

## PART 0: VERSION HISTORY

### v27.0 Changes from v26.0

v26.0 established the status-quo-biased direction stage, folded T3-High into an Attribution×Duration escalation factor, and added the Capability/Reach gate on T5. v27.0 keeps all of that **unchanged in substance** and makes four targeted revisions:

| Element | v26.0 | v27.0 |
| --- | --- | --- |
| **Tier T6 (Strategic WMD Employment)** | Separate tier on the ordered ladder, gated by the WMD hard gate (IHL-anchored two-test standard) | **Removed.** Ordered list collapses to T0–T5. The WMD concept is reformed as a **continuous severity modulator** — it enters $Shock_k$ at T5 as a ceiling-amplifier and informs the $Cap$ assessment ($WMD>0 \Rightarrow Cap\ge\tau$). The IHL-derived coding guidance for strategic-scale WMD use is retained as a Shock_k coder instruction (maximum magnitude, consequence-defined threshold). |
| **WMD hard gate (T6)** | $WMD=0$ hard-zeroed $\omega^+_{k,6}$ | **Removed.** T5 is the top tier. The Capability/Reach gate is now the **sole hard gate**, guarding T5 directly. |
| **T1 data pipeline** | MIDB only (hostlev=2 + diplomatic originators), 1900–2014 | **EUSANCT threats added** as a supplemental T1 source. EUSANCT's `threat_dyad=1` rows (1989–2015) are eligible for T1 coding, extending T1 coverage through 2015 and adding ~500 directed dyad-years. The combined T1 source set is ~1,800–2,000 dyad-years (MIDB 1900–2014 + EUSANCT 1989–2015). |
| **Empirical priors** | §3.8 marked "TBD" for 15+ parameters | **Set from the v26.1 transition matrix** (§3.8). Persistence rates, escalation thresholds, and de-escalation barriers are calibrated to observed year-over-year transition frequencies across ~4.4M dyad-years (1900–2025). Parameters that cannot be set from these data remain TBD but now have documented anchors. |
| **T4 dual-population** | Not noted | **Explicitly characterised.** Empirical T4 shows near-equal persistence (51.3%) and de-escalation (44.2%), unique among the active tiers. The model treats this as **Duration-dependent**: short-duration T4 (skirmishes) de-escalates rapidly; long-duration T4 (enduring limited standoffs) locks in via $b_{dur}D_k$. |
| **All other elements** | — | **UNCHANGED from v26.0** (engine, status-quo-biased direction stage, core variables + modifiers, composition, allocation, Attribution×Duration factor, degradation layer, public/private members, Cap/Reach gate logic). |

**Why these matter.**

1. **T6 removal.** v26.0's T6 tier had zero empirical observations to calibrate against — it was a purely theoretical tail. The collapse simplifies the model by removing a tier that cannot be validated. The WMD concept gains empirical leverage by operating *within* T5 (amplifying Shock_k), where tactical WMD events already route (§1.6.2 in v26.0). A single top tier with a single hard gate is more parsimonious and more testable.

2. **Empirical priors.** Moving from "TBD" to data-derived anchors is the single largest informational gain since v21. It converts the model from specification to initial calibration, and makes every §6.7 falsifiable prediction testable with actual numbers.

3. **T1 EUSANCT supplement.** Extends T1 coverage past MIDB's 2014 endpoint and adds post-Cold War threat observations. The ~500 additional dyad-years bolster the tier's empirical base without changing its definition or threshold.

4. **T4 dual-population.** The 50/50 persistence/de-escalation split at T4 is a distinguishing feature that calibrators need to reproduce. The model already contains the mechanism ($b_{dur}D_k$ in the down-barrier) — this makes the identification target explicit.

---

### v26.0 Changes from v25.1

v25.1 established the IHL-anchored Strategic WMD gate on top of v25.0's graceful-degradation architecture and nested-model family. v26.0 kept all of that **unchanged in substance** and made three targeted revisions, all motivated by a single observed pathology: **the v25.x direction stage over-weighted de-escalation in dyads that historically persisted or escalated.**

| Element | v25.1 | v26.0 |
| --- | --- | --- |
| **Direction stage / status-quo bias** | Down-barrier $B_{k\to k-1}$ a flat TBD constant; the structurally-positive down-gradient leaked over it, so falling escalation pressure read as de-escalation rather than as return-to-status-quo | **Status-quo-biased down-barrier:** $B_{k\to k-1}$ given a tier- and duration-dependent structural floor (lock-in), and de-escalation made an *earned* event via an additive **de-escalation activation term** $u_D\,DeEsc_k$ in $U^\downarrow$ — the exact mirror of $u_Z\,Shock_k$ in $U^\uparrow$. Absent enablers, the floor holds and persistence anchors. |
| **T3-High** | A separate tier on the ordered ladder (attribution-suppressed, sustained deniable campaign) | **Removed as a tier.** Ordered list collapses to T0–T6. Its distinguishing content is reconstructed as an **escalation-risk factor on the T3→T4 transition:** the interaction **Attribution × Duration**. Plain duration still raises persistence (lock-in); duration *conditional on deniability* raises the T3→T4 escalation hazard. |
| **Strategic-war feasibility** | No reachability gate on conventional war; contiguity/FMA only dampened pressure continuously | **New Capability/Reach gate $Cap_{i\to j}$ on T5.** T5 is reachable iff the dyad is contiguous OR at least one side can inflict considerable, sustainable damage on the other. T4 remains ungated (any state can land *some* attributed blow). $WMD>0 \Rightarrow Cap\ge\tau$ keeps the two gates consistent; T6 needs no separate reach gate. |
| **All other elements** | — | **UNCHANGED from v25.1** (engine, tiers T0–T6, Core 13, composition, allocation, WMD gate, degradation layer, public/private members). |

---

### v25.1 Changes from v25.0

v25.0 established the graceful-degradation architecture and nested-model family. v25.1 kept all of that unchanged and replaced the binary, weapon-class **Nuclear Gate ($Nuc$)** with the consequence-defined, physics-grounded **Strategic WMD Gate ($WMD$)**, anchored to the IHL indiscriminate-weapons standard (AP I Arts. 35–36, 51(4)): a weapon clears the gate only if its effects are structurally unlimitable *and* of strategic scale. Tactical WMD use was routed explicitly as a high-magnitude $Shock_k$ within T5.

### v25.0 Changes from v24.0

v24.0 established the cost-field engine, the modifier axes, the belief term, and the T3-High tier. v25.0 kept all of that unchanged and added the structural commitment that **the model is a nested family, not a single monolith.** Every advanced term has a documented null value that reduces the model to a strictly simpler, still-valid member; missing inputs degrade the model down the family rather than breaking it. v25.0 also formalized public vs private as two coding protocols over one engine, added the COVERAGE VECTOR output, and made fail-soft the default with fail-loud configurable for high-salience variables.

---

## PART 1: OVERVIEW & ARCHITECTURE

### 1.1 What This Model Does

The Unified Equation of Interstate War (UIW) v27.0 is a **directed-dyad stochastic-game model** for estimating next-period interstate conflict escalation, persistence, and de-escalation. For an ordered pair $(i \rightarrow j)$ — "the prospect of $i$ escalating against $j$" — it estimates the full distribution over next-period tiers. Each actor is a forward-looking agent minimizing a per-actor cost field over a *shared* state variable (the relationship tier), under uncertainty about the other's costs.

The model is **two-stage** plus a reframed engine:

0. **Cost field (engine).** For acting agent $i$, evaluate the cost-to-occupy each reachable tier, $\mathcal{C}_i(j)$ — occupancy cost + a forward-looking strategic term + a belief coupling to the counterpart's costs.
1. **Direction stage.** Movement scores are *cost gradients* between the current tier and adjacent tiers, each penalized by an inter-tier activation barrier. The barriers are **status-quo-biased**: the upward barrier is overcome by the cost gradient plus $Shock_k$; the downward barrier carries a tier/duration-dependent structural floor and is paid down only by an explicit de-escalation activation signal $DeEsc_k$. Softmax → $(P_\downarrow, P_0, P_\uparrow)$.
2. **Allocation stage.** Conditional on a direction, distribute that direction's mass across reachable destination tiers via skip weights $\omega^+$ (upward, catalytic) and $\omega^-$ (downward, bimodal), subject to the Capability/Reach hard gate on T5.

The output is the composition $\pi_{kj}(t) = \text{Pr}(\text{next tier} = j \mid \text{current tier} = k, \text{ inputs at } t)$, a vector over the ordered tier list summing to 1, **accompanied by a coverage vector** (§1.9) describing how much of the machinery was actually fed.

**Recommended forecast interval:** 30 days. See §1.5 for the slow-variable caveat.

### 1.2 Escalation Taxonomy (tiers are cuts on a continuum)

Tiers are **analyst-imposed cuts on a continuum**, not quantized states. Each cut must earn its place empirically (§6.7). **As of v27.0 the ordered list is T0–T5** (§0).

| **Tier** | **Name** | **Military Activity** | **Operational Definition** | **Examples** |
| --- | --- | --- | --- | --- |
| **T0** | Peace | None | No military activity or threat thereof | US–Canada 2020 |
| **T1** | Diplomatic Crisis | None | Formal friction: protests, recalls, ultimatums, UN votes, coercive threats. **Coding sources:** MIDB (hostlev=2 threats + hostlev=1 originators, 1900–2014) and EUSANCT (threat_dyad=1, 1989–2015). | US–Iran 2019; Russia–West threatened sanctions |
| **T2** | Economic Coercion | None | Active sanctions, trade restrictions, financial exclusion | Russia–West 2014; Iran sanctions |
| **T3** | Proxy/Indirect Military | Passive support only | *Sustained, selective* material support to $j$'s adversaries, directed at $j$; $i$ not in direct combat. See §1.7. A *sustained, deniable* T3 campaign carries elevated T3→T4 escalation risk via the Attribution×Duration factor (§1.6.1). | Iran funding Hezbollah; Israel–Iran shadow war; pre-2022 Donbas |
| **T4** | Limited Direct Military | Acknowledged direct combat | Open, attributed exchange of fire between $i$ and $j$ forces. **Ungated for reach:** any actor able to land *some* credible attributed blow can reach T4. **Dual population** (§1.6.3): short-duration skirmishes de-escalate rapidly; enduring limited standoffs lock in. | USS *Reuben James* 1941; smuggled-drone strikes; border clashes |
| **T5** | Strategic War | Expansive conventional | Nationwide / multi-front warfare, sustained campaigns. **Reach-gated (§3.7):** reachable only if the dyad is contiguous OR at least one side can inflict considerable, sustainable damage on the other. T5 is the top tier ($P_\uparrow(k{=}5)=0$). | Ukraine–Russia 2022+; Iran–Iraq 1980–88 |

> **Ordered list for "adjacency":** T0, T1, T2, T3, T4, T5. Adjacency is single steps.

> **Note on T1 (multiple sources).** MIDB provides global threat/diplomatic-originator coverage 1900–2014. EUSANCT supplements with sender-state threat dyads 1989–2015. The tiers do not distinguish MIDB-threat from EUSANCT-threat — the structural variables and stakes modifier do. Coders should deduplicate across sources by (initiator, target, year).

> **Note on T2 (two populations).** Coercive-prelude sanctions (live dispute, force conceivable) vs expressive/values sanctions (no security stake). The tiers do not distinguish them — the **structural variables and the stakes modifier do** — and the status-quo-biased direction stage should keep expressive-sanctions dyads in overwhelming persistence (§6.7).

> **T4/T5 boundary is a feasibility boundary as well as a magnitude boundary.** A dyad can sit at T4 (limited attributed combat) yet be unable to reach T5 because neither side can wage sustained strategic war against the other (§3.7).

> **WMD incidents at T5.** Tactical or strategic WMD use does not create a separate tier. It enters as a maximum-magnitude $Shock_k$ event at T5, with the magnitude anchored to the IHL-derived consequence threshold: a weapon qualifies for maximum Shock_k magnitude only if its effects are structurally unlimitable *and* of strategic scale (threatening the target state's stability, territorial integrity, or national survival). Tactical/localised WMD use (*e.g.* battlefield CW) enters as a sub-maximal $Shock_k$. The old T6 coding guidance (AP I Arts. 35–36, 51(4)) is preserved as the Shock_k magnitude anchor rather than as a tier gate.

### 1.3 Tier Assignment Rule

Assign the **highest** tier fully supported by operational evidence, descending from T5. Do not mix diplomatic language with operational coding. Caveats: (a) a dyad genuinely between tiers is coded at the nearest tier *and* flagged with the relevant modifier; (b) T3 carries the sustainment and selectivity entry conditions (§1.7), and a sustained deniable T3 is flagged with its Attribution and Duration values so the escalation factor (§1.6.1) is active; (c) **before assigning T5, verify the Capability/Reach gate (§3.7);** (d) WMD use is coded as a $Shock_k$ event at the dyad's current tier rather than as a tier change — magnitude is judged against the IHL-derived consequence threshold (§1.2).

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

v25.x represented a sustained deniable campaign as a *separate tier* (T3-High) on the argument that sustainment converts a transient barrier-suppression into a standing local cost-minimum. v26.0 dropped the tier and represented the same phenomenon as an **escalation-risk contribution to the T3→T4 transition**, built from the interaction of the attribution modifier and dwell time:

$$
\Delta\text{Esc}_{T3\to T4} = u_A \cdot \big(\text{Attribution}\cdot D_{k}\big),\qquad \text{entering } U^{\uparrow}\text{ at } k=\text{T3 (§3.2).}
$$

**The sign logic, and why it does not collide with the lock-in (§1.6.3).** Plain duration is *stabilising* — it raises persistence ($r_D D_k$ in $U^0$) and the down-barrier floor ($b_{dur}D_k$). Duration *multiplied by deniability* is *escalatory*. A sustained, deniable campaign accumulates provocations and erodes the target's tolerance, raising the hazard of a triggering incident that tips T3→T4; a sustained but fully *attributable* low-level standoff simply locks in. Coding the effect as the interaction lets both behaviours coexist: the deniable-campaign corner escalates, the attributable-standoff corner persists.

> **Equivalence to v25.x:** at Attribution $=0$ the factor vanishes and the dyad behaves as plain T3. Calibration should test whether $u_A>0$ improves out-of-sample fit (the parsimonious replacement for the deprecated "does T3-High beat T3-only" test — §6.7).

#### 1.6.2 WMD as Shock_k severity modulator (reformed from T6 gate)

The WMD concept from v26.0 — a weapon whose effects are structurally unlimitable *and* of strategic scale (ICRC standard: AP I Arts. 35–36, 51(4)) — is retained as a **severity anchor** for $Shock_k$ at T5. WMD use is not a tier event; it enters as $Shock_k$ with a magnitude reflecting the IHL-anchored consequence assessment. The coding guidance:

- **Nuclear employment** → Maximum Shock_k magnitude (near-certain persistence at T5, severe escalation pressure).
- **Strategic-scale biological/chemical** → Near-maximum Shock_k magnitude if the expected effect footprint is comparable to a nuclear detonation.
- **Tactical/localised WMD** (battlefield CW, small radiological device) → Sub-maximal Shock_k, proportional to the estimated immediate and contagion effect.
- **No WMD capability** → Shock_k operates normally; no WMD-related amplification.

The old WMD gate's sub-component recording (nuclear, biological, chemical, radiological assessments) is preserved as a coding instruction for Shock_k magnitude rather than for a tier gate. The consistency condition $WMD_i>0 \Rightarrow Cap_{i\to j}\ge\tau$ (§3.7) is retained: a state with strategic-scale WMD capability necessarily has the capacity to inflict considerable, sustainable damage at range, so it clears the T5 reach gate.

#### 1.6.3 Status-quo bias and the role of duration (unchanged from v26.0)

The direction stage is status-quo-biased: at neutral factor values, persistence $P_0$ should dominate, and movement in either direction must be *earned*. Duration appears in **three** consistent places — it raises persistence ($U^0$), raises the down-barrier floor (lock-in, $B_{k\to k-1}$), and — only when multiplied by deniability — raises the T3→T4 escalation hazard ($U^\uparrow$). The first two are distinct channels (whether to stay vs how hard to leave *downward*) and are calibrated separately; they are not double-counting. The net effect is that a dyad whose escalation pressure falls returns to **persistence**, and a long-running conflict resists casual de-escalation unless genuine enablers appear.

**T4 dual-population (new for v27.0).** Empirically, T4 shows near-equal persistence (51.3%) and de-escalation (44.2%), unique among the active tiers. This is consistent with T4 containing two sub-populations: **short-duration skirmishes** (limited border clashes, one-off strikes) that de-escalate to T0 within 1–2 years, and **enduring limited standoffs** (multi-year low-level hostilities) that resemble locked-in T3s in their persistence profile. The Duration variable in $b_{dur}D_k$ should separate these populations: low $D_k$ → low down-barrier → de-escalation accessible; high $D_k$ → high down-barrier → lock-in. Calibration should verify that the T4 persistence tail (dyads with $D_k > 2$ years) shows $P_0$ approaching T3 levels (~80%).

### 1.7 The T3 Entry Condition (patron vs merchant) — unchanged

"Selling weapons to $j$'s enemies" is **not sufficient** for T3. T3 requires support that is an **instrument of hostility toward $j$**, established through observables: (1) **Sustained**, (2) **Selective** (directed at $j$'s adversaries and not $j$ — selectivity is the observable proxy for intent), (3) **Targeted** at $j$'s strategic disadvantage, (4) **Corroborated** by co-moving diplomatic/economic friction. The arms dealer fails on selectivity (sells to both) and codes as not-T3 cleanly.

### 1.8 Model Architecture Summary

```
INPUT CODING (core variables + belief term + modifier vector, per directed dyad i→j)
├─ Each input carries a STATE: observed | defaulted | absent   [drives degradation]
├─ Path Dependency: Current Tier (X_t ∈ {0..5}), Duration (D_k)  [dual role: persistence + lock-in + (×Attribution) escalation]
├─ Structural/Military: Rivalry (Ω), Contiguity (Ξ), First-Mover Adv (FMA), Closing Window (−Ẇ)
├─ Economic: Status-Quo Burden (per-actor), Exhaustion (W_x)
├─ Operational/Diplomatic: Off-Ramp Absence (ORA), Stalemate (Stal_t), Dip Capacity (Dip_cap)
├─ Catalysts/Environment: Kinetic Shock (Shock_k), De-escalation Enabler (DeEsc_k),
│                          WMD Severity Modulator (→ Shock_k ceiling), Capability/Reach Gate (Cap, →T5), Contagion (V_contagion)
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
HARD GATE: Capability/Reach gate (T5) — sole hard gate
RECONCILIATION (§3.6): one-shot best response between the two cost landscapes

DEGRADATION LAYER (§1.9)
├─ Resolve each input's state; drop or default terms accordingly
├─ Select active model member (full ↔ public ↔ myopic ↔ diagnostic-fallback)
├─ Compute confidence penalty from coverage
└─ Emit COVERAGE VECTOR alongside π
```

### 1.9 The Nested-Model Family & Graceful Degradation

The model is a **family of nested members**. Each advanced term has a **documented null value** that, when the term's inputs are absent, reduces the model to a simpler member that is itself fully valid. Degradation is *down the family*, never into undefined behaviour.

#### 1.9.1 The three input states

| State | Meaning | Engine behaviour |
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
| Attribution×Duration escalation | $u_A(\text{Attr}\cdot D_k)$ | Attribution absent → factor dropped | **plain-T3** behaviour |
| Attribution modifier | suppression of upward $B$ | no suppression → barrier at default height | un-discounted transition |
| Integration depth | suppression of patron $B_{T3\to T4}$ | no suppression → default barrier | un-discounted patron transition |
| Stakes modifier | enters $V_i(\cdot)$ | falls back to $\Omega\Xi$ alone | structural-stakes-only |
| Down-barrier duration/tier floor | $b_{tier},b_{dur}$ in $B_{k\to k-1}$ | terms absent → flat $b_0$ floor | **flat-barrier** (v25.x-like) member |
| Capability/Reach | $Cap_{i\to j}$ | **high-salience: fail-loud** (§1.9.6); never silently defaulted | — |
| Intent/selectivity | T3 entry gate | gate unevaluable → see §1.9.4 | (classification fallback) |
| WMD severity | $WMD$ | absent → $Shock_k$ operates without WMD amplification | plain-Shock_k member |
| Cost-field occupancy components | $B^{econ}, B^{blood}, V_i$ | if any absent → fall back to deprecated $E_t/D_t/S_t$ diagnostics for that transition | **diagnostic-fallback** member |

The members form an ordered ladder of richness:

```
full model  ⊃  (drop belief, δ=0)  ⊃  public model
           ⊃  (also drop forward-looking, γ=0)  ⊃  myopic model
           ⊃  (also drop cost-field components)  ⊃  diagnostic-fallback (E_t/D_t/S_t)
```

Orthogonal reductions (do not change the member's tier on this ladder but increase status-quo bias / parsimony): dropping $u_D\,DeEsc_k$ → floor-only de-escalation; dropping the duration/tier floor → flat-barrier; dropping Attribution×Duration → plain-T3; dropping WMD severity → plain-Shock_k. Each ⊃ is a strict reduction. **This is testable** — see §6.9.

#### 1.9.3 Public vs private as members of the family — unchanged

- **Public member.** $\delta = 0$, modifiers at default unless an observable supports them, occupancy costs anchored to open data. Canonical degraded member; auditable on MIDs/UCDP.
- **Private member.** Belief term active with a narrowed band; occupancy costs measured; integration depth from privileged sources.
- **The divergence is an output.** Report $\|\pi^{\text{private}} - \pi^{\text{public}}\|$ as a first-class quantity (§5 step 11).

#### 1.9.4 Renormalise, don't impute — unchanged

Where a term is absent, the model **collapses to the simpler functional form** rather than guessing a placeholder. Special case — **T3 classification when intent/selectivity is absent:** the entry gate cannot be evaluated, so code the dyad at the highest tier supported *without* the proxy claim (typically T1/T2), flag the proxy question unresolved, and fail loud if the consumer requires the classification (§1.9.6).

#### 1.9.5 Confidence penalty from coverage — unchanged

$$
\text{conf} = \text{conf}_0 \cdot \prod_{t \in \text{terms}} \rho_t^{\,\mathbb{1}[t \text{ not observed}]}, \qquad \rho_t \in (0,1]
$$

The point forecast $\pi$ is still emitted; the penalty travels with it.

#### 1.9.6 Fail-soft vs fail-loud

- **Fail-soft (default, early warning / scenario comparison):** degrade down the family, emit $\pi$ + coverage + confidence penalty. Never refuse.
- **Fail-loud (configurable, decision-support claims):** for the **high-salience variables** — $\{Cap, \text{current-tier classification}, \text{T3 entry gate}\}$ — refuse to score and demand the value rather than emit a number that quietly ran without its most important input. $Cap$ is high-salience because it controls the sole hard gate on T5 (§3.7). $WMD$ is **not** high-salience in v27.0 (it is a Shock_k modifier, not a gate); its absence degrades gracefully to the plain-Shock_k member.

---

## PART 2: INPUT VARIABLES & CODING GUIDANCE (CORE VARIABLES + ADDITIONS)

Every input carries a state ∈ {observed, defaulted, absent} (§1.9.1). Variables are bounded **[0,1]** except $V_{contagion}\in[-1,+1]$, $X_t\in\{0,1,2,3,4,5\}$, $D_k\in[0,\infty)$.

### 2.1 Path Dependency

- **CurrentTier ($X_t$)** — operational reality now. Shared. Range $\{0,1,2,3,4,5\}$. **High-salience: fail-loud if unresolvable.**
- **Duration ($D_k$)** — time at current tier, months/10. **Triple role (§1.6.3):** carries memory; raises persistence ($U^0$); raises the down-barrier floor (lock-in); and, multiplied by Attribution, raises the T3→T4 escalation hazard. Default if absent: 0 (freshly entered).

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

- **Kinetic Shock ($Shock_k$)** — [0,1], upward activation energy in $U^\uparrow$. Default 0. **WMD use routes here** (§1.6.2): tactical WMD use that falls below the IHL-derived strategic-consequence threshold enters as a sub-maximal Shock_k; strategic-scale WMD use enters as maximum-magnitude Shock_k. The Shock_k magnitude is the **sole mechanism** for WMD-related escalation pressure in v27.0.

- **De-escalation Enabler ($DeEsc_k$)** — [0,1], the downward mirror of $Shock_k$; supplies activation energy in $U^\downarrow$ (§3.2). Derived composite of the de-escalation enablers already in the model:
  $$
  DeEsc_k = \text{clip}\big(d_W W_x + d_{Dip}Dip_{cap} + d_{off}(1-ORA),\,0,1\big).
  $$
  This is the **direction-stage** use of these enablers — *whether* to descend. Their **allocation-stage** use (*how far* — step-down vs collapse-to-peace) remains $\kappa$ (§3.5.2). Keep the two uses distinct to avoid double-counting (§3.2 caveat). Default 0 (no enabler this period → floor-only de-escalation member).

- **WMD Severity Modulator ($WMD$)** — [0,1], **symmetric**. No longer gates any tier. Acts as a **ceiling-amplifier** for $Shock_k$ at T5: when $WMD>0$, the maximum possible Shock_k magnitude reflects the IHL-anchored consequence assessment (§1.6.2). Sub-components (nuclear, biological, chemical, radiological) are recorded individually for audit. Also informs $Cap$: $WMD_i>0 \Rightarrow Cap_{i\to j}\ge\tau$ (§3.7). **Not high-salience** in v27.0 (absent → plain-Shock_k member, no gate failure). Default 0.

- **Capability/Reach Gate ($Cap_{i\to j}$)** — [0,1], **directional**. Gates **T5** — the sole hard gate in v27.0 (§3.7). $Cap_{i\to j}$ is the assessed capacity of $i$ to inflict **considerable, sustainable** damage on $j$'s **military *or* civilian infrastructure** (maximum over the two target classes — holding the adversary's cities at sustained risk counts even against a military one cannot defeat). The bar is *strategic-war-enabling*, not a single credible blow; a one-off interceptable strike does not clear it. Built from force projection (air/naval/missile/ground reach to $j$'s territory), geographic access (contiguity), basing/allies that extend reach, and penetration of $j$'s defences.

  - **Threshold $\tau$:** the T5 gate opens iff (dyad) $\;\Xi\ge\xi^\* \;\lor\; Cap_{A\to B}\ge\tau \;\lor\; Cap_{B\to A}\ge\tau$ (§3.7).
  - **Dual use:** the *gate* is the threshold crossing on T5; the *raw value* additionally feeds **continuous** escalation pressure into the ungated T4 (a near-incapable microstate gets no hard T4 block but a low $P_\uparrow$ on its own).
  - **Consistency with WMD:** $WMD_i>0 \Rightarrow Cap_{i\to j}\ge\tau$ (a confirmed strategic-WMD capability *is* considerable-damage-at-range).
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
B_{k\to k-1} = \text{clip}\big(b_0 + b_{tier}\cdot\text{idx}(k) + b_{dur}\cdot D_k,\;0,\;\infty\big),\qquad \text{idx}(k)\in\{0,\dots,5\}.
$$

- **The down-barrier is the mechanism of status-quo bias.** Because peace is usually the global minimum, the down-gradient $\mathcal{C}_i(k)-\mathcal{C}_i(k-1)$ is positive almost everywhere; $B_{k\to k-1}$ is sized to absorb the typical positive gradient, grows with tier (higher tiers are stickier to leave) and dwell time (lock-in), and is overcome only by genuine enablers via $u_D\,DeEsc_k$. **De-escalation is now earned, exactly as escalation is.** When escalation pressure falls, mass returns to $P_0$ (persistence), not to $P_\downarrow$.
- $B_{k\to k+1}\ge 0$ is the upward barrier; **absent modifiers leave it at default height** — absence of evidence for deniability ≠ a deniability discount.
- $Shock_k$ supplies upward activation; $DeEsc_k$ supplies downward activation; both default 0. **WMD use routes into $Shock_k$** (§1.6.2, §2.5).
- The **Attribution×Duration** term (§1.6.1) is the former-T3-High escalation factor, active only at the T3→T4 transition.

> **Note on the two duration channels.** $r_D D_k$ (in $U^0$) raises *persistence*; $b_{dur}D_k$ (in $B_{k\to k-1}$) specifically raises *resistance to de-escalation* while leaving escalation reachable. They are distinct channels and calibrated separately (§1.6.3).

> **Configurable alternative (de-escalation enablers as barrier suppression).** Equivalently, one may move the enablers from an additive $U^\downarrow$ term into a suppression of $B_{k\to k-1}$ (mirroring how the attribution/integration modifiers suppress the *upward* barrier). The two forms are near-equivalent at the margin but calibrate differently. The **canonical v27.0 form is the additive activation term** $u_D\,DeEsc_k$ (direct mirror of $u_Z\,Shock_k$); the suppression form is a documented configurable variant.

> **Confounding caveat (unchanged).** If *both* a barrier and the cost levels of a transition are undetermined, the transition is under-identified; fall back to the diagnostic member for that transition rather than emit a falsely precise gradient (§1.9.4).

### 3.3 Direction Probabilities (Softmax = multinomial logit) — unchanged

$$
Z = \exp(U_k^\downarrow) + \exp(U_k^0) + \exp(U_k^\uparrow),\qquad
P_\downarrow = \frac{\exp(U_k^\downarrow)}{Z},\quad P_0 = \frac{\exp(U_k^0)}{Z},\quad P_\uparrow = \frac{\exp(U_k^\uparrow)}{Z}
$$

Boundary constraints: $P_\downarrow(k{=}0)=0$; $P_\uparrow(k{=}5)=0$; adjacency follows the ordered list T0–T5. The softmax is well-defined for any finite $U$-scores, so it survives any combination of dropped terms.

### 3.4 Composition Equation — unchanged

$$
\boxed{\;\pi_{kj} = \begin{cases} P_\downarrow \cdot \omega^-_{kj} & j < k \\[4pt] P_0 & j = k \\[4pt] P_\uparrow \cdot \omega^+_{kj} & j > k \end{cases}\;}
$$

Mass conservation holds exactly since $\sum_{j<k}\omega^-_{kj}=\sum_{j>k}\omega^+_{kj}=1$ (after the hard gate renormalises the upward set — §3.7).

### 3.5 Allocation Stage — Skip Functions

#### 3.5.1 Upward Allocation $\omega^+$

$$
\Sigma^{\uparrow}_{i\to j} = (FMA_{i\to j})^{\eta_\phi}\,(-\dot W_{i\to j})^{\eta_w}\,(ORA)^{\eta_r}
$$

$$
\omega^+_{kj} \propto \exp\!\big[-\lambda^+_k\,(j-k-1)\,(1-\Sigma^\uparrow)\big]\cdot G^+_{kj},\qquad j>k
$$

normalised over $j>k$ **after the hard gate (§3.7) zeroes out unreachable destinations.** Skip distance $(j-k-1)$ is computed on the T0–T5 list. Absent $FMA$ or $-\dot W$ default to 0 → steep decay, mass on the adjacent tier (conservative).

> **WMD term removed from $\Sigma^\uparrow$ (change from v26.0).** v26.0 included $(1-WMD^{\eta_n})$ in $\Sigma^\uparrow$ to suppress skip mass toward T6. With T6 removed, this term is no longer needed. WMD influences escalation solely through the $Shock_k$ ceiling-amplifier (§2.5) and the $Cap$ consistency condition (§3.7).

#### 3.5.2 Downward Allocation $\omega^-$ (Bimodal) — unchanged in form

$$
\omega^-_{kj} \propto (1-\kappa)\exp\!\big[-\lambda^-_k(k-j-1)\big] + \kappa\,C_{kj},\qquad j<k
$$

$$
\kappa = \sigma\!\big(c_0 + c_W W_x + c_{Dip}Dip_{cap} - c_{Stal}Stal_t - c_{ORA}ORA\big)
$$

Step-down = local descent; collapse = a path opening over the ridge to the global minimum. **Division of labour:** $DeEsc_k$ in $U^\downarrow$ governs *whether* the dyad descends at all (direction stage); $\kappa$ governs *how far* it descends (allocation stage). The shared inputs ($W_x, Dip_{cap}, ORA$) appear in both by design but in non-overlapping roles.

### 3.6 Reconciling the Two Directed Runs — as a Game — unchanged

- **Escalation:** $P_\uparrow^{\text{rel}} = \max(P_\uparrow^{A\to B}, P_\uparrow^{B\to A})$ (unilaterally enforceable).
- **De-escalation:** $P_\downarrow^{\text{rel}} = \min(P_\downarrow^{A\to B}, P_\downarrow^{B\to A})$ (requires mutual consent; integration depth can make a patron the gating actor).
- **Persistence:** residual $P_0^{\text{rel}} = 1 - P_\uparrow^{\text{rel}} - P_\downarrow^{\text{rel}}$ (clip at 0, renormalise).

> The Capability/Reach gate is applied at the dyad level *before* reconciliation drives mass into T5 (the OR across directions, §3.7, is the dyad-level analogue of the escalation `max`). **Degradation note:** if one direction is fully coded and the other is sparse, reconcile with the better-covered direction and propagate the *worse* confidence penalty.

### 3.7 Hard Gate

| Gate | Rule |
| --- | --- |
| **Capability/Reach floor (T5)** | The dyad-level disjunction $\;G_{T5}=\mathbb{1}\big[\Xi\ge\xi^\* \;\lor\; Cap_{A\to B}\ge\tau \;\lor\; Cap_{B\to A}\ge\tau\big]$. If $G_{T5}=0$, set $\omega^+_{k,5}=0$ in **both** directed runs; renormalise the upward set over reachable destinations. T5 is unreachable for non-contiguous dyads in which neither side can inflict considerable, sustainable damage. **T4 is ungated** (any actor able to land a credible attributed blow can reach it); $Cap$ still feeds T4 as continuous pressure. T5 is the top tier — no tier above it exists. High-salience: if $Cap$ unresolvable, fail-loud rather than guess the gate. |
| Adjacent baseline | $G^\pm$ default = 1.00. |
| One-tier skip | Default = 0.35. |
| Two-tier skip | Default = 0.10. |
| Three or more skip | Default = 0.02. |

> **Gate consistency.** $WMD_i>0 \Rightarrow Cap_{i\to j}\ge\tau$: any state with a confirmed strategic-WMD capability necessarily has the capacity to inflict considerable, sustainable damage at range, so it clears the T5 reach gate. This replaces the v26.0 condition "$WMD>0\Rightarrow Cap\ge\tau$ (T6-reachable ⇒ T5-reachable)" — with T6 gone, the consistency condition is simply "$WMD>0 \Rightarrow$ T5 is reachable, ergo the gate opens."

> Skip-distance defaults are unchanged in value but are now indexed on the T0–T5 list. The maximum skip distance is T0→T5 (distance 4). Skip distance $(j-k-1)$ at T4→T5 = 0 (adjacent).

### 3.8 Operational Coefficients — with Empirical Priors

v22 priors carry over for retained terms. New v27.0 families are set from the v26.1 transition matrix (§6.7 identification targets) where possible; remaining terms explicitly TBD.

| Param | Default | Source / Constraint |
| --- | --- | --- |
| $a^0$ | 0.20 | unchanged (v22 prior) |
| $r_D$ | 0.03 | unchanged (v22 prior) |
| $u_Z$ (upward shock) | 0.55 | unchanged (v22 prior) |
| $\lambda^+_k$ | 1.20 | unchanged (v22 prior) |
| $\lambda^-_k$ | 1.20 | unchanged (v22 prior) |
| $\alpha_7$ ($\Omega\Xi$, diag.) | 0.50 | unchanged (v22 prior) |
| $\beta_{1,2,3}$ | TBD | Requires cost-data (enterprise survey, SIPRI/trade); cannot be set from transition matrix alone |
| $\gamma$ | TBD | Requires forward-looking data ($-\dot W$ series); transition matrix is myopic by construction |
| $\delta$ | TBD | Requires belief-survey data |
| $B_{k\to k+1}$ (upward) | TBD | must produce observed escalation rates at current-tier priors (target: T1→T4+ = 5.65%, T2→T4+ = 0.90%, T3→T4 = 0.59%) |
| modifier→$B$ suppression | TBD | calibration needed against attribution/integration-depth variation |
| $\kappa$ params $c_\bullet$ | TBD | calibration needed against observed collapse-to-peace vs step-down ratios |
| **$b_0$** (down-barrier floor) | **0.15** | set such that at neutral enablers T2 down-gradient does not produce $P_\downarrow>P_0$ (§6.7 identification) |
| **$b_{tier}$** (tier lock-in) | **0.04** | set such that $P_0$ increases with tier index; must reproduce tier-ordered persistence gradient: T2=77.7%, T3=80.0%, T5=80.4% |
| **$b_{dur}$** (duration lock-in) | **0.10** | set such that long-duration T4 ($D_k>2$) approaches T3 persistence (~80%); short-duration T4 permits the observed 44.2% de-escalation |
| **$u_D$** (de-escalation activation) | **0.40** | must reproduce observed de-escalation rates when $DeEsc_k$ is active; sensitivity target: $DeEsc_k$ spikes → $P_\downarrow$ rises measurably (§6.7) |
| **$d_W,d_{Dip},d_{off}$** ($DeEsc$ weights) | **0.33, 0.33, 0.33** | uniform starting prior; calibration should weight exhaustion heaviest |
| **$u_A$** (Attribution×Duration) | **0.12** | must improve out-of-sample fit on post-2007 deniable-T3 dyads (parsimony test — §6.7) |
| **$\tau$** (Cap threshold) | **0.40** | set such that ~0.85% of T4-year dyads clear it (matching observed T4→T5 rate when Cap is the sole gate) |
| **$\xi^\*$** (contiguity opener) | **0.5** | unchanged from v26.0 |
| $\rho_t$ (confidence retention) | TBD | requires inter-coder reliability data |
| conf$_0$ | 1.00 | unchanged |

> **Sign constraints to impose in calibration:** $b_0,b_{tier},b_{dur},u_D,u_A\ge 0$; the down-barrier should be large enough that at neutral enablers ($DeEsc=0$) a positive down-gradient does not by itself produce $P_\downarrow>P_0$ (the status-quo-bias identification target — §6.7).

> **Empirical anchor notes.** The transition matrix covers T0-T5 across 1900–2025 (~4.4M dyad-year transitions). These are *unconditional* empirical frequencies, not equilibrium fixed-points of the model. The priors above are set such that the model *can* reproduce the observed frequency profile at neutral parameter values; calibration then adjusts for structural variables and modifiers.

---

## PART 4: WORKED EXAMPLE (v27.0 — T0–T5, status-quo bias, reach gate)

### 4.1 Status-quo bias at a sanctioned standoff

Sanctioned dyad $(A\rightarrow B)$ at **T2**, coercive-prelude type. Full-model cost field for actor $A$:

| Tier $j$ | $\mathcal{C}_A(j)$ | Comment |
| --- | --- | --- |
| T1  | 0.55 | conceding the dispute is costly |
| **T2 (now)** | **0.60** | sanctions absorbed; floor raised |
| T3  | 0.50 | sustained selective proxy cheaper |

Inputs: $\text{idx}(\text{T2})=2$, $D_k=0.8$ (8 months at T2), $DeEsc_k=0.1$ (little exhaustion, weak off-ramp), $Shock_k=0$.

**Down-barrier (v27.0):** $B_{T2\to T1}=b_0+b_{tier}\cdot 2+b_{dur}\cdot 0.8$. Using v27.0 priors $b_0=0.15,\,b_{tier}=0.04,\,b_{dur}=0.10$: $B_{T2\to T1}=0.15+0.08+0.08=0.31$. Upward barrier $B_{T2\to T3}=0.05$. $u_D=0.40$.

$$
U^\uparrow = (0.60-0.50) - 0.05 = 0.05,\quad
U^0 = 0.20 + 0.03(0.8) = 0.224,\quad
U^\downarrow = (0.60-0.55) - 0.31 + 0.40(0.1) = -0.22
$$

Softmax → $P_\downarrow\approx0.16,\;P_0\approx0.45,\;P_\uparrow\approx0.39$.

Contrast with the v25.x flat-barrier behaviour ($B_{T2\to T1}\approx0.20$, no $DeEsc$ term): there $U^\downarrow=(0.60-0.55)-0.20=-0.15$, giving $P_\downarrow\approx0.26,\,P_0\approx0.38,\,P_\uparrow\approx0.36$. **v27.0 moves ~10 points of mass off de-escalation and onto persistence**, lengthening the modelled residence time at T2 toward what sanctioned standoffs actually exhibit (empirical T2 persistence = 77.7%). De-escalation now requires $DeEsc_k$ to rise (exhaustion + a real off-ramp), at which point $u_D\,DeEsc_k$ pays the barrier down and $P_\downarrow$ recovers.

### 4.2 Merged-T3 escalation factor

Suppose instead the dyad sits at **T3** with a *sustained, deniable* campaign: Attribution $=0.8$, $D_k=1.5$ (15 months). With $u_A=0.12$, the T3→T4 score gains $u_A(\text{Attr}\cdot D_k)=0.12(0.8\times1.5)=0.144$ — a substantial upward push that did not exist for a fresh or fully-attributable T3. A fully attributable campaign of the same duration (Attribution $=0$) gets none of this push and instead locks in via the down-barrier (larger $b_{dur}D_k$). This reproduces the old T3-High escalation tendency without a separate tier.

### 4.3 Reach gate

Two cases for whether T5 is reachable from this dyad's upward mass:

- **Contiguous rivals** ($\Xi=1$): $G_{T5}=1$ regardless of $Cap$ — T5 reachable; $\omega^+$ may place mass on T5.
- **Non-contiguous, low-reach** ($\Xi=0$, $Cap_{A\to B}=0.2<\tau$, $Cap_{B\to A}=0.15<\tau$): $G_{T5}=0$ — set $\omega^+_{k,5}=0$ and renormalise. All upward mass that would have skipped to T5 piles onto **T4** instead. The dyad can trade sustained limited attributed strikes but cannot mount a strategic war — the correct ceiling for distant rivals with no projection.

### 4.4 WMD as Shock_k severity (v27.0 reform)

A battlefield CW strike by actor $A$ routes as $Shock_k$ with a sub-maximal magnitude reflecting the non-strategic scale of effect. The Shock_k enters $U^\uparrow$ normally, raising $P_\uparrow$ within the dyad's current tier. Because $WMD$ is not a gate in v27.0, the dyad's top reachable tier is governed solely by the Capability/Reach gate. If $A$ independently possesses a strategic-scale WMD capability ($WMD_A>0$), then $Cap_{A\to B}\ge\tau$ by the consistency condition and T5 is reachable — the WMD capability opens the gate *through* $Cap$, not as a separate mechanism.

If neither actor has WMD capability, $Shock_k$ operates without WMD amplification and T5 reachability depends solely on conventional Cap and contiguity. The WMD-vs-no-WMD dyads are distinguished by the Shock_k ceiling and the ease of clearing the $Cap$ gate, not by a separate tier.

---

## PART 5: IMPLEMENTATION WORKFLOW

1. **Assign current tier $X_t$** (shared; range T0–T5). Apply the T3 entry condition (§1.7). If intent/selectivity is absent, use the classification fallback (§1.9.4). **Before assigning T5, evaluate the Capability/Reach gate (§3.7).** WMD incidents are coded as $Shock_k$ events, not as tier changes (§1.6.2). If $X_t$ or $Cap$ is unresolvable, fail-loud (§1.9.6).
2. **Code each input with its state** (observed / defaulted / absent — §1.9.1) for direction $(i\to j)$: $FMA$, $-\dot W$, belief term + uncertainty, directional modifiers (including **Attribution** for the T3→T4 factor), $Cap_{i\to j}$, and **$WMD$ sub-components** (for Shock_k magnitude determination, not for gate evaluation).
3. **Code symmetric variables** ($\Omega,\Xi,W_x,ORA,Stal_t,Dip_{cap},V_{contagion},WMD$), per-actor Status-Quo Burden, and $Duration$, each with a state. Compute $DeEsc_k$ from $W_x,Dip_{cap},(1-ORA)$. For T1 coding, check both MIDB (hostlev=2 + hostlev=1 originators, 1900–2014) and EUSANCT (threat_dyad=1, 1989–2015); deduplicate by (initiator, target, year).
4. **Resolve the active model member** from coverage (§1.9.2): full → public ($\delta=0$) → myopic ($\gamma=0$) → diagnostic-fallback; plus orthogonal reductions (floor-only de-escalation, flat-barrier, plain-T3, plain-Shock_k) as the corresponding inputs drop.
5. **Build the cost field** $\mathcal{C}_i(j)$ with surviving terms; apply modifier→barrier suppression only where modifiers are observed.
6. **Stage 1 (status-quo-biased):** compute $U^\uparrow$ (with the T3 Attribution×Duration term where applicable), $U^0$, and $U^\downarrow$ with the tier/duration down-barrier and the $u_D\,DeEsc_k$ activation; softmax → $(P_\downarrow,P_0,P_\uparrow)$; boundary constraints ($P_\downarrow(k{=}0)=0$, $P_\uparrow(k{=}5)=0$).
7. **Stage 2:** $\Sigma^\uparrow$ (simplified — no WMD term), $\kappa$, $\omega^+$, bimodal $\omega^-$. **Apply hard gate:** Capability/Reach gate on T5 (zero $\omega^+_{k,5}$ if $G_{T5}=0$); renormalise the upward set. T5 is the top tier, no tier beyond it exists.
8. **Compose** via §3.4.
9. **Repeat for the reverse direction**; evaluate the dyad-level reach gate once and apply to both runs.
10. **Reconcile** (§3.6), propagating the worse confidence penalty.
11. **Report** the cost fields, barriers used (including the tier/duration down-barrier values), the modifier vector, the Attribution×Duration escalation contribution, $DeEsc_k$, $Shock_k$ magnitude (including any WMD amplification), belief gap, both directed $\pi$ vectors, the reconciled distribution, the deprecated $E_t/D_t/S_t$ diagnostics, the COVERAGE VECTOR (per-input state + active member + confidence penalty), the $Cap$ sub-assessment and gate result, the $WMD$ sub-component scores, and — if both public and private members were run — the divergence $\|\pi^{\text{private}}-\pi^{\text{public}}\|$ (§1.9.3).

---

## PART 6: VALIDATION, LIMITATIONS & OPEN ISSUES

### 6.1 What "Calibration" Requires Before Any Production Claim

Point estimates **and standard errors** for all coefficients — cost-field weights, $\gamma$, $\delta$, every barrier (including $b_0,b_{tier},b_{dur}$ and the upward $B_{k\to k+1}$), modifier→barrier suppression, $u_D$ and the $DeEsc$ weights, $u_A$, the $Cap$ threshold $\tau$, and the confidence-penalty retention factors $\rho_t$ — via penalised MLE or Bayesian estimation (MIDs 1990–2015; UCDP-dyadic for proxy/T3). Out-of-sample Brier / log-loss / AUROC by tier. Inter-coder reliability (belief term and integration depth expected worst; **$Cap$ "considerable damage" assessments** expected high-variance; $WMD$ sub-component coding for Shock_k magnitude expected moderate-variance). Barrier identification via shocks that "pay" the barrier — symmetrically, **down-barrier identification via observed de-escalations that follow enabler spikes ($DeEsc$)**. Until then, every coefficient is an intelligent guess.

### 6.2 Retained Limitations

Rare-event tails (formerly T6 — now absorbed as maximum-Shock_k events within T5); $V_{contagion}$ needs network analysis; multi-actor wars exceed dyadic simplification (integration depth is the dyadic compression of a triadic reality); single representative decision-maker assumed; the $Cap$ "considerable damage" threshold compresses a continuous capability spectrum into one gate; the WMD Shock_k magnitude anchor compresses a multi-factor consequence assessment into a scalar.

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
- **T4 dual-population (new).** Long-duration T4 ($D_k>2$ years) should show persistence approaching T3 levels (~80%). Short-duration T4 should show de-escalation rates near the empirical 44%. If $b_{dur}$ cannot separate these populations, the down-barrier structure is mis-specified for T4.
- **WMD-as-Shock_k test (replaces T6 gate tests).** Dyads with WMD capability should show elevated Shock_k ceiling at T5 but no separate tier effect. Historical WMD incidents should map to Shock_k magnitudes consistent with the IHL-anchored consequence assessment. If WMD-capable dyads show behaviour indistinguishable from non-WMD dyads at the same Cap level, the Shock_k ceiling-amplifier has no identifying variation.
- **Reach-gate predictions.** Non-contiguous dyads with neither side clearing $\tau$ should never realise T5 and should cap at T4; their upward mass should concentrate on T4. Dyads that acquire strategic reach (new long-range capability, new basing/alliance) should show T5 become reachable at that point and not before. If T5 onsets appear in genuinely no-reach dyads, $\tau$ or the $Cap$ coding is wrong.
- **Tactical WMD coding test.** Historical battlefield CW cases (Syria 2013, Iraq–Kurds 1988) should code as sub-maximal Shock_k and remain ≤ T5. Nuclear employment (Hiroshima/Nagasaki 1945) should code as maximum-magnitude Shock_k at the dyad's current tier (T5, given the strategic-war context).

### 6.8 Proper Use — unchanged

✓ Early warning, scenario comparison, sensitivity analysis. ✗ Deterministic forecasting or point certainty.

### 6.9 Validating the Degradation Architecture

- **Nesting equivalence test.** Set a richer member's extra-term inputs to null; confirm it reproduces the simpler member's $\pi$ to numerical tolerance — including: $u_D=0$/$DeEsc=0$ → floor-only de-escalation; $b_{tier}=b_{dur}=0$ → flat-barrier (v25.x-like); Attribution $=0$ → plain-T3; $WMD=0$ → plain-Shock_k.
- **Public-as-anchor; degraded-vs-full divergence; confidence-penalty calibration; "absent" routing audit** — unchanged.
- **$Cap$ gate audit.** Verify that (a) $G_{T5}=0$ hard-zeroes $\omega^+_{k,5}$ and renormalises; (b) the gate is evaluated once at the dyad level and applied to both directed runs; (c) the disjunction is OR across contiguity and both directional $Cap$; (d) $WMD>0$ forces $Cap\ge\tau$ so WMD-capable dyads always clear the gate; (e) T4 and below are never reach-gated.
- **Status-quo-bias audit.** Verify that with $DeEsc=0$ and a positive down-gradient, $P_0\ge P_\downarrow$ at v27.0 priors, and that raising $DeEsc$ monotonically raises $P_\downarrow$.
- **$WMD$-as-Shock_k audit (new).** Verify that (a) $WMD$ does NOT gate any tier; (b) $WMD>0$ increases the $Shock_k$ ceiling at T5 but does not change the reachable tier set independently of $Cap$; (c) $WMD=0$ gracefully degrades to the plain-Shock_k member.

---

## PART 7: APPENDIX — VARIABLE SUMMARY

| Variable | Name | Type | Range | Directional? | State-aware? | Status |
| --- | --- | --- | --- | --- | --- | --- |
| $X_t$ | Current Tier | State | {0,1,2,3,4,5} | shared | high-salience | **T6 removed** |
| $D_k$ | Duration | State (memory) | [0,∞) | shared | yes | **triple role (persistence, lock-in, ×Attr escalation); T4 dual-population separator** |
| $\Omega$ | Rivalry | Structural | [0,1] | symmetric | yes | unchanged |
| $\Xi$ | Contiguity | Structural | {0,0.5,1} | symmetric | yes | **also feeds Cap gate** |
| $FMA_{i\to j}$ | First-Mover Adv. | Military | [0,1] | directional | yes | unchanged (posterior to Cap) |
| $-\dot W_{i\to j}$ | Closing Window | Military | [0,1] | directional | yes (γ=0 if absent) | unchanged |
| Status-Quo Burden | (was $C_{peace}$) | Economic | [0,1] | per-actor | yes | unchanged |
| $W_x$ | Exhaustion | Economic | [0,1] | symmetric | yes | **feeds $DeEsc_k$** |
| $ORA$ | Off-Ramp Absence | Diplomatic | [0,1] | symmetric | yes | **(1−ORA) feeds $DeEsc_k$** |
| $Stal_t$ | Stalemate | Operational | [0,1] | symmetric | yes | unchanged |
| $Dip_{cap}$ | Diplomatic Cap. | Diplomatic | [0,1] | symmetric | yes | **feeds $DeEsc_k$** |
| $Shock_k$ | Kinetic Shock (upward activation) | Catalyst | [0,1] | symmetric | yes | **WMD use routes here as ceiling-amplified magnitude** |
| $DeEsc_k$ | De-escalation Enabler (downward activation) | Catalyst | [0,1] | symmetric | yes | unchanged |
| $V_{contagion}$ | Regional Contagion | Geopolitical | [-1,+1] | symmetric | yes | unchanged |
| $WMD$ | WMD Severity Modulator — amplifies Shock_k ceiling at T5; sub-components recorded individually for audit; informs Cap ($WMD>0\Rightarrow Cap\ge\tau$) | Severity | [0,1] | symmetric | not high-salience | **reformed from T6 gate to T5 Shock_k modulator** |
| $Cap_{i\to j}$ | Capability/Reach Gate (→T5) — capacity to inflict considerable, sustainable damage on $j$'s military or civilian infrastructure; T5 opens iff $\Xi\ge\xi^\*$ OR either $Cap\ge\tau$; **sole hard gate** | Gatekeeper | [0,1] | directional | high-salience | unchanged from v26.0 |
| $\hat{\mathcal{C}}_i(\mathcal{C}_c)$ | Belief about counterpart costs | Strategic (agency) | est.+conf. | directional | yes (δ=0 if absent) | unchanged |
| Attribution | Modifier axis | Modifier | [0,1] | per-dyad | yes | **also × Duration → T3→T4 escalation** |
| Integration depth | Modifier axis | Modifier | [0,1] | directional | yes | unchanged |
| Stakes | Modifier axis | Modifier | [0,1] | symmetric | yes | unchanged |
| Intent/selectivity | Modifier axis (T3 gate) | Modifier | [0,1] | directional | high-salience | unchanged |
| $\mathcal{C}_i(j)$ | Per-actor cost field | Derived engine | ℝ per tier | per-actor | — | unchanged |
| $B_{k\to k+1}$ | Upward activation barrier | Derived/transition | [0,∞) | per transition | — | unchanged |
| $B_{k\to k-1}$ | Downward barrier $=b_0+b_{tier}\,\text{idx}(k)+b_{dur}D_k$ | Derived/transition | [0,∞) | per transition | — | **empirical priors set** |
| $u_A,u_D,b_0,b_{tier},b_{dur},\tau,\xi^\*$ | v27.0 coefficients | Calibration | per def. | — | — | **empirical priors set; full MLE/Bayes pending** |
| input **state** | observed/defaulted/absent | Meta | {3 states} | per input | — | unchanged |
| coverage vector | active member + states + penalty | Output | — | — | — | unchanged |
| $\rho_t$ | Confidence retention factor | Calibration | (0,1] | per term | — | unchanged |

---

**Version 27.0 | Specification & Initial Calibration Phase | T6 Collapsed · WMD Reformed as Shock_k Severity Modulator · Empirical Priors from v26.1 Transition Matrix · EUSANCT Threat Data Added to T1 · T4 Dual-Population Characterised · Status-Quo-Biased Direction Stage · Capability/Reach Sole Hard Gate on T5 · Attribution×Duration Escalation Factor · Graceful-Degradation Architecture · Nested-Model Family · Public/Private Layering | June 2026**
