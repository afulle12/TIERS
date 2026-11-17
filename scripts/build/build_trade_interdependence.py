"""Build the TIERS trade-interdependence source of truth.

Normalizes CEPII BACI and TRADHIST to the model key:

    year, initiator_gwno, target_gwno

Outputs one directed dyad-year row with bilateral trade flows and v28-ready
economic-interdependence variables. BACI is preferred in overlap years because
it is reconciled, product-level, and current; TRADHIST fills historical years.

Reads:
  data/raw/BACI_HS92_V202601.zip
  data/raw/TRADHIST_v4.dta
  data/processed/country_code_crosswalk.csv (built on demand)

Both directions of a pair are always written, from the same source, so the
fields the model treats as shared by the dyad agree across them.

Writes:
  data/processed/trade_interdependence.parquet
  data/processed/trade_interdependence.csv (only with --csv)
"""
from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from scripts.build.trade_country_crosswalk import load_crosswalk
except ModuleNotFoundError:  # Allow direct execution from scripts/build/.
    from trade_country_crosswalk import load_crosswalk


ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

BACI_ZIP = DATA_RAW / "BACI_HS92_V202601.zip"
TRADHIST_DTA = DATA_RAW / "TRADHIST_v4.dta"
OUT_BASE = DATA_PROCESSED / "trade_interdependence"

BACI_SOURCE_RANK = 0
TRADHIST_SOURCE_RANK = 1


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--year-min", type=int, default=1827)
    p.add_argument("--year-max", type=int, default=2024)
    p.add_argument("--source", choices=["all", "baci", "tradhist"], default="all")
    p.add_argument("--csv", action="store_true", help="Also write a CSV copy (about 600 MB)")
    p.add_argument("--force-crosswalk", action="store_true")
    return p.parse_args()


def _source_map(crosswalk: pd.DataFrame, source: str) -> dict[object, int]:
    cw = crosswalk[(crosswalk["source"] == source) & crosswalk["gwno"].notna()].copy()
    cw["gwno"] = cw["gwno"].astype(int)
    if source == "BACI":
        cw["source_code"] = cw["source_code"].astype(int)
    else:
        cw["source_code"] = cw["source_code"].astype(str).str.strip().str.upper()
    return dict(zip(cw["source_code"], cw["gwno"], strict=True))


def _year_from_baci_name(name: str) -> int | None:
    m = re.search(r"_Y(\d{4})_", name)
    return int(m.group(1)) if m else None


def load_baci(year_min: int, year_max: int, crosswalk: pd.DataFrame) -> pd.DataFrame:
    if not BACI_ZIP.exists():
        print(f"[WARN] BACI not found: {BACI_ZIP}")
        return pd.DataFrame()
    code_to_gw = _source_map(crosswalk, "BACI")
    frames: list[pd.DataFrame] = []
    with zipfile.ZipFile(BACI_ZIP) as zf:
        names = sorted(
            n for n in zf.namelist()
            if n.startswith("BACI_HS92_Y") and n.endswith(".csv")
        )
        for name in names:
            year = _year_from_baci_name(name)
            if year is None or year < year_min or year > year_max:
                continue
            print(f"  BACI {year}...")
            with zf.open(name) as fh:
                df = pd.read_csv(fh, usecols=["t", "i", "j", "v"])
            df["initiator_gwno"] = df["i"].map(code_to_gw)
            df["target_gwno"] = df["j"].map(code_to_gw)
            df = df.dropna(subset=["initiator_gwno", "target_gwno"])
            df["initiator_gwno"] = df["initiator_gwno"].astype(int)
            df["target_gwno"] = df["target_gwno"].astype(int)
            df = df[df["initiator_gwno"] != df["target_gwno"]]
            agg = (
                df.groupby(["t", "initiator_gwno", "target_gwno"], as_index=False)["v"]
                .sum()
                .rename(columns={"t": "year", "v": "exports_a_to_b"})
            )
            frames.append(agg)
    if not frames:
        return pd.DataFrame()
    flow = pd.concat(frames, ignore_index=True)
    return _complete_trade_frame(flow, "BACI", "thousand_current_usd", BACI_SOURCE_RANK)


