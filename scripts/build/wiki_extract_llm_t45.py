"""Stage 4 of the Wikipedia tier-extraction pipeline: combined extraction.

For each article that passed the stage 3 0/1 filter, this stage calls
the LLM ONCE and asks for everything the aggregator needs:

  - tier (T1 / T2 / T3 / T4 / T5 / NONE)
  - explanation (one short sentence, applied to every expanded row)
  - start_year, end_year (both nullable; used to expand multi-year
    wars into one row per year in the aggregator)
  - pairs: every directed (initiator, target) dyad that was at
    conflict, each with a confidence and an "implied" flag
    (implied pairs get a -0.2 confidence discount in the aggregator)

Replaces the legacy two-call design (tier classifier + event
extractor + correlate) with a single, richer LLM call. The LLM is the
sole tier authority — there is no structured infobox path.

n_parallel default is 5 (conservative; tune via OLLAMA_N_PARALLEL env).

Inputs:
  - tmp/wiki_t01_filter_kept.jsonl  (kept articles from stage 3)
  - tmp/wiki_tier_candidates.parquet (for the article text)
  - Ollama at $OLLAMA_BASE_URL/v1
  - scripts/build/prompts/wiki_t45_extract_v1.txt

Outputs:
  - tmp/wiki_t45_extracted.jsonl
      One row per article (even if tier is NONE):
        {article_id, article_title, tier, hostlev, tier_label,
         start_year, end_year, explanation, model,
         pairs: [{initiator, target, confidence, implied}]}
  - tmp/wiki_t45_failed.jsonl
      Articles where the LLM call returned no parseable JSON
  - tmp/wiki_t45_run.json
      Run metadata
  - tmp/wiki_t45_debug/<article_id>.json
      Per-article diagnostic (raw response, parsed output, error)
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

KEPT_JSONL = TMP / "wiki_t01_filter_kept.jsonl"
TIER_PARQUET = TMP / "wiki_tier_candidates.parquet"
OUT_JSONL = TMP / "wiki_t45_extracted.jsonl"
FAILED_JSONL = TMP / "wiki_t45_failed.jsonl"
RUN_JSON = TMP / "wiki_t45_run.json"
DEBUG_DIR = TMP / "wiki_t45_debug"

OLLAMA_DEFAULT_URL = "http://192.168.86.18:1234/v1"
DEFAULT_MODEL = "nemotron-3-nano:4b"
DEFAULT_N_PARALLEL = 5
# The combined extraction prompt asks for tier, explanation, two
# nullable year fields, and an N-pair list. The output JSON is
# typically 200-500 chars per article. We budget 4000 to leave
# headroom for CoT (the model uses internal reasoning before the
# final JSON).
DEFAULT_MAX_TOKENS = 4000

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_PATH = PROMPTS_DIR / "wiki_t45_extract_v1.txt"

TIER_RANK = {"T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5}
TIER_INFO = {
    "T1": {"tier_label": "T1-Diplomatic Crisis",       "hostlev": 1},
    "T2": {"tier_label": "T2-Economic Coercion",       "hostlev": 2},
    "T3": {"tier_label": "T3-Proxy/Indirect Military", "hostlev": 3},
    "T4": {"tier_label": "T4-Limited Military",        "hostlev": 4},
    "T5": {"tier_label": "T5-Strategic War",           "hostlev": 5},
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kept", default=str(KEPT_JSONL))
    p.add_argument("--tier-parquet", default=str(TIER_PARQUET),
                   help="Parquet of stage 2 candidates (for article text).")
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
        default=int(os.environ.get("OLLAMA_N_PARALLEL", str(DEFAULT_N_PARALLEL))),
    )
    p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--per-call-timeout", type=float, default=600.0)
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
    """{article_id: {name, abstract, sections_excerpt}}.

    Looks up article text from the stage 2 parquet. The parquet's
    `identifier` is the article_id; we pull name/abstract/sections_excerpt.
    """
    out: dict[int, dict] = {}
    if not Path(parquet_path).exists():
        return out
    try:
        import pyarrow.parquet as pq
        t = pq.read_table(parquet_path)
        for row in t.to_pylist():
            try:
                aid = int(row.get("identifier"))
            except (TypeError, ValueError):
                continue
            out[aid] = {
                "name": row.get("name") or "",
                "abstract": row.get("abstract") or "",
                "sections_excerpt": row.get("sections_excerpt") or "",
            }
    except Exception:
        pass
    return out


def _build_article_text(text_article: dict, max_chars: int = 4000) -> str:
    parts: list[str] = []
    nm = (text_article.get("name") or "").strip()
    if nm:
        parts.append(f"Title: {nm}")
    ab = (text_article.get("abstract") or "").strip()
    if ab:
        parts.append(f"Abstract: {ab}")
    sx = (text_article.get("sections_excerpt") or "").strip()
    if sx:
        parts.append(f"Sections:\n{sx}")
    text = "\n\n".join(parts)
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


def _load_prompt_template(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _coerce_year(v) -> int | None:
    if v is None:
        return None
    if isinstance(v, int) and 1800 <= v <= 2100:
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        m = re.search(r"\b(\d{3,4})\b", s)
        if m:
            y = int(m.group(1))
            if 1800 <= y <= 2100:
                return y
        return None
    try:
        y = int(v)
        if 1800 <= y <= 2100:
            return y
    except (TypeError, ValueError):
        return None
    return None


def _coerce_float(v, default: float = 0.0) -> float:
    try:
        f = float(v)
        if f != f:  # NaN
            return default
        return max(0.0, min(1.0, f))
    except (TypeError, ValueError):
        return default


def _coerce_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "y"}
    if isinstance(v, (int, float)):
        return bool(v)
    return False


def _coerce_str(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _parse_extraction_output(raw: str) -> dict | None:
    """Parse the LLM output into {tier, explanation, start_year,
    end_year, pairs: [{initiator, target, confidence, implied}]}.

    Returns None on failure. Robust to:
      - think tags (stripped upstream)
      - whitespace around JSON
      - pairs missing some fields (filled with defaults)
      - pairs given as bare list (defaults applied)
    """
    if not raw:
        return None
    s = raw.strip()
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    end = -1
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
                end = i
                break
    if end < 0:
        return None
    try:
        obj = json.loads(s[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None

    tier_raw = _coerce_str(obj.get("tier")).upper()
    if tier_raw not in TIER_RANK and tier_raw != "NONE":
        # Try to recover from common variants
        for t in TIER_RANK:
            if tier_raw.startswith(t):
                tier_raw = t
                break
        else:
            return None
    if tier_raw == "NONE":
        return {
            "tier": "NONE",
            "explanation": _coerce_str(obj.get("explanation"))[:300],
            "start_year": None,
            "end_year": None,
            "pairs": [],
        }

    info = TIER_INFO[tier_raw]
    start_year = _coerce_year(obj.get("start_year"))
    end_year = _coerce_year(obj.get("end_year"))
    if start_year is not None and end_year is not None and end_year < start_year:
        start_year, end_year = end_year, start_year

    pairs_raw = obj.get("pairs")
    pairs: list[dict] = []
    if isinstance(pairs_raw, list):
        for p in pairs_raw:
            if not isinstance(p, dict):
                continue
            initiator = _coerce_str(p.get("initiator"))
            target = _coerce_str(p.get("target"))
            if not initiator or not target:
                continue
            pairs.append({
                "initiator": initiator,
                "target": target,
                "confidence": _coerce_float(p.get("confidence"), 0.5),
                "implied": _coerce_bool(p.get("implied")),
            })

    return {
        "tier": tier_raw,
        "tier_label": info["tier_label"],
        "hostlev": info["hostlev"],
        "explanation": _coerce_str(obj.get("explanation"))[:300],
        "start_year": start_year,
        "end_year": end_year,
        "pairs": pairs,
    }


sys.path.insert(0, str(Path(__file__).resolve().parent))
from wiki_llm_helpers import (
    call_chat_with_json_parse,
    log_failure,
    make_request_nonce,
    print_progress,
)


def _process_one(
    client,
    art: dict,
    article_texts: dict[int, dict],
    chosen: str,
    prompt_head: str,
    prompt_tail: str,
    args,
) -> tuple[dict, dict | None, str | None, dict]:
    """Process one article. Returns (article_meta, parsed_obj, error_str, debug)."""
    article_id = int(art["article_id"])
    article_title = str(art.get("article_title") or "")
    text_article = article_texts.get(article_id, {
        "name": article_title,
        "abstract": "",
        "sections_excerpt": "",
    })
    text = _build_article_text(text_article)
    user_msg = (
        prompt_head
        .replace("{article_id}", str(article_id))
        .replace("{article}", text)
    ) + prompt_tail
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
    return art, parsed, None if parsed is not None else (debug.get("error") or "no_response"), debug


def main() -> int:
    args = _parse_args()

    for path in (args.kept, args.prompt, args.tier_parquet):
        if not Path(path).exists():
            print(f"Missing required input: {path}", file=sys.stderr)
            return 1

    template = _load_prompt_template(Path(args.prompt))
    head, tail = template.split("{article}", 1) if "{article}" in template else (template, "")
    print(f"Prompt: {args.prompt}  head={len(head)} chars  tail={len(tail)} chars")
    print(f"  max_tokens: {args.max_tokens}  per-call-timeout: {args.per_call_timeout}s")
    print(f"  base-url:   {args.base_url}  model: {args.model}")

    articles = _load_articles(Path(args.kept), args.max_articles)
    if args.smoke_test:
        articles = articles[: args.smoke_test]
    n_total = len(articles)
    print(f"Articles to extract from: {n_total:,}")
    if n_total == 0:
        print("No articles to process. Exiting.")
        return 0

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
        chosen = next(
            (i for i in ids if args.model.lower() in i.lower() or i.lower().endswith("/" + args.model.lower())),
            ids[0] if ids else args.model,
        )
        print(f"Ollama OK: {len(ids)} model(s); using '{chosen}'")
    except Exception as e:
        print(f"Could not reach Ollama at {args.base_url}: {e}", file=sys.stderr)
        return 1

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.debug_dir).mkdir(parents=True, exist_ok=True)
    out_mode = "a" if Path(args.out).exists() and Path(args.out).stat().st_size > 0 else "w"
    failed_mode = "a" if Path(args.failed).exists() and Path(args.failed).stat().st_size > 0 else "w"
    out_f = open(args.out, out_mode, encoding="utf-8", buffering=1)
    failed_f = open(args.failed, failed_mode, encoding="utf-8", buffering=1)

    n_with_pairs = 0
    n_none = 0
    n_failed = 0
    n_server_crashes = 0
    t_start = time.time()
    done = 0

    def _process(art: dict):
        return _process_one(client, art, article_texts, chosen, head, tail, args)

    try:
        with cf.ThreadPoolExecutor(max_workers=args.n_parallel) as ex:
            futures = {ex.submit(_process, a): a for a in articles}
            for fut in cf.as_completed(futures):
                art, parsed, err, debug = fut.result()
                done += 1
                n_server_crashes += int(debug.get("server_crash_count", 0) or 0)
                article_id = int(art["article_id"])
                article_title = str(art.get("article_title") or "")
                if parsed is None:
                    n_failed += 1
                    failed_f.write(json.dumps({
                        "article_id": article_id,
                        "article_title": article_title,
                        "error": err or "no_parse",
                        "raw_content": (debug.get("raw_content") or "")[:1000],
                        "raw_reasoning": (debug.get("raw_reasoning") or "")[:1000],
                    }, ensure_ascii=False) + "\n")
                    log_failure(
                        Path(args.debug_dir),
                        article_id,
                        raw_content=debug.get("raw_content", ""),
                        raw_reasoning=debug.get("raw_reasoning", ""),
                        parsed=None,
                        error=err or "no_parse",
                        block=None,
                        extra={"article_title": article_title},
                    )
                else:
                    out_obj = {
                        "article_id": article_id,
                        "article_title": article_title,
                        "tier": parsed["tier"],
                        "tier_label": parsed.get("tier_label"),
                        "hostlev": parsed.get("hostlev"),
                        "start_year": parsed["start_year"],
                        "end_year": parsed["end_year"],
                        "explanation": parsed["explanation"],
                        "model": chosen,
                        "pairs": parsed["pairs"],
                    }
                    out_f.write(json.dumps(out_obj, ensure_ascii=False) + "\n")
                    if parsed["tier"] == "NONE":
                        n_none += 1
                    else:
                        n_with_pairs += 1
                if done % 1 == 0 or done == n_total:
                    elapsed = time.time() - t_start
                    rate = done / max(elapsed, 1e-6)
                    eta = (n_total - done) / max(rate, 1e-6)
                    print_progress(
                        done=done,
                        total=n_total,
                        n_kept=n_with_pairs,
                        n_rejected=n_none,
                        n_failed=n_failed,
                        extra=f"with_pairs={n_with_pairs} none={n_none} rate={rate:.1f}/s eta={eta/60:.1f}m crashes={n_server_crashes}",
                    )
    finally:
        out_f.close()
        failed_f.close()

    elapsed = time.time() - t_start
    run_meta = {
        "n_articles_in": n_total,
        "n_articles_with_pairs": n_with_pairs,
        "n_articles_none": n_none,
        "n_articles_failed": n_failed,
        "server_crashes_total": n_server_crashes,
        "elapsed_seconds": round(elapsed, 1),
        "model": chosen,
        "base_url": args.base_url,
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
    print(f"Wrote {args.out} ({n_with_pairs:,} with pairs, {n_none:,} NONE)")
    print(f"Failed: {n_failed} (see {args.failed})")
    print(f"Meta:   {args.run_meta}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
