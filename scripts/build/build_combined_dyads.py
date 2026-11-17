"""Build combined conflict_dyads.csv = existing MIDB-derived dyads + UCDP T3 (proxy/indirect) dyads + UCDP interstate T4 dyads.

Inputs:
  - data/processed/conflict_dyads.csv (T1/T2/T4/T5 directed dyad-years, MIDB-style names)
  - data/raw/T3_broad_v26_1.csv (UCDP T3 supporter->host directed dyad-years)
  - data/raw/T4_interstate_v26_1.csv (UCDP T4 interstate directed dyad-years)
  - data/raw/CShapes-2.0.csv (GWN name registry, used to validate nation-state status
    and to add GWN codes to existing rows where mappable)

Output:
  - data/processed/conflict_dyads.csv (overwritten; the original is backed up to
    data/processed/conflict_dyads_midb_only.csv)
  - output/analysis/t3_only.csv (T3 contribution, for traceability)
"""
from __future__ import annotations

import os

import pandas as pd

from country_names import normalize_name

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
DATA_RAW = os.path.join(ROOT, "data", "raw")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
BACKUP_CSV = os.path.join(DATA_PROCESSED, "conflict_dyads_midb_only.csv")
EXISTING_CSV = os.path.join(DATA_PROCESSED, "conflict_dyads.csv")
T3_CSV = os.path.join(DATA_RAW, "T3_broad_v26_1.csv")
T4_INTERSTATE_CSV = os.path.join(DATA_RAW, "T4_interstate_v26_1.csv")
T1_CSV = os.path.join(DATA_RAW, "T1_directed_v5.csv")
CSHAPES_CSV = os.path.join(DATA_RAW, "CShapes-2.0.csv")
OUT_CSV = os.path.join(DATA_PROCESSED, "conflict_dyads.csv")
T3_OUT_CSV = os.path.join(OUT_ANALYSIS, "t3_only.csv")
NON_STATE_DROP_REPORT = os.path.join(OUT_ANALYSIS, "t3_non_state_dropped.csv")


def load_cshapes_state_registry() -> dict:
    cs = pd.read_csv(CSHAPES_CSV)
    return (
        cs.dropna(subset=["gwcode"])
        .assign(gwcode=lambda d: d["gwcode"].astype(int))
        [["gwcode", "cntry_name"]]
        .drop_duplicates("gwcode")
        .set_index("gwcode")["cntry_name"]
        .to_dict()
    )


def collapse_same_tier_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    key = ["year", "initiator", "target", "tier_label"]
    if not df.duplicated(key, keep=False).any():
        return df

    def join_sources(s: pd.Series) -> str:
        return "_".join(dict.fromkeys(str(v) for v in s.dropna() if str(v)))

    agg = {
        c: "first" for c in df.columns if c not in key
    }
    if "source" in agg:
        agg["source"] = join_sources
    if "intensity_level" in agg:
        agg["intensity_level"] = "max"
    if "D_k" in agg:
        agg["D_k"] = "max"
    if "attribution" in agg:
        agg["attribution"] = "max"
    if "n_conflicts_aggregated" in agg:
        agg["n_conflicts_aggregated"] = "max"
    return df.groupby(key, as_index=False, dropna=False).agg(agg)


