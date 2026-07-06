# Wikipedia tier-extraction pipeline

End-to-end driver for the seven-stage pipeline that builds
`data/processed/conflict_dyads_wikipedia.csv` from a
`wikimedia/structured-wikipedia` Parquet export.

The pipeline uses **Ollama** as the LLM server (not LM Studio) and
`nemotron-3-nano:4b` as the default model for all LLM stages. The
default endpoint is read from `OLLAMA_BASE_URL` (e.g.
`http://localhost:11434/v1`); set it to wherever your Ollama server runs.

## Quick start

```bash
# 0. Place the Wiki export under data/raw/structured-wikipedia/<name>/data/
#    e.g. data/raw/structured-wikipedia/enwikiV2/data/*.parquet
#    The filter auto-discovers the most recently modified subdir.
#
# 1. (Optional) Run a smoke test on a few articles:
.venv/bin/python scripts/build/_run_v2_pipeline.py --smoke-test 5

# 2. Run the full pipeline (uses OLLAMA_* env vars)
.venv/bin/python scripts/build/_run_v2_pipeline.py
```

## Architecture (7 stages, 3 LLM passes)

| # | Name | Description | Outputs |
|---|---|---|---|
| 1 | gwn_map | Resolve CShapes names to Wikidata QIDs via the English Wikipedia API | `data/processed/wiki_gwn_map.csv`, `data/processed/wiki_gwn_overrides.csv`, `tmp/wiki_gwn_map_diag.json` |
| 2 | filter | **DuckDB country-only** + Python bilateral gate. Auto-discovers parquet shards under `data/raw/structured-wikipedia/<name>/data/`. Yields ~50–60k LLM-path articles. | `tmp/wiki_tier_candidates.parquet`, `tmp/wiki_filter_stats.json` |
| 3 | t01_filter | Batched LLM 0/1 filter (3 articles per prompt). Asks whether each bilateral article contains a conflict or dispute between nation states. Broadened from the legacy regex tier-keyword gate to admit diplomatic friction. | `tmp/wiki_t01_filter_kept.jsonl`, `tmp/wiki_t01_filter_rejected.jsonl`, `tmp/wiki_t01_filter_run.json` |
| 4 | t45_extract | **Combined LLM extraction** (1 article per prompt). Emits `tier`, `start_year`, `end_year`, `explanation`, and a list of directed (initiator, target, confidence, implied) pairs. Replaces the legacy tier-classifier + event-extractor + correlate steps with a single call. | `tmp/wiki_t45_extracted.jsonl`, `tmp/wiki_t45_failed.jsonl`, `tmp/wiki_t45_run.json` |
| 5 | aggregate | Pure-Python aggregation. For each article: drop low-confidence pairs, apply -0.2 discount to implied pairs, resolve country names to GWN codes, expand `[start_year, end_year]` into one row per year, pick max tier per (year, ig, tg). Emits `year_status=""` for normal, `"unknown_start"` / `"unknown_end"` / `"unknown"` for sentinels. | `data/processed/conflict_dyads_wikipedia.csv` (31 cols) + `.parquet`, `tmp/wiki_year_tier_counts.csv`, `tmp/wiki_mismatch_pairs.jsonl`, `tmp/wiki_unresolved_pairs.log` |
| 6 | country_resolve | LLM pass over unresolved country names from stage 5. Maps each to a canonical name; writes the result as `Resolved (raw: Original)` in the original column, with downstream consumers treating the parenthetical as if it does not exist. Only runs when stage 5 emitted unresolved rows. | rewrites `conflict_dyads_wikipedia.csv`, `tmp/wiki_country_resolution.json`, `tmp/wiki_country_resolution_run.json` |
| 7 | validate | Cross-dataset comparison (agreement/disagreement/new vs `conflict_dyads_full.csv`, compound sources split on `_`) + diagnostics (per-year P/R/F1, per-tier metrics, source counts, GWN resolution, top dyads, transitions). Writes three new columns: `agreement_datasets`, `disagreement_datasets`, `is_new`. | rewrites `conflict_dyads_wikipedia.csv` (34 cols), `output/analysis/wiki_validation_report.md`, `output/analysis/wiki_mismatch_table.csv`, `output/analysis/wiki_extraction_diagnostics.{md,csv}` |

