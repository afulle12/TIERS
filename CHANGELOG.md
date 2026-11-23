# Changelog

All notable changes to TIERS are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/) with the spec major version as the
project version.

## [Unreleased] - 2026-11-22 — T3 military assistance from UCDP ESD

### Added
- `scripts/build/build_esd_t3.py`: directed T3 events from UCDP External
  Support Dataset 18.1 (triad-year, 1975–2017). A state's confirmed troops,
  joint operations, weapons, training or funding to a party fighting another
  state's government is a T3 event supporter -> that state. Alleged support,
  support by state elements, non-state supporters, support to a government
  against rebels, and materiel/intelligence/territory-only support are
  excluded. Writes `data/processed/esd_t3_events.csv` (1,772 rows).
- `source_coverage.py`: `UCDP_ESD` source (T3, 1975–2017); T3 partial note
  updated.
- `build_dyad_states.py` reads the ESD events as source `UCDP_ESD`;
  `build_pipeline.py` runs `build_esd_t3.py` before it.
- `tests/test_build_esd_t3.py` (8 rule tests) and an ESD contract check.

### Effect
- Shared T3 pair-years 1946–2014: 16 -> 851.
- Test window (1990–2014): T3 -> T4+ becomes evaluable (2 -> 24 positives,
  cumulative AUC 0.8482); T2 -> T3+ 42 -> 45 positives (AUC 0.6884).
  Headline v28 AUCs move by at most 0.003; LogReg(trade+struct) escalation
  AUC 0.7398 -> 0.7587.

## [Unreleased] - 2026-11-22 — T3 direction fix

### Fixed
- `build_dyad_states.py`: UCDP T3 events now keep only supporters of
  `side_b` (the side fighting the host government). Previously every
  secondary supporter in an internationalised internal conflict, including the
  3,115 of 3,305 rows that sent troops to *help* the host government, was a
  hostile supporter -> host T3 event (e.g. USA -> Afghanistan 2010,
  UK -> Iraq 2008, France -> Mali 2014, Cuba -> Angola 1980). Dropped rows
  are logged in `dyad_states_dropped.csv` as `T3 support to host government`.
- `tests/test_data_contracts.py`: every `UCDP_T3` event must trace to a
  `side_b` supporter row.

### Effect
- Shared T3 pair-years 1946–2014: 1,081 -> 16.
- Test window (1990–2014): T2 -> T3+ positives 57 -> 42 (AUC 0.6229 -> 0.7191);
  T3 -> T4+ positives 11 -> 2. Headline AUCs move by at most 0.004
  (onset-force 0.8246 -> 0.8218 on 266 positives).

## [Unreleased] - 2026-11 — Repair phase 2 (data): complete data & T1 union rebuild

### Added
- `scripts/build/state_system.py`: state-system membership by year (COW members
  from NMC that have a CShapes unit), with both COW and Gleditsch-Ward codes.
- `scripts/build/source_coverage.py` & `data/processed/source_coverage.csv`:
  declares tier observability by year and marks pre-1989 unobserved T2 sanctions
  with `unobserved_tiers` bitmask so evaluation withholds transitions whose label
  could change if missing tiers were observed.
- `scripts/build/build_mid_dyads.py`: derives every MID-sourced event from the
  raw MID 5.0 participant file. Direction and tier come from the acting state's
  own hostility level; threats and displays are T1, use of force T4, war T5.
  In coalition disputes a force-level tier needs evidence the force was aimed
  at that target. Replaces the inherited MID rows, whose initiator and target
  were reversed, and retires `build_t1_dyads.py`.
- `scripts/build/build_t1_sources.py`: builds the Section 2.8 T1 union from
  `EUSANCT_THREAT` (`threat_dyad==1`, `sanction_dyad!=1`), `TIES` v4.0 (with
  `TIESCorrection.txt` errata, non-imposed year spans, and EEC/EU `1000`
  expansion), `ICB` v16 (crisis dyad-years with `TRIGENT`/`SOUTHV` direction
  recovery, filtered to pair-years `< T3`), and `DIPREP` (Pardee DRD `Focus==3`
  recalls, withdrawals, severance, and expulsions).
