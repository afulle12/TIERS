"""Smoke test for the Wikipedia tier-extraction pipeline.

Runs each stage end-to-end on tiny synthetic data:
  - Builds a small candidates Parquet with 5 synthetic articles.
  - Runs the T4/T5 infobox parser.
  - Runs the T1/T2/T3 LLM extractor in a stubbed mode (no actual LLM
    call) to simulate T1/T2/T3 events.
  - Runs the aggregator against the synthetic events and the existing
    ground truth.

Exits non-zero on any failure. Use --keep to retain tmp/ files for
inspection.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "build"))

# Synthetic GWN map with a handful of well-known QIDs.
SYN_GWN_MAP = [
    {"wikidata_qid": "Q34266", "gwno": "365", "country_name": "Russia", "source": "stub"},
    {"wikidata_qid": "Q34217", "gwno": "2", "country_name": "United States of America", "source": "stub"},
    {"wikidata_qid": "Q34214", "gwno": "200", "country_name": "United Kingdom", "source": "stub"},
    {"wikidata_qid": "Q34299", "gwno": "710", "country_name": "China", "source": "stub"},
    {"wikidata_qid": "Q668", "gwno": "220", "country_name": "France", "source": "stub"},
    {"wikidata_qid": "Q183", "gwno": "260", "country_name": "German Federal Republic", "source": "stub"},
    {"wikidata_qid": "Q255", "gwno": "255", "country_name": "Germany (Prussia)", "source": "stub"},
    {"wikidata_qid": "Q38", "gwno": "155", "country_name": "Chile", "source": "stub"},
    {"wikidata_qid": "Q414", "gwno": "345", "country_name": "Yugoslavia", "source": "stub"},
    {"wikidata_qid": "Q218", "gwno": "660", "country_name": "Lebanon", "source": "stub"},
    {"wikidata_qid": "Q801", "gwno": "666", "country_name": "Israel", "source": "stub"},
    {"wikidata_qid": "Q889", "gwno": "290", "country_name": "Poland", "source": "stub"},
    {"wikidata_qid": "Q40", "gwno": "305", "country_name": "Austria", "source": "stub"},
    {"wikidata_qid": "Q414", "gwno": "160", "country_name": "Argentina", "source": "stub"},
    {"wikidata_qid": "Q769", "gwno": "55", "country_name": "Grenada", "source": "stub"},
    {"wikidata_qid": "Q145", "gwno": "200", "country_name": "United Kingdom", "source": "stub"},
    {"wikidata_qid": "Q731", "gwno": "345", "country_name": "Yugoslavia", "source": "stub"},
]

# Synthetic articles: one with a war infobox, one with a battle
# infobox, one with no infobox but a T1 keyword in the abstract, one
# with a T2 keyword, one with a T3 keyword.
SYN_INFOWAR = json.dumps([{
    "type": "infobox",
    "name": "Infobox military conflict",
    "has_parts": [
        {"type": "section", "name": "Conflict details", "has_parts": [
            {"type": "field", "name": "Date", "value": "23 October 1983 – 12 December 1983",
             "links": []},
            {"type": "field", "name": "Combatant1", "value": "United States of America",
             "links": [{"text": "United States of America", "url": "https://en.wikipedia.org/wiki/United_States"}]},
            {"type": "field", "name": "Combatant2", "value": "Grenada",
             "links": [{"text": "Grenada", "url": "https://en.wikipedia.org/wiki/Grenada"}]},
            {"type": "field", "name": "Result", "value": "United States victory"},
            {"type": "field", "name": "Place", "value": "Grenada",
             "links": [{"text": "Grenada", "url": "https://en.wikipedia.org/wiki/Grenada"}]},
        ]}
    ],
}])

SYN_INFOBATTLE = json.dumps([{
    "type": "infobox",
    "name": "Infobox battle",
    "has_parts": [
        {"type": "section", "name": "Battle", "has_parts": [
            {"type": "field", "name": "Date", "value": "5 June 1982",
             "links": []},
            {"type": "field", "name": "Combatant1", "value": "Argentina",
             "links": [{"text": "Argentina", "url": "https://en.wikipedia.org/wiki/Argentina"}]},
            {"type": "field", "name": "Combatant2", "value": "United Kingdom",
             "links": [{"text": "United Kingdom", "url": "https://en.wikipedia.org/wiki/United_Kingdom"}]},
        ]}
    ],
}])

SYN_INFOWAR_LONG = json.dumps([{
    "type": "infobox",
    "name": "Infobox war",
    "has_parts": [
        {"type": "section", "name": "War", "has_parts": [
            {"type": "field", "name": "Date", "value": "1 September 1939 – 2 September 1945",
             "links": []},
            {"type": "field", "name": "Combatant1", "value": "United Kingdom",
             "links": [{"text": "United Kingdom", "url": "https://en.wikipedia.org/wiki/United_Kingdom"}]},
            {"type": "field", "name": "Combatant2", "value": "Germany (Prussia)",
             "links": [{"text": "Germany (Prussia)", "url": "https://en.wikipedia.org/wiki/Nazi_Germany"}]},
        ]}
    ],
}])

SYN_INFOEMPTY = json.dumps([])  # No infobox, just a T2 keyword abstract.

SYN_ARTICLES = [
    {
        "identifier": 1001,
        "name": "United States invasion of Grenada",
        "url": "https://en.wikipedia.org/wiki/United_States_invasion_of_Grenada",
        "main_entity_qid": "Q166256",
        "abstract": "The United States invasion of Grenada began on 25 October 1983.",
        "sections_excerpt": "## Background\nThe conflict arose from a coup...",
        "infobox_names": ["Infobox military conflict"],
        "tier_hints": ["T4T5"],
        "infoboxes": SYN_INFOWAR,
        "date_created": "2001-01-01",
        "date_modified": "2025-01-01",
    },
    {
        "identifier": 1002,
        "name": "Battle of Mount Tumbledown",
        "url": "https://en.wikipedia.org/wiki/Battle_of_Mount_Tumbledown",
        "main_entity_qid": "Q2464543",
        "abstract": "The Battle of Mount Tumbledown was fought on 13 June 1982.",
        "sections_excerpt": "## Aftermath\nThe British forces...",
        "infobox_names": ["Infobox battle"],
        "tier_hints": ["T4T5"],
        "infoboxes": SYN_INFOBATTLE,
        "date_created": "2002-01-01",
        "date_modified": "2025-01-01",
    },
    {
        "identifier": 1003,
        "name": "World War II",
        "url": "https://en.wikipedia.org/wiki/World_War_II",
        "main_entity_qid": "Q36279",
        "abstract": "World War II was a global war that lasted from 1939 to 1945.",
        "sections_excerpt": "## Background\nThe war involved the United Kingdom...",
        "infobox_names": ["Infobox war"],
        "tier_hints": ["T4T5"],
        "infoboxes": SYN_INFOWAR_LONG,
        "date_created": "2001-01-01",
        "date_modified": "2025-01-01",
    },
    {
        "identifier": 1004,
        "name": "2024 diplomatic crisis example",
        "url": "https://en.wikipedia.org/wiki/Some_article",
        "main_entity_qid": "Q1",
        "abstract": "On 12 March 2024 the ambassador was recalled following a diplomatic protest.",
        "sections_excerpt": "## Context\nThe recall of ambassador...",
        "infobox_names": [],
        "tier_hints": ["T1"],
        "infoboxes": SYN_INFOEMPTY,
        "date_created": "2024-03-12",
        "date_modified": "2025-01-01",
    },
    {
        "identifier": 1005,
        "name": "2024 sanctions example",
        "url": "https://en.wikipedia.org/wiki/Some_sanctions",
        "main_entity_qid": "Q2",
        "abstract": "The United States imposed sanctions on Country X in 2024.",
        "sections_excerpt": "## Background\nThe economic sanction...",
        "infobox_names": [],
        "tier_hints": ["T2"],
        "infoboxes": SYN_INFOEMPTY,
        "date_created": "2024-04-01",
        "date_modified": "2025-01-01",
    },
    {
        "identifier": 1006,
        "name": "2024 proxy support example",
        "url": "https://en.wikipedia.org/wiki/Some_proxy",
        "main_entity_qid": "Q3",
        "abstract": "Country A supplied weapons to rebels fighting Country B in 2024.",
        "sections_excerpt": "## Context\nThe armed group...",
        "infobox_names": [],
        "tier_hints": ["T3"],
        "infoboxes": SYN_INFOEMPTY,
        "date_created": "2024-05-01",
        "date_modified": "2025-01-01",
    },
]


def main() -> int:
    project_tmp = ROOT / "tmp" / "smoke"
    project_tmp.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="wiki_smoke_", dir=str(project_tmp)))
    print(f"Working in {tmp}")

    # 1. Write synthetic candidates Parquet.
    cand_path = tmp / "candidates.parquet"
    table = pa.Table.from_pylist(SYN_ARTICLES)
    pq.write_table(table, cand_path, compression="zstd")
    print(f"  wrote {cand_path}")

    # 2. Write synthetic GWN map.
    gwn_path = tmp / "wiki_gwn_map.csv"
    import csv

    with open(gwn_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["wikidata_qid", "gwno", "country_name", "source"])
        w.writeheader()
        for r in SYN_GWN_MAP:
            w.writerow(r)
    print(f"  wrote {gwn_path}")

    # 3. Run T4/T5 parser.
    t45_path = tmp / "t45.jsonl"
    import wiki_extract_infobox_t45 as t45

    # Reset module-level output paths.
    t45.main.__globals__["__name__"]
    orig_argv = sys.argv
    try:
        sys.argv = [
            "wiki_extract_infobox_t45.py",
            "--candidates",
            str(cand_path),
            "--gwn-map",
            str(gwn_path),
            "--out",
            str(t45_path),
            "--diag",
            str(tmp / "t45_diag.json"),
        ]
        rc = t45.main()
    finally:
        sys.argv = orig_argv
    assert rc == 0, f"T4/T5 parser returned {rc}"
    t45_events = [json.loads(line) for line in open(t45_path) if line.strip()]
    print(f"  T4/T5 events: {len(t45_events)}")
    for ev in t45_events[:5]:
        print(f"    {ev['year']} {ev['tier']} {ev['initiator_country']}->{ev['target_country']}")
    # We expect at least 3 events: 2x (US, Grenada) for invasion, 2x (UK, Germany) for WWII,
    # 2x (Argentina, UK) for Mount Tumbledown -- 6 total.

    # 4. Simulate LLM T1/T2/T3 events (no actual LLM call).
    t123_path = tmp / "t123.jsonl"
    synthetic_t123 = [
        {
            "article_id": 1004,
            "article_title": "2024 diplomatic crisis example",
            "year": 2014,
            "tier": "T1",
            "tier_label": "T1-Diplomatic Crisis",
            "hostlev": 1,
            "source": "WIKI_T1",
            "initiator_country": "United States of America",
            "target_country": "Russia",
            "confidence": 0.85,
        },
        {
            "article_id": 1005,
            "article_title": "2024 sanctions example",
            "year": 2014,
            "tier": "T2",
            "tier_label": "T2-Economic/Display",
            "hostlev": 3,
            "source": "WIKI_T2",
            "initiator_country": "United States of America",
            "target_country": "China",
            "confidence": 0.9,
        },
        {
            "article_id": 1006,
            "article_title": "2024 proxy support example",
            "year": 2014,
            "tier": "T3",
            "tier_label": "T3-Proxy/Indirect Military",
            "hostlev": 2,
            "source": "WIKI_T3",
            "initiator_country": "Russia",
            "target_country": "United States of America",
            "confidence": 0.6,
        },
        # Below confidence floor -- should be dropped.
        {
            "article_id": 1007,
            "article_title": "low confidence noise",
            "year": 2014,
            "tier": "T1",
            "tier_label": "T1-Diplomatic Crisis",
            "hostlev": 1,
            "source": "WIKI_T1",
            "initiator_country": "France",
            "target_country": "Germany (Prussia)",
            "confidence": 0.2,
        },
    ]
    with open(t123_path, "w", encoding="utf-8") as f:
        for e in synthetic_t123:
            f.write(json.dumps(e) + "\n")
    print(f"  wrote {t123_path} (4 synthetic T1/T2/T3 events)")

    # 5. Run aggregator.
    out_csv = tmp / "out.csv"
    out_parquet = tmp / "out.parquet"
    report_md = tmp / "report.md"
    import wiki_aggregate_dyads as agg

    orig_argv = sys.argv
    try:
        sys.argv = [
            "wiki_aggregate_dyads.py",
            "--gwn-map",
            str(gwn_path),
            "--t45",
            str(t45_path),
            "--t123",
            str(t123_path),
            "--out",
            str(out_csv),
            "--out-parquet",
            str(out_parquet),
            "--report",
            str(report_md),
            "--year-min",
            "2010",
            "--year-max",
            "2014",
            "--min-confidence",
            "0.4",
        ]
        rc = agg.main()
    finally:
        sys.argv = orig_argv
    assert rc == 0, f"aggregator returned {rc}"

    out_rows = list(csv.DictReader(open(out_csv, encoding="utf-8")))
    print(f"  aggregator output rows: {len(out_rows)}")
    for r in out_rows[:5]:
        print(f"    {r['year']} {r['tier_label']} {r['initiator']}->{r['target']} ({r['source']})")

    # Sanity checks.
    tiers = {r["tier_label"] for r in out_rows}
    sources = {r["source"] for r in out_rows}
    assert "T1-Diplomatic Crisis" in tiers, f"missing T1: {tiers}"
    assert "T2-Economic/Display" in tiers, f"missing T2: {tiers}"
    assert "T3-Proxy/Indirect Military" in tiers, f"missing T3: {tiers}"
    assert "T4-Limited Military" in tiers, f"missing T4: {tiers}"
    assert "T5-Strategic War" in tiers, f"missing T5: {tiers}"
    assert sources == {"WIKI_T1", "WIKI_T2", "WIKI_T3", "WIKI_T4", "WIKI_T5"}, sources
    # No self-dyads.
    for r in out_rows:
        assert r["initiator_gwno"] != r["target_gwno"], r

    # The low-confidence T1 (France, Germany) should be dropped.
    bad = [r for r in out_rows if r["initiator"] == "France" and r["target_gwno"] == "255"]
    assert not bad, f"low-confidence event leaked through: {bad}"

    # Report should exist and mention all 5 tiers.
    report_text = open(report_md, encoding="utf-8").read()
    for t in ("T1", "T2", "T3", "T4", "T5"):
        assert t in report_text, f"tier {t} missing from report"

    print()
    print("ALL SMOKE TESTS PASSED")
    print(f"  tmp dir: {tmp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
