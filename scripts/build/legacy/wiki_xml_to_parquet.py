#!/usr/bin/env python3
"""Convert a MediaWiki XML dump to wikimedia/structured-wikipedia Parquet shards.

The filter pipeline (`wiki_filter_candidates.py`) reads Parquet files matching
the `wikimedia/structured-wikipedia` schema on HuggingFace
(https://huggingface.co/datasets/wikimedia/structured-wikipedia). This script
produces equivalent Parquet shards from a raw MediaWiki XML multistream dump
(e.g. `enwiki-20260601-pages-articles-multistream.xml` from
https://dumps.wikimedia.org/enwiki/), so a fresh Wiki export can be fed into
the pipeline without waiting for the next HF release.

The conversion is intentionally pragmatic. It is not a 1:1 replacement for
Wikimedia Enterprise's structured parser, but it produces a schema-compatible
Parquet that the filter, the T4/T5 infobox parser, and the LLM path can all
consume.

Output schema matches the existing `data/raw/structured-wikipedia/enwiki/`
parquet exactly (19 columns). Columns populated:

    identifier      from <id>
    name            from <title>
    url             https://en.wikipedia.org/wiki/{title_urlencoded}
    date_created    earliest <timestamp> in <revision>
    date_modified   latest <timestamp> in <revision>
    abstract        first non-template, non-ref, non-heading paragraph
    infoboxes       JSON list of {{Infobox ...}} templates with parameters
    sections        JSON list of == / === headings with their text
    in_language     const {"identifier": "en"}

Columns left null or empty (HF has richer content here that the XML doesn't):

    main_entity, additional_entities, description, event, image,
    is_part_of, license, references, tables, version

Skipped: pages with ns != 0 and any page with a <redirect> element.

Outputs to `data/raw/structured-wikipedia/<out_dir>/data/enwiki_namespace_0_NN.parquet`
(86 shards by default, matching the existing convention; auto-discovery in
`wiki_filter_candidates.py` will pick the newest-mtime subdir).

Usage:
    .venv/bin/python scripts/build/wiki_xml_to_parquet.py \\
        --xml data/raw/enwikiV2/enwiki-20260601-pages-articles-multistream.xml \\
        --out-dir enwikiV2 \\
        --shards 86

Run on a small slice first to verify the schema:
    head -c 10000000 enwiki-...xml > /tmp/wiki_slice.xml
    .venv/bin/python scripts/build/wiki_xml_to_parquet.py \\
        --xml /tmp/wiki_slice.xml --out-dir _smoke --shards 2
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from lxml import etree
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw" / "structured-wikipedia"

# Number of parquet shards to produce. The existing enwiki/ snapshot has 86
# shards; matching that makes file counts and per-shard sizes comparable.
DEFAULT_SHARDS = 86

# Max rows buffered in memory before flushing to a parquet shard.
ROWS_PER_SHARD_BUFFER = 50_000

# Max infobox params to keep per article (saves memory, filter only inspects
# the first 30 anyway via _extract_infobox_names).
MAX_INFOBOX_PARAMS = 30

# Cap abstract length to keep parquet small.
ABSTRACT_MAX_CHARS = 2000

# Cap each section's text excerpt to keep parquet small.
SECTION_TEXT_MAX_CHARS = 4000

WIKIMEDIA_NAMESPACES = {
    "": 0, "Media": -2, "Special": -1, "Talk": 1, "User": 2, "User_talk": 3,
    "Wikipedia": 4, "Wikipedia_talk": 5, "File": 6, "File_talk": 7,
    "MediaWiki": 8, "MediaWiki_talk": 9, "Template": 10, "Template_talk": 11,
    "Help": 12, "Help_talk": 13, "Category": 14, "Category_talk": 15,
    "Portal": 100, "Portal_talk": 101, "Draft": 118, "Draft_talk": 119,
    "Module": 828, "Module_talk": 829,
}


# ---------------------------------------------------------------------------
# Schema: match the existing enwiki/ parquet exactly so DuckDB's read_parquet
# unifies the schema across all shards without coercion.
# ---------------------------------------------------------------------------

def _load_reference_schema(reference_parquet: Path) -> pa.schema:
    """Load the schema from an existing parquet so we can match it exactly."""
    return pq.read_schema(reference_parquet)


def _make_schema() -> pa.schema:
    """A simplified but compatible schema. The reference schema (above) is
    preferred; this is the fallback if no reference is available."""
    return pa.schema([
        pa.field("abstract", pa.string(), nullable=True),
        pa.field("additional_entities", pa.list_(pa.struct([
            pa.field("aspects", pa.list_(pa.string())),
            pa.field("identifier", pa.string()),
            pa.field("url", pa.string()),
        ])), nullable=True),
        pa.field("date_created", pa.timestamp("ms"), nullable=True),
        pa.field("date_modified", pa.timestamp("ms"), nullable=True),
        pa.field("description", pa.string(), nullable=True),
        pa.field("event", pa.struct([
            pa.field("date_created", pa.string()),
            pa.field("date_published", pa.string()),
            pa.field("fail_count", pa.int64()),
            pa.field("fail_reason", pa.string()),
            pa.field("identifier", pa.string()),
            pa.field("type", pa.string()),
        ]), nullable=True),
        pa.field("identifier", pa.int64(), nullable=True),
        pa.field("image", pa.struct([
            pa.field("content_url", pa.string()),
            pa.field("height", pa.int64()),
            pa.field("width", pa.int64()),
        ]), nullable=True),
        pa.field("in_language", pa.struct([pa.field("identifier", pa.string())]), nullable=True),
        pa.field("infoboxes", pa.string(), nullable=True),
        pa.field("is_part_of", pa.struct([
            pa.field("identifier", pa.string()),
            pa.field("url", pa.string()),
        ]), nullable=True),
        pa.field("license", pa.list_(pa.struct([
            pa.field("identifier", pa.string()),
            pa.field("name", pa.string()),
            pa.field("url", pa.string()),
        ])), nullable=True),
        pa.field("main_entity", pa.struct([
            pa.field("identifier", pa.string()),
            pa.field("url", pa.string()),
        ]), nullable=True),
        pa.field("name", pa.string(), nullable=True),
        pa.field("references", pa.list_(pa.struct([
            pa.field("identifier", pa.string()),
            pa.field("metadata", pa.string()),
            pa.field("source", pa.struct([
                pa.field("links", pa.list_(pa.struct([
                    pa.field("text", pa.string()),
                    pa.field("url", pa.string()),
                ]))),
                pa.field("value", pa.string()),
            ])),
            pa.field("text", pa.struct([
                pa.field("links", pa.list_(pa.struct([
                    pa.field("text", pa.string()),
                    pa.field("url", pa.string()),
                ]))),
                pa.field("value", pa.string()),
            ])),
            pa.field("type", pa.string()),
        ])), nullable=True),
        pa.field("sections", pa.string(), nullable=True),
        pa.field("tables", pa.string(), nullable=True),
        pa.field("url", pa.string(), nullable=True),
        pa.field("version", pa.struct([pa.field("identifier", pa.string())]), nullable=True),
    ])


# ---------------------------------------------------------------------------
# Wikitext parsing
# ---------------------------------------------------------------------------

# Strip these tags/templates first. Order matters.
_REF_RE = re.compile(r"<ref\b[^>]*?(?:/>|>.*?</ref>)", re.DOTALL | re.IGNORECASE)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_FILE_IMAGE_RE = re.compile(r"\[\[(?:File|Image|Kategorie|Category):[^\]]*\]\]", re.IGNORECASE)


def _strip_balanced_braces(text: str, open_c: str = "{{", close_c: str = "}}") -> str:
    """Strip all balanced {{...}} regions from text. Handles nesting."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text[i:i + 2] == open_c:
            depth = 1
            j = i + 2
            while j < n - 1 and depth > 0:
                if text[j:j + 2] == open_c:
                    depth += 1
                    j += 2
                elif text[j:j + 2] == close_c:
                    depth -= 1
                    j += 2
                else:
                    j += 1
            if depth == 0:
                i = j
                continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _strip_wikilinks(text: str) -> str:
    """[[Article|Display]] -> Display, [[Article]] -> Article."""
    return re.sub(r"\[\[([^\]|]+?)(?:\|([^\]]*?))?\]\]", lambda m: m.group(2) or m.group(1), text)


