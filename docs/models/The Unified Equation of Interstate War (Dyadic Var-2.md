### The Unified Equation of Interstate War (Dyadic Variant) — v14

**Changelog (v13 → v14):** One structural extension to close the peacetime-alignment gap.

The v13 alliance pulls $\Phi^{opp}$ and $\Phi^{sup}$ are defined entirely over *active engagements* — they only register signal when some state in the alliance graph is currently fighting. In peacetime, both collapse to zero for every dyad, and the co-belligerency alignment factor degenerates to $\epsilon/\epsilon = 1$ regardless of whether the dyad is China–Taiwan or US–UK. This is mathematically correct under v13 (which scopes alignment to active co-belligerency) but creates a misleading display and, more importantly, loses signal that *should* enter the unified motive: deep peacetime rivalries should augment Motive even before any war begins.

v14 adds a single primitive — **structural rivalry** $\Omega_{AB}$ — that mirrors $\Gamma_{AB}$ on the opposition side of the alliance graph. The active-engagement machinery from v13 is preserved unchanged; the structural channel adds in parallel via noisy-OR.

**Variable added:** $\Omega_{AB}$ (structural rivalry, primitive; symmetric in standard use but allowed asymmetric).

**Variables modified:**
- $\Phi^{opp}_{AB,k}$ — direct $\Omega_{AB}$ prefactor added
- $\Phi^{sup}_{AB,k}$ — dropped the $\mathbb{1}[B \text{ engaged at tier } k]$ gate on the $\Gamma_{AB}$ channel; latent alliance commitment now registers in peacetime
- $\mathcal{E}_A$ — adversary set now defined quantitatively as $\{X : \Omega_{AX} > 0\}$, mirroring $\mathcal{A}_A = \{X : \Gamma_{AX} > 0\}$

**Variables removed:** none.

All Path 1 machinery downstream of $\Phi$ — net opposition pull, betrayal penalty, unified Motive, alignment factor, $C_{T,B}^{eff}$ — is unchanged in form. The fix propagates entirely through redefining the two inputs.

---

### The New Primitive: $\Omega_{AB}$

$\Omega_{AB} \in [0,1]$ — A's structural rivalry with B. The pull-side mirror of $\Gamma_{AB}$. Captures:

- Explicit rivalry framing in doctrine / strategic documents
- Contested territorial or sovereignty claims
- Sustained great-power competition
- Ideological opposition that survives leadership transitions
- Active sanctions or economic warfare absent open military conflict
- Sustained MID history without active engagement (past decade)

**Distinguish from $R_{h,AB}$.** $R_h$ is dyadic and feeds Spark — it captures "deep history influencing willingness to clash on a given flashpoint." $\Omega$ is alliance-graph-resident — it describes the rivalry edge between two nodes and is queryable for any pair $(A, X)$. They will be highly correlated in practice; a consistency check is $\Omega_{AB} \approx R_{h,AB}$ for the focal dyad, with deviation flagged for review. Treating them as independent primitives keeps the spec clean and lets calibration sources differ (R_h from MID/dispute records; $\Omega$ from contemporary strategic-competition coding).

**Symmetry.** Most rivalries are mutually recognized — both states code each other as adversaries — so the default convention is $\Omega_{AB} = \Omega_{BA}$. Asymmetry is permitted (e.g., one state views the relationship as rivalry while the other views it as transactional), matching the v13 convention for $\Gamma$.

**$\Omega_{AA} \equiv 0$** by convention.

---

### Updated Φ Formulas

**Opposition pull** — A's alliance-graph-driven motivation to fight B at tier $k$:

$$\Phi^{opp}_{AB,k} = 1 - (1 - \Omega_{AB}) \cdot \prod_{X \in \mathcal{A}_A} \big(1 - I_{XB,k} \cdot \Gamma_{AX}\big)$$

Three channels noisy-OR'd:

1. **Direct structural rivalry** ($\Omega_{AB}$) — A and B are themselves rivals.
2. **Active alliance-graph engagement** ($I_{XB,k} \cdot \Gamma_{AX}$) — A's ally X is actively fighting B; weighted by A's defection cost.

Setting $\Omega_{AB} = 0$ recovers the v13 formula exactly.

**Support pull** — A's alliance-graph-driven motivation to fight on B's side at tier $k$:

$$\Phi^{sup}_{AB,k} = 1 - (1 - \Gamma_{AB}) \cdot \prod_{Y \in \mathcal{E}_A} \big(1 - I_{BY,k}\big)$$

Two channels noisy-OR'd:

1. **Direct structural alliance** ($\Gamma_{AB}$) — A is committed to B; the commitment is latent in peacetime and becomes operative if B enters any war. **The v13 gate $\mathbb{1}[B \text{ engaged at tier } k]$ is removed**: betrayal cost is paid whenever A acts against B, including in peacetime, so peacetime commitment must register in the pull.
2. **Enemy-of-my-enemy** ($I_{BY,k}$) — A's adversary Y is actively fighting B.

Setting all $I_{BY,k} = 0$ in v13 with B not engaged yielded $\Phi^{sup} = 0$. The v14 form yields $\Phi^{sup} = \Gamma_{AB}$ — the latent commitment.

**Net opposition pull** — unchanged:

$$\Phi^{opp,net}_{AB,k} = \max\!\big(0,\ \Phi^{opp}_{AB,k} - C_b \cdot \Phi^{sup}_{AB,k}\big)$$

with $C_b = 0.95$. The betrayal penalty now operates on structural commitment too: a state structurally committed to B has its rivalry-driven opposition pull discounted, capturing "I dislike them but we're allied — I won't attack."

---

### Optional Extension: Allied-Network Structural Rivalry

The v14 formula for $\Phi^{opp}$ captures direct A-B structural rivalry but still requires *active engagement* ($I_{XB,k}$) for alliance-graph contagion. A fuller treatment would let allies' structural rivalries propagate too — e.g., if the US is structurally hostile to China, the UK (US's ally) feels some pull to also oppose China even with no active war.