## Wiki data: how to provide it

The pipeline no longer downloads the Wikipedia snapshot — the user
provides it. Place the parquet shards under any subdirectory of
`data/raw/structured-wikipedia/`, e.g.:

```
data/raw/structured-wikipedia/enwiki/data/*.parquet         (v1 export)
data/raw/structured-wikipedia/enwikiV2/data/*.parquet       (v2 export)
```

The filter (stage 2) auto-discovers the most recently modified
`*/data/*.parquet` directory. To use a specific export, pass
`--parquet-glob` explicitly:

```bash
.venv/bin/python scripts/build/wiki_filter_candidates.py \
    --parquet-glob 'data/raw/structured-wikipedia/enwikiV2/data/*.parquet'
```

## LLM passes (3)

1. **Stage 3 (t01_filter):** 0/1 batched call (3 articles per prompt). Cheap precision check. Drops ~75% of bilateral articles as non-conflict.
2. **Stage 4 (t45_extract):** 1 article per prompt, structured JSON with `tier`, `start_year`, `end_year`, `explanation`, and a list of directed (initiator, target, confidence, implied) pairs. The detailed event fields.
3. **Stage 6 (country_resolve):** 1 unresolved country name per prompt. Maps historical or unusual country names (e.g. "Russian Empire", "USSR") to canonical entries in the country list.

The structured infobox path that previously extracted T4/T5 events
from conflict-style Wikipedia infoboxes has been removed. The LLM
in stage 4 is now the sole tier authority; the only T4/T5 evidence
comes from the article text and the LLM's classification of it.

## Configuration

All knobs are environment variables, with sensible defaults:

| Variable | Default | Effect |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama OpenAI-compatible endpoint used by stages 3, 4, 6 |
| `OLLAMA_MODEL` | `nemotron-3-nano:4b` | Model name to verify against `GET /v1/models` |
| `OLLAMA_N_PARALLEL` | `5` | Concurrent worker count for stages 3, 4, 6 |
| `OLLAMA_BATCH_SIZE` | `3` | Articles per LLM prompt (stage 3 only) |
| `PIPELINE_MIN_CONFIDENCE` | `0.7` | Per-pair confidence floor (stage 5). Implied pairs get a further -0.2 discount. |
| `PIPELINE_MAX_ARTICLES` | `0` | Cap on input articles for stages 3, 4 (0 = no cap) |
| `PIPELINE_LOG` | `tmp/wiki_pipeline.log` | Log file path |

For backward compat, the legacy `LMSTUDIO_*` env vars are also read as
fallbacks when `OLLAMA_*` is unset.

## LLM reliability (important)

All three LLM scripts (`wiki_extract_llm_t45_ambiguous.py`,
`wiki_extract_llm_t123.py`, `wiki_extract_llm_t123_classifier.py`) use
the shared helper `scripts/build/wiki_llm_helpers.py`, which fixes
four LM Studio bug patterns:

1. **`response_format: json_object` is rejected with HTTP 400.**
   The OpenAI-compat layer only accepts `"json_schema"` or `"text"`.
   We omit `response_format` entirely and let the system message
   + one-shot JSON example in the prompt guide the LLM.

2. **Reasoning tokens can consume 100% of `max_tokens`**, leaving
   `content=""` and `finish_reason="length"`. The default
   `max_tokens` is 2500 for the T45 confirm pass, **8000** for the
   T123 classifier, and 6000 for the T123 detailed extractor.
   The 8000 value for the classifier was set after an empirical
   length-vs-failure diagnostic showed that ~15% of articles use
   4000+ tokens of chain-of-thought reasoning. The model's CoT
   length is non-deterministic even with `temperature=0` /
   `seed=42` — the same article can use 780 or 8000+ tokens on
   different runs. 8000 + the helper's 3 retries (which the
   existing `no_json_in_response` / `json_decode` retry path
   already covers) gives near-zero failure rate.

