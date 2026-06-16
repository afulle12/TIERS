# Unified Equation of Interstate War (Dyadic Variant) v19.4 — Specification

## Structured Specification

---

## 1. What v19.4 Changes From v19.2

v19.4 makes one substantive addition: a **unified equation section (§10)** that consolidates the full v19.2 model into a single master expression with sequential component definitions, in the same format as v18.3 §10. No equations, parameters, or architecture are changed. v19.3 was a notation pass only (not reproduced here).

| Change | v19.2 | v19.4 |
|---|---|---|
| Unified equation section | Absent | Added as §10 |
| All other architecture | As specified | Unchanged |

---

## 2. The Six-Tier Conflict Taxonomy

Unchanged from v19.2.

| Tier | Label | Character | Coding threshold |
|---|---|---|---|
| T0 | Absolute Peace | No conflict discourse; normal bilateral relations | Default state for all dyads |
| T1 | Diplomatic Dispute | Formal disagreement, protests, summoning of ambassadors, UN votes, legal filings | ICB crisis trigger or equivalent bilateral diplomatic friction |
| T2 | Economic Coercion | Sanctions, embargoes, asset freezes, tariff weapons deployed against the adversary | TIES coding: economic instrument deployed with coercive intent |
| T3 | Limited Military Action | Bounded military operations with defined scope, geography, or implicit ceiling | MID hostility level 4–5; discrete operation with identifiable limits |
| T4 | State of War | Sustained military conflict; operational restraints dissolved; political relationship organized around the war | COW inter-state war threshold or equivalent sustained mobilization |
| T5 | Nuclear War | Nuclear weapons employed against the adversary by a nuclear-armed state | Deployment of nuclear warhead against military or civilian target |

---

## 3–9. Architecture

Unchanged from v19.2. See v19.2 §§3–9 for full specification of the state-transition architecture, movement-category scores, nuclear capability constraints, bilateral escalation hazard, destination-tier allocation, within-tier severity, skip barriers, and nuclear shadow.

---

## 10. Unified Equation Summary (New in v19.4)

The full model reduces to the following expression plus its component definitions. Reading from top to bottom is a complete specification of the forecast for any dyad at any current tier.

---

### Master Equation

$$\boxed{
\pi_{kj}(t) =
\begin{cases}
P_{\downarrow}(T_k)\cdot\omega_{kj}^{-} & j < k \\[4pt]
P_{0}(T_k) & j = k \\[4pt]
P_{\uparrow}(T_k)\cdot\omega_{kj}^{+} & j > k
\end{cases}
}$$

$\pi_{kj}(t)$ is the probability of transitioning from current tier $T_k$ to tier $T_j$ over the next period $\Delta$, given dyad $AB$ at time $t$. $\sum_{j=0}^{5}\pi_{kj}=1$ by construction. Boundary constraints: $P_{\downarrow}(T_0)=0$; $P_{\uparrow}(T_5)=0$.

---

### Movement Probabilities

$$P_{\downarrow}(T_k) = \frac{\exp(U_k^{\downarrow})}{Z_k}, \qquad
P_{0}(T_k) = \frac{\exp(U_k^{0})}{Z_k}, \qquad
P_{\uparrow}(T_k) = \frac{\exp(U_k^{\uparrow})}{Z_k}$$

$$Z_k = \exp(U_k^{\downarrow}) + \exp(U_k^{0}) + \exp(U_k^{\uparrow})$$

---

### Movement-Category Scores

$$U_k^{\downarrow} = \alpha_k^{\downarrow} + \beta_{dS} S_k + \beta_M M_{AB}^{\text{med}} + \beta_C C_{AB}^{\text{conc}} + \beta_X X_{AB}^{\text{collapse}} - \lambda_k^{\downarrow} D_k$$

$$U_k^{0} = \alpha_k^{0} + \rho_k D_k + \beta_F F_{AB} - \beta_M^{0} M_{AB}^{\text{med}}$$

$$U_k^{\uparrow} = \alpha_k^{\uparrow} + \beta_{uS} S_k + \beta_s S_k^{**} + \sigma_k h_{AB} + \nu_k^{\text{nuke}} + \beta_{\text{haz}}\cdot h_k^{\uparrow}$$

---

### Nuclear Term in $U_k^{\uparrow}$

$$\nu_k^{\text{nuke}} = \mathbf{1}[\text{anyNuke}]\cdot\Bigl[\beta_{\Theta}\Theta_{AB}\cdot\mathbf{1}[k\ge 4] + \beta_N(1-\mathcal{N}_{AB})\cdot\mathbf{1}[k=4] + \beta_{\text{mono}}\cdot\text{Monopoly}_{AB}\cdot\mathbf{1}[k=5]\Bigr]$$

