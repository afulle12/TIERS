"""Extract T4/T5 conflict events from conflict-style Wikipedia infoboxes.

Pure-Python parser. No LLM. Walks the `infoboxes` JSON column of the
candidate set, finds conflict-style infoboxes, pulls the belligerent
field(s) and date field(s), and emits a directed dyad-year event for
each pair of belligerent sovereign states.

This script only produces rows for articles whose primary infobox is
one of the conflict types (military conflict, war, battle, etc.). It
deliberately does not handle T1/T2/T3; those go through the LLM
extractor in `wiki_extract_llm_t123.py`.

Inputs:
  - tmp/wiki_tier_candidates.parquet   (from wiki_filter_candidates.py)
  - data/processed/wiki_country_canonical.csv (alias + GWN map)
  - data/processed/wiki_t5_title_allowlist.csv (hand-curated T5 titles)

Outputs:
  - tmp/wiki_t45_events.jsonl
      One row per (year, initiator_gwno, target_gwno) event, schema:
        {
          "article_id": int,
          "article_title": str,
          "infobox_name": str,
          "year": int,
          "initiator_country": str,
          "initiator_qid": str,
          "initiator_gwno": int,
          "target_country": str,
          "target_qid": str,
          "target_gwno": int,
          "tier": "T4" | "T5",
          "hostlev": int,             # 4 for T4, 5 for T5 (v27.0)
          "start_year": int | null,
          "end_year": int | null,
          "tier_label": str,          # v27.0 label
          "source": "WIKI_T4" | "WIKI_T5",
        }
  - tmp/wiki_t45_diag.json
      Counts and per-tier hit stats.
  - tmp/wiki_t45_t5_candidates.jsonl  (NEW in v2)
      One row per T4 article that is a candidate for upgrade to T5
      (heuristic positives only). The actual upgrade is done by the
      LLM in `wiki_extract_llm_t45_ambiguous.py` (stage 4.5).
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
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
TMP = ROOT / "tmp"

CANDIDATES_PARQUET = TMP / "wiki_tier_candidates.parquet"
CANONICAL_CSV = DATA_PROCESSED / "wiki_country_canonical.csv"
GWN_MAP_CSV = DATA_PROCESSED / "wiki_gwn_map.csv"
CSHAPES_CSV = DATA_RAW / "CShapes-2.0.csv"
T5_ALLOWLIST_CSV = DATA_PROCESSED / "wiki_t5_title_allowlist.csv"
OUT_JSONL = TMP / "wiki_t45_events.jsonl"
DIAG_JSON = TMP / "wiki_t45_diag.json"
T5_CANDIDATES_JSONL = TMP / "wiki_t45_t5_candidates.jsonl"

# Infobox name -> tier. Anything else (or anything not matching) falls
# back to T4. "civil war" / "world war" are explicit T5; "war" by
# itself is also T5; "military conflict" defaults to T4 because that
# infobox is used for both kinds and we want to be conservative.
T4_INFOTYPES = {
    "Infobox military conflict",
    "Infobox battle",
    "Infobox siege",
    "Infobox military operation",
    "Infobox armed conflict",
    "Infobox revolution",
    "Infobox insurgency",
    "Infobox terrorist attack",
    "Infobox airstrike",
    "Infobox conflict",
    "Infobox coup",
}
T5_INFOTYPES = {
    "Infobox war",
    "Infobox civil war",
    "Infobox world war",
}

# T5 candidate heuristic: title keywords that suggest strategic war.
T5_TITLE_KEYWORDS_RE = re.compile(
    r"\b(?:war|world war|civil war|invasion|occupation|conflict)\b",
    re.IGNORECASE,
)

# Infobox field names (case insensitive) that hold belligerent lists.
# We try each name in order; first one with non-empty content wins.
BELLIGERENT_FIELD_NAMES = [
    "combatant1",
    "combatant 1",
    "belligerent1",
    "belligerent 1",
    "side1",
    "side 1",
    "combatants",
    "belligerents",
    "parties",
    "combatants1",
]
BELLIGERENT2_FIELD_NAMES = [
    "combatant2",
    "combatant 2",
    "belligerent2",
    "belligerent 2",
    "side2",
    "side 2",
    "combatants2",
]
# Some infoboxes (military operation) use a single combined "forces"
# or "units" field; we do not try to split it.
FORCE_FIELD_NAMES = ["forces1", "forces 1", "forces2", "forces 2"]

DATE_FIELD_NAMES = [
    "date",
    "start date",
    "end date",
    "started",
    "ended",
    "year",
    "time",
    "period",
]

# Tier label and hostlev mapping, matching the existing conflict_dyads.csv
# schema (see DATA_PROVENANCE.md).
TIER_INFO = {
    "T4": {"tier_label": "T4-Limited Military", "hostlev": 4},
    "T5": {"tier_label": "T5-Strategic War", "hostlev": 5},
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidates", default=str(CANDIDATES_PARQUET))
    p.add_argument("--canonical", default=str(CANONICAL_CSV))
    p.add_argument("--gwn-map", default=str(GWN_MAP_CSV))
    p.add_argument("--cshapes-csv", default=str(CSHAPES_CSV))
    p.add_argument("--t5-allowlist", default=str(T5_ALLOWLIST_CSV))
    p.add_argument("--out", default=str(OUT_JSONL))
    p.add_argument("--diag", default=str(DIAG_JSON))
    p.add_argument("--t5-candidates", default=str(T5_CANDIDATES_JSONL))
    p.add_argument(
        "--max-articles",
        type=int,
        default=0,
        help="Optional cap on articles to process (0 = no cap).",
    )
    return p.parse_args()


def _classify_infobox(name: str) -> str | None:
    """Return 'T4' or 'T5' based on the infobox template name, or None
    if the infobox is not a conflict-style one we handle."""
    if not name:
        return None
    if name in T5_INFOTYPES:
        return "T5"
    if name in T4_INFOTYPES:
        return "T4"
    return None


def _walk_infobox_fields(infobox: dict) -> list[dict]:
    """Yield all field nodes (type=='field') under an infobox, regardless
    of how deeply nested the section/part structure is."""
    out: list[dict] = []

    def _visit(node: object) -> None:
        if isinstance(node, dict):
            if node.get("type") == "field":
                out.append(node)
            for child in node.get("has_parts") or []:
                _visit(child)
        elif isinstance(node, list):
            for child in node:
                _visit(child)

    _visit(infobox)
    return out


def _field_name(field: dict) -> str:
    n = field.get("name") or field.get("label") or ""
    if isinstance(n, str):
        return n.strip().lower()
    return ""


def _field_links(field: dict) -> list[str]:
    """Return link texts from a field, preferring 'links' to 'value'."""
    out: list[str] = []
    for link in field.get("links") or []:
        if isinstance(link, dict):
            t = link.get("text")
            if isinstance(t, str) and t.strip():
                out.append(t.strip())
    return out


def _field_text(field: dict) -> str:
    v = field.get("value")
    return v if isinstance(v, str) else ""


def _extract_belligerents(infobox: dict) -> tuple[list[str], list[str]]:
    """Return (side1_strings, side2_strings). Each side is a list of
    raw country-name strings as found in the infobox.

    Two infobox patterns are supported:

    1. **Named-field pattern** (older Wikipedia): fields with names
       like "Combatant1" / "Combatant2" hold the belligerent lists as
       their values. Links inside the field give precise names.

    2. **Paired-field pattern** (newer Wikipedia, more common in
       current dumps): a "Belligerents" section header field is
       followed by one or more fields whose `name` is side 1 and
       whose `value` is side 2. Links inside give precise names.
       Example:
         {"type":"field","value":"Belligerents"},
         {"type":"field","name":"Kingdom of Spain",
          "value":"Carlist insurgents",
          "links":[{"text":"Kingdom of Spain",...},
                   {"text":"Carlist",...}]}

    If both patterns are present, the named-field pattern wins
    because it is more reliable.
    """
    fields = _walk_infobox_fields(infobox)

    def _first_field_with(name_options: list[str]) -> dict | None:
        for f in fields:
            if _field_name(f) in name_options:
                return f
        return None

    def _side(field: dict) -> list[str]:
        links = _field_links(field)
        if links:
            return links
        text = _field_text(field)
        if not text:
            return []
        parts = re.split(r"<br ?/?>|\n|\s*[|·•]\s*|\s{2,}|;\s*", text)
        return [p.strip() for p in parts if p.strip()]

    # Pattern 1: named belligerent fields.
    s1_field = _first_field_with(BELLIGERENT_FIELD_NAMES)
    s2_field = _first_field_with(BELLIGERENT2_FIELD_NAMES)
    if s1_field is not None or s2_field is not None:
        s1 = _side(s1_field) if s1_field else []
        s2 = _side(s2_field) if s2_field else []
        return s1, s2

    # Pattern 2: paired fields after a "Belligerents" section header.
    s1: list[str] = []
    s2: list[str] = []
    in_belligerents = False
    for f in fields:
        name = _field_name(f)
        if not in_belligerents:
            # The section header is a field with empty name and value
            # matching "Belligerents" (case-insensitive).
            if name == "" and _field_text(f).strip().lower() == "belligerents":
                in_belligerents = True
            continue
        # Once we hit the next section header (empty name + non-empty
        # value that isn't a belligerent label), stop.
        if name == "" and _field_text(f).strip():
            break
        # A paired belligerent field has both name and value (or links).
        side1_links = _field_links(f)[:1]
        side2_links = _field_links(f)[1:2]
        if side1_links:
            s1.extend(side1_links)
        elif name:
            s1.append(name)
        if side2_links:
            s2.extend(side2_links)
        else:
            v = _field_text(f).strip()
            if v:
                s2.append(v)
    return s1, s2


def _extract_dates(infobox: dict) -> tuple[int | None, int | None]:
    """Return (start_year, end_year) parsed from date-style fields.
    Tries dateparser; falls back to a regex on the raw value."""
    import dateparser

    fields = _walk_infobox_fields(infobox)
    out: dict[str, int | None] = {"start": None, "end": None}
    year_re = re.compile(r"\b(\d{3,4})\b")

    for f in fields:
        name = _field_name(f)
        if not any(d in name for d in ("date", "started", "ended", "year", "time", "period")):
            continue
        text = _field_text(f)
        if not text:
            continue
        for piece in re.split(r"<br ?/?>|\n| - | to | – ", text):
            piece = piece.strip()
            if not piece:
                continue
            try:
                dt = dateparser.parse(piece, settings={"PREFER_DATES_FROM": "past"})
            except Exception:
                dt = None
            year: int | None = None
            if dt is not None:
                year = dt.year
            if year is None:
                m = year_re.search(piece)
                if m:
                    year = int(m.group(1))
            if year is None:
                continue
            if "end" in name or "ended" in name:
                if out["end"] is None or year > (out["end"] or 0):
                    out["end"] = year
            else:
                if out["start"] is None or year < (out["start"] or 9_999):
                    out["start"] = year

    if out["start"] is None and out["end"] is None:
        return None, None
    if out["start"] is None:
        out["start"] = out["end"]
    if out["end"] is None:
        out["end"] = out["start"]
    return out["start"], out["end"]


def _load_canonical_countries(path: str) -> tuple[dict[str, dict], dict[str, str]]:
    """Load the canonical country list produced by build_country_canonical.py.

    Returns (alias_to_meta, name_to_gwno).

    alias_to_meta: {lowercased alias: {canonical, gwcode, qid, ...}}
    name_to_gwno : {lowercased canonical_name: gwno_str}
    """
    alias_to_meta: dict[str, dict] = {}
    name_to_gwno: dict[str, str] = {}
    if not Path(path).exists():
        return alias_to_meta, name_to_gwno
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            aliases = [a.strip() for a in row["aliases"].split("|") if a.strip()]
            try:
                gw = int(row["gwcode"]) if row["gwcode"] else None
            except ValueError:
                gw = None
            qid = row["wikidata_qid"]
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
                "qid": qid,
                "start_year": start,
                "end_year": end,
            }
            for a in aliases:
                alias_to_meta.setdefault(a.lower(), meta)
            if gw is not None:
                name_to_gwno.setdefault(row["canonical_name"].lower(), str(gw))
    return alias_to_meta, name_to_gwno


def _load_t5_allowlist(path: str) -> set[str]:
    """Return a set of lowercased article titles that are heuristic-positive
    for T5 (from the hand-curated allowlist)."""
    out: set[str] = set()
    if not Path(path).exists():
        return out
    with open(path, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            t = (row.get("title") or "").strip().lower()
            if t:
                out.add(t)
    return out


def _load_gwn_map(path: str) -> tuple[dict[str, dict], dict[str, str]]:
    """Return (qid_to_gwno, name_to_gwno).

    qid_to_gwno: {'Q34266': {'gwno': '365', 'country_name': 'Russia'}}
    name_to_gwno: case-folded country_name -> gwno (str)."""
    qid_map: dict[str, dict] = {}
    name_map: dict[str, str] = {}
    if not Path(path).exists():
        return qid_map, name_map
    csv.field_size_limit(sys.maxsize)
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            qid = (row.get("wikidata_qid") or "").strip()
            gwno = (row.get("gwno") or "").strip()
            name = (row.get("country_name") or "").strip()
            if qid and gwno:
                qid_map[qid] = {"gwno": gwno, "country_name": name}
            if name and gwno:
                key = name.lower()
                # do not overwrite earlier entries
                name_map.setdefault(key, gwno)
    return qid_map, name_map


def _load_cshapes_fallback(path: str) -> dict[str, str]:
    """Best-effort {lowercased cntry_name: gwcode} from CShapes."""
    out: dict[str, str] = {}
    if not Path(path).exists():
        return out
    csv.field_size_limit(sys.maxsize)
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                gw = str(int(float(row["gwcode"])))
            except (KeyError, ValueError):
                continue
            name = (row.get("cntry_name") or "").strip()
            if name:
                out.setdefault(name.lower(), gw)
    return out


def _resolve_country(
    raw: str,
    qid_to_gwno: dict[str, dict],
    name_to_gwno: dict[str, str],
    cshapes_fallback: dict[str, str],
    main_entity_qid: str | None,
) -> dict | None:
    """Return a dict {qid, gwno, name} or None if we cannot resolve."""
    raw = (raw or "").strip()
    if not raw:
        return None
    # Strip parentheticals like "United States (government)" for the
    # first pass, but keep the original so we can also try the
    # annotated form ("Germany (Prussia)").
    raw_clean = re.sub(r"\s*\(.*?\)\s*", "", raw).strip()

    # 1. Try the article's main_entity if the raw text matches the
    #    resolved country name.
    if main_entity_qid and main_entity_qid in qid_to_gwno:
        entry = qid_to_gwno[main_entity_qid]
        entry_name_lc = entry["country_name"].lower()
        if entry_name_lc == raw_clean.lower() or entry_name_lc == raw.lower():
            return {
                "qid": main_entity_qid,
                "gwno": entry["gwno"],
                "name": entry["country_name"],
            }

    # 2. Direct name match against the raw form and the cleaned form.
    for candidate in (raw, raw_clean):
        key = candidate.lower()
        gwno = name_to_gwno.get(key) or cshapes_fallback.get(key)
        if gwno:
            return {"qid": None, "gwno": gwno, "name": candidate}

    # 3. Common aliases for the cleaned form.
    aliases_clean = [
        raw_clean,
        raw_clean.replace("the ", ""),
        raw_clean.replace("the united states", "united states"),
        raw_clean.replace("u.s.", "united states"),
        raw_clean.replace("u.s", "united states"),
        raw_clean.replace("us", "united states"),
        raw_clean.replace("usa", "united states"),
        raw_clean.replace("u.k.", "united kingdom"),
        raw_clean.replace("uk", "united kingdom"),
        raw_clean.replace("u.s.s.r.", "soviet union"),
        raw_clean.replace("ussr", "soviet union"),
    ]
    for a in aliases_clean:
        k = a.lower()
        g = name_to_gwno.get(k) or cshapes_fallback.get(k)
        if g:
            return {"qid": None, "gwno": g, "name": a}

    return None


def _emit_pair(
    a: dict, b: dict, year: int, tier: str, infobox_name: str, start_year: int | None,
    end_year: int | None, article_id: int, article_title: str,
) -> list[dict]:
    """Emit two directed events (a->b and b->a) for an undirected pair."""
    info = TIER_INFO[tier]
    src = f"WIKI_{tier}"
    common = {
        "article_id": article_id,
        "article_title": article_title,
        "infobox_name": infobox_name,
        "year": year,
        "start_year": start_year,
        "end_year": end_year,
        "tier": tier,
        "hostlev": info["hostlev"],
        "tier_label": info["tier_label"],
        "source": src,
    }
    return [
        {
            **common,
            "initiator_country": a["name"],
            "initiator_qid": a["qid"],
            "initiator_gwno": int(a["gwno"]),
            "target_country": b["name"],
            "target_qid": b["qid"],
            "target_gwno": int(b["gwno"]),
        },
        {
            **common,
            "initiator_country": b["name"],
            "initiator_qid": b["qid"],
            "initiator_gwno": int(b["gwno"]),
            "target_country": a["name"],
            "target_qid": a["qid"],
            "target_gwno": int(a["gwno"]),
        },
    ]


def _process_article(
    article: dict,
    qid_to_gwno: dict[str, dict],
    name_to_gwno: dict[str, str],
    cshapes_fallback: dict[str, str],
    canonical_alias_to_meta: dict[str, dict] | None = None,
) -> tuple[list[dict], dict, dict | None]:
    """Process one article. Returns (events, diagnostics, t5_candidate_or_None).

    `t5_candidate_or_None` is set when the article is a T4 that may
    warrant upgrade to T5; the LLM in stage 4.5 makes the final call.
    """
    diag = {
        "has_infobox": False,
        "n_belligerents_resolved": 0,
        "n_belligerents_unresolved": 0,
        "n_pairs_emitted": 0,
        "tier": None,
        "belligerent_count": 0,
        "date_span_years": 0,
    }
    infoboxes = _article_conflict_infoboxes_from_json(article.get("infoboxes"))
    if not infoboxes:
        return [], diag, None
    tier, infobox = infoboxes[0]
    diag["has_infobox"] = True
    diag["tier"] = tier

    s1_raw, s2_raw = _extract_belligerents(infobox)
    start_year, end_year = _extract_dates(infobox)
    if not s1_raw and not s2_raw:
        return [], diag, None
    if start_year is None and end_year is None:
        return [], diag, None

    # Build a flat list of belligerent entries; some infoboxes only
    # have one side populated.
    raw_list = s1_raw + s2_raw
    if not raw_list:
        return [], diag, None
    resolved: list[dict] = []
    for raw in raw_list:
        entry = _resolve_country(
            raw, qid_to_gwno, name_to_gwno, cshapes_fallback,
            article.get("main_entity_qid"),
        )
        if entry is not None:
            resolved.append(entry)
        else:
            diag["n_belligerents_unresolved"] += 1
    diag["n_belligerents_resolved"] = len(resolved)
    # Deduplicate by gwno so (a, a) pairs are not emitted.
    seen: set[str] = set()
    unique: list[dict] = []
    for r in resolved:
        if r["gwno"] in seen:
            continue
        seen.add(r["gwno"])
        unique.append(r)
    diag["belligerent_count"] = len(unique)
    if len(unique) < 2:
        return [], diag, None

    # Determine the year range to emit. If the infobox has both start
    # and end and they differ, emit one directed-pair row per year in
    # the inclusive range. If start == end or one is missing, emit one
    # row at the resolved year.
    if start_year is None:
        start_year = end_year
    if end_year is None:
        end_year = start_year
    assert start_year is not None and end_year is not None
    if end_year < start_year:
        start_year, end_year = end_year, start_year
    diag["date_span_years"] = int(end_year) - int(start_year) + 1

    events: list[dict] = []
    article_id = int(article["identifier"])
    article_title = str(article.get("name") or "")
    infobox_name = str(infobox.get("name") or "")
    for y in range(int(start_year), int(end_year) + 1):
        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                events.extend(
                    _emit_pair(
                        unique[i], unique[j], y, tier, infobox_name,
                        int(start_year), int(end_year),
                        article_id, article_title,
                    )
                )
    diag["n_pairs_emitted"] = len(events)

    # T5 candidate heuristic (only for T4 articles)
    t5_candidate = None
    if tier == "T4":
        reasons: list[str] = []
        title_has_war_keyword = bool(T5_TITLE_KEYWORDS_RE.search(article_title))
        if title_has_war_keyword and (diag["belligerent_count"] >= 3 or diag["date_span_years"] >= 2):
            reasons.append("title_war_keyword_and_big")
        if infobox_name == "Infobox military conflict" and diag["belligerent_count"] >= 4:
            reasons.append("big_belligerent_count")
        if diag["date_span_years"] >= 3 and diag["belligerent_count"] >= 2:
            reasons.append("long_duration")
        if reasons:
            t5_candidate = {
                "article_id": article_id,
                "article_title": article_title,
                "infobox_name": infobox_name,
                "year": int(start_year),
                "end_year": int(end_year),
                "belligerent_count": diag["belligerent_count"],
                "date_span_years": diag["date_span_years"],
                "n_events_emitted": len(events),
                "reasons": reasons,
                "belligerents": [
                    {"name": u["name"], "gwno": int(u["gwno"])} for u in unique
                ],
            }
    return events, diag, t5_candidate


def _article_conflict_infoboxes_from_json(infoboxes_json: str | None) -> list[tuple[str, dict]]:
    if not infoboxes_json:
        return []
    try:
        boxes = json.loads(infoboxes_json)
    except json.JSONDecodeError:
        return []
    if not isinstance(boxes, list):
        return []
    out: list[tuple[str, dict]] = []
    for box in boxes:
        if not isinstance(box, dict):
            continue
        name = box.get("name") or ""
        tier = _classify_infobox(name)
        if tier:
            out.append((tier, box))
    return out


def main() -> int:
    args = _parse_args()

    for path in (args.candidates, args.canonical, args.t5_allowlist):
        if not Path(path).exists():
            print(f"Missing required input: {path}", file=sys.stderr)
            return 1

    try:
        import pyarrow.parquet as pq
    except ImportError as e:
        print("pyarrow is required. pip install 'pyarrow>=12.0'", file=sys.stderr)
        raise SystemExit(1) from e

    canonical_alias_to_meta, canonical_name_to_gwno = _load_canonical_countries(args.canonical)
    t5_allowlist_titles = _load_t5_allowlist(args.t5_allowlist)
    print(f"Canonical country list: {len(canonical_alias_to_meta):,} aliases, {len(canonical_name_to_gwno):,} canonical names")
    print(f"T5 allowlist: {len(t5_allowlist_titles):,} titles")

    # Backward-compat: also load the legacy gwn_map and CShapes so we
    # don't break any pre-existing rows in the codebase.
    qid_to_gwno, name_to_gwno = _load_gwn_map(args.gwn_map)
    cshapes_fallback = _load_cshapes_fallback(args.cshapes_csv)
    print(f"GWN map (legacy): {len(qid_to_gwno)} QIDs, {len(name_to_gwno)} names")
    print(f"CShapes fallback: {len(cshapes_fallback)} names")
    # Merge canonical into name_to_gwno so the resolver sees both
    for cn, gw in canonical_name_to_gwno.items():
        name_to_gwno.setdefault(cn, gw)

    table = pq.read_table(args.candidates)
    df = table.to_pylist()
    # Restrict to infobox-path articles only (the new filter sets
    # `path == "infobox"` for those). LLM-path articles do not have
    # conflict-style infoboxes.
    df = [r for r in df if r.get("path") == "infobox"]
    if args.max_articles and args.max_articles > 0:
        df = df[: args.max_articles]
    print(f"Infobox-path candidate articles: {len(df):,}")

    t0 = time.time()
    all_events: list[dict] = []
    tier_counts: dict[str, int] = {"T4": 0, "T5": 0}
    infobox_skipped = 0
    no_belligerents = 0
    no_dates = 0
    unresolved_total = 0
    years_emitted: list[int] = []
    t5_candidates: list[dict] = []
    allowlist_t5_emitted: list[dict] = []
    for art in df:
        events, diag, t5c = _process_article(
            art, qid_to_gwno, name_to_gwno, cshapes_fallback,
            canonical_alias_to_meta,
        )
        if not diag["has_infobox"]:
            infobox_skipped += 1
            continue
        if diag["n_belligerents_resolved"] == 0:
            no_belligerents += 1
            continue
        if diag["n_pairs_emitted"] == 0:
            no_dates += 1
            continue
        tier = diag["tier"] or "T4"
        title_lc = (art.get("name") or "").strip().lower()
        allowlist_promoted = tier == "T4" and title_lc in t5_allowlist_titles
        effective_tier = "T5" if allowlist_promoted else tier
        tier_counts[effective_tier] = tier_counts.get(effective_tier, 0) + diag["n_pairs_emitted"]
        unresolved_total += diag["n_belligerents_unresolved"]
        years_emitted.extend(e["year"] for e in events)
        # Emit events at their effective tier
        if allowlist_promoted:
            promoted = [
                {**e, "tier": "T5", "hostlev": 5,
                 "tier_label": "T5-Strategic War", "source": "WIKI_T5",
                 "promotion": "allowlist"}
                for e in events
            ]
            all_events.extend(promoted)
            allowlist_t5_emitted.append({
                "article_id": int(art["identifier"]),
                "article_title": art["name"],
                "n_events": len(events),
            })
        else:
            all_events.extend(events)
        # Collect T5 candidates (only for non-allowlist T4)
        if t5c is not None and not allowlist_promoted:
            t5_candidates.append(t5c)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for e in all_events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # T5 candidate sidecar (for stage 4.5 LLM pass)
    if t5_candidates:
        with open(args.t5_candidates, "w", encoding="utf-8") as f:
            for c in t5_candidates:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
    else:
        # Write an empty file to keep the orchestrator happy
        Path(args.t5_candidates).parent.mkdir(parents=True, exist_ok=True)
        Path(args.t5_candidates).write_text("")

    diag_out = {
        "n_articles_in": len(df),
        "n_articles_with_conflict_infobox": len(df) - infobox_skipped,
        "n_articles_no_belligerents_resolved": no_belligerents,
        "n_articles_no_dates": no_dates,
        "n_unresolved_belligerents_total": unresolved_total,
        "n_events_emitted": len(all_events),
        "events_per_tier": tier_counts,
        "year_min": min(years_emitted) if years_emitted else None,
        "year_max": max(years_emitted) if years_emitted else None,
        "n_t5_candidates": len(t5_candidates),
        "n_allowlist_t5_promotions": len(allowlist_t5_emitted),
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    with open(args.diag, "w") as f:
        json.dump(diag_out, f, indent=2)

    print()
    print(f"Wrote {args.out} ({len(all_events):,} events from {len(df) - infobox_skipped:,} articles)")
    print(f"  by tier: {tier_counts}")
    if years_emitted:
        print(f"  year range: {min(years_emitted)} - {max(years_emitted)}")
    print(f"  unresolved belligerents: {unresolved_total}")
    print(f"  T5 candidates (heuristic): {len(t5_candidates):,}")
    print(f"  T5 allowlist promotions: {len(allowlist_t5_emitted):,}")
    print(f"  elapsed: {time.time() - t0:.1f}s")
    print(f"Diagnostics -> {args.diag}")
    print(f"T5 candidates -> {args.t5_candidates}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
