"""Shared LLM helpers for the Wikipedia tier-extraction pipeline.

The qwen3.5-9B model on LM Studio has four known behaviors that bite
the JSON extractors:

  1. The OpenAI-compat `response_format={"type": "json_object"}` is
     rejected with HTTP 400 (only "json_schema" and "text" are
     accepted). Caller scripts must omit it or use
     `{"type": "text"}`.

  2. Chain-of-thought reasoning tokens can consume 100% of
     `max_tokens`, leaving `content=""` and `finish_reason="length"`.
     Callers must budget at least 4,000 reasoning tokens PLUS the
     expected JSON size (a single T1/T2/T3 record is ~70 tokens; a
     T4/T5 confirm pass is ~30 tokens).

  3. The model emits a "Thinking Process: ..." trace into
     `reasoning_content`. The actual JSON goes into `content`.
     If `content` is empty (truncation), the JSON may also be
     partially or fully inside `reasoning_content`.

  4. `<think>...</think>` tags can leak into `content` for some
     models. Strip them defensively before JSON extraction.

This module provides:

  - `chat_completions_create`: a thin wrapper around the OpenAI
    client that sets a per-call timeout, retries with exponential
    backoff, and strips `<think>` tags from the response.

  - `parse_json_response`: extracts a JSON object from a possibly
    contaminated string. Falls back to `reasoning_content` if
    `content` is empty.

  - `log_failure`: writes a per-article diagnostic JSON to
    `tmp/wiki_*_debug/<article_id>.json` with the raw response,
    parsed output, and error — automatically, not gated behind a
    `--debug` flag.
"""
from __future__ import annotations

import json
import re
import secrets
import time
from pathlib import Path
from typing import Any, Callable, Iterable

# Regex matches both <think> and <think> style thinking tags
# (some models use one, some the other).
_THINK_TAG_RE = re.compile(
    r"<\s*(?:think|redacted_reasoning|antml_thinking)\s*>([\s\S]*?)<\s*/\s*(?:think|redacted_reasoning|antml_thinking)\s*>",
    re.IGNORECASE,
)

# Error substrings that indicate the LM Studio server itself crashed or
# unloaded the model mid-request. Distinct from parse / content errors,
# which are the model's fault. Triggers the long-backoff reconnect loop
# in `call_chat_with_json_parse`.
_SERVER_CRASH_PATTERNS: tuple[str, ...] = (
    "model unloaded",
    "channel error",
    "connection error",
    "server disconnected",
    "temporarily unavailable",
    "tensor not allocated",
)


def _is_server_crash(err: str | None) -> bool:
    """Return True if `err` looks like a server-side crash/unload
    rather than a model/parse error."""
    if not err:
        return False
    e = err.lower()
    return any(p in e for p in _SERVER_CRASH_PATTERNS)


def wait_for_server_ready(
    client,
    *,
    model_id: str,
    timeout_per_probe: float = 5.0,
    max_wait: float = 120.0,
    poll_interval: float = 3.0,
) -> bool:
    """Poll GET /v1/models until `model_id` reappears, or `max_wait`
    elapses. Returns True if the model is loaded again, False on
    timeout. Used after a `Model unloaded` / `Channel Error` to wait
    out LM Studio's automatic model reload (10-60s for a 9B)."""
    t0 = time.time()
    while time.time() - t0 < max_wait:
        try:
            models = client.models.list()
            ids = [m.id for m in getattr(models, "data", [])]
            if any(model_id.lower() in i.lower() or i.lower().endswith("/" + model_id.lower()) for i in ids):
                return True
        except Exception:
            pass
        time.sleep(poll_interval)
    return False


def make_request_nonce() -> str:
    """Return a short random nonce (8 hex chars) used to break LM
    Studio's LCP (longest-common-prefix) prompt cache. Every request
    in the LLM-path scripts has a ~2,500-char shared prompt head, so
    without a unique nonce LM Studio matches each new request against
    a cached slot. If that slot's tensors have been freed (e.g. model
    auto-unloaded) the next request triggers the `tensor not
    allocated` GGML assertion and the engine crashes."""
    return secrets.token_hex(4)


