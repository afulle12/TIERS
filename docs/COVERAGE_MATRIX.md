# TIERS v27.0 Coverage Matrix

Per-variable observability for the v27.0 cost-field engine, the data sources
that feed it, and the active model member each input state implies. Spec
reference: `docs/models/Unified Equation of Interstate War (Directed-Dyad -5).md`
sections 1.6, 1.9, 3.1, 3.8.

| Variable | Spec § | Source | State in this run | Notes |
|---|---|---|---|---|
| $X_t$ — Current tier | 1.6.1 | `conflict_dyads_full.csv` (`uiw_tier`) | **observed** (100%) | High-salience; fail-loud if unresolvable. |
| $D_k$ — Duration | 1.6.3 | Derived from `tier_transitions_full.csv` (years at current tier) | **observed** (99%) | Triple role: persistence, lock-in, Attribution×Duration. |
| $\Omega$ — Rivalry | 1.6.4 | `data/processed/rivalry_omega.csv` (built from MIDB 5.0) | **empirical** (3% of 2014 dyads) | 928/30,435 directed pairs have a recency-decayed MID history. Other dyads default to 0 (no MID history). |
| $\Xi$ — Contiguity | 1.6.4 | `data/processed/contiguity_xi.csv` (built from CShapes 2.0) | **empirical** (100%) | {0, 0.5, 1}; also feeds the Capability/Reach gate. |
| $FMA_{i\to j}$ | 1.6.5 | `data/processed/contiguity_xi.csv` (`fma` column) | **empirical** (100%) | First-Mover Advantage from great-circle distance. |
| $-\dot W_{i\to j}$ | 1.6.5 | `data/processed/dyads_with_features_v27.parquet` (`closing_window_a/b`) | **empirical** (99.7%) | Rolling 5-year CINC growth from NMC v7.0. |
| Status-Quo Burden | 1.6.5 | None attached | **defaulted** | Spec allows a default; we use 0.5. |
| $W_x$ | 1.6.5 | None attached | **defaulted** | Used by DeEsc. |
| $ORA$ | 1.6.5 | None attached | **defaulted** | Used by DeEsc (1-ORA). |
| $Stal_t$ | 1.6.5 | None attached | **defaulted** | Used by the diagnostic fallback. |
| $Dip_{cap}$ | 1.6.5 | None attached | **defaulted** | Used by DeEsc. |
| $Shock_k$ | 1.6.5 | None attached | **defaulted** (set to 0) | Could be derived from event data. |
| $DeEsc_k$ | 1.6.5 | Composition of defaulted inputs | **defaulted** (set to 0) | Yields the floor-only de-escalation member. |
| $V_{contagion}$ | 1.6.5 | None attached | **absent** | Needs regional network analysis. |
| $WMD$ | 1.6.5 | None attached | **absent** | Cap consistency condition not exercised. |
| $Cap_{i\to j}$ | 1.6.5 / 3.7 | `data/processed/dyads_with_features_v27.parquet` (`cap_a_to_b`, `cap_b_to_a`) | **empirical** (100%) | Composite of $\Xi$, CINC share, distance. **High-salience** for the T5 reach gate. |
| $\hat{\mathcal{C}}_i(\mathcal{C}_c)$ — Belief | 1.6.5 | None attached | **absent** | $\delta=0$ -> public member active. |
| Attribution | 1.6.1 | `data/processed/conflict_dyads_full.csv` (`attribution`) | **empirical** (0.5% — T3 rows only) | Modifier is 0 for non-T3 dyads. |
| Integration depth | 1.6.5 | None attached | **defaulted** | Could be derived from ATOP depth asymmetry. |
| Stakes | 1.6.5 | None attached | **defaulted** | Per spec, falls back to $\Omega\Xi$. |
| Intent/selectivity | 1.6.5 | None attached | **absent** | T3 entry gate; classification fallback. |
| $A_{div}$ — Diversionary | 1.6.5 | None attached | **defaulted** | Needs domestic stress signal (election cycle, protest). |
| $E_n$ — Ethnic kinship | 1.6.5 | None attached | **defaulted** | Needs kin-countries dataset (not in repo). |
| $S_p$ — Strategic prestige | 1.6.5 | None attached | **defaulted** | Needs international status dataset (not in repo). |
| $B^{econ}, B^{blood}, V_i$ | 3.1 | None attached | **absent** | Triggers diagnostic-fallback member for the cost field. |

## Active member by row

The engine resolves the active member per spec section 1.9.2. In the
current run, every row operates in the **diagnostic-fallback** member (cost
field absent) for the cost field, but the **public** member for the
structural axis ($\delta=0$ for belief; the structural inputs themselves
are mostly empirical). All orthogonal reductions in the spec are reachable
if the relevant input drops to ABSENT in a future re-run.

## Coverage summary from the 2014 forward score

| Variable | Empirical | Defaulted | Absent |
|---|---|---|---|
| Contiguity (Xi) | 30,435 (100%) | 0 | 0 |
| FMA | 30,435 (100%) | 0 | 0 |
| Closing window | 30,353 (99.7%) | 82 (0.3%) | 0 |
| Rivalry (Omega) | 928 (3%) | 29,507 (97%) | 0 |
| Cap | 30,435 (100%) | 0 | 0 |
| Attribution | 160 (0.5%) | 30,275 (99.5%) | 0 |
| D_k | 30,142 (99%) | 293 (1%) | 0 |
| Cost field | 0 | 0 | 30,435 (100%) |

## Spec section 1.9.6 fail-loud variables

The spec lists three high-salience variables: CurrentTier, Cap, and the T3
entry gate. The implementation refuses to silently default them. In the
current run:
- CurrentTier: 100% observed.
- Cap: 100% observed (empirical composite of empirical inputs).
- T3 entry gate: marked as absent in the coverage; the engine treats T3
  rows as already gated by the existing T3 codings in `conflict_dyads_full`.

## What's NOT covered

The following would each be its own sub-project:
- A_div (diversionary incentive) — needs a domestic-stress signal.
- E_n (ethnic kinship) — needs a kin-countries dataset (Cederman-Magher
  fearon-laitin fractionalization is a partial proxy).
- S_p (strategic prestige) — needs an international-status dataset.
- V_contagion (regional contagion) — needs a regional-conflict network.
- B^econ, B^blood, V_i (cost-field occupancy) — needs cost data
  (SIPRI, trade flows, enterprise surveys).
- WMD sub-components — needs WMD capability data.
- Belief term — needs a belief-survey data source (or expert elicitation).

Adding any of these would extend coverage; the engine's active-member
resolver automatically uses a richer member when more inputs are observed.