def _strip_markup(text: str) -> str:
    text = text.replace("'''", "").replace("''", "")
    text = re.sub(r"<[^>]+>", "", text)  # any leftover HTML tags
    text = re.sub(r"\[https?://[^\s\]]+ ([\w\s.,'-]+)\]", r"\1", text)  # [url label]
    text = re.sub(r"\[https?://[^\s\]]+\]", "", text)
    return text


def _make_abstract(wikitext: str) -> str:
    if not wikitext:
        return ""
    # Optimization: the first paragraph almost always lives in the first
    # 5KB of wikitext. Restrict processing to that prefix to avoid
    # stripping balanced braces through a 100KB article.
    text = wikitext[:5000]
    text = _HTML_COMMENT_RE.sub("", text)
    text = _REF_RE.sub("", text)
    text = _FILE_IMAGE_RE.sub("", text)
    text = _strip_balanced_braces(text)
    # Stop at the first section heading (== ... ==).
    m = re.search(r"^=+\s*[^=]", text, re.MULTILINE)
    if m:
        text = text[:m.start()]
    # First non-empty paragraph
    for para in re.split(r"\n\s*\n", text):
        para = _strip_wikilinks(para)
        para = _strip_markup(para)
        para = re.sub(r"\s+", " ", para).strip()
        if len(para) >= 40:  # skip stubs/single lines
            return para[:ABSTRACT_MAX_CHARS]
    return ""


