"""Stage 6 of the Wikipedia tier-extraction pipeline: cheap LLM classifier.

Reads the LLM-path candidates from `tmp/wiki_tier_candidates.parquet`
(those with `path == "llm"` and `tier_hints_v2` containing T1/T2/T3
hints) and asks an LLM (LM Studio, qwen3.5-9B) a short yes/no
question per article:

  "Is this article describing a real interstate conflict event?"

The classifier is designed to be cheap:
  - per-article tier_hint prepended to the prompt
  - 2-way parallel by default
  - Per-call timeout with exponential backoff retry
  - <think>...</think> tag stripping
  - Fallback to reasoning_content if content is empty (LM Studio
    reasoning-content bug)
  - Automatic per-article diagnostic write to
    tmp/wiki_t123_classifier_debug/<article_id>.json on failure

Articles classified as positive pass to stage 7
(`wiki_extract_llm_t123.py`) for detailed extraction. Negatives
are logged and dropped.

Inputs:
  - tmp/wiki_tier_candidates.parquet (from wiki_filter_candidates.py)
  - LM Studio at $LMSTUDIO_BASE_URL/v1
  - scripts/build/prompts/wiki_t123_classifier_v1.txt

Outputs:
  - tmp/wiki_t123_classifier_kept.jsonl
      Kept articles with classifier output
  - tmp/wiki_t123_classifier_rejected.jsonl
      Rejected articles with reason
  - tmp/wiki_t123_classifier_debug/<article_id>.json
      Per-article diagnostic (auto-written on failure)
  - tmp/wiki_t123_classifier_run.json
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
OUT_KEPT = TMP / "wiki_t123_classifier_kept.jsonl"
OUT_REJECTED = TMP / "wiki_t123_classifier_rejected.jsonl"
OUT_RUN = TMP / "wiki_t123_classifier_run.json"
DEBUG_DIR = TMP / "wiki_t123_classifier_debug"

LMSTUDIO_DEFAULT_URL = "http://192.168.86.18:1234/v1"
DEFAULT_MODEL = "nemotron-3-nano:4b"
# n_parallel defaults to 1 because qwen3.5-9B on this GPU serializes
# internally; n_parallel>1 causes LM Studio to deadlock. The model is
# large enough (9B + chain-of-thought) that 1 worker fully saturates
# the GPU.
DEFAULT_N_PARALLEL = 1

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_PATH = PROMPTS_DIR / "wiki_t123_classifier_v1.txt"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidates", default=str(CANDIDATES_PARQUET))
    p.add_argument("--prompt", default=str(PROMPT_PATH))
    p.add_argument("--out-kept", default=str(OUT_KEPT))
    p.add_argument("--out-rejected", default=str(OUT_REJECTED))
    p.add_argument("--run-meta", default=str(OUT_RUN))
    p.add_argument("--debug-dir", default=str(DEBUG_DIR))
    p.add_argument("--base-url", default=os.environ.get("LMSTUDIO_BASE_URL", LMSTUDIO_DEFAULT_URL))
    p.add_argument("--api-key", default=os.environ.get("LMSTUDIO_API_KEY", "lm-studio"))
    p.add_argument("--model", default=os.environ.get("LMSTUDIO_MODEL_NAME", DEFAULT_MODEL))
    p.add_argument(
        "--n-parallel",
        type=int,
        default=int(os.environ.get("LMSTUDIO_N_PARALLEL", str(DEFAULT_N_PARALLEL))),
    )
    p.add_argument(
        "--max-tokens",
        type=int,
        default=8000,
        help=(
            "Output token budget. Must comfortably exceed the model's "
            "chain-of-thought length. With qwen3.5-9B, 4000 is too low "
            "~15%% of the time (the model goes into long CoT and the "
            "JSON never gets emitted); 8000 covers all observed cases."
        ),
    )
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--per-call-timeout", type=float, default=600.0)
    p.add_argument(
        "--max-server-crashes",
        type=int,
        default=5,
        help=(
            "Bounded reconnect budget for LM Studio 'Model "
            "unloaded' / 'Channel Error' / 'tensor not allocated' "
            "crashes per article. After a server crash, the script "
            "sleeps, polls /v1/models until the model is reloaded, "
            "and retries. Bounded to this many recoveries; 0 "
            "disables recovery. Default 5."
        ),
    )
    p.add_argument(
        "--max-articles",
        type=int,
        default=0,
        help="Optional cap on input articles (0 = no cap).",
    )
    p.add_argument(
        "--min-confidence",
        type=float,
        default=0.4,
        help="Drop articles whose classifier confidence is below this floor.",
    )
    p.add_argument(
        "--smoke-test",
        type=int,
        default=0,
        help="Run on the first N articles only (0 = normal).",
    )
    return p.parse_args()


def _load_prompt(path: Path) -> tuple[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "{article}" not in content:
        raise SystemExit(f"Prompt must contain '{{article}}' placeholder: {path}")
    head, tail = content.split("{article}", 1)
    return head, tail


def _load_candidates(path: Path, max_articles: int) -> list[dict]:
    import pyarrow.parquet as pq
    t = pq.read_table(path)
    rows = t.to_pylist()
    # Restrict to LLM-path articles with T1/T2/T3 hints
    rows = [
        r for r in rows
        if r.get("path") == "llm"
        and any(t in {"T1", "T2", "T3"} for t in (r.get("tier_hints_v2") or []))
    ]
    if max_articles and max_articles > 0:
        rows = rows[:max_articles]
    return rows


def _build_article_text(article: dict, max_chars: int = 4000) -> str:
    parts: list[str] = []
    ab = (article.get("abstract") or "").strip()
    if ab:
        parts.append("ABSTRACT:\n" + ab)
    sx = (article.get("sections_excerpt") or "").strip()
    if sx:
        if sx.startswith("## Abstract"):
            m = re.search(r"^##\s(?!Abstract)", sx, re.MULTILINE)
            if m:
                sx = sx[m.start():]
        parts.append("ARTICLE BODY (excerpt):\n" + sx)
    text = "\n\n".join(parts)
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


def _parse_classifier_output(obj) -> dict | None:
    if not isinstance(obj, dict):
        return None
    is_event = obj.get("is_conflict_event")
    if not isinstance(is_event, bool):
        if isinstance(is_event, str):
            is_event = is_event.lower().strip() in {"true", "yes", "1"}
        else:
            return None
    tier_likely = obj.get("tier_likely")
    if tier_likely is not None and tier_likely not in {"T1", "T2", "T3", "T4", "T5"}:
        tier_likely = None
    countries = obj.get("countries") or []
    if not isinstance(countries, list):
        countries = []
    countries = [str(c).strip() for c in countries if c and isinstance(c, (str, int))]
    year = obj.get("year")
    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = None
        if year is not None and not (1800 <= year <= 2100):
            year = None
    try:
        conf = float(obj.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    return {
        "is_conflict_event": is_event,
        "tier_likely": tier_likely,
        "countries": countries,
        "year": year,
        "confidence": conf,
    }


# Import the shared helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wiki_llm_helpers import (
    call_chat_with_json_parse,
    log_failure,
    make_request_nonce,
    print_progress,
)


def main() -> int:
    args = _parse_args()

    for path in (args.candidates, args.prompt):
        if not Path(path).exists():
            print(f"Missing required input: {path}", file=sys.stderr)
            return 1

    prompt_head, prompt_tail = _load_prompt(Path(args.prompt))
    print(f"Prompt: {args.prompt}  head={len(prompt_head)} chars  tail={len(prompt_tail)} chars")
    print(f"  max_tokens: {args.max_tokens}  per-call-timeout: {args.per_call_timeout}s")
    print(f"  base-url:   {args.base_url}  model: {args.model}")

    articles = _load_candidates(Path(args.candidates), args.max_articles)
    if args.smoke_test:
        articles = articles[: args.smoke_test]
    n_total = len(articles)
    print(f"LLM-path articles to classify: {n_total:,}")

    try:
        from openai import OpenAI
    except ImportError as e:
        print("openai>=1.0 is required", file=sys.stderr)
        raise SystemExit(1) from e

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    try:
        models = client.models.list()
        ids = [m.id for m in getattr(models, "data", [])]
        chosen = next((i for i in ids if args.model.lower() in i.lower() or i.lower().endswith("/" + args.model.lower())), ids[0] if ids else args.model)
        print(f"LM Studio OK: {len(ids)} model(s); using '{chosen}'")
    except Exception as e:
        print(f"Could not reach LM Studio at {args.base_url}: {e}", file=sys.stderr)
        return 1

    Path(args.out_kept).parent.mkdir(parents=True, exist_ok=True)
    Path(args.debug_dir).mkdir(parents=True, exist_ok=True)
    # Append mode if file has prior content; protects against re-runs
    kept_mode = "a" if Path(args.out_kept).exists() and Path(args.out_kept).stat().st_size > 0 else "w"
    rej_mode = "a" if Path(args.out_rejected).exists() and Path(args.out_rejected).stat().st_size > 0 else "w"
    # buffering=1 = line-buffered, so a SIGTERM or crash loses at most
    # the one in-flight line (default block buffering can lose 4-8 KB
    # = dozens of classifications).
    out_kept = open(args.out_kept, kept_mode, encoding="utf-8", buffering=1)
    out_rej = open(args.out_rejected, rej_mode, encoding="utf-8", buffering=1)

    n_kept = 0
    n_rejected = 0
    n_failed = 0
    n_server_crashes = 0
    t_start = time.time()
    done = 0

    def _process(art: dict) -> tuple[dict, dict | None, str | None, dict]:
        text = _build_article_text(art)
        tier_hint = (art.get("tier_hints_v2") or ["T1"])[0] if art.get("tier_hints_v2") else "T1"
        user_msg = (
            prompt_head
            + f"\n\n[tier_hint: {tier_hint}]\n\n"
            + text
            + prompt_tail
        )
        messages = [
            {"role": "system", "content": "You are a precise information-extraction assistant. Respond only with a single JSON object."},
            {"role": "user", "content": user_msg},
        ]
        parsed, debug = call_chat_with_json_parse(
            client,
            model=chosen,
            messages=messages,
            temperature=args.temperature,
            seed=args.seed,
            max_tokens=args.max_tokens,
            timeout=args.per_call_timeout,
            request_nonce=make_request_nonce(),
            max_server_crashes=args.max_server_crashes,
        )
        out = None
        if parsed is not None:
            out = _parse_classifier_output(parsed)
            if out is None:
                return art, None, "bad_classifier_output", debug
        return art, out, debug.get("error"), debug

    try:
        with cf.ThreadPoolExecutor(max_workers=args.n_parallel) as ex:
            futures = {ex.submit(_process, a): a for a in articles}
            for fut in cf.as_completed(futures):
                art, parsed, err, debug = fut.result()
                done += 1
                if err is not None or parsed is None:
                    n_failed += 1
                    n_server_crashes += int(debug.get("server_crash_count", 0) or 0)
                    out_rej.write(json.dumps({
                        "article_id": int(art["identifier"]),
                        "article_title": art.get("name") or "",
                        "reason": err or "no_parse",
                    }, ensure_ascii=False) + "\n")
                    log_failure(
                        Path(args.debug_dir),
                        art["identifier"],
                        raw_content=debug.get("raw_content", ""),
                        raw_reasoning=debug.get("raw_reasoning", ""),
                        parsed=debug.get("block"),
                        error=err or "no_parse",
                        block=debug.get("block"),
                        extra={"article_title": art.get("name"), "tier_hint": (art.get("tier_hints_v2") or [None])[0]},
                    )
                else:
                    reject_reason = None
                    if not parsed["is_conflict_event"]:
                        reject_reason = "not_conflict_event"
                    elif parsed["tier_likely"] not in {"T1", "T2", "T3"}:
                        reject_reason = f"tier_outside_T123:{parsed['tier_likely']}"
                    elif len(parsed["countries"]) < 2:
                        reject_reason = f"fewer_than_2_countries:{len(parsed['countries'])}"
                    elif parsed["year"] is None:
                        reject_reason = "no_year"
                    elif parsed["confidence"] < args.min_confidence:
                        reject_reason = f"low_confidence:{parsed['confidence']}"
                    if reject_reason:
                        out_rej.write(json.dumps({
                            "article_id": int(art["identifier"]),
                            "article_title": art.get("name") or "",
                            "reason": reject_reason,
                            "classifier_output": parsed,
                        }, ensure_ascii=False) + "\n")
                        n_rejected += 1
                    else:
                        out_kept.write(json.dumps({
                            "article_id": int(art["identifier"]),
                            "article_title": art.get("name") or "",
                            "tier_hints_v2": art.get("tier_hints_v2", []),
                            "matched_canonicals": art.get("matched_canonicals", []),
                            "matched_tiers": art.get("matched_tiers", []),
                            "abstract": art.get("abstract") or "",
                            "sections_excerpt": art.get("sections_excerpt") or "",
                            "classifier": parsed,
                        }, ensure_ascii=False) + "\n")
                        n_kept += 1
                if done % 1 == 0 or done == n_total:
                    elapsed = time.time() - t_start
                    rate = done / max(elapsed, 1e-6)
                    eta = (n_total - done) / max(rate, 1e-6)
                    print_progress(
                        done=done,
                        total=n_total,
                        n_kept=n_kept,
                        n_rejected=n_rejected,
                        n_failed=n_failed,
                        extra=f"rate={rate:.1f}/s eta={eta/60:.1f}m crashes={n_server_crashes}",
                    )
    finally:
        out_kept.close()
        out_rej.close()

    elapsed = time.time() - t_start
    run_meta = {
        "n_articles_in": n_total,
        "n_kept": n_kept,
        "n_rejected": n_rejected,
        "n_failed": n_failed,
        "server_crashes_total": n_server_crashes,
        "elapsed_seconds": round(elapsed, 1),
        "model": chosen,
        "base_url": args.base_url,
        "min_confidence": args.min_confidence,
        "max_tokens": args.max_tokens,
        "per_call_timeout": args.per_call_timeout,
        "max_server_crashes": args.max_server_crashes,
        "n_parallel": args.n_parallel,
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
    print(f"Debug: {args.debug_dir}/<article_id>.json")
    print(f"Meta:  {args.run_meta}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
