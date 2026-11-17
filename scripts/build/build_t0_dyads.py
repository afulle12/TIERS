"""Build conflict_dyads_full.csv (T0-T5) from the combined T1-T5 dataset
(data/processed/conflict_dyads.csv + EUSANCT-derived T2 rows).

For every directed pair of distinct countries in the union of all
initiator/target names, across every year 1900-2025, if no T1-T5 event
exists in data/processed/conflict_dyads_combined.csv, insert a T0 (peace) row.
"""
from __future__ import annotations

import os
import time
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
SRC = os.path.join(DATA_PROCESSED, "conflict_dyads_combined.csv")
OUT_CSV = os.path.join(DATA_PROCESSED, "conflict_dyads_full.csv")
OUT_PARQUET = os.path.join(DATA_PROCESSED, "conflict_dyads_full.parquet")
STATS = os.path.join(OUT_ANALYSIS, "t0_coverage.csv")
T0_LABEL = "T0-No Conflict/Peace"


def main() -> int:
    t0 = time.time()
    df = pd.read_csv(SRC, dtype={"year": int})
    print(f"Loaded {len(df):,} T1-T5 rows from {SRC} in {time.time()-t0:.1f}s")
    print(f"  sources: {df.source.value_counts().to_dict()}")

    countries = sorted(set(df.initiator) | set(df.target))
    year_min, year_max = int(df.year.min()), int(df.year.max())
    years = list(range(year_min, year_max + 1))
    print(f"Countries: {len(countries)} | Years: {year_min}-{year_max} ({len(years)})")

    gwno_map: dict[str, int] = {}
    for name_col, gwno_col in (("initiator", "initiator_gwno"), ("target", "target_gwno")):
        for name, code in df[[name_col, gwno_col]].dropna().drop_duplicates().itertuples(index=False):
            gwno_map.setdefault(name, int(code))
    print(f"GWNOs resolved for {len(gwno_map)}/{len(countries)} countries")

    t1 = time.time()
    grid = pd.MultiIndex.from_product(
        [countries, countries, years],
        names=["initiator", "target", "year"],
    ).to_frame(index=False)
    grid = grid[grid.initiator != grid.target].reset_index(drop=True)
    n_grid = len(grid)
    print(f"Full directed dyad-year grid (no self-loops): {n_grid:,} rows in {time.time()-t1:.1f}s")

    t2 = time.time()
    keys = df[["year", "initiator", "target"]].drop_duplicates()
    keys["_has_event"] = 1
    merged = grid.merge(keys, on=["year", "initiator", "target"], how="left")
    has_event = merged["_has_event"] == 1
    print(f"Merge done in {time.time()-t2:.1f}s")

    t0_df = merged.loc[~has_event].drop(columns="_has_event").copy()
    t0_df["hostlev"] = 1
    t0_df["uiw_tier"] = 0
    t0_df["tier_label"] = T0_LABEL
    t0_df["initiator_gwno"] = t0_df["initiator"].map(gwno_map)
    t0_df["target_gwno"] = t0_df["target"].map(gwno_map)
    t0_df["source"] = "INFERRED"
    for c in (
        "conflict_id", "dyad_id", "side_backed", "intensity_level", "D_k",
        "attribution", "selective", "targeted", "corroborated",
        "incompatibility", "territory_name", "region", "n_conflicts_aggregated",
    ):
        t0_df[c] = ""
    t0_df["in_conflict"] = False
    print(f"T0 rows: {len(t0_df):,}")

    cols = list(df.columns)
    t0_df = t0_df[cols]

    t3 = time.time()
    full = pd.concat([df, t0_df], ignore_index=True)
    full = full.sort_values(["year", "initiator", "target", "uiw_tier"], kind="stable").reset_index(drop=True)
    print(f"Concatenated: {len(full):,} rows in {time.time()-t3:.1f}s")

    t4 = time.time()
    full.to_csv(OUT_CSV, index=False)
    size_mb = os.path.getsize(OUT_CSV) / 1e6
    print(f"Wrote {OUT_CSV} ({size_mb:.1f} MB) in {time.time()-t4:.1f}s")

    try:
        import pyarrow  # noqa: F401
        t5 = time.time()
        full.to_parquet(OUT_PARQUET, index=False)
        print(f"Wrote {OUT_PARQUET} ({os.path.getsize(OUT_PARQUET)/1e6:.1f} MB) in {time.time()-t5:.1f}s")
    except Exception as e:
        print(f"Parquet write skipped: {e}")

    t6 = time.time()
    by_year = full.groupby(["year", "tier_label"]).size().unstack(fill_value=0)
    tier_cols = [
        "T0-No Conflict/Peace",
        "T1-Diplomatic Crisis",
        "T2-Economic/Display",
        "T3-Proxy/Indirect Military",
        "T4-Limited Military",
        "T5-Strategic War",
    ]
    for c in tier_cols:
        if c not in by_year.columns:
            by_year[c] = 0
    by_year = by_year[tier_cols]
    by_year["total"] = by_year[tier_cols].sum(axis=1)
    by_year["conflict_share"] = 1 - by_year["T0-No Conflict/Peace"] / by_year["total"]
    by_year.to_csv(STATS)
    print(f"Wrote {STATS} in {time.time()-t6:.1f}s")
    print("\nPer-year tier coverage (head 5 / tail 5):")
    print(pd.concat([by_year.head(5), by_year.tail(5)]).to_string())

    print(f"\nTotal runtime: {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
