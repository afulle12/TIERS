"""Build a Wikidata-QID <-> GWN-code reconciliation table.

Output:
  data/processed/wiki_gwn_map.csv
    Columns: wikidata_qid, gwno, country_name, source

How it works:
  1. Load the CShapes-2.0 country-year registry and extract the most
     recent canonical name for each GWN code (~200 states).
  2. Resolve each CShapes name to a Wikidata QID via the English
     Wikipedia API (action=query, prop=pageprops, ppprop=wikibase_item).
     This endpoint is the standard title -> QID lookup; it is much
     more permissive than the Wikidata SPARQL endpoint and does not
     return 429s under normal use.
  3. Apply a small hand-curated override file at
     `data/processed/wiki_gwn_overrides.csv` to cover the CShapes
     names that the API doesn't resolve (mostly historical states
     whose modern Wikipedia article has a different name).

Why not use a SPARQL query for this? Wikidata does not currently
have a clean external-id property for GWN codes. The candidate
property P5008 turns out to be "Game World Navigator ID", not GWN.
The Wikipedia API approach is the standard workaround used by other
research projects (see e.g. the Gleditsch-Ward numeric country
codes shipped in the `peacesciencer` R package).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
TMP = ROOT / "tmp"

CSHAPES_CSV = DATA_RAW / "CShapes-2.0.csv"
OUT_CSV = DATA_PROCESSED / "wiki_gwn_map.csv"
OVERRIDES_CSV = DATA_PROCESSED / "wiki_gwn_overrides.csv"

# English Wikipedia API. The MediaWiki action=query endpoint with
# prop=pageprops&ppprop=wikibase_item is the canonical title -> QID
# resolver used by the rest of the Wikimedia ecosystem.
WIKI_API = "https://en.wikipedia.org/w/api.php"

# Hand-curated fallback for GWN codes that the CShapes name -> QID
# resolution cannot find via the Wikipedia API. Common cases:
#   - Historical states whose modern Wikipedia article has a different
#     name (USSR, Yugoslavia, etc.).
#   - Names that the API can't disambiguate (small or contested states).
# Users are expected to extend this list on first run.
DEFAULT_OVERRIDES: list[dict[str, str]] = [
    # {"gwno": "365", "wikidata_qid": "Q34266", "country_name": "Russia (Soviet Union)"},
    # {"gwno": "345", "wikidata_qid": "Q36704", "country_name": "Yugoslavia"},
]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--cshapes-csv",
        default=str(CSHAPES_CSV),
        help="Path to the CShapes-2.0 country-year CSV.",
    )
    p.add_argument(
        "--out",
        default=str(OUT_CSV),
        help="Output wiki_gwn_map.csv path.",
    )
    p.add_argument(
        "--overrides-out",
        default=str(OVERRIDES_CSV),
        help="Override file path (read if it exists, written as a template otherwise).",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional cap on the number of CShapes names to resolve (0 = no cap).",
    )
    p.add_argument(
        "--user-agent",
        default="TIERS-WikipediaPipeline/1.0 (research use; contact: see README)",
        help="User-Agent header for the Wikipedia API request.",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="Number of titles per API request (max 50).",
    )
    return p.parse_args()


def _load_cshapes_modern_names(cshapes_csv: str) -> dict[str, str]:
    """Return a {gwno: most-recent cntry_name} mapping from CShapes."""
    by_gw: dict[str, str] = {}
    if not Path(cshapes_csv).exists():
        print(f"WARNING: CShapes CSV not found at {cshapes_csv}", file=sys.stderr)
        return by_gw
    csv.field_size_limit(sys.maxsize)
    with open(cshapes_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                gw = str(int(float(row["gwcode"])))
            except (KeyError, ValueError):
                continue
            name = (row.get("cntry_name") or "").strip()
            if not name:
                continue
            by_gw[gw] = name
    return by_gw


def _load_overrides(path: str) -> list[dict[str, str]]:
    if not Path(path).exists():
        return list(DEFAULT_OVERRIDES)
    out: list[dict[str, str]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("gwno") or not row.get("wikidata_qid"):
                continue
            out.append(
                {
                    "gwno": str(row["gwno"]).strip(),
                    "wikidata_qid": str(row["wikidata_qid"]).strip(),
                    "country_name": (row.get("country_name") or "").strip(),
                }
            )
    return out


def _write_overrides_template(path: str) -> None:
    """Write an empty overrides file with the expected header so users
    know how to extend it."""
    if Path(path).exists():
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["gwno", "wikidata_qid", "country_name"]
        )
        writer.writeheader()
        for row in DEFAULT_OVERRIDES:
            writer.writerow(row)
    print(f"Wrote overrides template -> {path}")


def _wiki_api_titles_to_qids(
    titles: list[str], user_agent: str, max_retries: int = 4
) -> dict[str, str | None]:
    """Resolve a batch of Wikipedia article titles to their Wikidata QIDs
    via the MediaWiki action=query API. Returns a {title: qid} dict;
    the value is None if the title didn't resolve.

    Honors the Retry-After header on 429/503 responses; uses
    exponential backoff for transient network errors.
    """
    if not titles:
        return {}
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageprops",
        "ppprop": "wikibase_item",
        "redirects": "1",
        "titles": "|".join(titles),
    }
    url = WIKI_API + "?" + urlencode(params, quote_via=quote)
    last_err: Exception | None = None
    for attempt in range(max_retries):
        req = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            pages = payload.get("query", {}).get("pages", {})
            # The API returns a dict keyed by pageid; build title -> qid.
            out: dict[str, str | None] = {}
            for page in pages.values():
                # If redirects are followed, the original title is in
                # `redirects` and the new title is `title`.
                title = page.get("title") or ""
                qid = page.get("pageprops", {}).get("wikibase_item")
                if not title:
                    continue
                out[title] = qid
            return out
        except HTTPError as e:
            last_err = e
            retry_after = e.headers.get("Retry-After") if e.headers else None
            try:
                wait_s = max(1, int(retry_after)) if retry_after else min(2 ** attempt, 30)
            except (TypeError, ValueError):
                wait_s = min(2 ** attempt, 30)
            if attempt < max_retries - 1:
                print(
                    f"  Wikipedia API HTTP {e.code}; sleeping {wait_s}s...",
                    file=sys.stderr,
                )
                time.sleep(wait_s)
        except (URLError, TimeoutError) as e:
            last_err = e
            wait_s = min(2 ** attempt, 30)
            if attempt < max_retries - 1:
                print(
                    f"  Wikipedia API {type(e).__name__}; sleeping {wait_s}s...",
                    file=sys.stderr,
                )
                time.sleep(wait_s)
    raise RuntimeError(
        f"Wikipedia API lookup failed after {max_retries} attempts: {last_err}"
    )


def _name_variants(name: str) -> list[str]:
    """Return alternative spellings of a CShapes country name to try
    against the Wikipedia API. Order matters: earlier variants are
    tried first."""
    out = [name]
    # Strip a parenthetical and try the bare form: "Russia (Soviet Union)" -> "Russia"
    import re

    m = re.match(r"^(.*?)\s*\(.*?\)\s*$", name)
    if m:
        bare = m.group(1).strip()
        if bare and bare not in out:
            out.append(bare)
    # Common alias rewrites.
    aliases = {
        "united states of america": "United States",
        "cote d'ivoire": "Ivory Coast",
        "burkina faso (upper volta)": "Burkina Faso",
        "congo, democratic republic of (zaire)": "Democratic Republic of the Congo",
        "tanzania (tanganyika)": "Tanzania",
        "germany (prussia)": "Germany",
        "russia (soviet union)": "Russia",
        "yugoslavia": "Yugoslavia",
        "italy/sardinia": "Italy",
        "bosnia-herzegovina": "Bosnia and Herzegovina",
        "macedonia (fyrom/north macedonia)": "North Macedonia",
        "macedonia (fyrom)": "North Macedonia",
        "rumania": "Romania",
        "belarus (byelorussia)": "Belarus",
        "french guyana": "French Guiana",
        "german federal republic": "Germany",
        "german democratic republic": "East Germany",
        "swaziland (eswatini)": "Eswatini",
        "korea, people's republic of": "North Korea",
        "korea, republic of": "South Korea",
        "vietnam, democratic republic of": "Vietnam",
        "vietnam, republic of": "Vietnam",
        "yemen, people's republic of": "Yemen",
        "kyrgyz republic": "Kyrgyzstan",
        "east timor": "Timor-Leste",
        "bahamas": "The Bahamas",
        "gambia": "The Gambia",
    }
    key = name.lower().strip()
    if key in aliases:
        a = aliases[key]
        if a not in out:
            out.append(a)
    return out


def _resolve_cshapes_to_qids(
    names_by_gwno: dict[str, str], user_agent: str, batch_size: int
) -> dict[str, str]:
    """Resolve each CShapes name to a QID via batched Wikipedia API calls.
    For names that don't resolve directly, tries a small set of
    pre-defined variants (stripping parentheticals, common aliases).
    Returns a {gwno: qid} dict for the gwnos that resolved.
    """
    # Build a unique set of (name -> gwnos) so we don't redundantly
    # query the same name for multiple gwnos.
    name_to_gwnos: dict[str, list[str]] = {}
    for g, n in names_by_gwno.items():
        name_to_gwnos.setdefault(n, []).append(g)

    # First pass: try every CShapes name verbatim.
    unique_names = list(name_to_gwnos.keys())
    print(
        f"Resolving {len(unique_names):,} unique CShapes names via Wikipedia API...",
        file=sys.stderr,
    )
    gwno_to_qid: dict[str, str] = {}
    unresolved: list[str] = []
    n_batches = (len(unique_names) + batch_size - 1) // batch_size
    t0 = time.time()
    for i in range(0, len(unique_names), batch_size):
        batch = unique_names[i : i + batch_size]
        try:
            qids = _wiki_api_titles_to_qids(batch, user_agent)
        except Exception as e:
            print(f"  batch {i // batch_size + 1}/{n_batches} failed: {e}", file=sys.stderr)
            unresolved.extend(batch)
            continue
        for name in batch:
            qid = qids.get(name)
            if qid and qid.startswith("Q"):
                for g in name_to_gwnos[name]:
                    gwno_to_qid[g] = qid
            else:
                unresolved.append(name)
        if (i // batch_size) % 5 == 0 or (i + batch_size) >= len(unique_names):
            elapsed = time.time() - t0
            done = min(i + batch_size, len(unique_names))
            rate = done / max(elapsed, 1e-6)
            eta = (len(unique_names) - done) / max(rate, 1e-6)
            print(
                f"  [{done:>5}/{len(unique_names)}] "
                f"resolved={len(gwno_to_qid)}  unresolved={len(unresolved)}  "
                f"rate={rate:.1f}/s  eta={eta:.0f}s",
                file=sys.stderr,
            )

    # Second pass: for the unresolved names, try the variant list.
    if unresolved:
        variant_to_gwnos: dict[str, list[str]] = {}
        for n in unresolved:
            for v in _name_variants(n):
                if v not in name_to_gwnos:  # don't shadow first-pass results
                    variant_to_gwnos.setdefault(v, []).extend(name_to_gwnos[n])
        unique_variants = list(variant_to_gwnos.keys())
        print(
            f"Second pass: trying {len(unique_variants):,} variants for the "
            f"{len(unresolved):,} unresolved names...",
            file=sys.stderr,
        )
        still_unresolved: list[str] = []
        t1 = time.time()
        for i in range(0, len(unique_variants), batch_size):
            batch = unique_variants[i : i + batch_size]
            try:
                qids = _wiki_api_titles_to_qids(batch, user_agent)
            except Exception as e:
                print(
                    f"  variant batch {i // batch_size + 1} failed: {e}",
                    file=sys.stderr,
                )
                still_unresolved.extend(batch)
                continue
            for v in batch:
                qid = qids.get(v)
                if qid and qid.startswith("Q"):
                    for g in variant_to_gwnos[v]:
                        if g not in gwno_to_qid:
                            gwno_to_qid[g] = qid
            elapsed = time.time() - t1
            done = min(i + batch_size, len(unique_variants))
            rate = done / max(elapsed, 1e-6)
            eta = (len(unique_variants) - done) / max(rate, 1e-6)
            if (i // batch_size) % 5 == 0 or done >= len(unique_variants):
                print(
                    f"  variants [{done:>5}/{len(unique_variants)}]  "
                    f"rate={rate:.1f}/s  eta={eta:.0f}s",
                    file=sys.stderr,
                )
        print(
            f"After both passes: resolved={len(gwno_to_qid)}  "
            f"unresolved={len(cs_gwnos := set(names_by_gwno.keys()) - set(gwno_to_qid.keys()))}",
            file=sys.stderr,
        )
    return gwno_to_qid


def main() -> int:
    args = _parse_args()
    if Path(args.out).exists():
        print(f"SKIPPED: {args.out} already exists ({Path(args.out).stat().st_size:,} bytes).")
        return 0
    TMP.mkdir(parents=True, exist_ok=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    cs_names = _load_cshapes_modern_names(args.cshapes_csv)
    print(f"CShapes: {len(cs_names):,} unique GWN codes")
    overrides = _load_overrides(args.overrides_out)
    _write_overrides_template(args.overrides_out)

    gwno_to_qid = _resolve_cshapes_to_qids(cs_names, args.user_agent, args.batch_size)
    if args.limit and args.limit > 0:
        # Apply the limit to the resolved gwnos.
        keep = dict(list(gwno_to_qid.items())[: args.limit])
        gwno_to_qid = keep

    # Build the final table.
    out_rows: list[dict[str, str]] = []
    for gwno, qid in gwno_to_qid.items():
        out_rows.append(
            {
                "wikidata_qid": qid,
                "gwno": gwno,
                "country_name": cs_names.get(gwno, ""),
                "source": "wikipedia_api",
            }
        )
    for o in overrides:
        qid = o["wikidata_qid"]
        gwno = o["gwno"]
        if not qid or not gwno:
            continue
        if gwno in gwno_to_qid:
            continue
        out_rows.append(
            {
                "wikidata_qid": qid,
                "gwno": gwno,
                "country_name": o["country_name"] or cs_names.get(gwno, ""),
                "source": "overrides",
            }
        )

    out_rows.sort(key=lambda r: (int(r["gwno"]), r["wikidata_qid"]))
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["wikidata_qid", "gwno", "country_name", "source"]
        )
        writer.writeheader()
        writer.writerows(out_rows)

    # Diagnostics
    gwnos_seen = {r["gwno"] for r in out_rows}
    cs_gwnos = set(cs_names.keys())
    missing = sorted(cs_gwnos - gwnos_seen, key=int)

    diag = {
        "n_cshapes_gwnos": len(cs_gwnos),
        "n_resolved_via_api": len(gwno_to_qid),
        "n_from_overrides": len([r for r in out_rows if r["source"] == "overrides"]),
        "n_total": len(out_rows),
        "n_cshapes_gwnos_covered": len(cs_gwnos & gwnos_seen),
        "n_cshapes_gwnos_missing": len(missing),
        "first_20_missing": [
            {"gwno": g, "name": cs_names.get(g, "?")} for g in missing[:20]
        ],
    }
    diag_path = TMP / "wiki_gwn_map_diag.json"
    with open(diag_path, "w") as f:
        json.dump(diag, f, indent=2)

    print()
    print(f"Wrote {args.out} ({len(out_rows):,} rows)")
    print(f"  resolved via Wikipedia API: {diag['n_resolved_via_api']}")
    print(f"  from overrides:             {diag['n_from_overrides']}")
    print(f"  CShapes coverage:           {diag['n_cshapes_gwnos_covered']}/{diag['n_cshapes_gwnos']}")
    if missing:
        print(f"  first 20 GWN codes missing:")
        for m in diag["first_20_missing"]:
            print(f"    {m['gwno']}: {m['name']}")
        print(f"  -> add to {args.overrides_out} as needed")
    print(f"Diagnostics -> {diag_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
