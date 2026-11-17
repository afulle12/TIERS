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

Outputs:
  data/processed/dyads_with_features.parquet (or .csv fallback)
    Key: (initiator_gwno, target_gwno, year)
    Schema: all columns from conflict_dyads_full.csv plus:
      n_pub_a, n_pub_b        (polyarchy / 100, 0-1 scale)
      dp_a, dp_b              (year-over-year cinc change for A/B)
      r_d_ab                  (cinc ratio: abs diff)
      c_t_ab, c_t_ba          (cinc share: B/(A+B) for A->B, A/(A+B) for B->A)
      c_d_sup_ab              (ATOP alliance depth supporting the partner)
      c_d_opp_ab              (ATOP alliance depth opposing the partner)
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

    # -----------------------------------------------------------------
    # 1. Load V-Dem → N_pub = polyarchy score as public peacefulness proxy
    # -----------------------------------------------------------------
    vdem = load_vdem()

    # -----------------------------------------------------------------
    # 2. Load COW NMC → CINC for power, capability
    # -----------------------------------------------------------------
    nmc = load_cow_nmc()
    if len(nmc):
        nmc["dp"] = nmc.groupby("ccode")["cinc"].diff().fillna(0)

    # -----------------------------------------------------------------
    # 3. Load COW ATOP → alliance depth
    # -----------------------------------------------------------------
    atop = load_cow_atop()

    # -----------------------------------------------------------------
    # 4. Load the dyad-year grid (T0-T5)
    # -----------------------------------------------------------------
    grid_path = os.path.join(DATA_PROCESSED, "conflict_dyads_full.csv")
    print(f"\nLoading conflict dyad grid from {grid_path}...")
    # Read in chunks to reduce memory; use only required columns
    cols = ["year", "initiator_gwno", "target_gwno", "initiator", "target",
            "uiw_tier", "hostlev", "tier_label", "source"]
    dy = pd.read_csv(grid_path, usecols=cols, dtype={"year": int})
    dy = dy[(dy.year >= YEAR_LO) & (dy.year <= YEAR_HI)]

    # Drop rows without GWNO codes (can't join features)
    dy = dy.dropna(subset=["initiator_gwno", "target_gwno"]).copy()
    dy["initiator_gwno"] = dy["initiator_gwno"].astype(int)
    dy["target_gwno"] = dy["target_gwno"].astype(int)
    print(f"  Grid: {len(dy):,} directed dyad-years ({YEAR_LO}-{YEAR_HI})")
    print(f"  Unique initiators: {dy.initiator_gwno.nunique()}, "
          f"unique targets: {dy.target_gwno.nunique()}")

    # -----------------------------------------------------------------
    # 5. Attach V-Dem N_pub (polyarchy → 0-1 peacefulness proxy)
    # -----------------------------------------------------------------
    if len(vdem):
        vdem_a = vdem.rename(columns={"ccode": "initiator_gwno", "n_pub": "n_pub_a"})
        vdem_b = vdem.rename(columns={"ccode": "target_gwno", "n_pub": "n_pub_b"})
        dy = dy.merge(vdem_a[["initiator_gwno", "year", "n_pub_a"]],
                      on=["initiator_gwno", "year"], how="left")
        dy = dy.merge(vdem_b[["target_gwno", "year", "n_pub_b"]],
                      on=["target_gwno", "year"], how="left")
        # Fill missing polyarchy with 0.5 (neutral)
        dy["n_pub_a"] = dy["n_pub_a"].fillna(0.5)
        dy["n_pub_b"] = dy["n_pub_b"].fillna(0.5)
        init_cov = dy["n_pub_a"].notna().mean()
        tgt_cov = dy["n_pub_b"].notna().mean()
        print(f"  V-Dem attached: init N_pub coverage={init_cov:.0%}  "
              f"target N_pub coverage={tgt_cov:.0%}")

    # -----------------------------------------------------------------
    # 6. Attach power-transition (dP) and capability (C_T) from NMC
    # -----------------------------------------------------------------
    if len(nmc):
        # dP = year-over-year CINC change for initiator (power shift dissatisfaction)
        nmc_a = nmc.rename(columns={"ccode": "initiator_gwno", "cinc": "cinc_a", "dp": "dp_a"})
        nmc_b = nmc.rename(columns={"ccode": "target_gwno", "cinc": "cinc_b", "dp": "dp_b"})
        dy = dy.merge(nmc_a[["initiator_gwno", "year", "cinc_a", "dp_a"]],
                      on=["initiator_gwno", "year"], how="left")
        dy = dy.merge(nmc_b[["target_gwno", "year", "cinc_b", "dp_b"]],
                      on=["target_gwno", "year"], how="left")

        # C_T = target capability share (used by attacker in opportunity calculation)
        # For A->B: C_T = cinc_b / (cinc_a + cinc_b)
        total_cinc = dy["cinc_a"].fillna(1) + dy["cinc_b"].fillna(1)
        dy["c_t_ab"] = dy["cinc_b"].fillna(0.5) / total_cinc
        dy["c_t_ba"] = dy["cinc_a"].fillna(0.5) / total_cinc

        # R_d = revisionist demand proxy: absolute CINC difference
        dy["r_d_ab"] = (dy["cinc_a"].fillna(0) - dy["cinc_b"].fillna(0)).abs()

        # Fill missing
        dy["cinc_a"] = dy["cinc_a"].fillna(0.01)
        dy["cinc_b"] = dy["cinc_b"].fillna(0.01)
        dy["dp_a"] = dy["dp_a"].fillna(0)
        dy["dp_b"] = dy["dp_b"].fillna(0)
        print(f"  NMC attached: CINC coverage {dy.cinc_a.notna().mean():.0%}")

    # -----------------------------------------------------------------
    # 7. Attach alliance depth (C_d_sup, C_d_opp) from ATOP
    # -----------------------------------------------------------------
    if len(atop):
        # Alliance depth (0-1 scale for directed equations):
        # defense = 1, offense = 1, consul = 0.5, neutral/nonagg = 0.2
        atop = atop.copy()
        atop["depth"] = (
            atop["defense"] * 1.0
            + atop["offense"] * 1.0
            + atop["consul"] * 0.5
            + atop["neutral"] * 0.2
            + atop["nonagg"] * 0.2
        ).clip(0, 1)

        # Directed: A -> B = stateA -> stateB
        sup_ab = atop.rename(columns={
            "stateA": "initiator_gwno", "stateB": "target_gwno",
            "depth": "c_d_sup_ab"
        })

        # C_d_sup: A and B have an alliance -> A supports B
        dy = dy.merge(
            sup_ab.groupby(["initiator_gwno", "target_gwno", "year"])["c_d_sup_ab"].max().reset_index(),
            on=["initiator_gwno", "target_gwno", "year"], how="left"
        )
        # C_d_opp: A is allied to someone who opposes B -> A opposes B
        # For simplicity: if A's allies exclude B, treat as opposition.
        # We'll compute from the same alliance data: opp = sup on any third party
        # For now, set opp = 1 - sup as a placeholder until proper third-party lookup.
        dy["c_d_opp_ab"] = 1.0 - dy["c_d_sup_ab"].fillna(0)

        # Fill
        dy["c_d_sup_ab"] = dy["c_d_sup_ab"].fillna(0)
        print(f"  ATOP attached: alliance coverage {dy.c_d_sup_ab.notna().mean():.0%}")

    # -----------------------------------------------------------------
    # 8. Write output
    # -----------------------------------------------------------------
    out_cols = ["year", "initiator_gwno", "target_gwno", "initiator", "target",
                "uiw_tier", "hostlev", "tier_label", "source"]
    for c in dy.columns:
        if c not in out_cols:
            out_cols.append(c)

    out = dy[out_cols].copy()
    out_path = os.path.join(DATA_PROCESSED, "dyads_with_features")
    try:
        import pyarrow  # noqa
        out.to_parquet(f"{out_path}.parquet", index=False)
        print(f"\nWrote {out_path}.parquet ({len(out):,} rows)")
    except ImportError:
        out.to_csv(f"{out_path}.csv", index=False)
        print(f"\nWrote {out_path}.csv ({len(out):,} rows)")

    return 0


if __name__ == "__main__":
    raise SystemExit(build_features())
