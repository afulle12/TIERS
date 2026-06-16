### The Unified Equation of Interstate War (Dyadic Variant) — v11

**Changelog (v10 → v11):** Constrained the calibration constant $\beta$ to the unit interval as an explicit model-spec requirement: $\beta \in [0,1]$. No structural changes; this codifies an assumption the rest of the model already relies on for $P_{init}$ to remain a valid probability.

---

**Path 1 — Direct Dyadic Initiation**

**Dyadic direct initiation:**
$$P_{direct}(A \to B, t) = N_{pub}(A,t) \cdot P_{init}(A \to B, t)$$

**Dyadic initiation core:**
$$P_{init}(A \to B, t) = \beta \cdot M_{AB} \cdot O_{AB} \cdot S_{AB} \cdot F_{AB}, \quad \beta \in [0,1]$$

$$M_{AB} = \max\left(\frac{\Delta P_{AB} + R_{d,AB} + A_{div,A}}{3},\ P_{v,A}\right)$$

$$O_{AB} = \max(V_{p,AB}, V_{t,AB}) \cdot \big[1 - C_{T,B}(1 - W_{v,AB})\big]$$

$$S_{AB} = \frac{B_{AB} + R_{h,AB} + I_{s,AB}}{3}$$

$$F_{AB} = 1 - (1 - I_{a,AB})(1 - C_{p,AB}^*)(1 - I_{i,AB})$$

$$C_{p,AB}^* = \begin{cases} 1 & \text{if } V_{t,AB} > V_{p,AB} \\ C_{p,AB} & \text{otherwise} \end{cases}$$

---

**Path 2 — Conditional Dyadic Contagion**

Assume State $B$ is involved in an ongoing war of severity $W_{sev}$. We evaluate State $A$'s probability of joining to support $B$ ($sup$) or joining to oppose $B$ ($opp$).

**Probability $A$ joins to SUPPORT $B$:**
$$P_{join,sup}(A \to B) = 1 - (1 - T_{sup})\Big(1 - E_{n,sup} \cdot W_{sev} \cdot \big(1 - N_{pub}(A)\big)\Big)\Big(1 - S_{p,sup} \cdot W_{sev} \cdot \big(1 - N_{pub}(A)\big)\Big)$$

**Probability $A$ joins to OPPOSE $B$:**
$$P_{join,opp}(A \to B) = 1 - (1 - T_{opp})\Big(1 - E_{n,opp} \cdot W_{sev} \cdot \big(1 - N_{pub}(A)\big)\Big)\Big(1 - S_{p,opp} \cdot W_{sev} \cdot \big(1 - N_{pub}(A)\big)\Big)$$

---

**The Betrayal Penalty ($C_b$) & Effective Intervention Costs**

The $N_{pub}$ inversion ensures peaceful publics heavily suppress intervention. The Betrayal Penalty ($C_b$) is applied if a state attempts to intervene on behalf of a side that opposes its current formal allies.

$$C_{i,sup}^* = \max\big(C_{i,A},\ 1 - N_{pub}(A)\big) + \big(\delta_{opp} \cdot C_b\big)$$

$$C_{i,opp}^* = \max\big(C_{i,A},\ 1 - N_{pub}(A)\big) + \big(\delta_{sup} \cdot C_b\big)$$

Where:
* $\delta_{opp} = 1$ if State $A$ has formal alliances with State $B$'s enemies (i.e., $C_{d,opp} > 0.5$).
* $\delta_{sup} = 1$ if State $A$ has formal alliances with State $B$ directly (i.e., $C_{d,sup} > 0.5$).
* $C_b = 0.95$ (The Betrayal Penalty Constant).

Note: $C_{i,sup}^*$ and $C_{i,opp}^*$ are *costs*, not probabilities, and may exceed 1. The contest functions below remain bounded regardless.

---

**Directional Treaty Triggers**

$$T_{sup} = \frac{C_{d,sup}^{\,2}}{C_{d,sup}^{\,2} + (C_{i,sup}^{*})^{2}}$$

$$T_{opp} = \frac{C_{d,opp}^{\,2}}{C_{d,opp}^{\,2} + (C_{i,opp}^{*})^{2}}$$

---

**Total Dyadic Probabilities**

**Overall Dyadic War Probability** (they fight *each other*):
$$P_{dyad}(A,B) = 1 - \big(1 - P_{direct}(A \to B)\big)\big(1 - P_{direct}(B \to A)\big)\big(1 - P_{join,opp}(A \to B)\big)\big(1 - P_{join,opp}(B \to A)\big)$$

**Overall Co-Belligerency Probability** (they fight *side by side*):
$$P_{co}(A,B) = 1 - \big(1 - P_{join,sup}(A \to B)\big)\big(1 - P_{join,sup}(B \to A)\big)$$

---

**Parameter constraints (model spec):**

| Symbol | Domain | Notes |
|---|---|---|
| $\beta$ | $[0,1]$ | **New in v11** — calibration constant for dyadic initiation |
| $C_b$ | $0.95$ | Betrayal penalty constant |
| All primitive inputs ($\Delta P, R_d, A_{div}, P_v, V_p, V_t, C_T, W_v, B, R_h, I_s, I_a, C_p, I_i, N_{pub}, W_{sev}, E_n, S_p, C_d, C_i$) | $[0,1]$ | Required for downstream probability semantics |
| $C_{i,sup}^*, C_{i,opp}^*$ | $[0, 1+C_b]$ | Costs, not probabilities; bounded by construction |

With $\beta \in [0,1]$ enforced, $P_{init} \in [0,1]$ follows directly from the bounded factors $M, O, S, F$, and the rest of the noisy-OR / contest-function machinery propagates that boundedness through to $P_{dyad}$ and $P_{co}$.

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