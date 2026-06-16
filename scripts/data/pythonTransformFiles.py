"""
Transform a country CSV into: Year -> List of countries that exist in that year.
Filters to years >= 1900.

Expected CSV columns:
  - cntry_name : country name
  - gwsyear    : year the country record starts (inclusive)
  - gweyear    : year the country record ends   (inclusive)

Usage:
  python transform_countries.py input.csv
  python transform_countries.py input.csv --output result.csv
  python transform_countries.py input.csv --format json
"""

import csv
import sys
import json
import argparse
from collections import defaultdict

# The geometry columns in this CSV can be very large
csv.field_size_limit(sys.maxsize)

# Territories / historical sub-units rolled up into their parent country.
# Edit this map to add or change any merges.
NORMALIZE: dict[str, str] = {
    "Alaska":        "United States of America",
    "Hawaii":        "United States of America",
    "Puerto Rico":   "United States of America",
    "Newfoundland":  "Canada",
}


def normalize_name(name: str) -> str:
    """Return the canonical country name, merging territories into parents."""
    return NORMALIZE.get(name, name)


def load_countries(filepath: str) -> list[dict]:
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def build_year_map(rows: list[dict], min_year: int = 1900) -> dict[int, set[str]]:
    """
    For each row, mark the country as existing for every year in
    [gwsyear, gweyear], keeping only years >= min_year.
    Territory names are normalized to their parent country.
    """
    year_map: dict[int, set[str]] = defaultdict(set)

    for row in rows:
        try:
            start = int(row["gwsyear"])
            end   = int(row["gweyear"])
            name  = normalize_name(row["cntry_name"].strip())
        except (KeyError, ValueError):
            continue  # skip malformed rows

        for year in range(max(start, min_year), end + 1):
            year_map[year].add(name)

    return year_map


def write_csv(year_map: dict[int, set[str]], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "countries"])
        for year in sorted(year_map):
            countries = "; ".join(sorted(year_map[year]))
            writer.writerow([year, countries])
    print(f"CSV written to: {output_path}")


def write_json(year_map: dict[int, set[str]], output_path: str) -> None:
    data = {
        str(year): sorted(year_map[year])
        for year in sorted(year_map)
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"JSON written to: {output_path}")


def print_preview(year_map: dict[int, set[str]], n: int = 5) -> None:
    print(f"\nPreview (first {n} years):")
    for year in sorted(year_map)[:n]:
        countries = ", ".join(sorted(year_map[year]))
        print(f"  {year}: {countries[:120]}{'...' if len(countries) > 120 else ''}")


def main():
    parser = argparse.ArgumentParser(description="Map years to existing countries.")
    parser.add_argument("input",          help="Path to input CSV file")
    parser.add_argument("--output", "-o", help="Output file path (default: countries_by_year.csv in CWD)")
    parser.add_argument("--format", "-f", choices=["csv", "json"], default="csv",
                        help="Output format: csv (default) or json")
    parser.add_argument("--min-year",     type=int, default=1900,
                        help="Earliest year to include (default: 1900)")
    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        ext = ".json" if args.format == "json" else ".csv"
        output_path = "output" + ext

    print(f"Reading: {args.input}")
    rows = load_countries(args.input)
    print(f"  {len(rows)} rows loaded")

    year_map = build_year_map(rows, min_year=args.min_year)
    print(f"  {len(year_map)} years found (from {min(year_map)} to {max(year_map)})")

    print_preview(year_map)

    if args.format == "json":
        write_json(year_map, output_path)
    else:
        write_csv(year_map, output_path)


if __name__ == "__main__":
    main()