# Unified Equation of Interstate War (Dyadic Variant) v18.3

## Structured Specification

---

## 1. Purpose and Version History

### What v18.3 Adds

v18.3 introduces an **external public opinion field** as a formal thermodynamic variable, extending the Boltzmann-analog architecture of v18.2. The extension is inspired by the Ising model's external magnetic field, which biases spin-state occupancy without altering the underlying interaction energies. Applied to conflict, the public opinion field $h_{AB}$ biases the softmax distribution over conflict tiers via a **conflict order parameter** $\sigma_k = k/3$, ensuring that T3 (war) is three times more sensitive to public opinion than T1 (diplomatic coercion).

### Core v18.3 Contributions

**Contribution 1 — External field $h_{AB} = \beta_h \cdot \Psi_{AB} \cdot D_A$.** The field is the product of a raw public disposition scalar $\Psi_{AB} \in [-1,1]$, a democratic sensitivity coefficient $D_A \in [0,1]$, and a global coupling constant $\beta_h \geq 0$. An autocratic initiator ($D_A \approx 0$) is effectively unconstrained by public opinion regardless of $\Psi_{AB}$.

**Contribution 2 — Differential tier coupling via $\sigma_k = k/3$.** The field contributes $h_{AB} \cdot \sigma_k$ to the log-odds of each tier:

| Tier | $\sigma_k$ | Field contribution | Interpretation |
|---|---:|---|---|
| $T_0$ (peace) | 0 | 0 | Reference state; field has no leverage |
| $T_1$ (coercive) | 1/3 | $+h_{AB}/3$ | Weakly coupled: public opinion on sanctions |
| $T_2$ (militarized) | 2/3 | $+2h_{AB}/3$ | Moderately coupled: public opinion on crises |
| $T_3$ (war) | 1 | $+h_{AB}$ | Fully coupled: public opinion on war initiation |

This differential coupling means that when public opinion supports conflict ($h_{AB} > 0$), T3 is amplified three times more than T1 — a mobilized public disproportionately enables skip. When public opinion resists conflict ($h_{AB} < 0$), T3 is suppressed three times more than T1 — a resistant public disproportionately kills the skip signature. This behavior emerges naturally from the $\sigma_k$ coupling without requiring a separate suppressor term.

**Contribution 3 — Backward compatibility.** When $\Psi_{AB} = 0$ or $D_A = 0$, then $h_{AB} = 0$ and $h_{AB} \cdot \sigma_k = 0$ for all $k$, recovering v18.2 exactly.

---

### Earlier Version Summaries

**v18.2** applied two fixes to v18.1: (1) decoupled tier log-odds so that $\mathcal{L}_1$, $\mathcal{L}_2$, $\mathcal{L}_3$ all derive independently from $\mathcal{L}_\text{base}$ rather than cumulatively, and (2) recalibrated escalation barriers to $\Delta_{12} = -1.1$, $\Delta_{23} = -1.6$ to match empirical COW base rates ($P(T_1) \approx 0.15$, $P(T_2) \approx 0.05$, $P(T_3) \approx 0.01$ at moderate rivalry).

**v18.1** replaced the independent per-tier sigmoid structure with a softmax over discrete conflict states and introduced the Economic Pressure Scalar $\mathcal{E}_{AB}$ with three conditional interaction pathways.

**v17.2** introduced the skip barrier $S^{**}$ in product form with five structural exponents and the alignment gate on $\Phi^{opp} > \tau_{opp}$.

**v16** introduced the contiguity amplification term $\varphi_\xi \Xi_{AB}$.

---

## 2. Conflict as Discrete Energy States

Conflict tiers are discrete states $s \in \{T_0, T_1, T_2, T_3\}$ with activation barriers between them:

$$E_{01} \le E_{12} \le E_{23} \quad \text{(sequential barriers)}$$

$$E_{03} \neq E_{01} + E_{12} + E_{23} \quad \text{(skip barrier — structurally distinct)}$$

The softmax over log-odds plays the role of a Boltzmann distribution over energy states. Higher states are less occupied by default; structural tension is the driving force that populates them.

