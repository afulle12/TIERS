#!/usr/bin/env python3
"""Run the full Wikipedia tier-extraction pipeline (9 stages, Ollama).

The user is expected to provide the Wiki export themselves — place the
parquet shards under `data/raw/structured-wikipedia/<name>/data/`. The
filter (stage 2) auto-discovers the most recently modified subdir.

This wrapper runs:
  1. Stage 1: gwn_map (skip if cached)
  2. Stage 2: filter (DuckDB country-only + bilateral gate)
  3. Stage 3: T4/T5 infobox parser
  4. Stage 4: T4 -> T5 LLM confirm (small, ~31 candidates)
  5. Stage 5: LLM 0/1 filter (batched 3-articles/prompt)
  6. Stage 6: LLM tier + explanation (1-article/prompt)
  7. Stage 7: LLM event extraction (1-article/prompt, CoT)
  7.5. correlate tier+explanation with events
  8. Stage 8: aggregator
  9. Stage 9: validate

Reads OLLAMA_* env vars. The user is expected to have run the smoke
test first (`python scripts/build/_smoke_test_new_pipeline.py`) to
verify Ollama and find a working OLLAMA_N_PARALLEL.

Outputs:
  data/processed/conflict_dyads_wikipedia.csv
  data/processed/conflict_dyads_wikipedia.parquet
  output/analysis/wiki_validation_report.md
  output/analysis/wiki_extraction_diagnostics.{md,csv}
  output/analysis/wiki_mismatch_table.csv
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "scripts" / "build"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the full Wikipedia tier-extraction pipeline")
    p.add_argument("--force", "-f", action="store_true",
                   help="Force re-run of all stages, ignoring cached outputs")
    return p.parse_args()


def _run(cmd: list[str], *, env: dict | None = None, timeout: int = 86400) -> int:
    """Run a subprocess with the user's env. Returns the exit code."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    print(f"  $ {' '.join(cmd)}")
    t0 = time.time()
    r = subprocess.run(cmd, cwd=ROOT, env=full_env, timeout=timeout)
    elapsed = time.time() - t0
    if r.returncode != 0:
        print(f"  FAILED (exit={r.returncode}, elapsed={elapsed:.0f}s)")
    else:
        print(f"  OK ({elapsed:.0f}s)")
    return r.returncode


