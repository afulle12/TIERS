"""LLM confirm pass for T4 -> T5 upgrade candidates.

Stage 5 of the Wikipedia tier-extraction pipeline. Reads the
heuristic-positive T5 candidates produced by the infobox parser
(`tmp/wiki_t45_t5_candidates.jsonl`) and asks an LLM (Ollama,
nemotron-3-nano:4b by default) whether each article is truly
T5 (strategic war) or T4 (limited direct military).

The v27.0 spec defines T5 as "nationwide or multi-front warfare
between two states, with sustained campaigns and the commitment of
the bulk of each state's military capacity" and T4 as "open,
attributed exchange of fire between the regular armed forces of two
states" (border clashes, airstrikes, naval engagements, small-scale
incursions).

Inputs:
  - tmp/wiki_t45_t5_candidates.jsonl (from wiki_extract_infobox_t45.py)
  - tmp/wiki_tier_candidates.parquet  (for the article text)
  - Ollama at $OLLAMA_BASE_URL/v1

Output:
  - tmp/wiki_t45_confirmed_t5.jsonl
      One row per confirmed T5 event, schema mirrors the T4/T5
      infobox parser (with tier="T5", hostlev=5, source="WIKI_T5").
  - tmp/wiki_t45_ambiguous_diag.json
      Counts of candidates, confirmed T5, confirmed T4, and
      disagreements (LLM flipped heuristic).
  - tmp/wiki_t45_ambiguous_review.csv
      Long-form table of LLM-vs-heuristic disagreements, for human
      review.
  - tmp/wiki_t45_ambiguous_debug/<article_id>.json
      Per-article diagnostic (raw response, parsed output, error)
      written automatically on every failure.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"

CANDIDATES_JSONL = TMP / "wiki_t45_t5_candidates.jsonl"
TIER_PARQUET = TMP / "wiki_tier_candidates.parquet"
OUT_JSONL = TMP / "wiki_t45_confirmed_t5.jsonl"
DIAG_JSON = TMP / "wiki_t45_ambiguous_diag.json"
REVIEW_CSV = TMP / "wiki_t45_ambiguous_review.csv"
DEBUG_DIR = TMP / "wiki_t45_ambiguous_debug"

OLLAMA_DEFAULT_URL = "http://192.168.86.18:1234/v1"
DEFAULT_MODEL = "nemotron-3-nano:4b"
# n_parallel defaults to 1 for this small model; the 31 candidates
# finish quickly and the conservative default avoids OOM.
DEFAULT_N_PARALLEL = 1

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_PATH = PROMPTS_DIR / "wiki_t45_ambiguous_v2.txt"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidates", default=str(CANDIDATES_JSONL))
    p.add_argument("--tier-parquet", default=str(TIER_PARQUET))
    p.add_argument("--prompt", default=str(PROMPT_PATH))
    p.add_argument("--out", default=str(OUT_JSONL))
    p.add_argument("--diag", default=str(DIAG_JSON))
    p.add_argument("--review", default=str(REVIEW_CSV))
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
    p.add_argument("--max-tokens", type=int, default=2500)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-candidates", type=int, default=0)
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
        "--confidence-threshold",
        type=float,
        default=0.5,
        help="Minimum LLM confidence to accept the T5 confirmation.",
    )
    p.add_argument("--smoke-test", type=int, default=0)
    return p.parse_args()


def _load_prompt(path: Path) -> tuple[str, str]:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "{article}" not in content:
        raise SystemExit(f"Prompt must contain '{{article}}' placeholder: {path}")
    head, tail = content.split("{article}", 1)
    return head, tail


def _load_jsonl(path: str) -> list[dict]:
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
    return out


def _load_article_texts(parquet_path: str) -> dict[int, dict]:
    """{article_id: {abstract, sections_excerpt, name}}."""
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


def _build_article_text(article: dict, max_chars: int = 4000) -> str:
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


# Import the shared helpers
sys.path.insert(0, str(Path(__file__).resolve().parent))
from wiki_llm_helpers import (
    call_chat_with_json_parse,
    log_failure,
    make_request_nonce,
    print_progress,
)


def _parse_classifier_output(obj) -> tuple[str | None, float, str]:
    """Return (tier, confidence, reason) from a parsed JSON object."""
    if not isinstance(obj, dict):
        return None, 0.0, "not_a_dict"
    tier = obj.get("tier")
    if tier not in {"T4", "T5"}:
        return None, 0.0, f"bad_tier:{tier!r}"
    try:
        conf = float(obj.get("confidence") or 0.0)
    except (TypeError, ValueError):
        conf = 0.0
    reason = str(obj.get("reason") or "")[:200]
    return tier, conf, reason


def main() -> int:
    args = _parse_args()

    if not Path(args.candidates).exists():
        print(f"Missing candidates file: {args.candidates}", file=sys.stderr)
        return 1
    if not Path(args.prompt).exists():
        print(f"Missing prompt file: {args.prompt}", file=sys.stderr)
        return 1

    candidates = _load_jsonl(args.candidates)
    if args.max_candidates:
        candidates = candidates[: args.max_candidates]
    if args.smoke_test:
        candidates = candidates[: args.smoke_test]
    n_total = len(candidates)
    print(f"T5 candidates to process: {n_total:,}")
    print(f"  base-url: {args.base_url}")
    print(f"  model:    {args.model}")
    print(f"  prompt:   {args.prompt}")
    print(f"  max_tokens: {args.max_tokens}")
    print(f"  per-call-timeout: {args.per_call_timeout}s")
    print(f"  n_parallel: {args.n_parallel}")

    article_texts = _load_article_texts(args.tier_parquet)
    print(f"Article texts loaded: {len(article_texts):,}")

    prompt_head, prompt_tail = _load_prompt(Path(args.prompt))
    print(f"Prompt head={len(prompt_head)} chars  tail={len(prompt_tail)} chars")
    print()

    try:
        from openai import OpenAI
    except ImportError as e:
        print("openai>=1.0 is required", file=sys.stderr)
        raise SystemExit(1) from e

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    try:
        models = client.models.list()
        ids = [m.id for m in getattr(models, "data", [])]
        chosen = next((i for i in ids if args.model.lower() in i.lower()), ids[0] if ids else args.model)
        print(f"Ollama OK: {len(ids)} model(s); using '{chosen}'")
    except Exception as e:
        print(f"Could not reach Ollama: {e}", file=sys.stderr)
        return 1

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.review).parent.mkdir(parents=True, exist_ok=True)
    Path(args.debug_dir).mkdir(parents=True, exist_ok=True)
    # Append mode if file has prior content; protects against re-runs
    out_mode = "a" if Path(args.out).exists() and Path(args.out).stat().st_size > 0 else "w"
    review_mode = "a" if Path(args.review).exists() and Path(args.review).stat().st_size > 0 else "w"
    out_f = open(args.out, out_mode, encoding="utf-8")
    review_f = open(args.review, review_mode, newline="")
    review_writer = csv.DictWriter(
        review_f,
        fieldnames=["article_id", "article_title", "year", "heuristic_positive", "llm_tier", "llm_confidence", "reason"],
    )
    if review_mode == "w":
        review_writer.writeheader()

    n_confirmed_t5 = 0
    n_confirmed_t4 = 0
    n_failed = 0
    n_skipped = 0
    n_disagreement = 0
    n_server_crashes = 0
    t_start = time.time()
    done = 0

    def _process(c: dict) -> tuple[dict, dict | None, str | None, dict]:
        article = article_texts.get(c["article_id"], {})
        if not article:
            return c, None, "no_text", {"raw_content": "", "raw_reasoning": "", "block": None, "error": "no_text", "elapsed_seconds": 0.0}
        article_text = _build_article_text(article)
        user_msg = prompt_head + article_text + prompt_tail
        messages = [
            {"role": "system", "content": "You are a precise conflict-tier classifier. Respond only with a single JSON object."},
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
        tier, conf, reason = (None, 0.0, "")
        if parsed is not None:
            tier, conf, reason = _parse_classifier_output(parsed)
            if tier is None:
                debug["error"] = reason
                return c, None, reason, debug
        return c, {"tier": tier, "confidence": conf, "reason": reason}, debug.get("error"), debug

    try:
        with cf.ThreadPoolExecutor(max_workers=args.n_parallel) as ex:
            futures = {ex.submit(_process, c): c for c in candidates}
            for fut in cf.as_completed(futures):
                c, result, err, debug = fut.result()
                done += 1
                if err is not None:
                    n_failed += 1
                    n_server_crashes += int(debug.get("server_crash_count", 0) or 0)
                    log_failure(
                        Path(args.debug_dir),
                        c["article_id"],
                        raw_content=debug.get("raw_content", ""),
                        raw_reasoning=debug.get("raw_reasoning", ""),
                        parsed=None,
                        error=err,
                        block=debug.get("block"),
                        extra={"article_title": c.get("article_title"), "year": c.get("year")},
                    )
                elif result is None or result["tier"] is None:
                    n_skipped += 1
                else:
                    heuristic_positive = True
                    if result["tier"] == "T5" and result["confidence"] >= args.confidence_threshold:
                        n_confirmed_t5 += 1
                        belligerents = c.get("belligerents", [])
                        for i in range(len(belligerents)):
                            for j in range(i + 1, len(belligerents)):
                                a, b = belligerents[i], belligerents[j]
                                for year in range(c["year"], c.get("end_year", c["year"]) + 1):
                                    out_f.write(json.dumps({
                                        "article_id": c["article_id"],
                                        "article_title": c["article_title"],
                                        "infobox_name": c["infobox_name"],
                                        "year": year,
                                        "start_year": c["year"],
                                        "end_year": c.get("end_year", c["year"]),
                                        "tier": "T5",
                                        "hostlev": 5,
                                        "tier_label": "T5-Strategic War",
                                        "source": "WIKI_T5",
                                        "initiator_country": a["name"],
                                        "initiator_qid": None,
                                        "initiator_gwno": int(a["gwno"]),
                                        "target_country": b["name"],
                                        "target_qid": None,
                                        "target_gwno": int(b["gwno"]),
                                        "confidence": result["confidence"],
                                        "promotion": "llm_confirm",
                                    }, ensure_ascii=False) + "\n")
                                    out_f.write(json.dumps({
                                        "article_id": c["article_id"],
                                        "article_title": c["article_title"],
                                        "infobox_name": c["infobox_name"],
                                        "year": year,
                                        "start_year": c["year"],
                                        "end_year": c.get("end_year", c["year"]),
                                        "tier": "T5",
                                        "hostlev": 5,
                                        "tier_label": "T5-Strategic War",
                                        "source": "WIKI_T5",
                                        "initiator_country": b["name"],
                                        "initiator_qid": None,
                                        "initiator_gwno": int(b["gwno"]),
                                        "target_country": a["name"],
                                        "target_qid": None,
                                        "target_gwno": int(a["gwno"]),
                                        "confidence": result["confidence"],
                                        "promotion": "llm_confirm",
                                    }, ensure_ascii=False) + "\n")
                    else:
                        n_confirmed_t4 += 1
                    if result["tier"] != "T5":
                        n_disagreement += 1
                        review_writer.writerow({
                            "article_id": c["article_id"],
                            "article_title": c["article_title"],
                            "year": c["year"],
                            "heuristic_positive": heuristic_positive,
                            "llm_tier": result["tier"],
                            "llm_confidence": round(result["confidence"], 3),
                            "reason": result["reason"],
                        })
                if done % 1 == 0 or done == n_total:
                    elapsed = time.time() - t_start
                    rate = done / max(elapsed, 1e-6)
                    eta = (n_total - done) / max(rate, 1e-6)
                    print_progress(
                        done=done,
                        total=n_total,
                        n_kept=n_confirmed_t5,
                        n_rejected=n_confirmed_t4,
                        n_failed=n_failed,
                        extra=f"rate={rate:.1f}/s eta={eta/60:.1f}m crashes={n_server_crashes}",
                    )
    finally:
        out_f.close()
        review_f.close()

    elapsed = time.time() - t_start
    diag = {
        "n_in": n_total,
        "n_confirmed_t5": n_confirmed_t5,
        "n_confirmed_t4": n_confirmed_t4,
        "n_failed": n_failed,
        "n_skipped": n_skipped,
        "n_disagreement": n_disagreement,
        "server_crashes_total": n_server_crashes,
        "elapsed_seconds": round(elapsed, 1),
        "model": chosen,
        "base_url": args.base_url,
        "prompt_path": args.prompt,
        "confidence_threshold": args.confidence_threshold,
        "max_tokens": args.max_tokens,
        "per_call_timeout": args.per_call_timeout,
        "max_server_crashes": args.max_server_crashes,
        "n_parallel": args.n_parallel,
    }
    with open(args.diag, "w") as f:
        json.dump(diag, f, indent=2)

    print()
    print("=" * 60)
    print(f"Wrote {args.out} ({n_confirmed_t5} confirmed T5 events)")
    print(f"  confirmed T5: {n_confirmed_t5}  confirmed T4: {n_confirmed_t4}  failed: {n_failed}")
    print(f"  disagreements (LLM flipped heuristic): {n_disagreement}")
    print(f"  review file: {args.review}")
    print(f"  debug dir:   {args.debug_dir}")
    print(f"  diagnostics: {args.diag}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
