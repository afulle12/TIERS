## The Unified Equation of Interstate War (v7)

**Core structural change:** Wars now carry an explicit partition into opposing coalitions. The v7 update introduces a **Betrayal Penalty ($C_b$)** to structurally differentiate between abandonment (neutrality) and betrayal (side-switching). This prevents the model from treating allies fighting each other as a symmetric outcome of defection.

$$\mathcal{W}_t = \{(w,\, X_w,\, \neg X_w,\, W_{sev,w}) \mid w \text{ ongoing at } t\}$$

where $X_w$ and $\neg X_w$ are disjoint subsets of states (the belligerent sides).

---

### Path 1 — Direct Dyadic Initiation

**Dyadic direct initiation**:

$$P_{direct}(A \to B, t) = N_{pub}(A,t) \cdot P_{init}(A \to B, t)$$

The public-hostility gate is applied at the **dyad level**.

**Dyadic initiation core**:

$$P_{init}(A \to B, t) = \beta \cdot M_{AB} \cdot O_{AB} \cdot S_{AB} \cdot F_{AB}$$

$$M_{AB} = \max\left(\frac{\Delta P_{AB} + R_{d,AB} + A_{div,A}}{3},\ P_{v,A}\right)$$

$$O_{AB} = \max(V_{p,AB}, V_{t,AB}) \cdot \big[1 - C_{T,B}(1 - W_{v,AB})\big]$$

$$S_{AB} = \frac{B_{AB} + R_{h,AB} + I_{s,AB}}{3}$$

$$F_{AB} = 1 - (1 - I_{a,AB})(1 - C_{p,AB}^*)(1 - I_{i,AB})$$

$$C_{p,AB}^* = \begin{cases} 1 & \text{if } V_{t,AB} > V_{p,AB} \\ C_{p,AB} & \text{otherwise} \end{cases}$$

**State-year direct initiation** (marginal exposure):

$$P_{direct}(A,t) = 1 - \prod_{B \neq A}\big(1 - P_{direct}(A \to B, t)\big)$$

---

### Path 2 — Structural Contagion (Side-Specific)

For each war $w \in \mathcal{W}_t$ and each side $Y \in \{X_w, \neg X_w\}$:

$$P_{join}(A \to Y, t) = 1 - (1 - T_{A,Y})(1 - E_{n,A,w} \cdot W_{sev,w} \cdot N_{pub}(A,t))(1 - S_{p,A,w} \cdot W_{sev,w} \cdot N_{pub}(A,t))$$

**Side-specific treaty trigger (v7 update):**

$$T_{A,Y} = \frac{C_{d,A,Y}^{\,2}}{C_{d,A,Y}^{\,2} + (C_{i,A,w}^{*}(Y))^{2}}$$

**Effective Intervention Cost with Betrayal Penalty:**

$$C_{i,A,w}^*(Y) = \max\big(C_{i,A,w},\ 1 - N_{pub}(A,t)\big) + \big(\delta_{A, \neg Y} \cdot C_b\big)$$

Where:
- $\delta_{A, \neg Y}$ is an indicator function that equals $1$ if state $A$ has a formal alliance with any member of the opposing coalition $\neg Y$, and $0$ otherwise.
- $C_b$ is the **Betrayal Penalty** constant (e.g., $C_b = 0.95$), representing the catastrophic domestic and geopolitical cost of fighting former allies.

This formulation ensures that while a state can defect to neutrality (where $C_{i,A,w}^*$ remains low), defecting to the *enemy* side incurs a massive friction cost, driving $T_{A,Y}$ toward zero for allies.

**War-level entry** (used only for marginal state-year exposure):

$$P_{join}(A \to w, t) = 1 - \big(1 - P_{join}(A \to X_w, t)\big)\big(1 - P_{join}(A \to \neg X_w, t)\big)$$

**State-year contagion:**

$$P_{contagion}(A,t) = 1 - \prod_{w \in \mathcal{W}_t}\big(1 - P_{join}(A \to w, t)\big)$$

---

### Dyadic Contagion Probabilities

**Probability $A$ and $B$ fight on opposite sides of an ongoing war:**

$$P_{opp}(A,B,t) = 1 - \prod_{w \in \mathcal{W}_t}\Big[1 - \big(P_{join}(A \to X_w)P_{join}(B \to \neg X_w) + P_{join}(A \to \neg X_w)P_{join}(B \to X_w)\big)\Big]$$

**Probability $A$ and $B$ fight on the same side of an ongoing war:**

$$P_{co}(A,B,t) = 1 - \prod_{w \in \mathcal{W}_t}\Big[1 - \big(P_{join}(A \to X_w)P_{join}(B \to X_w) + P_{join}(A \to \neg X_w)P_{join}(B \to \neg X_w)\big)\Big]$$

---

### Total Probabilities

**Total dyadic war probability** (they fight *each other*):

$$P_{dyad}(A,B,t) = 1 - \big(1 - P_{direct}(A \to B,t)\big)\big(1 - P_{direct}(B \to A,t)\big)\big(1 - P_{opp}(A,B,t)\big)$$

**Total state-year war probability** (marginal exposure):

$$P_{war}(A,t) = 1 - \big(1 - P_{direct}(A,t)\big)\big(1 - P_{contagion}(A,t)\big)$$

---

### Endogenous Severity Generation