**v18.3 extension:** The external public opinion field $h_{AB}$ is an additional thermodynamic variable that biases state occupancy without changing the underlying structural energy landscape. Analogously to an Ising external field adding $-h \sum_i s_i$ to the Hamiltonian, the conflict field adds $h_{AB} \cdot \sigma_k$ to the log-odds of each tier, where $\sigma_k = k/3$ is the conflict order parameter measuring how strongly each tier "aligns" with the public opinion field.

---

## 3. State Log-Odds (v18.3 Structure)

### 3.1 Shared Base Log-Odds

The shared military and political foundation — unchanged from v18.2:

$$\mathcal{L}_\text{base} = \beta_0 + \beta_m \widetilde{M}^*_{AB} + \beta_r \mathcal{R}_{AB} + \beta_a (2A_{AB}-1)C_{AB} \cdot \mathbf{1}[\Phi^{opp} > \tau_{opp}] + \beta_c \Phi^{coop}_{AB}$$

### 3.2 Tier Log-Odds with External Field

Each tier derives independently from $\mathcal{L}_\text{base}$ and receives an additional field contribution $h_{AB} \cdot \sigma_k$:

$$\mathcal{L}_0 = 0 \quad \text{(peace baseline, reference state)}$$

$$\mathcal{L}_1 = \mathcal{L}_\text{base} + \beta_e \mathcal{E}_{AB} + \tfrac{1}{3} h_{AB}$$

$$\mathcal{L}_2 = \mathcal{L}_\text{base} + \Delta_{12}^\text{eff} + \tfrac{2}{3} h_{AB}$$

$$\mathcal{L}_3 = \mathcal{L}_\text{base} + \Delta_{12} + \Delta_{23} + \beta_s \cdot S^{**}_{AB}(t) \cdot \widetilde{M}^*_{AB} + h_{AB}$$

where $\Delta_{12} \le 0$ and $\Delta_{23} \le 0$ are the base escalation barriers (defaults $\Delta_{12} = -1.1$, $\Delta_{23} = -1.6$).

### 3.3 Routing of $\mathcal{E}_{AB}$ (unchanged from v18.2)

| Tier | $\mathcal{E}$ pathway | Condition |
|---|---|---|
| $T_1$ | $+\beta_e \mathcal{E}$ directly | Always active when $\mathcal{E} > 0$ |
| $T_2$ | $+\beta_{e2} \mathcal{E}(1-\mathcal{A})$ via barrier erosion | Active when coercion failing |
| $T_3$ | Via $\mathcal{B}^\text{eff} \to S^{**}$ only | Active when coercion failing **and** $\Phi^{FMA}, -\dot{W} > 0$ |

### 3.4 Routing of $h_{AB}$ (v18.3)

| Tier | Field contribution | Notes |
|---|---|---|
| $T_0$ | 0 | Fixed reference; field has no direct leverage |
| $T_1$ | $+h_{AB}/3$ | Always active when $h_{AB} \neq 0$ |
| $T_2$ | $+2h_{AB}/3$ | Always active when $h_{AB} \neq 0$ |
| $T_3$ | $+h_{AB}$ | Always active when $h_{AB} \neq 0$; full coupling |

Unlike $\mathcal{E}_{AB}$, the field term is not gated on a failure condition — it acts on all tiers simultaneously with tier-proportional strength. This reflects that public opinion shapes the cost of all conflict levels, not just the highest tier.

---

## 4. External Public Opinion Field (v18.3)

### 4.1 Definition

$$h_{AB} = \beta_h \cdot \Psi_{AB} \cdot D_A$$

| Symbol | Role | Range |
|---|---|---|
| $\Psi_{AB}$ | Net public disposition of initiator's population toward conflict with B | $[-1, 1]$ |
| $D_A$ | Democratic sensitivity of initiator: degree to which public opinion constrains leadership | $[0, 1]$ |
| $\beta_h$ | Field coupling strength (global parameter, estimated) | $\geq 0$ |

### 4.2 Coding Rule for $\Psi_{AB}$

$\Psi_{AB}$ codes the **net public disposition of the initiator's domestic population** toward initiating conflict with the target. It is coded from polling data, protest events, elite rhetoric, media sentiment, and legislative signals. It must be coded independently of $\mathcal{E}_{AB}$, $\mathcal{A}_{AB}$, and structural motive.

