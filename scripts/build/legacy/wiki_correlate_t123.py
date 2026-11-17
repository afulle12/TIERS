"""Correlate the LLM tier+explanation output with the LLM event-extraction
output. Writes a single per-event CSV that the aggregator consumes.

The tier pass (`wiki_extract_llm_t123_tier.py`) emits one row per article:
    {article_id, tier, hostlev, tier_label, explanation, ...}

The event extractor (`wiki_extract_llm_t123.py`) emits one or more rows
per article:
    {article_id, year, initiator_country, target_country, confidence, ...}

This script joins them on `article_id` and emits one row per event,
copying the article's tier+explanation onto each event. The aggregator
later reads this CSV and produces the final dyad-year CSV.

Inputs:
  - tmp/wiki_t123_tier.jsonl       (per-article tier+explanation)
  - tmp/wiki_t123_extracted.jsonl  (per-event from extractor)

Outputs:
  - tmp/wiki_t123_events.csv
      One row per event with tier+explanation attached.
      Schema:
        article_id,article_title,tier,hostlev,tier_label,
        year,initiator_country,target_country,confidence,explanation,model
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"

TIER_JSONL = TMP / "wiki_t123_tier.jsonl"
EXTRACTED_JSONL = TMP / "wiki_t123_extracted.jsonl"
OUT_CSV = TMP / "wiki_t123_events.csv"

# CSV columns
CSV_COLUMNS = [
    "article_id",
    "article_title",
    "tier",
    "hostlev",
    "tier_label",
    "year",
    "initiator_country",
    "target_country",
    "confidence",
    "explanation",
    "model",
]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tier", default=str(TIER_JSONL))
    p.add_argument("--extracted", default=str(EXTRACTED_JSONL))
    p.add_argument("--out", default=str(OUT_CSV))
    return p.parse_args()


def _load_jsonl(path: Path) -> list[dict]:
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
    return out


def main() -> int:
    args = _parse_args()

    print("=" * 60)
    print("Correlate tier+explanation with extracted events")
    print("=" * 60)

    print(f"[1] Loading tier rows from {args.tier}...")
    tier_rows = _load_jsonl(Path(args.tier))
    print(f"    {len(tier_rows):,} tier rows")

    print(f"[2] Loading extracted events from {args.extracted}...")
    event_rows = _load_jsonl(Path(args.extracted))
    print(f"    {len(event_rows):,} event rows")

    # Build tier lookup: article_id -> {tier, hostlev, tier_label, explanation, model}
    tier_by_aid: dict[int, dict] = {}
    for t in tier_rows:
        aid = t.get("article_id")
        if aid is None:
            continue
        tier_by_aid[int(aid)] = {
            "tier": t.get("tier"),
            "hostlev": t.get("hostlev"),
            "tier_label": t.get("tier_label"),
            "explanation": t.get("explanation", "") or "",
            "model": t.get("model", ""),
        }

    # Drop tier rows for articles that have no events
    matched_articles = {int(e.get("article_id")) for e in event_rows if e.get("article_id") is not None}
    print(f"[3] Articles with events: {len(matched_articles):,}")
    print(f"    Articles with tier but no events: {len(tier_by_aid) - len(matched_articles & set(tier_by_aid.keys())):,}")

    # Write CSV
    print(f"[4] Writing {args.out}...")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    n_written = 0
    n_tier_match = 0
    n_tier_mismatch = 0
    n_no_tier = 0
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for ev in event_rows:
            aid = ev.get("article_id")
            if aid is None:
                continue
            aid_i = int(aid)
            tier_info = tier_by_aid.get(aid_i)
            row_tier = ev.get("tier")
            if tier_info is None:
                # No tier row — fall back to the event's own tier (legacy)
                w.writerow({
                    "article_id": aid_i,
                    "article_title": ev.get("article_title", ""),
                    "tier": row_tier,
                    "hostlev": ev.get("hostlev"),
                    "tier_label": ev.get("tier_label"),
                    "year": ev.get("year"),
                    "initiator_country": ev.get("initiator_country"),
                    "target_country": ev.get("target_country"),
                    "confidence": ev.get("confidence"),
                    "explanation": "",
                    "model": ev.get("model", ""),
                })
                n_no_tier += 1
            else:
                # Tier row exists. Use the tier row's tier/explanation
                # (which is the focused, single-tier call) for
                # consistency. If the extractor emitted a different
                # tier, note the disagreement but use the tier-row
                # tier for the canonical CSV (it's the more recent
                # decision and was the one explicitly asked for).
                if tier_info["tier"] != row_tier and tier_info["tier"] != "NONE" and row_tier is not None:
                    n_tier_mismatch += 1
                w.writerow({
                    "article_id": aid_i,
                    "article_title": ev.get("article_title") or tier_info.get("model", ""),
                    "tier": tier_info["tier"] if tier_info["tier"] != "NONE" else row_tier,
                    "hostlev": tier_info["hostlev"] if tier_info["hostlev"] is not None else ev.get("hostlev"),
                    "tier_label": tier_info["tier_label"] or ev.get("tier_label"),
                    "year": ev.get("year"),
                    "initiator_country": ev.get("initiator_country"),
                    "target_country": ev.get("target_country"),
                    "confidence": ev.get("confidence"),
                    "explanation": tier_info["explanation"],
                    "model": tier_info["model"] or ev.get("model", ""),
                })
                n_tier_match += 1
            n_written += 1

    print()
    print(f"    Wrote {n_written:,} rows")
    print(f"    Tier matches:        {n_tier_match:,}")
    print(f"    Tier mismatches:     {n_tier_mismatch:,}")
    print(f"    No tier row found:   {n_no_tier:,}")
    print()
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