def load_tradhist(year_min: int, year_max: int, crosswalk: pd.DataFrame) -> pd.DataFrame:
    if not TRADHIST_DTA.exists():
        print(f"[WARN] TRADHIST not found: {TRADHIST_DTA}")
        return pd.DataFrame()
    code_to_gw = _source_map(crosswalk, "TRADHIST")
    chunks: list[pd.DataFrame] = []
    cols = ["iso_o", "iso_d", "year", "FLOW", "XPTOT_o", "IPTOT_o", "XPTOT_d", "IPTOT_d"]
    print("  TRADHIST chunks...")
    for chunk in pd.read_stata(TRADHIST_DTA, columns=cols, chunksize=250_000):
        chunk = chunk[(chunk["year"] >= year_min) & (chunk["year"] <= year_max)].copy()
        if chunk.empty:
            continue
        chunk["initiator_gwno"] = chunk["iso_o"].astype(str).str.strip().str.upper().map(code_to_gw)
        chunk["target_gwno"] = chunk["iso_d"].astype(str).str.strip().str.upper().map(code_to_gw)
        chunk = chunk.dropna(subset=["initiator_gwno", "target_gwno"])
        chunk = chunk[chunk["FLOW"].notna()]
        chunk["initiator_gwno"] = chunk["initiator_gwno"].astype(int)
        chunk["target_gwno"] = chunk["target_gwno"].astype(int)
        chunk = chunk[chunk["initiator_gwno"] != chunk["target_gwno"]]
        if chunk.empty:
            continue
        chunks.append(
            chunk[[
                "year", "initiator_gwno", "target_gwno", "FLOW",
                "XPTOT_o", "IPTOT_o", "XPTOT_d", "IPTOT_d",
            ]]
        )
    if not chunks:
        return pd.DataFrame()
    df = pd.concat(chunks, ignore_index=True)
    flow = (
        df.groupby(["year", "initiator_gwno", "target_gwno"], as_index=False)
        .agg(
            exports_a_to_b=("FLOW", "sum"),
            total_exports_a=("XPTOT_o", "max"),
            total_imports_a=("IPTOT_o", "max"),
            total_exports_b=("XPTOT_d", "max"),
            total_imports_b=("IPTOT_d", "max"),
        )
    )
    return _complete_trade_frame(
        flow,
        "TRADHIST",
        "nominal_gbp_sterling",
        TRADHIST_SOURCE_RANK,
        has_totals=True,
    )


def _complete_pairs(flow: pd.DataFrame) -> pd.DataFrame:
    """Return one row per direction for every pair that reports a flow either way.

    A pair with exports in one direction only still gets both directed rows;
    the unreported direction has zero exports. Without this the two
    directions of a dyad disagree on whether trade was observed at all.
    """
    key = ["year", "initiator_gwno", "target_gwno"]
    fwd = flow[key + ["exports_a_to_b"]]
    rev = fwd.rename(columns={
        "initiator_gwno": "target_gwno",
        "target_gwno": "initiator_gwno",
        "exports_a_to_b": "exports_b_to_a",
    })
    out = fwd.merge(rev, on=key, how="outer")
    out["exports_a_to_b"] = out["exports_a_to_b"].fillna(0.0)
    out["exports_b_to_a"] = out["exports_b_to_a"].fillna(0.0)
    return out


