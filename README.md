# TIERS

**T**iered **I**nterstate **E**scalation **R**isk **S**ystem — a
directed-dyad stochastic-game model of interstate conflict escalation,
persistence, and de-escalation.

TIERS merges seven major conflict and state-capability datasets into a
unified directed-dyad-year table, then estimates the probability that any
given pair of states will move up or down a six-tier conflict ladder over the
next year. It is intended both as a research instrument and as an operational
early-warning / scoring tool for current interstate dyads.

**Current implemented model:** v28.0 — transition-specific hazards plus
explicit economic interdependence: trade surface raises low-tier conflict
exposure, directed trade leverage raises economic-coercion risk, and mutual
dependence raises the cost of direct military escalation. See
[`docs/models/Unified Equation of Interstate War (Directed-Dyad -6 v28 draft).md`](docs/models/Unified%20Equation%20of%20Interstate%20War%20%28Directed-Dyad%20-6%20v28%20draft%29.md).

---

## At a glance

- **Multi-source data pipeline** integrating MIDB, UCDP, EUSANCT, CShapes,
  V-Dem, COW NMC, ATOP, CEPII BACI, and CEPII TRADHIST into a single
  directed-dyad-year schema.
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
- [Acknowledgments](#acknowledgments)
- [License](#license)

---

## Installation

The recommended setup uses [`uv`](https://github.com/astral-sh/uv) (handles
PEP 668 on Debian 13 / Ubuntu 24.04+ cleanly), but plain `pip` in a
virtual environment works too.

```bash
# Clone or download the repository
git clone https://github.com/afulle12/TIERS.git
cd tiers

# Option A: with uv
uv venv
uv pip install -r requirements.txt

# Option B: with plain pip in a venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

After setup, activate the environment before running anything:

```bash
source .venv/bin/activate            # bash / zsh
# or
.venv\Scripts\activate               # PowerShell on Windows
```

Requires Python 3.10 or newer.

### Running the Wikipedia tier-extraction pipeline

The Wikipedia pipeline (`scripts/build/wiki_pipeline.py` and
`scripts/build/_run_v2_pipeline.py`) is an orchestrator that runs
seven stages end-to-end and produces
`data/processed/conflict_dyads_wikipedia.csv`. The output is aligned
to the **v27.0 spec scheme** (T1=1, T2=2, T3=3, T4=4, T5=5) and the
**v27.0 labels** (`T2-Economic Coercion`, `T3-Proxy/Indirect Military`),
which differs from the legacy MIDB-based ground-truth labeling
(T2 and T3 both at hostlev=3). See
[`docs/wiki_pipeline.md`](docs/wiki_pipeline.md) for the full stage
table, configuration knobs, and validation report format. Quick start:

```bash
# Run all 7 stages end-to-end (uses OLLAMA_* env vars)
.venv/bin/python scripts/build/_run_v2_pipeline.py

# Or invoke individual stages via the orchestrator
.venv/bin/python scripts/build/wiki_pipeline.py run --stages 1,2,3,4,5,6,7
```

The v2 pipeline (7 stages, 3 LLM passes) replaces the legacy 9-stage
design that mixed structured infobox parsing with a tier classifier
and a separate event extractor. In the v2 design:

- **Stage 2** filters the 35 GB enwiki snapshot down to ~50–60k
  bilateral articles (DuckDB country scan + Python bilateral gate).
- **Stage 3** runs a batched LLM 0/1 filter that drops ~75% of
  articles as non-conflict.
- **Stage 4** is a single LLM call per article that emits the tier,
  start/end year, explanation, and the list of directed
  (initiator, target, confidence, implied) pairs.
- **Stage 5** is pure-Python aggregation that expands the duration
  range into one row per year, resolves country names to GWN codes,
  and writes a directed-dyad-year table covering 1900–2025.
- **Stage 6** resolves any unmapped country names via a final LLM
  pass, preserving the raw name in parentheses.
- **Stage 7** compares against `conflict_dyads_full.csv` (compound
  sources split on `_`) and produces a validation report and
  diagnostics.

The output is a directed-dyad-year table covering 1900–2025 with
per-year precision/recall/F1, per-dyad mismatch table, and a
cross-dataset comparison (agreement / disagreement / new) against
all ground-truth datasets (MIDB, UCDP, EUSANCT, ATOP).

Files in `scripts/build/legacy/` are from the old 9-stage design
and are no longer used by the active pipeline.

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
| EUSANCT | 2022 | T1 threats + T2 sanctions | [dataverse.harvard.edu](https://dataverse.harvard.edu/) |
| TIES | v4.0 | T1 non-imposed sanction threats | [sanctions.web.unc.edu](https://sanctions.web.unc.edu/) |
| ICB | v16 | T1 international crises (below T3) | [sites.duke.edu/icbdata](https://sites.duke.edu/icbdata/) |
| Pardee Diplometrics DRD | 1960–2025 | T1 recalls, withdrawals & expulsions | [pardee.du.edu](https://pardee.du.edu/) |
| CShapes | 2.0 | Country-year registry, GWN mapping | [icr.ethz.ch/data/cshapes](https://icr.ethz.ch/data/cshapes/) |
| V-Dem | v16 (Core) | Democracy proxy for `N_pub` | [v-dem.net/data](https://v-dem.net/data/) |
| COW NMC | v7.0 | Capability ratios, CINC | [correlatesofwar.org/data-sets/national-material-capabilities](https://correlatesofwar.org/data-sets/national-material-capabilities/) |
| ATOP | 3.0 | Alliance depth / treaty triggers | [dataverse.harvard.edu/dataset/doi:10.7910/DVN/IUUPWR](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/IUUPWR) |
| CEPII BACI | HS92 V202601 | 1995-2024 bilateral trade, v28 economic interdependence | [cepii.fr BACI](https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37) |
| CEPII TRADHIST | v4 | 1827-2014 historical bilateral trade and gravity data | [cepii.fr TRADHIST](https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=32) |

See `DATA_PROVENANCE.md` for source-by-source licensing and attribution notes.

---

## Running the pipeline

```bash
# 1. Rebuild all data tables (state system, source coverage, MID5, EUSANCT,
#    T1 union, dyad states, rivalry, trade interdependence, feature grids)
#    and verify all data-contract tests:
python scripts/build/build_pipeline.py

# 2. Run the full test suite
pytest tests/ -v

# 3. Backtest the models (writes summaries to output/analysis/)
python scripts/model/backtest_tiers_v27.py          # v27 structural baseline
python scripts/model/backtest_tiers_v28.py          # v28 transition-hazard engine
python scripts/model/backtest_tiers_v28_by_tier.py  # v28 per-tier step breakdown
python scripts/model/baseline_tiers_v27.py          # statistical baselines
```

The individual stage scripts under `scripts/build/` (`state_system.py`,
`source_coverage.py`, `build_mid_dyads.py`, `integrate_eusanct.py`,
`build_t1_sources.py`, `build_dyad_states.py`, `build_rivalry.py`,
`build_trade_interdependence.py`, `build_features.py`, `build_features_v27.py`,
`build_features_v28.py`) can also be run individually when iterating.

```bash
# 4. Forward-score live dyads (latest available year)
python scripts/model/tiers_score_v28.py

# 5. Run model invariants / sensitivity tests
python scripts/model/testModelv10.py
python scripts/model/tiers_invariants_testing.py
python scripts/model/tiers_v27_invariants_testing.py
python scripts/model/tiers_v28_invariants_testing.py
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

Three independent test suites run against the model:

- `scripts/model/testModelv10.py` — 4-level systematic validation: invariants,
  local sensitivity tornado, Monte Carlo global sensitivity, and rank-order
  validity against an expert-ordered set of dyads.
- `scripts/model/tiers_invariants_testing.py` — 5,000 random parameter sets
  checked for probability bounds, monotonicity, and edge cases.
- `scripts/model/tiers_v27_invariants_testing.py` — invariant and
  edge-case suite for the retained v27.0 cost-field baseline.
- `scripts/model/tiers_v28_invariants_testing.py` — probability-bound,
  Capability/Reach gate, and economic-sign tests for v28.0.
- `scripts/model/baseline_tiers_v27.py` — baseline comparison against
  logistic-regression and random-forest models trained on the same v27
  structural features.

Historical backtest of the v28.0 transition-hazard engine on 1946–2014
(train 1946–1989 / test 1990–2014, one row per unordered dyad-year, with
`source_coverage.py` masks applied), plus the v28 trade-enhanced 1995–2014
window:

| Target | Test AUC | Brier | Positives (test) |
|---|---:|---:|---:|
| Onset, any | 0.5637 | 0.0195 | 3,027 |
| Onset, force | **0.8246** | 0.0008 | 258 |
| Onset, war | NA (<20 pos) | NA | 14 |
| Escalation | 0.5870 | 0.0205 | 3,533 |
| De-escalation | 0.5577 | 0.1971 | 2,755 |

Per-step cumulative adjacent-tier AUCs are also reported (`backtest_tiers_v28_by_tier.py`):

| Transition | Cumulative AUC | Positives |
|---|---:|---:|
| T0 → T1+ | 0.6518 | 2,608 |
| T1 → T2+ | 0.5216 | 369 |
| T2 → T3+ | 0.6229 | 57 |
| T3 → T4+ | NA (<20 pos) | 11 |
| T4 → T5 | NA (<20 pos) | 4 |

Baseline comparison on `test_1990_2014` shows that the uncalibrated starting
priors still trail simple logistic regression on the repaired grid:

| Target | TIERS v28 AUC | Transition Matrix AUC | LogReg (`trade+struct`) AUC |
|---|---:|---:|---:|
| Onset, any | 0.5637 | 0.5000 | 0.7340 |
| Onset, force | 0.8246 | 0.5000 | 0.9113 |
| Escalation | 0.5870 | 0.5539 | 0.7383 |
| De-escalation | 0.5577 | 0.6889 | 0.7077 |

v28 results should be read as sign-constrained starting-prior results, not as
calibrated estimates. For full reports see
`output/analysis/model_calibration_summary_v28.md`,
`output/analysis/model_calibration_summary_v27.md`, and
`output/analysis/baseline_summary_v28.md`.

---

## Limitations

- **v28 coefficients are starting priors.** The v28 transition hazards use
  sign-constrained priors from the draft model. The CEPII trade inputs are now
  attached, but full coefficient calibration remains pending. The legacy v21
  product-form implementation (`tiers_lib.py`, `backtest_tiers.py`) and v27
  cost-field engine (`tiers_lib_v27.py`, `backtest_tiers_v27.py`) are retained
  for comparison.
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

If you use TIERS in academic work, please cite the current model
specification document and the upstream data sources listed in
`DATA_PROVENANCE.md`.

```bibtex
@article{tiers2026,
  title={Unified Equation of Interstate War (Directed-Dyad Variant) v28.0},
  author={Fuller, Andrew},
  year={2026},
  month={July}
}
```

See `CITATION.cff` for machine-readable citation metadata.

---

## Acknowledgments

This project was developed with the assistance of large language model
(LLM) tools. They were used for code review, refactoring, documentation
drafting, and infrastructure scaffolding. All theoretical content — model
specifications, tier taxonomy, variable definitions, mathematical
formulations, and the integration and interpretation of empirical
results — is the author's own work. The intent of this disclosure is
transparency: LLMs were used as a productivity aid, not as a source of
intellectual contribution.

---

## License

Code: **MIT** (see [LICENSE](LICENSE)).

Data: each source dataset is governed by its own license. The raw source files
are not redistributed in this repository; users must download them directly
from the providers and comply with the respective terms. See
[DATA_PROVENANCE.md](DATA_PROVENANCE.md) for details.

---

## Contact

Author: Andrew Fuller  
Repository URL: https://github.com/afulle12/TIERS
