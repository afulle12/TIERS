"""Stage 6 of the Wikipedia tier-extraction pipeline: LLM tier + explanation.

Reads the LLM-path articles kept by the 0/1 filter
(`tmp/wiki_t123_filter_kept.jsonl`) and asks the LLM (Ollama,
nemotron-3-nano-4b by default) one short question per article:

  "Which tier of the v27.0 T-scale is this article? Explain in 1
  sentence (max 20 words)."

The output is the article's tier plus a 1-sentence explanation of WHY
that tier. The event fields (year, initiator, target, confidence) are
extracted separately by stage 7 (`wiki_extract_llm_t123.py`).

This stage is intentionally CHEAP: 1-article-per-prompt, no chain-of-
thought, max_tokens=1500. Wall time on nemotron-nano with 8 parallel
workers is ~5 sec/call.

Inputs:
  - tmp/wiki_t123_filter_kept.jsonl (from stage 3b)
  - tmp/wiki_tier_candidates.parquet (for the article text)
  - Ollama at $OLLAMA_BASE_URL/v1
  - scripts/build/prompts/wiki_t123_tier_v1.txt

Outputs:
  - tmp/wiki_t123_tier.jsonl
      One row per article: {article_id, tier, hostlev, tier_label,
      explanation, model, elapsed_s}
  - tmp/wiki_t123_tier_run.json
      Run metadata
  - tmp/wiki_t123_tier_debug/<article_id>.json
      Per-article raw-response diagnostic (auto-written on failure)
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
OUT_JSONL = TMP / "wiki_t123_tier.jsonl"
RUN_JSON = TMP / "wiki_t123_tier_run.json"
DEBUG_DIR = TMP / "wiki_t123_tier_debug"

OLLAMA_DEFAULT_URL = "http://192.168.86.18:1234/v1"
DEFAULT_MODEL = "nemotron-3-nano:4b"
DEFAULT_N_PARALLEL = 8
DEFAULT_MAX_TOKENS = 1500

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_PATH = PROMPTS_DIR / "wiki_t123_tier_v1.txt"

# v27.0 tier scheme
TIER_INFO = {
    "T1": {"tier_label": "T1-Diplomatic Crisis",       "hostlev": 1},
    "T2": {"tier_label": "T2-Economic Coercion",       "hostlev": 2},
    "T3": {"tier_label": "T3-Proxy/Indirect Military", "hostlev": 3},
    "T4": {"tier_label": "T4-Limited Military",        "hostlev": 4},
    "T5": {"tier_label": "T5-Strategic War",           "hostlev": 5},
}
VALID_TIERS = set(TIER_INFO.keys())


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kept", default=str(KEPT_JSONL))
    p.add_argument("--tier-parquet", default=str(TIER_PARQUET))
    p.add_argument("--prompt", default=str(PROMPT_PATH))
    p.add_argument("--out", default=str(OUT_JSONL))
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


def _load_prompt(path: Path) -> tuple[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "{article}" not in content:
        raise SystemExit(f"Prompt must contain '{{article}}' placeholder: {path}")
    head, tail = content.split("{article}", 1)
    return head, tail


def _load_articles_from_kept(path: Path, max_articles: int) -> list[dict]:
    if not Path(path).exists():
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


sys.path.insert(0, str(Path(__file__).resolve().parent))
from wiki_llm_helpers import (
    call_chat_with_json_parse,
    log_failure,
    make_request_nonce,
    print_progress,
)


def _parse_tier_output(obj) -> dict | None:
    """Return {tier, hostlev, tier_label, explanation} or None."""
    if not isinstance(obj, dict):
        return None
    tier = obj.get("tier")
    if not isinstance(tier, str):
        return None
    tier = tier.strip().upper()
    if tier == "NONE":
        return {"tier": "NONE", "hostlev": None, "tier_label": None, "explanation": ""}
    if tier not in VALID_TIERS:
        return None
    info = TIER_INFO[tier]
    hostlev = obj.get("hostlev")
    if hostlev is None:
        hostlev = info["hostlev"]
    try:
        hostlev = int(hostlev)
    except (TypeError, ValueError):
        hostlev = info["hostlev"]
    tier_label = obj.get("tier_label") or info["tier_label"]
    explanation = obj.get("explanation") or ""
    if not isinstance(explanation, str):
        explanation = str(explanation)
    explanation = explanation.strip()[:500]
    return {
        "tier": tier,
        "hostlev": hostlev,
        "tier_label": tier_label,
        "explanation": explanation,
    }


def main() -> int:
    args = _parse_args()

    for path in (args.kept, args.prompt, args.tier_parquet):
        if not Path(path).exists():
            print(f"Missing required input: {path}", file=sys.stderr)
            return 1

    prompt_head, prompt_tail = _load_prompt(Path(args.prompt))
    print(f"Prompt: {args.prompt}  head={len(prompt_head)} chars  tail={len(prompt_tail)} chars")
    print(f"  base-url: {args.base_url}  model: {args.model}")
    print(f"  n-parallel: {args.n_parallel}  max-tokens: {args.max_tokens}")

    articles = _load_articles_from_kept(Path(args.kept), args.max_articles)
    if args.smoke_test:
        articles = articles[: args.smoke_test]
    n_total = len(articles)
    print(f"Articles to tier-classify: {n_total:,}")
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
    out_f = open(args.out, out_mode, encoding="utf-8", buffering=1)

    n_tier = 0
    n_none = 0
    n_failed = 0
    n_server_crashes = 0
    t_start = time.time()
    done = 0

    def _process(art: dict) -> tuple[dict, dict | None, str | None, dict]:
        article_id = int(art["article_id"])
        text_article = article_texts.get(article_id, {})
        if not text_article:
            return art, None, "no_text", {"raw_content": "", "raw_reasoning": "", "block": None, "error": "no_text", "elapsed_seconds": 0.0}
        text = _build_article_text(text_article)
        user_msg = prompt_head.replace("{article_id}", str(article_id)) + text + prompt_tail
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
            out = _parse_tier_output(parsed)
            if out is None:
                return art, None, "bad_tier_output", debug
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
                    log_failure(
                        Path(args.debug_dir),
                        art.get("article_id"),
                        raw_content=debug.get("raw_content", ""),
                        raw_reasoning=debug.get("raw_reasoning", ""),
                        parsed=debug.get("block"),
                        error=err or "no_parse",
                        block=debug.get("block"),
                        extra={"article_title": art.get("article_title")},
                    )
                else:
                    if parsed["tier"] == "NONE":
                        n_none += 1
                    else:
                        n_tier += 1
                    out_f.write(json.dumps({
                        "article_id": int(art["article_id"]),
                        "article_title": art.get("article_title") or "",
                        "tier": parsed["tier"],
                        "hostlev": parsed["hostlev"],
                        "tier_label": parsed["tier_label"],
                        "explanation": parsed["explanation"],
                        "model": chosen,
                        "elapsed_s": round(debug.get("elapsed_seconds", 0.0), 2),
                    }, ensure_ascii=False) + "\n")
                if done % 1 == 0 or done == n_total:
                    elapsed = time.time() - t_start
                    rate = done / max(elapsed, 1e-6)
                    eta = (n_total - done) / max(rate, 1e-6)
                    print_progress(
                        done=done,
                        total=n_total,
                        n_kept=n_tier,
                        n_rejected=n_none,
                        n_failed=n_failed,
                        extra=f"rate={rate:.1f}/s eta={eta/60:.1f}m crashes={n_server_crashes}",
                    )
    finally:
        out_f.close()

    elapsed = time.time() - t_start
    run_meta = {
        "n_articles_in": n_total,
        "n_tier": n_tier,
        "n_none": n_none,
        "n_failed": n_failed,
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
    print(f"Wrote {args.out} ({n_tier} tier, {n_none} NONE, {n_failed} failed)")
    print(f"Debug: {args.debug_dir}/<article_id>.json")
    print(f"Meta:  {args.run_meta}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