def main() -> int:
    if not os.path.exists(BACKUP_CSV):
        pd.read_csv(EXISTING_CSV).to_csv(BACKUP_CSV, index=False)
        print(f"Backed up original -> {BACKUP_CSV}")
    else:
        print(f"Using existing backup -> {BACKUP_CSV}")

    state_registry = load_cshapes_state_registry()
    state_gws = set(state_registry.keys())
    name_to_gw = {}
    for gw, name in state_registry.items():
        name_to_gw.setdefault(name, gw)
        name_to_gw.setdefault(normalize_name(name), gw)

    existing = pd.read_csv(BACKUP_CSV, dtype={"year": int})
    existing["initiator"] = existing["initiator"].map(normalize_name)
    existing["target"] = existing["target"].map(normalize_name)
    existing["initiator_gwno"] = existing["initiator"].map(name_to_gw)
    existing["target_gwno"] = existing["target"].map(name_to_gw)
    existing["source"] = "MIDB"
    existing["conflict_id"] = pd.NA
    existing["dyad_id"] = pd.NA
    existing["in_conflict"] = True
    print(f"Existing rows: {len(existing)} | GWN mapped: "
          f"init={existing['initiator_gwno'].notna().sum()} "
          f"tgt={existing['target_gwno'].notna().sum()}")

    t3 = pd.read_csv(T3_CSV)
    t3 = t3.dropna(subset=["supporter_gwno", "host_gwno"]).copy()
    t3["supporter_gwno"] = t3["supporter_gwno"].astype(int)
    t3["host_gwno"] = t3["host_gwno"].astype(int)

    dropped_mask = ~t3["supporter_gwno"].isin(state_gws)
    dropped = t3[dropped_mask].copy()
    kept = t3[~dropped_mask].copy()
    print(f"T3 rows: {len(t3)} | kept (state actor): {len(kept)} | "
          f"dropped (non-state): {len(dropped)}")
    if len(dropped):
        os.makedirs(os.path.dirname(NON_STATE_DROP_REPORT), exist_ok=True)
        dropped.to_csv(NON_STATE_DROP_REPORT, index=False)
        print(f"  dropped report -> {NON_STATE_DROP_REPORT}")

    cshapes_name = pd.read_csv(CSHAPES_CSV)
    latest_name_by_gw = (
        cshapes_name.dropna(subset=["gwcode"])
        .assign(gwcode=lambda d: d["gwcode"].astype(int))
        .sort_values("gwsyear", ascending=False)
        .drop_duplicates("gwcode")
        .set_index("gwcode")["cntry_name"]
        .to_dict()
    )
    gw_to_name = {gw: normalize_name(name) for gw, name in latest_name_by_gw.items()}

    def resolve_name(raw_name: str, gw: int) -> str:
        gwn = int(gw) if pd.notna(gw) else None
        gwn_name = gw_to_name.get(gwn) if gwn is not None else None
        if gwn_name:
            return gwn_name
        norm = normalize_name(raw_name)
        return norm or (f"GWN_{gwn}" if gwn is not None else "GWN_unknown")

    kept["initiator"] = [
        resolve_name(n, g) for n, g in zip(kept["supporter_name"], kept["supporter_gwno"])
    ]
    kept["target"] = [
        resolve_name(n, g) for n, g in zip(kept["host_name"], kept["host_gwno"])
    ]

    t3_out = pd.DataFrame({
        "year": kept["year"].astype(int),
        "initiator": kept["initiator"].values,
        "target": kept["target"].values,
        "hostlev": kept["hostlev"].astype(int).values,
        "uiw_tier": kept["uiw_tier"].astype(int).values,
        "tier_label": kept["tier_label"].values,
        "initiator_gwno": kept["supporter_gwno"].astype(int).values,
        "target_gwno": kept["host_gwno"].astype(int).values,
        "source": "UCDP_T3",
        "conflict_id": kept["conflict_id"].astype(int).values,
        "dyad_id": kept["dyad_id"].astype(int).values,
        "side_backed": kept["side_backed"].values,
        "intensity_level": kept["intensity_level"].astype(int).values,
        "D_k": kept["D_k"].astype(int).values,
        "attribution": kept["attribution"].astype(float).values,
        "selective": kept["selective"].astype(bool).values,
        "targeted": kept["targeted"].astype(bool).values,
        "corroborated": kept["corroborated"].astype(bool).values,
        "in_conflict": kept["in_conflict"].astype(bool).values,
        "incompatibility": kept["incompatibility"].astype(int).values,
        "territory_name": kept["territory_name"].values,
        "region": kept["region"].astype(int).values,
    })

    os.makedirs(os.path.dirname(T3_OUT_CSV), exist_ok=True)
    t3_out_aggregated = (
        t3_out.sort_values(["year", "initiator", "target", "intensity_level", "conflict_id"], ascending=[True, True, True, False, True])
        .groupby(["year", "initiator", "target"], as_index=False)
        .agg(
            hostlev=("hostlev", "first"),
            uiw_tier=("uiw_tier", "first"),
            tier_label=("tier_label", "first"),
            initiator_gwno=("initiator_gwno", "first"),
            target_gwno=("target_gwno", "first"),
            source=("source", "first"),
            conflict_id=("conflict_id", "first"),
            dyad_id=("dyad_id", "first"),
            side_backed=("side_backed", "first"),
            intensity_level=("intensity_level", "max"),
            D_k=("D_k", "max"),
            attribution=("attribution", "max"),
            selective=("selective", "first"),
            targeted=("targeted", "first"),
            corroborated=("corroborated", "first"),
            in_conflict=("in_conflict", "first"),
            incompatibility=("incompatibility", "first"),
            territory_name=("territory_name", "first"),
            region=("region", "first"),
            n_conflicts_aggregated=("conflict_id", "nunique"),
        )
    )
    t3_out_aggregated.to_csv(T3_OUT_CSV, index=False)
    print(f"T3-only output (aggregated to (year, initiator, target)) -> {T3_OUT_CSV} ({len(t3_out_aggregated)} rows)")

    # ---- T4 (Interstate) from UCDP Dyadic ----
    t4_path = T4_INTERSTATE_CSV
    if os.path.exists(t4_path):
        t4 = pd.read_csv(t4_path, dtype={"year": int})
        t4 = t4.dropna(subset=["initiator_gwno", "target_gwno"]).copy()
        t4["initiator_gwno"] = t4["initiator_gwno"].astype(int)
        t4["target_gwno"] = t4["target_gwno"].astype(int)
        dropped_mask = ~t4["initiator_gwno"].isin(state_gws) | ~t4["target_gwno"].isin(state_gws)
        t4_kept = t4[~dropped_mask].copy()
        print(f"UCDP interstate rows: {len(t4)} | kept (state actors): {len(t4_kept)} | "
              f"dropped: {dropped_mask.sum()}")
        t4_kept["initiator"] = [
            resolve_name(n, g)
            for n, g in zip(t4_kept.get("initiator", ""), t4_kept["initiator_gwno"])
        ]
        t4_kept["target"] = [
            resolve_name(n, g)
            for n, g in zip(t4_kept.get("target", ""), t4_kept["target_gwno"])
        ]
        t4_out_aggregated = (
            t4_kept.sort_values(
                ["year", "initiator", "target", "intensity_level", "conflict_id"],
                ascending=[True, True, True, False, True],
            )
            .groupby(["year", "initiator", "target"], as_index=False)
            .agg(
                hostlev=("hostlev", "first"),
                uiw_tier=("uiw_tier", "first"),
                tier_label=("tier_label", "first"),
                initiator_gwno=("initiator_gwno", "first"),
                target_gwno=("target_gwno", "first"),
                source=("source", "first"),
                conflict_id=("conflict_id", "first"),
                dyad_id=("dyad_id", "first"),
                intensity_level=("intensity_level", "max"),
                D_k=("D_k", "max"),
                attribution=("attribution", "max"),
                in_conflict=("in_conflict", "first"),
                incompatibility=("incompatibility", "first"),
                territory_name=("territory_name", "first"),
                region=("region", "first"),
                n_conflicts_aggregated=("conflict_id", "nunique"),
            )
        )
        for c in ("side_backed", "selective", "targeted", "corroborated"):
            if c not in t4_out_aggregated.columns:
                t4_out_aggregated[c] = pd.NA
        print(f"UCDP interstate aggregated -> {len(t4_out_aggregated)} rows")
    else:
        t4_out_aggregated = pd.DataFrame(columns=existing.columns)
        print(f"UCDP interstate file not found at {t4_path}, skipping")

    # ---- T1 (Diplomatic Crisis) from MIDB ----
    t1_path = T1_CSV
    if os.path.exists(t1_path):
        t1 = pd.read_csv(t1_path, dtype={"year": int})
        t1["initiator"] = t1["initiator"].map(normalize_name)
        t1["target"] = t1["target"].map(normalize_name)
        t1["initiator_gwno"] = t1["initiator"].map(name_to_gw)
        t1["target_gwno"] = t1["target"].map(name_to_gw)
        t1["source"] = "MIDB_T1"
        for c in ("conflict_id", "dyad_id", "side_backed", "intensity_level", "D_k",
                  "attribution", "selective", "targeted", "corroborated",
                  "incompatibility", "territory_name", "region", "n_conflicts_aggregated"):
            t1[c] = pd.NA
        t1["in_conflict"] = True
        t1_out = t1[list(existing.columns)]
        print(f"T1 rows (from {t1_path}): {len(t1_out)} | GWN mapped: "
              f"init={t1_out['initiator_gwno'].notna().sum()} "
              f"tgt={t1_out['target_gwno'].notna().sum()}")
    else:
        t1_out = pd.DataFrame(columns=existing.columns)
        print(f"T1 file not found at {t1_path}, skipping")

    # Remove old T1 rows (existing has T1 from the original MIDB pipeline) to
    # avoid duplicate (year, initiator, target, tier_label) rows
    existing_no_t1 = existing[existing["tier_label"] != "T1-Diplomatic Crisis"].copy()
    dropped_t1 = len(existing) - len(existing_no_t1)
    if dropped_t1:
        print(f"Dropped {dropped_t1} old T1 rows (replaced by MIDB_T1)")

    combined = pd.concat([existing_no_t1, t3_out_aggregated, t4_out_aggregated, t1_out], ignore_index=True, sort=False)
    before_dedupe = len(combined)
    combined = collapse_same_tier_duplicates(combined)
    print(f"Collapsed same-tier duplicate rows: {before_dedupe - len(combined)}")
    combined = combined.sort_values(
        ["year", "tier_label", "initiator", "target"]
    ).reset_index(drop=True)
    combined.to_csv(OUT_CSV, index=False)
    print(f"Combined output -> {OUT_CSV} ({len(combined)} rows)")

    print()
    print("Tier counts in combined file:")
    print(combined["tier_label"].value_counts().to_string())
    print()
    print("Source counts:")
    print(combined["source"].value_counts().to_string())
    print()
    print("Year range:", combined.year.min(), "-", combined.year.max())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