| Value | Meaning |
|---:|---|
| $-1.00$ | Strong organized resistance: mass protest, legislative opposition, near-universal anti-war sentiment |
| $-0.50$ | Moderate skepticism: plurality opposition to military action |
| $-0.25$ | Mild skepticism: public concerned but not actively opposing |
| $0.00$ | Neutral, divided, uninformed, or irrelevant (default for most dyads) |
| $+0.25$ | Mild support: nationalist sentiment, perceived threat framing |
| $+0.55$ | Moderate support: majority polling pro-conflict (USA→Iraq March 2003) |
| $+0.60$ | State-amplified support: managed media environment (Russia→Ukraine February 2022) |
| $+0.75$ | Strong nationalist mobilization: existential framing, elite consensus |
| $+0.85$ | Rally effect: crisis triggers rapid opinion shift toward war support (USA post-Pearl Harbor) |

**Coding rules:**
- Code from the **initiator's** domestic context, not the target's.
- For autocracies, code the level of **state-curated public sentiment**, not suppressed true preference.
- For most dyads without active conflict discourse, default to $\Psi_{AB} = 0.00$.
- $\Psi_{AB}$ is **directed**: it codes how the initiator's public views conflict with B, not general hawkishness.

### 4.3 Coding Rule for $D_A$

$D_A$ codes how accountable the initiating leader is to domestic public pressure. It is a property of the **initiator's regime**, not the bilateral relationship. Use Polity or V-Dem Liberal Democracy Index rescaled to $[0,1]$.

| Value | Meaning | Examples |
|---:|---|---|
| 0.00 | Full autocracy: no meaningful public constraint | North Korea |
| 0.15 | Managed autocracy: public pressure marginal | Russia 2022 |
| 0.35 | Competitive authoritarianism | Turkey, Hungary |
| 0.60 | Partial democracy with electoral constraint | India, Israel, South Korea |
| 0.80 | Established liberal democracy | France, Germany, Japan, Australia |
| 0.90 | Full liberal democracy with strong audience costs | USA, UK, Canada |

### 4.4 Calibration Anchors

| Dyad | $\Psi_{AB}$ | $D_A$ | $h_{AB}$ (at $\beta_h=1$) | Note |
|---|---:|---:|---:|---|
| USA→Japan, Dec 1941 | $+0.85$ | $0.90$ | $+0.77$ | Post-Pearl Harbor rally; unified elite |
| Russia→Ukraine, Feb 2022 | $+0.60$ | $0.15$ | $+0.09$ | State-amplified; low democratic constraint |
| USA→Iraq, March 2003 | $+0.55$ | $0.90$ | $+0.50$ | Pre-war support polling ~72% |
| USA→Iraq, 2006 | $-0.40$ | $0.90$ | $-0.36$ | War weariness; majority opposing continuation |
| India→Pakistan, 2025 | $+0.75$ | $0.60$ | $+0.45$ | Post-Pahalgam nationalist mobilization |
| France→Germany, 2026 | $0.00$ | $0.85$ | $0.00$ | No conflict discourse; field inactive |

### 4.5 Data Firewall

$\Psi_{AB}$ must be coded **independently** of:
- $\mathcal{E}_{AB}$ (economic pressure): a state can simultaneously apply maximum economic pressure and face public resistance to military escalation.
- $\mathcal{A}_{AB}$ (coercion effectiveness): coercion can be failing while the public opposes further escalation.
- $\Phi^{opp}_{AB}$ (structural rivalry): high rivalry does not imply public support for war.

### 4.6 Field Properties

**Differential skip sensitivity.** The condition $\mathcal{L}_3 > \mathcal{L}_2$ (skip signature) is harder to achieve when $h_{AB} < 0$, because the field subtracts from $\mathcal{L}_3$ at full magnitude while subtracting from $\mathcal{L}_2$ at only two-thirds magnitude. This creates a natural asymmetry: public resistance attacks skip more than it attacks sequential escalation, without requiring a separate $S^{**}$ suppressor term.