def _country_totals(flow: pd.DataFrame, has_totals: bool) -> pd.DataFrame:
    """One row of total exports and imports per country-year.

    Each country gets a single pair of totals, used wherever it appears, so a
    dependence share is the same whichever direction of the dyad reads it.
    """
    if has_totals:
        as_origin = flow.rename(columns={
            "initiator_gwno": "gwno", "total_exports_a": "total_exports", "total_imports_a": "total_imports",
        })[["year", "gwno", "total_exports", "total_imports"]]
        as_dest = flow.rename(columns={
            "target_gwno": "gwno", "total_exports_b": "total_exports", "total_imports_b": "total_imports",
        })[["year", "gwno", "total_exports", "total_imports"]]
        both = pd.concat([as_origin, as_dest], ignore_index=True)
        for col in ("total_exports", "total_imports"):
            both[col] = pd.to_numeric(both[col], errors="coerce")
        return both.groupby(["year", "gwno"], as_index=False)[["total_exports", "total_imports"]].max().fillna(0.0)
    exp_totals = (
        flow.groupby(["year", "initiator_gwno"], as_index=False)["exports_a_to_b"].sum()
        .rename(columns={"initiator_gwno": "gwno", "exports_a_to_b": "total_exports"})
    )
    imp_totals = (
        flow.groupby(["year", "target_gwno"], as_index=False)["exports_a_to_b"].sum()
        .rename(columns={"target_gwno": "gwno", "exports_a_to_b": "total_imports"})
    )
    return exp_totals.merge(imp_totals, on=["year", "gwno"], how="outer").fillna(0.0)


