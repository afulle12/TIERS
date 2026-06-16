## The Unified Equation of Interstate War (v5)

For state $A$ in year $t$, the total probability of war participation is the noisy union of direct initiation and contagion:

$$P_{war}(A,t) = 1 - \big(1 - P_{direct}(A,t)\big)\big(1 - P_{contagion}(A,t)\big)$$

---

### Path 1 — Direct Dyadic Initiation (State-Year)

Public non-hostility acts as a **domestic feasibility gate** on the entire portfolio of potential wars. If the public is maximally hostile, the state cannot initiate regardless of dyadic opportunity.

$$P_{direct}(A,t) = N_{pub}(A,t) \cdot \left[1 - \prod_{B \neq A}\big(1 - P_{init}(A \to B, t)\big)\right]$$

**Dyadic initiation core:**

$$P_{init}(A \to B, t) = \beta \cdot M_{AB} \cdot O_{AB} \cdot S_{AB} \cdot F_{AB}$$

$$M_{AB} = \max\left(\frac{\Delta P_{AB} + R_{d,AB} + A_{div,A}}{3},\ P_{v,A}\right)$$

$$O_{AB} = \max(V_{p,AB}, V_{t,AB}) \cdot \big[1 - C_{T,B}(1 - W_{v,AB})\big]$$

$$S_{AB} = \frac{B_{AB} + R_{h,AB} + I_{s,AB}}{3}$$

$$F_{AB} = 1 - (1 - I_{a,AB})(1 - C_{p,AB}^*)(1 - I_{i,AB})$$

$$C_{p,AB}^* = \begin{cases} 1 & \text{if } V_{t,AB} > V_{p,AB} \\ C_{p,AB} & \text{otherwise} \end{cases}$$

---

### Path 2 — Structural Contagion (State-Year)

The state joins existing wars through alliance obligation, economic necessity, or strategic paranoia. Each mechanism is dampened by public hostility.

$$P_{contagion}(A,t) = 1 - \prod_{w \in \mathcal{W}_t}\left[1 - P_{join}(A \to w, t)\right]$$

$$P_{join}(A \to w, t) = 1 - (1 - T_{Aw})(1 - E_{n,Aw} \cdot W_{sev,w} \cdot N_{pub}(A,t))(1 - S_{p,Aw} \cdot W_{sev,w} \cdot N_{pub}(A,t))$$

**Treaty trigger with politically adjusted intervention costs:**

$$T_{Aw} = \frac{C_{d,Aw}^2}{C_{d,Aw}^2 + (C_{i,Aw}^*)^2}$$

$$C_{i,Aw}^* = \max\big(C_{i,Aw},\ 1 - N_{pub}(A,t)\big)$$

---

### Endogenous Severity Generation

Wars are born with initial severity driven by the dyadic conditions that produced them. This severity then enters $\mathcal{W}_t$ and feeds forward into contagion pressures.

For a war $w_{new}$ initiated by $A$ against $B$ at time $t$:

$$W_{sev,w_{new}}^{(0)} = \frac{M_{AB} + O_{AB} + F_{AB}}{3}$$

The ongoing war set updates as $\mathcal{W}_{t+1} = \mathcal{W}_t \cup \{w_{new}\}$.

---

### Within-Period Cascade Resolution

Path 2 is evaluated **iteratively** within each time period $t$:

1. In iteration $k$, calculate $P_{join}$ for all states not yet in each $w \in \mathcal{W}_t$.
2. Draw entry outcomes. New participants alter alliance exposure for other states.
3. Recompute $P_{join}$ for iteration $k+1$ with updated participant sets.
4. Iterate until $\mathcal{W}_t$ stabilizes (no new entries).

---

### Variable Definitions

All variables normalized to $[0, 1]$. $\beta$ is a per-dyad calibration constant.

**Domestic Feasibility**
- **$N_{pub}$ — Public non-hostility.** The baseline domestic permissiveness toward military action. $1$ = full acquiescence; $0$ = active hostility blocking war. In Path 1, it gates the entire state-year initiation probability. In Path 2, it raises the effective cost of intervention ($C_i^*$) and scales the severity-weighted economic and strategic pressures.

**Calibration**
- **$\beta$ — Base rate scaling constant.** Tunes the per-dyad probability to match empirical state-year war frequencies.

**Motive ($M$) — why fight at all**
- **$\Delta P$ — Power advantage.** Initiator's military and economic superiority over the target.
- **$R_d$ — Revisionist desire.** Ideological or territorial drive to overturn the status quo.
- **$A_{div}$ — Diversionary incentive.** Domestic political pressure to use external conflict as a distraction (state-level).
- **$P_v$ — Preventive logic.** "Fight now while we still can" calculation about the initiator's own anticipated relative decline (state-level).

**Opportunity ($O$) — why this target, now**
- **$V_p$ — Prize value.** Positive value of conquering the target.
- **$V_t$ — Threat value.** Negative value of the target's continued existence.
- **$C_T$ — Target capacity.** Baseline ability to resist and maintain order.
- **$W_v$ — Window of vulnerability.** Temporary degradation of target defensibility. When $W_v = 1$, resistance is fully discounted; when $0$, capacity stands at $C_T$.

**Spark ($S$) — dyadic friction**
- **$B$ — Borders.** Geographic contiguity.
- **$R_h$ — Historical rivalry.** Entrenched animosity between the two populations.
- **$I_s$ — Immediate flashpoint.** Recent triggering event.

**Friction ($F$) — bargaining failure**
- **$I_a$ — Information asymmetry.** Incentives to bluff or hide true strength.
- **$C_p$ — Commitment problem.** Inability to trust that today's deal will hold tomorrow.
- **$C_p^*$ — Adjusted commitment problem.** Forced to $1$ when $V_t > V_p$, since regime-change goals cannot be settled diplomatically.
- **$I_i$ — Issue indivisibility.** The prize literally cannot be split.

**Contagion**
- **$C_d$ — Cost of defection.** Price of abandoning a treaty ally.
- **$C_i$ — Baseline cost of intervention.** Blood, treasure, and escalation risk.
- **$C_i^*$ — Politically adjusted cost of intervention.** Inflated toward $1$ as public hostility rises.
- **$T$ — Treaty trigger.** Probability the alliance holds under pressure.
- **$E_n$ — Economic necessity.** Damage to vital supply chains, energy, or trade from the ongoing war.
- **$S_p$ — Strategic paranoia.** Perceived inevitability that non-intervention leads to later destruction.
- **$W_{sev}$ — War severity.** Scale and intensity of ongoing conflict. Endogenously generated at birth; multiplies $E_n$ and $S_p$ but not $T$.

[^1]: [Democratic peace theory - Wikipedia](https://en.wikipedia.org/wiki/Democratic_peace_theory) (100%)
