# TIERS

**T**iered **I**nterstate **E**scalation **R**isk **S**ystem — a
directed-dyad stochastic-game model of interstate conflict escalation,
persistence, and de-escalation.

TIERS merges seven major conflict and state-capability datasets into a
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
- [Acknowledgments](#acknowledgments)
- [License](#license)

---

## Installation

The recommended setup uses [`uv`](https://github.com/astral-sh/uv) (handles
PEP 668 on Debian 13 / Ubuntu 24.04+ cleanly), but plain `pip` in a
virtual environment works too.

```bash
# Clone or download the repository
git clone <repo-url>       # to be added once the public GitHub repo is set up
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
| EUSANCT | 2022 | T1 threats + T2 sanctions | [sanctionsplatform.ohchr.org/record/20861](https://sanctionsplatform.ohchr.org/record/20861?ln=en) |
| CShapes | 2.0 | Country-year registry, GWN mapping | [icr.ethz.ch/data/cshapes](https://icr.ethz.ch/data/cshapes/) |
| V-Dem | v16 (Core) | Democracy proxy for `N_pub` | [v-dem.net/data](https://v-dem.net/data/) |
| COW NMC | v7.0 | Capability ratios, CINC | [correlatesofwar.org/data-sets/national-material-capabilities](https://correlatesofwar.org/data-sets/national-material-capabilities/) |
| ATOP | 3.0 | Alliance depth / treaty triggers | [dataverse.harvard.edu/dataset/doi:10.7910/DVN/IUUPWR](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/IUUPWR) |

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

# 6. Build the v27 structural inputs and features grid
python scripts/build/build_contiguity.py       # CShapes contiguity, distance, FMA
python scripts/build/build_rivalry.py          # MIDB recency-decayed rivalry (Omega)
python scripts/build/build_features_v27.py     # v27 features grid (parquet)

# 7. Backtest the models
python scripts/model/backtest_eirene.py        # legacy v21 product-form
python scripts/model/backtest_eirene_v27.py    # v27 cost-field engine

# 8. Forward-score live dyads (latest available year)
python scripts/model/eirene_score_v27.py

# 9. Run model invariants / sensitivity tests
python scripts/model/testModelv10.py
python scripts/model/eirene_invariants_testing.py
python scripts/model/eirene_v27_invariants_testing.py
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
- `scripts/model/eirene_invariants_testing.py` — 5,000 random parameter sets
  checked for probability bounds, monotonicity, and edge cases.
- `scripts/model/eirene_v27_invariants_testing.py` — invariant and
  edge-case suite for the v27.0 cost-field engine.

Historical backtest of the v27.0 cost-field engine on 1946–2014
(train 1946–1989 / test 1990–2014):

| Threshold | Test AUC | Brier | Positives (test) |
|---|---|---|---|
| T0 → T1+ | 0.63 | 0.0228 | 622 |
| T0 → T4+ | 0.86 | 0.0013 | 98 |
| T0 → T5 | **0.94** | 0.0002 | 62 |
| Any escalation | 0.66 | 0.0227 | 673 |

The engine discriminates high-severity escalation (T0→T4+ and T0→T5)
strongly, even though the cost-field occupancy inputs (B^econ, B^blood,
V_i) are not yet attached and every row therefore runs in the
diagnostic-fallback member. Low-severity onset (T0→T1+) remains the
weakest threshold. These results have not yet been compared against a
regression baseline, and confidence intervals are pending. For full
results see `output/analysis/model_calibration_summary_v27.md`; the
legacy v21 product-form results are in
`output/analysis/model_calibration_summary.md` for comparison
(v21 test AUC was 0.30–0.64, so v27 is a large improvement).

---

## Limitations

- **Cost field runs in diagnostic fallback.** The v27.0 cost-field engine
  (`scripts/model/eirene_lib_v27.py`) is implemented and backtested, but the
  cost-field occupancy inputs (B^econ, B^blood, V_i) have no attached data
  source, so every row currently resolves to the diagnostic-fallback member.
  See `docs/COVERAGE_MATRIX.md` for per-variable coverage. The legacy v21
  product-form implementation (`eirene_lib.py`, `backtest_eirene.py`) is
  retained for comparison.
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
  title={Unified Equation of Interstate War (Directed-Dyad Variant) v27.0},
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

Code: **MIT** (see `LICENSE`).

Data: each source dataset is governed by its own license. The raw source files
are not redistributed in this repository; users must download them directly
from the providers and comply with the respective terms. See
`DATA_PROVENANCE.md` for details.

---

## Contact

Author: Andrew Fuller  
Repository URL: to be added once the public GitHub repo is set up.