# Heading splitter for sections.
_SECTION_RE = re.compile(r"^(={2,6})\s*([^=\n]+?)\s*\1\s*$", re.MULTILINE)


def _make_sections(wikitext: str) -> str:
    """Split the article into sections, returning JSON.

    Each section: {"name": str, "level": int, "content": str}.
    Section text is truncated to SECTION_TEXT_MAX_CHARS per section.
    """
    if not wikitext:
        return "[]"
    matches = list(_SECTION_RE.finditer(wikitext))
    if not matches:
        return "[]"
    sections = []
    for i, m in enumerate(matches):
        level = len(m.group(1))
        name = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(wikitext)
        body = wikitext[start:end]
        body = _HTML_COMMENT_RE.sub("", body)
        body = _REF_RE.sub("", body)
        body = re.sub(r"\s+", " ", body).strip()
        if body:
            sections.append({
                "name": name,
                "level": level,
                "content": body[:SECTION_TEXT_MAX_CHARS],
            })
    return json.dumps(sections, ensure_ascii=False)


# Infobox parser: find the FIRST {{Infobox ... }} block.
_INFOBOX_START_RE = re.compile(r"{{\s*[Ii]nfobox\s+", re.MULTILINE)


def _parse_one_infobox(body: str) -> dict | None:
    """Parse a single {{Infobox ... }} block. Returns {name, parameters}
    or None on failure."""
    # Find the matching closing }}
    depth = 2  # we're past the opening {{
    i = 2
    n = len(body)
    while i < n - 1 and depth > 0:
        if body[i:i + 2] == "{{":
            depth += 1
            i += 2
        elif body[i:i + 2] == "}}":
            depth -= 1
            i += 2
        elif body[i] == "|" and depth == 2:
            # found the first parameter; split into key|value
            break
        else:
            i += 1
    if depth != 2 or i >= n:
        return None
    head = body[2:i]  # between {{ and first |
    # The regex that found us already required {{[Ii]nfobox\s+, so the head
    # starts with "Infobox " (or "infobox "). Use the first whitespace- or
    # newline-separated token as the template name verbatim.
    name = head.split("\n", 1)[0].strip()
    if not name:
        return None
    # Now parse params from body[i+1:] up to matching }}
    inner = body[i + 1:]
    depth = 2
    j = 0
    while j < len(inner) - 1 and depth > 0:
        if inner[j:j + 2] == "{{":
            depth += 1
            j += 2
        elif inner[j:j + 2] == "}}":
            depth -= 1
            j += 2
        else:
            j += 1
    inner = inner[:j - 2] if depth == 0 else inner
    # Parse key=value pairs at top level
    params: dict[str, str] = {}
    k = 0
    while k < len(inner) and len(params) < MAX_INFOBOX_PARAMS:
        # find next |
        d = 0
        m_kv = k
        while m_kv < len(inner):
            if inner[m_kv:m_kv + 2] == "{{":
                d += 1
                m_kv += 2
            elif inner[m_kv:m_kv + 2] == "}}":
                d -= 1
                m_kv += 2
            elif inner[m_kv] == "|" and d == 0:
                break
            else:
                m_kv += 1
        kv = inner[k:m_kv]
        k = m_kv + 1
        if "=" not in kv:
            continue
        ek, _, ev = kv.partition("=")
        ek = ek.strip()
        ev = ev.strip()
        if not ek:
            continue
        # Strip wikitext from value
        ev = _HTML_COMMENT_RE.sub("", ev)
        ev = _REF_RE.sub("", ev)
        ev = _strip_balanced_braces(ev)
        ev = _strip_wikilinks(ev)
        ev = _strip_markup(ev)
        ev = re.sub(r"\s+", " ", ev).strip()
        if len(ev) > 1000:
            ev = ev[:1000]
        params[ek] = ev
    return {"name": name, "parameters": params}