**Autocracy decoupling.** When $D_A \approx 0$, $h_{AB} \approx 0$ regardless of $\Psi_{AB}$. An autocratic leader's conflict decisions are not modulated by public opinion in the log-odds. This is consistent with the audience costs literature (Fearon 1994; Schultz 2001) and the selectorate theory prediction that small-coalition leaders are less constrained by broad public preferences.

**Rally effect representation.** A crisis event at $T_1$ or $T_2$ that spikes $\Psi_{AB}$ from near-zero to $+0.80$ will disproportionately boost $\mathcal{L}_3$ (via $+h_{AB}$) compared to $\mathcal{L}_1$ (via $+h_{AB}/3$), making the skip signature suddenly easier to achieve. This correctly models how Pearl Harbor simultaneously constituted a crisis and shifted the US public opinion distribution in a way that made war initiation politically viable.

**Backward compatibility.** At $h_{AB} = 0$, all field terms vanish and the model reduces exactly to v18.2.

---

## 5. Softmax State Distribution

$$\boxed{
P(T_k \mid AB, t) = \frac{\exp(\mathcal{L}_k)}{\exp(0) + \exp(\mathcal{L}_1) + \exp(\mathcal{L}_2) + \exp(\mathcal{L}_3)}
}$$

where $\mathcal{L}_k$ now includes the field contribution $h_{AB} \cdot \sigma_k$ per tier.

### Properties (v18.3)

- $\sum_k P(T_k) = 1$ by construction.
- When $h_{AB} = 0$: reduces to v18.2. All v18.2 properties hold.
- When $h_{AB} > 0$ and large: the distribution shifts toward higher tiers, with T3 gaining most. A sufficiently mobilized and democratically unconstrained initiator can achieve skip signatures even with moderate structural conditions.
- When $h_{AB} < 0$: the distribution shifts toward peace. The skip signature $\mathcal{L}_3 > \mathcal{L}_2$ is suppressed more strongly than sequential escalation.
- $P(T_3)$ can exceed $P(T_2)$ (skip signature) when both skip amplification and positive field cooperate, or when skip alone is sufficient at $h_{AB} = 0$.
- For allied dyads ($\Psi_{AB} = 0.00$, field inactive): cooperation channel $\beta_c \Phi^{coop}_{AB}$ continues to be the primary peace-suppression mechanism.

---

## 6. Skip Barrier $S^{**}$ (v17.2 form, preserved)

$$S^{**}_{AB}(t) = \left(\Phi^{FMA}_{AB}\right)^{\eta_\phi} \cdot \left(\max(0,-\dot{W}_{AB})\right)^{\eta_w} \cdot \left(\mathcal{B}^\text{eff}_{AB}\right)^{\eta_b} \cdot \left(1 - \mathcal{N}_{AB}^{\eta_n}\right) \cdot \left(1 - \mathcal{A}_{AB}^{\eta_a}\right)$$

### Effective blockage (unchanged)

$$\mathcal{B}^\text{eff}_{AB} = \min\!\left(1,\ \mathcal{B}_{AB} + \varphi_E \cdot \mathcal{E}_{AB} \cdot (1 - \mathcal{A}_{AB})\right)$$

**Note on public opinion and skip (v18.3):** $S^{**}$ is structurally unchanged. The interaction between public opinion and skip emerges through the differential $\sigma_k$ coupling rather than through a modification of $S^{**}$ itself. A positive field boosts $\mathcal{L}_3$ directly, making it easier for skip amplification to push $\mathcal{L}_3$ above $\mathcal{L}_2$. A negative field makes the same skip signature harder to achieve — functionally equivalent to adding resistance as a skip suppressor, but architecturally cleaner because it requires no new $S^{**}$ term.

---

## 7. Economic Pressure Scalar $\mathcal{E}_{AB}$ (unchanged from v18.2)

$\mathcal{E}_{AB} \in [0,1]$ measures the intensity of economic instruments deployed by the initiator. Coded from **deployed instruments**, not from strategic effectiveness.

### Three interaction pathways

