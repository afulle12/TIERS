"""End-to-end smoke test for the wiki_pipeline.py orchestrator.

Strategy:
  1. Bypass the heavyweight stages (1, 2, 3) by writing synthetic
     inputs directly to their expected output paths.
  2. Patch the LLM call in `wiki_extract_llm_t123` with a deterministic
     stub so stage 5 doesn't need a real LM Studio server.
  3. Run the orchestrator with --stages 4,5,6 and verify that the final
     `conflict_dyads_wikipedia.csv` and validation report are written
     and that the manifest / state / log files are correct.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest.mock as um
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "build"))


SYN_GWN_MAP = [
    {"wikidata_qid": "Q34217", "gwno": "2", "country_name": "United States of America", "source": "stub"},
    {"wikidata_qid": "Q34214", "gwno": "200", "country_name": "United Kingdom", "source": "stub"},
    {"wikidata_qid": "Q34266", "gwno": "365", "country_name": "Russia", "source": "stub"},
    {"wikidata_qid": "Q34299", "gwno": "710", "country_name": "China", "source": "stub"},
    {"wikidata_qid": "Q255", "gwno": "255", "country_name": "Germany (Prussia)", "source": "stub"},
    {"wikidata_qid": "Q414", "gwno": "160", "country_name": "Argentina", "source": "stub"},
    {"wikidata_qid": "Q769", "gwno": "55", "country_name": "Grenada", "source": "stub"},
    {"wikidata_qid": "Q668", "gwno": "220", "country_name": "France", "source": "stub"},
]

SYN_INFOWAR = json.dumps([{
    "type": "infobox",
    "name": "Infobox military conflict",
    "has_parts": [
        {"type": "section", "name": "Conflict", "has_parts": [
            {"type": "field", "name": "Date", "value": "23 October 1983 – 12 December 1983", "links": []},
            {"type": "field", "name": "Combatant1", "value": "United States of America",
             "links": [{"text": "United States of America", "url": "x"}]},
            {"type": "field", "name": "Combatant2", "value": "Grenada",
             "links": [{"text": "Grenada", "url": "x"}]},
        ]}
    ],
}])

SYN_INFOBATTLE = json.dumps([{
    "type": "infobox",
    "name": "Infobox battle",
    "has_parts": [
        {"type": "section", "name": "Battle", "has_parts": [
            {"type": "field", "name": "Date", "value": "5 June 1982", "links": []},
            {"type": "field", "name": "Combatant1", "value": "Argentina",
             "links": [{"text": "Argentina", "url": "x"}]},
            {"type": "field", "name": "Combatant2", "value": "United Kingdom",
             "links": [{"text": "United Kingdom", "url": "x"}]},
        ]}
    ],
}])

SYN_INFOWAR_LONG = json.dumps([{
    "type": "infobox",
    "name": "Infobox war",
    "has_parts": [
        {"type": "section", "name": "War", "has_parts": [
            {"type": "field", "name": "Date", "value": "1 September 1939 – 2 September 1945", "links": []},
            {"type": "field", "name": "Combatant1", "value": "United Kingdom",
             "links": [{"text": "United Kingdom", "url": "x"}]},
            {"type": "field", "name": "Combatant2", "value": "Germany (Prussia)",
             "links": [{"text": "Germany (Prussia)", "url": "x"}]},
        ]}
    ],
}])

SYN_INFOEMPTY = "[]"

SYN_ARTICLES = [
    {
        "identifier": 1001,
        "name": "United States invasion of Grenada",
        "url": "x",
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
        "url": "x",
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
        "url": "x",
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
        "name": "2014 diplomatic crisis example",
        "url": "x",
        "main_entity_qid": "Q1",
        "abstract": "On 12 March 2014 the ambassador was recalled following a diplomatic protest.",
        "sections_excerpt": "## Context\nThe recall of ambassador...",
        "infobox_names": [],
        "tier_hints": ["T1"],
        "infoboxes": SYN_INFOEMPTY,
        "date_created": "2014-03-12",
        "date_modified": "2025-01-01",
    },
    {
        "identifier": 1005,
        "name": "2014 sanctions example",
        "url": "x",
        "main_entity_qid": "Q2",
        "abstract": "The United States imposed sanctions on Country X in 2014.",
        "sections_excerpt": "## Background\nThe economic sanction...",
        "infobox_names": [],
        "tier_hints": ["T2"],
        "infoboxes": SYN_INFOEMPTY,
        "date_created": "2014-04-01",
        "date_modified": "2025-01-01",
    },
    {
        "identifier": 1006,
        "name": "2014 proxy support example",
        "url": "x",
        "main_entity_qid": "Q3",
        "abstract": "Country A supplied weapons to rebels fighting Country B in 2014.",
        "sections_excerpt": "## Context\nThe armed group...",
        "infobox_names": [],
        "tier_hints": ["T3"],
        "infoboxes": SYN_INFOEMPTY,
        "date_created": "2014-05-01",
        "date_modified": "2025-01-01",
    },
]


def _stub_call_one(client, model, prompt_template, article, **kwargs):
    """Stubbed LLM call: returns canned events based on the article id."""
    art_id = article.get("identifier")
    if art_id == 1004:
        events = [
            {
                "year": 2014,
                "initiator_country": "United States of America",
                "target_country": "Russia",
                "tier": "T1",
                "confidence": 0.85,
            }
        ]
    elif art_id == 1005:
        events = [
            {
                "year": 2014,
                "initiator_country": "United States of America",
                "target_country": "China",
                "tier": "T2",
                "confidence": 0.9,
            }
        ]
    elif art_id == 1006:
        events = [
            {
                "year": 2014,
                "initiator_country": "Russia",
                "target_country": "United States of America",
                "tier": "T3",
                "confidence": 0.7,
            }
        ]
    else:
        events = []
    out = []
    for ev in events:
        info_map = {
            "T1": {"tier_label": "T1-Diplomatic Crisis", "hostlev": 1},
            "T2": {"tier_label": "T2-Economic/Display", "hostlev": 3},
            "T3": {"tier_label": "T3-Proxy/Indirect Military", "hostlev": 2},
        }
        info = info_map[ev["tier"]]
        out.append(
            {
                "article_id": int(art_id),
                "article_title": str(article.get("name") or ""),
                "infobox_name": "",
                "year": ev["year"],
                "start_year": ev["year"],
                "end_year": ev["year"],
                "tier": ev["tier"],
                "hostlev": info["hostlev"],
                "tier_label": info["tier_label"],
                "source": f"WIKI_{ev['tier']}",
                "initiator_country": ev["initiator_country"],
                "initiator_qid": None,
                "initiator_gwno": None,
                "target_country": ev["target_country"],
                "target_qid": None,
                "target_gwno": None,
                "confidence": ev["confidence"],
            }
        )
    return out, None


def main() -> int:
    # We will write synthetic inputs into the real on-disk locations
    # (data/processed/wiki_gwn_map.csv and tmp/wiki_tier_candidates.parquet),
    # then call the orchestrator with --stages 4,5,6. The orchestrator
    # imports the child modules and calls main(); we patch the LLM call
    # to avoid needing a real LM Studio.
    data_processed = ROOT / "data" / "processed"
    tmp = ROOT / "tmp"

    # 1. Write synthetic GWN map (used by stages 4 and 6).
    import csv

    gwn_path = data_processed / "wiki_gwn_map.csv"
    overrides_path = data_processed / "wiki_gwn_overrides.csv"
    backup_gwn = data_processed / "wiki_gwn_map.csv.orchestrator_smoke_backup"
    backup_overrides = data_processed / "wiki_gwn_overrides.csv.orchestrator_smoke_backup"
    if gwn_path.exists():
        shutil.copy(gwn_path, backup_gwn)
    if overrides_path.exists():
        shutil.copy(overrides_path, backup_overrides)
    with open(gwn_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["wikidata_qid", "gwno", "country_name", "source"])
        w.writeheader()
        for r in SYN_GWN_MAP:
            w.writerow(r)
    if not overrides_path.exists():
        with open(overrides_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["gwno", "wikidata_qid", "country_name"])
            w.writeheader()

    # 2. Write synthetic candidate Parquet.
    cand_path = tmp / "wiki_tier_candidates.parquet"
    backup_cand = tmp / "wiki_tier_candidates.parquet.orchestrator_smoke_backup"
    if cand_path.exists():
        shutil.copy(cand_path, backup_cand)
    table = pa.Table.from_pylist(SYN_ARTICLES)
    pq.write_table(table, cand_path, compression="zstd")

    # 3. Stub the LLM call.
    import wiki_extract_llm_t123 as llm

    with um.patch.object(llm, "_call_one", side_effect=_stub_call_one), \
         um.patch.object(llm, "_check_lmstudio", return_value="Qwen3.5-9B"):
        import wiki_pipeline as orch

        # 4. Run the orchestrator with --stages 4,5,6.
        rc = orch.main(["run", "--stages", "4,5,6"])
    assert rc == 0, f"orchestrator returned {rc}"

    # 5. Verify outputs.
    out_csv = data_processed / "conflict_dyads_wikipedia.csv"
    out_parquet = data_processed / "conflict_dyads_wikipedia.parquet"
    report_md = ROOT / "output" / "analysis" / "wiki_validation_report.md"
    manifest = tmp / "wiki_pipeline_manifest.json"
    state = tmp / "wiki_pipeline_state.json"
    run_summary = tmp / "wiki_pipeline_run.json"
    log_file = tmp / "wiki_pipeline.log"

    for p in (out_csv, out_parquet, report_md, manifest, state, run_summary, log_file):
        assert p.exists(), f"missing: {p}"

    # Final CSV should have all 5 tiers represented.
    out_rows = list(csv.DictReader(open(out_csv, encoding="utf-8")))
    tier_labels = {r["tier_label"] for r in out_rows}
    for t in ("T1-Diplomatic Crisis", "T2-Economic/Display",
              "T3-Proxy/Indirect Military", "T4-Limited Military", "T5-Strategic War"):
        assert t in tier_labels, f"missing tier {t} in output: {tier_labels}"

    # Manifest should have entries for stages 4, 5, 6.
    m = json.loads(manifest.read_text())
    assert set(m["stages"].keys()) == {"4", "5", "6"}, m["stages"].keys()
    for sn, entry in m["stages"].items():
        assert entry["exit_code"] == 0, entry
        assert entry["output_bytes"] >= 0
        assert "config_fingerprint" in entry
    # State file should also have the same stage keys.
    s = json.loads(state.read_text())
    assert set(s["stages"].keys()) == {"4", "5", "6"}, s["stages"].keys()

    # Log file should mention each stage.
    log_text = log_file.read_text()
    for n in (4, 5, 6):
        assert f"[stage {n}]" in log_text, f"log missing stage {n} entry"

    # Run summary should be a single JSON object with all stages.
    rs = json.loads(run_summary.read_text())
    assert rs["error_stage"] is None
    assert len(rs["stages"]) == 3

    # Restore real files.
    if backup_gwn.exists():
        shutil.move(backup_gwn, gwn_path)
    if backup_overrides.exists():
        shutil.move(backup_overrides, overrides_path)
    if backup_cand.exists():
        shutil.move(backup_cand, cand_path)

    # Clean up the orchestrator's generated files.
    for p in (out_csv, out_parquet, report_md, manifest, state, run_summary, log_file):
        if p.exists():
            p.unlink()

    print()
    print("ORCHESTRATOR SMOKE TEST PASSED")
    print(f"  stages 4,5,6 executed via orchestrator.main()")
    print(f"  final CSV: {len(out_rows)} rows, tiers={sorted(tier_labels)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