- `scripts/build/build_dyad_states.py`: one row per ordered pair of existing
  states per year, resolved to the highest recorded tier and shared by both
  directions (`uiw_tier`), with `directed_tier`, `t1_basis`, `unobserved_tiers`,
  and Sechser MCT v0.9 validation check (`106/117` in-window dyad-years and
  `92/103` episodes at T1+).
- `scripts/build/build_pipeline.py`: single command to rebuild the full Phase 2
  table chain and run `tests/test_data_contracts.py`.
- `tests/test_build_mid_dyads.py`, `tests/test_build_t1_sources.py`,
  `tests/test_data_contracts.py` (53 tests total passing; obsolete trade xfail
  removed; rivalry mirroring, coverage bitmask, and T1 union checks added).
- `evaluation.dyad_year_codes` / `mean_over_directions`: all backtests and
  baselines count each dyad-year once using the mean of directed forecasts and
  respect `unobserved_tiers`.

### Changed
- `integrate_eusanct.py`: T2 filters dyadic `sanction_dyad == 1` (fixing 121
  premature threat-only US/EU rows), resolves COW `ccodecow` via `state_system`
  (preserving Yemen `679`, Germany `255`, Myanmar `775`, Sri Lanka `780`, Nepal
  `790`, Fiji `950`, Barbados `53`), and exports `eusanct_threat_events.csv`.