The extended form:

$$\Phi^{opp}_{AB,k} = 1 - (1 - \Omega_{AB}) \cdot \prod_{X \in \mathcal{A}_A} \big(1 - \Gamma_{AX} \cdot \eta_{XB,k}\big)$$

where the conflict indicator becomes structural-or-active:

$$\eta_{XB,k} = 1 - (1 - I_{XB,k})(1 - \Omega_{XB})$$

And symmetrically for support:

$$\Phi^{sup}_{AB,k} = 1 - (1 - \Gamma_{AB}) \cdot \prod_{Y \in \mathcal{E}_A} \big(1 - \Omega_{AY} \cdot \zeta_{BY,k}\big)$$

$$\zeta_{BY,k} = 1 - (1 - I_{BY,k})(1 - \Omega_{BY})$$

**This extension is left optional in v14** because it requires the full bilateral $\Omega$ matrix over the alliance graph, not just $\Omega_{AB}$ for the focal dyad. Applications targeting a single dyad in a stable alliance graph (NATO-internal, e.g.) can use the minimal v14 form; applications computing many dyads simultaneously across a graph (regional risk maps) should use the extended form. The dashboard variant in the simplified UI uses minimal v14.

---

### Recovery of v13 Outputs

v13 is recoverable from v14 by setting:

1. $\Omega_{AB} = 0$ for the focal dyad
2. All $\Omega_{XB} = 0$ in the extended form (no allied-network structural channel)
3. Re-introducing the gate: $\Gamma_{AB} \leftarrow \Gamma_{AB} \cdot \mathbb{1}[B \text{ engaged at tier } k]$ in the $\Phi^{sup}$ direct channel

Conditions 1–2 alone give "v13 alignment math with v14 latent support" — a useful intermediate for sensitivity analysis.

---

### Worked Examples

All examples use the minimal v14 form with no active third-party engagements ($I_{XB,k} = I_{BY,k} = 0$ throughout). This is the regime where v13 produces the degenerate alignment $\approx 1.000$.

**China–Taiwan** ($\Gamma_{dyad} = 0$, $\Omega_{dyad} = 0.95$ symmetric)

