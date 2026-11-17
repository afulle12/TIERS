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
| EUSANCT | 2022 | 1989-2015 | Research use | Weber, P. M., & Schneider, G. (2022). *Post-Cold War Sanctioning by the EU, the UN, and the US: Introducing the EUSANCT Dataset*. |
| TIES (Threat and Imposition of Economic Sanctions) | v4.0 / v4.1 | 1945-2005 | Research use | Morgan, T. C., Bapat, N., & Kobayashi, Y. (2014). *Threat and Imposition of Economic Sanctions 1945–2005*. |
| ICB (International Crisis Behavior) | v16 | 1918-2022 | Research use | Brecher, M., Wilkenfeld, J., et al. (2025). *International Crisis Behavior Data Archive, Version 16*. |
| Pardee Diplometrics Diplomatic Representation | v2023 / 2026 release | 1960-2025 | Research use | Frederick S. Pardee Institute for International Futures. *Diplomatic Representation Dataset*. |
| Militarized Compellent Threats (validation check) | v0.9 | 1918-2001 | Research use | Sechser, T. S. (2011). *Militarized Compellent Threats, 1918–2001*. |
| CShapes | 2.0 | 1946-onward | CC-BY 4.0 | Weidmann, N. B., Rød, J. K., & Ketterer, L. (2024). *Introducing the CShapes 2.0 dataset*. |
| V-Dem | v16 (CY Core) | 1789-2024 | CC-BY 4.0 | Coppedge, M. et al. (2025). *V-Dem [Country-Year/Country-Date] Dataset v16*. |
| NMC (COW National Material Capabilities) | v7.0 abridged | 1816-2022 | Research use | Singer, J. D., Bremer, S. A., & Stuckey, J. (1972); updated. |
| ATOP | 3.0 | 1815-onward | Research use | Leeds, B. A., Long, A. G., & Mitchell, S. M. (2000). *Alliance Treaty Obligations and Provisions*. |
| Wikipedia (structured-wikipedia) | 2026-05-13 snapshot | 1816-onward | CC-BY-SA-4.0 | Wikimedia Foundation (2026). *Structured Wikipedia*, Hugging Face dataset. |
| CEPII BACI | HS92 V202601 | 1995-2024 | Etalab Open Licence 2.0 | Gaulier, G., & Zignago, S. (2010). *BACI: International Trade Database at the Product-Level. The 1994-2007 Version*. CEPII Working Paper No. 2010-23. |
| CEPII TRADHIST | v4 | 1827-2014 | Etalab Open Licence 2.0 | Fouquin, M., & Hugot, J. (2016). *Two Centuries of Bilateral Trade and Gravity Data: 1827-2014*. CEPII Working Paper No. 2016-14. |

## Tier definitions and source mapping

| Tier | Definition | Sources used |
|---|---|---|
| T1 — Diplomatic Crisis | Formal friction: protests, recalls, ultimatums, coercive threats | MID5 (`hostlev` 2–3 threats/displays + coalition-capped force, 1900–2014) + EUSANCT (`threat_dyad==1`, `sanction_dyad!=1`, 1989–2015) + TIES v4.0 (`threat==1`, non-imposed years, 1945–2005) + ICB v16 (crisis dyad-years below T3, 1918–2022) + Pardee DRD (`Focus==3` recalls/withdrawals/expulsions, 1960–2025) |
| T2 — Economic Coercion | Active sanctions, trade restrictions, financial exclusion | EUSANCT (`sanction_dyad==1` for US/EU, 1989–2015; unobserved 1946–1988 via `source_coverage.py`) |
| T3 — Proxy/Indirect Military | Sustained, selective material support to j's adversaries, directed at j | UCDP Dyadic v26.1, `type_of_conflict==4` troop support |
| T4 — Limited Direct Military | Open, attributed exchange of fire between i and j forces | MID5 (`hostlev==4` with target evidence) + UCDP Interstate Armed Conflict v26.1 |
| T5 — Strategic War | Nationwide / multi-front warfare, sustained campaigns | MID5 (`hostlev==5` with target evidence) |
| T0 — Peace | Inferred: no T1–T5 event in the dyad-year | Complement of T1–T5 events across `state_system` members |

## Economic-interdependence data

CEPII BACI and TRADHIST are normalized into a shared directed dyad-year
source of truth at `data/processed/trade_interdependence.csv` (and
`.parquet` when Parquet support is available). The key is
`year, initiator_gwno, target_gwno`, matching the model feature grid.

- BACI HS92 V202601 is used for 1995-2024 and is preferred in overlap
  years because it is reconciled, product-level, and current.
- TRADHIST v4 fills historical bilateral-trade coverage through 2014.
- `data/processed/country_code_crosswalk.csv` records the BACI/TRADHIST
  code-to-GWNO mapping and unresolved source codes.
- The processed trade table includes observed flows, country trade totals,
  directed dependence, mutual dependence, import/export leverage, trade
  surface, and trade-surface percentile variables for the v28 economic block.

## Wikipedia-derived tier data (extension source)

