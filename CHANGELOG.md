# Changelog

All notable changes to WarModel are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/) with the spec major version as the
project version.

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
- `scripts/model/backtest_war_model.py` runs Path 1 (direct initiation) on
  the T0–T5 grid; β calibrated to observed T0→T1+ rate.
- Test-set AUC: T0→T5 = 0.64 (best); T0→T1+ = 0.30 (worst). High-severity
  thresholds predicted meaningfully above chance; low-severity discrimination
  still weak (Path 2 contagion not yet implemented).

### Known gaps (next release priorities)
- **Codebase vs spec drift:** `war_model_lib.py` and `backtest_war_model.py`
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
