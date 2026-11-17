"""Filter the structured-wikipedia snapshot to a candidate set for tier extraction.

The filter runs in two stages (DuckDB + Python bilateral) and produces
two parallel paths:

  T4/T5 (military conflict, war, battle, etc.) — the **infobox path**:
    regexp match on the pre-parsed `infoboxes` JSON for conflict-style
    infobox template names. These articles have structured belligerent
    and date fields that the pure-Python parser in
    `wiki_extract_infobox_t45.py` consumes.

  T1/T2/T3 (diplomatic crisis, sanctions, proxy support) — the **LLM path**:
    bilateral country gate over the abstract / title. The LLM
    classifier in `wiki_extract_llm_t123_filter.py` then decides
    whether each bilateral article describes a real conflict event.
    These articles have no conflict-style infobox, so the LLM
    extractors in `wiki_extract_llm_t123_tier.py` and
    `wiki_extract_llm_t123.py` consume their text.

Two-stage narrowing (see docs/wiki_pipeline.md §A):

  Stage 3a  DuckDB    country-only filter over the full snapshot.
                     Yields articles with >=1 country mention in
                     (abstract || name).
  Stage 3b  Python    bilateral gate: at least 2 canonical country
                     names in (abstract || name), with at least one
                     being a modern sovereign state. Also annotates
                     each row with its `sections_excerpt` for the
                     LLM filter.

  (No 3a.5 broad-keyword pre-filter; the LLM filter is the precision
   check. No 3c tier-keyword gate — the LLM tier pass replaces it.)

Output:
  tmp/wiki_tier_candidates.parquet
    Columns: identifier, name, url, main_entity_qid, abstract,
             sections_excerpt, infobox_names, infoboxes, tier_hints,
             tier_hints_v2, date_created, date_modified.
    `tier_hints`     — old style: 'T1'/'T2'/'T3'/'T4T5' (used by the
                       downstream scripts).
    `tier_hints_v2`  — new style: 'T1'/'T2'/'T3' for LLM path,
                       'T4T5' for infobox path. Used by the validator.
  tmp/wiki_filter_stats.json
    Per-stage hit counts.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw" / "structured-wikipedia"
TMP = ROOT / "tmp"
DATA_PROCESSED = ROOT / "data" / "processed"

CANONICAL_CSV = DATA_PROCESSED / "wiki_country_canonical.csv"

# ---------------------------------------------------------------------------
# Conflict infobox detection (unchanged from v1 filter)
# ---------------------------------------------------------------------------
_CONFLICT_INFOBOX_PATTERN = (
    r'"name"\s*:\s*"Infobox (?:'
    r"military conflict"
    r"|civil conflict"
    r"|war"
    r"|battle"
    r"|armed conflict"
    r"|revolution"
    r"|insurgency"
    r"|civil war"
    r"|siege"
    r"|military operation"
    r"|terrorist attack"
    r"|airstrike)"
    r'"'
)
CONFLICT_INFOBOX_RE = re.compile(_CONFLICT_INFOBOX_PATTERN, re.IGNORECASE)

# ---------------------------------------------------------------------------
# Broad conflict keyword set (stage 3a)
#
# These are the words/phrases that make a Wikipedia article *about* a
# conflict event. Kept generous on purpose — the bilateral and tier-
# keyword gates will narrow.
# ---------------------------------------------------------------------------
BROAD_KEYWORD_PATTERNS: list[str] = [
    r"conflict",
    r"war\b",
    r"wars\b",
    r"sanction",
    r"sanctioned",
    r"embargo",
    r"blockade",
    r"dispute",
    r"tension",
    r"tensions",
    r"hostilit",
    r"crisis",
    r"invasion",
    r"occupation",
    r"annexation",
    r"recall.{0,5}ambassador",
    r"recalled.{0,5}ambassador",
    r"withdrew.{0,5}ambassador",
    r"expelled.{0,5}diplomat",
    r"expelled.{0,5}ambassador",
    r"ultimatum",
    r"ceasefire",
    r"truce",
    r"armistice",
    r"mobiliz",
    r"airstrike",
    r"air strike",
    r"bombing",
    r"clash",
    r"clashes",
    r"skirmish",
    r"insurgent",
    r"insurgency",
    r"rebel",
    r"rebels",
    r"separatist",
    r"militant",
    r"terrorist",
    r"interven",
    r"intervention",
    r"deploy",
    r"deployed",
    r"missile",
    r"diplomatic protest",
    r"sever.{0,5}diplomatic",
    r"withdrew.{0,5}diplomatic",
    r"armed forces",
    r"strike on",
    r"shelling",
    r"proxy",
    r"covert",
    r"backed.{0,20}rebel",
    r"armed group",
    r"cease-fire",
    r"naval",
    r"troops",
]
BROAD_KEYWORD_RE = re.compile(
    r"\b(?:" + "|".join(BROAD_KEYWORD_PATTERNS) + r")\b", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Tier-specific keyword sets (stage 3c)
#
# T1: diplomatic-crisis-class actions. The T1 set is intentionally
#     strict because stage 3a will already have eliminated articles
#     that don't mention a country + a conflict word.
# T2: sanctions/economic-coercion-class actions. Includes weapons
#     embargoes (a UN action) and asset freezes.
# T3: proxy/indirect-military support. Includes transfers of weapons,
#     training, financing, intelligence, or personnel to armed groups.
# ---------------------------------------------------------------------------
TIER_KEYWORD_PATTERNS: dict[str, list[str]] = {
    "T1": [
        r"recall.{0,5}ambassador",
        r"recalled.{0,5}ambassador",
        r"withdrew.{0,5}ambassador",
        r"expelled.{0,5}diplomat",
        r"expelled.{0,5}ambassador",
        r"ultimatum",
        r"severed?\s+diplomatic",
        r"severed?\s+ties",
        r"withdrew.{0,5}diplomatic",
        r"diplomatic protest",
        r"demarche",
        r"demarched",
        r"UN.{0,5}(general assembly|security council|vote|resolution|censure)",
        r"draft resolution",
        r"condemn.{0,30}(invasion|attack|annexation|occupation)",
        r"imposed a travel ban",
        r"declared.{0,5}persona non grata",
        r"recalled.{0,5}its envoy",
        r"withdrew.{0,5}its envoy",
    ],
    "T2": [
        r"imposed sanction",
        r"imposed a sanction",
        r"imposed economic sanction",
        r"imposed a trade embargo",
        r"imposed a weapons embargo",
        r"imposed an arms embargo",
        r"imposed an oil embargo",
        r"imposed an asset freeze",
        r"imposed asset freeze",
        r"imposed an export ban",
        r"imposed export control",
        r"imposed a ban on",
        r"imposed restrictions on",
        r"imposed a travel ban",
        r"imposed a no-fly zone",
        r"announced sanction",
        r"enacted sanction",
        r"economic sanction",
        r"trade embargo",
        r"arms embargo",
        r"weapons embargo",
        r"asset freeze",
        r"disconnected from swift",
        r"swift disconnection",
        r"targeted sanction",
        r"designated as a state sponsor",
        r"state sponsor of terrorism",
        r"added to the entity list",
        r"entity list",
        r"frozen.{0,20}assets",
        r"oil embargo",
        r"banned.{0,20}imports",
        r"export control",
        r"export ban",
        r"trade restriction",
        r"financial sanction",
        r"financial exclusion",
    ],
    "T3": [
        r"supplied weapons to",
        r"supplied arms to",
        r"supplied.{0,30}rebel",
        r"supplied.{0,30}insurgent",
        r"supplied.{0,30}militant",
        r"armed (?:group|rebel|insurgent|militant|opposition)",
        r"armed and funded",
        r"proxy force",
        r"materiel to",
        r"covert support to",
        r"covert support for",
        r"covertly support",
        r"trained and equipped",
        r"trained and armed",
        r"transferred.{0,30}drones",
        r"transferred.{0,30}missiles",
        r"transferred.{0,30}rockets",
        r"transferred.{0,30}weapons",
        r"logistics support to",
        r"logistical support to",
        r"foreign fighter pipeline",
        r"funding.{0,20}hezbollah",
        r"funding.{0,20}hamas",
        r"backed.{0,20}rebel",
        r"backed.{0,20}insurgent",
        r"intelligence support to",
        r"provided intelligence to",
        r"weapons shipments to",
        r"arms pipeline",
        r"material support to",
        r"military advisors to",
    ],
    "T4": [
        r"airstrike",
        r"air strike",
        r"shelling",
        r"border clash",
        r"naval engagement",
        r"missile strike",
        r"exchange of fire",
        r"incursion",
        r"military operation",
        r"deployment of troops",
        r"deployed.{0,10}troops",
        r"mobilization",
        r"armed forces deployed",
        r"ceasefire violation",
        r"border skirmish",
        r"artillery duel",
        r"drone strike",
        r"special forces raid",
        r"cross-border.{0,10}(attack|raid|strike|fire)",
        r"retaliatory.{0,10}(strike|attack|raid)",
        r"precision strike",
        r"surgical strike",
        r"naval blockade",
        r"no-fly zone",
    ],
    "T5": [
        r"\bwar\b",
        r"\binvasion\b",
        r"\boccupation\b",
        r"\bannexation\b",
        r"declared war",
        r"full-scale war",
        r"multi-front war",
        r"world war",
        r"nationwide mobilization",
        r"strategic bombing",
        r"war of attrition",
        r"total war",
        r"armed conflict",
        r"military conflict",
    ],
}
TIER_KEYWORD_RES: dict[str, re.Pattern[str]] = {
    t: re.compile(r"\b(?:" + "|".join(p) + r")\b", re.IGNORECASE)
    for t, p in TIER_KEYWORD_PATTERNS.items()
}

SECTION_EXCERPT_CHARS = 6_000

# Co-occurrence window for the tier-keyword gate (stage 3c): the tier
# keyword must appear within this many characters of a country name.
CO_OCCURRENCE_WINDOW = 400

# Year regex: matches 1800-2029 as standalone 4-digit numbers.
YEAR_RE = re.compile(r"\b(1[8-9]\d{2}|20[0-2]\d)\b")


# ---------------------------------------------------------------------------
# Canonical country list (loaded once, used by all three stages)
# ---------------------------------------------------------------------------

def _load_canonical_countries() -> tuple[list[str], dict[str, dict], list[dict], "re.Pattern[str]", dict[str, "re.Pattern[str]"]]:
    """Return (alias_list_for_regex, name_to_meta, full_rows, combined_re, per_alias_res).

    alias_list_for_regex  : flat list of all aliases (lowercase, whole-word)
    name_to_meta          : {lowercase alias: {canonical, gwcode, qid,
                            start_year, end_year, modern}}
    full_rows             : the raw rows for diagnostics
    combined_re           : single compiled regex `\b(alias1|alias2|...)\b` (case-insensitive)
                            for fast country-mention scanning
    per_alias_res         : dict alias -> compiled regex (for very short aliases
                            that we want to match with strict word boundaries)
    """
    alias_to_meta: dict[str, dict] = {}
    rows: list[dict] = []
    if not CANONICAL_CSV.exists():
        raise SystemExit(f"Missing canonical country list at {CANONICAL_CSV}. Run scripts/build/build_country_canonical.py first.")
    with open(CANONICAL_CSV, "r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
            aliases = [a.strip() for a in r["aliases"].split("|") if a.strip()]
            try:
                gw = int(r["gwcode"]) if r["gwcode"] else None
            except ValueError:
                gw = None
            try:
                start = int(r["start_year"])
            except ValueError:
                start = 1816
            try:
                end = int(r["end_year"])
            except ValueError:
                end = 2099
            qid = r["wikidata_qid"]
            modern = (end >= 2020 and gw is not None)
            meta = {
                "canonical": r["canonical_name"],
                "gwcode": gw,
                "qid": qid,
                "start_year": start,
                "end_year": end,
                "modern": modern,
            }
            for a in aliases:
                key = a.lower()
                # Don't overwrite — alias dict is curated to be consistent.
                alias_to_meta.setdefault(key, meta)
    # For DuckDB regex: filter to aliases >=4 chars (or 3-char and the alias
    # is an exact match to a known long name, e.g. "uae"). 2-3 char aliases
    # cause too many false positives; we apply them only in the Python pass.
    safe_aliases = sorted({a for a in alias_to_meta.keys() if len(a) >= 4})
    # Build a single combined regex for fast Python-side matching.
    # Use an alternation that is sorted with longest-first so "united kingdom"
    # is matched before "kingdom" (which would otherwise match the substring).
    sorted_aliases = sorted(alias_to_meta.keys(), key=lambda a: -len(a))
    combined_re = re.compile(
        r"\b(?:" + "|".join(re.escape(a) for a in sorted_aliases) + r")\b",
        re.IGNORECASE,
    )
    # Per-alias regex for strict short matches (we use it on the captured
    # text from combined_re.finditer)
    per_alias_res: dict[str, "re.Pattern[str]"] = {
        a: re.compile(rf"\b{re.escape(a)}\b", re.IGNORECASE)
        for a in sorted_aliases
        if len(a) < 4
    }
    return safe_aliases, alias_to_meta, rows, combined_re, per_alias_res


# ---------------------------------------------------------------------------
# Stage 3a — DuckDB country-only filter
# ---------------------------------------------------------------------------

def _build_duckdb_country_only_sql(parquet_glob: str, country_regex: str, max_rows: int) -> str:
    """Stage 3a: country-only filter.

    Unlike the previous (country AND conflict-keyword) design, this is just
    a country-mention filter over `abstract || name`. The LLM filter
    (stage 3b in the orchestrator) is the precision check, so we cast a
    wide net here.
    """
    limit_clause = f"LIMIT {int(max_rows)}" if max_rows and max_rows > 0 else ""
    country_pattern = (
        "(?i)(^|[^a-z0-9])("
        + country_regex
        + ")($|[^a-z0-9])"
    )
    sql_lines = [
        "SELECT",
        "  identifier,",
        "  name,",
        "  url,",
        "  main_entity,",
        "  abstract,",
        "  sections,",
        "  infoboxes,",
        "  date_created,",
        "  date_modified",
        f"FROM read_parquet('{parquet_glob}')",
        "WHERE",
        f"  regexp_matches(coalesce(abstract,'') || ' ' || coalesce(name,''), '{country_pattern}')",
    ]
    if limit_clause:
        sql_lines.append(limit_clause)
    return "\n".join(sql_lines)


def _duckdb_country_only_pass(parquet_glob: str, country_regex: str, max_rows: int):
    """Yield rows from the DuckDB country-only filter in batches to avoid
    materializing the entire result set in memory."""
    try:
        import duckdb
    except ImportError as e:
        print("duckdb is required. pip install 'duckdb>=0.10'", file=sys.stderr)
        raise SystemExit(1) from e

    con = duckdb.connect()
    con.execute("SET threads TO 4")
    (ROOT / "tmp" / "duckdb_tmp").mkdir(parents=True, exist_ok=True)
    con.execute("SET temp_directory TO 'tmp/duckdb_tmp'")
    sql = _build_duckdb_country_only_sql(parquet_glob, country_regex, max_rows)
    print(f"Stage 3a (DuckDB country-only filter)...")
    t0 = time.time()
    rel = con.execute(sql)
    cols = [d[0] for d in rel.description]
    n_yielded = 0
    while True:
        batch = rel.fetchmany(10_000)
        if not batch:
            break
        for row in batch:
            yield dict(zip(cols, row))
        n_yielded += len(batch)
        elapsed = time.time() - t0
        rate = n_yielded / max(elapsed, 1e-6)
        print(
            f"  stage 3a: [{n_yielded:>7,}] rows streamed  "
            f"rate={rate:.0f}/s  elapsed={elapsed:.0f}s",
            flush=True,
        )
    print(f"  stage 3a done: {n_yielded:,} rows in {time.time() - t0:.1f}s")


# ---------------------------------------------------------------------------
# Stage 3b/3c — Python bilateral and tier-keyword gates
# ---------------------------------------------------------------------------

def _extract_country_mentions_fast(
    text: str,
    combined_re: "re.Pattern[str]",
    alias_to_meta: dict[str, dict],
) -> tuple[set[str], set[str]]:
    """Fast country-mention extraction using a single compiled regex.

    Returns (set of canonical_names, set of aliases that matched).
    The combined regex matches all aliases at once with longest-first
    alternation, so substring overlaps are not a problem.
    """
    if not text:
        return set(), set()
    matched_aliases: set[str] = set()
    matched_canonicals: set[str] = set()
    for m in combined_re.finditer(text):
        alias = m.group(0).lower()
        meta = alias_to_meta.get(alias)
        if meta is None:
            continue
        matched_aliases.add(alias)
        matched_canonicals.add(meta["canonical"])
    return matched_canonicals, matched_aliases


def _bilateral_gate(
    rows: list[dict],
    alias_to_meta: dict[str, dict],
    combined_re: "re.Pattern[str]",
    modern_canonicals: set[str],
    progress: bool = True,
) -> tuple[list[dict], dict]:
    """Stage 3b: keep articles that mention >=2 canonical countries in
    (abstract OR title), with at least one being a modern sovereign
    state.

    The bilateral survivors are the LLM-path input. The LLM filter
    (stage 3b in the orchestrator) then decides per article whether it
    describes a real conflict event.
    """
    keep: list[dict] = []
    diagnostics = {
        "n_in": len(rows),
        "n_dropped_no_countries": 0,
        "n_dropped_one_country": 0,
        "n_dropped_no_modern_sovereign": 0,
        "n_kept": 0,
    }
    t0 = time.time()
    n = len(rows)
    for i, r in enumerate(rows):
        # Use only abstract + title for the bilateral decision. Sections
        # parsing is expensive at this scale; we extract sections_excerpt
        # later, only for the bilateral survivors.
        text_parts: list[str] = []
        ab = r.get("abstract")
        if isinstance(ab, str):
            text_parts.append(ab)
        nm = r.get("name")
        if isinstance(nm, str):
            text_parts.append(nm)
        text = " ".join(text_parts)

        canon, aliases = _extract_country_mentions_fast(text, combined_re, alias_to_meta)
        if len(canon) == 0:
            diagnostics["n_dropped_no_countries"] += 1
            continue
        if len(canon) == 1:
            diagnostics["n_dropped_one_country"] += 1
            continue
        # At least one modern sovereign state
        if not (canon & modern_canonicals):
            diagnostics["n_dropped_no_modern_sovereign"] += 1
            continue
        # Pass — annotate with matched countries for downstream use
        r2 = dict(r)
        r2["_matched_canonicals"] = sorted(canon)
        r2["_matched_aliases"] = sorted(aliases)
        keep.append(r2)
        diagnostics["n_kept"] += 1
        if progress and (i + 1) % 5000 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / max(elapsed, 1e-6)
            eta = (n - i - 1) / max(rate, 1e-6)
            print(
                f"  stage 3b: [{i+1:>6}/{n}] kept={diagnostics['n_kept']:,} "
                f"rate={rate:.0f}/s eta={eta/60:.1f}m"
            )
    return keep, diagnostics


def _tier_keyword_gate(
    rows: list[dict],
    co_occurrence_window: int,
    progress: bool = True,
) -> tuple[list[dict], dict]:
    """Stage 3c: keep articles where a tier-specific keyword matches
    within `co_occurrence_window` characters of a country mention.
    """
    keep: list[dict] = []
    tier_counts: dict[str, int] = {t: 0 for t in TIER_KEYWORD_RES}
    diagnostics = {
        "n_in": len(rows),
        "n_dropped_no_tier_keyword": 0,
        "n_kept": 0,
        "tier_counts": tier_counts,
    }
    n = len(rows)
    t0 = time.time()
    for i, r in enumerate(rows):
        text = " ".join(
            s for s in (r.get("abstract") or "", r.get("name") or "") if s
        )
        # Find ALL tier-keyword matches and the offsets where they occur
        hits: list[tuple[str, int]] = []
        for tier, rx in TIER_KEYWORD_RES.items():
            for m in rx.finditer(text):
                hits.append((tier, m.start()))
        if not hits:
            diagnostics["n_dropped_no_tier_keyword"] += 1
            continue
        # Country mention offsets (whole-word alias matches, any alias)
        country_offsets: list[int] = []
        for alias in r.get("_matched_aliases") or []:
            for m in re.finditer(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE):
                country_offsets.append(m.start())
        if not country_offsets:
            diagnostics["n_dropped_no_tier_keyword"] += 1
            continue
        # For each tier-keyword hit, check if any country mention is
        # within `co_occurrence_window` characters.
        matched_tiers: set[str] = set()
        for tier, off in hits:
            for co in country_offsets:
                if abs(off - co) <= co_occurrence_window:
                    matched_tiers.add(tier)
                    break
        if not matched_tiers:
            diagnostics["n_dropped_no_tier_keyword"] += 1
            continue
        r2 = dict(r)
        r2["_matched_tiers"] = sorted(matched_tiers)
        keep.append(r2)
        for t in matched_tiers:
            tier_counts[t] += 1
        diagnostics["n_kept"] += 1
        if progress and (i + 1) % 2000 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / max(elapsed, 1e-6)
            eta = (n - i - 1) / max(rate, 1e-6)
            print(
                f"  stage 3c: [{i+1:>6}/{n}] kept={diagnostics['n_kept']:,} "
                f"tiers={tier_counts} rate={rate:.0f}/s eta={eta/60:.1f}m"
            )
    diagnostics["tier_counts"] = tier_counts
    return keep, diagnostics


# ---------------------------------------------------------------------------
# Infobox detection (T4/T5 path) — unchanged from v1
# ---------------------------------------------------------------------------

def _extract_infobox_names(infoboxes_json: str | None) -> list[str]:
    if not infoboxes_json:
        return []
    out: list[str] = []
    for m in re.finditer(
        r'"type"\s*:\s*"infobox"\s*,\s*"name"\s*:\s*"([^"]+)"',
        infoboxes_json,
    ):
        out.append(m.group(1))
    return out


def _has_conflict_infobox(infobox_names: list[str]) -> bool:
    if not infobox_names:
        return False
    for n in infobox_names:
        if n.lower().startswith("infobox"):
            if CONFLICT_INFOBOX_RE.search('"name":"' + n + '"'):
                return True
    return False


def _section_excerpt(sections_json: str | None) -> str:
    if not sections_json:
        return ""
    parts: list[str] = []
    buf = 0

    def _pull_text_value(node: object) -> str:
        if isinstance(node, dict):
            for k in ("value", "text"):
                v = node.get(k)
                if isinstance(v, str):
                    return v
        return ""

    try:
        sections = json.loads(sections_json)
    except json.JSONDecodeError:
        return ""
    for sec in sections:
        if buf >= SECTION_EXCERPT_CHARS:
            break
        if not isinstance(sec, dict):
            continue
        title = sec.get("name") or sec.get("title")
        if isinstance(title, str) and title.strip():
            parts.append("\n## " + title.strip() + "\n")
            buf += len(title) + 8
        for part in sec.get("has_parts") or []:
            if buf >= SECTION_EXCERPT_CHARS:
                break
            t = _pull_text_value(part)
            if t:
                parts.append(t)
                buf += len(t) + 1
            for sub in (part.get("has_parts") if isinstance(part, dict) else None) or []:
                if buf >= SECTION_EXCERPT_CHARS:
                    break
                t = _pull_text_value(sub)
                if t:
                    parts.append(t)
                    buf += len(t) + 1
    return "".join(parts)[:SECTION_EXCERPT_CHARS]


# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------

def _build_tier_hints(infobox_names: list[str], matched_tiers: list[str] | None) -> list[str]:
    hints: list[str] = []
    if _has_conflict_infobox(infobox_names):
        hints.append("T4T5")
    if matched_tiers:
        hints.extend(matched_tiers)
    seen: set[str] = set()
    return [h for h in hints if not (h in seen or seen.add(h))]


def _discover_parquet_glob(data_raw: Path) -> str | None:
    """Auto-discover the enwiki Parquet shards under
    `data_raw/<name>/data/*.parquet`.

    Prefers the most recently modified subdirectory (handles multiple
    Wiki exports side by side; the user can keep the new export in a
    separate subdir like `enwiki_2026_07`).

    Returns a glob string, or None if no enwiki parquet shards are found.
    """
    if not data_raw.exists():
        return None
    candidates: list[tuple[float, Path]] = []
    for sub in data_raw.iterdir():
        if not sub.is_dir() or sub.name.startswith("."):
            continue
        data_dir = sub / "data"
        if not data_dir.is_dir():
            continue
        # Look for *namespace_0*.parquet files (the structured-wikipedia
        # convention)
        parquets = list(data_dir.glob("*namespace_0*.parquet"))
        if not parquets:
            continue
        # Most recently modified parquet
        mtime = max(p.stat().st_mtime for p in parquets)
        candidates.append((mtime, data_dir))
    if not candidates:
        return None
    candidates.sort(reverse=True)  # newest first
    return str(candidates[0][1] / "*.parquet")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--parquet-glob",
        default=None,
        help=(
            "Glob to the enwiki Parquet shards. If unset, auto-discovers the "
            "most recently modified `data/raw/structured-wikipedia/<name>/data/` "
            "directory. Override this if you have a specific export you "
            "want to use."
        ),
    )
    p.add_argument(
        "--canonical",
        default=str(CANONICAL_CSV),
        help="Canonical country list CSV.",
    )
    p.add_argument(
        "--out",
        default=str(TMP / "wiki_tier_candidates.parquet"),
        help="Output Parquet file.",
    )
    p.add_argument(
        "--stats-out",
        default=str(TMP / "wiki_filter_stats.json"),
        help="Per-stage hit-count JSON.",
    )
    p.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Optional cap on rows returned from the DuckDB pass (0 = no cap). Useful for smoke tests.",
    )
    p.add_argument(
        "--co-occurrence-window",
        type=int,
        default=CO_OCCURRENCE_WINDOW,
        help="Stage 3c: tier keyword must be within N chars of a country name.",
    )
    p.add_argument(
        "--smoke-test",
        type=int,
        default=0,
        help="Run DuckDB pass with this cap and skip the LLM-output write (0 = normal).",
    )
    args = p.parse_args()

    # Auto-discover the parquet glob if not specified
    if args.parquet_glob is None:
        discovered = _discover_parquet_glob(DATA_RAW)
        if discovered is None:
            print(
                f"No enwiki Parquet shards found under {DATA_RAW}/<name>/data/.\n"
                f"Place the Wiki export (parquet shards) in a subdirectory like\n"
                f"  {DATA_RAW}/enwiki_v2/data/*.parquet\n"
                f"or pass --parquet-glob explicitly.",
                file=sys.stderr,
            )
            return 1
        args.parquet_glob = discovered
        print(f"[setup] Auto-discovered parquet glob: {args.parquet_glob}")

    if not Path(args.parquet_glob.split("*")[0]).exists():
        print(
            f"Parquet shards not found at {args.parquet_glob!r}.",
            file=sys.stderr,
        )
        return 1

    print("=" * 70)
    print("Wikipedia filter — country-only DuckDB pass + bilateral Python gate")
    print("=" * 70)

    # -- Load canonical list
    print(f"[setup] Loading canonical country list from {args.canonical}...")
    safe_aliases, alias_to_meta, canonical_rows, combined_re, per_alias_res = _load_canonical_countries()
    print(f"        {len(canonical_rows):,} canonical rows, {len(safe_aliases):,} DuckDB-safe aliases (>=4 chars)")
    print(f"        {len(alias_to_meta):,} total aliases for Python matching")
    modern_canonicals = {m["canonical"] for m in alias_to_meta.values() if m["modern"]}
    print(f"        {len(modern_canonicals):,} modern sovereign canonicals")
    print()

    # -- Stage 3a (DuckDB country-only) — streamed in batches
    safe_aliases_duckdb = [a for a in safe_aliases if " " not in a and "'" not in a]
    country_regex = "|".join(re.escape(a) for a in safe_aliases_duckdb)
    print(f"[stage 3a] {len(safe_aliases_duckdb):,} aliases for DuckDB (excluded {len(safe_aliases) - len(safe_aliases_duckdb):,} with spaces or apostrophes; will be matched in Python pass).")
    country_only_rows_iter = _duckdb_country_only_pass(args.parquet_glob, country_regex, args.max_rows)

    # -- Single pass: bilateral gate + keyword+year gate + infobox detection
    #    (streams rows from DuckDB without materializing the full result set)
    print(f"[stage 3b] bilateral gate + keyword+year gate + infobox detection (streaming)...")
    bilateral_rows: list[dict] = []
    infobox_rows: list[dict] = []
    diag_3b = {
        "n_in": 0,
        "n_dropped_no_countries": 0,
        "n_dropped_one_country": 0,
        "n_dropped_no_modern_sovereign": 0,
        "n_dropped_no_year": 0,
        "n_dropped_no_keyword": 0,
        "n_kept": 0,
    }
    t0 = time.time()
    for r in country_only_rows_iter:
        diag_3b["n_in"] += 1

        # --- bilateral gate ---
        text_parts: list[str] = []
        ab = r.get("abstract")
        if isinstance(ab, str):
            text_parts.append(ab)
        nm = r.get("name")
        if isinstance(nm, str):
            text_parts.append(nm)
        text = " ".join(text_parts)
        canon, aliases = _extract_country_mentions_fast(text, combined_re, alias_to_meta)

        if len(canon) < 2 or not (canon & modern_canonicals):
            if len(canon) == 0:
                diag_3b["n_dropped_no_countries"] += 1
            elif len(canon) == 1:
                diag_3b["n_dropped_one_country"] += 1
            else:
                diag_3b["n_dropped_no_modern_sovereign"] += 1
            # Still check infobox below (infobox path doesn't need bilateral)
        else:
            # --- 3B: year + conflict keyword co-occurrence gate ---
            if not YEAR_RE.search(text):
                diag_3b["n_dropped_no_year"] += 1
            else:
                # Check for tier keyword near a country mention
                kw_hits: list[tuple[str, int]] = []
                for tier, rx in TIER_KEYWORD_RES.items():
                    for m in rx.finditer(text):
                        kw_hits.append((tier, m.start()))
                if kw_hits:
                    country_offsets: list[int] = []
                    for alias in aliases:
                        for m in re.finditer(rf"\b{re.escape(alias)}\b", text, re.IGNORECASE):
                            country_offsets.append(m.start())
                    matched_tiers: set[str] = set()
                    for tier, off in kw_hits:
                        for co in country_offsets:
                            if abs(off - co) <= CO_OCCURRENCE_WINDOW:
                                matched_tiers.add(tier)
                                break
                    if matched_tiers:
                        r2 = dict(r)
                        r2["_matched_canonicals"] = sorted(canon)
                        r2["_matched_aliases"] = sorted(aliases)
                        r2["_matched_tiers"] = sorted(matched_tiers)
                        bilateral_rows.append(r2)
                        diag_3b["n_kept"] += 1
                    else:
                        diag_3b["n_dropped_no_keyword"] += 1
                else:
                    diag_3b["n_dropped_no_keyword"] += 1

        # --- infobox detection (independent of bilateral/keyword gate) ---
        infobox_names = _extract_infobox_names(r.get("infoboxes"))
        if _has_conflict_infobox(infobox_names):
            main_qid = None
            me = r.get("main_entity")
            if isinstance(me, dict):
                main_qid = me.get("identifier")
            elif isinstance(me, str) and me:
                try:
                    main_qid = json.loads(me).get("identifier")
                except json.JSONDecodeError:
                    main_qid = None
            r3 = dict(r)
            r3["main_entity_qid"] = main_qid
            r3["infobox_names"] = infobox_names
            r3["_matched_tiers"] = ["T4T5"]
            r3["_matched_canonicals"] = []
            r3["_matched_aliases"] = []
            infobox_rows.append(r3)

        n = diag_3b["n_in"]
        if n % 50_000 == 0:
            elapsed = time.time() - t0
            rate = n / max(elapsed, 1e-6)
            print(
                f"  [{n:>7,}] bilateral={len(bilateral_rows):,}  infobox={len(infobox_rows):,}  "
                f"dropped_no_year={diag_3b['n_dropped_no_year']:,}  dropped_no_kw={diag_3b['n_dropped_no_keyword']:,}  "
                f"rate={rate:.0f}/s  elapsed={elapsed:.0f}s",
                flush=True,
            )

    n_3a = diag_3b["n_in"]
    print()
    print(f"        kept (year+keyword): {diag_3b['n_kept']:,}")
    print(f"        dropped (0/1 country): {diag_3b['n_dropped_no_countries'] + diag_3b['n_dropped_one_country']:,}")
    print(f"        dropped (no modern sovereign): {diag_3b['n_dropped_no_modern_sovereign']:,}")
    print(f"        dropped (no year): {diag_3b['n_dropped_no_year']:,}")
    print(f"        dropped (no keyword near country): {diag_3b['n_dropped_no_keyword']:,}")
    print()

    print(f"[infobox] {len(infobox_rows):,} articles with conflict infoboxes")
    print()

    # -- Merge: LLM path = ALL bilateral survivors (not just tier-keyword);
    #    T4/T5 path = infobox rows.
    out_rows: list[dict] = []
    infobox_ids = set()
    for r in infobox_rows:
        infobox_ids.add(r["identifier"])
        abstract = r.get("abstract")
        infobox_names = r.get("infobox_names", [])
        tier_hints = _build_tier_hints(infobox_names, ["T4T5"])
        sections_excerpt = _section_excerpt(r.get("sections"))
        out_rows.append(
            {
                "identifier": r["identifier"],
                "name": r["name"],
                "url": r["url"],
                "main_entity_qid": r.get("main_entity_qid"),
                "abstract": abstract,
                "sections_excerpt": sections_excerpt,
                "infobox_names": infobox_names,
                "infoboxes": r.get("infoboxes"),
                "tier_hints": tier_hints,
                "tier_hints_v2": tier_hints,
                "date_created": r.get("date_created"),
                "date_modified": r.get("date_modified"),
                "matched_canonicals": r.get("_matched_canonicals", []),
                "matched_tiers": r.get("_matched_tiers", []),
                "path": "infobox",
            }
        )
    for r in bilateral_rows:
        # Avoid duplicating any article that ALSO has a conflict infobox
        if r["identifier"] in infobox_ids:
            continue
        abstract = r.get("abstract")
        infobox_names = _extract_infobox_names(r.get("infoboxes"))
        # No tier hints from regex — the LLM filter is the only tier
        # decision. We tag these as LLM-path with no tier hint.
        tier_hints = _build_tier_hints(infobox_names, None)
        sections_excerpt = _section_excerpt(r.get("sections"))
        out_rows.append(
            {
                "identifier": r["identifier"],
                "name": r["name"],
                "url": r["url"],
                "main_entity_qid": None,
                "abstract": abstract,
                "sections_excerpt": sections_excerpt,
                "infobox_names": infobox_names,
                "infoboxes": r.get("infoboxes"),
                "tier_hints": tier_hints,
                "tier_hints_v2": tier_hints,
                "date_created": r.get("date_created"),
                "date_modified": r.get("date_modified"),
                "matched_canonicals": r.get("_matched_canonicals", []),
                "matched_tiers": r.get("_matched_tiers", []),
                "path": "llm",
            }
        )
    print(f"[merge] LLM-path rows: {len(bilateral_rows):,}; infobox rows: {len(infobox_rows):,}; total: {len(out_rows):,}")
    print()

    # -- Write output
    if args.smoke_test:
        print(f"SMOKE TEST: skipping parquet write (--smoke-test {args.smoke_test})")
    else:
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as e:
            print("pyarrow is required. pip install 'pyarrow>=12.0'", file=sys.stderr)
            raise SystemExit(1) from e
        table = pa.Table.from_pylist(out_rows)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, args.out, compression="zstd")
        print(f"Wrote {args.out} ({len(out_rows):,} rows, {os.path.getsize(args.out) / 1e6:.1f} MB)")

    # -- Stats JSON
    stats = {
        "n_candidates": len(out_rows),
        "stage_3a_country_only": n_3a,
        "stage_3b_bilateral": {
            "n_in": diag_3b["n_in"],
            "n_kept": diag_3b["n_kept"],
            "n_dropped_no_countries": diag_3b["n_dropped_no_countries"],
            "n_dropped_one_country": diag_3b["n_dropped_one_country"],
            "n_dropped_no_modern_sovereign": diag_3b["n_dropped_no_modern_sovereign"],
            "n_dropped_no_year": diag_3b["n_dropped_no_year"],
            "n_dropped_no_keyword": diag_3b["n_dropped_no_keyword"],
        },
        # Backward-compat aliases for the validator (which still reads
        # the old keys). The actual 3c tier-keyword gate is gone.
        "stage_3a_broad": n_3a,
        "stage_3c_tier_keyword": {
            "n_in": diag_3b["n_kept"],
            "n_kept": diag_3b["n_kept"],
            "n_dropped": 0,
            "tier_counts": {},
            "co_occurrence_window": 0,
        },
        "infobox_t45": {
            "n": len(infobox_rows),
        },
        "n_llm_path": sum(1 for r in out_rows if r["path"] == "llm"),
        "n_infobox_path": sum(1 for r in out_rows if r["path"] == "infobox"),
        "parquet_glob": args.parquet_glob,
        "out": args.out,
    }
    with open(args.stats_out, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Stats -> {args.stats_out}")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
