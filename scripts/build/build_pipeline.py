"""Single entry point to rebuild all Phase 2 data tables and verify contracts.

Runs the full build chain in dependency order using the active Python
interpreter, stopping immediately if any step or contract check fails:

  1. state_system.py
  2. source_coverage.py
  3. build_mid_dyads.py
  4. integrate_eusanct.py
  5. build_t1_sources.py
  5b. build_esd_t3.py
  6. build_dyad_states.py
  7. build_contiguity.py (skipped if shapely is absent and contiguity_xi.csv exists)
  8. build_rivalry.py
  9. build_trade_interdependence.py (unless --skip-trade)
 10. build_features.py
 11. build_features_v27.py
 12. build_features_v28.py
 13. pytest tests/test_data_contracts.py
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD_DIR = os.path.join(ROOT, "scripts", "build")
PROCESSED = os.path.join(ROOT, "data", "processed")


def _run(cmd: list[str], label: str) -> None:
    print(f"\n=== {label} ===", flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(f"Step failed ({proc.returncode}): {label}")
    print(f"--- {label} finished in {time.time() - t0:.1f}s ---", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild all TIERS Phase 2 tables and verify contracts.")
    parser.add_argument("--skip-trade", action="store_true", help="Reuse existing trade_interdependence table.")
    args = parser.parse_args()

    py = sys.executable
    steps = [
        ("state_system.py", "1. Build state system"),
        ("source_coverage.py", "2. Build source coverage matrix"),
        ("build_mid_dyads.py", "3. Build MID dyad events"),
        ("integrate_eusanct.py", "4. Integrate EUSANCT sanctions & threats"),
        ("build_t1_sources.py", "5. Build Section 2.8 T1 union events"),
        ("build_esd_t3.py", "5b. Build UCDP ESD T3 military-assistance events"),
        ("build_dyad_states.py", "6. Resolve dyad events -> dyad states"),
    ]
    for script, label in steps:
        _run([py, os.path.join(BUILD_DIR, script)], label)

    contiguity_out = os.path.join(PROCESSED, "contiguity_xi.csv")
    has_shapely = importlib.util.find_spec("shapely") is not None
    if has_shapely:
        _run([py, os.path.join(BUILD_DIR, "build_contiguity.py")], "7. Build CShapes contiguity & distance")
    elif os.path.exists(contiguity_out):
        print(f"\n=== 7. Skip build_contiguity.py (shapely not installed; reusing {contiguity_out}) ===")
    else:
        raise SystemExit("build_contiguity.py requires shapely and contiguity_xi.csv is missing.")

    _run([py, os.path.join(BUILD_DIR, "build_rivalry.py")], "8. Build directed rivalry")
    if not args.skip_trade:
        _run([py, os.path.join(BUILD_DIR, "build_trade_interdependence.py")], "9. Build trade interdependence")
    else:
        print("\n=== 9. Skip build_trade_interdependence.py (--skip-trade) ===")

    for script, label in (
        ("build_features.py", "10. Build base feature grid"),
        ("build_features_v27.py", "11. Build v27 structural feature grid"),
        ("build_features_v28.py", "12. Build v28 feature grid"),
    ):
        _run([py, os.path.join(BUILD_DIR, script)], label)

    _run([py, "-m", "pytest", os.path.join(ROOT, "tests", "test_data_contracts.py"), "-v"],
         "13. Verify data contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
