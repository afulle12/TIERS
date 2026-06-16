# Data provenance and attribution

This project integrates data from several third-party sources. Each source has
its own license and attribution requirements. **Users of derived outputs are
responsible for complying with the licensing terms of each source dataset.**

| Source | Version | Coverage | License | Citation |
|---|---|---|---|---|
| MIDB 5.0 (Correlates of War) | 5.0 | 1816-2014 | Research use; COW data-use agreement | Gibler, D. M., & Miller, S. V. (2021). *International Conflict Logic of Unexpected Returns*. |
| MIDA / MIDIP / MIDI | 5.0 | 1816-2014 | Research use | Gibler & Miller (2021). |
| UCDP Dyadic | v26.1 | 1946-onward | CC-BY 4.0 | Davies, S., Pettersson, T., Sollenberg, M., & Öberg, M. (2025). *Organized violence 1989–2024 and the return of armed conflict*. |
| UCDP/PRIO Armed Conflict | v26.1 | 1946-onward | CC-BY 4.0 | Davies et al. (2025); UCDP/PRIO ACD Dataset Codebook. |
| EUSANCT | 2022 | 1989-2015 | Research use | Hufbauer, G., Jung, E., Moran, T., & Oldenski, L. (2022). *The EUSANCT Dataset*. Peterson Institute. |
| CShapes | 2.0 | 1946-onward | CC-BY 4.0 | Weidmann, N. B., Rød, J. K., & Ketterer, L. (2024). *Introducing the CShapes 2.0 dataset*. |
| V-Dem | v16 (CY Core) | 1789-2024 | CC-BY 4.0 | Coppedge, M. et al. (2025). *V-Dem [Country-Year/Country-Date] Dataset v16*. |
| NMC (COW National Material Capabilities) | v7.0 abridged | 1816-2022 | Research use | Singer, J. D., Bremer, S. A., & Stuckey, J. (1972); updated. |
| ATOP | 3.0 | 1815-onward | Research use | Leeds, B. A., Long, A. G., & Mitchell, S. M. (2000). *Alliance Treaty Obligations and Provisions*. |

## Tier definitions and source mapping

| Tier | Definition | Sources used |
|---|---|---|
| T1 — Diplomatic Crisis | Formal friction: protests, recalls, ultimatums, UN votes, coercive threats | MIDB (hostlev=2 threats + hostlev=1 diplomatic originators, 1900–2014) + EUSANCT (threat_dyad=1, 1989–2015) |
| T2 — Economic Coercion | Active sanctions, trade restrictions, financial exclusion | MIDB + EUSANCT (dyadic sanctions, 1989–2015) |
| T3 — Proxy/Indirect Military | Sustained, selective material support to j's adversaries, directed at j | UCDP Dyadic v26.1, type_of_conflict==4 (internationalized internal) |
| T4 — Limited Direct Military | Open, attributed exchange of fire between i and j forces | MIDB (hostlev≥3, militarized action) |
| T5 — Strategic War | Nationwide / multi-front warfare, sustained campaigns | MIDB (highest hostlev/fatality thresholds) |
| T0 — Peace | Inferred: no T1–T5 event in the dyad-year | Inverse of the above; inferred by the build pipeline |

## Derived data

- `data/processed/conflict_dyads.csv` — T1/T2/T4/T5 directed dyad-years
- `data/processed/conflict_dyads_eus.csv` — T2 events extracted from EUSANCT
- `data/processed/conflict_dyads_combined.csv` — combined T1–T5 source
- `data/processed/conflict_dyads_full.csv` (+ .parquet) — T0–T5 full grid,
  with T0 inferred by complement. Largest file (~390 MB CSV).
- `data/processed/dyads_with_features.csv` (+ .parquet) — full grid plus
  V-Dem (N_pub), NMC (CINC, dP, C_T), ATOP (alliance depth) features.
- `data/processed/countries_by_year.csv` — CShapes-derived per-year country lists
- `data/processed/conflict_tiers.csv` — tier reference table

## Adding a new source

When integrating a new dataset, add a row to the table above and a brief
description of the tier(s) it informs in the `Tier definitions and source
mapping` section. Update `scripts/build/` with the corresponding builder and
ensure the data file is placed in `data/raw/` (or referenced from a
download-on-demand location).