def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> style blocks from a model response.

    Returns the text with all think blocks removed and the
    surrounding whitespace collapsed. Safe on None and empty
    strings.
    """
    if not text:
        return ""
    cleaned = _THINK_TAG_RE.sub("", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _balanced_json_end(text: str, start: int) -> int | None:
    """Return the index just past the balanced closing brace of a
    JSON object starting at `start`, or None if unbalanced."""
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
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
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return None


def extract_json_object(text: str) -> str | None:
    """Return the first balanced top-level JSON object substring.

    Returns None if no balanced `{...}` block is found.
    """
    if not text:
        return None
    s = text.strip()
    if s.startswith("{") and s.endswith("}"):
        # Quick path
        return s
    start = s.find("{")
    if start < 0:
        return None
    end = _balanced_json_end(s, start)
    if end is None:
        return None
    return s[start:end]


def _wrap_openai_call(
    client,
    *,
    model: str,
    messages: list[dict],
    temperature: float,
    seed: int,
    max_tokens: int,
    timeout: float,
) -> tuple[Any, str | None]:
    """Call OpenAI chat.completions.create with a per-call timeout
    and translate common exceptions to a string error."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            seed=seed,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return resp, None
    except Exception as e:
        return None, f"api_error: {type(e).__name__}: {e}"


def call_chat_with_json_parse(
    client,
    *,
    model: str,
    messages: list[dict],
    temperature: float = 0.0,
    seed: int = 42,
    max_tokens: int = 2500,
    timeout: float = 600.0,
    max_retries: int = 3,
    backoff_base: float = 1.5,
    request_nonce: str | None = None,
    max_server_crashes: int = 5,
    server_backoff: float = 15.0,
    server_recovery_timeout: float = 120.0,
) -> tuple[dict | list | None, dict]:
    """Call the chat completion and parse a JSON object from the
    response.

    Returns (parsed_json, debug_info) where debug_info has:
      - "raw_content" (str, possibly empty)
      - "raw_reasoning" (str, possibly empty)
      - "raw_combined" (str) — content first, then reasoning if content
        was empty (defensive fallback for the LM Studio reasoning-
        content bug)
      - "block" (str | None) — the extracted JSON block
      - "error" (str | None)
      - "finish_reason" (str | None)
      - "elapsed_seconds" (float)
      - "usage" (dict | None)
      - "server_crash_count" (int) — number of server-crash recoveries
      - "server_crash_history" (list[str]) — last few crash messages

    The function retries up to `max_retries` times on
    `api_error`, `no_json_in_response`, or `json_decode` errors
    with exponential backoff. It does NOT retry on logical errors
    (e.g. "bad_tier" from the caller's parser).

    If `request_nonce` is provided, a single line of the form
    `<!-- req=<nonce> -->` is prepended to the LAST user message.
    This breaks LM Studio's LCP (longest-common-prefix) prompt cache
    so that the request does not collide with a stale slot whose
    tensors have been freed (the `tensor not allocated` crash).

    Server-crash errors (`Model unloaded`, `Channel Error`,
    `tensor not allocated`, `connection error`, `server
    disconnected`, `temporarily unavailable`) are detected and
    trigger a separate bounded reconnect loop: sleep
    `server_backoff`, call `wait_for_server_ready` (polls
    GET /v1/models for up to `server_recovery_timeout`), then
    retry. Bounded to `max_server_crashes` consecutive recoveries;
    0 disables server-crash recovery.
    """
    debug: dict = {
        "raw_content": "",
        "raw_reasoning": "",
        "raw_combined": "",
        "block": None,
        "error": None,
        "finish_reason": None,
        "elapsed_seconds": 0.0,
        "usage": None,
        "server_crash_count": 0,
        "server_crash_history": [],
    }
    last_err: str | None = None
    t_start = time.time()

    # Inject a unique nonce into the last user message to break LCP
    # cache matching. Done once, outside the retry loop, so all
    # retries for a single logical call share one nonce (the actual
    # LCP-breaking effect is achieved just by having a unique prefix).
    if request_nonce and messages and messages[-1].get("role") in ("user", "assistant"):
        prefix = f"<!-- req={request_nonce} -->\n"
        last = messages[-1]
        messages = list(messages)
        messages[-1] = {**last, "content": prefix + (last.get("content") or "")}

    for server_round in range(max_server_crashes + 1):
        last_err = None
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
                last_err = err
                if _is_server_crash(err):
                    # Bail out of the inner retry loop; the outer
                    # server-crash loop will handle this.
                    break
                time.sleep(backoff_base * (attempt + 1))
                continue
            msg = resp.choices[0].message
            content = (msg.content or "") if msg else ""
            reasoning = (getattr(msg, "reasoning_content", "") or "") if msg else ""
            finish_reason = resp.choices[0].finish_reason
            usage = resp.usage.model_dump() if getattr(resp, "usage", None) and hasattr(resp.usage, "model_dump") else None
            debug["raw_content"] = content
            debug["raw_reasoning"] = reasoning
            debug["finish_reason"] = finish_reason
            debug["usage"] = usage
            # If content is empty, fall back to reasoning_content (LM Studio
            # reasoning-content bug). The reasoning may be a few KB of
            # thinking prose followed by the JSON.
            if content.strip():
                cleaned = strip_think_tags(content)
            else:
                cleaned = strip_think_tags(reasoning)
                last_err = "content_empty_fallback_to_reasoning"
            debug["raw_combined"] = cleaned
            block = extract_json_object(cleaned)
            debug["block"] = block
            if block is None:
                if last_err is None:
                    last_err = "no_json_in_response"
                time.sleep(backoff_base * (attempt + 1))
                continue
            try:
                parsed = json.loads(block)
            except json.JSONDecodeError as e:
                last_err = f"json_decode: {e}"
                time.sleep(backoff_base * (attempt + 1))
                continue
            debug["elapsed_seconds"] = round(time.time() - t_start, 2)
            return parsed, debug

        # Inner retry loop exited without success. Decide whether
        # this is a server crash we should recover from.
        if last_err is None:
            last_err = "exhausted_retries"
        if not _is_server_crash(last_err):
            break
        if server_round >= max_server_crashes:
            break
        # Server crash — sleep, wait for the model to come back, retry.
        debug["server_crash_count"] = server_round + 1
        debug["server_crash_history"].append(
            f"round={server_round + 1} err={last_err[:120]} sleep={server_backoff:.0f}s"
        )
        if len(debug["server_crash_history"]) > 10:
            debug["server_crash_history"] = debug["server_crash_history"][-10:]
        time.sleep(server_backoff)
        recovered = wait_for_server_ready(
            client,
            model_id=model,
            max_wait=server_recovery_timeout,
        )
        if not recovered:
            last_err = f"server_unrecoverable_after_{server_recovery_timeout:.0f}s: {last_err}"
            break
        # Loop again with a fresh attempt budget.

    debug["elapsed_seconds"] = round(time.time() - t_start, 2)
    if debug["server_crash_count"] >= max_server_crashes and _is_server_crash(last_err):
        debug["error"] = f"server_crash_exhausted({max_server_crashes}): {last_err}"
    else:
        debug["error"] = last_err or "exhausted_retries"
    return None, debug