- $\Phi^{opp}_{CN,TW} = \Omega = 0.95$;  $\Phi^{sup}_{CN,TW} = \Gamma = 0$
- $\Phi^{opp}_{TW,CN} = 0.95$;  $\Phi^{sup}_{TW,CN} = 0$
- Alignment: $(0 \cdot 0 + \epsilon) / (0 + 0.95 \cdot 0.95 + \epsilon) \approx 0.011$ ✓
- Net opposition pull for China: $\max(0, 0.95 - 0.95 \cdot 0) = 0.95$ → strong augmentation of $M^u$ ✓

**US–UK** ($\Gamma_{dyad} \approx 0.95$, $\Omega_{dyad} \approx 0$)

- $\Phi^{opp} \approx 0$ both directions
- $\Phi^{sup} \approx 0.95$ both directions
- Alignment: $\approx 1.0$ ✓
- Net opposition pull: $\max(0, 0 - 0.95 \cdot 0.95) = 0$ ✓ (no alliance-driven motive to attack)

**Russia–Iran** ($\Gamma_{dyad} \approx 0.35$, $\Omega_{dyad} \approx 0$; both anti-US)

- $\Phi^{opp} \approx 0$ both directions (no direct rivalry)
- $\Phi^{sup} \approx 0.35$ both directions (latent commitment from strategic alignment)
- Alignment: $\approx (0.12 + \epsilon)/(0.12 + 0 + \epsilon) \approx 1.0$ ✓

