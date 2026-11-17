"""Build T4 directed-dyad rows from UCDP Dyadic v26.1 interstate conflicts.

Approach:
  1. Filter Dyadic to type_of_conflict == 2 (interstate armed conflict).
  2. Extract gwno_a / gwno_b (may be comma-separated lists of GWN codes).
  3. Explode into one row per (a_gwno, b_gwno) directed pair.
  4. Map both directions: (a->b) and (b->a).
  5. Resolve GWN to standard country names via CShapes.
  6. Emit as T4 (Limited Direct Military) with intensity_level preserved.
  7. Compute D_k (consecutive-year duration) per (initiator, target, conflict_id).

Inputs:
  - data/raw/Dyadic_v26_1.csv (UCDP Dyadic v26.1)
  - data/raw/CShapes-2.0.csv (GWN name registry)

Outputs:
  - data/raw/T4_interstate_v26_1.csv (directed dyad-year rows)
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from country_names import normalize_name

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")

DY = os.path.join(DATA_RAW, "Dyadic_v26_1.csv")
CSHAPES_CSV = os.path.join(DATA_RAW, "CShapes-2.0.csv")
OUT = os.path.join(DATA_RAW, "T4_interstate_v26_1.csv")


def load_cshapes_state_registry() -> set[int]:
    cs = pd.read_csv(CSHAPES_CSV)
    return set(
        cs.dropna(subset=["gwcode"])
        .assign(gwcode=lambda d: d["gwcode"].astype(int))
        ["gwcode"]
        .unique()
    )


def load_latest_cshapes_name(gw: int) -> str:
    cs = pd.read_csv(CSHAPES_CSV)
    sub = (
        cs.dropna(subset=["gwcode"])
        .assign(gwcode=lambda d: d["gwcode"].astype(int))
    )
    sub = sub[sub.gwcode == gw]
    if sub.empty:
        return f"GWN_{gw}"
    return normalize_name(sub.sort_values("gwsyear", ascending=False).iloc[0]["cntry_name"])


def parse_gwn_list(raw: object) -> list[int]:
    if pd.isna(raw) or raw is None:
        return []
    s = str(raw).strip()
    if not s:
        return []
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            try:
                out.append(int(float(part)))
            except (ValueError, OverflowError):
                pass
    return out


def consecutive_duration(grp: pd.DataFrame) -> pd.Series:
    years = grp["year"].values
    out = []
    run = 0
    prev = None
    for y in years:
        run = run + 1 if (prev is not None and y == prev + 1) else 1
        out.append(run)
        prev = y
    return pd.Series(out, index=grp.index)


def main() -> int:
    print("Loading UCDP Dyadic v26.1...")
    dy = pd.read_csv(DY)
    print(f"  {len(dy):,} rows, type_of_conflict counts:")
    print(dy["type_of_conflict"].value_counts().sort_index().to_string())

    interstate = dy[dy.type_of_conflict == 2].copy()
    print(f"\nInterstate (type=2) rows: {len(interstate):,}")

    state_gws = load_cshapes_state_registry()
    print(f"  CShapes state GWNs: {len(state_gws):,}")

    # Build directed pairs
    rows: list[dict] = []
    for _, r in interstate.iterrows():
        a_gwns = parse_gwn_list(r.get("gwno_a"))
        b_gwns = parse_gwn_list(r.get("gwno_b"))
        year = int(r["year"])
        conflict_id = int(r["conflict_id"]) if pd.notna(r.get("conflict_id")) else None
        dyad_id = int(r["dyad_id"]) if pd.notna(r.get("dyad_id")) else None
        intensity = int(r["intensity_level"]) if pd.notna(r.get("intensity_level")) else 1
        incompatibility = int(r["incompatibility"]) if pd.notna(r.get("incompatibility")) else None
        territory = r.get("territory_name") if pd.notna(r.get("territory_name")) else None
        region_raw = r.get("region")
        if pd.notna(region_raw):
            try:
                region = int(str(region_raw).split(",")[0].strip())
            except (ValueError, AttributeError):
                region = None
        else:
            region = None

        for ag in a_gwns:
            for bg in b_gwns:
                if ag == bg:
                    continue
                if ag not in state_gws or bg not in state_gws:
                    continue
                # a -> b
                rows.append({
                    "year": year,
                    "initiator_gwno": ag,
                    "target_gwno": bg,
                    "conflict_id": conflict_id,
                    "dyad_id": dyad_id,
                    "intensity_level": intensity,
                    "incompatibility": incompatibility,
                    "territory_name": territory,
                    "region": region,
                })
                # b -> a
                rows.append({
                    "year": year,
                    "initiator_gwno": bg,
                    "target_gwno": ag,
                    "conflict_id": conflict_id,
                    "dyad_id": dyad_id,
                    "intensity_level": intensity,
                    "incompatibility": incompatibility,
                    "territory_name": territory,
                    "region": region,
                })

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(["year", "initiator_gwno", "target_gwno", "conflict_id"])
    print(f"Total directed pairs (both directions): {len(df):,}")

    # Sort for D_k
    df = df.sort_values(["initiator_gwno", "target_gwno", "conflict_id", "year"]).reset_index(drop=True)

    # D_k per directed dyad-conflict
    df["D_k"] = (
        df.groupby(["initiator_gwno", "target_gwno", "conflict_id"], group_keys=False)
          .apply(consecutive_duration)
    )

    # Resolve country names
    gw_to_name = {gw: load_latest_cshapes_name(gw) for gw in sorted(set(df.initiator_gwno) | set(df.target_gwno))}
    df["initiator"] = df["initiator_gwno"].map(gw_to_name)
    df["target"] = df["target_gwno"].map(gw_to_name)

    # Set tier fields
    df["uiw_tier"] = 4
    df["tier_label"] = "T4-Limited Military"
    df["hostlev"] = 4
    df["source"] = "UCDP_INTERSTATE"
    df["in_conflict"] = True
    df["attribution"] = 1.0
    df["selective"] = False
    df["targeted"] = False
    df["corroborated"] = True
    df["side_backed"] = pd.NA

    # Output columns matching the combined schema
    out_cols = [
        "year", "initiator", "target", "hostlev", "uiw_tier", "tier_label",
        "initiator_gwno", "target_gwno", "source", "conflict_id", "dyad_id",
        "in_conflict", "side_backed", "intensity_level", "D_k", "attribution",
        "selective", "targeted", "corroborated",
        "incompatibility", "territory_name", "region",
    ]
    for c in out_cols:
        if c not in df.columns:
            df[c] = pd.NA

    out = df[out_cols].copy()
    out["year"] = out["year"].astype(int)
    out["intensity_level"] = out["intensity_level"].fillna(1).astype(int)
    out["D_k"] = out["D_k"].fillna(1).astype(int)

    out.to_csv(OUT, index=False)
    print(f"\nEmitted {len(out)} T4 directed-dyad rows -> {OUT}")
    print(f"  Year range: {int(out.year.min())}-{int(out.year.max())}")
    print(f"  Distinct directed dyads: {out.groupby(['initiator_gwno','target_gwno']).ngroups}")
    print(f"  Intensity 1: {(out.intensity_level == 1).sum()}, Intensity 2: {(out.intensity_level == 2).sum()}")
    print(f"  Post-2014 rows: {len(out[out.year > 2014])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
