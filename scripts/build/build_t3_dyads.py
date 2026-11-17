"""Build T3 directed-dyad rows from UCDP Dyadic v26.1 internationalized internal conflicts.

Approach:
  1. Filter Dyadic to type_of_conflict == 4 (internationalized internal).
  2. For each non-empty side_a_2nd / side_b_2nd (which are comma-separated GWN lists),
     explode into one row per supporter.
  3. Map supporter GWN -> standard country name via data/processed/conflict_tiers.csv.
  4. Emit a directed T3 row: (year, conflict_id, dyad_id, supporter_gwno, supporter_name,
     host_gwno, host_name, side_backed, intensity_level, D_k, attribution).
  5. Compute D_k (consecutive-year duration) per (supporter, host, conflict).
  6. Default attribution=0.5; bump to 0.7 when intensity_level==2 (war); record
     as absent if you have no source for deniability.
"""
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
DY = os.path.join(DATA_RAW, "Dyadic_v26_1.csv")
TIERS = os.path.join(DATA_PROCESSED, "conflict_tiers.csv")
OUT = os.path.join(DATA_RAW, "T3_directed_v26_1.csv")

dy = pd.read_csv(DY)
tiers = pd.read_csv(TIERS)

def make_supporter_name_map(d: pd.DataFrame) -> pd.Series:
    """Build a GWN -> supporter name map using only single-entry rows (length-1 lists)
    from side_a / side_b (where supporters appear as primary actors in other conflicts)."""
    parts = []
    for gwn_col, name_col in [("gwno_a", "side_a"), ("gwno_b", "side_b")]:
        sub = d[[gwn_col, name_col]].copy()
        sub.columns = ["gwno", "name"]
        sub = sub.dropna(subset=["gwno", "name"])
        sub = sub.assign(
            gwno_list=sub["gwno"].astype(str).str.split(","),
            name_list=sub["name"].astype(str).str.split(","),
        )
        sub = sub[sub["gwno_list"].apply(len) == 1]
        sub = sub[sub["name_list"].apply(len) == 1]
        sub["gwno"] = sub["gwno_list"].str[0].str.strip()
        sub["name"] = sub["name_list"].str[0].str.strip()
        sub = sub[(sub["gwno"] != "") & (sub["name"] != "")]
        parts.append(sub[["gwno", "name"]])
    out = pd.concat(parts, ignore_index=True).drop_duplicates("gwno", keep="first")
    return out.set_index("gwno")["name"]

supporter_name_map = make_supporter_name_map(dy)

def split_supporters(df: pd.DataFrame, gwn_col: str, side: str) -> pd.DataFrame:
    sub = df[df.type_of_conflict == 4].copy()
    sub[gwn_col] = sub[gwn_col].fillna("").astype(str)
    sub = sub[sub[gwn_col].str.strip() != ""]
    sub = sub.assign(_gwn=sub[gwn_col].str.split(","))
    sub = sub.explode("_gwn")
    sub["_gwn"] = sub["_gwn"].str.strip()
    sub = sub[sub["_gwn"] != ""]
    sub = sub.rename(columns={"_gwn": "supporter_gwno"})
    sub["side_backed"] = side
    return sub

CANONICAL_T3 = True
OUT_BROAD = os.path.join(DATA_RAW, "T3_broad_v26_1.csv")

if CANONICAL_T3:
    rebels = split_supporters(dy, "gwno_b_2nd", "side_b")
    t3 = rebels
    print(f"Using canonical T3: supporters of side_b (rebels) only.")
    a = split_supporters(dy, "gwno_a_2nd", "side_a")
    b = split_supporters(dy, "gwno_b_2nd", "side_b")
    t3_broad = pd.concat([a, b], ignore_index=True)
else:
    a = split_supporters(dy, "gwno_a_2nd", "side_a")
    b = split_supporters(dy, "gwno_b_2nd", "side_b")
    t3 = pd.concat([a, b], ignore_index=True)
    print(f"Using broad T3: supporters of side_a + side_b.")

t3 = t3.merge(
    supporter_name_map.rename("supporter_name"),
    left_on="supporter_gwno",
    right_index=True,
    how="left",
)
t3["supporter_name"] = t3["supporter_name"].fillna("GWN_" + t3["supporter_gwno"].astype(str))
t3["host_name"] = t3["location"]

t3["host_gwno"] = t3["gwno_loc"]

