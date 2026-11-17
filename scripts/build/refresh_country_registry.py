"""Refresh the country-name registry in data/processed/ to use the new naming
convention (natural English order, e.g. 'Democratic Republic of Vietnam' instead
of 'Vietnam, Democratic Republic of').

The rewriting rule is defined once in scripts/build/country_names.py and shared
by build_combined_dyads.py:
  - Strip 'Government of' prefix.
  - Strip trailing parenthetical.
  - Rewrite 'Country, X of' -> 'X of Country', preserving the parenthetical.
  - Collapse multiple spaces.
  - Apply CANONICAL_NAME_OVERRIDES (historical / common variants).

Files updated:
  - data/processed/conflict_tiers.csv        (country column)
  - data/processed/countries_by_year.csv    (countries column)
  - data/processed/conflict_dyads.csv       (initiator, target columns)
  - data/processed/conflict_dyads_midb_only.csv (initiator, target columns)
  - data/processed/conflict_dyads_eus.csv   (initiator, target columns)
  - data/processed/conflict_dyads_combined.csv (initiator, target columns)
  - data/processed/conflict_dyads_full.csv  (initiator, target columns;
    the .parquet companion is regenerated when pyarrow is available)

The script preserves all existing rows (including historical states that are
not in CShapes) and only changes the country-name columns.
"""
from __future__ import annotations

import csv
import os
import sys

import pandas as pd

from country_names import normalize_name

csv.field_size_limit(sys.maxsize)


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
TIERS_CSV = os.path.join(DATA_PROCESSED, "conflict_tiers.csv")
COUNTRIES_BY_YEAR_CSV = os.path.join(DATA_PROCESSED, "countries_by_year.csv")
DYADS_CSV = os.path.join(DATA_PROCESSED, "conflict_dyads.csv")
DYADS_MIDB_CSV = os.path.join(DATA_PROCESSED, "conflict_dyads_midb_only.csv")
DYADS_EUS_CSV = os.path.join(DATA_PROCESSED, "conflict_dyads_eus.csv")
DYADS_COMBINED_CSV = os.path.join(DATA_PROCESSED, "conflict_dyads_combined.csv")
DYADS_FULL_CSV = os.path.join(DATA_PROCESSED, "conflict_dyads_full.csv")
DYADS_FULL_PARQUET = os.path.join(DATA_PROCESSED, "conflict_dyads_full.parquet")


def refresh_conflict_tiers() -> None:
    rows = []
    with open(TIERS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["country"] = normalize_name(row["country"])
            rows.append(row)
    with open(TIERS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "country", "in_conflict", "hostlev", "uiw_tier", "tier_label"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Refreshed: {TIERS_CSV} ({len(rows)} rows)")


def refresh_countries_by_year() -> None:
    rows = []
    with open(COUNTRIES_BY_YEAR_CSV, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            year, country_str = row[0], row[1]
            countries = [normalize_name(c.strip()) for c in country_str.split(";") if c.strip()]
            countries_sorted = "; ".join(sorted(set(countries)))
            rows.append([year, countries_sorted])
    with open(COUNTRIES_BY_YEAR_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"Refreshed: {COUNTRIES_BY_YEAR_CSV} ({len(rows)} rows)")


def _refresh_dyads_csv(path: str) -> None:
    """Normalize the initiator/target columns of a directed-dyad CSV in place.

    The CSV is read with pandas, the two name columns are mapped through
    normalize_name, and the result is written back. All other columns are
    preserved exactly as-is.
    """
    df = pd.read_csv(path, dtype={"year": int})
    n0 = len(df)
    df["initiator"] = df["initiator"].map(normalize_name)
    df["target"] = df["target"].map(normalize_name)
    df.to_csv(path, index=False)
    print(f"Refreshed: {path} ({n0:,} rows)")


def refresh_conflict_dyads() -> None:
    _refresh_dyads_csv(DYADS_CSV)


def refresh_conflict_dyads_midb_only() -> None:
    _refresh_dyads_csv(DYADS_MIDB_CSV)


def refresh_conflict_dyads_eus() -> None:
    _refresh_dyads_csv(DYADS_EUS_CSV)


def refresh_conflict_dyads_combined() -> None:
    _refresh_dyads_csv(DYADS_COMBINED_CSV)


def refresh_conflict_dyads_full() -> None:
    _refresh_dyads_csv(DYADS_FULL_CSV)
    if os.path.exists(DYADS_FULL_PARQUET):
        try:
            import pyarrow  # noqa: F401
            df = pd.read_csv(DYADS_FULL_CSV, dtype={"year": int})
            df.to_parquet(DYADS_FULL_PARQUET, index=False)
            print(f"Refreshed: {DYADS_FULL_PARQUET}")
        except Exception as e:
            print(f"Parquet refresh skipped: {e}")


if __name__ == "__main__":
    refresh_conflict_tiers()
    refresh_countries_by_year()
    refresh_conflict_dyads()
    refresh_conflict_dyads_midb_only()
    refresh_conflict_dyads_eus()
    refresh_conflict_dyads_combined()
    refresh_conflict_dyads_full()
