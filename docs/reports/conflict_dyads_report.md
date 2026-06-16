# Conflict Dyads - Data Analysis Report

Source: `conflict_dyads.csv` (10219 directed dyad-year rows, 1900-2025).

## 1. Dataset overview

| Metric | Value |
|---|---|
| rows | 10219 |
| year_min | 1900 |
| year_max | 2025 |
| unique_years | 126 |
| year_gaps | 0 |
| unique_initiators | 173 |
| unique_targets | 165 |
| unique_dyads | 1664 |
| missing_cells_total | 100022 |
| duplicate_year_init_target_rows | 0 |
| dual_coded_rows_same_year_pair_diff_tier | 2533 |
| self_loops | 0 |

**Columns:** `year, initiator, target, hostlev, uiw_tier, tier_label`

**Tiers present:**

| Tier | Label | Rows |
|---|---|---|
| T1 | T1-Diplomatic Crisis | 1458 |
| T2 | T2-Economic/Display | 791 |
| T3 | T3-Proxy/Indirect Military | 2667 |
| T4 | T4-Limited Military | 2953 |
| T5 | T5-Strategic War | 2350 |

Note: T3 rows are present (proxy/indirect military support, UCDP type-4 conflicts, both-sides-backed).

### T1 derivation

T1 (Diplomatic Crisis) was rebuilt from MIDB 5.0 with an expanded definition:

| Source | Definition | Rows |
|---|---|---|
| **hostlev=2** | Active threat to use force (action codes 1-6 in MIDB codebook) | 215 |
| **hostlev=1 + orig=1** | Participant originated a dispute but did not personally militarise | 1,243 |
| **Total** | | **1,458** |

Previously the pipeline only captured hostlev=2 participants, yielding 46 T1 rows. Adding hostlev=1 conflict originators (states that started a dispute through diplomatic means) increased T1 coverage by 32× and added 782 unique directed dyads.

**Action code → T1 inclusion (MIDB 5.0 Codebook):**

| Action | Hostlev | Description | Included in T1 |
|---|---|---|---|
| 0 | 1 | No militarized action | Only if orig==1 |
| 1-6 | 2 | Threat to use force / blockade / occupy / declare war / CBR / join war | Always |
| 7-12 | 3 | Show of force / alert / mobilization / fortify border / border violation | No (→ T2) |
| 13-19 | 4 | Blockade / occupation / seizure / attack / clash / war declaration / CBR use | No (→ T4) |
| 20-21 | 5 | Begin / join interstate war | No (→ T5) |

The T1 transition row in the T0–T5 grid (n=230 transitions):

| From | T0 | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|---|
| T1 | 91.3% | 3.0% | 0.9% | 0.9% | 3.9% | 0.0% |

Most diplomatic crises end within a year (91.3% → T0). Those that escalate most often go to T4 (limited military, 3.9%). No T1→T5 transitions are observed in the data.

![T1 comparison](../../output/charts/t1_old_vs_new.png)

## 2. Data quality

- **Missing cells:** 100022 (most are T3-specific columns left null on MIDB rows, e.g. `attribution`, `side_backed`).
- **Duplicate `(year, initiator, target, source, tier_label)` rows:** 0.
- **Dual-coded (year, initiator, target) pairs with different tier_labels** (e.g. direct + proxy in same year):** 2533.
- **Self-loops (initiator == target):** 0.
- **Year gaps:** 0 year(s) missing across the range 1900-2025 (i.e. coverage is contiguous).

### hostlev vs uiw_tier

- **Offset distribution (hostlev - uiw_tier):** {0: 9213, 1: 1006}.
- Rows with `hostlev == uiw_tier + 1`: 1006 (all T1 and T2 rows).
- Rows with `hostlev == uiw_tier`: 9213 (all T4 and T5 rows).

| hostlev \\ uiw_tier | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| 1 | 1243 | 0 | 0 | 0 | 0 |
| 2 | 215 | 0 | 0 | 0 | 0 |
| 3 | 0 | 791 | 2667 | 0 | 0 |
| 4 | 0 | 0 | 0 | 2953 | 0 |
| 5 | 0 | 0 | 0 | 0 | 2350 |

**Interpretation:** `hostlev` is a 1-5 hostility scale where `1` = "no militarized action" (present here only for T1 diplomatic-originator rows added by the MIDB_T1 build). `uiw_tier` uses the same 1-5 ladder with `3` = T3 proxy/indirect military. Concretely: T1 -> hostlev 1 or 2 / uiw_tier 1, T2 -> hostlev 3 / uiw_tier 2, T3 -> hostlev 3 / uiw_tier 3, T4 -> hostlev 4 / uiw_tier 4, T5 -> hostlev 5 / uiw_tier 5. `tier_label` is the human-readable source of truth and the recommended column for downstream analysis.

## 3. Temporal trends

- **Total events:** 10219.
- **Years with at least one T5 event:** 83 / 126.
- **Years with at least one T3 event:** 70 / 126.
- **Longest T5 streak (consecutive years with >=1 T5):** 25 years.
- **Peak year:** 1940 with 257 events.

### Events per decade