t3 = t3[["year", "conflict_id", "dyad_id",
         "supporter_gwno", "supporter_name",
         "host_gwno", "host_name",
         "side_backed", "intensity_level",
         "incompatibility", "territory_name", "region"]]

t3 = t3.drop_duplicates(["year", "supporter_gwno", "host_gwno", "conflict_id"])

t3 = t3.sort_values(["supporter_gwno", "host_gwno", "conflict_id", "year"]).reset_index(drop=True)

def consecutive_duration(grp: pd.DataFrame) -> pd.Series:
    grp = grp.sort_values("year")
    years = grp["year"].values
    out = []
    run = 0
    prev = None
    for y in years:
        run = run + 1 if (prev is not None and y == prev + 1) else 1
        out.append(run)
        prev = y
    return pd.Series(out, index=grp.index)

t3["D_k"] = (
    t3.groupby(["supporter_gwno", "host_gwno", "conflict_id"], group_keys=False)
      .apply(consecutive_duration)
)

t3["attribution"] = 0.5
t3.loc[t3.intensity_level == 2, "attribution"] = 0.7

t3["selective"] = True
t3["targeted"] = True
t3["corroborated"] = False

t3["uiw_tier"] = 3
t3["tier_label"] = "T3-Proxy/Indirect Military"
t3["hostlev"] = 3
t3["in_conflict"] = True

t3.to_csv(OUT, index=False)

print(f"\nEmitted {len(t3)} T3 directed-dyad rows -> {OUT}")
print(f"Year range: {t3.year.min()}-{t3.year.max()}")
print(f"Distinct (supporter -> host) pairs: {t3.groupby(['supporter_gwno','host_gwno']).ngroups}")
print(f"Distinct supporters: {t3.supporter_gwno.nunique()}")
print(f"Distinct host states: {t3.host_gwno.nunique()}")

if CANONICAL_T3:
    t3_broad_out = t3_broad.copy()
    t3_broad_out = t3_broad_out.merge(
        supporter_name_map.rename("supporter_name"),
        left_on="supporter_gwno",
        right_index=True,
        how="left",
    )
    t3_broad_out["supporter_name"] = t3_broad_out["supporter_name"].fillna(
        "GWN_" + t3_broad_out["supporter_gwno"].astype(str)
    )
    t3_broad_out["host_name"] = t3_broad_out["location"]
    t3_broad_out["host_gwno"] = t3_broad_out["gwno_loc"]
    t3_broad_out = t3_broad_out[
        ["year", "conflict_id", "dyad_id", "supporter_gwno", "supporter_name",
         "host_gwno", "host_name", "side_backed", "intensity_level",
         "incompatibility", "territory_name", "region"]
    ].drop_duplicates(["year", "supporter_gwno", "host_gwno", "conflict_id"])
    t3_broad_out = t3_broad_out.sort_values(
        ["supporter_gwno", "host_gwno", "conflict_id", "year"]
    ).reset_index(drop=True)
    t3_broad_out["D_k"] = (
        t3_broad_out.groupby(["supporter_gwno", "host_gwno", "conflict_id"], group_keys=False)
                    .apply(consecutive_duration)
    )
    t3_broad_out["attribution"] = 0.5
    t3_broad_out.loc[t3_broad_out.intensity_level == 2, "attribution"] = 0.7
    t3_broad_out["selective"] = True
    t3_broad_out["targeted"] = True
    t3_broad_out["corroborated"] = False
    t3_broad_out["uiw_tier"] = 3
    t3_broad_out["tier_label"] = "T3-Proxy/Indirect Military"
    t3_broad_out["hostlev"] = 3
    t3_broad_out["in_conflict"] = True
    t3_broad_out.to_csv(OUT_BROAD, index=False)
    print(f"Emitted {len(t3_broad_out)} broad T3 directed-dyad rows -> {OUT_BROAD}")

print()
print("Top 10 supporters by T3 directed-dyad-years:")
print(t3.supporter_name.value_counts().head(10))
print()
print("Top 10 host states by T3 directed-dyad-years received:")
print(t3.groupby("host_name").size().sort_values(ascending=False).head(10))
print()
print("Year distribution:")
print(t3.year.value_counts().sort_index().tail(15))
print()
print("D_k distribution (consecutive-year support run length):")
print(t3.D_k.value_counts().sort_index().head(15))
print()
print("Sample rows:")
print(t3.head(5).to_string(index=False))
