# WarModel

A directed-dyad stochastic-game model of interstate conflict escalation,
persistence, and de-escalation.

WarModel merges seven major conflict and state-capability datasets into a
unified directed-dyad-year table, then estimates the probability that any
given pair of states will move up or down a six-tier conflict ladder over the
next year. It is intended both as a research instrument and as an operational
early-warning / scoring tool for current interstate dyads.

**Current model:** v27.0 — six-tier taxonomy, cost-field engine with
status-quo-biased direction stage, Capability/Reach gate on strategic war, and
WMD handled as a continuous severity modulator rather than a separate tier.

---

## At a glance

- **Multi-source data pipeline** integrating MIDB, UCDP, EUSANCT, CShapes,
  V-Dem, COW NMC, and ATOP into a single directed-dyad-year schema.
- **Stochastic-game model** with two paths to war: direct initiation and
  contagion / joining an existing war.
- **Empirical backtest** on 2.3M dyad-years (1946–2014), with calibrated
  parameters and ROC evaluation per escalation threshold.
- **Graceful degradation** — the model remains valid when inputs are missing,
  degrading to simpler nested members rather than failing.
- **Full version history** of model specs archived in `docs/model_drafts_archive/`.

---

## Table of contents

- [Installation](#installation)
- [Data](#data)
- [Running the pipeline](#running-the-pipeline)
- [Model overview](#model-overview)
- [Validation](#validation)
- [Limitations](#limitations)
- [Citation](#citation)
- [License](#license)

---

## Installation

```bash
# Clone or download the repository
git clone <repo-url>       # to be added once the public GitHub repo is set up
cd WarModel

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Requires Python 3.10 or newer.

---

## Data

The repository **does not include the raw source datasets** because several of
them have licenses that restrict bulk redistribution (e.g., COW MIDB/NMC,
EUSANCT, ATOP). Download them from their official providers and place them in
`data/raw/` before running the pipeline.

| Dataset | Version | Used for | Download / registration |
|---|---|---|---|
| COW MIDB + MIDA + MIDIP + MIDI | 5.0 | T1, T4, T5 events | [correlatesofwar.org/data-sets/MIDs](https://correlatesofwar.org/data-sets/MIDs/) |
| UCDP Dyadic | v26.1 | T3 proxy/support events | [ucdp.uu.se/downloads](https://ucdp.uu.se/downloads/) |
| UCDP/PRIO Armed Conflict | v26.1 | T3 conflict metadata | [ucdp.uu.se/downloads](https://ucdp.uu.se/downloads/) |
| EUSANCT | 2022 | T1 threats + T2 sanctions | [piie.com/research/eusanct](https://www.piie.com/research/eusanct) |
| CShapes | 2.0 | Country-year registry, GWN mapping | [cshapes.ethz.ch](https://cshapes.ethz.ch/) |
| V-Dem | v16 (Core) | Democracy proxy for `N_pub` | [v-dem.net/data](https://v-dem.net/data/) |
| COW NMC | v7.0 | Capability ratios, CINC | [correlatesofwar.org/data-sets/national-material-capabilities](https://correlatesofwar.org/data-sets/national-material-capabilities/) |
| ATOP | 3.0 | Alliance depth / treaty triggers | [atopdata.org](https://www.atopdata.org/) |

See `DATA_PROVENANCE.md` for source-by-source licensing and attribution notes.

---

## Running the pipeline

```bash
# 1. Build the directed-dyad event table (T1-T5)
python scripts/build/build_t1_dyads.py
python scripts/build/build_t3_dyads.py
python scripts/build/build_combined_dyads.py

# 2. Integrate EUSANCT sanctions and threats
python scripts/build/integrate_eusanct.py

# 3. Infer peace years and create the full T0-T5 grid
python scripts/build/build_t0_dyads.py

# 4. Attach empirical features (V-Dem, NMC, ATOP)
python scripts/build/build_features.py

# 5. Run analyses
python scripts/analysis/analyze_conflict_dyads.py
python scripts/analysis/tier_transition_risk.py
python scripts/analysis/tier_transition_risk_full.py

# 6. Backtest the model
python scripts/model/backtest_war_model.py

# 7. Run model invariants / sensitivity tests
python scripts/model/testModelv10.py
python scripts/model/warModelInvarientsTesting.py
```

Generated outputs go to `output/analysis/` and `output/charts/`; intermediate
large CSVs/Parquet files go to `data/processed/`.

---

## Model overview

### Tier taxonomy

| Tier | Label | Definition |
|---|---|---|
| T0 | Peace | Inferred: no T1–T5 event in the dyad-year |
| T1 | Diplomatic Crisis | Protests, recalls, ultimatums, coercive threats |
| T2 | Economic Coercion | Active sanctions, trade restrictions, financial exclusion |
| T3 | Proxy/Indirect Military | Sustained, selective support to j's adversaries |
| T4 | Limited Direct Military | Open, attributed exchange of fire |
| T5 | Strategic War | Nationwide / multi-front warfare; gated by reach/contiguity |

### Core equation (Path 1 — direct initiation)

For actor *A* considering escalation against *B*:

```
P_direct(A → B) = (1 − N_pub_A) · β · M · O · S · F

where
  M = max(avg(dP, R_d, A_div), P_v)                 # Motive
  O = max(V_p, V_t) · (1 − C_T_B · (1 − W_v_A))     # Opportunity
  S = avg(B, R_h, I_s)                              # Spark
  F = 1 − (1 − I_a) · (1 − C_p*) · (1 − I_i)        # Friction
```

**Path 2 — joining an existing war** is driven by treaty triggers, ethnic
kinship, strategic prestige, and the severity of an ongoing war.

### Architecture highlights

- **Cost-field engine**: each actor evaluates the cost of occupying each tier,
  plus a forward-looking strategic term and a belief-coupling term.
- **Status-quo-biased direction stage**: at neutral inputs the model predicts
  persistence; escalation and de-escalation must be *earned* through shocks or
  enablers.
- **Capability/Reach gate**: T5 is reachable only if the dyad is contiguous or
  one side can inflict considerable, sustainable damage on the other.
- **Nested-model family**: missing inputs degrade the model to simpler, still-
  valid members, each with a documented null value.

The full specification is in
`docs/models/Unified Equation of Interstate War (Directed-Dyad -5.md`.

---

## Validation

Two independent test suites run against the model:

- `scripts/model/testModelv10.py` — 4-level systematic validation: invariants,
  local sensitivity tornado, Monte Carlo global sensitivity, and rank-order
  validity against an expert-ordered set of dyads.
- `scripts/model/warModelInvarientsTesting.py` — 5,000 random parameter sets
  checked for probability bounds, monotonicity, and edge cases.

Historical backtest on 1946–2014 (train 1946–1989 / test 1990–2014):

| Threshold | Test AUC | Brier | Events |
|---|---|---|---|
| T0 → T1+ | 0.30 | 0.0053 | 1,061 |
| T0 → T4+ | 0.55 | 0.0008 | 151 |
| T0 → T5 | **0.64** | 0.0003 | 53 |
| Any escalation | 0.31 | 0.0060 | 1,198 |

The model discriminates high-severity escalation (T0→T5) meaningfully above
chance, but low-severity onset (T0→T1+) remains weak. See
`output/analysis/model_calibration_summary.md` for full results.

---

## Limitations

- **Spec-code drift.** `war_model_lib.py` and `backtest_war_model.py` still
  implement the v21-level product-form model. The v27.0 cost-field engine with
  status-quo-biased barriers and the Capability/Reach gate is fully specified
  in `docs/models/` but not yet implemented in code.
- **Path 2 not backtested.** The historical backtest currently scores only
  direct initiation (Path 1). Contagion/joining behavior (Path 2) is tested for
  invariants but not evaluated against historical data.
- **Defaults for structural inputs.** Several parameters — rivalry history
  (`R_h`), diversionary incentives (`A_div`), contiguity/proximity, ethnic
  kinship (`E_n`), prestige (`S_p`) — are set to neutral defaults because the
  corresponding empirical datasets are not yet attached.
- **C_d_opp is a placeholder.** Opposing alliance depth is currently computed
  as `1 − C_d_sup` rather than a real third-party lookup.
- **Calibration is partial.** Only the global `β` is calibrated to the observed
  T0→T1+ rate. Full maximum-likelihood or Bayesian calibration over all model
  parameters is pending.

---

## Citation

If you use WarModel in academic work, please cite the current model
specification document and the upstream data sources listed in
`DATA_PROVENANCE.md`.

```bibtex
@article{warmodel2026,
  title={Unified Equation of Interstate War (Directed-Dyad Variant) v27.0},
  author={Fuller, Andrew},
  year={2026},
  month={June}
}
```

See `CITATION.cff` for machine-readable citation metadata.

---

## License

Code: **MIT** (see `LICENSE`).

Data: each source dataset is governed by its own license. The raw source files
are not redistributed in this repository; users must download them directly
from the providers and comply with the respective terms. See
`DATA_PROVENANCE.md` for details.

---

## Contact

Author: Andrew Fuller  
Repository URL: to be added once the public GitHub repo is set up.