3. **The model emits a "Thinking Process: ..." trace into
   `reasoning_content`. The actual JSON goes into `content`. If
   `content` is empty (truncation), the JSON may also be partially
   or fully inside `reasoning_content`.** The helper falls back
   to `reasoning_content` if `content` is empty.

4. **`<think>...</think>` tags can leak into `content`.** The
   helper strips these defensively before JSON extraction.

In addition:

- **Per-call timeout** (default 600 s) on every LLM call. Hung
  calls fail fast and the script moves to the next article.
- **Automatic per-article diagnostic write** to
  `tmp/wiki_*_debug/<article_id>.json` on every failure. The
  payload includes `raw_content`, `raw_reasoning`, the extracted
  JSON block, the error, the article's `tier_hint`, and the
  `finish_reason` (e.g. `"length"` for `max_tokens` truncation).
  Inspect these to diagnose LM Studio reasoning-content issues
  without re-running the script.
- **Append-mode file output** with **line buffering** (`buffering=1`).
  Re-runs no longer destroy prior results; the script extends the
  existing JSONL. Line buffering means a SIGTERM or crash loses at
  most the in-flight line, not the default 4-8 KB block-buffered
  amount.
- **One-line progress meter** updated every article: percentage
  bar, kept/rejected/failed counts, rate, ETA.

### Throughput expectations

With `n_parallel=1` on the qwen3.5-9B model with chain-of-thought reasoning:

- **T45 confirm pass** (31 candidates): ~30–60 min serial
- **T123 classifier** (1,500 articles): ~21–50 hours serial
- **T123 detailed extractor** (~500–1,000 classifier positives): ~7–25 hours serial

Per-article wall time for the classifier is highly variable
(14 s to 6+ min) because the model's chain-of-thought length
varies non-deterministically even with `temperature=0` / `seed=42`.
The classifier's average is ~40-50 s per article, but worst-case
articles (complex modern conflicts, list articles) can take
several minutes. Use `--max-articles N` to cap input and
`--max-tokens` to override the 8000-token budget.

You can stop and resume any LLM stage safely (append-mode file
output with line buffering preserves prior results).

## Country-name resolution

The pipeline uses a canonical country-name list at
`data/processed/wiki_country_canonical.csv` (built once by
`scripts/build/build_country_canonical.py`). The list is the union of:

1. **CShapes-2.0** (252 unique `cntry_name` values, with year-ranges per state)
2. **wiki_gwn_map** (234 QID→GWN rows for modern sovereign states)
3. **Hand-curated alias dict** (~60 entries: russia ↔ ussr ↔ soviet union, myanmar ↔ burma, sri lanka ↔ ceylon, eswatini ↔ swaziland, etc.)

The list has 289 canonical rows, 775 total aliases, and 180 modern sovereign states. The aggregator and LLM prompts both rely on it for name→GWN lookup and tier-crosswalk validation.

## Tier scheme

The Wikipedia output (`conflict_dyads_wikipedia.csv`) is aligned to the
**v27.0 spec scheme**:

| Tier | Label | hostlev | Notes |
|---|---|---|---|
| T1 | T1-Diplomatic Crisis | 1 | Protests, recalls, ultimatums, coercive threats, UN votes, demarches |
| T2 | T2-Economic Coercion | 2 | Imposed sanctions, embargoes, asset freezes, financial exclusion |
| T3 | T3-Proxy/Indirect Military | 3 | Sustained selective support to armed groups |
| T4 | T4-Limited Military | 4 | Open, attributed exchange of fire |
| T5 | T5-Strategic War | 5 | Nationwide / multi-front warfare (reach-gated) |

The legacy ground-truth dataset (`conflict_dyads_full.csv`) uses a different scheme (T2=hostlev-3, T3=hostlev-3, the two collide). The validation report includes a tier-crosswalk table for comparison.

## Stage 3 — country+keyword 3-stage narrowing

Stage 3 replaces the legacy tier-keyword filter with a broader country+keyword approach:

**Stage 3a (DuckDB broad filter):** one columnar pass over the 35 GB enwiki snapshot. Keeps articles where:
- ≥1 canonical country name appears in `abstract OR name` (whole-word, case-insensitive), AND
- ≥1 broad conflict keyword appears in `abstract OR name` (whole-word, case-insensitive)

