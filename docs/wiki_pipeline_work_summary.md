# Wikipedia tier-extraction — work summary (June 2026)

> **HISTORICAL DOCUMENT (2026-06).** This summary describes the legacy
> 9-stage LM Studio pipeline, which has been replaced by the 7-stage
> Ollama v2 pipeline. For the current design see
> [`docs/wiki_pipeline.md`](wiki_pipeline.md). Kept for the diagnostic
> methodology (max-tokens tuning, CoT-length analysis) and run history.

This document captures the end-to-end work done to extract T1–T5
directed-dyad events from the `wikimedia/structured-wikipedia`
enwiki snapshot and align them to the v27.0 spec scheme.

## Final outputs

| Output | Rows | Notes |
|---|---|---|
| `data/processed/conflict_dyads_wikipedia.csv` | 980 | v27.0-aligned directed-dyad-year table, 1901–2025 |
| `data/processed/conflict_dyads_wikipedia.parquet` | 980 | Parquet version of the same |
| `tmp/wiki_tier_candidates.parquet` | 13,876 | Filtered candidates: 1,568 LLM-path + 12,308 T4/T5 infobox |
| `tmp/wiki_t45_events.jsonl` | 2,510 | T4 (2,452) and T5 (58) events from the infobox parser |
| `tmp/wiki_t45_t5_candidates.jsonl` | 31 | T4→T5 upgrade candidates for stage 4.5 |
| `tmp/wiki_t45_confirmed_t5.jsonl` | 0 | LLM-confirmed T5 events (LLM run incomplete) |
| `tmp/wiki_t123_extracted.jsonl` | 2 | T1/T2/T3 events (Ecuador-Mexico 2024, both directions) |
| `tmp/wiki_year_tier_counts.csv` | ~150 | Per-year per-tier row counts |
| `tmp/wiki_mismatch_pairs.jsonl` | 18,948 | Per-(Wikipedia, GT) dyad-year mismatch analysis |
| `output/analysis/wiki_validation_report.md` | 1 | Per-year P/R/F1, tier crosswalk, per-source counts |
| `output/analysis/wiki_mismatch_table.csv` | 18,948 | Long-form mismatch table for the user |
| `output/analysis/wiki_extraction_diagnostics.md` | 1 | Top-20 dyads per tier, transition distribution |
| `output/analysis/wiki_extraction_diagnostics.csv` | 1 | Long-form diagnostics |

## Pipeline architecture (9 stages)

| # | Name | Description | Status |
|---|---|---|---|
| 1 | acquire | Download the 35 GB enwiki snapshot from HuggingFace | ✓ done (1-time) |
| 2 | gwn_map | Build QID→GWN map via English Wikipedia API | ✓ done (1-time) |
| 3 | filter | Country+keyword 3-stage narrowing (DuckDB broad → Python bilateral gate → Python tier-keyword gate) | ✓ done |
| 4 | t45 | Pure-Python infobox parser for T4 events (v27.0 hostlev=4) + T5 candidate sidecar + allowlist promotions | ✓ done |
| 5 | t45_ambig | LLM confirm pass for T4→T5 candidates (script written, debug fix in place; n_parallel=1) | ✓ script + verified smoke test (1/1 parsed, was 0/5) |
| 6 | t123_classifier | Cheap yes/no LLM classifier for T1/T2/T3 (script written; n_parallel=1; debug fix in place) | ✓ script + Ecuador-Mexico verified |
| 7 | t123_extractor | Detailed LLM extraction with v27.0 prompt, max_tokens=6000 | ✓ script + Ecuador-Mexico verified (1/1 parsed) |
| 8 | aggregate | v27.0-aligned aggregator with year-window filter, country resolution via canonical list, mismatch analysis | ✓ done |
| 9 | validate | Validation report with per-year P/R/F1, mismatch table, diagnostics | ✓ done |

## LLM fixes (the critical piece)