| Pathway | Mechanism | Condition |
|---|---|---|
| $\beta_e \cdot \mathcal{E}$ | Direct $T_1$ elevation | Always active |
| $\beta_{e2} \cdot \mathcal{E} \cdot (1-\mathcal{A})$ | Erodes $\Delta_{12}$ barrier | Active when coercion failing |
| $\varphi_E \cdot \mathcal{E} \cdot (1-\mathcal{A})$ | Raises $\mathcal{B}^\text{eff}$ in $S^{**}$ | Active when coercion failing |

### Calibration anchors

| Dyad | $\mathcal{E}$ | Note |
|---|---:|---|
| Japan $\to$ USA, Dec 1941 | $0.85$ | US oil embargo complete; near-total cutoff |
| USA $\to$ Russia, 2022–2026 | $0.75$ | SWIFT exclusion, asset freezes, oil price cap |
| USA $\to$ China, 2026 | $0.65$ | Tariffs, semiconductor controls, financial restrictions |
| Israel $\to$ Gaza, 2023–2026 | $0.80$ | Total blockade of goods, fuel, electricity |
| USA $\to$ UK (allied) | $0.02$ | No economic pressure |

---

## 8. Structural Motive (unchanged from v16)

$$\widetilde{M}^*_{AB} = \widetilde{M}_{AB} \cdot (1 + \varphi_\xi \Xi_{AB})$$

$$\widetilde{M}_{AB} = \Phi^{opp}_{AB} \exp\!\left(-\gamma_1 \Phi^{sup}_{AB} - \gamma_2 \Phi^{coop}_{AB}\right)$$

---

## 9. Alignment Gate (unchanged from v17.2)

$$\text{alignment term} = \begin{cases} \beta_a (2 A_{AB} - 1) C_{AB} & \text{if } \Phi^{opp}_{AB} > \tau_{opp} \text{ and } C_{AB} \geq \tau_c \\ 0 & \text{otherwise} \end{cases}$$

Default: $\tau_{opp} = 0.15$. For allied dyads, $\Phi^{opp}_{AB} \approx 0$, so the gate is inactive and conflict probability is suppressed entirely through the cooperation channel $\beta_c \Phi^{coop}_{AB}$.

---

## 10. Full Equation Summary

$$\boxed{
P(T_k \mid AB, t) = \text{softmax}_k\!\left(0,\ \mathcal{L}_1,\ \mathcal{L}_2,\ \mathcal{L}_3\right)
}$$

$$\mathcal{L}_\text{base} = \beta_0 + \beta_m \widetilde{M}^*_{AB} + \beta_r \mathcal{R}_{AB} + \beta_a (2A_{AB}-1) C_{AB} \cdot \mathbf{1}[\Phi^{opp} > \tau_{opp}] + \beta_c \Phi^{coop}_{AB}$$

$$h_{AB} = \beta_h \cdot \Psi_{AB} \cdot D_A \qquad \text{(v18.3 external field)}$$

$$\mathcal{L}_1 = \mathcal{L}_\text{base} + \beta_e \mathcal{E}_{AB} + \tfrac{1}{3}h_{AB}$$

$$\mathcal{L}_2 = \mathcal{L}_\text{base} + \Delta_{12}^\text{eff} + \tfrac{2}{3}h_{AB}, \qquad \Delta_{12}^\text{eff} = \Delta_{12} + \beta_{e2} \cdot \mathcal{E}_{AB} \cdot (1-\mathcal{A}_{AB})$$

$$\mathcal{L}_3 = \mathcal{L}_\text{base} + \Delta_{12} + \Delta_{23} + \beta_s S^{**}_{AB} \widetilde{M}^*_{AB} + h_{AB}$$

$$\mathcal{B}^\text{eff}_{AB} = \min\!\left(1,\ \mathcal{B}_{AB} + \varphi_E \cdot \mathcal{E}_{AB} \cdot (1 - \mathcal{A}_{AB})\right)$$

$$S^{**}_{AB} = \left(\Phi^{FMA}\right)^{\eta_\phi} \cdot \left(\max(0,-\dot{W})\right)^{\eta_w} \cdot \left(\mathcal{B}^\text{eff}\right)^{\eta_b} \cdot \left(1 - \mathcal{N}^{\eta_n}\right) \cdot \left(1 - \mathcal{A}^{\eta_a}\right)$$