When $A$ initiates against $B$, the new war enters $\mathcal{W}_t$ with an initial partition and severity.

$$W_{sev,w_{new}}^{(0)} = \frac{M_{AB} + O_{AB} + F_{AB}}{3}$$

Initial partition: $X_{w_{new}} = \{A\}$, $\neg X_{w_{new}} = \{B\}$.

Update: $\mathcal{W}_{t+1} = \mathcal{W}_t \cup \{w_{new}\}$.

---

### Within-Period Cascade Resolution

Path 2 is evaluated **iteratively** within each time period $t$:

1. In iteration $k$, for each war $w$ and each side $Y \in \{X_w, \neg X_w\}$, calculate $P_{join}(S \to Y, t)$ for all states $S \notin X_w \cup \neg X_w$ using current coalition memberships and the v7 betrayal penalty.
2. Draw side-entry outcomes. If a state triggers for both sides of the same war, assign it to the side with higher $P_{join}$ (break ties randomly).
3. Update $X_w$ and $\neg X_w$ with new participants.
4. Recompute $C_{d,\cdot,Y}$ and $\delta_{\cdot, \neg Y}$ for all treaty-linked states not yet in $w$.
5. Iterate until no new side-entries occur across all wars.

---

### Variable Definitions

All variables normalized to $[0, 1]$ unless noted. $\beta$ is a per-dyad calibration constant.

**War Structure**
- **$X_w, \neg X_w$** — Disjoint belligerent coalitions (sides) of war $w$.
- **$W_{sev,w}$** — Severity of war $w$. Endogenously generated at birth; multiplies economic and strategic pressures but not treaty triggers.

**Dyadic Outputs**
- **$P_{direct}(A \to B,t)$** — Probability $A$ directly initiates against $B$.
- **$P_{opp}(A,B,t)$** — Probability $A$ and $B$ enter the same ongoing war on opposite sides.
- **$P_{co}(A,B,t)$** — Probability $A$ and $B$ enter the same ongoing war on the same side.
- **$P_{dyad}(A,B,t)$** — Probability $A$ and $B$ fight each other (direct or opposite-side contagion).

**State-Year Outputs**
- **$P_{direct}(A,t)$** — Marginal probability $A$ initiates a new war against any target.
- **$P_{contagion}(A,t)$** — Marginal probability $A$ joins any ongoing war on either side.
- **$P_{war}(A,t)$** — Marginal probability $A$ is at war somewhere for any reason.

**Domestic Feasibility**
- **$N_{pub}(A,t)$** — Public non-hostility. Gates dyadic initiation and scales severity-weighted pressures while inflating $C_i^*$.

**Calibration**
- **$\beta$** — Base rate scaling constant.

**Motive ($M$)**
- **$\Delta P_{AB}$** — Power advantage.
- **$R_{d,AB}$** — Revisionist desire.
- **$A_{div,A}$** — Diversionary incentive (state-level).
- **$P_{v,A}$** — Preventive logic (state-level).

**Opportunity ($O$)**
- **$V_{p,AB}$** — Prize value.
- **$V_{t,AB}$** — Threat value.
- **$C_{T,B}$** — Target capacity.
- **$W_{v,AB}$** — Window of vulnerability.

**Spark ($S$)**
- **$B_{AB}$** — Borders.
- **$R_{h,AB}$** — Historical rivalry.
- **$I_{s,AB}$** — Immediate flashpoint.

**Friction ($F$)**
- **$I_{a,AB}$** — Information asymmetry.
- **$C_{p,AB}$** — Commitment problem.
- **$C_{p,AB}^*$** — Adjusted commitment problem (forced to 1 when $V_t > V_p$).
- **$I_{i,AB}$** — Issue indivisibility.

**Contagion**
- **$C_{d,A,Y}$** — Cost of defecting from allies on side $Y$. Computed from alliance ties to current members of $Y$.
- **$C_{i,A,w}$** — Baseline cost of intervention.
- **$C_{i,A,w}^*(Y)$** — Politically adjusted cost of intervention for side $Y$, including betrayal penalty.
- **$C_b$** — **Betrayal Penalty** constant (v7). Applied when a state joins a side opposing its allies.
- **$T_{A,Y}$** — Treaty trigger for side $Y$.
- **$E_{n,A,w}$** — Economic necessity from war $w$.
- **$S_{p,A,w}$** — Strategic paranoia regarding war $w$.
- **$P_{join}(A \to Y,t)$** — Probability $A$ joins side $Y$.
- **$P_{join}(A \to w,t)$** — Probability $A$ enters war $w$ on either side.

---

### Dashboard Readouts

**Do not combine dyadic and marginal quantities.** Report three distinct columns:

| Readout | Formula | Interpretation |
|---|---|---|
| **Dyadic War** | $P_{dyad}(A,B,t)$ | $A$ and $B$ fight *each other* |
| **Co-Belligerency** | $P_{co}(A,B,t)$ | $A$ and $B$ fight *side by side* in the same war |
| **State Exposure** | $P_{war}(A,t)$ | $A$ is at war *somewhere* for any reason |

For a two-state simulation with no active wars forcing opposing coalitions, **$P_{dyad}$ collapses to the direct-initiation terms only**, giving the honest near-zero result for non-rivals such as UK–USA. The v7 betrayal penalty ensures that even if both states have high intervention costs, they will defect to neutrality rather than to opposing sides, preserving the alliance structure.