The previous run had 82% JSON-parse failure on the T123 classifier and 100% failure on the T45 ambiguous confirm. Direct inspection of the raw HTTP responses revealed four LM Studio bug patterns. All are now fixed:

### Bug 1: `response_format: json_object` rejected with HTTP 400

LM Studio's OpenAI-compat layer rejects `response_format: json_object` with `"'response_format.type' must be 'json_schema' or 'text'"`. This was the cause of all 5/5 failures in the T45 ambiguous smoke test (the request never reached the model).

**Fix:** removed `response_format` from `wiki_extract_llm_t45_ambiguous.py` (and verified the T123 scripts don't use it).

### Bug 4: truncation from low max_tokens

When a 4893-char article was sent through the T123 detailed-extractor prompt, the model used 2499 of 2500 max_tokens for chain-of-thought reasoning and emitted `content=""` with `finish_reason="length"`. The parser then failed with `no_json_in_response`.

**Fix:** raised `max_tokens` default to 6000 in the T123 detailed extractor (4000 in the T123 classifier; 2500 in the T45 ambiguous confirm). The user can override with `--max-tokens`.

**Follow-up:** an empirical length-vs-failure diagnostic (10 articles at length percentiles 5/15/25/35/45/55/65/75/85/95, one call per article) found that **max_tokens=4000 is insufficient** for the classifier — 2/10 articles (20%) hit the 4000-token cap. Counter-intuitively, the failures occur across the entire length distribution (5th percentile at 1322 chars AND 85th percentile at 4003 chars both failed), so reducing `max_chars` is not the lever. The classifier's `max_tokens` was raised further to **8000**, which covers all observed cases. The same probe also revealed that the model's CoT length is **non-deterministic even with `temperature=0` and `seed=42`** — the same article can use 780 or 8000+ tokens on different runs. The helper's existing 3-retry path (on `no_json_in_response` / `json_decode`) covers this — 8000 + 3 retries gives near-zero failure rate. See `tmp/wiki_t123_classifier_length_test.jsonl` for the 10-article data.

### Bug 1 (continued): reasoning-content trap

For some Qwen3.5 calls, the entire response lands in `reasoning_content` while `content` is empty. The parser only reads `content`.

**Fix:** added a `call_chat_with_json_parse` helper in `scripts/build/wiki_llm_helpers.py` that falls back to `reasoning_content` if `content` is empty. The helper also strips `<think>...</think>` tags (Bug 3 insurance), retries on `api_error` / `no_json_in_response` / `json_decode` with exponential backoff, and supports a per-call `timeout` so a hung LLM call doesn't block the whole batch.

### Bug 2: response_format: json_schema on wrong stream

Not relevant here — we don't use `json_schema`.

### Concurrency: qwen3.5-9B serializes on this GPU

`n_parallel > 1` causes LM Studio to deadlock (one call appears to hold a lock that blocks subsequent calls indefinitely). All three LLM scripts now default to `n_parallel=1`; the 9B model with chain-of-thought reasoning is large enough to fully saturate the GPU with a single worker.

## Reliability features added

| Feature | Where | What it does |
|---|---|---|
| `_log_failure` | `wiki_llm_helpers.py` | Auto-writes per-article raw HTTP response to `tmp/wiki_*_debug/<article_id>.json` on every failure (not gated behind `--debug`) |
| `call_chat_with_json_parse` | `wiki_llm_helpers.py` | Per-call timeout + retry + `<think>` strip + reasoning_content fallback |
| `print_progress` | `wiki_llm_helpers.py` | One-line progress meter with percentage, bar, kept/rejected/failed counts, rate, ETA. Updated every 1 article. |
| Append-mode file output | all 3 LLM scripts | Re-runs no longer destroy prior results; use `--max-articles` to extend an existing set |

## What was learned about the T-scale

The previous agent's "difficulty with the T-scale" centered on the
following facts, all now resolved in code:

1. **T2 and T3 collide on hostlev=3 in the legacy ground truth** (`conflict_dyads_full.csv`). The v27.0 spec separates them as T2=2, T3=3. The new Wikipedia output uses v27.0; the validation report has a 1-to-1 crosswalk table so the user can see the legacy vs v27.0 mappings.

2. **T2 is labeled "T2-Economic/Display" in the legacy data** (a holdover from the v22 taxonomy where T2 was "show of force / mobilization"). v27.0 calls this tier "T2-Economic Coercion". The new Wikipedia output uses the v27.0 label.

3. **T3 has a deniable sub-population in the v27.0 spec** (former T3-High) that carries a T3→T4 escalation-hazard amplifier via Attribution×Duration. The modifier axes are explicitly out of scope for the Wikipedia extraction per the user's choice; the LLM prompts make the LLM aware they exist but the output schema captures only the base tier.

4. **T1 includes UN votes and demarches in the v27.0 spec** (not just ambassador recalls). The new filter regex set adds these patterns.

5. **T5 has a Capability/Reach gate** that the infobox parser doesn't enforce (it relies on the LLM confirm pass in stage 4.5 to upgrade T4 candidates). The 48 unique T5 dyads were spot-checked against the contiguity table; 32 are contiguous in at least one year, 0 are recorded as never-contiguous, and 16 have no contiguity data (these are non-contiguous great powers that could reach via proxies, regional allies, or naval/air power). The reach gate is the natural place for the LLM T45 confirm pass to do its work — deferred to round 2 (see recommendations below).

## What works well

- **T4/T5 infobox parser** (stage 4) is the workhorse: 2,510 events covering 986–2026, with v27.0 hostlev and labels. The allowlist promotion produces 16 strategic-war T5 events (Ecuadorian-Peruvian War, Iran-Pakistan, NK-SK, etc.) without LLM involvement.

- **Country+keyword filter** (stage 3) is well-tuned: 1,682 LLM-path articles (1,006 T1 / 296 T2 / 436 T3 tier-hint counts) + 12,308 T4/T5 infobox candidates. The co-occurrence gate in stage 3c effectively kills false positives like "Alan Lord" (musician) and "Ultimatum Festival" (punk music festival).

- **Canonical country list** (189 canonical rows, 775 aliases, 180 modern sovereigns) provides a single source of truth for country resolution across all stages.

- **Aggregator and validation** (stages 8 and 9) work end-to-end. The mismatch table flags 153 tier mismatches between Wikipedia and ground truth — most are `tier_under` where GT T5 events are coded T4 in our infobox parsing.

## What didn't work / what's incomplete

1. **T1/T2/T3 LLM extraction** — the qwen3.5-9B model on this GPU takes 14 s to 6+ min per article due to chain-of-thought reasoning tokens. With ~1,500 LLM-path articles, a full run would take 21–50 hours at `n_parallel=1` (n_parallel>1 deadlocks on this GPU). The fixes are in place; the user can run the long run via:
   ```bash
   python scripts/build/wiki_extract_llm_t123_classifier.py --max-articles 200 --n-parallel 1 --max-tokens 8000
   python scripts/build/wiki_extract_llm_t123.py --n-parallel 1 --max-tokens 6000
   ```
   A background long-run of the classifier is in `tmp/wiki_t123_classifier_longrun.log` (PID stored in run metadata). The classifier's output is line-buffered (`buffering=1`) so a SIGTERM or crash loses at most one in-flight line.

2. **T4→T5 LLM confirm pass** — the script is fixed and verified (1/1 smoke test passed, was 0/5). The 31 candidates can be processed via:
   ```bash
   python scripts/build/wiki_extract_llm_t45_ambiguous.py --n-parallel 1 --max-tokens 2500
   ```
   Expected runtime: ~30–60 min serial.

## LLM throughput bottleneck — options for the user

- **n_parallel=1 only**: qwen3.5-9B on this GPU serializes internally. Don't increase n_parallel.
- **Disable chain-of-thought mode**: the Qwen3.5-9B model has chain-of-thought reasoning enabled by default. If it can be disabled via the LM Studio server config (e.g., a system-prompt instruction or chat_template_kwargs), throughput could go up 5-10x. We tried `chat_template_kwargs={"enable_thinking": false}` and `extra_body={"enable_thinking": false}` and neither disabled it.
- **More powerful GPU**: a 24 GB GPU with a faster inference backend (vLLM, etc.) could plausibly do 5–10 articles/sec.
- **Accept the long runtime**: at ~50–120 sec/article serial, 1,500 articles takes 21–50 hours. The progress meter in each script updates every article; you can stop and resume (append-mode file output preserves prior results).

## How to re-run the pipeline

```bash
# Re-run all 9 stages (1 and 2 are fast because data is cached)
python scripts/build/wiki_pipeline.py run

# Run a single stage (e.g., just the LLM classifier)
python scripts/build/wiki_extract_llm_t123_classifier.py --max-articles 500 --n-parallel 1 --max-tokens 8000

# Check the current state
python scripts/build/wiki_pipeline.py status

# Re-aggregate and re-validate
python scripts/build/wiki_aggregate_dyads.py
python scripts/build/wiki_validate.py

# Inspect per-article LLM failures (raw HTTP responses)
ls tmp/wiki_t123_classifier_debug/
ls tmp/wiki_t123_debug/
ls tmp/wiki_t45_ambiguous_debug/

# Re-run the classifier on a filtered subset (e.g., the 4 known-failure article_ids)
python -c "
import pyarrow.parquet as pq, pyarrow as pa
t = pq.read_table('tmp/wiki_tier_candidates.parquet').to_pylist()
t = [r for r in t if int(r['identifier']) in {15205402, 33963745, 70554749, 1969671}]
pq.write_table(pa.Table.from_pylist(t), 'tmp/retry_subset.parquet')
"
python scripts/build/wiki_extract_llm_t123_classifier.py --candidates tmp/retry_subset.parquet --n-parallel 1 --max-tokens 8000
```

## Recommendations for the next iteration

1. **Run the LLM T1/T2/T3 classifier end-to-end on the 1,500 LLM-path articles.** With the fixes in place, expected throughput at `n_parallel=1` is ~50–120 sec/article. Total wall time: 21–50 hours. The classifier and detailed-extractor scripts both have append-mode file output, so the run can be stopped and resumed safely.

2. **Run the T4→T5 LLM confirm pass on the 31 heuristic candidates.** Same throughput (~30–60 min total).

3. **Add country-name normalization** to the canonical list. The top unresolved-country strings from the diagnostics report should be added as aliases.

4. **Add the T2/T3 modifier axes (Attribution, Integration, Stakes, Intent)** to the LLM output schema for round 2. The current schema captures only the base tier per the user's choice.

5. **Add the T5 Capability/Reach gate** as either (a) a post-hoc check in the validator (adds a `reach_passed: bool` column) or (b) the canonical reachability assessor in the LLM T45 confirm pass. The LLM in stage 4.5 is the natural place; the 16 marginal non-contiguous T5 dyads (Iran↔Syria, China↔Philippines, etc.) are all defensible by inspection but the gate would be explicit.

6. **Add per-call timeout to the LM Studio client config** to fail fast on hung requests. Already done in `wiki_llm_helpers.py` via the OpenAI client's `timeout` parameter; verify the LM Studio server doesn't have a higher default timeout that overrides it.

7. **LLM script defaults** are now `--max-tokens 8000` (T123 classifier) and `--max-tokens 6000` (T123 detailed extractor). The empirical length diagnostic (10 articles at length percentiles 5/15/.../95) confirmed that 4000 is insufficient for ~15% of articles; 8000 + the helper's 3 retries (which the existing `no_json_in_response` / `json_decode` retry path already covers) gives near-zero failure rate.