def log_failure(
    debug_dir: Path,
    article_id: int | str,
    *,
    raw_content: str,
    raw_reasoning: str,
    parsed: Any,
    error: str | None,
    block: str | None,
    extra: dict | None = None,
) -> None:
    """Write a per-article diagnostic JSON to `debug_dir/<article_id>.json`.

    Always called on failure paths, so the user can inspect raw
    HTTP responses in `tmp/wiki_*_debug/` after any failed run.
    """
    debug_dir.mkdir(parents=True, exist_ok=True)
    payload: dict = {
        "article_id": int(article_id) if isinstance(article_id, (int, str)) and str(article_id).lstrip("-").isdigit() else article_id,
        "raw_content": raw_content[:2000],
        "raw_reasoning": raw_reasoning[:1000],
        "parsed": parsed,
        "block": block[:500] if block else None,
        "error": error,
        "finish_reason": (extra or {}).get("finish_reason"),
    }
    if extra:
        payload.update(extra)
    out = debug_dir / f"{article_id}.json"
    try:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def print_progress(
    *,
    done: int,
    total: int,
    n_kept: int = 0,
    n_rejected: int = 0,
    n_failed: int = 0,
    extra: str = "",
    width: int = 20,
) -> None:
    """Print a one-line progress meter with percentage + bar.

    Used by all LLM scripts to give the user a real-time update.
    """
    pct = 100.0 * done / max(total, 1)
    bar_filled = int(width * pct / 100.0)
    bar = "█" * bar_filled + "░" * (width - bar_filled)
    rate_text = ""
    if extra:
        rate_text = f"  {extra}"
    print(
        f"  [{bar}] {done:>5}/{total}  ({pct:5.1f}%)  "
        f"kept={n_kept}  rejected={n_rejected}  failed={n_failed}{rate_text}",
        flush=True,
    )


