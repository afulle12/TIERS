"""Stage 3 of the Wikipedia tier-extraction pipeline: LLM 0/1 filter.

Reads the LLM-path candidates from `tmp/wiki_tier_candidates.parquet`
(those with `path == "llm"`) and asks the LLM (Ollama, nemotron-3-nano:4b
by default) a short yes/no question PER BATCH OF {batch_size} ARTICLES.

The model is given a rich conflict-keyword vocabulary as a hint, then
must judge whether the article contains a conflict or dispute between
nation states. The output is 0 (no such conflict) or 1 (yes) per article.

Articles classified as 1 are passed to stage 4 (combined extraction).
Articles classified as 0 are logged and dropped.

The prompt is BROADER than the legacy t123 filter: it admits diplomatic
friction, sanctions, proxy support, border clashes, AND full-scale war
under the same 0/1 gate, since the tier is now assigned downstream by
stage 4 in a single LLM call.

Batch size default is 3 (small enough for nemotron-nano to handle in
one prompt, large enough to amortize per-call overhead).
n_parallel default is 5 (conservative; tune via OLLAMA_N_PARALLEL env).

Inputs:
  - tmp/wiki_tier_candidates.parquet (from wiki_filter_candidates.py)
  - Ollama at $OLLAMA_BASE_URL/v1
  - scripts/build/prompts/wiki_t01_filter_v1.txt

Outputs:
  - tmp/wiki_t01_filter_kept.jsonl
      Kept articles (is_conflict_event=1) with the parsed output
  - tmp/wiki_t01_filter_rejected.jsonl
      Rejected articles with reason
  - tmp/wiki_t01_filter_run.json
      Run metadata
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"

CANDIDATES_PARQUET = TMP / "wiki_tier_candidates.parquet"
OUT_KEPT = TMP / "wiki_t01_filter_kept.jsonl"
OUT_REJECTED = TMP / "wiki_t01_filter_rejected.jsonl"
OUT_RUN = TMP / "wiki_t01_filter_run.json"
DEBUG_DIR = TMP / "wiki_t01_filter_debug"

OLLAMA_DEFAULT_URL = "http://192.168.86.18:1234/v1"
DEFAULT_MODEL = "nemotron-3-nano:4b"
DEFAULT_N_PARALLEL = 5
DEFAULT_BATCH_SIZE = 3
# nemotron-3-nano-4b uses chain-of-thought reasoning internally and can
# consume thousands of tokens for thinking before emitting the JSON.
# max_tokens=80 is way too low and the model truncates mid-thought
# (finish_reason=length, content=""). The actual JSON output for a
# 3-article batched 0/1 prompt is ~50 chars; we budget 2000 to leave
# headroom for CoT. 4000-8000 is safer if you see truncations; reduce
# to 200 if you want to fail fast on non-thinking models.
DEFAULT_MAX_TOKENS = 2000

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_PATH = PROMPTS_DIR / "wiki_t01_filter_v1.txt"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidates", default=str(CANDIDATES_PARQUET))
    p.add_argument("--prompt", default=str(PROMPT_PATH))
    p.add_argument("--out-kept", default=str(OUT_KEPT))
    p.add_argument("--out-rejected", default=str(OUT_REJECTED))
    p.add_argument("--run-meta", default=str(OUT_RUN))
    p.add_argument("--debug-dir", default=str(DEBUG_DIR))
    p.add_argument(
        "--base-url",
        default=os.environ.get(
            "OLLAMA_BASE_URL",
            os.environ.get("LMSTUDIO_BASE_URL", OLLAMA_DEFAULT_URL),
        ),
    )
    p.add_argument(
        "--api-key",
        default=os.environ.get("OLLAMA_API_KEY", os.environ.get("LMSTUDIO_API_KEY", "ollama")),
    )
    p.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", os.environ.get("LMSTUDIO_MODEL_NAME", DEFAULT_MODEL)),
    )
    p.add_argument(
        "--n-parallel",
        type=int,
        default=int(os.environ.get("OLLAMA_N_PARALLEL", str(DEFAULT_N_PARALLEL))),
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=int(os.environ.get("OLLAMA_BATCH_SIZE", str(DEFAULT_BATCH_SIZE))),
        help="Articles per LLM prompt (default 3).",
    )
    p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--per-call-timeout", type=float, default=120.0)
    p.add_argument("--max-server-crashes", type=int, default=5)
    p.add_argument(
        "--max-articles",
        type=int,
        default=0,
        help="Optional cap on input articles (0 = no cap).",
    )
    p.add_argument(
        "--smoke-test",
        type=int,
        default=0,
        help="Run on the first N articles only (0 = normal).",
    )
    return p.parse_args()


def _load_prompt_template(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _load_candidates(path: Path, max_articles: int) -> list[dict]:
    import pyarrow.parquet as pq
    t = pq.read_table(path)
    rows = t.to_pylist()
    rows = [r for r in rows if r.get("path") == "llm"]
    if max_articles and max_articles > 0:
        rows = rows[:max_articles]
    return rows


def _build_article_text(article: dict, max_chars: int = 2000) -> str:
    parts: list[str] = []
    ab = (article.get("abstract") or "").strip()
    if ab:
        parts.append(ab)
    sx = (article.get("sections_excerpt") or "").strip()
    if sx:
        parts.append(sx)
    text = "\n\n".join(parts)
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


def _build_batched_prompt(template: str, batch: list[dict]) -> str:
    """Insert the {batch_size} articles into the template, in order."""
    n = len(batch)
    head = template.replace("{batch_size}", str(n))
    blocks: list[str] = []
    for idx, art in enumerate(batch, start=1):
        art_id = art.get("identifier", "?")
        text = _build_article_text(art)
        blocks.append(f"\n\nARTICLE {idx} (id={art_id}):\n{text}\n")
    return head + "".join(blocks)


def _extract_json_array(text: str) -> str | None:
    """Find the first balanced top-level JSON array substring."""
    if not text:
        return None
    s = text.strip()
    start = s.find("[")
    if start < 0:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    return None


def _parse_results_output(raw: str, expected_n: int) -> list[dict] | None:
    """Parse the new `{"results": [1, 0, 1, ...]}` output format.

    Returns a list of {"i": int, "v": 0|1} of length expected_n, or None.
    Order is preserved from the LLM output. Falls back to the legacy
    `[{i, v}, ...]` array form if the object form isn't found.
    """
    if not raw:
        return None
    s = raw.strip()
    # Try object form first
    obj = None
    try:
        # Find the first balanced top-level object
        start = s.find("{")
        if start >= 0:
            depth = 0
            in_str = False
            esc = False
            for i in range(start, len(s)):
                c = s[i]
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        in_str = False
                    continue
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(s[start:i + 1])
                        except json.JSONDecodeError:
                            obj = None
                        break
    except Exception:
        obj = None
    if obj is not None and isinstance(obj, dict) and isinstance(obj.get("results"), list):
        arr = obj["results"]
    else:
        # Fall back to legacy array form
        block = _extract_json_array(raw)
        if block is None:
            return None
        try:
            arr = json.loads(block)
        except json.JSONDecodeError:
            return None
    if not isinstance(arr, list) or len(arr) != expected_n:
        return None
    out: list[dict] = []
    for j, item in enumerate(arr):
        if isinstance(item, bool):
            v = 1 if item else 0
            i = j
        elif isinstance(item, int):
            v = 1 if item == 1 else 0 if item == 0 else None
            i = j
            if v is None:
                return None
        elif isinstance(item, str):
            t = item.strip().lower()
            if t in {"1", "true", "yes"}:
                v = 1
            elif t in {"0", "false", "no"}:
                v = 0
            else:
                return None
            i = j
        elif isinstance(item, dict):
            i = item.get("i")
            v = item.get("v")
            if not isinstance(i, int):
                return None
            if isinstance(v, str):
                v = v.strip().lower()
                v = 1 if v in {"1", "true", "yes"} else 0 if v in {"0", "false", "no"} else None
            if v not in (0, 1):
                return None
        else:
            return None
        out.append({"i": i, "v": v})
    return out


sys.path.insert(0, str(Path(__file__).resolve().parent))
from wiki_llm_helpers import (
    _wrap_openai_call,
    log_failure,
    make_request_nonce,
    print_progress,
    strip_think_tags,
    wait_for_server_ready,
)


def _call_ollama_batch(
    client,
    *,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    seed: int,
    timeout: float,
    max_retries: int = 3,
    max_server_crashes: int = 5,
) -> tuple[str | None, dict]:
    """Call Ollama chat.completions.create for one batch. Returns
    (raw_text, debug) where raw_text is the model output (cleaned of
    think tags), or None on failure. Retries with exponential backoff.
    """
    debug: dict = {
        "raw_content": "",
        "raw_reasoning": "",
        "elapsed_seconds": 0.0,
        "error": None,
        "finish_reason": None,
        "server_crash_count": 0,
    }
    t0 = time.time()
    messages = [
        {"role": "system", "content": "You are a precise information-extraction assistant. Respond only with a JSON array."},
        {"role": "user", "content": prompt},
    ]

    for server_round in range(max_server_crashes + 1):
        for attempt in range(max_retries):
            resp, err = _wrap_openai_call(
                client,
                model=model,
                messages=messages,
                temperature=temperature,
                seed=seed,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            if err is not None:
                debug["error"] = err
                # Check for server crash
                if any(p in err.lower() for p in ("model unloaded", "channel error", "connection error", "server disconnected", "tensor not allocated", "temporarily unavailable")):
                    break  # outer loop handles this
                time.sleep(1.5 * (attempt + 1))
                continue
            msg = resp.choices[0].message
            content = (msg.content or "") if msg else ""
            reasoning = (getattr(msg, "reasoning_content", "") or "") if msg else ""
            debug["raw_content"] = content
            debug["raw_reasoning"] = reasoning
            debug["finish_reason"] = resp.choices[0].finish_reason
            if content.strip():
                cleaned = strip_think_tags(content)
            else:
                cleaned = strip_think_tags(reasoning)
            if not cleaned.strip():
                debug["error"] = "empty_response"
                time.sleep(1.5 * (attempt + 1))
                continue
            debug["elapsed_seconds"] = round(time.time() - t0, 2)
            return cleaned, debug
        # If we reach here and last err was a server crash, recover
        last_err = debug.get("error") or ""
        if not any(p in last_err.lower() for p in ("model unloaded", "channel error", "connection error", "server disconnected", "tensor not allocated", "temporarily unavailable")):
            break
        debug["server_crash_count"] += 1
        if debug["server_crash_count"] > max_server_crashes:
            debug["error"] = f"server_crash_exhausted({max_server_crashes})"
            break
        time.sleep(15.0)
        wait_for_server_ready(client, model_id=model, max_wait=120.0)

    debug["elapsed_seconds"] = round(time.time() - t0, 2)
    return None, debug


def main() -> int:
    args = _parse_args()

    for path in (args.candidates, args.prompt):
        if not Path(path).exists():
            print(f"Missing required input: {path}", file=sys.stderr)
            return 1

    template = _load_prompt_template(Path(args.prompt))
    print(f"Prompt: {args.prompt}  ({len(template)} chars)")
    print(f"  base-url: {args.base_url}  model: {args.model}")
    print(f"  batch-size: {args.batch_size}  n-parallel: {args.n_parallel}  max-tokens: {args.max_tokens}")

    articles = _load_candidates(Path(args.candidates), args.max_articles)
    if args.smoke_test:
        articles = articles[: args.smoke_test]
    n_total = len(articles)
    print(f"LLM-path articles to classify: {n_total:,}")
    if n_total == 0:
        print("No articles to process. Exiting.")
        return 0

    # Build batches
    batches: list[list[dict]] = []
    for i in range(0, n_total, args.batch_size):
        batches.append(articles[i : i + args.batch_size])
    n_batches = len(batches)
    print(f"  -> {n_batches:,} batches of {args.batch_size}")

    try:
        from openai import OpenAI
    except ImportError as e:
        print("openai>=1.0 is required", file=sys.stderr)
        raise SystemExit(1) from e

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    try:
        models = client.models.list()
        ids = [m.id for m in getattr(models, "data", [])]
        chosen = next(
            (i for i in ids if args.model.lower() in i.lower() or i.lower().endswith("/" + args.model.lower())),
            ids[0] if ids else args.model,
        )
        print(f"Ollama OK: {len(ids)} model(s); using '{chosen}'")
    except Exception as e:
        print(f"Could not reach Ollama at {args.base_url}: {e}", file=sys.stderr)
        return 1

    Path(args.out_kept).parent.mkdir(parents=True, exist_ok=True)
    Path(args.debug_dir).mkdir(parents=True, exist_ok=True)
    kept_mode = "a" if Path(args.out_kept).exists() and Path(args.out_kept).stat().st_size > 0 else "w"
    rej_mode = "a" if Path(args.out_rejected).exists() and Path(args.out_rejected).stat().st_size > 0 else "w"
    out_kept = open(args.out_kept, kept_mode, encoding="utf-8", buffering=1)
    out_rej = open(args.out_rejected, rej_mode, encoding="utf-8", buffering=1)

    n_kept = 0
    n_rejected = 0
    n_failed = 0
    n_server_crashes = 0
    t_start = time.time()
    done_articles = 0
    done_batches = 0

    def _process_batch(batch: list[dict]) -> tuple[list[dict], list[dict], int, int]:
        """Process one batch. Returns (kept_rows, rejected_rows, n_fail, n_crashes)."""
        prompt = _build_batched_prompt(template, batch)
        cleaned, debug = _call_ollama_batch(
            client,
            model=chosen,
            prompt=prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            seed=args.seed,
            timeout=args.per_call_timeout,
            max_server_crashes=args.max_server_crashes,
        )
        kept_rows: list[dict] = []
        rej_rows: list[dict] = []
        n_fail = 0
        n_crashes = int(debug.get("server_crash_count", 0) or 0)
        if cleaned is None:
            n_fail = len(batch)
            for art in batch:
                log_failure(
                    Path(args.debug_dir),
                    art.get("identifier"),
                    raw_content=debug.get("raw_content", ""),
                    raw_reasoning=debug.get("raw_reasoning", ""),
                    parsed=None,
                    error=debug.get("error") or "no_response",
                    block=None,
                    extra={"article_title": art.get("name")},
                )
            return kept_rows, rej_rows, n_fail, n_crashes
        parsed = _parse_results_output(cleaned, len(batch))
        if parsed is None:
            n_fail = len(batch)
            for art in batch:
                log_failure(
                    Path(args.debug_dir),
                    art.get("identifier"),
                    raw_content=debug.get("raw_content", ""),
                    raw_reasoning=debug.get("raw_reasoning", ""),
                    parsed=cleaned[:500],
                    error="bad_array_output",
                    block=cleaned[:500],
                    extra={"article_title": art.get("name")},
                )
            return kept_rows, rej_rows, n_fail, n_crashes
        for item, art in zip(parsed, batch):
            v = item.get("v")
            row = {
                "article_id": int(art["identifier"]),
                "article_title": art.get("name") or "",
                "batch_idx": item.get("i"),
                "is_conflict_event": int(v),
                "model": chosen,
                "elapsed_s": round(debug.get("elapsed_seconds", 0.0) / max(len(batch), 1), 3),
            }
            if v == 1:
                kept_rows.append(row)
            else:
                rej_rows.append({**row, "reason": "llm_says_no"})
        return kept_rows, rej_rows, n_fail, n_crashes

    try:
        with cf.ThreadPoolExecutor(max_workers=args.n_parallel) as ex:
            futures = {ex.submit(_process_batch, b): b for b in batches}
            for fut in cf.as_completed(futures):
                kept_rows, rej_rows, n_fail, n_crashes = fut.result()
                done_batches += 1
                done_articles += len(kept_rows) + len(rej_rows) + n_fail
                n_kept += len(kept_rows)
                n_rejected += len(rej_rows)
                n_failed += n_fail
                n_server_crashes += n_crashes
                for r in kept_rows:
                    out_kept.write(json.dumps(r, ensure_ascii=False) + "\n")
                for r in rej_rows:
                    out_rej.write(json.dumps(r, ensure_ascii=False) + "\n")
                if done_batches % 1 == 0 or done_batches == n_batches:
                    elapsed = time.time() - t_start
                    rate = done_articles / max(elapsed, 1e-6)
                    eta = (n_total - done_articles) / max(rate, 1e-6)
                    print_progress(
                        done=done_articles,
                        total=n_total,
                        n_kept=n_kept,
                        n_rejected=n_rejected,
                        n_failed=n_failed,
                        extra=f"batches={done_batches}/{n_batches} rate={rate:.1f}/s eta={eta/60:.1f}m crashes={n_server_crashes}",
                    )
    finally:
        out_kept.close()
        out_rej.close()

    elapsed = time.time() - t_start
    run_meta = {
        "n_articles_in": n_total,
        "n_batches": n_batches,
        "n_kept": n_kept,
        "n_rejected": n_rejected,
        "n_failed": n_failed,
        "server_crashes_total": n_server_crashes,
        "elapsed_seconds": round(elapsed, 1),
        "model": chosen,
        "base_url": args.base_url,
        "batch_size": args.batch_size,
        "n_parallel": args.n_parallel,
        "max_tokens": args.max_tokens,
        "per_call_timeout": args.per_call_timeout,
        "temperature": args.temperature,
        "seed": args.seed,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - elapsed)),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(args.run_meta, "w") as f:
        json.dump(run_meta, f, indent=2)
    print()
    print("=" * 60)
    print(f"Wrote {args.out_kept} ({n_kept:,} kept)")
    print(f"Wrote {args.out_rejected} ({n_rejected + n_failed:,} rejected/failed)")
    print(f"Debug:  {args.debug_dir}/<article_id>.json")
    print(f"Meta:   {args.run_meta}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
