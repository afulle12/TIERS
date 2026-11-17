# Phase 0 "Before" Reference

Recorded: 2026-11-16 (before any model or data changes)

## Environment
- Package manager: `uv 0.13.8`
- Python: `3.13.18` (pinned in `.python-version`)
- Virtualenv location: `~/.venvs/tiers` (outside Tresorit synced folder; 57 packages installed, 79 resolved in `uv.lock`, 78 pinned in `requirements.txt`)

## Invariant Suites (all passed unchanged)
- `scripts/model/tiers_invariants_testing.py`: 5000 / 5000 passed (100.00%)
- `scripts/model/tiers_v27_invariants_testing.py`: 9 / 9 passed
- `scripts/model/tiers_v28_invariants_testing.py`: 4 / 4 passed
- `scripts/model/testModelv10.py`: Level 1 invariants passed; Level 4 Spearman `rho = +1.000`

## Backtest (`backtest_tiers_v28.py --sample 200000`)
Input grid: `data/processed/dyads_with_features_v28.parquet` (`2,070,941` dyad-years with next-year tier; CSV and Parquet grids agree on row count and on the transition matrix to within one transition).

### Reproduced 200k run vs README.md
The README's v28 tables (last edited 2026-07-07 12:23) do **not** match the current Parquet grid (rebuilt after the README edit; library versions also updated in the new environment):

| Window | Threshold | README AUC (n_pos) | Reproduced 200k AUC (n_pos) | Jul 7 50k on disk AUC (n_pos) |
|---|---|---:|---:|---:|
| test_1990_2014 | T0->T1+ | 0.5403 (622) | 0.5416 (625) | 0.5315 (155) |
| test_1990_2014 | T0->T4+ | 0.7832 (98) | 0.7883 (102) | 0.7743 (24) |
| test_1990_2014 | T0->T5 | 0.9316 (62) | 0.9229 (55) | 0.9990 (13) |
| test_1990_2014 | Any esc | 0.5745 (673) | 0.5755 (676) | 0.5721 (170) |
| trade_window_1995_2014 | T0->T1+ | 0.5713 (639) | 0.5720 (642) | 0.5570 (159) |
| trade_window_1995_2014 | T0->T4+ | 0.8304 (76) | 0.8335 (80) | 0.8717 (16) |
| trade_window_1995_2014 | T0->T5 | 0.8802 (66) | 0.8785 (62) | 0.8521 (14) |
| trade_window_1995_2014 | Any esc | 0.6000 (686) | 0.6005 (689) | 0.5778 (167) |

Local gitignored outputs preserved under:
- `output/analysis/before_phase1/jul7_on_disk/`
- `output/analysis/before_phase1/reproduced_200k/`