def _make_infoboxes(wikitext: str) -> str:
    """Find all {{Infobox ...}} blocks, return JSON list of {name, parameters}.
    Limited to the first 3 infoboxes per article for speed.
    Optimization: the first infobox is almost always in the first 3KB
    of wikitext. We try the prefix first; if none found, fall back to
    the full text.
    """
    if not wikitext:
        return "[]"
    head = wikitext[:3000]
    if not _INFOBOX_START_RE.search(head):
        if not _INFOBOX_START_RE.search(wikitext):
            return "[]"
        head = wikitext
    out = []
    for m in _INFOBOX_START_RE.finditer(head):
        body = head[m.start():]
        info = _parse_one_infobox(body)
        if info is not None:
            out.append(info)
            if len(out) >= 3:
                break
    return json.dumps(out, ensure_ascii=False)


# ---------------------------------------------------------------------------
# XML streaming
# ---------------------------------------------------------------------------

def _url_for(title: str) -> str:
    return "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe="()_,")


def _to_ms(ts: str) -> int | None:
    """Parse a MediaWiki timestamp (ISO 8601 with Z) and return epoch ms.
    Returns None on failure."""
    if not ts:
        return None
    try:
        # 2024-04-15T14:38:04Z
        from datetime import datetime, timezone
        return int(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000)
    except ValueError:
        return None


class _ProgressFile:
    """Thin file wrapper that updates a tqdm bar on every read()."""

    def __init__(self, path: Path, pbar: "tqdm[bytes]") -> None:
        self._fh = open(path, "rb")
        self._pbar = pbar

    def read(self, size: int = -1) -> bytes:
        chunk = self._fh.read(size)
        self._pbar.update(len(chunk))
        return chunk

    # lxml may call these on the underlying file object
    def seek(self, offset: int, whence: int = 0) -> int:
        return self._fh.seek(offset, whence)

    def tell(self) -> int:
        return self._fh.tell()

    def close(self) -> None:
        self._fh.close()

    @property
    def name(self) -> str:
        return self._fh.name

    def __getattr__(self, name: str):
        return getattr(self._fh, name)