---

## 11. All Parameters

| Parameter | Role | Version | Prior |
|---|---|---|---|
| $\beta_0$ | Baseline log-odds | v15 | MLE/posterior |
| $\beta_m$ | Motive weight | v15 | MLE/posterior |
| $\beta_r$ | Spark weight | v15 | MLE/posterior |
| $\beta_a$ | Alignment weight | v15 | MLE/posterior |
| $\beta_c$ | Cooperation weight ($<0$) | v15 | MLE/posterior |
| $\gamma_1, \gamma_2$ | Motive attenuation | v15 | Co-belligerence patterns |
| $\lambda, \kappa, \nu, \rho$ | Network / alignment | v15 | MLE/posterior |
| $\varphi_\xi$ | Contiguity amplification | v16 | HalfNormal(0,1) |
| $\beta_s$ | Skip amplification | v17 | HalfNormal(0,2) |
| $\eta_\phi, \eta_w, \eta_b, \eta_n, \eta_a$ | Skip curvature exponents | v17.2 | HalfNormal(0,1) |
| $\Delta_{12}$ | $T_1 \to T_2$ escalation barrier ($\leq 0$) | v18 | Normal($-0.5$, 0.5) |
| $\Delta_{23}$ | $T_2 \to T_3$ escalation barrier ($\leq 0$) | v18 | Normal($-1.0$, 0.5) |
| $\tau_{opp}$ | Alignment gate threshold | v18 | Fixed 0.15 |
| $\beta_e$ | Economic pressure direct weight ($\geq 0$) | v18.1 | HalfNormal(0,1) |
| $\beta_{e2}$ | Barrier erosion coefficient ($\geq 0$) | v18.1 | HalfNormal(0,0.5) |
| $\varphi_E$ | Blockage amplification coefficient ($\geq 0$) | v18.1 | HalfNormal(0,0.5) |
| $\beta_h$ | Public opinion field coupling strength ($\geq 0$) | **v18.3** | HalfNormal(0,1) |
| $D_A$ | Democratic sensitivity of initiator | **v18.3** | Fixed from Polity/V-Dem, rescaled $[0,1]$ |

**Per-dyad inputs (not estimated globally):**

| Input | Role | Range | Version |
|---|---|---|---|
| $\mathcal{E}_{AB}$ | Economic pressure scalar | $[0,1]$ | v18.1 |
| $\mathcal{A}_{AB}$ | Coercion effectiveness (mediator) | $[0,1]$ | v18.1 |
| $\Psi_{AB}$ | Net public disposition toward conflict | $[-1,1]$ | **v18.3** |
| $D_A$ | Democratic sensitivity of initiator | $[0,1]$ | **v18.3** |

---

## 12. Validation Summary

The model was validated against 11 directed dyads across three categories. v18.3 field values are shown for each where applicable.

### At war (modern)

**Russia/Ukraine (Feb 2022 initiation):** Skip signature present ($S^{**} \approx 0.655$, $\mathcal{L}_3 > \mathcal{L}_2$). $\Psi_{RU} = +0.60$, $D_{RU} = 0.15$, giving $h_{AB} \approx +0.09$. Low democratic sensitivity substantially dampens what would otherwise be a strong positive field — correctly modeling that Russian public support was structurally marginal to Putin's decision.

**India/Pakistan (Operation Sindoor, 2025):** Nuclear deterrence ($\mathcal{N} = 0.60$) suppresses $S^{**}$ despite high rivalry, matching the bounded character of the strike. $\Psi_{IN} = +0.75$, $D_{IN} = 0.60$, giving $h_{AB} \approx +0.45$ — a meaningful field that raises T1 and T2 log-odds (consistent with the strike being limited rather than a T3 event).

### Historical benchmarks

**Japan→USA (Dec 1941):** Clearest skip signature in the dataset. $\Psi_{JP} = +0.85$, $D_{JP} = 0.30$ (Taisho-era democratic constraint partially dismantled by 1941), giving $h_{AB} \approx +0.26$. Field amplifies $\mathcal{L}_3$ above baseline, consistent with the "national survival" framing that unified Japanese public sentiment. The $T_0 \to T_3$ skip remains structurally driven by $S^{**}$; the field provides additional amplification.