The structured-wikipedia dataset (`wikimedia/structured-wikipedia`,
Hugging Face) is used as a **supplementary signal** to extend tier
codings past the COW MIDB 5.0 (2014) and EUSANCT (2015) cutoffs. It is
not used to replace or override the existing COW/UCDP codings in
`conflict_dyads_full.csv`. The Wikipedia-derived rows live in a
parallel file, `data/processed/conflict_dyads_wikipedia.csv`, with the
same schema and `source ∈ {WIKI_T1, WIKI_T2, WIKI_T3, WIKI_T4, WIKI_T5}`.

The extraction pipeline is:

1. `wiki_acquire.py` — downloads the 2026-05-13 snapshot of enwiki to
   `data/raw/structured-wikipedia/` (~35 GB).
2. `wiki_filter_candidates.py` — DuckDB columnar pass that selects
   articles with conflict-style infoboxes (T4/T5) and articles whose
   abstract matches tier-discriminating keywords (T1/T2/T3). Writes
   `tmp/wiki_tier_candidates.parquet`.
3. `wiki_build_gwn_map.py` — Resolves each CShapes country name to
   a Wikidata QID via the English Wikipedia API
   (`action=query&prop=pageprops&ppprop=wikibase_item`). A second
   pass tries a small set of pre-defined variants (stripping
   parentheticals, common historical-state aliases) for the names
   that don't resolve directly. Writes
   `data/processed/wiki_gwn_map.csv` (QID ↔ GWN). Achieves ~93%
   coverage of the CShapes registry out of the box; the remaining
   ~7% (mostly historical states like Danzig, German Togoland,
   Northern Nigeria Protectorate) can be added by hand via
   `data/processed/wiki_gwn_overrides.csv`.

   Note: Wikidata does not currently expose GWN as a single
   external-id property — the natural-looking candidate P5008 is
   "Game World Navigator ID", not GWN. The Wikipedia API approach
   is the standard workaround.
4. `wiki_extract_infobox_t45.py` — pure-Python parser of the
   conflict-style infoboxes (`Infobox military conflict`, `Infobox war`,
   `Infobox battle`, etc.) to emit directed dyad-year T4/T5 events.
   No LLM. Output: `tmp/wiki_t45_events.jsonl`.
5. `wiki_extract_llm_t123.py` — LLM extraction (LM Studio, Qwen3.5-9B
   Q8_0 by default) for T1/T2/T3. Reads the candidate parquet, sends
   the abstract + first ~6k chars of section text to the LLM, and
   records a JSON event list per article. Output:
   `tmp/wiki_t123_extracted.jsonl`, plus `tmp/wiki_t123_run.json` with
   the prompt SHA-256, model name, and timing.
6. `wiki_aggregate_dyads.py` — joins both JSONLs, resolves country
   names to GWN codes via the QID↔GWN map, drops self-dyads and
   non-state actors, aggregates to one row per (year, initiator_gwno,
   target_gwno, max_tier), and writes
   `data/processed/conflict_dyads_wikipedia.csv` (and `.parquet`).
   Also writes `output/analysis/wiki_validation_report.md` comparing
   the 2010–2014 window against the MIDB+UCDP+EUSANCT ground truth.

### Known biases

- English-language Wikipedia: significant under-representation of
  non-English-speaking regions' conflicts, especially for T1/T2/T3
  events.
- Single snapshot (May 2026): no edit-history-aware extraction. The
  state of an article on date X is approximated by the state of the
  article on 2026-05-13.
- T1 (diplomatic crisis) and T3 (proxy support) are the noisiest
  tiers; they depend on LLM extraction of free text.
- T3 specifically is expected to under-detect: covert proxy support
  is exactly what underdocumented conflicts lack in Wikipedia, which
  is why the existing pipeline also uses UCDP Dyadic as a structured
  proxy.
- The Wikipedia snapshot is dated 2026-05-13, so events that occurred
  after the MIDB/EUSANCT cutoffs (2014/2015) are recoverable but with
  the precision/recall trade-offs documented in
  `output/analysis/wiki_validation_report.md`.

### Licensing

The structured-wikipedia dataset is published under CC-BY-SA-4.0.
Derived outputs (the CSV/Parquet files) inherit the same license.
Attribution: "Structured Wikipedia, Wikimedia Foundation, 2026-05-13
snapshot, used under CC-BY-SA-4.0."

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
- `data/processed/conflict_dyads_wikipedia.csv` (+ .parquet) — T1–T5
  directed dyad-years extracted from the structured-wikipedia snapshot.
  Held separate from `conflict_dyads_full.csv`; not merged by default.
- `data/processed/wiki_gwn_map.csv` — Wikidata-QID ↔ GWN-code
  reconciliation table (built once via SPARQL).
- `data/processed/country_code_crosswalk.csv` — BACI/TRADHIST source-code
  reconciliation to GWNO.
- `data/processed/trade_interdependence.csv` (+ .parquet) — CEPII
  BACI/TRADHIST directed dyad-year economic-interdependence source of truth.
- `data/processed/dyads_with_features_v28.csv` (+ .parquet) — v27 structural
  feature grid plus the v28 economic-interdependence block.

## Adding a new source

When integrating a new dataset, add a row to the table above and a brief
description of the tier(s) it informs in the `Tier definitions and source
mapping` section. Update `scripts/build/` with the corresponding builder and
ensure the data file is placed in `data/raw/` (or referenced from a
download-on-demand location).