def _complete_trade_frame(
    flow: pd.DataFrame,
    source: str,
    value_unit: str,
    source_rank: int,
    has_totals: bool = False,
) -> pd.DataFrame:
    """Attach reverse flows, totals, and directed dependence variables.

    The output has both directions of every pair, and every field that the
    model treats as shared by the dyad (`trade_surface_ab`,
    `mutual_trade_dependence_ab`, `trade_shock_ab`) is equal across them.
    """
    flow = flow.copy()
    flow["year"] = flow["year"].astype(int)
    flow["initiator_gwno"] = flow["initiator_gwno"].astype(int)
    flow["target_gwno"] = flow["target_gwno"].astype(int)
    flow["exports_a_to_b"] = pd.to_numeric(flow["exports_a_to_b"], errors="coerce").fillna(0.0)

    out = _complete_pairs(flow)
    totals = _country_totals(flow, has_totals)
    out = out.merge(
        totals.rename(columns={
            "gwno": "initiator_gwno", "total_exports": "total_exports_a", "total_imports": "total_imports_a",
        }),
        on=["year", "initiator_gwno"], how="left",
    ).merge(
        totals.rename(columns={
            "gwno": "target_gwno", "total_exports": "total_exports_b", "total_imports": "total_imports_b",
        }),
        on=["year", "target_gwno"], how="left",
    )

    for col in ["total_exports_a", "total_imports_a", "total_exports_b", "total_imports_b"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    out["total_trade_a"] = out["total_exports_a"] + out["total_imports_a"]
    out["total_trade_b"] = out["total_exports_b"] + out["total_imports_b"]
    out["imports_a_from_b"] = out["exports_b_to_a"]
    out["imports_b_from_a"] = out["exports_a_to_b"]

    out["dep_a_on_b"] = _safe_div(out["exports_a_to_b"] + out["imports_a_from_b"], out["total_trade_a"])
    out["dep_b_on_a"] = _safe_div(out["exports_b_to_a"] + out["imports_b_from_a"], out["total_trade_b"])
    out["import_dep_a_on_b"] = _safe_div(out["imports_a_from_b"], out["total_imports_a"])
    out["import_dep_b_on_a"] = _safe_div(out["imports_b_from_a"], out["total_imports_b"])
    out["export_dep_a_on_b"] = _safe_div(out["exports_a_to_b"], out["total_exports_a"])
    out["export_dep_b_on_a"] = _safe_div(out["exports_b_to_a"], out["total_exports_b"])

    out["mutual_trade_dependence_ab"] = np.minimum(out["dep_a_on_b"], out["dep_b_on_a"])
    out["import_leverage_a_over_b"] = (out["import_dep_b_on_a"] - out["import_dep_a_on_b"]).clip(lower=0.0)
    out["export_leverage_a_over_b"] = (out["export_dep_b_on_a"] - out["export_dep_a_on_b"]).clip(lower=0.0)
    out["trade_leverage_a_over_b"] = np.maximum(
        out["import_leverage_a_over_b"], out["export_leverage_a_over_b"]
    )
    out["trade_vulnerability_b_to_a"] = out["dep_b_on_a"]
    out["trade_surface_ab"] = np.log1p(out["exports_a_to_b"] + out["exports_b_to_a"])
    out = out.sort_values(["initiator_gwno", "target_gwno", "year"]).reset_index(drop=True)
    out["trade_shock_ab"] = out.groupby(["initiator_gwno", "target_gwno"])["trade_surface_ab"].diff().fillna(0.0)
    out["trade_source"] = source
    out["trade_value_unit"] = value_unit
    out["source_rank"] = source_rank
    return out


def _safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    den = den.replace({0.0: np.nan})
    return (num / den).replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(lower=0.0)


def combine_sources(frames: list[pd.DataFrame]) -> pd.DataFrame:
    frames = [f for f in frames if not f.empty]
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    # Choose the source per pair-year, not per direction: where a pair appears
    # in both sources, both of its directed rows come from the preferred one.
    lo = np.minimum(out["initiator_gwno"], out["target_gwno"])
    hi = np.maximum(out["initiator_gwno"], out["target_gwno"])
    best = out.groupby([out["year"], lo, hi])["source_rank"].transform("min")
    out = out[out["source_rank"] == best]
    out = out.sort_values(["year", "initiator_gwno", "target_gwno"])
    if out.duplicated(["year", "initiator_gwno", "target_gwno"]).any():
        raise ValueError("trade: duplicate directed dyad-year after combining sources")
    out["trade_surface_norm_ab"] = out.groupby("year")["trade_surface_ab"].rank(pct=True)
    out = out.drop(columns=["source_rank"])

    order = [
        "year", "initiator_gwno", "target_gwno", "trade_source", "trade_value_unit",
        "exports_a_to_b", "exports_b_to_a", "imports_a_from_b", "imports_b_from_a",
        "total_exports_a", "total_imports_a", "total_trade_a",
        "total_exports_b", "total_imports_b", "total_trade_b",
        "trade_surface_ab", "trade_surface_norm_ab",
        "dep_a_on_b", "dep_b_on_a", "mutual_trade_dependence_ab",
        "import_dep_a_on_b", "import_dep_b_on_a", "import_leverage_a_over_b",
        "export_dep_a_on_b", "export_dep_b_on_a", "export_leverage_a_over_b",
        "trade_leverage_a_over_b", "trade_vulnerability_b_to_a", "trade_shock_ab",
    ]
    return out[order].sort_values(["year", "initiator_gwno", "target_gwno"]).reset_index(drop=True)


def main() -> int:
    args = _parse_args()
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    print("Loading/building country-code crosswalk...")
    crosswalk = load_crosswalk(force=args.force_crosswalk)

    frames: list[pd.DataFrame] = []
    if args.source in {"all", "tradhist"}:
        frames.append(load_tradhist(args.year_min, args.year_max, crosswalk))
    if args.source in {"all", "baci"}:
        frames.append(load_baci(args.year_min, args.year_max, crosswalk))

    out = combine_sources(frames)
    if out.empty:
        print("[WARN] No trade rows produced")
        return 1

    pq_path = OUT_BASE.with_suffix(".parquet")
    out.to_parquet(pq_path, index=False)
    print(f"Wrote {pq_path} ({len(out):,} directed dyad-years)")
    csv_path = OUT_BASE.with_suffix(".csv")
    if args.csv:
        out.to_csv(csv_path, index=False)
        print(f"Wrote {csv_path}")
    elif csv_path.exists():
        print(f"[NOTE] {csv_path} is from an earlier build and was not rewritten; "
              "the feature builders read the Parquet file.")

    print("Rows by source:")
    for source, count in out["trade_source"].value_counts().sort_index().items():
        print(f"  {source}: {count:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