- `build_rivalry.py` & `tiers_lib_v27.py`: rivalry is now directed (`ActorState.rivalry`:
  decayed history of the other side's militarised actions using events from 1900).
- `build_trade_interdependence.py`: builds both directions from one source and
  enforces symmetric `trade_surface_norm_ab` and `mutual_trade_dependence_ab`.
- `build_features.py`, `build_features_v27.py`, `build_features_v28.py`: no
  silent deduplication, skip-if-exists, or redundant CSV mirrors.
- `tiers_lib_v27.py`: reconciliation ties average both directional allocations
  within `1e-12` instead of breaking arbitrarily on floating-point noise.

### Effect
- Directed dyad-years 1946–2014: 2,101,408 -> 1,388,704 (non-existent states
  removed). Capability shares summing to one: 62.7% -> 100% of rows; trade and
  rivalry symmetry invariants pass across all 1,388,704 rows.
- T1 pair-years (1946–2014): expanded to 4,565 via Section 2.8 union (`TIES`:
  1,533 alone; `EUSANCT_THREAT`: 922 alone; `DIPREP`: 826 alone; `MID`: 740
  alone; `ICB`: 128 alone; plus overlaps).
- Test-window (1990–2014) onset from peace, per dyad-year: 3,027 any-onset, 258
  force-onset, 14 war-onset (suppressed `< 20`). TIERS v28 force-onset AUC
  0.8246 vs LogReg(trade+struct) 0.9113; `T1->T2` now has 369 test positives
  (up from 19 previously).


## [Unreleased] - 2026-07 — v27.0 engine implemented and backtested

### Added
- `scripts/model/tiers_lib_v27.py`: the v27.0 cost-field engine —
  status-quo-biased direction stage, Capability/Reach gate on T5,
  Attribution×Duration T3→T4 factor, nested-member resolution with
  diagnostic fallback when cost-field occupancy inputs are absent.
- `scripts/model/backtest_tiers_v27.py`: v27 backtest mirroring the v21
  backtest (same 1946–1989 / 1990–2014 split) for direct comparison.
  Test-set AUC: T0→T5 = 0.94, T0→T4+ = 0.86, T0→T1+ = 0.63
  (v21: 0.64 / 0.55 / 0.30). Results in
  `output/analysis/model_calibration_summary_v27.md`.
- `scripts/model/tiers_score_v27.py`: forward-scores live dyads for a
  target year; output in `output/forecasts/`.
- `scripts/model/tiers_v27_invariants_testing.py`: invariant suite for
  the v27 engine.
- `scripts/model/baseline_tiers_v27.py`: baseline comparison against
  logistic-regression and random-forest classifiers on the same v27 structural
  feature grid and train/test split.
- `scripts/build/build_contiguity.py` (CShapes contiguity/distance/FMA),
  `scripts/build/build_rivalry.py` (MIDB recency-decayed Omega),
  `scripts/build/build_features_v27.py` (v27 features grid parquet).
- `docs/COVERAGE_MATRIX.md`: per-variable observability (empirical /
  defaulted / absent) and active-member resolution for the v27 run.
- `scripts/analysis/t0_to_t1_cohort.py`,
  `scripts/analysis/un_voting_dyad_alignment.py`.

### Changed
- Project renamed to **TIERS** (Tiered Interstate
  Escalation Risk System) to reflect the model's symmetric focus on
  escalation, persistence, and de-escalation across the six-tier taxonomy.
- Fixed v27 dyad-level reconciliation to apply the spec §3.6 min-rule for
  de-escalation mass and residual persistence. Refreshed the v27 backtest:
  test AUC is T0→T5 = 0.9380, T0→T4+ = 0.8550, T0→T1+ = 0.6295, and
  Any escalation = 0.6569.
- Renamed model scripts/modules to `tiers_*` and updated imports, README
  commands, and package metadata.
- Made generated Wikipedia validation reports use repo-relative paths instead
  of local absolute paths.
- Added baseline comparison results. The diagnostic-fallback engine remains
  strongest on T0→T5 (0.9380 AUC), but simple baselines outperform it on
  T0→T1+, T0→T4+, and Any escalation until cost-field inputs are attached.

### Known gaps carried forward
- Cost-field occupancy inputs (B^econ, B^blood, V_i) unattached — engine
  runs in diagnostic-fallback member on every row.
- Bootstrap confidence intervals are still pending.
- Path 2 (contagion) still not scored in the backtest.

## [Unreleased] - 2026-06-20 — Pipeline rewrite: Ollama, 3-LLM-pass, explanation column

### Changed
- **Wikipedia pipeline no longer downloads the Wiki snapshot.** The
  user provides the parquet export themselves; the filter auto-
  discovers the most recently modified `data/raw/structured-wikipedia/
  <name>/data/*.parquet` directory.
- **Pipeline is now 7 stages, 3 LLM passes** (was 9/10 in the legacy
  design). Stage 1 (acquire) removed; classifier/extractor/correlate
  merged into a single combined extraction stage. See
  `docs/wiki_pipeline.md` for the current stage table.
- **Wikipedia pipeline now uses Ollama** (was LM Studio). All scripts
  read `OLLAMA_*` env vars with `LMSTUDIO_*` as fallback aliases.
- **Stage 2 filter** dropped the regex tier-keyword gate and
  re-ordered: DuckDB country-only (no keyword AND) → Python bilateral.
  The LLM 0/1 filter (stage 5) is now the precision check.
- **Stage 5** is now a batched LLM 0/1 filter (3 articles per prompt),
  not a per-article classifier. Replaces the old regex gate and the
  old per-article classifier.
- **Stage 6** is a new LLM tier+explanation pass (1 article per prompt,
  very short output, max 20 words). The detailed event extractor moved
  to stage 7.
- All 4 LLM scripts now default to `nvidia/nemotron-3-nano-4b`
  (was qwen3.5-9B on LM Studio, which serialized internally and
  deadlocked at n_parallel>1).
- Aggregator output (`data/processed/conflict_dyads_wikipedia.csv`)
  gains an `explanation` column. New intermediate
  `tmp/wiki_t123_events.csv` is the per-event join of tier+explanation
  with extracted event fields.

### Added
- New `scripts/build/wiki_extract_llm_t123_filter.py`: batched 0/1
  filter (3 articles per prompt, max_tokens=80). Replaces the old
  per-article classifier.
- New `scripts/build/wiki_extract_llm_t123_tier.py`: 1-article-per-
  prompt tier+explanation call (max_tokens=120, no CoT).
- New `scripts/build/wiki_correlate_t123.py`: joins tier+explanation
  with extracted events on `article_id`.
- New `scripts/build/prompts/wiki_t123_filter_v1.txt`: prompt with a
  rich conflict-keyword vocabulary per tier (T1–T5) as hints.
- New `scripts/build/prompts/wiki_t123_tier_v1.txt`: prompt asking
  for tier + 1-sentence explanation (max 20 words).
- New `scripts/build/_smoke_test_new_pipeline.py`: smoke test that
  runs each LLM stage on a tiny subset and finds a working
  `OLLAMA_N_PARALLEL` via a 8 → 7 → 6 → 5 → 4 ladder.
- New `scripts/build/_run_full_pipeline.py`: one-script end-to-end
  runner.
- New helper `call_chat_batched()` in `wiki_llm_helpers.py` for
  JSON-array responses.

### Removed
- The 3a/3b/3c funnel's 3c regex tier-keyword gate is gone. The LLM
  tier pass replaces it.
- The old per-article classifier (stage 6 in v1) is replaced by the
  batched 0/1 filter. The old `wiki_extract_llm_t123_classifier.py`
  is preserved on disk but is no longer wired into the orchestrator.

## [Unreleased] - 2026-06-16 — Renamed from WarModel

### Added — Wikipedia tier extraction (v27.0-aligned, 1900-2025)
- New 9-stage Wikipedia pipeline (`scripts/build/wiki_pipeline.py`)
  extracts T1–T5 directed-dyad events from the 35 GB
  `wikimedia/structured-wikipedia` enwiki snapshot and writes
  `data/processed/conflict_dyads_wikipedia.csv` aligned to the
  v27.0 spec scheme (T1=1, T2=2, T3=3, T4=4, T5=5).
- New canonical country list (`data/processed/wiki_country_canonical.csv`,
  289 canonical rows, 775 aliases, 180 modern sovereigns) built from
  CShapes + wiki_gwn_map + a hand-curated alias dict.
- New T4/T5 allowlist (`data/processed/wiki_t5_title_allowlist.csv`,
  ~700 strategic-war titles) for hand-curated T5 promotion.
- New prompts:
  - `wiki_t123_classifier_v1.txt` (cheap yes/no classifier)
  - `wiki_t123_v2.txt` (v27.0-aligned detailed extractor)
  - `wiki_t45_ambiguous_v1.txt` and `_v2.txt` (T4→T5 confirm)
- New shared LLM helper (`scripts/build/wiki_llm_helpers.py`) fixes
  four LM Studio bug patterns: (1) `response_format: json_object`
  HTTP-400 rejection; (2) `max_tokens` truncation from chain-of-thought
  reasoning; (3) reasoning-content trap (JSON in `reasoning_content`
  when `content` is empty); (4) `<think>...</think>` tag leakage.
  Per-call timeout, exponential-backoff retry, auto per-article
  diagnostic logging, and append-mode file output.
- Stage 9 (`wiki_validate.py`) emits per-year P/R/F1, tier-crosswalk
  table, per-source row counts, GWN-resolution rate, top-20 dyads
  per tier, year-over-year transition distribution, and a
  `wiki_mismatch_table.csv` long-form mismatch analysis
  (18,948 dyad-year rows in the current run).
- New docs: `docs/wiki_pipeline.md` (full stage table) and
  `docs/wiki_pipeline_work_summary.md` (work summary with
  recommendations).

### Changed — T1/T2/T3 LLM fixes
- All three LLM scripts now default to `n_parallel=1`. qwen3.5-9B
  on this GPU serializes internally; `n_parallel>1` causes LM Studio
  to deadlock. The 9B model with chain-of-thought reasoning fully
  saturates the GPU with a single worker.
- `max_tokens` raised to 6000 in the T123 detailed extractor (was
  1024 / 1500), 4000 in the T123 classifier (was 1500), and 2500
  in the T45 ambiguous confirm pass. The model uses ~99% of the
  previous max_tokens for reasoning, truncating the actual JSON
  output.
- `max_tokens` further raised to **8000** in the T123 classifier
  after an empirical length-vs-failure diagnostic (10 percentile
  articles × 1 call each) showed that ~15% of articles consume
  4000+ tokens of chain-of-thought reasoning; 8000 covers all
  observed cases. The model's CoT length is non-deterministic even
  with `temperature=0` and `seed=42` — the same article can use
  780 or 8000+ tokens on different runs. 8000 + the helper's 3
  retries (which the existing `no_json_in_response` / `json_decode`
  retry path already covers) gives near-zero failure rate.
- T123 classifier now uses **line-buffered** JSONL output
  (`buffering=1`) so a SIGTERM or crash loses at most the
  in-flight line, not the default 4-8 KB block-buffered amount
  (which could lose dozens of classifications).
- `log_failure` in `wiki_llm_helpers.py` now writes
  `finish_reason` into the per-article diagnostic JSON, so future
  truncation-induced failures are diagnosable from the debug
  payload alone.
- All three LLM scripts now use append-mode file output. Re-runs
  no longer destroy prior results; the script extends the
  existing JSONL.
- One-line progress meter with percentage, bar, kept/rejected/
  failed counts, rate, and ETA, updated every article.

### Changed — Tier scale (T-scale) drift fixed
- All Wikipedia output uses the **v27.0 spec scheme** (T1=1, T2=2,
  T3=3, T4=4, T5=5) and **v27.0 labels** (`T2-Economic Coercion`,
  `T3-Proxy/Indirect Military`). The legacy MIDB-based
  `conflict_dyads_full.csv` uses a different scheme (T2=3, T3=3
  collide) and is preserved for comparison; the validation report
  includes a 1-to-1 tier-crosswalk table.
- Filter regex set tightened: T1 now includes UN votes, demarches,
  and travel-ban announcements; T2 includes asset freezes, SWIFT
  disconnections, weapons-embargo announcements; T3 includes
  materiel/drone/rocket transfers and foreign-fighter pipelines.

### Verified smoke tests
- T45 ambiguous confirm: 1/1 article parsed (was 0/5).
- T123 detailed extractor: 1/1 article extracted (Ecuador-Mexico
  2024 diplomatic severance, both directions).
- T123 classifier: working with auto per-article diagnostic write
  to `tmp/wiki_t123_classifier_debug/<article_id>.json`.

### Changed
- Project renamed from **WarModel** as part of the transition to **TIERS**.
  The name better reflects the model's scope — escalation *and* de-escalation
  dynamics — and is intended as a neutral, scholarly label.
- `pyproject.toml` package metadata and keywords refreshed.
- `CITATION.cff` title and message updated.
- `README.md` and `CHANGELOG.md` updated throughout.
- Renamed script files:
  - `scripts/model/war_model.py` → `tiers_model.py`
  - `scripts/model/war_model_lib.py` → `tiers_lib.py`
  - `scripts/model/backtest_war_model.py` → `backtest_tiers.py`
  - `scripts/model/warModelInvarientsTesting.py` → `tiers_invariants_testing.py`
    (also corrects the `Invarients` → `Invariants` typo)

## [27.0.0] - 2026-06 — v27.0 spec; infrastructure + operational scaffolding

### Added — Infrastructure
- Git repository initialized with `main` branch and project-local config.
- `.gitignore` excluding generated processed CSVs, `output/`, `tmp/`,
  Python caches, IDE configs, secrets, and lock files.
- `pyproject.toml` with package metadata, pinned dependencies, tool config
  (pytest, ruff), and console-script entry points.
- `requirements.txt` mirroring the runtime dependency set.
- `LICENSE` (MIT) with explicit notes on third-party data licensing.
- `CHANGELOG.md`, `CITATION.cff`, `DATA_PROVENANCE.md`.
- `output/.gitkeep` and `tmp/.gitkeep` to preserve empty dirs in version control.

### Updated — Public-facing docs and attribution
- Rewrote `README.md` for a broad audience: clear executive summary,
  installation steps, data download links, tier taxonomy, core equation,
  validation results, limitations, and citation info.
- Set author attribution to **Andrew Fuller** across `README.md`,
  `CITATION.cff`, `pyproject.toml`, and `LICENSE`.
- Removed placeholder GitHub URLs from `pyproject.toml` and `CITATION.cff`
  until the public repo is created.

### Changed — Raw data handling
- `data/raw/` is now excluded from version control.
- Upstream datasets (COW MIDB/NMC, UCDP, EUSANCT, CShapes, V-Dem, ATOP)
  must be downloaded directly from their providers before running the
  pipeline. Download links and licensing notes are in `README.md` and
  `DATA_PROVENANCE.md`.

### Added — Acknowledgments and history rewrite
- New `Acknowledgments` section in `README.md` disclosing the use of
  large language model tools for code review, refactoring, documentation,
  and infrastructure work.
- `README.md` table of contents updated to include the new section.
- Git history rewritten with `git filter-branch` to fully purge any
  raw data references from the object store. `.git` reduced from
  ~90 MB to ~3 MB. The two-commit structure is preserved; commit SHAs
  have changed.

### Model — v27.0 specification (code still implementing v21-level, tracked in next release)
- T6 (Strategic WMD Employment) **removed** as a separate tier; the ordered
  ladder collapses to T0–T5.
- WMD concept **reformed** as a continuous severity modulator: enters `Shock_k`
  at T5 as a ceiling amplifier; informs `Cap` via `WMD>0 ⇒ Cap≥τ`.
- T1 **supplemented** with EUSANCT threat_dyad=1 rows (1989–2015), extending
  coverage past MIDB's 2014 endpoint.
- **Empirical priors** set from the v26.1 transition matrix (~4.4M dyad-year
  observations): persistence rates, escalation thresholds, de-escalation
  barriers. Several cost-field parameters remain TBD.
- **T4 dual-population** explicitly characterised: short-duration T4
  de-escalates; long-duration T4 locks in via `b_dur·D_k`.

### Backtesting
- `scripts/model/backtest_tiers.py` runs Path 1 (direct initiation) on
  the T0–T5 grid; β calibrated to observed T0→T1+ rate.
- Test-set AUC: T0→T5 = 0.64 (best); T0→T1+ = 0.30 (worst). High-severity
  thresholds predicted meaningfully above chance; low-severity discrimination
  still weak (Path 2 contagion not yet implemented).

### Known gaps (next release priorities)
- **Codebase vs spec drift:** `tiers_lib.py` and `backtest_tiers.py`
  still implement the v21-level two-path product formula. v27.0's
  cost-field engine with status-quo-biased direction stage and
  Capability/Reach gate is not yet coded.
- **Path 2 (contagion) not scored in backtest** — needs `W_sev` (war
  severity) lookup.
- **Empirical defaulting:** ~10 structural parameters (A_div, P_v, R_h, B,
  I_s, E_n, S_p) are set to neutral defaults because no source dataset is
  attached. Calibrated priors cannot be evaluated for these.
- **C_d_opp is a placeholder** (`1 − C_d_sup`); needs real third-party
  alliance opposition lookup.
- **No test framework.** All tests are ad-hoc `__main__` scripts; no
  pytest, no CI.

## [26.x and earlier] - 2024 - 2026

See `docs/models/` for full historical specifications and
`docs/model_drafts_archive/` for archived drafts (v1 through v20). Major
upstream milestones (in brief):

- **v26.0** — Status-quo-biased direction stage; Capability/Reach gate on
  T5; T3-High collapsed into Attribution×Duration escalation factor.
- **v25.1** — IHL-anchored Strategic WMD gate (later removed in v27.0).
- **v25.0** — Graceful-degradation architecture; nested-model family.
- **v24.0** — Cost-field engine; modifier axes; belief term; T3-High tier.
- **v21.0** — Two-path product formula (current code base).