Broad keyword set (~30 phrases): `conflict`, `war`, `sanction`, `embargo`, `blockade`, `dispute`, `tension`, `hostilit`, `crisis`, `invasion`, `occupation`, `annexation`, `recall.{0,5}ambassador`, `ultimatum`, `ceasefire`, `truce`, `armistice`, `mobiliz`, `airstrike`, `bombing`, `clash`, `skirmish`, `insurgent`, `rebel`, `separatist`, `militant`, `terrorist`, `interven`, `deploy`, `missile`, `proxy`, `covert`, etc.

Yields ~300–500k broad candidates.

**Stage 3b (Python bilateral gate):** keep articles where:
- ≥2 canonical country names in `(abstract OR name)`, AND
- ≥1 of those countries is a modern sovereign state (end_year ≥ 2020)

Yields ~50–200k.

**Stage 3c (Python tier-keyword gate):** keep articles where a tier-specific keyword matches within 400 characters of a country name mention. The tier-specific sets are:

- **T1**: `recall.{0,5}ambassador`, `expelled diplomat`, `ultimatum`, `severed diplomatic`, `demarche`, `UN.{0,5}(vote|resolution|censure)`, `condemn.{0,30}(invasion|attack)`, `imposed a travel ban`
- **T2**: `imposed sanction`, `announced sanction`, `economic sanction`, `trade embargo`, `weapons embargo`, `asset freeze`, `SWIFT disconnection`, `designated as state sponsor`, `oil embargo`, `banned.{0,20}imports`
- **T3**: `supplied weapons to`, `armed (group|rebel)`, `proxy force`, `trained and equipped`, `transferred.{0,30}drones`, `covert support to`, `funding.{0,20}hezbollah`

Yields ~1,500 LLM-path articles (1,006 T1 / 296 T2 / 436 T3).

The T4/T5 path stays the same: any article with a conflict-style infobox (military conflict, war, battle, etc.) is routed to the infobox parser, regardless of the tier-keyword gate. ~12k T4/T5 candidates.

## Stage 5 — T4→T5 LLM confirm pass

The infobox parser defaults T4 articles to hostlev=4 (limited military). The v27.0 spec has T5 = "strategic war" which can be reached by a T4 article that:
- Has a `Infobox military conflict` with ≥4 belligerents, OR
- Spans ≥3 years, OR
- Has a title matching `r"\b(war|world war|civil war|invasion|occupation)\b"` with ≥3 belligerents or ≥2 year span, OR
- Has a title in the hand-curated allowlist at `data/processed/wiki_t5_title_allowlist.csv` (~700 strategic-war titles)

For each T5 candidate, stage 5 asks the LLM (LM Studio, qwen3.5-9B) a yes/no question with a short prompt (`scripts/build/prompts/wiki_t45_ambiguous_v1.txt`). Confirmed T5 articles are emitted as T5 events; disagreements go to `tmp/wiki_t45_ambiguous_review.csv` for human review.

## Stage 6 — T1/T2/T3 LLM classifier

This is a two-pass LLM pipeline for the textual tiers:

**Pass 1 (classifier):** for each T1/T2/T3 candidate article, ask the LLM a short yes/no question: "Does this describe a real interstate conflict event? If so, what tier is most likely?" Output is a JSON with `is_conflict_event`, `tier_likely`, `countries`, `year`, `confidence`. Articles where `is_conflict_event=true` and `tier_likely in {T1,T2,T3}` and `len(countries) >= 2` and `year is not null` and `confidence >= 0.4` are passed to pass 2; the rest are rejected with reason.

The classifier prompt (`scripts/build/prompts/wiki_t123_classifier_v1.txt`) is short and pre-pended with the article's tier_hint (T1/T2/T3) so the LLM can specialize.