| Decade | T1 | T2 | T3 | T4 | T5 | Total | T4+T5 share |
|---|---|---|---|---|---|---|---|
| 1900s | 36 | 21 | 0 | 55 | 20 | 132 | 56.8% |
| 1910s | 81 | 32 | 0 | 157 | 202 | 472 | 76.1% |
| 1920s | 65 | 28 | 0 | 76 | 11 | 180 | 48.3% |
| 1930s | 57 | 27 | 0 | 78 | 204 | 366 | 77.0% |
| 1940s | 126 | 21 | 1 | 205 | 1129 | 1482 | 90.0% |
| 1950s | 101 | 39 | 7 | 267 | 137 | 551 | 73.3% |
| 1960s | 163 | 39 | 45 | 477 | 169 | 893 | 72.3% |
| 1970s | 102 | 65 | 67 | 326 | 183 | 743 | 68.5% |
| 1980s | 231 | 89 | 72 | 443 | 20 | 855 | 54.2% |
| 1990s | 175 | 134 | 88 | 411 | 176 | 984 | 59.7% |
| 2000s | 219 | 187 | 472 | 243 | 99 | 1220 | 28.0% |
| 2010s | 102 | 109 | 1128 | 215 | 0 | 1554 | 13.8% |
| 2020s | 0 | 0 | 787 | 0 | 0 | 787 | 0.0% |

![Severity over time](../../output/charts/severity_over_time.png)

![Events per decade](../../output/charts/events_per_decade.png)

**Observations:**
- The 1940s dominate (WWII) with 1,129 T5 events - more than the next three decades combined.
- The 1910s and 1930s show two earlier T5 surges (WWI and the lead-up to WWII).
- T5 frequency collapses after 1990, while T2 (economic/display) and T4 (limited military) activity continues.
- Post-2000, the dataset contains **no T5 events** at all (2000s: 99, 2010s partial through 2014: 0).
- T3 (proxy/indirect military) events are UCDP-sourced and concentrate from 2013 onward, peaking 2022-2023.

## 4. Network findings

- **Nodes (countries):** 177.
- **Directed dyads:** 1664.
- **Total directed events:** 10219.
- **Reciprocal pairs (both directions present):** 413.

### Top 10 actors by total severity initiated

| Country | Events init. | Severity init. | Max tier init. | Events target. | Severity target. | Offense-Defense |
|---|---|---|---|---|---|---|
| Russia (Soviet Union) | 572 | 2122 | 5 | 581 | 1849 | -9 |
| United States of America | 427 | 1384 | 5 | 523 | 1685 | -96 |
| Japan | 368 | 1368 | 5 | 85 | 253 | +283 |
| France | 329 | 1332 | 5 | 173 | 626 | +156 |
| China | 335 | 1169 | 5 | 385 | 1397 | -50 |
| Germany (Prussia) | 272 | 1075 | 5 | 198 | 696 | +74 |
| Rumania | 233 | 997 | 5 | 89 | 387 | +144 |
| United Kingdom | 298 | 987 | 5 | 227 | 760 | +71 |
| Spain | 230 | 982 | 5 | 39 | 116 | +191 |
| Iraq | 240 | 937 | 5 | 417 | 1385 | -177 |

![Top actors](../../output/charts/top_actors.png)

**Observations:**
- **Russia (Soviet Union)** leads on both initiation and being targeted.
- **Iraq** stands out as strongly offense-leaning: 210 events initiated vs 167 targeted, and a positive offense-defense balance.
- **People's Republic of Korea** and **Iran (Persia)** are heavily targeted relative to their initiation counts.
- **Rumania**, **Spain**, and **Japan** appear in the initiator top-10 but not the target top-10, indicating an offense-skewed profile.

### Most persistent rivalries (longest span of repeated years)

| Initiator -> Target | First | Last | Years observed | Events |
|---|---|---|---|---|
| Japan -> Russia (Soviet Union) | 1900 | 2014 | 115 | 69 |
| China -> Japan | 1900 | 2014 | 115 | 36 |
| China -> United States of America | 1900 | 2013 | 114 | 38 |
| China -> Russia (Soviet Union) | 1900 | 2012 | 113 | 43 |
| Turkey (Ottoman Empire) -> Russia (Soviet Union) | 1902 | 2014 | 113 | 22 |
| United Kingdom -> United States of America | 1902 | 2014 | 113 | 18 |
| United Kingdom -> Russia (Soviet Union) | 1904 | 2014 | 111 | 35 |
| Venezuela -> Colombia | 1900 | 2010 | 111 | 7 |
| Japan -> China | 1907 | 2014 | 108 | 32 |
| Greece -> Turkey (Ottoman Empire) | 1909 | 2014 | 106 | 45 |

## 5. Aggregated CSV index

- `output/analysis/quality_report.csv` - dataset-level quality metrics
- `output/analysis/yearly_counts.csv` - event counts by year and tier
- `output/analysis/decade_tier_counts.csv` - event counts by decade and tier
- `output/analysis/actor_metrics.csv` - per-country initiation/targeting stats
- `output/analysis/dyads.csv` - per-dyad aggregated event count and mean/max tier