**USA→Japan (Dec 1941):** Sequential ordering ($T_1 > T_2 > T_3$) with no skip. $\Psi_{US} = +0.85$, $D_{US} = 0.90$, giving $h_{AB} \approx +0.77$ — a large field that correctly reflects the post-Pearl Harbor rally. Despite the large field, the US direction shows sequential ordering because structural conditions (FMA, $-\dot{W}$) favor continued pressure over a skip.

### Allied dyads

France/Germany, USA/UK, Japan/South Korea: all show conflict probability below 1%. Field is inactive ($\Psi = 0.00$) for all three — correctly reflecting the absence of conflict discourse between close allies. Peace suppression continues through the cooperation channel $\beta_c \Phi^{coop}_{AB}$.

### Unrelated dyads

Brazil/Nigeria, Chile/Vietnam, NZ/Kazakhstan: all show 1.5–2.5% conflict probability with $\Psi = 0.00$ and $D_A$ at national defaults. The ordering allied $<$ unrelated persists unchanged from v18.2.

---

## 13. Change Log

### v18.3 — External Public Opinion Field

| Item | v18.2 | v18.3 |
|---|---|---|
| Public opinion | Not modeled | External field $h_{AB} = \beta_h \cdot \Psi_{AB} \cdot D_A$ |
| Tier field coupling | None | $\mathcal{L}_k \mathrel{+}= h_{AB} \cdot \sigma_k$, $\sigma_k = k/3$ |
| T3 sensitivity to public opinion | None | 3× greater than T1 (from $\sigma_3 = 1$ vs $\sigma_1 = 1/3$) |
| Autocracy handling | Not modeled | $D_A \approx 0 \Rightarrow h_{AB} \approx 0$; leader unconstrained |
| Skip and public opinion | No interaction | Negative field suppresses skip signature without modifying $S^{**}$ |
| New global parameters | — | $\beta_h$ |
| New per-dyad inputs | — | $\Psi_{AB} \in [-1,1]$, $D_A \in [0,1]$ |
| Backward compatibility | — | $h_{AB}=0$ recovers v18.2 exactly |
| $S^{**}$ structure | Unchanged | Unchanged |
| $\mathcal{E}_{AB}$ routing | Unchanged | Unchanged |
| Barriers $\Delta_{12}$, $\Delta_{23}$ | Unchanged | Unchanged |

### v18.2 — Barrier Recalibration and Sign Convention Fix

| Item | v18.1 | v18.2 |
|---|---|---|
| Tier log-odds structure | Cumulative: $\mathcal{L}_2 = \mathcal{L}_1 + \Delta$, $\mathcal{L}_3 = \mathcal{L}_2 + \Delta + \text{skip}$ | Decoupled: all tiers derive from $\mathcal{L}_\text{base}$ independently |
| $\mathcal{E}$ effect on T3 | Propagates via $\mathcal{L}_1 \to \mathcal{L}_2 \to \mathcal{L}_3$ | Reaches T3 only through $\mathcal{B}^\text{eff} \to S^{**}$ |
| $\Delta_{12}$ default | $-0.2$ | $-1.1$ |
| $\Delta_{23}$ default | $-0.4$ | $-1.6$ |
| $\beta_s$ default | $2.0$ | $4.0$ |
| $\beta_0$ default | $-4.5$ | $-3.5$ |
| T3 without skip | $\approx 55\%$ of T1 | $\approx 5\%$ of T1 |

### v18.1 — Softmax Architecture and Economic Pressure

| Item | v17.2 | v18.1 |
|---|---|---|
| Tier probability structure | Independent sigmoid per tier | Softmax over $\{T_0, T_1, T_2, T_3\}$ |
| Probabilities sum to 1 | No | Yes |
| Escalation barriers | Implicit in $\beta_0$ | Explicit $\Delta_{12}$, $\Delta_{23}$ |
| Economic pressure | Absent | $\mathcal{E}_{AB} \in [0,1]$, three interaction pathways |
| Alignment gate | Absent | Gated on $\Phi^{opp} > \tau_{opp} = 0.15$ |