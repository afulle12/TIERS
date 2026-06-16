### The Unified Equation of Interstate War (Dyadic Variant) — v13

**Changelog (v12 → v13):** Three structural simplifications.

1. **Path 2 (contagion) eliminated.** Alliance entanglement is now captured by two pull variables $\Phi^{opp}_{AB,k}$ and $\Phi^{sup}_{AB,k}$ that enter the unified Path 1 machinery as motive inputs. The betrayal penalty $C_b$ is preserved through net-pull subtraction rather than as a separate Path 2 mechanism. Extended deterrence now operates in Path 1 via the target's effective resistance $C_{T,B}^{eff}$ — closing the v12 gap where extended deterrence existed only for third-party joining decisions.

2. **$\psi_i$ (decision-maker resolve) removed from $U_i$.** Leader-level variation can be captured implicitly through time-varying $D_i$ (doctrine reflecting leadership) and $K_i$ (operational protocols reflecting leadership).

3. **$P_{T4}^{direct}$ removed.** Nuclear war enters the model only through escalation from $T3$: $P_{T4} = P_{T3} \cdot E_{3 \to 4}$. This commits to the empirical regularity that all observed and credibly-modeled nuclear use occurs in active conventional conflict.

**Variables added:** $\Phi^{opp}_{AB,k}$, $\Phi^{sup}_{AB,k}$ (alliance pulls, derived); $\Gamma_{AX}$ (defection cost, primitive); $R_X$ (deliverable reinforcement, primitive).

**Variables removed:** $\psi_i$, $U_i^{first}$, $\mu$ (extended deterrence multiplier — now native in $C_{T,B}^{eff}$), $W_{sev}^{(k)}$ (severity now captured by tier index), and all of Path 2's directional treaty machinery ($T_{sup}$, $T_{opp}$, $C_{i,sup}^*$, $C_{i,opp}^*$, $E_{n,sup}$, $E_{n,opp}$, $S_{p,sup}$, $S_{p,opp}$). $E_n$ and $S_p$ are preserved but folded into Motive directly without sup/opp directional split.

---

### Architecture

The model outputs four ordered probabilities per dyad:

$$\{P_{T1}, P_{T2}, P_{T3}, P_{T4}\}, \quad P_{T1} \geq P_{T2} \geq P_{T3} \geq P_{T4}$$

with tier definitions unchanged from v12 (T1 economic, T2 limited military, T3 all-out conventional, T4 nuclear).

A single initiation path produces direct-entry probabilities at each tier, linked by escalation operators:

$$P_{Tk}(A,B) = 1 - \big(1 - P_{Tk}^{direct}(A,B)\big) \cdot \big(1 - P_{T_{k-1}}(A,B) \cdot E_{k-1 \to k}(A,B)\big)$$

for $k \in \{1, 2, 3\}$ with $P_{T0} \equiv 1$. For $T4$:

$$P_{T4}(A,B) = P_{T3}(A,B) \cdot E_{3 \to 4}(A,B)$$

Nuclear war has no direct-entry pathway in v13; all nuclear use is conditioned on prior $T3$ engagement.

---

### The Unified Initiation Path

For each tier $k \in \{1,2,3\}$:

$$P_{Tk}^{direct}(A \to B) = N_{pub}^{(k)}(A) \cdot \beta_k \cdot M_{AB}^{(k),u} \cdot O_{AB}^{(k),u} \cdot S_{AB}^{(k)} \cdot F_{AB}^{(k)}$$

$$P_{Tk}^{direct}(A,B) = 1 - \big(1 - P_{Tk}^{direct}(A \to B)\big)\big(1 - P_{Tk}^{direct}(B \to A)\big)$$

The "$u$" superscript indicates unified (alliance-augmented) variants. Tier-specific factor forms are preserved from v12; the only change is the unified Motive and the substitution of $C_{T,B}^{eff}$ for $C_{T,B}$ in Opportunity.

