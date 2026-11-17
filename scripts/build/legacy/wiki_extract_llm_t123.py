"""Stage 8 of the Wikipedia tier-extraction pipeline: detailed LLM event extractor.

Reads the *kept* articles from the stage 6 LLM 0/1 filter
(`tmp/wiki_t123_filter_kept.jsonl`) and asks the LLM to extract
structured T1/T2/T3 event records (year, initiator, target, confidence).

v27.0-aligned:
  T1 = 1, T2 = 2, T3 = 3
  Labels: "T1-Diplomatic Crisis", "T2-Economic Coercion",
          "T3-Proxy/Indirect Military"

The tier+explanation pass (stage 7) runs alongside this and produces
`tmp/wiki_t123_tier.jsonl`. The correlate step (`wiki_correlate_t123.py`)
joins them and writes `tmp/wiki_t123_events.csv` for the aggregator.

False-positive guard + tier-boundary rules are in the prompt. The
prompt also makes the LLM aware of the v27.0 modifier axes
(Attribution, Integration, Stakes, Intent) but only the base tier is
emitted in the output (modifier axes are out of scope for this round).

Reliability features (see scripts/build/wiki_llm_helpers.py):
  - Per-call timeout with exponential backoff retry
  - <think>...</think> tag stripping
  - Fallback to reasoning_content if content is empty
  - Automatic per-article diagnostic write to
    tmp/wiki_t123_debug/<article_id>.json on every failure

Inputs:
  - tmp/wiki_t123_filter_kept.jsonl (from stage 6 LLM 0/1 filter)
  - tmp/wiki_tier_candidates.parquet (for the article text)
  - scripts/build/prompts/wiki_t123_v2.txt
  - Ollama at $OLLAMA_BASE_URL/v1

Outputs:
  - tmp/wiki_t123_extracted.jsonl
      One row per extracted event.
  - tmp/wiki_t123_failed.jsonl
      Per-article failures.
  - tmp/wiki_t123_debug/<article_id>.json
      Per-article raw-response diagnostic (auto-written on failure).
  - tmp/wiki_t123_run.json
      Run metadata.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"

KEPT_JSONL = TMP / "wiki_t123_filter_kept.jsonl"
TIER_PARQUET = TMP / "wiki_tier_candidates.parquet"
OUT_JSONL = TMP / "wiki_t123_extracted.jsonl"
FAILED_JSONL = TMP / "wiki_t123_failed.jsonl"
RUN_JSON = TMP / "wiki_t123_run.json"
DEBUG_DIR = TMP / "wiki_t123_debug"

OLLAMA_DEFAULT_URL = "http://192.168.86.18:1234/v1"
DEFAULT_MODEL = "nemotron-3-nano:4b"
# n_parallel default: 4 for nemotron-3-nano (small model, Ollama handles
# parallelism well). User can raise/lower via env var.
DEFAULT_N_PARALLEL = 4

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_PATH = PROMPTS_DIR / "wiki_t123_v2.txt"

# v27.0 tier scheme
VALID_TIERS = {"T1", "T2", "T3"}
TIER_INFO = {
    "T1": {"tier_label": "T1-Diplomatic Crisis",       "hostlev": 1},
    "T2": {"tier_label": "T2-Economic Coercion",       "hostlev": 2},
    "T3": {"tier_label": "T3-Proxy/Indirect Military", "hostlev": 3},
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kept", default=str(KEPT_JSONL))
    p.add_argument("--tier-parquet", default=str(TIER_PARQUET))
    p.add_argument("--prompt", default=str(PROMPT_PATH))
    p.add_argument("--out", default=str(OUT_JSONL))
    p.add_argument("--failed", default=str(FAILED_JSONL))
    p.add_argument("--run-meta", default=str(RUN_JSON))
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
        default=int(
            os.environ.get("OLLAMA_N_PARALLEL")
            or os.environ.get("LMSTUDIO_N_PARALLEL")
            or str(DEFAULT_N_PARALLEL)
        ),
    )
    p.add_argument("--max-tokens", type=int, default=6000)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--per-call-timeout", type=float, default=600.0)
    p.add_argument(
        "--max-server-crashes",
        type=int,
        default=5,
        help=(
            "Bounded reconnect budget for Ollama 'Model "
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
        help="Drop events with confidence below this floor.",
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


def _load_articles(path: Path, max_articles: int) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if max_articles and max_articles > 0:
        out = out[:max_articles]
    return out


def _load_article_texts(parquet_path: str) -> dict[int, dict]:
    """{article_id: {name, abstract, sections_excerpt}}."""
    if not Path(parquet_path).exists():
        return {}
    try:
        import pyarrow.parquet as pq
    except ImportError as e:
        print("pyarrow required", file=sys.stderr)
        raise SystemExit(1) from e
    t = pq.read_table(parquet_path, columns=["identifier", "name", "abstract", "sections_excerpt"])
    out: dict[int, dict] = {}
    for r in t.to_pylist():
        out[int(r["identifier"])] = {
            "name": r.get("name") or "",
            "abstract": r.get("abstract") or "",
            "sections_excerpt": r.get("sections_excerpt") or "",
        }
    return out


def _build_article_text(article: dict, max_chars: int = 6000) -> str:
    parts: list[str] = []
    ab = (article.get("abstract") or "").strip()
    if ab:
        parts.append("ABSTRACT:\n" + ab)
    sx = (article.get("sections_excerpt") or "").strip()
    if sx:
        if sx.startswith("## Abstract"):
            import re as _re
            m = _re.search(r"^##\s(?!Abstract)", sx, _re.MULTILINE)
            if m:
                sx = sx[m.start():]
        parts.append("ARTICLE BODY (excerpt):\n" + sx)
    text = "\n\n".join(parts)
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


def _normalize_event(raw: dict, article: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    tier = raw.get("tier")
    if tier not in VALID_TIERS:
        return None
    year = raw.get("year")
    if year is not None:
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = None
        if year is not None and not (1800 <= year <= 2100):
            year = None
    initiator = raw.get("initiator_country")
    target = raw.get("target_country")
    if isinstance(initiator, str):
        initiator = initiator.strip() or None
    else:
        initiator = None
    if isinstance(target, str):
        target = target.strip() or None
    else:
        target = None
    if not initiator and not target:
        return None
    try:
        conf = float(raw.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    info = TIER_INFO[tier]
    return {
        "article_id": int(article["article_id"]),
        "article_title": str(article.get("article_title") or ""),
        "infobox_name": "",
        "year": year,
        "start_year": year,
        "end_year": year,
        "tier": tier,
        "hostlev": info["hostlev"],
        "tier_label": info["tier_label"],
        "source": f"WIKI_{tier}",
        "initiator_country": initiator,
        "initiator_qid": None,
        "initiator_gwno": None,
        "target_country": target,
        "target_qid": None,
        "target_gwno": None,
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

    for path in (args.kept, args.prompt, args.tier_parquet):
        if not Path(path).exists():
            print(f"Missing required input: {path}", file=sys.stderr)
            return 1

    prompt_head, prompt_tail = _load_prompt(Path(args.prompt))
    print(f"Prompt: {args.prompt}  head={len(prompt_head)} chars  tail={len(prompt_tail)} chars")
    print(f"  max_tokens: {args.max_tokens}  per-call-timeout: {args.per_call_timeout}s")
    print(f"  base-url:   {args.base_url}  model: {args.model}")

    articles = _load_articles(Path(args.kept), args.max_articles)
    if args.smoke_test:
        articles = articles[: args.smoke_test]
    n_total = len(articles)
    print(f"Articles to extract from: {n_total:,}")

    article_texts = _load_article_texts(args.tier_parquet)
    print(f"Article texts loaded: {len(article_texts):,}")

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
        print(f"Ollama OK: {len(ids)} model(s); using '{chosen}'")
    except Exception as e:
        print(f"Could not reach Ollama at {args.base_url}: {e}", file=sys.stderr)
        return 1

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.debug_dir).mkdir(parents=True, exist_ok=True)
    out_mode = "a" if Path(args.out).exists() and Path(args.out).stat().st_size > 0 else "w"
    failed_mode = "a" if Path(args.failed).exists() and Path(args.failed).stat().st_size > 0 else "w"
    out_f = open(args.out, out_mode, encoding="utf-8")
    failed_f = open(args.failed, failed_mode, encoding="utf-8")

    n_events = 0
    n_with_events = 0
    n_failed = 0
    n_server_crashes = 0
    t_start = time.time()
    done = 0

    def _process(art: dict) -> tuple[dict, list[dict], str | None, dict]:
        # Look up the full article text in the parquet (the filter kept
        # JSONL only has the article_id, not the text).
        article_id = int(art.get("article_id") or 0)
        text_article = article_texts.get(article_id, {})
        if not text_article:
            # Fallback to anything in the kept row
            text_article = {
                "abstract": art.get("abstract", ""),
                "sections_excerpt": art.get("sections_excerpt", ""),
            }
        text = _build_article_text(text_article)
        classifier = art.get("classifier") or {}
        tier_hint = classifier.get("tier_likely") or "T1"
        countries_hint = classifier.get("countries") or []
        year_hint = classifier.get("year")
        hint_block = f"\n\n[hint from classifier: tier={tier_hint}, countries={countries_hint}, year={year_hint}]\n"
        user_msg = prompt_head + hint_block + text + prompt_tail
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
        events: list[dict] = []
        if parsed is not None:
            events_raw = parsed.get("events") if isinstance(parsed, dict) else None
            if isinstance(events_raw, list):
                for ev in events_raw:
                    ne = _normalize_event(ev, art)
                    if ne is not None:
                        events.append(ne)
            elif events_raw is None:
                # The model didn't return an "events" array; record as a soft failure
                return art, [], "no_events_array", debug
            else:
                return art, [], f"bad_events_type:{type(events_raw).__name__}", debug
        return art, events, debug.get("error"), debug

    try:
        with cf.ThreadPoolExecutor(max_workers=args.n_parallel) as ex:
            futures = {ex.submit(_process, a): a for a in articles}
            for fut in cf.as_completed(futures):
                art, events, err, debug = fut.result()
                done += 1
                if err is not None:
                    n_failed += 1
                    n_server_crashes += int(debug.get("server_crash_count", 0) or 0)
                    failed_f.write(json.dumps({
                        "article_id": art.get("article_id"),
                        "article_title": art.get("article_title"),
                        "error": err,
                    }, ensure_ascii=False) + "\n")
                    log_failure(
                        Path(args.debug_dir),
                        art.get("article_id"),
                        raw_content=debug.get("raw_content", ""),
                        raw_reasoning=debug.get("raw_reasoning", ""),
                        parsed=debug.get("block"),
                        error=err,
                        block=debug.get("block"),
                        extra={"article_title": art.get("article_title")},
                    )
                else:
                    emitted = 0
                    for ev in events:
                        if ev.get("confidence", 0.0) < args.min_confidence:
                            continue
                        out_f.write(json.dumps(ev, ensure_ascii=False) + "\n")
                        n_events += 1
                        emitted += 1
                    if emitted > 0:
                        n_with_events += 1
                if done % 1 == 0 or done == n_total:
                    elapsed = time.time() - t_start
                    rate = done / max(elapsed, 1e-6)
                    eta = (n_total - done) / max(rate, 1e-6)
                    print_progress(
                        done=done,
                        total=n_total,
                        n_kept=n_with_events,
                        n_rejected=0,
                        n_failed=n_failed,
                        extra=f"events={n_events} rate={rate:.1f}/s eta={eta/60:.1f}m crashes={n_server_crashes}",
                    )
    finally:
        out_f.close()
        failed_f.close()

    elapsed = time.time() - t_start
    run_meta = {
        "n_articles_in": n_total,
        "n_articles_with_events": n_with_events,
        "n_events_emitted": n_events,
        "n_articles_failed": n_failed,
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
    print(f"Wrote {args.out} ({n_events:,} events from {n_with_events:,} articles)")
    print(f"Failed: {n_failed} -> {args.failed}")
    print(f"Debug:  {args.debug_dir}/<article_id>.json")
    print(f"Meta:   {args.run_meta}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