def main(force: bool = False) -> int:
    print("=" * 70)
    print("Wikipedia tier-extraction pipeline (Ollama, batched 0/1 filter)")
    print("=" * 70)
    print()
    print("Env vars in effect:")
    for k in ("OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_N_PARALLEL", "OLLAMA_BATCH_SIZE", "PIPELINE_MIN_CONFIDENCE"):
        v = os.environ.get(k, "(unset)")
        print(f"  {k} = {v}")
    print()

    n_parallel = int(os.environ.get("OLLAMA_N_PARALLEL", "8"))
    batch_size = int(os.environ.get("OLLAMA_BATCH_SIZE", "3"))
    min_confidence = float(os.environ.get("PIPELINE_MIN_CONFIDENCE", "0.4"))
    model = os.environ.get("OLLAMA_MODEL", "nemotron-3-nano:4b")
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://192.168.86.18:1234/v1")

    # ------------------------------------------------------------------
    # Stage 1: gwn_map (skip if cached)
    # ------------------------------------------------------------------
    print("[1/9] Stage 1: gwn_map...")
    gwn_map = ROOT / "data" / "processed" / "wiki_gwn_map.csv"
    if force and gwn_map.exists():
        gwn_map.unlink()
        print("  (--force: deleted cached wiki_gwn_map.csv)")
    if not gwn_map.exists():
        rc = _run([sys.executable, str(SCRIPTS / "wiki_build_gwn_map.py")])
        if rc != 0:
            return rc
    else:
        print("  SKIP (data/processed/wiki_gwn_map.csv exists)")

    # ------------------------------------------------------------------
    # Stage 2: filter (auto-discovers the user's Wiki export)
    #
    # DuckDB pass over the full snapshot is the slowest stage (~9-17h).
    # If a candidates parquet already exists, ask the user whether to
    # skip (use cache) or rerun. Override with PIPELINE_FORCE_STAGE2=1
    # to skip the prompt and always rerun.
    # ------------------------------------------------------------------
    print("\n[2/9] Stage 2: filter (DuckDB country-only + bilateral gate)...")
    candidates_parquet = ROOT / "tmp" / "wiki_tier_candidates.parquet"
    force_s2 = force or os.environ.get("PIPELINE_FORCE_STAGE2", "0") == "1"
    skip = False
    if candidates_parquet.exists() and not force_s2:
        age_h = (time.time() - candidates_parquet.stat().st_mtime) / 3600
        try:
            import pyarrow.parquet as pq
            n_rows = pq.read_table(candidates_parquet, columns=["identifier"]).num_rows
        except Exception:
            n_rows = "?"
        print(f"  Found existing {candidates_parquet.name} ({n_rows} rows, {age_h:.1f}h old)")
        print("  [s]kip (use cached) / [r]erun DuckDB pass (~9-17h) / [q]uit")
        while True:
            try:
                ans = input("  Choice [s/r/q]: ").strip().lower()
            except EOFError:
                ans = "q"
            if ans in ("s", ""):
                skip = True
                break
            if ans == "r":
                candidates_parquet.unlink()
                break
            if ans == "q":
                print("  Aborted by user.")
                return 0
            print("  Please answer s, r, or q.")
    if skip:
        print("  SKIP (using cached candidates)")
    else:
        rc = _run([sys.executable, str(SCRIPTS / "wiki_filter_candidates.py")])
        if rc != 0:
            return rc

    # ------------------------------------------------------------------
    # Stages 3-4: T4/T5 infobox path (no LLM)
    # ------------------------------------------------------------------
    print("\n[3/9] Stage 3: T4/T5 infobox parser...")
    rc = _run([sys.executable, str(SCRIPTS / "wiki_extract_infobox_t45.py")])
    if rc != 0:
        return rc

    print("\n[4/9] Stage 4: T4 -> T5 LLM confirm pass (31 candidates)...")
    candidates = ROOT / "tmp" / "wiki_t45_t5_candidates.jsonl"
    if candidates.exists() and candidates.stat().st_size > 0:
        rc = _run([
            sys.executable, str(SCRIPTS / "wiki_extract_llm_t45_ambiguous.py"),
            "--base-url", base_url, "--model", model, "--n-parallel", "1",
        ])
        if rc != 0:
            print("  WARN: T4->T5 confirm failed; continuing.")
    else:
        print("  SKIP (no T5 candidates)")

    # ------------------------------------------------------------------
    # Stages 5-7: LLM path (3 passes)
    # ------------------------------------------------------------------
    print("\n[5/9] Stage 5: LLM 0/1 filter (batched 3-articles/prompt)...")
    print(f"  n_parallel={n_parallel}  batch_size={batch_size}  model={model}")
    rc = _run([
        sys.executable, str(SCRIPTS / "wiki_extract_llm_t123_filter.py"),
        "--base-url", base_url, "--model", model,
        "--n-parallel", str(n_parallel), "--batch-size", str(batch_size),
    ])
    if rc != 0:
        return rc

    print("\n[6/9] Stage 6: LLM tier + explanation (1-article/prompt)...")
    print(f"  n_parallel={n_parallel}  model={model}")
    rc = _run([
        sys.executable, str(SCRIPTS / "wiki_extract_llm_t123_tier.py"),
        "--base-url", base_url, "--model", model, "--n-parallel", str(n_parallel),
    ])
    if rc != 0:
        return rc

    print("\n[7/9] Stage 7: LLM event extraction (1-article/prompt, CoT)...")
    print(f"  n_parallel={n_parallel}  model={model}")
    rc = _run([
        sys.executable, str(SCRIPTS / "wiki_extract_llm_t123.py"),
        "--base-url", base_url, "--model", model, "--n-parallel", str(n_parallel),
        "--min-confidence", str(min_confidence),
    ])
    if rc != 0:
        return rc

    # ------------------------------------------------------------------
    # Stage 7.5: correlate tier+explanation with extracted events
    # ------------------------------------------------------------------
    print("\n[7/9] Stage 7.5: correlate tier+explanation with events...")
    rc = _run([sys.executable, str(SCRIPTS / "wiki_correlate_t123.py")])
    if rc != 0:
        print("  WARN: correlate failed; aggregator will fall back to the JSONL path.")

    # ------------------------------------------------------------------
    # Stage 8: aggregator
    # ------------------------------------------------------------------
    print("\n[8/9] Stage 8: aggregator...")
    rc = _run([
        sys.executable, str(SCRIPTS / "wiki_aggregate_dyads.py"),
        "--min-confidence", str(min_confidence),
    ])
    if rc != 0:
        return rc

    # ------------------------------------------------------------------
    # Stage 9: validate
    # ------------------------------------------------------------------
    print("\n[9/9] Stage 9: validate...")
    rc = _run([sys.executable, str(SCRIPTS / "wiki_validate.py")])
    if rc != 0:
        return rc

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    print("\nDONE!")
    print()
    print("Outputs:")
    print(f"  data/processed/conflict_dyads_wikipedia.csv  ({os.path.getsize(ROOT / 'data' / 'processed' / 'conflict_dyads_wikipedia.csv') / 1e3:.1f} KB)")
    print(f"  data/processed/conflict_dyads_wikipedia.parquet")
    print(f"  output/analysis/wiki_validation_report.md")
    print(f"  output/analysis/wiki_extraction_diagnostics.{{md,csv}}")
    print(f"  output/analysis/wiki_mismatch_table.csv")
    print()
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(force=_parse_args().force))