**Pass 2 (extractor):** for each classifier-positive article, ask the LLM to extract structured event records. The detailed-extractor prompt (`scripts/build/prompts/wiki_t123_v2.txt`) includes:
- One-shot JSON example
- Tier-boundary rules (e.g. "if a coercive threat was followed by sanctions, emit a T1 row for the threat year AND a T2 row for the sanctions year")
- False-positive guard (e.g. "the keyword may appear in non-conflict contexts")
- v27.0 spec verbatim tier definitions

Output is `tmp/wiki_t123_extracted.jsonl` with one row per event, schema:
```json
{
  "article_id": 72830659,
  "article_title": "Executive Order 13871",
  "year": 2019,
  "start_year": 2019,
  "end_year": 2019,
  "tier": "T2",
  "hostlev": 2,
  "tier_label": "T2-Economic Coercion",
  "source": "WIKI_T2",
  "initiator_country": "United States of America",
  "target_country": "Iran",
  "confidence": 0.95
}
```

## Validation report

Stage 9 emits `output/analysis/wiki_validation_report.md` comparing the Wikipedia dyad-years against `conflict_dyads_full.csv` for the 2010–2014 validation window. Per-tier precision/recall/F1, tier-crosswalk table, per-source row counts, GWN-resolution rate, and stage diagnostics are all included.

`output/analysis/wiki_mismatch_table.csv` is a long-form table with one row per (Wikipedia dyad-year, ground-truth dyad-year) pair. Mismatch kinds: `tier_over`, `tier_under`, `year_off`, `direction_flip`, `hostlev_drift`, `only_in_wiki`, `only_in_ground_truth`, `match`.

## Throughput notes

- Stages 1–2: download + Wikidata (one-time, 1–2 hours total)
- Stage 3: ~6 min for the DuckDB pass + ~6 min for the Python narrowing = ~12 min
- Stage 4: ~2 min
- Stage 5: ~10 min (small candidate set)
- Stage 6 (LLM classifier): ~21–50 hours for 1,500 articles at n_parallel=1 (qwen3.5-9B Q8_0, 16 GB RDNA-2). n_parallel=4 documented previously is not achievable — qwen3.5-9B on this GPU serializes internally; n_parallel>1 deadlocks LM Studio. With max_tokens=8000 the failure rate is near zero (one observed failure in the empirical 10-article length diagnostic, attributable to non-deterministic CoT length).
- Stage 7 (LLM extractor): ~7–25 hours for ~500–1,000 classifier positives at n_parallel=1
- Stage 8 (aggregate): ~30 sec
- Stage 9 (validate): ~30 sec

The qwen3.5-9B model uses chain-of-thought reasoning internally. Each LLM call may take 14 s to 6+ min even for short prompts. The smoke test (`--smoke-test 5`) takes ~5–10 minutes; a full classifier run on 1,500 articles takes ~25–40 hours.

## Failure handling

If a stage exits with a non-zero code (or raises an unhandled
exception), the orchestrator:

1. Logs the error to `tmp/wiki_pipeline.log`.
2. Writes a partial `tmp/wiki_pipeline_run.json` with `error_stage`
   set to the failing stage number.
3. Exits with code 1.

Subsequent stages are not run. Re-run the orchestrator with the
failing stage(s) selected to retry, e.g.
`python scripts/build/wiki_pipeline.py run --stages 6,7`.

## Adding a new stage

1. Write the child script in `scripts/build/`. Its `main()` should
   parse `sys.argv` with `argparse` and return an integer exit code.
2. Add an entry to `_build_stage_defs()` in `wiki_pipeline.py` with
   the module name, output paths, and an `args_factory` callable.
3. Update this doc and the stage table.

## Outputs (orchestrator)

The orchestrator writes four JSON files in `tmp/` to make runs
inspectable:

- `tmp/wiki_pipeline.log` — one line per stage event (rolling text log)
- `tmp/wiki_pipeline_manifest.json` — per-stage outputs, timestamps, byte sizes
- `tmp/wiki_pipeline_state.json` — per-stage config fingerprint (display only; not used for skip decisions)
- `tmp/wiki_pipeline_run.json` — final run summary (which stages ran, total time, total bytes)

The orchestrator does not skip stages. Every `run` invocation
re-executes the selected stages. The manifest and state files are
written for diagnostic purposes only.
