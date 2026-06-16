Unified Equation of Interstate War (Directed-Dyad Variant) v25.0

# Unified Equation of Interstate War (Directed-Dyad Variant) v25.0

## Complete Specification with Full Context & Definitions

**Version:** 25.0 (Graceful-Degradation Architecture; Nested-Model Family; Public/Private Information Layering)  
**Status:** Specification Phase — Awaiting Empirical Calibration (NOT production-validated)  
**Last Updated:** May 2026

* * *

## PART 0: VERSION 25.0 CHANGES FROM 24.0

v24.0 established the cost-field engine, the modifier axes, the belief term, and the T3-High tier. v25.0 keeps all of that **unchanged in substance** and adds one structural commitment: **the model is a nested family, not a single monolith.** Every advanced term has a documented null value that reduces the model to a strictly simpler, still-valid member. Missing inputs degrade the model down the family rather than breaking it or distorting it.

This change is motivated by two practical needs:

1.  **Information asymmetry.** An outside analyst (public information only) and an intelligence consumer (privileged information) should run *the same model* with different inputs revealed, not two divergent codebases. The public model is the member with the belief coupling off and modifiers at default; the private model adds those inputs back on top.
2.  **Robustness.** Real coding situations have missing variables. The model must produce a sensible — and *visibly* degraded — forecast rather than a falsely precise one or a crash.

| Element | v24.0 | v25.0 |
| --- | --- | --- |
| **Model identity** | Single specification with optional terms | **Nested family; each missing input drops to a strictly simpler valid member** |
| **Missing-input behavior** | Undefined / ad hoc | **Documented null value per term; "absent" routed separately from "zero"** |
| **Belief term** | Belief coupling $\delta\,\Phi(\cdot)$ | Unchanged; **$\delta=0$ is the canonical public/belief-blind member** |
| **Modifiers** | Suppress specific barriers | Unchanged; **absent modifier = no suppression = default barrier height** |
| **Forward-looking term** | $\gamma\,\mathbb{E}[\cdot]$ | Unchanged; **$\gamma=0$ yields a valid myopic member** |
| **Output report** | Cost fields, barriers, modifier vector, $\pi$ | **Adds a COVERAGE VECTOR: which terms were active / defaulted / dropped, plus a confidence penalty** |
| **Public vs private** | Discussed informally | **Formalized as two coding protocols over one engine; their divergence is itself an output** |
| **Fail mode** | Unspecified | **Fail-soft (degrade + flag) for early warning; fail-loud configurable for high-salience variables** |
| **Engine, tiers, Core 13, composition, allocation, gates** | —   | **UNCHANGED from v24.0** |

**Why this matters.** v24's reviewer flagged that the belief term, integration depth, and the latent occupancy costs are the hardest inputs to code and the most likely to become overfitting sponges. Those same inputs are exactly what distinguishes a privileged coder from an open-source one. By making the model degrade gracefully along the line between observable and privileged information, v25.0 turns that fragility into structure: the simpler members are auditable and calibratable; the richer members are structured overlays whose *divergence from the simpler member is the signal*.

* * *

## PART 1: OVERVIEW & ARCHITECTURE

### 1.1 What This Model Does

The Unified Equation of Interstate War (UIW) v25.0 is a **directed-dyad stochastic-game model** for estimating next-period interstate conflict escalation, persistence, and de-escalation. For an ordered pair $(i \rightarrow j)$ — "the prospect of $i$ escalating against $j$" — it estimates the full distribution over next-period tiers. Each actor is a forward-looking agent minimizing a per-actor cost field over a *shared* state variable (the relationship tier), under uncertainty about the other's costs.

The model is **two-stage** plus a reframed engine (all unchanged from v24.0):

0.  **Cost field (engine).** For acting agent $i$, evaluate the cost-to-occupy each reachable tier, $\mathcal{C}_i(j)$ — occupancy cost + a forward-looking strategic term + a belief coupling to the counterpart's costs.
1.  **Direction stage.** Movement scores are *cost gradients* between the current tier and adjacent tiers, each penalized by an inter-tier activation barrier. Softmax → $(P_\downarrow, P_0, P_\uparrow)$.
2.  **Allocation stage.** Conditional on a direction, distribute that direction's mass across reachable destination tiers via skip weights $\omega^+$ (upward, catalytic) and $\omega^-$ (downward, bimodal).

The output is the composition $\pi_{kj}(t) = \text{Pr}(\text{next tier} = j \mid \text{current tier} = k, \text{ inputs at } t)$, a vector over the ordered tier list summing to 1, **accompanied by a coverage vector** (§1.9) describing how much of the machinery was actually fed.

**Recommended forecast interval:** 30 days. See §1.5 for the slow-variable caveat.

### 1.2 Escalation Taxonomy (UNCHANGED from v24.0 — T3-High; tiers are cuts on a continuum)

Tiers are **analyst-imposed cuts on a continuum**, not quantized states. Each cut must earn its place empirically (§6.7).