def stream_pages(xml_path: Path, pbar: "tqdm[bytes] | None" = None):
    """Yield (identifier, name, redirect_title, timestamps, wikitext) for each <page>.
    Skips ns != 0 and pages without a usable <id>.

    If *pbar* is given, wraps the file so the bar tracks bytes read."""
    source: Path | _ProgressFile
    if pbar is not None:
        source = _ProgressFile(xml_path, pbar)
    else:
        source = xml_path
    context = etree.iterparse(source, events=("end",), tag="{*}page", huge_tree=True)
    for _, elem in context:
        ns_el = elem.find("{*}ns")
        ns = int(ns_el.text) if ns_el is not None and ns_el.text else -1
        id_el = elem.find("{*}id")
        identifier = int(id_el.text) if id_el is not None and id_el.text else None
        title_el = elem.find("{*}title")
        title = title_el.text if title_el is not None else None
        redirect_el = elem.find("{*}redirect")
        redirect = redirect_el.get("title") if redirect_el is not None else None
        timestamps: list[str] = []
        latest_text = ""
        earliest_ts = None
        for rev in elem.findall("{*}revision"):
            ts_el = rev.find("{*}timestamp")
            if ts_el is not None and ts_el.text:
                timestamps.append(ts_el.text)
            text_el = rev.find("{*}text")
            if text_el is not None and text_el.text is not None:
                # last revision's text wins (latest)
                latest_text = text_el.text
                earliest_ts = ts_el.text if ts_el is not None else None
        if ns == 0 and identifier is not None and title is not None and redirect is None:
            yield identifier, title, timestamps, earliest_ts, latest_text
        elem.clear(keep_tail=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--xml", required=True, type=Path, help="Path to the MediaWiki XML dump.")
    p.add_argument("--out-dir", required=True, help="Subdir under data/raw/structured-wikipedia/.")
    p.add_argument("--shards", type=int, default=DEFAULT_SHARDS, help=f"Number of parquet shards (default {DEFAULT_SHARDS}).")
    p.add_argument("--rows-per-shard", type=int, default=ROWS_PER_SHARD_BUFFER, help="Approx rows per shard (default 50000).")
    p.add_argument("--max-articles", type=int, default=0, help="Stop after N articles (0 = no cap). For smoke tests.")
    p.add_argument("--reference-schema", type=Path, default=None,
                   help="Parquet file to copy the schema from (recommended for compatibility). "
                        f"Defaults to data/raw/structured-wikipedia/enwiki/data/enwiki_namespace_0_0.parquet.")
    args = p.parse_args()

    if not args.xml.exists():
        print(f"XML file not found: {args.xml}", file=sys.stderr)
        return 1

    out_root = DATA_RAW / args.out_dir / "data"
    out_root.mkdir(parents=True, exist_ok=True)

    # Schema: use the reference if available so the new parquets union cleanly
    # with the existing ones in DuckDB.
    if args.reference_schema is None:
        candidate = ROOT / "data" / "raw" / "structured-wikipedia" / "enwiki" / "data" / "enwiki_namespace_0_0.parquet"
        args.reference_schema = candidate if candidate.exists() else None
    if args.reference_schema is not None and args.reference_schema.exists():
        print(f"[setup] using reference schema from {args.reference_schema}")
        schema = _load_reference_schema(args.reference_schema)
    else:
        print(f"[setup] no reference parquet found, using built-in schema")
        schema = _make_schema()

    print(f"[setup] XML: {args.xml}  ({args.xml.stat().st_size / 1e9:.2f} GB)")
    print(f"[setup] output: {out_root}  ({args.shards} shards)")
    print(f"[setup] rows per shard buffer: {args.rows_per_shard:,}")
    print()

    in_language = {"identifier": "en"}

    shard_idx = 0
    rows_in_shard = 0
    buffer: dict[str, list] = {f.name: [] for f in schema}
    n_kept = 0
    n_total = 0
    t0 = time.time()
    xml_bytes = args.xml.stat().st_size

    def flush() -> None:
        nonlocal shard_idx, rows_in_shard
        if rows_in_shard == 0:
            return
        shard_path = out_root / f"enwiki_namespace_0_{shard_idx:02d}.parquet"
        table = pa.Table.from_pydict(buffer, schema=schema)
        pq.write_table(table, shard_path, compression="zstd")
        shard_idx += 1
        rows_in_shard = 0
        for k in buffer:
            buffer[k] = []

    def append(article: int, name: str, ts_first: str | None, ts_last: str | None, wikitext: str) -> None:
        nonlocal rows_in_shard, n_kept
        url = _url_for(name)
        abstract = _make_abstract(wikitext)
        infoboxes = _make_infoboxes(wikitext)
        sections = _make_sections(wikitext)
        # Map schema fields. Unknown fields (not in our parser) are filled with None.
        for f in schema:
            n = f.name
            if n == "identifier":
                buffer[n].append(article)
            elif n == "name":
                buffer[n].append(name)
            elif n == "url":
                buffer[n].append(url)
            elif n == "date_created":
                ms = _to_ms(ts_first) if ts_first else None
                buffer[n].append(ms)
            elif n == "date_modified":
                ms = _to_ms(ts_last) if ts_last else None
                buffer[n].append(ms)
            elif n == "abstract":
                buffer[n].append(abstract or None)
            elif n == "infoboxes":
                buffer[n].append(infoboxes)
            elif n == "sections":
                buffer[n].append(sections)
            elif n == "in_language":
                buffer[n].append(in_language)
            else:
                buffer[n].append(None)
        rows_in_shard += 1
        n_kept += 1
        if rows_in_shard >= args.rows_per_shard:
            flush()

    pbar = tqdm(
        total=xml_bytes,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc="Parsing XML",
        smoothing=0.05,
    )

    try:
        for identifier, title, timestamps, ts_first, wikitext in stream_pages(args.xml, pbar):
            n_total += 1
            pbar.set_postfix(articles=f"{n_total:,}", kept=f"{n_kept:,}", shards=shard_idx)
            if args.max_articles and n_kept >= args.max_articles:
                break
            ts_last = timestamps[-1] if timestamps else ts_first
            append(identifier, title, ts_first, ts_last, wikitext)
    except etree.XMLSyntaxError as e:
        pbar.write(f"\n[warn] XML syntax error after {n_total:,} pages: {e}", file=sys.stderr)
    finally:
        pbar.close()

    flush()

    total_bytes = sum(p.stat().st_size for p in out_root.glob("*.parquet"))
    elapsed = time.time() - t0
    print()
    print(f"[done] scanned {n_total:,} pages, kept {n_kept:,} articles")
    print(f"[done] wrote {shard_idx} shards to {out_root}  ({total_bytes / 1e9:.2f} GB)")
    print(f"[done] elapsed {elapsed / 60:.1f}m  ({n_kept / max(elapsed, 1):,.0f} art/s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
