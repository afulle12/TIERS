"""Country-code reconciliation for trade datasets.

The conflict pipeline uses Gleditsch-Ward / COW-style GWNO codes. CEPII
trade sources use BACI numeric country codes, ISO3-like strings, and a
large set of historical TRADHIST entity codes. This module centralizes the
translation logic so BACI and TRADHIST are normalized the same way.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pandas as pd

try:
    from scripts.build.build_country_canonical import ALIAS_DICT
    from scripts.build.country_names import normalize_name
except ModuleNotFoundError:  # Allow direct execution from scripts/build/.
    from build_country_canonical import ALIAS_DICT
    from country_names import normalize_name


ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

CSHAPES_CSV = DATA_RAW / "CShapes-2.0.csv"
BACI_ZIP = DATA_RAW / "BACI_HS92_V202601.zip"
OUT_CSV = DATA_PROCESSED / "country_code_crosswalk.csv"


# TRADHIST uses ISO3 for modern countries but custom mnemonics for many
# historical and colonial entities. Only map cases that have a clear GWNO
# analogue in the TIERS/CShapes registry; leave ambiguous colonies unmapped.
TRADHIST_CODE_OVERRIDES: dict[str, tuple[int, str]] = {
    "AUTHUN": (300, "Austria-Hungary"),
    "CZSK": (315, "Czechoslovakia"),
    "DANTZ": (291, "Danzig"),
    "EDEU": (265, "East Germany"),
    "WDEU": (260, "West Germany"),
    "USSR": (365, "Russia (Soviet Union)"),
    "YUG": (345, "Serbia (Yugoslavia)"),
    "YAR": (678, "Yemen"),
    "YMD": (680, "Yemen People's Republic"),
    "ZANZ": (511, "Zanzibar"),
}


ISO3_GWNO_OVERRIDES: dict[str, tuple[int, str]] = {
    "COD": (490, "Democratic Republic of Congo (Zaire)"),
    "CIV": (437, "Cote d'Ivoire"),
    "CZE": (316, "Czech Republic"),
    "DEU": (255, "Germany (Prussia)"),
    "MMR": (775, "Myanmar (Burma)"),
    "MKD": (343, "Macedonia (FYROM)"),
    "ROU": (360, "Romania"),
    "RUS": (365, "Russia (Soviet Union)"),
    "SRB": (340, "Serbia"),
    "SWZ": (572, "Eswatini (Swaziland)"),
    "TLS": (860, "Timor-Leste"),
    "TUR": (640, "Turkey (Ottoman Empire)"),
    "USA": (2, "United States of America"),
    "VNM": (816, "Vietnam"),
    "YEM": (678, "Yemen"),
}


def _key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.strip().lower())


def _load_cshapes_names() -> pd.DataFrame:
    csh = pd.read_csv(
        CSHAPES_CSV,
        usecols=["cntry_name", "gwcode", "gwsyear", "gweyear"],
    )
    csh = csh.dropna(subset=["cntry_name", "gwcode"])
    csh["gwcode"] = csh["gwcode"].astype(int)
    csh["gwsyear"] = csh["gwsyear"].fillna(0).astype(int)
    csh["gweyear"] = csh["gweyear"].fillna(2099).astype(int)
    csh["canonical_name"] = csh["cntry_name"].map(normalize_name)
    grouped = (
        csh.groupby(["gwcode", "canonical_name"], as_index=False)
        .agg(start_year=("gwsyear", "min"), end_year=("gweyear", "max"))
        .sort_values(["canonical_name", "start_year"])
    )
    return grouped


def build_name_to_gw() -> dict[str, tuple[int, str, str]]:
    """Return lowercased country-name/alias -> (gwno, canonical_name, source)."""
    out: dict[str, tuple[int, str, str]] = {}
    csh = _load_cshapes_names()
    for row in csh.itertuples(index=False):
        out.setdefault(_key(row.canonical_name), (int(row.gwcode), row.canonical_name, "cshapes"))

    for canonical, (gwno, _qid, _start, _end, aliases) in ALIAS_DICT.items():
        if gwno is None:
            continue
        out.setdefault(_key(canonical), (int(gwno), canonical, "wiki_alias"))
        for alias in aliases:
            out.setdefault(_key(alias), (int(gwno), canonical, "wiki_alias"))
    return out


def _read_baci_country_codes() -> pd.DataFrame:
    if not BACI_ZIP.exists():
        return pd.DataFrame(columns=["country_code", "country_name", "country_iso2", "country_iso3"])
    with zipfile.ZipFile(BACI_ZIP) as zf:
        names = [n for n in zf.namelist() if n.startswith("country_codes_") and n.endswith(".csv")]
        if not names:
            return pd.DataFrame(columns=["country_code", "country_name", "country_iso2", "country_iso3"])
        with zf.open(names[0]) as fh:
            return pd.read_csv(fh)


def build_crosswalk() -> pd.DataFrame:
    name_to_gw = build_name_to_gw()
    rows: list[dict[str, object]] = []

    baci = _read_baci_country_codes()
    for row in baci.itertuples(index=False):
        iso3 = str(row.country_iso3).strip().upper() if isinstance(row.country_iso3, str) else ""
        resolved = None
        if iso3 in ISO3_GWNO_OVERRIDES:
            gwno, cname = ISO3_GWNO_OVERRIDES[iso3]
            resolved = (gwno, cname, "iso3_override")
        if resolved is None:
            resolved = name_to_gw.get(_key(row.country_name))
        rows.append(
            {
                "source": "BACI",
                "source_code": int(row.country_code),
                "source_name": row.country_name,
                "iso3": iso3,
                "gwno": resolved[0] if resolved else pd.NA,
                "canonical_name": resolved[1] if resolved else pd.NA,
                "match_source": resolved[2] if resolved else "unresolved",
            }
        )

    # TRADHIST codes are discovered from the local raw file if present. This
    # keeps the crosswalk reproducible without storing another upstream codebook.
    tradhist = DATA_RAW / "TRADHIST_v4.dta"
    tradhist_codes: set[str] = set()
    if tradhist.exists():
        for chunk in pd.read_stata(tradhist, columns=["iso_o", "iso_d"], chunksize=200_000):
            tradhist_codes.update(chunk["iso_o"].dropna().astype(str).str.strip().str.upper())
            tradhist_codes.update(chunk["iso_d"].dropna().astype(str).str.strip().str.upper())
    for code in sorted(c for c in tradhist_codes if c):
        resolved = None
        if code in TRADHIST_CODE_OVERRIDES:
            gwno, cname = TRADHIST_CODE_OVERRIDES[code]
            resolved = (gwno, cname, "tradhist_override")
        elif code in ISO3_GWNO_OVERRIDES:
            gwno, cname = ISO3_GWNO_OVERRIDES[code]
            resolved = (gwno, cname, "iso3_override")
        else:
            baci_hit = baci[baci["country_iso3"].astype(str).str.upper() == code]
            if not baci_hit.empty:
                name = baci_hit.iloc[0]["country_name"]
                resolved = name_to_gw.get(_key(name))

        rows.append(
            {
                "source": "TRADHIST",
                "source_code": code,
                "source_name": pd.NA,
                "iso3": code if len(code) == 3 else pd.NA,
                "gwno": resolved[0] if resolved else pd.NA,
                "canonical_name": resolved[1] if resolved else pd.NA,
                "match_source": resolved[2] if resolved else "unresolved",
            }
        )
    out = pd.DataFrame(rows)
    out = out.drop_duplicates(["source", "source_code"], keep="first")
    return out.sort_values(["source", "source_code"]).reset_index(drop=True)


def load_crosswalk(force: bool = False) -> pd.DataFrame:
    if OUT_CSV.exists() and not force:
        return pd.read_csv(OUT_CSV, dtype={"source_code": str})
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out = build_crosswalk()
    out.to_csv(OUT_CSV, index=False)
    return out


def main() -> int:
    out = load_crosswalk(force=True)
    by_source = out.groupby("source")["gwno"].agg(total="size", resolved="count").reset_index()
    print(f"Wrote {OUT_CSV}")
    for row in by_source.itertuples(index=False):
        print(f"  {row.source}: {row.resolved:,}/{row.total:,} codes resolved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
