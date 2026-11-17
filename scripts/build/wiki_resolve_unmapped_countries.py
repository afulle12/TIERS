"""Stage 6 of the Wikipedia tier-extraction pipeline: country resolution LLM.

Reads the aggregated dyad-year CSV from stage 5
(`data/processed/conflict_dyads_wikipedia.csv`) and looks for rows
where `unresolved = True` (one or both country names failed the
canonical list lookup in the aggregator). For each unique
unresolved country name, asks an LLM (Ollama, nemotron-3-nano:4b
by default) which canonical entry in the country list it best
maps to.

Resolution policy (per spec):

  - The unresolved country names are saved as-is in the original
    column.
  - After the LLM picks a match, the column is updated to:
        "Resolved Name (raw: Original Name)"
    e.g. "Russia (raw: Russian Empire)".
  - For DOWNSTREAM consumers (joins, GWN lookups, etc.), the
    parenthetical is treated as if it does not exist — only the
    "Resolved Name" before the parenthesis is used.

Only the unresolved rows are sent to the LLM. Resolved rows are
passed through unchanged.

n_parallel default is 5 (conservative).

Inputs:
  - data/processed/conflict_dyads_wikipedia.csv (from stage 5)
  - data/processed/wiki_country_canonical.csv
  - Ollama at $OLLAMA_BASE_URL/v1

Outputs:
  - data/processed/conflict_dyads_wikipedia.csv  (overwritten in place
    with the resolved names; resolved columns updated; `unresolved` set
    to False for rows the LLM resolved)
  - tmp/wiki_country_resolution.json  (LLM picks, for review)
  - tmp/wiki_country_resolution_run.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = ROOT / "data" / "processed"
TMP = ROOT / "tmp"

WIKI_CSV = DATA_PROCESSED / "conflict_dyads_wikipedia.csv"
CANONICAL_CSV = DATA_PROCESSED / "wiki_country_canonical.csv"
RESOLUTION_JSON = TMP / "wiki_country_resolution.json"
RUN_JSON = TMP / "wiki_country_resolution_run.json"

OLLAMA_DEFAULT_URL = "http://192.168.86.18:1234/v1"
DEFAULT_MODEL = "nemotron-3-nano:4b"
DEFAULT_N_PARALLEL = 5

# Out cols (must match stage 5)
OUT_COLUMNS = [
    "year", "initiator", "target", "hostlev", "uiw_tier", "tier_label",
    "initiator_gwno", "target_gwno", "source", "conflict_id", "dyad_id",
    "in_conflict", "side_backed", "intensity_level", "D_k", "attribution",
    "selective", "targeted", "corroborated", "incompatibility",
    "territory_name", "region", "n_conflicts_aggregated", "explanation",
    "start_year", "end_year", "year_status", "pair_confidence",
    "n_pairs_in_conflict", "article_id", "unresolved",
]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wiki", default=str(WIKI_CSV))
    p.add_argument("--canonical", default=str(CANONICAL_CSV))
    p.add_argument("--out", default=str(WIKI_CSV),
                   help="Where to write the resolved CSV (overwrites input by default).")
    p.add_argument("--resolution", default=str(RESOLUTION_JSON))
    p.add_argument("--run-meta", default=str(RUN_JSON))
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
    p.add_argument("--max-tokens", type=int, default=2000)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--per-call-timeout", type=float, default=120.0)
    p.add_argument("--max-server-crashes", type=int, default=5)
    return p.parse_args()


def _load_canonical(path: str) -> tuple[list[str], dict[str, dict]]:
    """Returns (canonical_names, alias_to_meta). canonical_names is the
    sorted list of canonical country names for the LLM prompt."""
    alias_to_meta: dict[str, dict] = {}
    canonicals: list[str] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            cn = (row.get("canonical_name") or "").strip()
            if not cn:
                continue
            canonicals.append(cn)
            try:
                gw = int(row["gwcode"]) if row.get("gwcode") else None
            except ValueError:
                gw = None
            try:
                start = int(row.get("start_year", "1816"))
            except ValueError:
                start = 1816
            try:
                end = int(row.get("end_year", "2099"))
            except ValueError:
                end = 2099
            meta = {
                "canonical": cn,
                "gwcode": gw,
                "qid": row.get("wikidata_qid", ""),
                "start_year": start,
                "end_year": end,
            }
            for a in (row.get("aliases") or "").split("|"):
                a = a.strip().lower()
                if a:
                    alias_to_meta.setdefault(a, meta)
            alias_to_meta.setdefault(cn.lower(), meta)
    canonicals.sort()
    return canonicals, alias_to_meta


def _strip_paren(s: str) -> str:
    """Strip anything in parentheses from a country name. Used to
    detect the "raw" portion vs the resolved portion."""
    return re.sub(r"\s*\(.*?\)\s*", "", s).strip()


def _parse_args_alias() -> str | None:
    return None


sys.path.insert(0, str(Path(__file__).resolve().parent))
from wiki_llm_helpers import call_chat_with_json_parse, make_request_nonce


def _build_prompt(raw_name: str, canonicals: list[str]) -> str:
    n = len(canonicals)
    # Cap the list size to keep the prompt reasonable. 290 canonical
    # names fit comfortably in ~3K tokens.
    canon_block = "\n".join(f"  - {c}" for c in canonicals)
    return (
        f"You are a precise entity-resolution assistant. Given a country "
        f"name extracted from a Wikipedia article about an interstate conflict, "
        f"pick the canonical country it best maps to from the list below.\n\n"
        f"Input country name: {raw_name!r}\n\n"
        f"Canonical country list ({n} entries):\n{canon_block}\n\n"
        f"Rules:\n"
        f"  - If the input is a clear alias or historical variant of a canonical "
        f"name (e.g. 'Russian Empire' -> 'Russia', 'USSR' -> 'Russia', "
        f"'U.S.A.' -> 'United States of America'), return that canonical name.\n"
        f"  - If the input is a sub-national entity, region, or non-state actor "
        f"(e.g. 'Kurdistan', 'Taliban', 'European Union'), return null.\n"
        f"  - If the input is ambiguous or doesn't appear to be a sovereign "
        f"state, return null.\n"
        f"  - Match the exact spelling of the canonical name (case-insensitive).\n\n"
        f"Output a single JSON object: "
        f'{{"canonical": "<name from list>" | null, "confidence": <float 0-1>, '
        f'"reason": "<≤15 words>"}}\n'
    )


def _parse_resolution(raw: str) -> dict | None:
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
    canon = obj.get("canonical")
    if canon is not None:
        canon = str(canon).strip()
        if canon.lower() in {"null", "none", ""}:
            canon = None
    conf = obj.get("confidence", 0.0)
    try:
        conf = max(0.0, min(1.0, float(conf)))
    except (TypeError, ValueError):
        conf = 0.0
    reason = str(obj.get("reason") or "").strip()[:200]
    return {"canonical": canon, "confidence": conf, "reason": reason}


def main() -> int:
    args = _parse_args()

    print("=" * 72)
    print("Wikipedia country resolution (LLM, stage 6)")
    print("=" * 72)

    if not Path(args.wiki).exists():
        print(f"Missing input: {args.wiki}", file=sys.stderr)
        return 1
    if not Path(args.canonical).exists():
        print(f"Missing input: {args.canonical}", file=sys.stderr)
        return 1

    canonicals, alias_to_meta = _load_canonical(args.canonical)
    print(f"Loaded {len(canonicals):,} canonical country names")

    with open(args.wiki, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows):,} dyad-year rows from {args.wiki}")

    # Find unique unresolved country names
    unresolved: dict[str, int] = {}
    for r in rows:
        if r.get("unresolved", "").lower() not in {"true", "1", "yes"}:
            continue
        # raw name is whatever's in initiator/target (not yet been
        # wrapped with parens)
        for col in ("initiator", "target"):
            v = (r.get(col) or "").strip()
            if v and _strip_paren(v).lower() not in {c.lower() for c in canonicals}:
                # Strip any prior "(raw: ...)" suffix that might have
                # been written by a previous stage 6 run
                clean = re.sub(r"\s*\(raw:.*?\)\s*$", "", v).strip()
                unresolved[clean] = unresolved.get(clean, 0) + 1
    print(f"Unique unresolved country names: {len(unresolved):,}")
    if not unresolved:
        print("Nothing to resolve. Exiting.")
        # Still write the run meta and resolution file
        with open(args.resolution, "w") as f:
            json.dump({}, f, indent=2)
        with open(args.run_meta, "w") as f:
            json.dump({
                "n_unresolved_names": 0,
                "n_resolved": 0,
                "n_unresolved_after": 0,
                "elapsed_seconds": 0.0,
                "model": args.model,
            }, f, indent=2)
        return 0

    # Connect to Ollama
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

    import concurrent.futures as cf

    # Build lookup of (raw_name -> resolved_canonical) via LLM
    raw_names = list(unresolved.keys())
    print(f"Asking LLM to resolve {len(raw_names):,} unique names...")

    resolution: dict[str, dict] = {}

    def _process_one(raw: str) -> tuple[str, dict | None, dict]:
        prompt = _build_prompt(raw, canonicals)
        messages = [
            {"role": "system", "content": "You are a precise entity-resolution assistant. Respond only with a single JSON object."},
            {"role": "user", "content": prompt},
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
        if parsed is None:
            return raw, None, debug
        # The helper may return a dict, list, etc. We expect a dict.
        if isinstance(parsed, dict):
            r = _parse_resolution(json.dumps(parsed))
        else:
            r = _parse_resolution(str(parsed))
        return raw, r, debug

    t_start = time.time()
    done = 0
    n_resolved = 0
    n_failed = 0

    with cf.ThreadPoolExecutor(max_workers=args.n_parallel) as ex:
        futures = {ex.submit(_process_one, n): n for n in raw_names}
        for fut in cf.as_completed(futures):
            raw, r, debug = fut.result()
            done += 1
            if r is not None and r.get("canonical") is not None:
                resolution[raw] = r
                n_resolved += 1
            else:
                n_failed += 1
            if done % 10 == 0 or done == len(raw_names):
                elapsed = time.time() - t_start
                rate = done / max(elapsed, 1e-6)
                eta = (len(raw_names) - done) / max(rate, 1e-6)
                print(
                    f"  [{done:>4}/{len(raw_names)}]  resolved={n_resolved:>4}  "
                    f"failed={n_failed:>4}  rate={rate:.1f}/s  eta={eta/60:.1f}m",
                    flush=True,
                )

    elapsed = time.time() - t_start
    print(f"LLM resolution done in {elapsed:.0f}s. {n_resolved}/{len(raw_names)} resolved.")

    # Apply resolutions to the rows
    print()
    print("Applying resolutions to dyad-year rows...")
    canon_lookup = {c.lower(): c for c in canonicals}
    n_updated = 0
    n_still_unresolved = 0
    for r in rows:
        if r.get("unresolved", "").lower() not in {"true", "1", "yes"}:
            continue
        for col in ("initiator", "target"):
            v = (r.get(col) or "").strip()
            if not v:
                continue
            clean = re.sub(r"\s*\(raw:.*?\)\s*$", "", v).strip()
            res = resolution.get(clean)
            if res is None or res.get("canonical") is None:
                continue
            resolved_canon = res["canonical"]
            # If the LLM picked a name that's already in the
            # canonical list, use it as-is. Otherwise warn.
            if resolved_canon.lower() in canon_lookup:
                resolved_canon = canon_lookup[resolved_canon.lower()]
            # Write as "Resolved (raw: Original)" per spec
            new_val = f"{resolved_canon} (raw: {clean})"
            if new_val != v:
                r[col] = new_val
                n_updated += 1
        # If both columns now have a canonical part (the text before
        # the parenthesis), mark the row as resolved.
        i_pre = _strip_paren(r.get("initiator", "")).lower()
        t_pre = _strip_paren(r.get("target", "")).lower()
        if i_pre in canon_lookup and t_pre in canon_lookup:
            r["unresolved"] = "False"
            r["initiator_gwno"] = alias_to_meta[i_pre]["gwcode"]
            r["target_gwno"] = alias_to_meta[t_pre]["gwcode"]
            r["initiator"] = f"{canon_lookup[i_pre]} (raw: {_strip_paren(r['initiator'])})"
            r["target"] = f"{canon_lookup[t_pre]} (raw: {_strip_paren(r['target'])})"
        else:
            n_still_unresolved += 1

    # Write the updated CSV
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in OUT_COLUMNS})
    print(f"Wrote {args.out} ({len(rows):,} rows; {n_updated} cells updated; {n_still_unresolved} still unresolved)")

    # Persist resolution JSON
    with open(args.resolution, "w", encoding="utf-8") as f:
        json.dump(resolution, f, indent=2, ensure_ascii=False)
    print(f"Resolution map -> {args.resolution}")

    # Run meta
    with open(args.run_meta, "w", encoding="utf-8") as f:
        json.dump({
            "n_unresolved_names": len(raw_names),
            "n_resolved": n_resolved,
            "n_failed": n_failed,
            "n_rows_updated": n_updated,
            "n_rows_still_unresolved": n_still_unresolved,
            "elapsed_seconds": round(elapsed, 1),
            "model": chosen,
            "base_url": args.base_url,
            "n_parallel": args.n_parallel,
        }, f, indent=2)
    print(f"Run meta -> {args.run_meta}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
