# WarModel

A directed-dyad stochastic-game model of interstate conflict escalation,
persistence, and de-escalation. Combines conflict datasets (MIDB, UCDP, EUSANCT,
CShapes, V-Dem, COW NMC, ATOP) into a unified directed-dyad-year table, then
estimates tier-transition risk and validates a closed-form probability model
against invariants and historical data.

**Current model: v27.0** (T6 collapsed, WMD reformed as Shock_k severity
modulator, empirical priors from v26.1 transition matrix, EUSANCT threats
added to T1, T4 dual-population characterised). See
`docs/models/Unified Equation of Interstate War (Directed-Dyad -5.md` for the
full specification.

## Goal: operational early-warning / scoring tool

This project is being developed as a **live early-warning and scoring system**
for current interstate dyads, not just a historical backtest. The model is
designed to emit a per-directed-dyad probability distribution over next-period
tier transitions, plus a coverage vector indicating how much of the machinery
was actually fed (the graceful-degradation architecture from §1.9 of the
specification).

## Directory layout

```
WarModel/
├── README.md                         Project overview & quickstart
├── LICENSE                           MIT license + third-party data notes
├── pyproject.toml                    Package metadata, deps, tool config
├── requirements.txt                  Pinned runtime dependencies
├── CHANGELOG.md                      Version history (spec + code)
├── CITATION.cff                      Citation metadata
├── DATA_PROVENANCE.md                Source-by-source licensing & attribution
├── data/
│   ├── raw/                          Source datasets (read-only inputs)
│   │   ├── CShapes-2.0.csv           GWN name registry, 1946-onward
│   │   ├── Dyadic_v26_1.csv          UCDP Dyadic v26.1
│   │   ├── UcdpPrioConflict_v26_1.csv UCDP/PRIO Armed Conflict dataset
│   │   ├── EUSANCT_Dataset_Dyadic.xls EUSANCT sanctions dyads
│   │   ├── V-Dem-CY-Core-v16.csv     Democracy indices
│   │   ├── NMC-70-abridged.csv       COW National Material Capabilities v7
│   │   ├── atop3_0ddyr.csv           ATOP 3.0 alliance data
│   │   ├── T{1,3}_directed_v*        Intermediate T1/T3 files
│   │   └── MID-5-Data-and-Supporting-Materials/  (MIDB, MIDA, MIDIP, MIDI)
│   └── processed/                    Generated datasets (regenerable)
│       ├── conflict_dyads.csv        T1/T2/T4/T5 directed dyad-years
│       ├── conflict_dyads_eus.csv    T2 events extracted from EUSANCT
│       ├── conflict_dyads_combined.csv  conflict_dyads + EUSANCT T2
│       ├── conflict_dyads_full.csv   T0-T5 (with inferred T0 peace years)
│       ├── conflict_dyads_full.parquet  same as above, parquet form
│       ├── dyads_with_features.csv   Full grid + V-Dem/NMC/ATOP features
│       ├── dyads_with_features.parquet  same as above, parquet form
│       ├── countries_by_year.csv     year -> country list (CShapes derived)
│       └── conflict_tiers.csv        tier reference table
├── scripts/
│   ├── build/                        Data-pipeline builders
│   │   ├── build_t1_dyads.py         MIDB + MIDIP -> T1 dyad rows
│   │   ├── build_t3_dyads.py         UCDP -> T3 directed dyads
│   │   ├── build_combined_dyads.py   MIDB + T3 -> combined
│   │   ├── integrate_eusanct.py      EUSANCT -> T2 rows + combined
│   │   ├── build_t0_dyads.py         combined -> full (T0-T5)
│   │   ├── build_features.py         Attach V-Dem/NMC/ATOP features
│   │   ├── refresh_country_registry.py  Normalize country names
│   │   └── country_names.py          Shared name-normalization utility
│   ├── analysis/                     Analyses on the processed datasets
│   │   ├── analyze_conflict_dyads.py
│   │   ├── tier_transition_risk.py
│   │   ├── tier_transition_risk_full.py
│   │   ├── severity_over_time_fullycovered.py
│   │   ├── t1_validation.py
│   │   ├── v26_tiers_overview.py
│   │   ├── v26_tier_following.py
│   │   └── v26_tier_following_filtered.py
│   ├── model/                        Theoretical dyadic war model
│   │   ├── war_model.py              Self-contained implementation
│   │   ├── war_model_lib.py          Importable library
│   │   ├── backtest_war_model.py     Backtest (Path 1) on T0-T5 dataset
│   │   ├── testModelv10.py           Invariants / sensitivity / MC tests
│   │   └── warModelInvarientsTesting.py  Standalone invariant test
│   └── data/                         Data utilities
│       └── pythonTransformFiles.py   CShapes -> year->country list
├── output/                           Generated outputs (not versioned)
│   ├── analysis/                     CSVs, tables
│   └── charts/                       PNG plots
├── docs/
│   ├── models/                       Current model specifications
│   ├── model_drafts_archive/         Archived older model drafts
│   ├── reports/                      Generated reports (markdown, HTML)
│   │   ├── conflict_dyads_report.md
│   │   └── calc.html                 UIW v25.0 calculator
│   └── invariant_logs/               Test-run logs
├── tests/                            (planned) pytest test suite
└── tmp/                              Scratch / one-off scripts
```

