"""Build the v27.0 features grid for TIERS.

Extends `data/processed/dyads_with_features.parquet` (the directed dyad-year
grid of existing states, with V-Dem / NMC / ATOP features attached) with the
v27.0 structural inputs:

  contiguity_xi          in {0, 0.5, 1}      from CShapes (build_contiguity.py)
  distance_km            great-circle km     from CShapes
  fma                    First-Mover Adv.    from CShapes distance
  rivalry_omega          initiator's rivalry toward the target, from MID
  rivalry_omega_b        target's rivalry toward the initiator
  conflict_history       shared decayed history   (all three: build_rivalry.py)
  closing_window_a       -W_dot_{A->B}       from rolling CINC growth
  closing_window_b       -W_dot_{B->A}
  cap_a_to_b             Cap_{A->B}          composite (Xi, CINC, distance)
  cap_b_to_a             Cap_{B->A}
  trade_*                v28 economic        from trade_interdependence if built
                          interdependence

`attribution` and `d_k_years` already come from the state table
(build_dyad_states.py). Geography and trade join on Gleditsch-Ward numbers;
NMC growth and rivalry join on Correlates of War codes.

Reads:
  data/processed/dyads_with_features.parquet
  data/processed/contiguity_xi.csv
  data/processed/rivalry_omega.csv
  data/processed/trade_interdependence.parquet or .csv (optional)
  data/raw/NMC-70-abridged.csv   (for CINC rolling growth)

Writes:
  data/processed/dyads_with_features_v27.parquet
"""
from __future__ import annotations

import os
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
    """Load the base feature grid written by `build_features.py`."""
    pq = os.path.join(DATA_PROCESSED, "dyads_with_features.parquet")
    df = pd.read_parquet(pq)
    df = df[(df.year >= YEAR_LO) & (df.year <= YEAR_HI)].copy()
    for c in ("initiator_gwno", "target_gwno", "initiator_ccode", "target_ccode"):
        df[c] = df[c].astype(np.int64)
    # One row per directed dyad-year is a contract of the state table, not
    # something to repair here.
    if df.duplicated(subset=["year", "initiator_ccode", "target_ccode"]).any():
        raise ValueError("base grid has duplicate directed dyad-years")
    return df


def load_contiguity() -> pd.DataFrame:
    path = os.path.join(DATA_PROCESSED, "contiguity_xi.csv")
    return pd.read_csv(path)


RIVALRY_COLUMNS = ["rivalry_omega", "rivalry_omega_b", "conflict_history"]


def load_rivalry() -> pd.DataFrame:
    """Directed rivalry keyed on COW codes (`build_rivalry.py`). The table is
    sparse: a pair with no militarised history has no row."""
    path = os.path.join(DATA_PROCESSED, "rivalry_omega.csv")
    riv = pd.read_csv(path)
    missing = [c for c in ["year", "initiator_ccode", "target_ccode"] + RIVALRY_COLUMNS if c not in riv.columns]
    if missing:
        raise ValueError(f"rivalry_omega.csv is from an older build (missing {missing}); run build_rivalry.py")
    return riv


def load_trade_interdependence() -> pd.DataFrame:
    """Load the shared v28 trade source of truth if it has been built."""
    pq = os.path.join(DATA_PROCESSED, "trade_interdependence.parquet")
    csv = os.path.join(DATA_PROCESSED, "trade_interdependence.csv")
    if os.path.exists(pq):
        return pd.read_parquet(pq)
    if os.path.exists(csv):
        return pd.read_csv(csv)
    return pd.DataFrame(columns=["year", "initiator_gwno", "target_gwno"])


