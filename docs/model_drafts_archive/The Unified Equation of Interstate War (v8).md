Here is the v8 specification of the Unified Equation of Interstate War. 

This version integrates the v7 Betrayal Penalty while resolving the structural flaws in Path 2. Specifically, it **inverts $N_{pub}$** so that peaceful publics suppress (rather than multiply) the urge to join foreign wars, and it makes **non-treaty pressures ($E_n$, $S_p$) side-specific** to eliminate the "coin-flip" joining behavior.

---

## The Unified Equation of Interstate War (v8)

**Core Structure:** Wars maintain the explicit partition into opposing coalitions introduced in v7, alongside the Betrayal Penalty ($C_b$) to differentiate abandonment from side-switching.

$$\mathcal{W}_t = \{(w,\, X_w,\, \neg X_w,\, W_{sev,w}) \mid w \text{ ongoing at } t\}$$

---

### Path 1 — Direct Dyadic Initiation
*(Unchanged from v7)*

**Dyadic direct initiation**:
$$P_{direct}(A \to B, t) = N_{pub}(A,t) \cdot P_{init}(A \to B, t)$$

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
*(Updated for v8: Directional Pressures and $N_{pub}$ Inversion)*

For each war $w \in \mathcal{W}_t$ and each side $Y \in \{X_w, \neg X_w\}$:

$$P_{join}(A \to Y, t) = 1 - (1 - T_{A,Y})\Big(1 - E_{n,A,Y} \cdot W_{sev,w} \cdot \big(1 - N_{pub}(A,t)\big)\Big)\Big(1 - S_{p,A,Y} \cdot W_{sev,w} \cdot \big(1 - N_{pub}(A,t)\big)\Big)$$

**Side-specific treaty trigger:**
$$T_{A,Y} = \frac{C_{d,A,Y}^{\,2}}{C_{d,A,Y}^{\,2} + (C_{i,A,w}^{*}(Y))^{2}}$$

**Effective Intervention Cost with Betrayal Penalty:**
$$C_{i,A,w}^*(Y) = \max\big(C_{i,A,w},\ 1 - N_{pub}(A,t)\big) + \big(\delta_{A, \neg Y} \cdot C_b\big)$$

Where:
* $\delta_{A, \neg Y}$ equals $1$ if state $A$ has a formal alliance with any member of the opposing coalition $\neg Y$, and $0$ otherwise.
* $C_b$ is the **Betrayal Penalty** constant.
* **[v8 Fix]** Economic ($E_{n,A,Y}$) and Strategic ($S_{p,A,Y}$) pressures are now indexed to side $Y$, ensuring states are pulled toward specific coalitions rather than the war in general.
* **[v8 Fix]** Public non-hostility is inverted as $(1 - N_{pub})$, ensuring highly peaceful populations ($N_{pub} \to 1$) drive the multiplier to $0$, suppressing the intervention urge.

**War-level entry** (used only for marginal state-year exposure):
$$P_{join}(A \to w, t) = 1 - \big(1 - P_{join}(A \to X_w, t)\big)\big(1 - P_{join}(A \to \neg X_w, t)\big)$$

**State-year contagion:**
$$P_{contagion}(A,t) = 1 - \prod_{w \in \mathcal{W}_t}\big(1 - P_{join}(A \to w, t)\big)$$

---

### Dyadic Contagion Probabilities
*(Unchanged from v7)*

**Probability $A$ and $B$ fight on opposite sides of an ongoing war:**
$$P_{opp}(A,B,t) = 1 - \prod_{w \in \mathcal{W}_t}\Big[1 - \big(P_{join}(A \to X_w)P_{join}(B \to \neg X_w) + P_{join}(A \to \neg X_w)P_{join}(B \to X_w)\big)\Big]$$

**Probability $A$ and $B$ fight on the same side of an ongoing war:**
$$P_{co}(A,B,t) = 1 - \prod_{w \in \mathcal{W}_t}\Big[1 - \big(P_{join}(A \to X_w)P_{join}(B \to X_w) + P_{join}(A \to \neg X_w)P_{join}(B \to \neg X_w)\big)\Big]$$

---

### Total Probabilities
*(Unchanged from v7)*

**Total dyadic war probability** (they fight *each other*):
$$P_{dyad}(A,B,t) = 1 - \big(1 - P_{direct}(A \to B,t)\big)\big(1 - P_{direct}(B \to A,t)\big)\big(1 - P_{opp}(A,B,t)\big)$$

**Total state-year war probability** (marginal exposure):
$$P_{war}(A,t) = 1 - \big(1 - P_{direct}(A,t)\big)\big(1 - P_{contagion}(A,t)\big)$$

---

### Endogenous Severity Generation & Resolution Cascade
*(Unchanged from v7)*

$$W_{sev,w_{new}}^{(0)} = \frac{M_{AB} + O_{AB} + F_{AB}}{3}$$

Initial partition: $X_{w_{new}} = \{A\}$, $\neg X_{w_{new}} = \{B\}$.

The cascade resolution functions identically: evaluate Path 2 iteratively within period $t$, assigning states to the side with the highest $P_{join}$ until no new side-entries occur.

---

### v8 Variable Definitions Update

All variables remain identical to the v7 specification, with the exception of the following modified structural contagion inputs:

* **$E_{n,A,Y}$** — Economic necessity for state $A$ to ensure the victory/survival of side $Y$. (Replaces $E_{n,A,w}$).
* **$S_{p,A,Y}$** — Strategic paranoia/security imperative for state $A$ regarding the potential defeat of side $Y$. (Replaces $S_{p,A,w}$).