def _extract_json_array(text: str) -> str | None:
    """Return the first balanced top-level JSON array substring, or None."""
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


def call_chat_batched(
    client,
    *,
    model: str,
    prompt: str,
    expected_n: int,
    temperature: float = 0.0,
    seed: int = 42,
    max_tokens: int = 200,
    timeout: float = 120.0,
    max_retries: int = 3,
    max_server_crashes: int = 5,
) -> tuple[list[dict] | None, dict]:
    """Call Ollama chat.completions with a batched multi-article prompt.

    The model is expected to return a JSON array of `expected_n` objects.
    Returns (parsed_list, debug) where parsed_list is a list of dicts (one
    per article, in order) or None on failure. `debug` mirrors
    `call_chat_with_json_parse` but tracks a JSON-array parse instead of
    a single-object parse.

    Retries with exponential backoff on bad-array or empty responses, and
    triggers server-crash recovery (sleep, wait for the model to come
    back) on LM Studio / Ollama unload / channel errors.
    """
    debug: dict = {
        "raw_content": "",
        "raw_reasoning": "",
        "raw_combined": "",
        "block": None,
        "error": None,
        "finish_reason": None,
        "elapsed_seconds": 0.0,
        "server_crash_count": 0,
        "server_crash_history": [],
    }
    last_err: str | None = None
    t_start = time.time()

    messages = [
        {"role": "system", "content": "You are a precise information-extraction assistant. Respond only with a JSON array."},
        {"role": "user", "content": prompt},
    ]

    for server_round in range(max_server_crashes + 1):
        last_err = None
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
                last_err = err
                if _is_server_crash(err):
                    break
                time.sleep(1.5 * (attempt + 1))
                continue
            msg = resp.choices[0].message
            content = (msg.content or "") if msg else ""
            reasoning = (getattr(msg, "reasoning_content", "") or "") if msg else ""
            finish_reason = resp.choices[0].finish_reason
            debug["raw_content"] = content
            debug["raw_reasoning"] = reasoning
            debug["finish_reason"] = finish_reason
            if content.strip():
                cleaned = strip_think_tags(content)
            else:
                cleaned = strip_think_tags(reasoning)
                last_err = "content_empty_fallback_to_reasoning"
            debug["raw_combined"] = cleaned
            block = _extract_json_array(cleaned)
            debug["block"] = block
            if block is None:
                if last_err is None:
                    last_err = "no_json_array_in_response"
                time.sleep(1.5 * (attempt + 1))
                continue
            try:
                parsed = json.loads(block)
            except json.JSONDecodeError as e:
                last_err = f"json_decode: {e}"
                time.sleep(1.5 * (attempt + 1))
                continue
            if not isinstance(parsed, list):
                last_err = f"not_a_list: {type(parsed).__name__}"
                time.sleep(1.5 * (attempt + 1))
                continue
            if len(parsed) != expected_n:
                last_err = f"array_length_mismatch: expected {expected_n}, got {len(parsed)}"
                time.sleep(1.5 * (attempt + 1))
                continue
            debug["elapsed_seconds"] = round(time.time() - t_start, 2)
            return parsed, debug

        if last_err is None:
            last_err = "exhausted_retries"
        if not _is_server_crash(last_err):
            break
        if server_round >= max_server_crashes:
            break
        debug["server_crash_count"] = server_round + 1
        debug["server_crash_history"].append(
            f"round={server_round + 1} err={last_err[:120]} sleep=15.0s"
        )
        if len(debug["server_crash_history"]) > 10:
            debug["server_crash_history"] = debug["server_crash_history"][-10:]
        time.sleep(15.0)
        recovered = wait_for_server_ready(
            client,
            model_id=model,
            max_wait=120.0,
        )
        if not recovered:
            last_err = f"server_unrecoverable_after_120s: {last_err}"
            break

    debug["elapsed_seconds"] = round(time.time() - t_start, 2)
    if debug["server_crash_count"] >= max_server_crashes and _is_server_crash(last_err):
        debug["error"] = f"server_crash_exhausted({max_server_crashes}): {last_err}"
    else:
        debug["error"] = last_err or "exhausted_retries"
    return None, debug