| **Tier** | **Name** | **Military Activity** | **Operational Definition** | **Examples** |
| --- | --- | --- | --- | --- |
| **T0** | Peace | None | No military activity or threat thereof | US–Canada 2020 |
| **T1** | Diplomatic Crisis | None | Formal friction: protests, recalls, ultimatums, UN votes | US–Iran 2019 |
| **T2** | Economic Coercion | None | Active sanctions, trade restrictions, financial exclusion | Russia–West 2014 |
| **T3** | Proxy/Indirect Military | Passive support only | *Sustained, selective* material support to $j$'s adversaries, directed at $j$; $i$ not in direct combat. See §1.7. | Iran funding Hezbollah |
| **T3-High** | Sustained Gray-Zone Campaign | Deniable kinetic, sustained | A *resourced, directed, multi-period* campaign of deniable strikes / sabotage / cyber-with-physical-effect. A **latched** tier (min. $D_k$ + observable effort). One-off deniable acts are $Shock_k$, not this tier. | Israel–Iran shadow war; pre-2022 Donbas |
| **T4** | Limited Direct Military | Acknowledged direct combat | Open, attributed exchange of fire between $i$ and $j$ forces | USS *Reuben James* 1941 |
| **T5** | Strategic War | Expansive conventional | Nationwide / multi-front warfare, sustained campaigns | Ukraine–Russia 2022+ |
| **T6** | Nuclear Exchange | Nuclear weapons used | Nuclear weapons detonated in anger | Japan 1945 |

> **Ordered list for "adjacency":** T0, T1, T2, T3, T3-High, T4, T5, T6. T3-High sits between proxy support and acknowledged combat in *escalation* terms, but it is high on a *different* axis (attribution-suppressed harm); its tier status is earned by *sustainment*.

> **Note on T2 (two populations).** Coercive-prelude sanctions (live dispute, force conceivable) vs expressive/values sanctions (no security stake). The tiers do not distinguish them — the **structural variables and the stakes modifier do**.

### 1.3 Tier Assignment Rule (UNCHANGED in spirit)

Assign the **highest** tier fully supported by operational evidence, descending from T6. Do not mix diplomatic language with operational coding. Caveats: (a) a dyad genuinely between tiers is coded at the nearest tier *and* flagged with the relevant modifier; (b) T3 and T3-High carry sustainment and selectivity conditions (§1.7).

### 1.4 Directed-Dyad Convention (UNCHANGED)

A dyad is an **ordered pair** $(i \rightarrow j)$. Run twice. Current tier $k$ is shared; directional variables carry the acting actor's subscript; symmetric variables take the same value both ways. The two runs are the **two players' cost landscapes over the same state variable**. War is what happens when those landscapes disagree about where the minimum lies and no belief correction intervenes before a barrier is crossed (§3.6).

### 1.5 Forecast-Interval Caveat (UNCHANGED)

Slow structural inputs ($\Omega, \Xi, -\dot{W}$) are near-constant over 30 days; period-to-period variation comes from fast inputs ($Shock_k$, $Dip_{cap}$, $V_{contagion}$, belief updates). Slow variables set the baseline landscape; fast variables provide timing; shocks supply activation energy.

### 1.6 The Modifier-Axes Structure (UNCHANGED)

| Modifier axis | What it captures | Where it acts | Canonical case |
| --- | --- | --- | --- |
| **Attribution** | Deniability of harm | Suppresses upward barrier $B$; sustained → latches T3-High | Israel–Iran shadow war |
| **Integration depth** | Patron entanglement short of combat | Suppresses patron's $T3\to T4$ barrier; gates patron de-escalation | US–Ukraine vs Russia |
| **Stakes** | Existential vs peripheral | Enters $V_i(\cdot)$ via $\Omega\Xi$; separates expressive from coercive-prelude T2 | Values-sanctions vs prelude |
| **Intent/selectivity** | Hostile-directed vs indifferent commerce | T3 entry gate (§1.7) | Arms dealer selling to both sides |

A tier label alone is not a state. Coding records *tier + modifier vector*.

#### 1.6.1 Why sustainment converts a modifier into a tier (T3-High) — UNCHANGED

A one-off deniable strike is an *event* ($Shock_k$). A *sustained* deniable campaign is a *state* with its own residence time and characteristic exits. Sustainment converts transient barrier-suppression into a standing local cost-minimum.

### 1.7 The T3 Entry Condition (patron vs merchant) — UNCHANGED

