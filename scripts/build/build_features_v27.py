"""Build the v27.0 features grid for TIERS.

Extends `data/processed/dyads_with_features.csv` (the existing T0-T5 directed
dyad-year grid with V-Dem / NMC / ATOP features attached) with the v27.0
structural inputs:

  contiguity_xi          in {0, 0.5, 1}      from CShapes (build_contiguity.py)
  distance_km            great-circle km     from CShapes
  fma                    First-Mover Adv.    from CShapes distance
  rivalry_omega          recency-decayed     from MIDB  (build_rivalry.py)
  d_k_years              years at current tier (computed from tier_transitions_full)
  closing_window_a       -W_dot_{A->B}       from rolling CINC growth
  closing_window_b       -W_dot_{B->A}
  cap_a_to_b             Cap_{A->B}          composite (Xi, CINC, distance)
  cap_b_to_a             Cap_{B->A}
  attribution            modifier            from conflict_dyads_full (T3 only;
                                                  0 for non-T3; 0.5 default)
  trade_*                v28 economic        from trade_interdependence if built
                          interdependence

Reads:
  data/processed/dyads_with_features.csv
  data/processed/contiguity_xi.csv
  data/processed/rivalry_omega.csv
  data/processed/trade_interdependence.csv or .parquet (optional)
  data/processed/conflict_dyads_full.csv
  data/raw/NMC-70-abridged.csv   (for CINC rolling growth)
  output/analysis/tier_transitions_full.csv   (for D_k)

Writes:
  data/processed/dyads_with_features_v27.parquet
  data/processed/dyads_with_features_v27.csv   (fallback)
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")

YEAR_LO, YEAR_HI = 1946, 2014

# Capability/Reach composite (placeholder; calibration pending)
# Cap = clip(w_xi * Xi + w_cinc * (1 - c_t) + w_dist * exp(-d/d_scale), 0, 1)
CAP_W_XI = 0.40
CAP_W_CINC = 0.40
CAP_W_DIST = 0.20
CAP_D_SCALE_KM = 8000.0   # ~ half the Earth's circumference

# Closing-window window (years for rolling CINC growth)
CLOSING_WINDOW_YEARS = 5


def load_base_grid() -> pd.DataFrame:
    """Load the existing v21 dyads_with_features grid."""
    pq = os.path.join(DATA_PROCESSED, "dyads_with_features.parquet")
    csv = os.path.join(DATA_PROCESSED, "dyads_with_features.csv")
    if os.path.exists(pq):
        df = pd.read_parquet(pq)
    else:
        df = pd.read_csv(csv, dtype={"year": int})
    df = df[(df.year >= YEAR_LO) & (df.year <= YEAR_HI)].copy()
    df["initiator_gwno"] = df["initiator_gwno"].astype(np.int64)
    df["target_gwno"] = df["target_gwno"].astype(np.int64)
    # Dedupe on (year, i, j): the base grid has 273k duplicate rows in
    # the 1946-2014 window (likely from EUSANCT/MIDB reconciliation).
    df = df.drop_duplicates(subset=["year", "initiator_gwno", "target_gwno"], keep="first")
    return df


def load_contiguity() -> pd.DataFrame:
    path = os.path.join(DATA_PROCESSED, "contiguity_xi.csv")
    return pd.read_csv(path)


def load_rivalry() -> pd.DataFrame:
    path = os.path.join(DATA_PROCESSED, "rivalry_omega.csv")
    return pd.read_csv(path)


def load_trade_interdependence() -> pd.DataFrame:
    """Load the shared v28 trade source of truth if it has been built."""
    pq = os.path.join(DATA_PROCESSED, "trade_interdependence.parquet")
    csv = os.path.join(DATA_PROCESSED, "trade_interdependence.csv")
    if os.path.exists(pq):
        return pd.read_parquet(pq)
    if os.path.exists(csv):
        return pd.read_csv(csv)
    return pd.DataFrame(columns=["year", "initiator_gwno", "target_gwno"])


def load_attribution() -> pd.DataFrame:
    """From conflict_dyads_full: per-row attribution, plus 0 for non-T3 rows."""
    path = os.path.join(DATA_PROCESSED, "conflict_dyads_full.csv")
    cf = pd.read_csv(
        path,
        usecols=["year", "initiator_gwno", "target_gwno", "uiw_tier", "attribution"],
    )
    cf = cf.dropna(subset=["initiator_gwno", "target_gwno"])
    cf["initiator_gwno"] = cf["initiator_gwno"].astype(np.int64)
    cf["target_gwno"] = cf["target_gwno"].astype(np.int64)
    cf["attribution"] = cf["attribution"].fillna(0.0)
    # For non-T3 rows, attribution is set to 0 (the modifier is inactive).
    cf.loc[cf["uiw_tier"] != 3, "attribution"] = 0.0
    # Dedupe: for each (year, i, j) keep the maximum attribution
    # (the active T3 modifier, if any).
    cf = cf.sort_values(["year", "initiator_gwno", "target_gwno", "attribution"])
    cf = cf.drop_duplicates(
        subset=["year", "initiator_gwno", "target_gwno"], keep="last"
    )
    return cf[["year", "initiator_gwno", "target_gwno", "attribution"]]


def compute_dk(grid: pd.DataFrame) -> pd.DataFrame:
    """Compute D_k (years at current tier) per (i, j, year).

    For each directed pair, walk the sorted tier history and expand each
    (y_from, y_to) interval into per-year rows. For each (y, run), the
    d_k is (y - run_start_year). Runs are sequences of consecutive rows
    where t_from is constant within the pair.
    """
    path = os.path.join(OUT_ANALYSIS, "tier_transitions_full.csv")
    tt = pd.read_csv(path)
    tt = tt[(tt.y_from >= YEAR_LO) & (tt.y_from <= YEAR_HI)]

    cf_path = os.path.join(DATA_PROCESSED, "conflict_dyads_full.csv")
    cf = pd.read_csv(cf_path, usecols=["initiator", "target", "initiator_gwno", "target_gwno"])
    cf = cf.dropna(subset=["initiator_gwno", "target_gwno"])
    cf["initiator_gwno"] = cf["initiator_gwno"].astype(int)
    cf["target_gwno"] = cf["target_gwno"].astype(int)
    name_to_gw_i = dict(zip(cf["initiator"], cf["initiator_gwno"]))
    name_to_gw_t = dict(zip(cf["target"], cf["target_gwno"]))
    tt = tt[tt.initiator.isin(name_to_gw_i) & tt.target.isin(name_to_gw_t)].copy()
    tt["initiator_gwno"] = tt["initiator"].map(name_to_gw_i).astype(int)
    tt["target_gwno"] = tt["target"].map(name_to_gw_t).astype(int)
    tt = tt.sort_values(["initiator_gwno", "target_gwno", "y_from"]).reset_index(drop=True)

    # A "run" starts when t_from differs from the previous row's t_from
    # within the (i, j) group, or on the very first row of a group.
    tt["t_from"] = tt["t_from"].astype(int)
    tt["t_from_prev"] = tt.groupby(["initiator_gwno", "target_gwno"])["t_from"].shift(1)
    is_new_run = (tt["t_from"] != tt["t_from_prev"]).fillna(True)
    tt["run_id"] = is_new_run.groupby([tt["initiator_gwno"], tt["target_gwno"]]).cumsum().astype(int)
    run_starts = (
        tt.groupby(["initiator_gwno", "target_gwno", "run_id"])["y_from"].first().reset_index()
    )
    run_starts = run_starts.rename(columns={"y_from": "run_start_year"})
    tt = tt.merge(run_starts, on=["initiator_gwno", "target_gwno", "run_id"], how="left")

    # Clip y_to to YEAR_HI for expansion
    tt["y_to_clip"] = tt["y_to"].fillna(YEAR_HI).clip(upper=YEAR_HI).astype(int)
    tt["y_from_i"] = tt["y_from"].astype(int)

    # Expand intervals row-wise using a fast repeat. Each row repeats
    # (y_to_clip - y_from_i + 1) times, then we add the offset.
    span = (tt["y_to_clip"] - tt["y_from_i"] + 1).clip(lower=0)
    # Filter out zero-span rows (shouldn't happen but be safe)
    valid = span > 0
    tt = tt.loc[valid].copy()
    span = span.loc[valid]

    expanded_idx = tt.index.repeat(span).to_numpy()
    expanded_offset = np.arange(span.sum()) - np.repeat(span.cumsum() - span, span)
    expanded_year = tt.loc[expanded_idx, "y_from_i"].to_numpy() + expanded_offset
    expanded_gw_i = tt.loc[expanded_idx, "initiator_gwno"].to_numpy()
    expanded_gw_t = tt.loc[expanded_idx, "target_gwno"].to_numpy()
    expanded_run = tt.loc[expanded_idx, "run_start_year"].to_numpy()

    out = pd.DataFrame({
        "year": expanded_year.astype(int),
        "initiator_gwno": expanded_gw_i.astype(int),
        "target_gwno": expanded_gw_t.astype(int),
        "d_k_years": (expanded_year - expanded_run).astype(float),
    })
    # Window clip
    out = out[(out.year >= YEAR_LO) & (out.year <= YEAR_HI)]
    # Dedupe: if a (year, i, j) appears in multiple runs (overlapping intervals
    # in tier_transitions_full), take the smallest d_k_years (the most recent
    # run start gives the smallest duration at the current tier).
    out = out.sort_values(["year", "initiator_gwno", "target_gwno", "d_k_years"])
    out = out.drop_duplicates(subset=["year", "initiator_gwno", "target_gwno"], keep="first")
    out["initiator_gwno"] = out["initiator_gwno"].astype(np.int64)
    out["target_gwno"] = out["target_gwno"].astype(np.int64)
    return out


def compute_closing_windows(grid: pd.DataFrame) -> pd.DataFrame:
    """For each directed pair, compute the rolling 5-year CINC growth of A
    relative to B. The closing window -W_dot is positive when A's CINC share
    is growing relative to B's (i.e. A perceives an opening).

    Returns per-row -W_dot_{A->B} (closing_window_a) and -W_dot_{B->A}
    (closing_window_b) clipped to [0, 1].
    """
    nmc_path = os.path.join(DATA_RAW, "NMC-70-abridged.csv")
    if not os.path.exists(nmc_path):
        return pd.DataFrame(columns=["year", "initiator_gwno", "target_gwno",
                                       "closing_window_a", "closing_window_b"])
    nmc = pd.read_csv(nmc_path, usecols=["ccode", "year", "cinc"])
    nmc = nmc.dropna(subset=["ccode", "cinc"])
    nmc["ccode"] = nmc["ccode"].astype(int)
    nmc["year"] = nmc["year"].astype(int)
    nmc = nmc[(nmc.year >= YEAR_LO - CLOSING_WINDOW_YEARS) & (nmc.year <= YEAR_HI)]

    # Pivot to (ccode, year) -> cinc, then compute 5-year rolling delta.
    nmc = nmc.sort_values(["ccode", "year"])
    nmc["cinc_lag5"] = nmc.groupby("ccode")["cinc"].shift(CLOSING_WINDOW_YEARS)
    nmc["delta_cinc_5y"] = (nmc["cinc"] - nmc["cinc_lag5"]).fillna(0.0)
    # Normalise to [0, 1] by tanh of the delta (units are CINC share, ~0-1).
    nmc["growth_norm"] = np.tanh(nmc["delta_cinc_5y"] * 50.0) * 0.5 + 0.5

    # Join per (initiator, year) and (target, year)
    out = grid[["year", "initiator_gwno", "target_gwno"]].copy()
    out = out.merge(
        nmc[["ccode", "year", "growth_norm"]].rename(
            columns={"ccode": "initiator_gwno", "growth_norm": "growth_a"}
        ),
        on=["initiator_gwno", "year"], how="left",
    )
    out = out.merge(
        nmc[["ccode", "year", "growth_norm"]].rename(
            columns={"ccode": "target_gwno", "growth_norm": "growth_b"}
        ),
        on=["target_gwno", "year"], how="left",
    )
    out["growth_a"] = out["growth_a"].fillna(0.5)
    out["growth_b"] = out["growth_b"].fillna(0.5)
    out["closing_window_a"] = np.clip(out["growth_a"] - out["growth_b"] + 0.5, 0.0, 1.0)
    out["closing_window_b"] = np.clip(out["growth_b"] - out["growth_a"] + 0.5, 0.0, 1.0)
    return out[["year", "initiator_gwno", "target_gwno",
                "closing_window_a", "closing_window_b"]]


def compute_cap(grid: pd.DataFrame) -> pd.DataFrame:
    """Capability/Reach Cap_{i->j} = clip(w_xi*Xi + w_cinc*(1-c_t_ij) +
    w_dist*exp(-d/d_scale), 0, 1).

    Where c_t_ij is A's CINC share of the dyad.
    """
    out = grid[["year", "initiator_gwno", "target_gwno",
                "c_t_ab", "c_t_ba"]].copy()
    con = load_contiguity()
    out = out.merge(con, on=["year", "initiator_gwno", "target_gwno"], how="left")
    out["contiguity_xi"] = out["contiguity_xi"].fillna(0.0)
    out["distance_km"] = out["distance_km"].fillna(10000.0)
    out["fma"] = out["fma"].fillna(0.0)
    # Cap_{A->B}: uses A's CINC share of dyad (c_t_ab) and contiguity from A's side
    # (Xi is symmetric so we just use it).
    out["cap_a_to_b"] = (
        CAP_W_XI * out["contiguity_xi"]
        + CAP_W_CINC * (1.0 - out["c_t_ab"])
        + CAP_W_DIST * np.exp(-out["distance_km"] / CAP_D_SCALE_KM)
    )
    out["cap_b_to_a"] = (
        CAP_W_XI * out["contiguity_xi"]
        + CAP_W_CINC * (1.0 - out["c_t_ba"])
        + CAP_W_DIST * np.exp(-out["distance_km"] / CAP_D_SCALE_KM)
    )
    out["cap_a_to_b"] = out["cap_a_to_b"].clip(0.0, 1.0)
    out["cap_b_to_a"] = out["cap_b_to_a"].clip(0.0, 1.0)
    return out[["year", "initiator_gwno", "target_gwno",
                "contiguity_xi", "distance_km", "fma",
                "cap_a_to_b", "cap_b_to_a"]]


def main() -> int:
    out_pq = os.path.join(DATA_PROCESSED, "dyads_with_features_v27.parquet")
    out_csv = os.path.join(DATA_PROCESSED, "dyads_with_features_v27.csv")
    if os.path.exists(out_pq):
        print(f"Already exists: {out_pq}")
        return 0

    print("Loading base grid (dyads_with_features)...")
    base = load_base_grid()
    print(f"  {len(base):,} rows; years {base.year.min()}-{base.year.max()}")

    print("Loading contiguity...")
    con = load_contiguity()
    print(f"  {len(con):,} rows")

    print("Loading rivalry...")
    riv = load_rivalry()
    print(f"  {len(riv):,} rows")

    print("Loading attribution...")
    attr = load_attribution()
    print(f"  {len(attr):,} rows")

    print("Loading trade interdependence (optional)...")
    trade = load_trade_interdependence()
    print(f"  {len(trade):,} rows")

    print("Computing D_k from tier_transitions_full...")
    dk = compute_dk(base)
    print(f"  {len(dk):,} rows")

    print("Computing closing windows from NMC...")
    cw = compute_closing_windows(base)
    print(f"  {len(cw):,} rows")

    print("Computing Capability/Reach...")
    cap = compute_cap(base)
    print(f"  {len(cap):,} rows")

    print("Joining into v27 grid...")
    grid = base.merge(cap, on=["year", "initiator_gwno", "target_gwno"], how="left")
    grid = grid.merge(cw, on=["year", "initiator_gwno", "target_gwno"], how="left")
    grid = grid.merge(riv, on=["year", "initiator_gwno", "target_gwno"], how="left")
    grid = grid.merge(attr, on=["year", "initiator_gwno", "target_gwno"], how="left")
    if len(trade):
        grid = grid.merge(trade, on=["year", "initiator_gwno", "target_gwno"], how="left")
    # dk includes a uiw_tier that would clash with the base grid's; drop it
    dk_to_merge = dk[["year", "initiator_gwno", "target_gwno", "d_k_years"]]
    grid = grid.merge(dk_to_merge, on=["year", "initiator_gwno", "target_gwno"], how="left")

    # Fill missing with documented defaults
    grid["contiguity_xi"] = grid["contiguity_xi"].fillna(0.0)
    grid["distance_km"] = grid["distance_km"].fillna(10000.0)
    grid["fma"] = grid["fma"].fillna(0.0)
    grid["rivalry_omega"] = grid["rivalry_omega"].fillna(0.0)
    grid["attribution"] = grid["attribution"].fillna(0.0)
    grid["cap_a_to_b"] = grid["cap_a_to_b"].fillna(0.0)
    grid["cap_b_to_a"] = grid["cap_b_to_a"].fillna(0.0)
    grid["closing_window_a"] = grid["closing_window_a"].fillna(0.5)
    grid["closing_window_b"] = grid["closing_window_b"].fillna(0.5)
    grid["d_k_years"] = grid["d_k_years"].fillna(0.0)
    for c in [
        "exports_a_to_b", "exports_b_to_a", "imports_a_from_b", "imports_b_from_a",
        "total_exports_a", "total_imports_a", "total_trade_a",
        "total_exports_b", "total_imports_b", "total_trade_b",
        "trade_surface_ab", "trade_surface_norm_ab",
        "dep_a_on_b", "dep_b_on_a", "mutual_trade_dependence_ab",
        "import_dep_a_on_b", "import_dep_b_on_a", "import_leverage_a_over_b",
        "export_dep_a_on_b", "export_dep_b_on_a", "export_leverage_a_over_b",
        "trade_leverage_a_over_b", "trade_vulnerability_b_to_a", "trade_shock_ab",
    ]:
        if c in grid.columns:
            grid[c] = grid[c].fillna(0.0)
    if "trade_source" in grid.columns:
        grid["trade_source"] = grid["trade_source"].fillna("NONE")
    if "trade_value_unit" in grid.columns:
        grid["trade_value_unit"] = grid["trade_value_unit"].fillna("none")

    # Cast back to int
    for c in ["initiator_gwno", "target_gwno", "uiw_tier_x", "uiw_tier_y"]:
        if c in grid.columns:
            grid = grid.drop(columns=[c])
    grid["uiw_tier"] = grid["uiw_tier"].astype("Int64")

    print(f"\nFinal grid: {len(grid):,} rows, {len(grid.columns)} columns")
    try:
        grid.to_parquet(out_pq, index=False)
        print(f"Wrote {out_pq}")
    except Exception as e:
        print(f"Parquet failed ({e}); falling back to CSV")
    grid.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv}")
    print()
    print("Column dtypes:")
    print(grid.dtypes.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