## Data pipeline

```
[data/raw/*] -- build_t1_dyads ----\                                    [conflict_dyads.csv]
                                   +-- build_combined_dyads -----------/
[data/raw/Dyadic_v26_1.csv] -- build_t3_dyads --------------------------/

[conflict_dyads.csv] -- integrate_eusanct -- [conflict_dyads_eus.csv]
                                              [conflict_dyads_combined.csv]

[conflict_dyads_combined.csv] -- build_t0_dyads -- [conflict_dyads_full.csv/parquet]
                                                  [output/analysis/t0_coverage.csv]

[conflict_dyads_full.csv] -- build_features -- [dyads_with_features.csv/parquet]
                                                (V-Dem N_pub, NMC dP/C_T/CINC, ATOP alliance depth)

[conflict_dyads.csv]        -- analyze_conflict_dyads --> [output/analysis/*, output/charts/*]
[conflict_dyads.csv]        -- tier_transition_risk --->  [output/analysis/tier_*]
[conflict_dyads_full.csv]   -- tier_transition_risk_full -> [output/analysis/tier_*_full]
[dyads_with_features.csv]   -- backtest_war_model ---->  [output/analysis/model_backtest_*]
                                                       [output/charts/model_backtest_*.png]
```

## Tier scheme

| Tier | Label | Meaning |
|---|---|---|
| T0 | No Conflict/Peace | Inferred (no T1-T5 event in dyad-year) |
| T1 | Diplomatic Crisis | MIDB threats + diplomatic originators + EUSANCT threat_dyad |
| T2 | Economic Coercion | Active sanctions, trade restrictions; includes EUSANCT |
| T3 | Proxy/Indirect Military | UCDP internationalized internal, supporter->host |
| T4 | Limited Direct Military | Open, attributed exchange of fire between i and j |
| T5 | Strategic War | Multi-front warfare; reach-gated by contiguity or Cap |

## Quickstart

```bash
# 1. Set up environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Build the processed datasets (run after data/raw/* is in place)
python scripts/build/build_t1_dyads.py
python scripts/build/build_t3_dyads.py
python scripts/build/build_combined_dyads.py
python scripts/build/integrate_eusanct.py
python scripts/build/build_t0_dyads.py
python scripts/build/build_features.py

# 3. Analyse
python scripts/analysis/analyze_conflict_dyads.py
python scripts/analysis/tier_transition_risk.py
python scripts/analysis/tier_transition_risk_full.py

# 4. Backtest the model against historical data
python scripts/model/backtest_war_model.py

# 5. Model tests
python scripts/model/testModelv10.py
python scripts/model/warModelInvarientsTesting.py
```

## Dependencies

- Python 3.10+
- `pandas`, `numpy`, `scipy`, `scikit-learn` — core data + numerics
- `matplotlib`, `networkx` — visualisation + graph analytics
- `pyarrow` — Parquet I/O for processed datasets

Dev / test extras: `pytest`, `pytest-cov`, `ruff`.

## Model specifications

- **Current:** v27.0 — `docs/models/Unified Equation of Interstate War (Directed-Dyad -5.md`
- **Archive:** `docs/model_drafts_archive/` — v1 through v20 retained for reference

## Notes

- `data/processed/conflict_dyads_full.csv` and `dyads_with_features.csv` are
  large (~390 MB / ~450 MB). Use the `.parquet` form for repeated reads.
- Large processed CSVs are gitignored; rebuild via the pipeline above.
- All scripts use `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`
  to resolve the project root from any subdirectory.

## License

Code: MIT (see `LICENSE`).
Data: each source dataset has its own license — see `DATA_PROVENANCE.md` and
comply with attribution requirements when redistributing derived outputs.