def compute_closing_windows(grid: pd.DataFrame) -> pd.DataFrame:
    """For each directed pair, compute the rolling 5-year CINC growth of A
    relative to B. The closing window -W_dot is positive when A's CINC share
    is growing relative to B's (i.e. A perceives an opening).

    Returns per-row -W_dot_{A->B} (closing_window_a) and -W_dot_{B->A}
    (closing_window_b) clipped to [0, 1].
    """
    nmc_path = os.path.join(DATA_RAW, "NMC-70-abridged.csv")
    if not os.path.exists(nmc_path):
        return pd.DataFrame(columns=["year", "initiator_ccode", "target_ccode",
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

    # Join per (initiator, year) and (target, year). NMC is keyed on COW codes.
    out = grid[["year", "initiator_ccode", "target_ccode"]].copy()
    out = out.merge(
        nmc[["ccode", "year", "growth_norm"]].rename(
            columns={"ccode": "initiator_ccode", "growth_norm": "growth_a"}
        ),
        on=["initiator_ccode", "year"], how="left",
    )
    out = out.merge(
        nmc[["ccode", "year", "growth_norm"]].rename(
            columns={"ccode": "target_ccode", "growth_norm": "growth_b"}
        ),
        on=["target_ccode", "year"], how="left",
    )
    out["growth_a"] = out["growth_a"].fillna(0.5)
    out["growth_b"] = out["growth_b"].fillna(0.5)
    out["closing_window_a"] = np.clip(out["growth_a"] - out["growth_b"] + 0.5, 0.0, 1.0)
    out["closing_window_b"] = np.clip(out["growth_b"] - out["growth_a"] + 0.5, 0.0, 1.0)
    return out[["year", "initiator_ccode", "target_ccode",
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

    print("Loading base grid (dyads_with_features)...")
    base = load_base_grid()
    print(f"  {len(base):,} rows; years {base.year.min()}-{base.year.max()}")

    print("Loading contiguity...")
    con = load_contiguity()
    print(f"  {len(con):,} rows")

    print("Loading rivalry...")
    riv = load_rivalry()
    print(f"  {len(riv):,} rows")

    print("Loading trade interdependence (optional)...")
    trade = load_trade_interdependence()
    print(f"  {len(trade):,} rows")

    print("Computing closing windows from NMC...")
    cw = compute_closing_windows(base)
    print(f"  {len(cw):,} rows")

    print("Computing Capability/Reach...")
    cap = compute_cap(base)
    print(f"  {len(cap):,} rows")

    gw_key = ["year", "initiator_gwno", "target_gwno"]
    cow_key = ["year", "initiator_ccode", "target_ccode"]
    print("Joining into v27 grid...")
    grid = base.merge(cap, on=gw_key, how="left")
    grid = grid.merge(cw, on=cow_key, how="left")
    grid = grid.merge(riv, on=cow_key, how="left")
    if len(trade):
        grid = grid.merge(trade, on=gw_key, how="left")
    if len(grid) != len(base) or grid.duplicated(subset=cow_key).any():
        raise ValueError("a feature join changed the number of directed dyad-years")

    # Record what was observed before filling defaults. `attribution` and
    # `d_k_years` already come from the state table.
    grid["geography_observed"] = grid["distance_km"].notna()
    # Rivalry is observed for every member pair (MID covers the whole window);
    # a missing row means no militarised history, which is a true zero.
    grid["rivalry_observed"] = True
    print(f"  geography observed on {grid['geography_observed'].mean():.1%} of rows")
    print(f"  rivalry history present on {grid['rivalry_omega'].notna().mean():.1%} of rows")

    grid["contiguity_xi"] = grid["contiguity_xi"].fillna(0.0)
    grid["distance_km"] = grid["distance_km"].fillna(10000.0)
    grid["fma"] = grid["fma"].fillna(0.0)
    for c in RIVALRY_COLUMNS:
        grid[c] = grid[c].fillna(0.0)
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
    grid["uiw_tier"] = grid["uiw_tier"].astype(int)

    print(f"\nFinal grid: {len(grid):,} rows, {len(grid.columns)} columns")
    grid.to_parquet(out_pq, index=False)
    print(f"Wrote {out_pq}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
