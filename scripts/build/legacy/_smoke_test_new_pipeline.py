#!/usr/bin/env python3
"""Smoke test for the new Wikipedia pipeline (Ollama + batched 0/1 filter).

Runs each LLM stage on a tiny subset of articles to:
  1. Verify the Ollama server is reachable
  2. Verify the batched 0/1 filter returns valid JSON
  3. Verify the tier+explanation pass returns valid JSON
  4. Verify the event extractor returns valid JSON
  5. Find a working n_parallel (smoke test ladder 8 -> 7 -> 6 -> 5 -> 4)

For the 0/1 filter, runs a 30-article smoke test. If that succeeds at
n_parallel=N, the user can use N for the full run. If it fails (crash,
OOM, JSON parse errors > 5%), try N-1.

Outputs to stdout only; does NOT touch any production files.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "scripts" / "build"

# Default: 30 articles per smoke test (3 batches of 10 with batch_size=3).
# This is fast enough to complete in <5 minutes even on slow Ollama.
N_ARTICLES_FILTER = int(os.environ.get("SMOKE_N_ARTICLES", "30"))
N_ARTICLES_TIER = int(os.environ.get("SMOKE_N_TIER", "5"))
N_ARTICLES_T123 = int(os.environ.get("SMOKE_N_T123", "3"))
PARALLEL_LADDER = [8, 7, 6, 5, 4]


def _run(cmd: list[str], *, env: dict | None = None, timeout: int = 600) -> tuple[int, str, str]:
    """Run a subprocess, capture stdout/stderr, return (exit, stdout, stderr)."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    print(f"  $ {' '.join(cmd)}")
    try:
        r = subprocess.run(
            cmd,
            cwd=ROOT,
            env=full_env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"TIMEOUT after {timeout}s"


def _check_ollama_reachable() -> bool:
    """Check that the Ollama server responds to GET /v1/models."""
    import urllib.request
    base = os.environ.get("OLLAMA_BASE_URL", "http://192.168.86.18:1234/v1")
    models_url = base.rstrip("/").removesuffix("/v1") + "/v1/models" if not base.endswith("/v1") else base + "/models"
    try:
        req = urllib.request.Request(models_url, headers={"Authorization": "Bearer ollama"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
            ids = [m.get("id", "?") for m in data.get("data", [])]
            print(f"  Ollama OK: {len(ids)} model(s): {ids[:5]}{'...' if len(ids) > 5 else ''}")
            return len(ids) > 0
    except Exception as e:
        print(f"  Ollama check failed: {e}")
        return False


def _check_parquet_exists() -> bool:
    p = ROOT / "tmp" / "wiki_tier_candidates.parquet"
    if not p.exists():
        print(f"  Missing: {p}")
        print(f"  Run `python scripts/build/wiki_filter_candidates.py` first to generate this.")
        return False
    return True


def smoke_test_filter(n_parallel: int) -> bool:
    """Smoke test the batched 0/1 filter at a given n_parallel."""
    print(f"\n[Smoke test] LLM 0/1 filter at n_parallel={n_parallel}, n_articles={N_ARTICLES_FILTER}")
    cmd = [
        sys.executable,
        str(SCRIPTS / "wiki_extract_llm_t123_filter.py"),
        "--max-articles", str(N_ARTICLES_FILTER),
        "--n-parallel", str(n_parallel),
        "--batch-size", "3",
    ]
    exit_code, stdout, stderr = _run(cmd, timeout=600)
    if exit_code != 0:
        print(f"  FAILED (exit={exit_code})")
        if stderr:
            print(f"  stderr (last 500 chars): {stderr[-500:]}")
        return False
    # Look at the run meta to confirm the filter produced results
    run_meta_path = ROOT / "tmp" / "wiki_t123_filter_run.json"
    if not run_meta_path.exists():
        print(f"  FAILED: no run meta at {run_meta_path}")
        return False
    meta = json.loads(run_meta_path.read_text())
    n_kept = meta.get("n_kept", 0)
    n_rejected = meta.get("n_rejected", 0)
    n_failed = meta.get("n_failed", 0)
    n_batches = meta.get("n_batches", 0)
    elapsed = meta.get("elapsed_seconds", 0)
    rate = (n_kept + n_rejected + n_failed) / max(elapsed, 1e-6)
    print(f"  kept={n_kept} rejected={n_rejected} failed={n_failed} batches={n_batches} elapsed={elapsed}s rate={rate:.2f}/s")
    fail_pct = n_failed / max(n_kept + n_rejected + n_failed, 1) * 100
    if fail_pct > 5:
        print(f"  FAILED: {fail_pct:.1f}% failure rate (>5% threshold)")
        return False
    return True


def smoke_test_tier(n_parallel: int) -> bool:
    """Smoke test the tier+explanation pass."""
    print(f"\n[Smoke test] LLM tier+explanation at n_parallel={n_parallel}, n_articles={N_ARTICLES_TIER}")
    cmd = [
        sys.executable,
        str(SCRIPTS / "wiki_extract_llm_t123_tier.py"),
        "--max-articles", str(N_ARTICLES_TIER),
        "--n-parallel", str(n_parallel),
    ]
    exit_code, stdout, stderr = _run(cmd, timeout=300)
    if exit_code != 0:
        print(f"  FAILED (exit={exit_code})")
        if stderr:
            print(f"  stderr (last 500 chars): {stderr[-500:]}")
        return False
    out_path = ROOT / "tmp" / "wiki_t123_tier.jsonl"
    if not out_path.exists():
        print(f"  FAILED: no output at {out_path}")
        return False
    # Read first row
    with open(out_path) as f:
        first = f.readline()
    if not first.strip():
        print(f"  FAILED: empty output")
        return False
    row = json.loads(first)
    print(f"  Sample row: tier={row.get('tier')} explanation={row.get('explanation', '')[:60]!r}")
    return True


def smoke_test_t123(n_parallel: int) -> bool:
    """Smoke test the event extractor."""
    print(f"\n[Smoke test] LLM event extractor at n_parallel={n_parallel}, n_articles={N_ARTICLES_T123}")
    cmd = [
        sys.executable,
        str(SCRIPTS / "wiki_extract_llm_t123.py"),
        "--max-articles", str(N_ARTICLES_T123),
        "--n-parallel", str(n_parallel),
    ]
    exit_code, stdout, stderr = _run(cmd, timeout=300)
    if exit_code != 0:
        print(f"  FAILED (exit={exit_code})")
        if stderr:
            print(f"  stderr (last 500 chars): {stderr[-500:]}")
        return False
    out_path = ROOT / "tmp" / "wiki_t123_extracted.jsonl"
    if not out_path.exists():
        print(f"  FAILED: no output at {out_path}")
        return False
    with open(out_path) as f:
        first = f.readline()
    if not first.strip():
        print(f"  no events emitted (this is OK if the smoke-test articles don't have events)")
        return True
    row = json.loads(first)
    print(f"  Sample event: tier={row.get('tier')} year={row.get('year')} initiator={row.get('initiator_country')!r} target={row.get('target_country')!r}")
    return True


def main() -> int:
    print("=" * 70)
    print("Wikipedia pipeline smoke test (Ollama + batched 0/1 filter)")
    print("=" * 70)

    print("\n[1] Checking Ollama server is reachable...")
    if not _check_ollama_reachable():
        print("\n  Start Ollama first: `ollama serve` and ensure the model is loaded:")
        print("    ollama pull nemotron-3-nano:4b")
        return 1

    print("\n[2] Checking tier candidates parquet exists...")
    if not _check_parquet_exists():
        return 1

    # Find a working n_parallel via the ladder
    working_n = None
    for n in PARALLEL_LADDER:
        if smoke_test_filter(n):
            working_n = n
            break
        print(f"  n_parallel={n} failed, trying next...")
    if working_n is None:
        print("\n  ALL n_parallel values in the ladder FAILED.")
        print("  Inspect tmp/wiki_t123_filter_debug/ for raw responses.")
        return 1
    print(f"\n  Working n_parallel for the 0/1 filter: {working_n}")

    # Tier smoke test
    if not smoke_test_tier(working_n):
        print("\n  Tier smoke test failed. Inspect tmp/wiki_t123_tier_debug/ for raw responses.")
        return 1

    # Event extractor smoke test
    if not smoke_test_t123(4):
        print("\n  Event extractor smoke test failed. Inspect tmp/wiki_t123_debug/ for raw responses.")
        return 1

    print()
    print("=" * 70)
    print("All smoke tests passed!")
    print(f"Recommended OLLAMA_N_PARALLEL={working_n}")
    print()
    print("Now run the full pipeline:")
    print(f"  export OLLAMA_N_PARALLEL={working_n}")
    print("  python scripts/build/wiki_pipeline.py run --stages 1,2,3,4,5,6,7,8,9,10")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
