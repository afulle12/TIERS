#!/usr/bin/env python3
# Usage: .venv/bin/python scripts/build/_run_v2_pipeline.py
#
# This script uses pandas, duckdb, pyarrow, and openai — all installed
# in the project's .venv. Running it with a bare `python` (system
# interpreter) will fail with ModuleNotFoundError. Always invoke via
# the project's venv, e.g.:
#   .venv/bin/python scripts/build/_run_v2_pipeline.py
# or activate the venv first (`source .venv/bin/activate`) and then run
# with `python` as usual.

"""End-to-end runner for the v2 Wikipedia tier-extraction pipeline (7 stages).

Reads the same OLLAMA_* env vars as the orchestrator and runs all 7
stages in order. Designed to be the single command the user runs.

Stages:
  1. gwn_map            — CShapes -> Wikipedia API -> GWN code map
  2. filter             — DuckDB country scan + Python bilateral gate
  3. t01_filter         — LLM 0/1 (is this article an interstate conflict?)
  4. t45_extract        — LLM per-article extraction
  5. aggregate          — Pure Python. Expand duration to per-year rows.
  6. country_resolve    — LLM. Resolve unmapped country names.
  7. validate           — Cross-dataset comparison + diagnostics report.

Outputs:
  data/processed/conflict_dyads_wikipedia.csv
  data/processed/conflict_dyads_wikipedia.parquet
  output/analysis/wiki_validation_report.md
  output/analysis/wiki_mismatch_table.csv
  output/analysis/wiki_extraction_diagnostics.{md,csv}

Reads env vars:
  OLLAMA_BASE_URL    default http://192.168.86.18:1234/v1
  OLLAMA_MODEL       default nemotron-3-nano:4b
  OLLAMA_N_PARALLEL  default 5
  OLLAMA_BATCH_SIZE  default 3  (only stage 3)
  PIPELINE_MIN_CONFIDENCE  default 0.7
  PIPELINE_MAX_ARTICLES   default 0  (no cap)
  PIPELINE_LOG       default tmp/wiki_pipeline.log

Usage:
  python scripts/build/_run_v2_pipeline.py
  python scripts/build/_run_v2_pipeline.py --stages 1,2  # only the first two
  python scripts/build/_run_v2_pipeline.py --force       # re-run everything
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
TMP = ROOT / "tmp"


def _env() -> dict:
    """Collect the OLLAMA_* + PIPELINE_* env vars for the child subprocess."""
    return {k: v for k, v in os.environ.items() if k.startswith(("OLLAMA_", "PIPELINE_", "LMSTUDIO_"))}


def _run(cmd: list[str], *, env: dict | None = None, timeout: int = 86400) -> int:
    """Run a subprocess with the user's env. Returns the exit code."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    print(f"  $ {' '.join(cmd)}")
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=ROOT, env=full_env, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after {timeout}s")
        return 124
    elapsed = time.time() - t0
    if r.returncode != 0:
        print(f"  FAILED (exit={r.returncode}, elapsed={elapsed:.0f}s)")
    else:
        print(f"  OK ({elapsed:.0f}s)")
    return r.returncode


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument(
        "--stages",
        default="1,2,3,4,5,6,7",
        help="Comma-separated stage numbers to run (default: all 7).",
    )
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="(Reserved) force re-run of all stages; current behavior always re-runs.",
    )
    p.add_argument(
        "--smoke-test",
        type=int,
        default=0,
        help="Pass --max-articles N to stages 2/3/4 to limit them to N inputs (for smoke testing).",
    )
    return p.parse_args()


def _print_banner(stages: list[int]) -> None:
    print("=" * 70)
    print("Wikipedia tier-extraction pipeline (v2, 7 stages)")
    print("=" * 70)
    print()
    print("Env vars in effect:")
    for k in (
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "OLLAMA_N_PARALLEL",
        "OLLAMA_BATCH_SIZE",
        "PIPELINE_MIN_CONFIDENCE",
        "PIPELINE_MAX_ARTICLES",
        "PIPELINE_LOG",
    ):
        v = os.environ.get(k, "(unset)")
        print(f"  {k} = {v}")
    print()
    print(f"Stages to run: {stages}")
    print()


