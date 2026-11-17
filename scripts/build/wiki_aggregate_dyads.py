"""Stage 5 of the Wikipedia tier-extraction pipeline: aggregator.

Pure-Python, no LLM. Combines the per-article output of stage 4
(`tmp/wiki_t45_extracted.jsonl`) into the final directed-dyad-year
table aligned to the v27.0 spec scheme (T1=1, T2=2, T3=3, T4=4, T5=5).

Key behavior:

  1. For each article, for each directed (initiator, target) pair:
     - Apply the per-pair confidence threshold (default 0.7).
     - Apply an extra -0.2 discount to `implied: true` pairs.
     - Resolve (initiator, target) country names to GWN codes via
       `wiki_country_canonical.csv`. Unresolved pairs are emitted
       with `gwno = null` and `unresolved = true` so stage 6 can
       try to map them later.
  2. For each surviving pair, expand the article's `[start_year,
     end_year]` range into one row per year:
     - both years known: emit one row per year in [start, end]
     - start missing, end known: emit ONE row with year=end,
       year_status="unknown_start"
     - end missing, start known: emit ONE row with year=start,
       year_status="unknown_end"
     - both missing: emit ONE row with year=-1 (sentinel),
       year_status="unknown"
  3. When two articles produce rows for the same (year, ig, tg),
     keep the row with the higher tier; ties break on the longer
     explanation, then on the higher pair_confidence.

Output schema (24 columns, matches conflict_dyads.csv + 4 new):
  year, initiator, target, hostlev, uiw_tier, tier_label,
  initiator_gwno, target_gwno, source, conflict_id, dyad_id,
  in_conflict, side_backed, intensity_level, D_k, attribution,
  selective, targeted, corroborated, incompatibility,
  territory_name, region, n_conflicts_aggregated, explanation,
  start_year, end_year, year_status, pair_confidence,
  n_pairs_in_conflict, article_id, unresolved

Inputs:
  - tmp/wiki_t45_extracted.jsonl   (from stage 4)
  - data/processed/wiki_country_canonical.csv
  - data/processed/wiki_gwn_map.csv (optional, for cross-checking)
  - data/processed/conflict_dyads_full.csv (for the mismatch analysis
    that stage 7 reads)

Outputs:
  - data/processed/conflict_dyads_wikipedia.csv (24+ columns)
  - data/processed/conflict_dyads_wikipedia.parquet
  - tmp/wiki_year_tier_counts.csv
  - tmp/wiki_mismatch_pairs.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = ROOT / "data" / "processed"
TMP = ROOT / "tmp"

CANONICAL_CSV = DATA_PROCESSED / "wiki_country_canonical.csv"
GROUND_TRUTH_CSV = DATA_PROCESSED / "conflict_dyads_full.csv"
EXTRACTED_JSONL = TMP / "wiki_t45_extracted.jsonl"
OUT_CSV = DATA_PROCESSED / "conflict_dyads_wikipedia.csv"
OUT_PARQUET = DATA_PROCESSED / "conflict_dyads_wikipedia.parquet"
YEAR_COUNTS_CSV = TMP / "wiki_year_tier_counts.csv"
MISMATCH_JSONL = TMP / "wiki_mismatch_pairs.jsonl"
UNRESOLVED_LOG = TMP / "wiki_unresolved_pairs.log"

# v27.0 spec scheme
TIER_RANK = {"T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5}
TIER_LABEL = {
    "T1": "T1-Diplomatic Crisis",
    "T2": "T2-Economic Coercion",
    "T3": "T3-Proxy/Indirect Military",
    "T4": "T4-Limited Military",
    "T5": "T5-Strategic War",
}

# Year-status sentinels (column stays int; status flag in year_status)
YEAR_UNKNOWN_SENTINEL = -1  # only used when both start and end are null

# Output schema
OUT_COLUMNS = [
    # 24 columns from conflict_dyads.csv (kept in order)
    "year",
    "initiator",
    "target",
    "hostlev",
    "uiw_tier",
    "tier_label",
    "initiator_gwno",
    "target_gwno",
    "source",
    "conflict_id",
    "dyad_id",
    "in_conflict",
    "side_backed",
    "intensity_level",
    "D_k",
    "attribution",
    "selective",
    "targeted",
    "corroborated",
    "incompatibility",
    "territory_name",
    "region",
    "n_conflicts_aggregated",
    "explanation",
    # 7 new columns
    "start_year",
    "end_year",
    "year_status",
    "pair_confidence",
    "n_pairs_in_conflict",
    "article_id",
    "unresolved",
]

# Floor / ceiling for expansion
YEAR_FLOOR = 1900
YEAR_CEIL = 2025


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--extracted", default=str(EXTRACTED_JSONL))
    p.add_argument("--canonical", default=str(CANONICAL_CSV))
    p.add_argument("--ground-truth", default=str(GROUND_TRUTH_CSV))
    p.add_argument("--out", default=str(OUT_CSV))
    p.add_argument("--out-parquet", default=str(OUT_PARQUET))
    p.add_argument("--year-counts", default=str(YEAR_COUNTS_CSV))
    p.add_argument("--mismatch", default=str(MISMATCH_JSONL))
    p.add_argument("--unresolved-log", default=str(UNRESOLVED_LOG))
    p.add_argument("--year-min", type=int, default=YEAR_FLOOR)
    p.add_argument("--year-max", type=int, default=YEAR_CEIL)
    p.add_argument(
        "--min-confidence",
        type=float,
        default=0.7,
        help="Drop per-pair events below this confidence floor (after implied discount).",
    )
    p.add_argument(
        "--implied-discount",
        type=float,
        default=0.2,
        help="Subtract this from the confidence of any pair marked implied: true.",
    )
    return p.parse_args()


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


def _load_canonical(path: str) -> dict[str, dict]:
    """{lowercase alias: {canonical, gwcode, qid, start_year, end_year}}"""
    out: dict[str, dict] = {}
    if not Path(path).exists():
        return out
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            aliases = [a.strip() for a in row["aliases"].split("|") if a.strip()]
            try:
                gw = int(row["gwcode"]) if row["gwcode"] else None
            except ValueError:
                gw = None
            try:
                start = int(row["start_year"])
            except ValueError:
                start = 1816
            try:
                end = int(row["end_year"])
            except ValueError:
                end = 2099
            meta = {
                "canonical": row["canonical_name"],
                "gwcode": gw,
                "qid": row["wikidata_qid"],
                "start_year": start,
                "end_year": end,
            }
            for a in aliases:
                out.setdefault(a.lower(), meta)
    return out


def _resolve_country_name(
    raw: str | None,
    alias_to_meta: dict[str, dict],
    year: int | None,
) -> dict | None:
    """Return {canonical, gwcode, qid} or None.

    Strips parentheticals from the raw name (e.g. "Russia (Soviet
    Union)" -> "Russia") before matching.
    """
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    s_clean = re.sub(r"\s*\(.*?\)\s*", "", s).strip()
    candidates = [s, s_clean, s_clean.replace("the ", "")]
    sorted_aliases = sorted(alias_to_meta.keys(), key=lambda a: -len(a))
    for cand in candidates:
        key = cand.lower()
        for alias in sorted_aliases:
            if re.search(rf"\b{re.escape(alias)}\b", key):
                meta = alias_to_meta[alias]
                if meta["gwcode"] is None:
                    continue
                return {
                    "canonical": meta["canonical"],
                    "gwcode": int(meta["gwcode"]),
                    "qid": meta["qid"],
                }
    return None


def _coerce_int(v) -> int | None:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return int(float(s))
        except (TypeError, ValueError):
            return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _expand_pair_to_rows(
    year: int,
    start_year: int | None,
    end_year: int | None,
    year_status: str,
) -> list[int]:
    """Return the list of year values to emit for one (year, year_status)
    combination. When start and end are both known, the year is already
    one of the range members; this function still returns [year].
    For sentinel rows (year_status != ""), returns [year] directly.
    """
    return [year]


def _load_ground_truth(
    path: str, year_min: int, year_max: int
) -> list[dict]:
    if not Path(path).exists():
        return []
    out: list[dict] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            try:
                year = int(r["year"])
            except (KeyError, ValueError):
                continue
            if not (year_min <= year <= year_max):
                continue
            ig = _coerce_int(r.get("initiator_gwno"))
            tg = _coerce_int(r.get("target_gwno"))
            if ig is None or tg is None or ig == tg:
                continue
            label = r.get("tier_label") or ""
            tier = None
            for t in TIER_RANK:
                if label.startswith(t + "-") or label == t:
                    tier = t
                    break
            if tier is None:
                continue
            out.append({
                "year": year,
                "initiator_gwno": ig,
                "target_gwno": tg,
                "tier": tier,
                "tier_label": label,
                "source": r.get("source") or "",
            })
    return out


def _is_better_candidate(
    new: dict,
    existing: dict,
) -> bool:
    """Decide whether `new` should replace `existing` in the
    aggregated (year, ig, tg) slot.

    Priority: higher tier rank > longer explanation > higher
    pair_confidence.
    """
    new_rank = TIER_RANK[new["uiw_tier_label_to_tier"]]
    old_rank = TIER_RANK[existing["uiw_tier_label_to_tier"]]
    if new_rank != old_rank:
        return new_rank > old_rank
    if len(new["explanation"] or "") != len(existing["explanation"] or ""):
        return len(new["explanation"] or "") > len(existing["explanation"] or "")
    return float(new.get("pair_confidence") or 0.0) > float(existing.get("pair_confidence") or 0.0)


def main() -> int:
    args = _parse_args()

    print("=" * 72)
    print("Wikipedia aggregator (v2, 7-stage pipeline, year_status sentinels)")
    print("=" * 72)

    print(f"[1] Loading canonical country list from {args.canonical}...")
    alias_to_meta = _load_canonical(args.canonical)
    print(f"    {len(alias_to_meta):,} aliases")

    print(f"[2] Loading stage 4 output from {args.extracted}...")
    articles = _load_jsonl(args.extracted)
    print(f"    {len(articles):,} articles")
    if not articles:
        print("    No input. Exiting.")
        return 0

    aggregated: dict[tuple, dict] = {}
    dropped: dict[str, int] = {
        "below_confidence": 0,
        "year_out_of_range": 0,
        "self_dyad": 0,
        "no_year": 0,
    }
    n_pairs_total = 0
    n_pairs_emitted = 0
    n_unresolved_initiator = 0
    n_unresolved_target = 0
    unresolved_examples: list[dict] = []

    print()
    print(f"[3] Expanding (year, initiator, target) tuples...")
    for art in articles:
        tier = art.get("tier")
        if tier not in TIER_RANK:
            continue
        start_year = _coerce_int(art.get("start_year"))
        end_year = _coerce_int(art.get("end_year"))
        if start_year is not None and end_year is not None and end_year < start_year:
            start_year, end_year = end_year, start_year
        explanation = (art.get("explanation") or "").strip()
        pairs = art.get("pairs") or []
        article_id = art.get("article_id")
        n_pairs_in_conflict = len(pairs)

        for pair in pairs:
            n_pairs_total += 1
            initiator_raw = (pair.get("initiator") or "").strip()
            target_raw = (pair.get("target") or "").strip()
            if not initiator_raw or not target_raw:
                continue
            conf = float(pair.get("confidence") or 0.0)
            implied = bool(pair.get("implied"))
            if implied:
                conf = max(0.0, conf - args.implied_discount)
            if conf < args.min_confidence:
                dropped["below_confidence"] += 1
                continue

            ig = _resolve_country_name(initiator_raw, alias_to_meta, start_year or end_year)
            tg = _resolve_country_name(target_raw, alias_to_meta, start_year or end_year)
            ig_resolved = ig is not None
            tg_resolved = tg is not None
            ig_gwcode = ig["gwcode"] if ig_resolved else None
            tg_gwcode = tg["gwcode"] if tg_resolved else None
            ig_canonical = ig["canonical"] if ig_resolved else initiator_raw
            tg_canonical = tg["canonical"] if tg_resolved else target_raw
            if not ig_resolved:
                n_unresolved_initiator += 1
                if len(unresolved_examples) < 50:
                    unresolved_examples.append({
                        "article_id": article_id,
                        "role": "initiator",
                        "raw": initiator_raw,
                        "target_raw": target_raw,
                    })
            if not tg_resolved:
                n_unresolved_target += 1
                if len(unresolved_examples) < 50:
                    unresolved_examples.append({
                        "article_id": article_id,
                        "role": "target",
                        "raw": target_raw,
                        "initiator_raw": initiator_raw,
                    })

            # Skip self-dyads only when both resolved
            if ig_resolved and tg_resolved and ig_gwcode == tg_gwcode:
                dropped["self_dyad"] += 1
                continue

            # Determine year_status and the year values to emit
            if start_year is not None and end_year is not None:
                # Normal case: expand over the full range
                year_status = ""
                years_to_emit = list(range(start_year, end_year + 1))
            elif start_year is None and end_year is not None:
                year_status = "unknown_start"
                years_to_emit = [end_year]
            elif start_year is not None and end_year is None:
                year_status = "unknown_end"
                years_to_emit = [start_year]
            else:
                year_status = "unknown"
                years_to_emit = [YEAR_UNKNOWN_SENTINEL]

            for y in years_to_emit:
                if y == YEAR_UNKNOWN_SENTINEL:
                    # Both years null - skip year range check
                    pass
                elif y < args.year_min or y > args.year_max:
                    dropped["year_out_of_range"] += 1
                    continue

                key = (y, ig_gwcode, tg_gwcode)
                new_row = {
                    "year": y,
                    "initiator": ig_canonical,
                    "target": tg_canonical,
                    "hostlev": TIER_RANK[tier],
                    "uiw_tier": TIER_RANK[tier],
                    "tier_label": TIER_LABEL[tier],
                    "initiator_gwno": ig_gwcode,
                    "target_gwno": tg_gwcode,
                    "source": f"WIKI_{tier}",
                    "explanation": explanation,
                    "start_year": start_year,
                    "end_year": end_year,
                    "year_status": year_status,
                    "pair_confidence": round(conf, 3),
                    "n_pairs_in_conflict": n_pairs_in_conflict,
                    "article_id": article_id,
                    "unresolved": not (ig_resolved and tg_resolved),
                    "uiw_tier_label_to_tier": tier,
                }
                existing = aggregated.get(key)
                if existing is None or _is_better_candidate(new_row, existing):
                    aggregated[key] = new_row
                n_pairs_emitted += 1

    print(f"    total pairs seen: {n_pairs_total:,}")
    print(f"    pairs emitted to aggregated table: {n_pairs_emitted:,}")
    print(f"    unique (year, ig, tg) rows: {len(aggregated):,}")
    print(f"    unresolved initiator: {n_unresolved_initiator:,}")
    print(f"    unresolved target:    {n_unresolved_target:,}")
    print()
    print(f"[4] Dropped events:")
    for k, v in dropped.items():
        print(f"    {k}: {v:,}")

    # Build output rows
    rows: list[dict] = []
    for v in aggregated.values():
        rows.append({k: v.get(k) for k in OUT_COLUMNS})
    rows.sort(key=lambda r: (
        r["year"] if isinstance(r["year"], int) else 9999,
        r["tier_label"] or "",
        r["initiator"] or "",
        r["target"] or "",
    ))

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print()
    print(f"[5] Wrote {args.out} ({len(rows):,} rows)")

    # Parquet
    try:
        import pandas as pd
        df = pd.read_csv(args.out)
        df.to_parquet(args.out_parquet, index=False)
        print(f"    Parquet -> {args.out_parquet}")
    except Exception as e:
        print(f"    Parquet write skipped: {e}")

    # Year counts
    year_counts: dict[tuple[int, str], int] = defaultdict(int)
    for r in rows:
        y = r["year"]
        t = r["tier_label"] or ""
        tier = None
        for tt in TIER_RANK:
            if t.startswith(tt + "-") or t == tt:
                tier = tt
                break
        if tier and isinstance(y, int) and y != YEAR_UNKNOWN_SENTINEL:
            year_counts[(y, tier)] += 1
    with open(args.year_counts, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["year", "tier", "n_rows"])
        w.writeheader()
        for (year, tier), n in sorted(year_counts.items()):
            w.writerow({"year": year, "tier": tier, "n_rows": n})
    print(f"    Year-tier counts -> {args.year_counts}")

    # Unresolved log (for stage 6)
    if unresolved_examples:
        with open(args.unresolved_log, "w", encoding="utf-8") as f:
            for ex in unresolved_examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
        print(f"    Unresolved log -> {args.unresolved_log} ({len(unresolved_examples):,} examples)")

    # Mismatch JSONL (consumed by stage 7)
    print()
    print(f"[6] Computing mismatch pairs (wiki vs ground truth {args.year_min}-{args.year_max})...")
    gt = _load_ground_truth(args.ground_truth, args.year_min, args.year_max)
    wiki_year_set = {
        (k[0], k[1], k[2])
        for k in aggregated.keys()
        if isinstance(k[0], int) and k[0] != YEAR_UNKNOWN_SENTINEL
        and k[1] is not None and k[2] is not None
    }
    gt_set = {(g["year"], g["initiator_gwno"], g["target_gwno"]) for g in gt}
    only_wiki = wiki_year_set - gt_set
    only_gt = gt_set - wiki_year_set
    both = wiki_year_set & gt_set
    print(f"    ground-truth dyad-years in window: {len(gt_set):,}")
    print(f"    wiki dyad-years in window:        {len(wiki_year_set):,}")
    print(f"    only in wiki: {len(only_wiki):,}")
    print(f"    only in GT:   {len(only_gt):,}")
    print(f"    in both:      {len(both):,}")

    gt_by_key = {(g["year"], g["initiator_gwno"], g["target_gwno"]): g for g in gt}
    wiki_by_key = aggregated
    mismatch_rows: list[dict] = []
    for k in sorted(wiki_year_set | gt_set):
        w = wiki_by_key.get(k)
        g = gt_by_key.get(k)
        if w is None and g is not None:
            mismatch_rows.append({
                "wiki_year": None,
                "wiki_initiator": None,
                "wiki_target": None,
                "wiki_tier": None,
                "gt_year": g["year"],
                "gt_initiator": g["initiator_gwno"],
                "gt_target": g["target_gwno"],
                "gt_tier": g["tier"],
                "mismatch_kind": "only_in_ground_truth",
                "notes": "no Wikipedia event in the validation window",
            })
            continue
        if g is None and w is not None:
            mismatch_rows.append({
                "wiki_year": w["year"],
                "wiki_initiator": w["initiator_gwno"],
                "wiki_target": w["target_gwno"],
                "wiki_tier": w["uiw_tier_label_to_tier"],
                "gt_year": None,
                "gt_initiator": None,
                "gt_target": None,
                "gt_tier": None,
                "mismatch_kind": "only_in_wiki",
                "notes": "no ground-truth event in the validation window",
            })
            continue
        w_tier = w["uiw_tier_label_to_tier"]
        g_tier = g["tier"]
        tier_match = w_tier == g_tier
        kind = "match" if tier_match else (
            "tier_over" if TIER_RANK[w_tier] > TIER_RANK[g_tier] else "tier_under"
        )
        mismatch_rows.append({
            "wiki_year": w["year"],
            "wiki_initiator": w["initiator_gwno"],
            "wiki_target": w["target_gwno"],
            "wiki_tier": w_tier,
            "gt_year": g["year"],
            "gt_initiator": g["initiator_gwno"],
            "gt_target": g["target_gwno"],
            "gt_tier": g_tier,
            "tier_match": tier_match,
            "mismatch_kind": kind,
            "notes": f"v27.0={w_tier}, legacy={g_tier}",
        })
    with open(args.mismatch, "w", encoding="utf-8") as f:
        for r in mismatch_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"    Mismatch pairs -> {args.mismatch} ({len(mismatch_rows):,} rows)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
