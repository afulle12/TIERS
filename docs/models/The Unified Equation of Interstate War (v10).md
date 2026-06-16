### The Unified Equation of Interstate War (Dyadic Variant)

**Path 1 — Direct Dyadic Initiation**

**Dyadic direct initiation**:
$$P_{direct}(A \to B, t) = N_{pub}(A,t) \cdot P_{init}(A \to B, t)$$

**Dyadic initiation core**:
$$P_{init}(A \to B, t) = \beta \cdot M_{AB} \cdot O_{AB} \cdot S_{AB} \cdot F_{AB}$$

$$M_{AB} = \max\left(\frac{\Delta P_{AB} + R_{d,AB} + A_{div,A}}{3},\ P_{v,A}\right)$$

$$O_{AB} = \max(V_{p,AB}, V_{t,AB}) \cdot \big[1 - C_{T,B}(1 - W_{v,AB})\big]$$

$$S_{AB} = \frac{B_{AB} + R_{h,AB} + I_{s,AB}}{3}$$

$$F_{AB} = 1 - (1 - I_{a,AB})(1 - C_{p,AB}^*)(1 - I_{i,AB})$$

$$C_{p,AB}^* = \begin{cases} 1 & \text{if } V_{t,AB} > V_{p,AB} \\ C_{p,AB} & \text{otherwise} \end{cases}$$

**Path 2 — Conditional Dyadic Contagion**

Assume State $B$ is involved in an ongoing war of severity $W_{sev}$. We evaluate State $A$'s probability of joining to support $B$ ($sup$) or joining to oppose $B$ ($opp$).

**Probability $A$ joins to SUPPORT $B$:**
$$P_{join,sup}(A \to B) = 1 - (1 - T_{sup})\Big(1 - E_{n,sup} \cdot W_{sev} \cdot \big(1 - N_{pub}(A)\big)\Big)\Big(1 - S_{p,sup} \cdot W_{sev} \cdot \big(1 - N_{pub}(A)\big)\Big)$$

**Probability $A$ joins to OPPOSE $B$:**
$$P_{join,opp}(A \to B) = 1 - (1 - T_{opp})\Big(1 - E_{n,opp} \cdot W_{sev} \cdot \big(1 - N_{pub}(A)\big)\Big)\Big(1 - S_{p,opp} \cdot W_{sev} \cdot \big(1 - N_{pub}(A)\big)\Big)$$

**The Betrayal Penalty ($C_b$) & Effective Intervention Costs**
The $N_{pub}$ inversion ensures peaceful publics heavily suppress intervention. The Betrayal Penalty ($C_b$) is applied if a state attempts to intervene on behalf of a side that opposes its current formal allies.

$$C_{i,sup}^* = \max\big(C_{i,A},\ 1 - N_{pub}(A)\big) + \big(\delta_{opp} \cdot C_b\big)$$
$$C_{i,opp}^* = \max\big(C_{i,A},\ 1 - N_{pub}(A)\big) + \big(\delta_{sup} \cdot C_b\big)$$

Where:
* $\delta_{opp} = 1$ if State $A$ has formal alliances with State $B$'s enemies (i.e., $C_{d,opp} > 0.5$).
* $\delta_{sup} = 1$ if State $A$ has formal alliances with State $B$ directly (i.e., $C_{d,sup} > 0.5$).
* $C_b = 0.95$ (The Betrayal Penalty Constant).

**Directional Treaty Triggers**
$$T_{sup} = \frac{C_{d,sup}^{\,2}}{C_{d,sup}^{\,2} + (C_{i,sup}^{*})^{2}}$$
$$T_{opp} = \frac{C_{d,opp}^{\,2}}{C_{d,opp}^{\,2} + (C_{i,opp}^{*})^{2}}$$

**Total Dyadic Probabilities**

**Overall Dyadic War Probability (They fight *each other*):**
$$P_{dyad}(A,B) = 1 - \big(1 - P_{direct}(A \to B)\big)\big(1 - P_{direct}(B \to A)\big)\big(1 - P_{join,opp}(A \to B)\big)\big(1 - P_{join,opp}(B \to A)\big)$$

**Overall Co-Belligerency Probability (They fight *side by side*):**
$$P_{co}(A,B) = 1 - \big(1 - P_{join,sup}(A \to B)\big)\big(1 - P_{join,sup}(B \to A)\big)$$