"""Build the v28.0 model feature grid.

v28 keeps the v27 structural features and adds the shared CEPII-derived
economic-interdependence table built by `build_trade_interdependence.py`.

Reads:
  data/processed/dyads_with_features_v27.parquet or .csv
  data/processed/trade_interdependence.parquet or .csv

Writes:
  data/processed/dyads_with_features_v28.parquet
  data/processed/dyads_with_features_v28.csv
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = ROOT / "data" / "processed"

TRADE_COLUMNS = [
    "trade_source", "trade_value_unit", "exports_a_to_b", "exports_b_to_a",
    "imports_a_from_b", "imports_b_from_a", "total_exports_a", "total_imports_a",
    "total_trade_a", "total_exports_b", "total_imports_b", "total_trade_b",
    "trade_surface_ab", "trade_surface_norm_ab", "dep_a_on_b", "dep_b_on_a",
    "mutual_trade_dependence_ab", "import_dep_a_on_b", "import_dep_b_on_a",
    "import_leverage_a_over_b", "export_dep_a_on_b", "export_dep_b_on_a",
    "export_leverage_a_over_b", "trade_leverage_a_over_b",
    "trade_vulnerability_b_to_a", "trade_shock_ab",
]


def _read_base() -> pd.DataFrame:
    pq = DATA_PROCESSED / "dyads_with_features_v27.parquet"
    csv = DATA_PROCESSED / "dyads_with_features_v27.csv"
    if pq.exists():
        return pd.read_parquet(pq)
    return pd.read_csv(csv)


def _read_trade() -> pd.DataFrame:
    pq = DATA_PROCESSED / "trade_interdependence.parquet"
    csv = DATA_PROCESSED / "trade_interdependence.csv"
    if pq.exists():
        return pd.read_parquet(pq)
    return pd.read_csv(csv)


def _ensure_gwno_keys(grid: pd.DataFrame) -> pd.DataFrame:
    if {"initiator_gwno", "target_gwno"}.issubset(grid.columns):
        return grid
    cf = pd.read_csv(
        DATA_PROCESSED / "conflict_dyads_full.csv",
        usecols=["year", "initiator", "target", "initiator_gwno", "target_gwno"],
    )
    cf = cf.dropna(subset=["initiator_gwno", "target_gwno"])
    cf = cf.drop_duplicates(["year", "initiator", "target"], keep="first")
    out = grid.merge(cf, on=["year", "initiator", "target"], how="left")
    out = out.dropna(subset=["initiator_gwno", "target_gwno"])
    out["initiator_gwno"] = out["initiator_gwno"].astype(int)
    out["target_gwno"] = out["target_gwno"].astype(int)
    return out


def main() -> int:
    print("Loading v27 structural feature grid...")
    grid = _read_base()
    grid = _ensure_gwno_keys(grid)
    print(f"  {len(grid):,} rows")

    print("Loading trade interdependence source of truth...")
    trade = _read_trade()
    print(f"  {len(trade):,} rows")

    existing = [c for c in TRADE_COLUMNS if c in grid.columns]
    if existing:
        grid = grid.drop(columns=existing)
    grid = grid.merge(trade, on=["year", "initiator_gwno", "target_gwno"], how="left")

    for c in TRADE_COLUMNS:
        if c not in grid.columns:
            continue
        if c in {"trade_source", "trade_value_unit"}:
            grid[c] = grid[c].fillna("NONE" if c == "trade_source" else "none")
        else:
            grid[c] = pd.to_numeric(grid[c], errors="coerce").fillna(0.0)

    out_pq = DATA_PROCESSED / "dyads_with_features_v28.parquet"
    out_csv = DATA_PROCESSED / "dyads_with_features_v28.csv"
    grid.to_parquet(out_pq, index=False)
    grid.to_csv(out_csv, index=False)
    print(f"Wrote {out_pq}")
    print(f"Wrote {out_csv}")
    print("Trade coverage:")
    print(grid["trade_source"].value_counts(dropna=False).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