(The extended-form would further raise $\Phi^{sup}$ via the shared-adversary channel — capturing Russia and Iran's mutual rivalry with the US even without active war.)

**India–Pakistan** ($\Gamma_{dyad} = 0$, $\Omega_{dyad} \approx 0.85$)

- $\Phi^{opp} \approx 0.85$ both directions
- $\Phi^{sup} \approx 0$ both directions
- Alignment: $\approx 0.014$ ✓
- Net opposition pull augments Motive on both sides ✓

**Brazil–Indonesia** ($\Gamma_{dyad} \approx 0$, $\Omega_{dyad} \approx 0$ — no significant relationship)

- All $\Phi \approx 0$
- Alignment: $\epsilon/\epsilon = 1.0$ — **still degenerate**

The alignment factor remains undefined for truly disconnected dyads (no relationship in either direction). The fix for this is at the *display* layer, not the model: when $\Phi^{sup}_{AB} \cdot \Phi^{sup}_{BA} + \Phi^{opp}_{AB} \cdot \Phi^{opp}_{BA}$ is below a threshold, the dashboard should render `—` or `N/A (no graph signal)`. v14 changes the model so that this "no signal" case becomes restricted to genuinely irrelevant pairs rather than "any peacetime dyad."

---

### Calibration Notes for $\Omega$

- **Anchor with rivalry datasets.** Thompson's "strategic rivalry" coding, Bennett-Stam, and the Klein-Goertz-Diehl dataset all provide binary or ordinal rivalry indicators that can be rescaled to $[0,1]$.
- **Cross-check with $R_h$.** If $R_h$ has already been coded for the focal dyad from MID/dispute history, $\Omega_{AB}$ should be calibrated to a value within ~0.2 of $R_h$. Larger gaps warrant analytical review (e.g., a rivalry that has cooled — $R_h$ high but $\Omega$ low — or one that has flared recently without long history — $\Omega$ high, $R_h$ low).
- **Watch the $C_b = 0.95$ interaction.** Because the betrayal penalty is severe, even modest $\Gamma_{AB}$ heavily discounts $\Omega_{AB}$ in the net pull. This is intentional — formal commitments to a structural rival are rare but extremely binding when they exist (e.g., postwar France–Germany). Document any case where $\Gamma_{AB} > 0$ and $\Omega_{AB} > 0$ coexist; these are model edge cases that should be sanity-checked manually.
- **Avoid double-counting $R_h$ in Spark vs. $\Omega$ in Motive.** They serve different functions: $R_h$ governs "given a flashpoint, does the dyad clash" (Spark), while $\Omega$ governs "does the dyad have latent motive to engage" (Motive via $\Phi^{opp,net}$). Both channels are legitimate and the v13 separation of Spark from Motive is preserved. Empirically, the same rivalry-source data will inform both — that is acceptable as long as the analyst is aware they are populating two distinct theoretical roles.

---

### Implementation: Simplified UI Form

The dashboard implementation uses aggregated scalars rather than the full graph. The minimal v14 patch to the v13 JavaScript:

```javascript
// Add to varDefs:
{ id: 'Omega_dyad', math: '&Omega;<sub>dyad</sub>',
  name: 'Structural rivalry with target',
  group: 'contagion', defaultA: 0.0, defaultB: 0.0 }

// Replace the v13 Phi calculations in calculate():
const Phi_opp_v13 = s.I_ally_vs_opp * s.Gamma_allies;
const Phi_opp = 1 - (1 - s.Omega_dyad) * (1 - Phi_opp_v13);

const Phi_sup_v13 = 1 - (1 - s.Gamma_dyad * s.I_opp_engaged) * (1 - s.I_enemy_vs_opp);
// v14: latent Γ_dyad replaces the gated form; active engagement still amplifies via enemy channel
const Phi_sup = 1 - (1 - s.Gamma_dyad) * (1 - s.I_enemy_vs_opp);

const Phi_opp_net = Math.max(0, Phi_opp - 0.95 * Phi_sup);
```

A display-layer guard is also recommended to avoid the residual $\epsilon/\epsilon = 1$ issue on truly disconnected dyads:

```javascript
const total = resA.Phi_sup * resB.Phi_sup + resA.Phi_opp * resB.Phi_opp;
const align = total < 1e-4 ? null : (resA.Phi_sup * resB.Phi_sup + eps) / (total + eps);
document.getElementById('dash-co').innerText =
  align === null ? '—' : align.toFixed(3);
```

The prompt template should also be updated to ask the LLM for $\Omega_{dyad}$, with a sentence in the variable-definition block:

> `Omega_dyad`: Structural rivalry between A and B — explicit hostility, contested claims, sustained strategic competition. Distinct from R_h (which captures historical dispute pattern); should be close to R_h for most dyads but can diverge when rivalry has recently flared or cooled.

The `I_opp_engaged` primitive can remain in the UI (it still has a use in the *extended* form for downstream third-party tier calculations) but no longer gates anything in the minimal v14.

---

### Open Issues / Forward-Looking Considerations

- **Allied-network structural rivalry.** The optional extended form propagates $\Omega$ through the alliance graph. The minimal v14 deliberately does not, to limit the new-primitive surface area. Applications that compute many dyads on a stable graph should adopt the extended form (it costs nothing additional once $\Omega$ is coded graph-wide).
- **Asymmetric $\Omega$.** Standard usage is symmetric. Asymmetric coding (one state perceives rivalry, the other does not) is rare but real — typically captured in cases of unrequited threat perception (e.g., a small state fearing a large neighbor that views the small state as irrelevant). When asymmetric, treat as two distinct primitives $\Omega_{AB}$ and $\Omega_{BA}$ as v13 already does for $\Gamma$.
- **Tier-dependence of $\Omega$.** Like $\Gamma$ in v13, $\Omega$ is currently tier-independent. For high-stakes applications, $\Omega_{AB,k}$ with monotone increase in $k$ may be warranted — economic rivalry (T1) can be very high while military rivalry (T3) is lower (US–China economic, less so military), or vice versa.
- **The latent-vs-operative distinction.** Removing the gate on $\Gamma_{AB}$ in $\Phi^{sup}$ means peacetime alliance commitment registers in the alignment factor. This is correct for measuring *strategic* alignment. It is overly generous if the alignment factor is to be interpreted as a probability of *actual* co-belligerent participation: a state committed to an ally that is at peace contributes no actual fighting force. A future v15 could split $\Phi^{sup,latent}$ (used in alignment) from $\Phi^{sup,operative}$ (used in P_co probability), with the gate restored only on the operative variant. v14 keeps the two unified for simplicity.
- **Sanity check the $\Gamma > 0, \Omega > 0$ corner.** Formally allowed but historically rare. When it arises (think: postwar France–Germany, or Cold War US–Yugoslavia), the model should produce dampened but non-zero net opposition pull, and analysts should verify the case manually.