"Selling weapons to $j$'s enemies" is **not sufficient** for T3. T3 requires support that is an **instrument of hostility toward $j$**, established through observables: (1) **Sustained**, (2) **Selective** (directed at $j$'s adversaries and not $j$ — selectivity is the observable proxy for intent), (3) **Targeted** at $j$'s strategic disadvantage, (4) **Corroborated** by co-moving diplomatic/economic friction. The arms dealer fails on selectivity (sells to both) and codes as not-T3 cleanly.

### 1.8 Model Architecture Summary (UPDATED — coverage tracking added)

```
INPUT CODING (CORE 13 + belief term + modifier vector, per directed dyad i->j)
├─ Each input carries a STATE: observed | defaulted | absent   [NEW: drives degradation]
├─ Path Dependency: Current Tier (X_t), Duration (D_k)
├─ Structural/Military: Rivalry (Ω), Contiguity (Ξ), First-Mover Adv (FMA), Closing Window (-Ẇ)
├─ Economic: Status-Quo Burden (per-actor), Exhaustion (W_x)
├─ Operational/Diplomatic: Off-Ramp Absence (ORA), Stalemate (Stal_t), Dip Capacity (Dip_cap)
├─ Catalysts/Environment: Kinetic Shock (Shock_k), Nuclear Gate (Nuc), Contagion (V_contagion)
├─ BELIEF: Ĉ_i(C_c) — estimate of counterpart cost field + uncertainty   [gated by δ]
└─ MODIFIER VECTOR: attribution, integration depth, stakes, intent/selectivity

ENGINE — PER-ACTOR COST FIELD  C_i(j)
├─ Occupancy cost: economic burden + blood/matériel burden − value extracted at tier j
├─ Status-quo floor; cost-of-war differential
├─ Strategic term: forward-looking (gated by γ)
└─ Belief coupling: depends on i's estimate of c's costs (gated by δ)

STAGE 1 — DIRECTION (cost gradients across activation barriers) → softmax → (P↓, P0, P↑)
STAGE 2 — ALLOCATION (UNCHANGED): ω⁺ catalytic, ω⁻ bimodal
COMPOSITION (UNCHANGED): π_j = P↓·ω⁻ (j<k) ; P0 (j=k) ; P↑·ω⁺ (j>k)
RECONCILIATION (§3.6): one-shot best response between the two cost landscapes

DEGRADATION LAYER (NEW — §1.9)
├─ Resolve each input's state; drop or default terms accordingly
├─ Select active model member (full ↔ public ↔ myopic ↔ diagnostic-fallback)
├─ Compute confidence penalty from coverage
└─ Emit COVERAGE VECTOR alongside π
```

### 1.9 The Nested-Model Family & Graceful Degradation (NEW — core of v25.0)

The model is a **family of nested members**. Each advanced term has a **documented null value** that, when the term's inputs are absent, reduces the model to a simpler member that is itself fully valid. Degradation is *down the family*, never into undefined behavior.

#### 1.9.1 The three input states

Every input is coded with one of three states. This is the load-bearing distinction of v25.0:

| State | Meaning | Engine behavior |
| --- | --- | --- |
| **observed** | A real coded value (any number in range, including 0) | Used as-is |
| **defaulted** | Not coded; a documented neutral default applies | Default substituted; flagged in coverage |
| **absent** | Explicitly unobservable for this dyad | The *term* is dropped from the cost field / barrier set; flagged in coverage |

> **Critical: "absent" ≠ "zero."** A missing belief term is *not* "I am confident the counterpart's costs are zero." The first drops the $\delta\Phi(\cdot)$ contribution entirely; the second is a real, dangerous coding (a confidently-wrong low-cost belief — §6.7). Because the belief input is a *pair* (point estimate + confidence), the coder has a third channel — state = absent — that routes to the degenerate path and can never be silently read as an extreme value. The same applies to every advanced term.

#### 1.9.2 Documented null values (the degradation table)

| Term | Symbol | Null value when absent | Resulting member |
| --- | --- | --- | --- |
| Belief coupling | $\delta\,\Phi(\hat{\mathcal{C}}_i(\mathcal{C}_c))$ | $\delta = 0$ → term dropped | **belief-blind / public** member |
| Forward-looking | $\gamma\,\mathbb{E}[\mathcal{C}_i(\text{future})\mid j]$ | $\gamma = 0$ → term dropped | **myopic** member |
| Attribution modifier | suppression of upward $B$ | no suppression → barrier at default height | un-discounted transition |
| Integration depth | suppression of patron $B_{T3\to T4}$ | no suppression → default barrier | un-discounted patron transition |
| Stakes modifier | enters $V_i(\cdot)$ | falls back to $\Omega\Xi$ alone | structural-stakes-only |
| Intent/selectivity | T3 entry gate | gate unevaluable → see §1.9.4 | (classification fallback) |
| Cost-field occupancy components | $B^{econ}, B^{blood}, V_i$ | if any absent → fall back to deprecated $E_t/D_t/S_t$ diagnostics for that transition | **diagnostic-fallback** member |

The members form an ordered ladder of richness:

```
full model  ⊃  (drop belief, δ=0)  ⊃  public model
            ⊃  (also drop forward-looking, γ=0)  ⊃  myopic model
            ⊃  (also drop cost-field components)  ⊃  diagnostic-fallback (E_t/D_t/S_t)
```

Each ⊃ is a strict reduction: the richer member equals the simpler one when the dropped term's input is set to its null. **This is testable** — see §6.9.

#### 1.9.3 Public vs private as members of the family

The public and private models are **not two codebases.** They are two coding protocols over one engine:

- **Public member.** $\delta = 0$ (belief-blind), modifiers at default unless an observable supports them, occupancy costs anchored to open data (trade/sanctions indices, troop deployments, casualty rates). Auditable and calibratable on MIDs/UCDP. This is the canonical degraded member.
- **Private member.** Belief term active with a narrowed uncertainty band; occupancy costs replaced by measured ones; integration depth coded from privileged sources. Same engine, more inputs revealed, tighter priors.

> **The divergence is an output.** Where the private member's $\pi$ departs from the public member's $\pi$ is exactly where privileged information is doing work. A confidently-wrong belief configuration shows up as a large public/private divergence. Report $\|\pi^{\text{private}} - \pi^{\text{public}}\|$ as a first-class quantity (§5 step 10).

#### 1.9.4 Renormalize, don't impute

Where a term is absent, the model **collapses to the simpler functional form** rather than guessing a placeholder. Imputing a "typical" belief gap injects fake signal; dropping the term injects none. The softmax (§3.3) and composition (§3.4) remain valid under term-dropping because they only require the $U$\-scores to be finite and comparable — dropping a term changes the value of a $U$\-score but not its existence.

Special case — **T3 classification when intent/selectivity is absent.** The entry gate cannot be evaluated, so the model must not silently assign or deny T3. Instead it codes the dyad at the highest tier supported *without* the proxy claim (typically T1/T2 from the observable friction), flags the proxy question as unresolved in coverage, and — if the consumer requires it — fails loud on this specific classification (§1.9.6). Allocation/skip cannot patch a classification hole (it governs transitions of an already-placed dyad), so this must be handled at assignment.

#### 1.9.5 Confidence penalty from coverage

Each degraded or dropped term widens the forecast's uncertainty. The reported confidence is penalized monotonically in the number and salience of non-observed terms:

$$
\text{conf} = \text{conf}_0 \cdot \prod_{t \in \text{terms}} \rho_t^{\,\mathbb{1}[t \text{ not observed}]}, \qquad \rho_t \in (0,1]
$$

where $\rho_t$ is a per-term retention factor (TBD in calibration; smaller = more salient term). The point forecast $\pi$ is still emitted; the penalty travels with it so a richly-fed and a sparsely-fed $\pi$ are never presented as equally trustworthy.

#### 1.9.6 Fail-soft vs fail-loud

- **Fail-soft (default, for early warning / scenario comparison):** degrade down the family, emit $\pi$ + coverage + confidence penalty. Never refuse.
- **Fail-loud (configurable, for decision-support claims):** for a designated set of **high-salience variables** (e.g. $Nuc$, current-tier classification, the T3 entry gate), refuse to score and demand the value rather than emit a number that quietly ran without its most important input. The high-salience set is a deployment choice, not a model constant.

* * *

## PART 2: INPUT VARIABLES & CODING GUIDANCE (THE CORE 13 + ADDITIONS)

Unchanged from v24.0 except that **every input now carries a state ∈ {observed, defaulted, absent}** (§1.9.1). Variables are bounded **\[0,1\]** except $V_{contagion}\in[-1,+1]$, $X_t\in\{0,1,2,3,\text{3H},4,5,6\}$, $D_k\in[0,\infty)$.

### 2.1 Path Dependency

- **CurrentTier ($X_t$)** — operational reality now. Shared. Includes T3-High. **High-salience: defaults to fail-loud if unresolvable.**
- **Duration ($D_k$)** — time at current tier, months/10. Carries memory; latches T3-High. Default if absent: 0 (treated as freshly entered).

### 2.2 Structural & Military

- **Rivalry ($\Omega$)** — \[0,1\], symmetric. Default: historical base rate for the region if absent.
- **Contiguity ($\Xi$)** — {0,0.5,1}, symmetric. Almost always observable; default 0.
- **First-Mover Advantage ($FMA_{i\to j}$)** — \[0,1\], directional. Default 0 (no assumed advantage).
- **Closing Window ($-\dot{W}_{i\to j}$)** — \[0,1\], directional; drives the forward-looking term. **If absent, $\gamma$ effectively 0 for this dyad (myopic member).**

### 2.3 Economic

- **Status-Quo Burden (was $C_{peace}$)** — observable burden of occupying the current tier; per-actor; \[0,1\]. Anchor to open data in the public member. If fully absent, fall back to diagnostic member for affected transitions.
- **Exhaustion ($W_x$)** — \[0,1\], symmetric. Default 0.

### 2.4 Operational & Diplomatic

- **Off-Ramp Absence ($ORA$)** — \[0,1\]. Default 0.5 (neutral).
- **Stalemate ($Stal_t$)** — \[0,1\]. Default 0.5.
- **Diplomatic Capacity ($Dip_{cap}$)** — \[0,1\]. Default 0.5.

### 2.5 Catalysts & Environment

- **Kinetic Shock ($Shock_k$)** — \[0,1\], activation energy. Default 0 (no shock this period).
- **Nuclear Gate ($Nuc$)** — \[0,1\], symmetric. **High-salience: fail-loud if unresolvable** (it controls a hard gate). 0 if neither side nuclear.
- **Bidirectional Contagion ($V_{contagion}$)** — \[-1,+1\], symmetric, lag ≥1 period, instrument with distance-to-regional-conflict. Default 0 if absent.

### 2.6 Belief Term

- **Belief about counterpart costs ($\hat{\mathcal{C}}_i(\mathcal{C}_c)$)** — directional; coded as point estimate + confidence $[0,1]$, **or state = absent**. When absent, $\delta=0$ → public/belief-blind member. A confidently *wrong* belief (low uncertainty, large gap) is the most dangerous configuration and is distinct from absence.

### 2.7 Modifier Vector

Coded from observables; layered on the tier. Each carries a state.

- **Attribution** \[0,1\] — deniability. Absent → no barrier suppression.
- **Integration depth** \[0,1\], directional — patron entanglement. Absent → no patron-barrier suppression.
- **Stakes** \[0,1\] — carried by $\Omega\Xi$. Absent → falls back to $\Omega\Xi$ alone.
- **Intent/selectivity** \[0,1\], directional — T3 entry gate. Absent → classification fallback (§1.9.4), possibly fail-loud.

* * *

## PART 3: MATHEMATICAL SPECIFICATION

### 3.0 The Cost Field (engine — UNCHANGED form; degradation noted)

For acting actor $i$ contemplating tier $j$ against counterpart $c$:

$$
\mathcal{C}_i(j) = \underbrace{\beta_1 B^{econ}_i(j) + \beta_2 B^{blood}_i(j) - \beta_3 V_i(j)}_{\text{occupancy cost at } j} + \underbrace{\gamma\, \mathbb{E}\!\left[\mathcal{C}_i(\text{future}) \mid j\right]}_{\text{strategic / forward-looking}} + \underbrace{\delta\, \Phi\!\big(\hat{\mathcal{C}}_i(\mathcal{C}_c(j))\big)}_{\text{belief coupling}}
$$

**Degradation of the engine (NEW):**

- If the belief input is **absent**, set $\delta = 0$: the third term vanishes; $\mathcal{C}_i(j)$ is well-defined from occupancy + strategic alone.
- If $-\dot W$ is **absent**, set $\gamma = 0$: the second term vanishes; $\mathcal{C}_i(j)$ is the myopic occupancy cost.
- If any occupancy component ($B^{econ}, B^{blood}, V_i$) is **absent** for tier $j$, the cost level $\mathcal{C}_i(j)$ is undetermined; that transition falls back to the deprecated $E_t/D_t/S_t$ diagnostics (§3.1) and the coverage flag marks the transition as diagnostic-grade.
- A dropped term changes the *value* of $\mathcal{C}_i(j)$ but never its existence; the gradients (§3.2) and softmax (§3.3) remain valid.

**Encoded consequences (UNCHANGED):** sanctions raise $B^{econ}_i(k)$ and lower $B^{econ}_i(\text{war tiers})$; expressive sanctions keep war tiers expensive (persistence); the global minimum is usually T0 but barriers prevent the fall; modifiers act on barriers, not on $\mathcal{C}$ levels directly.

### 3.1 Composite Indices ($E_t, D_t, S_t$ — DEPRECATED to diagnostics; now also the fallback member)

Retained as **reported diagnostics** *and* as the **diagnostic-fallback member** invoked when cost-field components are absent (§1.9.2). v22 forms (with $\Omega\Xi$ interaction):

**Escalation Pressure ($E_t$):** $\;\text{clip}(\alpha_1\Omega + \alpha_2\Xi + \alpha_3 FMA_{i\to j} + \alpha_4(-\dot W_{i\to j}) + \alpha_5 C_{peace} + \alpha_6 V_{contagion} + \alpha_7(\Omega\cdot\Xi),\,0,1)$  
**De-Escalation Capacity ($D_t$):** $\;\text{clip}(\theta_1 W_x + \theta_2 Dip_{cap} + \theta_3(1-C_{peace}) - \theta_4 V_{contagion},\,0,1)$  
**Persistence Lock ($S_t$):** $\;\text{clip}(\rho_1 Stal_t + \rho_2 ORA + \rho_3 D_k + \rho_4 V_{contagion},\,0,1)$

> The $\Omega\Xi$ interaction is preserved in the full model by entering $V_i(\cdot)$. The diagnostic forms let any term degrade gracefully: when the cost field cannot be built, these still produce a coarse, valid direction signal.

### 3.2 Movement Scores — Cost Gradients with Barriers (UNCHANGED)

$$
U_k^{\uparrow} = \big[\mathcal{C}_i(k) - \mathcal{C}_i(k+1)\big] - B_{k\to k+1} + u_Z\, Shock_k
$$

$$
U_k^{0} = a_k^{0} + r_D\, D_k
$$

$$
U_k^{\downarrow} = \big[\mathcal{C}_i(k) - \mathcal{C}_i(k-1)\big] - B_{k\to k-1}
$$

- $B_{k\to j}\ge 0$ is the activation barrier. **Absent modifiers leave barriers at default height** — the correct neutral behavior (absence of evidence for deniability ≠ a deniability discount).
- $Shock_k$ supplies activation energy; default 0 if absent.
- **Confounding caveat (NEW emphasis):** if *both* a barrier and the cost levels of a transition are undetermined (modifier absent *and* occupancy component absent), the transition is under-identified. The model must fall back to the diagnostic member for that transition rather than emit a falsely precise gradient (§1.9.4).

### 3.3 Direction Probabilities (Softmax = multinomial logit — UNCHANGED)

$$
Z = \exp(U_k^\downarrow) + \exp(U_k^0) + \exp(U_k^\uparrow)
$$

$$
P_\downarrow = \frac{\exp(U_k^\downarrow)}{Z},\quad P_0 = \frac{\exp(U_k^0)}{Z},\quad P_\uparrow = \frac{\exp(U_k^\uparrow)}{Z}
$$

Boundary constraints unchanged: $P_\downarrow(k{=}0)=0$; $P_\uparrow(k{=}6)=0$; adjacency follows the ordered list. The softmax is well-defined for any finite $U$\-scores, so it survives any combination of dropped terms.

### 3.4 Composition Equation (UNCHANGED)

$$
\boxed{\;\pi_{kj} = \begin{cases} P_\downarrow \cdot \omega^-_{kj} & j < k \\[4pt] P_0 & j = k \\[4pt] P_\uparrow \cdot \omega^+_{kj} & j > k \end{cases}\;}
$$

Mass conservation holds exactly since $\sum_{j<k}\omega^-_{kj}=\sum_{j>k}\omega^+_{kj}=1$.

### 3.5 Allocation Stage — Skip Functions (UNCHANGED)

#### 3.5.1 Upward Allocation $\omega^+$

$$
\Sigma^{\uparrow}_{i\to j} = (FMA_{i\to j})^{\eta_\phi}\,(-\dot W_{i\to j})^{\eta_w}\,(ORA)^{\eta_r}\,(1 - Nuc^{\eta_n})
$$

$$
\omega^+_{kj} \propto \exp\!\big[-\lambda^+_k\,(j-k-1)\,(1-\Sigma^\uparrow)\big]\cdot G^+_{kj},\qquad j>k
$$

normalized over $j>k$. Absent $FMA$ or $-\dot W$ default to 0, which collapses $\Sigma^\uparrow$ toward 0 → steep decay, mass on the adjacent tier — a conservative skip assumption.

#### 3.5.2 Downward Allocation $\omega^-$ (Bimodal)

$$
\omega^-_{kj} \propto (1-\kappa)\exp\!\big[-\lambda^-_k(k-j-1)\big] + \kappa\,C_{kj},\qquad j<k
$$

$$
\kappa = \sigma\!\big(c_0 + c_W W_x + c_{Dip}Dip_{cap} - c_{Stal}Stal_t - c_{ORA}ORA\big)
$$

Step-down = local descent; collapse = a path opening over the ridge to the global minimum.

### 3.6 Reconciling the Two Directed Runs — as a Game (UNCHANGED)

- **Escalation:** $P_\uparrow^{\text{rel}} = \max(P_\uparrow^{A\to B}, P_\uparrow^{B\to A})$ (unilaterally enforceable).
- **De-escalation:** $P_\downarrow^{\text{rel}} = \min(P_\downarrow^{A\to B}, P_\downarrow^{B\to A})$ (requires mutual consent; integration depth can make a patron the gating actor).
- **Persistence:** residual $P_0^{\text{rel}} = 1 - P_\uparrow^{\text{rel}} - P_\downarrow^{\text{rel}}$ (clip at 0, renormalize).

> Default reporting approximation to a true equilibrium computation; flag for calibration. **Degradation note:** if one direction is fully coded and the other is sparse, reconcile with the better-covered direction and propagate the *worse* of the two confidence penalties.

### 3.7 Hard Gates (UNCHANGED)

| Gate | Rule |
| --- | --- |
| Nuclear floor | If $Nuc=0$, set $\omega^+_{k,6}=0$; renormalize. |
| Adjacent baseline | $G^\pm$ default = 1.00. |
| Two-tier skip | Default = 0.35. |
| Three-tier skip | Default = 0.10. |
| Larger skip | Default = 0.02. |

$Nuc$ is high-salience (§2.5): if unresolvable, fail-loud rather than guess the gate.

### 3.8 Default Operational Coefficients (PRIORS, not calibrated)

v22 priors carry over for retained terms. New families remain explicitly TBD: $\beta_{1,2,3}$, $\gamma$, $\delta$, $\Phi$ shape, barriers $B_{k\to j}$, modifier→barrier suppression, **and the per-term retention factors $\rho_t$ for the confidence penalty (§1.9.5)**.

| Param | Default | Param | Default | Param | Default |
| --- | --- | --- | --- | --- | --- |
| $a^0$ | 0.20 | $r_D$ | 0.03 | $u_Z$ | 0.55 |
| $\lambda^+_k$ | 1.20 | $\lambda^-_k$ | 1.20 | $\alpha_7$ ($\Omega\Xi$, diag.) | 0.50 |
| $\beta_{1,2,3}$ | TBD | $\gamma$ | TBD | $\delta$ | TBD |
| $B_{k\to j}$ | TBD | modifier→$B$ suppression | TBD | $\kappa$ params $c_\bullet$ | TBD |
| $\rho_t$ (confidence retention) | TBD | conf$_0$ | 1.00 | —   | —   |

* * *

## PART 4: WORKED EXAMPLE (now showing degradation)

Sanctioned dyad $(A\rightarrow B)$ at **T2**, coercive-prelude type. Full-model cost field for actor $A$:

| Tier $j$ | $\mathcal{C}_A(j)$ | Comment |
| --- | --- | --- |
| T1  | 0.55 | conceding the dispute is costly |
| **T2 (now)** | **0.60** | sanctions absorbed; floor raised |
| T3  | 0.50 | sustained selective proxy cheaper |
| T3-High | 0.48 | deniable campaign: low attributable cost |

Barriers: $B_{T2\to T3}=0.05$, $B_{T2\to T1}=0.20$.

**Full model — Stage 1:**

$$
U^\uparrow = (0.60-0.50) - 0.05 + 0.55(0.20) = 0.16,\quad U^\downarrow = (0.60-0.55) - 0.20 = -0.15,\quad U^0 = 0.20 + 0.03(0.50) = 0.215
$$

Softmax → $P_\downarrow\approx0.26,\;P_0\approx0.38,\;P_\uparrow\approx0.36$.

**Degraded run — belief term absent (public member, $\delta=0$).** Suppose the full-model T3 cost included a $\delta\Phi$ contribution of $-0.04$ (A believes B folds cheaply, making escalation look cheaper). Dropping it raises $\mathcal{C}_A(\text{T3})$ from 0.50 to 0.54:

$$
U^\uparrow = (0.60-0.54) - 0.05 + 0.55(0.20) = 0.12
$$

Softmax → roughly $P_\downarrow\approx0.27,\;P_0\approx0.40,\;P_\uparrow\approx0.33$. The public member predicts *less* escalation pressure than the full model — and the **divergence $\|\pi^{\text{full}}-\pi^{\text{public}}\|\approx0.03$ on $P_\uparrow$ is precisely the contribution of the (privileged) belief that B folds cheaply.** That gap is the early-warning signal: privileged information says this dyad is more escalation-prone than open sources reveal.

**Coverage vector for the public run:** belief = absent (δ=0), all else observed; confidence penalty = $\rho_{\text{belief}} < 1$ applied.

**Degraded run — occupancy components absent.** If $B^{econ}/B^{blood}/V_A$ cannot be built for T3, that transition falls back to the diagnostic $E_t/D_t/S_t$ direction signal, flagged diagnostic-grade, with a larger confidence penalty.

* * *

## PART 5: IMPLEMENTATION WORKFLOW (UPDATED)

1.  **Assign current tier $X_t$** (shared). Apply the T3 entry condition (§1.7) and T3-High latch (§1.6.1). **If intent/selectivity is absent, use the classification fallback (§1.9.4); if $X_t$ or $Nuc$ is unresolvable, fail-loud (§1.9.6).**
2.  **Code each input with its state** (observed / defaulted / absent — §1.9.1) for direction $(i\to j)$: $FMA$, $-\dot W$, belief term + uncertainty, directional modifiers.
3.  **Code symmetric variables** and per-actor Status-Quo Burden, each with a state.
4.  **Resolve the active model member** from the coverage of inputs (§1.9.2): full → public ($\delta=0$) → myopic ($\gamma=0$) → diagnostic-fallback.
5.  **Build the cost field** $\mathcal{C}_i(j)$ with surviving terms; apply modifier→barrier suppression only where modifiers are observed.
6.  **Stage 1:** cost-gradient movement scores → softmax → $(P_\downarrow,P_0,P_\uparrow)$; boundary constraints.
7.  **Stage 2:** $\Sigma^\uparrow$, $\kappa$, $\omega^+$, bimodal $\omega^-$; hard gates.
8.  **Compose** via §3.4.
9.  **Repeat for the reverse direction**, reconcile (§3.6), propagating the worse confidence penalty.
10. **Report** the cost fields, barriers used, modifier vector, belief gap, both directed $\pi$ vectors, the reconciled distribution, the deprecated $E_t/D_t/S_t$ diagnostics, **the COVERAGE VECTOR (per-input state + active member + confidence penalty), and — if both public and private members were run — the divergence $\|\pi^{\text{private}}-\pi^{\text{public}}\|$ (§1.9.3).**

* * *

## PART 6: VALIDATION, LIMITATIONS & OPEN ISSUES

### 6.1 What "Calibration" Requires Before Any Production Claim

Point estimates **and standard errors** for all coefficients — cost-field weights, $\gamma$, $\delta$, every barrier $B_{k\to j}$, modifier→barrier suppression, **and the confidence-penalty retention factors $\rho_t$** — via penalized MLE or Bayesian estimation (MIDs 1990–2015; UCDP-dyadic for proxy / T3-High). Out-of-sample Brier / log-loss / AUROC by tier. Inter-coder reliability (belief term and integration depth expected worst). Barrier identification via shocks that "pay" the barrier. Until then, every coefficient is an intelligent guess.

### 6.2 Retained Limitations

Rare-event tails (T6); $V_{contagion}$ needs network analysis; multi-actor wars exceed dyadic simplification (integration depth is the dyadic compression of a triadic reality); single representative decision-maker assumed.

### 6.3 Contagion Endogeneity (Manski Reflection)

Lag ≥1 period; instrument with distance-to-regional-conflict, not local intensity.

### 6.4 Status-Quo Burden vs Cost-of-War

Split resolved; the forward-looking term still reintroduces a counterfactual by construction — code it as a coarse "is the trend adverse?" signal. **When $-\dot W$ is absent, the myopic member ($\gamma=0$) sidesteps the counterfactual entirely at the cost of preventive logic.**

### 6.5 Structural Incompleteness (Regime Type)

Still excluded; if added, must improve out-of-sample fit beyond $\Xi$.

### 6.6 The Physics Analogy — Explicit Caveat (UNCHANGED)

Good generative source, bad governing theory. Conflict has memory, agency, and a second player. The governing theory is a **Markov game with cost-shaped transition probabilities.**

### 6.7 Falsifiable Predictions (UNCHANGED + degradation predictions)

- Expressive-sanctions dyads → overwhelming persistence mass.
- Sanctioned-into-a-corner dyads → elevated escalation vs comparable un-sanctioned high-stakes dyads (2014→2022 Russia–Ukraine, motivating not confirming).
- Confidently-wrong belief configurations → miscalculation-driven escalation cost fields alone miss.
- T3-High → improves out-of-sample fit over T3-only on post-2007 dyads, or is removed.
- Deeply-integrated proxy dyads → higher $T3\to T4$ rates than shallow, controlling for $\Omega\Xi$.
- Merchant test: non-selective support → not T3, no proxy-war dynamics.

### 6.8 Proper Use

✓ Early warning, scenario comparison, sensitivity analysis. ✗ Deterministic forecasting or point certainty.

### 6.9 Validating the Degradation Architecture (NEW)

The nested-family claim is itself testable and must be tested before relying on any degraded member:

- **Nesting equivalence test.** Set a richer member's extra-term inputs to their null values; confirm it reproduces the simpler member's $\pi$ to numerical tolerance. A failure means a term is not cleanly separable and the "degradation" silently distorts. Build and pass this test for each ⊃ in §1.9.2 *before* adding the richer term back.
- **Public-as-anchor.** Calibrate the public member on open data; treat the private member as a structured overlay, not a co-equal validated tool (its belief inputs aren't in any public backtest set).
- **Degraded-vs-full divergence.** On historical dyads where privileged information was later declassified, check that $\|\pi^{\text{private}}-\pi^{\text{public}}\|$ was large precisely on the miscalculation cases — i.e., that the divergence had predictive content rather than being noise.
- **Confidence-penalty calibration.** The $\rho_t$ must be set so that a degraded member's stated confidence matches its realized out-of-sample reliability (a degraded forecast claiming high confidence and missing badly means $\rho_t$ is too close to 1).
- **"Absent" routing audit.** Verify in code that state = absent drops the term and is never coerced to 0 in the cost field — the single most dangerous silent failure (§1.9.1).

* * *

## PART 7: APPENDIX — VARIABLE SUMMARY

| Variable | Name | Type | Range | Directional? | State-aware? | Status |
| --- | --- | --- | --- | --- | --- | --- |
| $X_t$ | Current Tier | State | {0,1,2,3,3H,4,5,6} | shared | high-salience | unchanged |
| $D_k$ | Duration | State (memory) | \[0,∞) | shared | yes | unchanged |
| $\Omega$ | Rivalry | Structural | \[0,1\] | symmetric | yes | unchanged |
| $\Xi$ | Contiguity | Structural | {0,0.5,1} | symmetric | yes | unchanged |
| $FMA_{i\to j}$ | First-Mover Adv. | Military | \[0,1\] | directional | yes | unchanged |
| $-\dot W_{i\to j}$ | Closing Window | Military | \[0,1\] | directional | yes (γ=0 if absent) | unchanged |
| Status-Quo Burden | (was $C_{peace}$) | Economic | \[0,1\] | per-actor | yes | unchanged |
| $W_x$ | Exhaustion | Economic | \[0,1\] | symmetric | yes | unchanged |
| $ORA$ | Off-Ramp Absence | Diplomatic | \[0,1\] | symmetric | yes | unchanged |
| $Stal_t$ | Stalemate | Operational | \[0,1\] | symmetric | yes | unchanged |
| $Dip_{cap}$ | Diplomatic Cap. | Diplomatic | \[0,1\] | symmetric | yes | unchanged |
| $Shock_k$ | Kinetic Shock | Catalyst | \[0,1\] | symmetric | yes | unchanged |
| $V_{contagion}$ | Regional Contagion | Geopolitical | \[-1,+1\] | symmetric | yes | unchanged |
| $Nuc$ | Nuclear Gate | Gatekeeper | \[0,1\] | symmetric | high-salience | unchanged |
| $\hat{\mathcal{C}}_i(\mathcal{C}_c)$ | Belief about counterpart costs | Strategic (agency) | est.+conf. | directional | yes (δ=0 if absent) | unchanged |
| Attribution | Modifier axis | Modifier | \[0,1\] | per-dyad | yes | unchanged |
| Integration depth | Modifier axis | Modifier | \[0,1\] | directional | yes | unchanged |
| Stakes | Modifier axis | Modifier | \[0,1\] | symmetric | yes | unchanged |
| Intent/selectivity | Modifier axis (T3 gate) | Modifier | \[0,1\] | directional | high-salience | unchanged |
| $\mathcal{C}_i(j)$ | Per-actor cost field | Derived engine | ℝ per tier | per-actor | —   | unchanged |
| $B_{k\to j}$ | Activation barrier | Derived/transition | \[0,∞) | per transition | —   | unchanged |
| input **state** | observed/defaulted/absent | Meta | {3 states} | per input | —   | **NEW** |
| coverage vector | active member + states + penalty | Output | —   | —   | —   | **NEW** |
| $\rho_t$ | Confidence retention factor | Calibration | (0,1\] | per term | —   | **NEW** |

**Version 25.0 | Specification Phase — Awaiting Calibration | Graceful-Degradation Architecture, Nested-Model Family, Public/Private Information Layering | May 2026**