def main() -> int:
    args = _parse_args()
    try:
        stages = [int(s.strip()) for s in args.stages.split(",") if s.strip()]
    except ValueError:
        print(f"Invalid --stages value: {args.stages!r}")
        return 1
    for n in stages:
        if not 1 <= n <= 7:
            print(f"Stage out of range: {n} (must be 1-7)")
            return 1

    _print_banner(stages)

    n_parallel = int(os.environ.get("OLLAMA_N_PARALLEL", "5"))
    batch_size = int(os.environ.get("OLLAMA_BATCH_SIZE", "3"))
    min_confidence = float(os.environ.get("PIPELINE_MIN_CONFIDENCE", "0.7"))
    max_articles = args.smoke_test or int(os.environ.get("PIPELINE_MAX_ARTICLES", "0"))
    model = os.environ.get("OLLAMA_MODEL", "nemotron-3-nano:4b")
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://192.168.86.18:1234/v1")

    rc_total = 0
    t_start = time.time()

    # ------------------------------------------------------------------
    # Stage 1: gwn_map (skip if cached)
    # ------------------------------------------------------------------
    if 1 in stages:
        print("[1/7] Stage 1: gwn_map...")
        gwn_map = ROOT / "data" / "processed" / "wiki_gwn_map.csv"
        if gwn_map.exists():
            print("  SKIP (data/processed/wiki_gwn_map.csv exists)")
        else:
            rc = _run([sys.executable, str(SCRIPTS / "wiki_build_gwn_map.py")])
            if rc != 0:
                return rc

    # ------------------------------------------------------------------
    # Stage 2: filter
    # ------------------------------------------------------------------
    if 2 in stages:
        print()
        print("[2/7] Stage 2: filter (DuckDB country-only + bilateral gate)...")
        candidates_parquet = TMP / "wiki_tier_candidates.parquet"
        if candidates_parquet.exists() and not (max_articles > 0):
            print("  SKIP (tmp/wiki_tier_candidates.parquet exists; pass --smoke-test to re-run)")
        else:
            cmd = [sys.executable, str(SCRIPTS / "wiki_filter_candidates.py")]
            if max_articles > 0:
                cmd += ["--max-rows", str(max_articles)]
            rc = _run(cmd, timeout=4 * 3600)
            if rc != 0:
                return rc

    # ------------------------------------------------------------------
    # Stage 3: t01_filter (LLM 0/1)
    # ------------------------------------------------------------------
    if 3 in stages:
        print()
        print("[3/7] Stage 3: LLM 0/1 filter (batched 3-articles/prompt)...")
        print(f"  n_parallel={n_parallel}  batch_size={batch_size}  model={model}")
        cmd = [
            sys.executable, str(SCRIPTS / "wiki_extract_llm_t01_filter.py"),
            "--base-url", base_url, "--model", model,
            "--n-parallel", str(n_parallel), "--batch-size", str(batch_size),
        ]
        if max_articles > 0:
            cmd += ["--max-articles", str(max_articles)]
        rc = _run(cmd, timeout=20 * 3600)
        if rc != 0:
            return rc

    # ------------------------------------------------------------------
    # Stage 4: t45_extract (LLM per-article)
    # ------------------------------------------------------------------
    if 4 in stages:
        print()
        print("[4/7] Stage 4: LLM combined extraction (1-article/prompt)...")
        print(f"  n_parallel={n_parallel}  model={model}")
        cmd = [
            sys.executable, str(SCRIPTS / "wiki_extract_llm_t45.py"),
            "--base-url", base_url, "--model", model,
            "--n-parallel", str(n_parallel),
        ]
        if max_articles > 0:
            cmd += ["--max-articles", str(max_articles)]
        rc = _run(cmd, timeout=24 * 3600)
        if rc != 0:
            return rc

    # ------------------------------------------------------------------
    # Stage 5: aggregate (pure Python)
    # ------------------------------------------------------------------
    if 5 in stages:
        print()
        print("[5/7] Stage 5: aggregate (year expansion, GWN resolve, max-tier-per-year)...")
        rc = _run([
            sys.executable, str(SCRIPTS / "wiki_aggregate_dyads.py"),
            "--min-confidence", str(min_confidence),
        ])
        if rc != 0:
            return rc

    # ------------------------------------------------------------------
    # Stage 6: country_resolve (LLM)
    # ------------------------------------------------------------------
    if 6 in stages:
        print()
        print("[6/7] Stage 6: country resolution (LLM, unmapped names only)...")
        rc = _run([
            sys.executable, str(SCRIPTS / "wiki_resolve_unmapped_countries.py"),
            "--base-url", base_url, "--model", model,
            "--n-parallel", str(n_parallel),
        ], timeout=4 * 3600)
        if rc != 0:
            return rc

    # ------------------------------------------------------------------
    # Stage 7: validate (cross-dataset + diagnostics)
    # ------------------------------------------------------------------
    if 7 in stages:
        print()
        print("[7/7] Stage 7: cross-dataset validation + diagnostics...")
        rc = _run([
            sys.executable, str(SCRIPTS / "wiki_cross_dataset_validate.py"),
        ])
        if rc != 0:
            return rc

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    elapsed = time.time() - t_start
    print()
    print("=" * 70)
    print(f"DONE in {elapsed:.0f}s")
    print()
    out_csv = ROOT / "data" / "processed" / "conflict_dyads_wikipedia.csv"
    if out_csv.exists():
        sz = out_csv.stat().st_size
        print(f"  data/processed/conflict_dyads_wikipedia.csv  ({sz/1e6:.1f} MB)")
    print(f"  data/processed/conflict_dyads_wikipedia.parquet")
    print(f"  output/analysis/wiki_validation_report.md")
    print(f"  output/analysis/wiki_mismatch_table.csv")
    print(f"  output/analysis/wiki_extraction_diagnostics.{{md,csv}}")
    print()
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
