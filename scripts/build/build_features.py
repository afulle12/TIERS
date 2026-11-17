"""Attach external features to the directed dyad-year grid for model back-testing.

External data used (place in data/raw/):

  V-Dem-CY-Core-v16.csv
    V-Dem v16 Country-Year: V-Dem Core.
    Required columns: COWcode, year, v2x_polyarchy

  NMC-70-abridged.csv
    COW National Material Capabilities v7.0 (extracted from NMC-v7-abridged.zip).
    Required columns: ccode, year, cinc

  atop3_0ddyr.csv
    ATOP 3.0 directed dyad-year data.
    Required columns: stateA, stateB, year, defense, offense, neutral, nonagg, consul

Input grid:
  data/processed/dyad_states.parquet (build_dyad_states.py): one row per
  ordered pair of states that both exist in the year.

Joins use the code system each source is keyed on. V-Dem `COWcode`, NMC and
ATOP are Correlates of War codes, so they join on `initiator_ccode` /
`target_ccode`, never on the Gleditsch-Ward numbers.

Outputs:
  data/processed/dyads_with_features.parquet
    Key: (year, initiator_ccode, target_ccode)
    Schema: all columns from dyad_states.parquet plus:
      n_pub_a, n_pub_b        (V-Dem polyarchy, 0-1; 0.5 where unobserved)
      n_pub_observed_a/_b     (False where the 0.5 default was used)
      cinc_a, cinc_b          (COW CINC; empty where unobserved)
      dp_a, dp_b              (year-over-year cinc change for A/B)
      r_d_ab                  (absolute cinc difference)
      c_t_ab, c_t_ba          (target's cinc share: B/(A+B) and A/(A+B);
                               they sum to one, 0.5 each where unobserved)
      cinc_observed           (False where either cinc is missing)
      c_d_sup_ab              (ATOP alliance depth supporting the partner)
      c_d_opp_ab              (placeholder: 1 - c_d_sup_ab)
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

YEAR_LO, YEAR_HI = 1946, 2014


def load_vdem() -> pd.DataFrame:
    path_16 = os.path.join(DATA_RAW, "V-Dem-CY-Core-v16.csv")
    if not os.path.exists(path_16):
        print(f"[WARN] V-Dem v16 not found at {path_16}")
        return pd.DataFrame(columns=["COWcode", "year", "v2x_polyarchy"])
    vd = pd.read_csv(path_16, usecols=["COWcode", "year", "v2x_polyarchy"])
    vd = vd.dropna(subset=["COWcode"])
    vd["COWcode"] = vd["COWcode"].astype(int)
    vd["year"] = vd["year"].astype(int)
    vd = vd[(vd.year >= YEAR_LO) & (vd.year <= YEAR_HI)]
    vd = vd.rename(columns={"v2x_polyarchy": "n_pub", "COWcode": "ccode"})
    print(f"  V-Dem v16: {len(vd):,} rows, {vd.ccode.nunique()} countries")
    return vd


def load_cow_nmc() -> pd.DataFrame:
    path = os.path.join(DATA_RAW, "NMC-70-abridged.csv")
    if not os.path.exists(path):
        print(f"[WARN] NMC v7 not found at {path}")
        return pd.DataFrame(columns=["ccode", "year", "cinc"])
    nmc = pd.read_csv(path, usecols=["ccode", "year", "cinc"])
    nmc = nmc.dropna(subset=["ccode", "cinc"])
    nmc["ccode"] = nmc["ccode"].astype(int)
    nmc["year"] = nmc["year"].astype(int)
    nmc = nmc[(nmc.year >= YEAR_LO) & (nmc.year <= YEAR_HI)]
    print(f"  COW NMC v7: {len(nmc):,} rows, {nmc.ccode.nunique()} countries")
    return nmc


def load_cow_atop() -> pd.DataFrame:
    path = os.path.join(DATA_RAW, "atop3_0ddyr.csv")
    if not os.path.exists(path):
        print(f"[WARN] ATOP 3.0 not found at {path}")
        return pd.DataFrame(columns=["stateA", "stateB", "year", "defense",
                                      "offense", "neutral", "nonagg", "consul"])
    atop = pd.read_csv(path)
    atop = atop.dropna(subset=["stateA", "stateB", "year"])
    atop["stateA"] = atop["stateA"].astype(int)
    atop["stateB"] = atop["stateB"].astype(int)
    atop["year"] = atop["year"].astype(int)
    atop = atop[(atop.year >= YEAR_LO) & (atop.year <= YEAR_HI)]
    print(f"  ATOP 3.0: {len(atop):,} rows, "
          f"{atop.groupby(['stateA','stateB']).ngroups:,} directed dyads")
    return atop


def build_features() -> int:
    print("Building features for model back-test...\n")
    vdem = load_vdem()
    nmc = load_cow_nmc()
    if len(nmc):
        nmc = nmc.sort_values(["ccode", "year"])
        nmc["dp"] = nmc.groupby("ccode")["cinc"].diff().fillna(0)
    atop = load_cow_atop()

    grid_path = os.path.join(DATA_PROCESSED, "dyad_states.parquet")
    print(f"\nLoading dyad-year states from {grid_path}...")
    dy = pd.read_parquet(grid_path)
    dy = dy[(dy.year >= YEAR_LO) & (dy.year <= YEAR_HI)].copy()
    print(f"  Grid: {len(dy):,} directed dyad-years ({YEAR_LO}-{YEAR_HI}), "
          f"{dy.initiator_ccode.nunique()} states")

    # V-Dem polyarchy -> N_pub. Unobserved values take the neutral 0.5 and are flagged.
    if len(vdem):
        for side, col in (("a", "initiator_ccode"), ("b", "target_ccode")):
            dy = dy.merge(
                vdem.rename(columns={"ccode": col, "n_pub": f"n_pub_{side}"})[[col, "year", f"n_pub_{side}"]],
                on=[col, "year"], how="left",
            )
            dy[f"n_pub_observed_{side}"] = dy[f"n_pub_{side}"].notna()
            print(f"  V-Dem N_pub_{side} observed on {dy[f'n_pub_observed_{side}'].mean():.1%} of rows")
            dy[f"n_pub_{side}"] = dy[f"n_pub_{side}"].fillna(0.5)

    # COW capabilities. Shares are computed once, from observed values only.
    if len(nmc):
        for side, col in (("a", "initiator_ccode"), ("b", "target_ccode")):
            dy = dy.merge(
                nmc.rename(columns={"ccode": col, "cinc": f"cinc_{side}", "dp": f"dp_{side}"})[
                    [col, "year", f"cinc_{side}", f"dp_{side}"]
                ],
                on=[col, "year"], how="left",
            )
        dy["cinc_observed"] = dy["cinc_a"].notna() & dy["cinc_b"].notna()
        print(f"  NMC CINC observed for both states on {dy['cinc_observed'].mean():.1%} of rows")
        total = dy["cinc_a"] + dy["cinc_b"]
        share_b = (dy["cinc_b"] / total).where(dy["cinc_observed"] & (total > 0))
        # C_T = target capability share. Unobserved pairs take an even split, flagged above.
        dy["c_t_ab"] = share_b.fillna(0.5)
        dy["c_t_ba"] = 1.0 - dy["c_t_ab"]
        dy["r_d_ab"] = (dy["cinc_a"] - dy["cinc_b"]).abs().fillna(0.0)
        dy["dp_a"] = dy["dp_a"].fillna(0.0)
        dy["dp_b"] = dy["dp_b"].fillna(0.0)

    # ATOP alliance depth (ATOP state codes are COW codes).
    if len(atop):
        atop = atop.copy()
        atop["depth"] = (
            atop["defense"] * 1.0 + atop["offense"] * 1.0 + atop["consul"] * 0.5
            + atop["neutral"] * 0.2 + atop["nonagg"] * 0.2
        ).clip(0, 1)
        sup = (
            atop.rename(columns={"stateA": "initiator_ccode", "stateB": "target_ccode", "depth": "c_d_sup_ab"})
            .groupby(["initiator_ccode", "target_ccode", "year"])["c_d_sup_ab"].max().reset_index()
        )
        dy = dy.merge(sup, on=["initiator_ccode", "target_ccode", "year"], how="left")
        print(f"  ATOP alliance present on {dy['c_d_sup_ab'].notna().mean():.1%} of rows")
        dy["c_d_sup_ab"] = dy["c_d_sup_ab"].fillna(0.0)
        # Placeholder until a real third-party lookup exists.
        dy["c_d_opp_ab"] = 1.0 - dy["c_d_sup_ab"]

    if dy.duplicated(["year", "initiator_ccode", "target_ccode"]).any():
        raise ValueError("build_features: a join duplicated directed dyad-years")
    if "c_t_ab" in dy.columns and not np.allclose(dy["c_t_ab"] + dy["c_t_ba"], 1.0):
        raise ValueError("build_features: capability shares do not sum to one")

    out_path = os.path.join(DATA_PROCESSED, "dyads_with_features.parquet")
    dy.to_parquet(out_path, index=False)
    print(f"\nWrote {out_path} ({len(dy):,} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(build_features())