$\nu_k^{\text{nuke}} = 0$ identically when $\text{anyNuke}=\text{false}$; T5 is excluded from the reachable destination set in that case.

---

### Bilateral Escalation Hazard

$$h_k^{\uparrow} = 1-(1-p_k^A)(1-p_k^B)$$

where $p_k^A$, $p_k^B$ are actor-specific escalation probabilities at tier $k$.

**Nuclear initiation gate** (feeds $p_k^i$ at $k=4$):

$$p_4^i = \text{HasNuke}_i \cdot \sigma\!\left(\alpha_{45} + \beta_{\Theta}\Theta_{AB} + \beta_N(1-\mathcal{N}_{AB}) + \beta_{\Psi}\Psi_i\cdot D_{A,i} + \beta_{\text{mono}}\cdot\text{Monopoly}_{AB} + w_5\cdot L_{\text{base},i} + f_{5,i}\right)$$

---

### External Public Opinion Field

$$h_{AB} = \beta_h\cdot\Psi_{AB}\cdot D_A$$

$$\sigma_k = k/5 \qquad (k \in \{0,1,2,3,4,5\})$$

---

### Skip Barrier

$$S_k^{**} = \left(\Phi_{AB}^{FMA}\right)^{\eta_\phi} \cdot \left(\text{WindowClose}_{AB}\right)^{\eta_w} \cdot \left(\text{OffRampAbsence}_{AB}\right)^{\eta_r} \cdot \left(1-\mathcal{N}_{AB}^{\eta_n}\right)$$

For the T2→T4 skip: multiply by $\mathbf{1}[S_2>\tau_E]$.

---

### Structural Motive

$$\widetilde{M}^*_{AB} = \widetilde{M}_{AB}\cdot(1+\varphi_\xi\Xi_{AB})$$

$$\widetilde{M}_{AB} = \Phi_{AB}^{opp}\exp\!\left(-\gamma_1\Phi_{AB}^{sup} - \gamma_2\Phi_{AB}^{coop}\right)$$

---

### Base Log-Odds

$$\mathcal{L}_{\text{base}} = \beta_0 + \beta_m\widetilde{M}^*_{AB} + \beta_r\mathcal{R}_{AB} + \beta_a(2A_{AB}-1)C_{AB}\cdot\mathbf{1}[\Phi^{opp}>\tau_{opp}] + \beta_c\Phi^{coop}_{AB}$$

$\mathcal{L}_{\text{base}}$ enters $U_k^{\uparrow}$ through the actor-level hazard chains $p_k^A$, $p_k^B$ and through the severity scalars at higher tiers.

---

### Destination-Tier Allocation Weights

$$\omega_{kj}^{-} = \frac{\exp(V_{kj}^{-})}{\displaystyle\sum_{m=0}^{k-1}\exp(V_{km}^{-})} \quad (j<k), \qquad
\omega_{kj}^{+} = \frac{\exp(V_{kj}^{+})}{\displaystyle\sum_{m=k+1}^{5}\exp(V_{km}^{+})} \quad (j>k)$$

$V_{kj}^{+}$ is set to $-\infty$ for $j=5$ when $\text{anyNuke}=\text{false}$.

---

### Nuclear Regime Auto-Derivation

$$\text{Monopoly}_{AB} = \mathbf{1}\!\left[\text{HasNuke}_A + \text{HasNuke}_B = 1\right]$$

| $\text{HasNuke}_A$ | $\text{HasNuke}_B$ | Regime | T5 reachable |
|:---:|:---:|---|:---:|
| 0 | 0 | Non-nuclear | No |
| 1 | 0 | Monopoly (A) | Yes (A only) |
| 0 | 1 | Monopoly (B) | Yes (B only) |
| 1 | 1 | MAD | Yes (both) |

---

## 11. Open Questions

Unchanged from v19.2. See v19.2 §11 for current status of all open questions.

---

## 12. Parameters

Unchanged from v19.2. See v19.2 §12.

---

## 13. Validation Priorities

Unchanged from v19.2. See v19.2 §13.

---

## 14. Practical Interpretation

Unchanged from v19.2. Workflow:

1. Code `HasNuke` for each actor → determines T5 reachability and auto-derives Monopoly.
2. Code current tier $X_t$ from the structured questionnaire.
3. Code within-tier severity $S_k$, duration $D_k$, and dynamic covariates.
4. Compute $(U_k^\downarrow, U_k^0, U_k^\uparrow)$ from §10.
5. Softmax → $(P_\downarrow, P_0, P_\uparrow)$.
6. Allocate across destination tiers → full $\pi_{kj}$ distribution.

---

*v19.4 supersedes v19.2 in presentation only. All parameter values, equations, and architectural decisions from v19.2 are unchanged. The §10 unified summary is the sole addition.*