**Unified Motive** (replaces v12's per-tier $M$):

$$M_{AB}^{(k),u} = 1 - \big(1 - M_{AB}^{(k)}\big)\big(1 - \Phi^{opp,net}_{AB,k}\big)\big(1 - E_{n,AB,k}\big)\big(1 - S_{p,AB,k}\big)$$

where $M_{AB}^{(k)}$ is the v12 tier-specific motive (e.g. $M^{(1)}$ for T1, etc.), and the three additional terms are noisy-OR'd in:

- $\Phi^{opp,net}_{AB,k}$ — net alliance pull to oppose B (defined below)
- $E_{n,AB,k}$ — economic necessity to engage (supply chain, energy, financial damage from B's actions or B's wars)
- $S_{p,AB,k}$ — strategic paranoia (perceived inevitability of later confrontation if A stays out now)

**Unified Opportunity** (replaces $C_{T,B}$ with effective resistance):

$$O_{AB}^{(k),u} = \max(V_{p,AB}^{\,(k)}, V_{t,AB}^{\,(k)}) \cdot \big[1 - C_{T,B}^{eff}(1 - W_{v,AB})\big]$$

with $V_p^{(k)}, V_t^{(k)}$ following the v12 tier-specific definitions ($V_p, V_t$ for T1/T2; $V_p^{\dagger} = V_p(1-\Sigma_{AB})$ and $V_t^{\dagger} = V_t(1-\Sigma_{AB})$ for T3).

**Spark and Friction** unchanged from v12:

$$S_{AB}^{(2)} = \min\!\big(1, S_{AB}(1 + \kappa \Sigma_{AB})\big), \quad S_{AB}^{(k)} = S_{AB} \text{ for } k \in \{1,3\}$$

(with the T1 variant dropping $B_{AB}$ as in v12)

$$F_{AB}^{(k)} = \text{v12 tier-specific form}$$

---

### Alliance Pulls

**Opposition pull** — A's alliance-driven motivation to fight B at tier $k$:

$$\Phi^{opp}_{AB,k} = 1 - \prod_{X \in \mathcal{A}_A} \big(1 - I_{XB,k} \cdot \Gamma_{AX}\big)$$

For each ally $X$ of $A$: if $X$ is actively engaged against $B$ at tier $k$ ($I_{XB,k}$), $A$ feels pull proportional to $A$'s defection cost relative to $X$ ($\Gamma_{AX}$). Noisy-OR aggregates across allies.

**Support pull** — A's alliance-driven motivation to fight on B's side at tier $k$:

$$\Phi^{sup}_{AB,k} = 1 - \big(1 - \Gamma_{AB} \cdot \mathbb{1}[\text{B engaged at tier } k]\big) \cdot \prod_{Y \in \mathcal{E}_A} \big(1 - I_{BY,k}\big)$$

Two channels combined via noisy-OR: (a) A is directly committed to B and B is in a tier-$k$ conflict (any opponent); (b) A's enemy $Y$ is fighting B (enemy-of-my-enemy logic).

**Net opposition pull** (betrayal-penalty-adjusted):

$$\Phi^{opp,net}_{AB,k} = \max\!\big(0,\ \Phi^{opp}_{AB,k} - C_b \cdot \Phi^{sup}_{AB,k}\big)$$

Cross-pressured states — pulled both ways — see their opposition pull discounted by the betrayal-penalty coefficient $C_b = 0.95$. This reproduces the v11/v12 betrayal-penalty intuition through netting rather than conditional logic.

**Notes on $\Gamma$ and $\mathcal{A}, \mathcal{E}$:**

- $\Gamma_{AX} \in [0,1]$ — A's defection cost relative to X. Combines treaty depth, prior fulfillment record, reputational stakes, public sentiment. Non-zero only where formal or revealed commitments exist; $\Gamma_{AA} \equiv 0$ by convention.
- $\mathcal{A}_A$ — set of states with which A has positive commitments ($\Gamma_{AX} > 0$).
- $\mathcal{E}_A$ — set of states A has identified as adversaries (rivalry-graph membership).
- These are not strict partitions; states can be neither ally nor enemy. The defining feature is alliance-graph operation: $X \in \mathcal{A}_A$ iff $\Gamma_{AX}$ is meaningfully positive.

---

### Extended Deterrence in Opportunity

The target's effective resistance now incorporates expected ally reinforcement:

$$C_{T,B}^{eff} = 1 - (1 - C_{T,B}) \prod_{X \neq A, B} \big(1 - \Gamma_{XB} \cdot R_X\big)$$

For each potential ally $X$ of $B$: $B$'s effective defense is augmented by $X$'s commitment to $B$ ($\Gamma_{XB}$) weighted by $X$'s deliverable reinforcement capacity ($R_X$). Noisy-OR aggregates across $B$'s alliance network.

This single formula captures both **active intervention threat** (X would join if A attacked) and **extended deterrence** (X's existence raises the cost of attacking B even before any engagement). It closes the v12 gap where extended deterrence operated only through Path 2 third-party joining decisions.

**Note:** unlike $\Phi^{sup}$, the effective resistance uses $\Gamma_{XB}$ directly rather than active engagement — capturing that umbrellas work via *commitment credibility*, not active engagement. A nuclear-armed patron deters even without entering the war.

---

### Escalation Operators

$$E_{1 \to 2}(A,B) = 1 - (1 - \tau_{red})(1 - I_{s,AB}^{(2)})$$

$$E_{2 \to 3}(A,B) = 1 - (1 - \sigma_{T2})(1 - I_{i,AB})(1 - I_{a,AB})$$

$$E_{3 \to 4}(A,B) = 1 - (1 - U_A)(1 - U_B)$$

with simplified conditional nuclear use:

$$U_i = \nu_i \cdot \Big[1 - (1 - D_i)(1 - L_{conv,i})(1 - K_i)\Big]$$

Three risk channels: doctrinal ($D_i$), situational ($L_{conv,i}$), operational ($K_i$). The $\psi_i$ leader-resolve term is gone; leader effects enter through time-variation in $D_i$ and $K_i$ if relevant.

Asymmetry retained: $T3$ is suppressed by $\Sigma_{AB} = \min(\nu_A, \nu_B)$, but $E_{3 \to 4}$ depends on $\max(\nu_A, \nu_B)$ via the noisy-OR over $U_A$ and $U_B$.

---

### Co-Belligerency

Recovered from support pulls without a separate path:

$$P_{co}(A,B,k) = P_{Tk}(A) \cdot P_{Tk}(B) \cdot \text{align}(A,B,k)$$

with the alignment factor:

$$\text{align}(A,B,k) = \frac{\Phi^{sup}_{AB,k} \cdot \Phi^{sup}_{BA,k} + \epsilon}{\Phi^{sup}_{AB,k} \cdot \Phi^{sup}_{BA,k} + \Phi^{opp}_{AB,k} \cdot \Phi^{opp}_{BA,k} + \epsilon}$$

$\epsilon$ is a small regularization constant ($\epsilon \approx 0.01$) preventing zero-division when both pull terms are zero. A and B are co-belligerent at tier $k$ when both are present at tier $k$ *and* the alignment factor is high (mutual support-pulls dominate mutual opposition-pulls).

---

### Total Aggregate Outputs

**Per-tier probabilities** (evaluated recursively from $k=1$ to $k=3$, then $k=4$):

$$P_{Tk}(A,B) = 1 - \big(1 - P_{Tk}^{direct}(A,B)\big) \cdot \big(1 - P_{T_{k-1}}(A,B) \cdot E_{k-1 \to k}(A,B)\big), \quad k \in \{1,2,3\}$$

$$P_{T4}(A,B) = P_{T3}(A,B) \cdot E_{3 \to 4}(A,B)$$

**Expected conflict severity** (optional summary):

$$\mathbb{E}[\text{severity}](A,B) = \sum_{k=1}^{4} (P_{Tk} - P_{T_{k+1}}) \cdot s_k, \quad P_{T5} \equiv 0$$

with $s_k \in \{0.15, 0.35, 0.75, 1.0\}$ (severity weights, formerly $W_{sev}^{(k)}$ — retained here as an output-side weighting rather than an input-side primitive).

---

### Parameter Constraints

| Symbol | Domain | Notes |
|---|---|---|
| $\beta_k$ | $[0,1]$ | Per-tier base rate scaling (4 constants) |
| $\rho$ | $[0.2, 0.4]$ | T1 public gate exponent |
| $\kappa$ | $[0,1]$ | Stability-instability coefficient |
| $\eta$ | $[0, 0.3]$ | T1 substitution channel (optional) |
| $C_b$ | $0.95$ | Betrayal penalty constant |
| $\epsilon$ | $\approx 0.01$ | Co-belligerency alignment regularizer |
| $s_k$ | $\{0.15, 0.35, 0.75, 1.0\}$ | Output severity weights (optional) |
| $\nu_i, D_i, K_i$ | $[0,1]$ | Per-state nuclear primitives |
| $\Sigma_{AB} = \min(\nu_A, \nu_B)$ | $[0,1]$ | Mutual nuclear shadow (derived) |
| $\Gamma_{AX}, R_X$ | $[0,1]$ | Alliance primitives |
| $L_{AB}, D_{AB}, \rho_{ideo,AB}$ | $[0,1]$ | T1 primitives |
| $L_{conv,i}$ | $[0,1]$ | Wartime conventional losing pressure (derived) |
| $\tau_{red}, \sigma_{T2}$ | $[0,1]$ | Escalation primitives |
| $\Phi^{opp}, \Phi^{sup}, \Phi^{opp,net}$ | $[0,1]$ | Alliance pulls (derived) |
| $C_{T,B}^{eff}$ | $[0,1]$ | Effective target resistance (derived) |
| All v11 primitives | $[0,1]$ | Unchanged |
| $S_{AB}^{(2)}$ post-amplification | $[0,1]$ | Clipped at 1 |

All probability outputs $P_{Tk} \in [0,1]$ follow from the bounded primitives and noisy-OR / multiplicative aggregations.

---

### Variable Definitions — Changes from v12

**New primitives**

- **$\Gamma_{AX}$ — Defection cost.** A's penalty for failing to honor a commitment to X (treaty obligation, reputational stake, prior commitments, public-sentiment cost). The single most consequential new variable: it drives opposition pull, support pull, and extended deterrence simultaneously. Estimate from ATOP / COW alliance depth coding plus credibility adjustments.
- **$R_X$ — Deliverable reinforcement capability.** X's expected military/economic contribution to a war it joins. Composite of force projection, alliance interoperability, geographic deliverability. Distinguishable from raw capability because most allies can't deliver their full power at distance.

**Removed primitives**

- **$\psi_i$ — Decision-maker resolve.** Removed; leader effects enter through time-varying $D_i$ and $K_i$ if needed.
- **$U_i^{first}$ — Baseline nuclear first-strike propensity.** Removed; nuclear war is now purely escalation-conditional.
- **$\mu$ — Extended deterrence multiplier.** Removed; extended deterrence is now native in $C_{T,B}^{eff}$ via the noisy-OR over $\Gamma_{XB} \cdot R_X$.
- **All Path 2 directional variables.** $T_{sup}, T_{opp}, C_{i,sup}^*, C_{i,opp}^*, E_{n,sup}, E_{n,opp}, S_{p,sup}, S_{p,opp}$ — collapsed into $\Phi^{opp}, \Phi^{sup}$, and a single non-directional $E_n, S_p$ per dyad-tier.
- **$W_{sev}^{(k)}$ — Tier-indexed severity.** No longer needed as input; severity is implicit in which tier the model evaluates. Retained as optional output-side weight $s_k$ for severity-summary statistics.

**Derived quantities (computed, not supplied)**

- $\Sigma_{AB} = \min(\nu_A, \nu_B)$ — mutual nuclear shadow
- $L_{conv,i} = \max(0, -\Delta P_i^{wartime})$ — wartime losing pressure
- $\Phi^{opp}, \Phi^{sup}, \Phi^{opp,net}$ — alliance pulls
- $C_{T,B}^{eff}$ — effective target resistance
- $U_i$ — conditional nuclear use probability
- $V_p^{\dagger}, V_t^{\dagger}$ — nuclear-shadow-suppressed prize/threat values (T3)
- $C_{p,AB}^*$ — adjusted commitment problem
- $S_{AB}^{(2)}$ — stability-instability-amplified spark

---

### Calibration Notes

- **Parameter count down substantially from v12.** The Path 2 machinery removal alone collapses ~14 parameters into 3–4 new ones. Combined with $\psi$ and $U^{first}$ removal, the model is meaningfully closer to identifiability against the available conflict-dyad evidence.
- **$\Gamma_{AX}$ is now the most important new variable.** It drives three distinct model channels (opposition pull, support pull, extended deterrence). Calibrate using ATOP alliance-depth coding adjusted for revealed credibility (history of honoring commitments, public statements, force posture). Treating $\Gamma_{AX} = \Gamma_{XA}$ is a simplifying assumption; real commitments are often asymmetric (US guarantees to South Korea vs. South Korea's reciprocal commitment).
- **$\Gamma$ should arguably be tier-indexed.** NATO Article 4 (T2) and Article 5 (T3) credibility differ. The base spec treats $\Gamma$ as tier-independent for simplicity; for high-stakes applications consider $\Gamma_{AX,k}$ with $\Gamma_{AX,1} \leq \Gamma_{AX,2} \leq \Gamma_{AX,3}$.
- **$R_X$ has reasonable empirical anchors.** Force projection literature, deployment time studies, and historical wartime contribution records all inform $R_X$. Distinguish from raw capability ($\nu_X$ or conventional equivalent): a nuclear-armed state with no deliverable conventional reinforcement (e.g., remote ally) has high $\nu$ but low $R$.
- **The alignment factor in $P_{co}$ requires $\Phi$ values from both sides of the dyad.** Asymmetric situations (A pulled to support B; B not pulled to support A) yield low alignment and low co-belligerency — capturing the realistic asymmetry that "alliance" is often one-sided.
- **Anchor for $\kappa$ unchanged** from v12: nuclear dyad MID rate ≈ 3–5× comparable non-nuclear dyads (Rauchhaus and successors).
- **The "leader effects through doctrine" claim should be tested.** If applications find $\psi_i$ removal misses important variation, the cleanest fix is allowing $D_i$ and $K_i$ to be time-varying with documented leader transitions, rather than restoring $\psi$ as a separate primitive.
- **Remaining structural concerns (carried over from v12 critique):** tier monotonicity interpretation, endogeneity of $D_i$ and $K_i$ to wartime dynamics, conventional MAD treatment, T4a/T4b split for tactical vs. strategic nuclear use, time-implicit period specification. These are independent of v13's simplifications and would require their own design decisions.

---

### Recovery of Prior Versions

- **v11 $P_{dyad}$** recoverable as either $P_{T2}$ (broadest "any militarized conflict") or $P_{T3}$ ("war" in the COW sense). Backward calibration should be done against whichever empirical target the v11 $\beta$ was tuned to.
- **v12 Path 1 outputs** recoverable by setting all $\Gamma_{AX} = 0$ (no alliance entanglement), all $I_{XB,k} = 0$ (no ongoing third-party wars), and using v12's $C_{T,B}$ in place of $C_{T,B}^{eff}$.
- **v12 Path 2 outputs** approximately recoverable through $\Phi^{opp}$ and $\Phi^{sup}$ given appropriate $\Gamma$ and $I$ inputs, though the conditional structure ("given B is at war") is now implicit rather than explicit.