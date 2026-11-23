"""Build directed T3 events from the UCDP External Support Dataset (ESD) 18.1.

T3 pathway A: one state gives military assistance to an armed party fighting
another state's government. ESD records, per year, who supported which
primary warring party against which opponent and with what kind of support.

Input
-----
  data/raw/ucdp_esd/ucdp-esd-ty-181.dta   ESD triad-year file, 1975-2017
                                          (https://ucdp.uu.se/downloads/)
  data/raw/Dyadic_v26_1.csv               to map "Government of X" names to GW codes

Rules
-----
1. Supporter. A state government (`ext_nonstate == 0`). Support from
   elements of a state acting without the government's approval
   (`ext_elements == 1`) is not attributable to the state and is dropped.
2. Target. The opponent the support is aimed at must be a state government.
   Support to a government against rebels is not hostile to any state and is
   dropped. Support against another state, or to rebels fighting a
   government, is a directed event supporter -> that government's state.
3. Confirmed. Alleged support (`ext_alleged == 1`) is dropped.
4. Material. At least one of: troops (X), troop presence (P), joint
   operations or access to military infrastructure (Y), weapons (W),
   training (T), funding (F). Materiel/logistics (M), intelligence (I),
   access to territory (L), other (O) and unknown (U) alone do not qualify.
   ESD already excludes commercial arms sales.
5. The supporter and target differ.
6. Attribution prior. 0.7 when troops are sent (X), else 0.5. These are
   starting values, like the UCDP T3 defaults, not measured deniability.

Output: data/processed/esd_t3_events.csv, one row per supporter, target,
recipient and year, with the support-type flags kept for audit.
"""
from __future__ import annotations

import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
ESD_DTA = os.path.join(DATA_RAW, "ucdp_esd", "ucdp-esd-ty-181.dta")
DYADIC_CSV = os.path.join(DATA_RAW, "Dyadic_v26_1.csv")
OUT_CSV = os.path.join(DATA_PROCESSED, "esd_t3_events.csv")

SUPPORT_TYPES = ("x", "p", "y", "w", "m", "t", "f", "i", "l", "o", "u")
MATERIAL_TYPES = ("x", "p", "y", "w", "t", "f")
# Governments in ESD that never appear as a party in UCDP Dyadic v26.1.
NAME_FALLBACK = {
    "Government of East Germany": 265,
    "Government of Solomon Islands": 940,
}
OUT_COLUMNS = [
    "year", "supporter_gwno", "target_gwno", "supporter_name", "target_name",
    "recipient_name", "conflict_id", "dyad_id", "civil", "coalition", "bothsides",
    *[f"type_{t}" for t in SUPPORT_TYPES], "attribution",
]


def government_gw_map(dyadic: pd.DataFrame) -> dict[str, int]:
    """Map each "Government of X" name in UCDP Dyadic to its GW code.

    Names and codes come in parallel comma-separated lists on the primary and
    secondary sides. A name is taken from the code it is paired with most often.
    """
    pairs = []
    for name_col, gw_col in (("side_a", "gwno_a"), ("side_b", "gwno_b"),
                             ("side_a_2nd", "gwno_a_2nd"), ("side_b_2nd", "gwno_b_2nd")):
        for names, codes in zip(dyadic[name_col].fillna("").astype(str),
                                dyadic[gw_col].fillna("").astype(str), strict=True):
            n = [x.strip() for x in names.split(",") if x.strip()]
            c = [x.strip() for x in codes.split(",") if x.strip()]
            if n and len(n) == len(c):
                pairs += [(a, int(float(b))) for a, b in zip(n, c, strict=True) if a.startswith("Government of")]
    counts = pd.DataFrame(pairs, columns=["name", "gw"]).value_counts().reset_index()
    best = counts.sort_values(["count", "gw"], ascending=[False, True]).drop_duplicates("name")
    out = dict(zip(best["name"], best["gw"].astype(int), strict=True))
    for name, gw in NAME_FALLBACK.items():
        out.setdefault(name, gw)
    return out


def directed_support(esd: pd.DataFrame, gw_of: dict[str, int]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the rules to ESD triad-year rows; return `(events, unmapped)`."""
    e = esd.copy()
    for c in ("ext_sup", "ext_nonstate", "ext_elements", "ext_alleged", "ext_coalition", "ext_bothsides",
              *[f"ext_{t}" for t in SUPPORT_TYPES]):
        e[c] = pd.to_numeric(e[c], errors="coerce").fillna(0).astype(int)
    keep = (
        (e["ext_sup"] == 1)
        & (e["ext_nonstate"] == 0)
        & (e["ext_elements"] == 0)
        & (e["ext_alleged"] == 0)
        & e["oppo_name"].astype(str).str.startswith("Government of")
        & (e[[f"ext_{t}" for t in MATERIAL_TYPES]].max(axis=1) == 1)
    )
    e = e[keep].copy()
    e["supporter_gwno"] = e["ext_name"].map(gw_of)
    e["target_gwno"] = e["oppo_name"].map(gw_of)
    unmapped = e[e["supporter_gwno"].isna() | e["target_gwno"].isna()][["year", "ext_name", "oppo_name"]]
    e = e.dropna(subset=["supporter_gwno", "target_gwno"])
    e["supporter_gwno"] = e["supporter_gwno"].astype(int)
    e["target_gwno"] = e["target_gwno"].astype(int)
    e = e[e["supporter_gwno"] != e["target_gwno"]]

    out = pd.DataFrame({
        "year": e["year"].astype(int),
        "supporter_gwno": e["supporter_gwno"],
        "target_gwno": e["target_gwno"],
        "supporter_name": e["ext_name"],
        "target_name": e["oppo_name"],
        "recipient_name": e["actor_name"],
        "conflict_id": e["conflict_id"].astype(int),
        "dyad_id": e["dyad_id"].astype(int),
        "civil": e["civil"].astype(int),
        "coalition": e["ext_coalition"],
        "bothsides": e["ext_bothsides"],
        **{f"type_{t}": e[f"ext_{t}"] for t in SUPPORT_TYPES},
    })
    out["attribution"] = out["type_x"].map({1: 0.7}).fillna(0.5)
    out = out[OUT_COLUMNS].drop_duplicates().sort_values(
        ["year", "supporter_gwno", "target_gwno", "dyad_id", "recipient_name"]
    ).reset_index(drop=True)
    return out, unmapped


def main() -> int:
    if not os.path.exists(ESD_DTA):
        raise SystemExit(f"Missing {ESD_DTA}: download ucdp-esd-ty-181.zip from https://ucdp.uu.se/downloads/")
    esd = pd.read_stata(ESD_DTA, convert_categoricals=False)
    gw_of = government_gw_map(pd.read_csv(DYADIC_CSV, dtype=str))
    events, unmapped = directed_support(esd, gw_of)
    events.to_csv(OUT_CSV, index=False)
    print(f"ESD T3 events -> {OUT_CSV} ({len(events):,} rows, {events.year.min()}-{events.year.max()})")
    print(f"  directed pairs: {events.groupby(['supporter_gwno', 'target_gwno']).ngroups}")
    print("  rows by support type:", {t.upper(): int(events[f'type_{t}'].sum()) for t in SUPPORT_TYPES})
    if len(unmapped):
        names = pd.concat([unmapped["ext_name"], unmapped["oppo_name"]])
        names = names[~names.isin(gw_of)].value_counts()
        print(f"  unmapped rows: {len(unmapped)} ({names.to_dict()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
