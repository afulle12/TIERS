"""Integrate EUSANCT_Dataset_Dyadic into conflict_dyads.csv as T2 events.

Rules:
- sender = US  -> initiator = 'United States of America'
- sender = EU  -> expand to one row per EU member state at that year
- sender = UN  -> drop (analogous 'all UN members' would be uninformative)
- target cname -> mapped to existing conflict_dyads name via (gwno, year) lookup
  with a manual override for cases where the EUSANCT name doesn't match anything
  in the existing dataset
- tier_label = 'T2-Economic/Display', uiw_tier = 2, hostlev = 3
- source = 'EUSANCT'

Outputs:
  - data/processed/conflict_dyads_eus.csv: T2 events extracted from EUSANCT
  - data/processed/conflict_dyads_combined.csv: conflict_dyads.csv + EUSANCT T2 rows
  - output/analysis/eus_mapping_log.csv: per-EUSANCT-row mapping status
"""
from __future__ import annotations

import os
import time

import pandas as pd
from state_system import load_state_system

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
DATA_RAW = os.path.join(ROOT, "data", "raw")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
SRC_CD = os.path.join(DATA_PROCESSED, "conflict_dyads.csv")
SRC_EUS = os.path.join(DATA_RAW, "EUSANCT_Dataset_Dyadic.xls")
OUT_EUS = os.path.join(DATA_PROCESSED, "conflict_dyads_eus.csv")
OUT_EUS_THREATS = os.path.join(DATA_PROCESSED, "eusanct_threat_events.csv")
OUT_COMBINED = os.path.join(DATA_PROCESSED, "conflict_dyads_combined.csv")
LOG = os.path.join(OUT_ANALYSIS, "eus_mapping_log.csv")

# EU membership timeline: gwno -> accession year (during EUSANCT 1989-2015)
EU_ACCESSION = {
    211: 1958,  # Belgium
    212: 1958,  # Luxembourg
    220: 1958,  # France
    260: 1958,  # German Federal Republic (modern Germany; 255 = Germany (Prussia) pre-1945, not EU)
    325: 1958,  # Italy
    210: 1958,  # Netherlands
    390: 1973,  # Denmark
    205: 1973,  # Ireland
    200: 1973,  # United Kingdom (left 2020; in EU throughout EUSANCT window)
    350: 1981,  # Greece
    230: 1986,  # Spain
    235: 1986,  # Portugal
    305: 1995,  # Austria
    375: 1995,  # Finland
    380: 1995,  # Sweden
    290: 2004,  # Poland
    310: 2004,  # Hungary
    316: 2004,  # Czech Republic
    317: 2004,  # Slovakia
    338: 2004,  # Malta
    349: 2004,  # Slovenia
    352: 2004,  # Cyprus
    366: 2004,  # Estonia
    367: 2004,  # Latvia
    368: 2004,  # Lithuania
    355: 2007,  # Bulgaria
    360: 2007,  # Rumania
    344: 2013,  # Croatia
}

# Map: gwno -> 'modern' name used in conflict_dyads (for 1989-2015)
GWNO_NAME_1989_2015 = {
    2: "United States of America",
    20: "Canada",
    31: "Bahamas",
    40: "Cuba",
    41: "Haiti",
    42: "Dominican Republic",
    51: "Jamaica",
    52: "Trinidad and Tobago",
    70: "Mexico",
    80: "Belize",
    90: "Guatemala",
    91: "Honduras",
    92: "El Salvador",
    93: "Nicaragua",
    94: "Costa Rica",
    95: "Panama",
    100: "Colombia",
    101: "Venezuela",
    110: "Guyana",
    130: "Ecuador",
    135: "Peru",
    140: "Brazil",
    145: "Bolivia",
    150: "Paraguay",
    155: "Chile",
    160: "Argentina",
    165: "Uruguay",
    200: "United Kingdom",
    205: "Ireland",
    210: "Netherlands",
    211: "Belgium",
    212: "Luxembourg",
    220: "France",
    225: "Switzerland",
    230: "Spain",
    235: "Portugal",
    255: "Germany (Prussia)",  # pre-1945 only; should not be used 1989-2015
    260: "German Federal Republic",
    265: "German Democratic Republic",  # pre-1990 only
    290: "Poland",
    300: "Austria-Hungary",  # historical
    305: "Austria",
    310: "Hungary",
    315: "Czechoslovakia",  # pre-1993
    316: "Czech Republic",
    317: "Slovakia",
    325: "Italy/Sardinia",
    338: "Malta",
    339: "Albania",
    341: "Montenegro",
    343: "Macedonia (FYROM)",
    344: "Croatia",
    345: "Yugoslavia",  # pre-1992
    346: "Bosnia-Herzegovina",
    347: "Kosovo",
    349: "Slovenia",
    350: "Greece",
    352: "Cyprus",
    355: "Bulgaria",
    359: "Moldova",
    360: "Rumania",
    365: "Russia (Soviet Union)",
    366: "Estonia",
    367: "Latvia",
    368: "Lithuania",
    369: "Ukraine",
    370: "Belarus",
    371: "Armenia",
    372: "Georgia",
    373: "Azerbaijan",
    375: "Finland",
    380: "Sweden",
    385: "Norway",
    390: "Denmark",
    395: "Iceland",
    404: "Guinea-Bissau",
    411: "Equatorial Guinea",
    420: "Gambia",
    432: "Mali",
    433: "Senegal",
    434: "Benin",
    435: "Mauritania",
    436: "Niger",
    437: "Ivory Coast",
    438: "Guinea",
    439: "Burkina Faso",
    450: "Liberia",
    451: "Sierra Leone",
    452: "Ghana",
    461: "Togo",
    471: "Cape Verde",
    475: "Nigeria",
    481: "Gabon",
    482: "Central African Republic",
    483: "Chad",
    484: "Congo",
    490: "Democratic Republic of Congo (Zaire)",
    500: "Uganda",
    501: "Kenya",
    510: "Tanzania",
    511: "Zanzibar",
    516: "Burundi",
    517: "Rwanda",
    520: "Somalia",
    522: "Djibouti",
    530: "Ethiopia",
    531: "Eritrea",
    540: "Angola",
    541: "Mozambique",
    551: "Zambia",
    552: "Zimbabwe",
    553: "Malawi",
    560: "South Africa",
    565: "Namibia",
    570: "Lesotho",
    571: "Botswana",
    572: "Swaziland (Eswatini)",
    580: "Madagascar",
    581: "Comoros",
    590: "Mauritius",
    600: "Morocco",
    615: "Algeria",
    616: "Tunisia",
    620: "Libya",
    625: "Sudan",
    626: "South Sudan",
    630: "Iran (Persia)",
    640: "Turkey (Ottoman Empire)",
    645: "Iraq",
    651: "Egypt",
    652: "Syria",
    660: "Lebanon",
    663: "Jordan",
    666: "Israel",
    670: "Saudi Arabia",
    678: "Yemen (Arab Republic of Yemen)",
    679: "People's Republic of Yemen",
    680: "Yemen",
    690: "Kuwait",
    692: "Bahrain",
    694: "Qatar",
    696: "United Arab Emirates",
    698: "Oman",
    700: "Afghanistan",
    701: "Turkmenistan",
    702: "Tajikistan",
    703: "Kyrgyz Republic",
    704: "Uzbekistan",
    705: "Kazakhstan",
    710: "China",
    711: "Mongolia",
    712: "Taiwan",
    713: "Hong Kong",
    714: "Macao",
    715: "People's Republic of Korea",
    720: "India",
    721: "Pakistan",
    722: "Bangladesh",
    723: "Nepal",
    724: "Bhutan",
    725: "Sri Lanka (Ceylon)",
    726: "Sri Lanka",
    730: "Republic of Korea",
    731: "Japan",
    732: "Korea",
    740: "Democratic Republic of Vietnam",
    741: "Republic of Vietnam",
    742: "Vietnam",
    750: "Malaysia",
    751: "Singapore",
    752: "Brunei",
    760: "Indonesia",
    761: "Timor-Leste",
    770: "Philippines",
    771: "Cambodia (Kampuchea)",
    772: "Laos",
    773: "Myanmar (Burma)",
    800: "Australia",
    801: "Papua New Guinea",
    802: "New Zealand",
    803: "Solomon Islands",
    804: "Vanuatu",
    805: "Fiji",
    810: "Tonga",
    811: "Samoa",
    812: "Tuvalu",
    813: "Nauru",
    814: "Kiribati",
    815: "Marshall Islands",
    816: "Micronesia",
    817: "Palau",
    820: "Hawaii",  # historical
    840: "United States of America",  # duplicate; not used
    850: "Marshall Islands",
    900: "Cuba",  # already
    910: "Panama",
    920: "Haiti",
}


def is_eu_member(gwno: int, year: int) -> bool:
    acc = EU_ACCESSION.get(int(gwno))
    if acc is None:
        return False
    return year >= acc


def name_for(gwno: int) -> str | None:
    return GWNO_NAME_1989_2015.get(int(gwno))


def _state_lookups(states: pd.DataFrame) -> tuple[dict, dict, dict, dict]:
    """Build (year, ccode)->(gwno, name) and (year, gwno)->(ccode, name) lookups with latest fallback."""
    by_cc_yr = {
        (int(r.year), int(r.ccode)): (int(r.gwno), str(r.name))
        for r in states.itertuples(index=False)
    }
    by_cc_latest = {
        int(r.ccode): (int(r.gwno), str(r.name))
        for r in states.sort_values("year").drop_duplicates("ccode", keep="last").itertuples(index=False)
    }
    by_gw_yr = {
        (int(r.year), int(r.gwno)): (int(r.ccode), str(r.name))
        for r in states.itertuples(index=False)
    }
    by_gw_latest = {
        int(r.gwno): (int(r.ccode), str(r.name))
        for r in states.sort_values("year").drop_duplicates("gwno", keep="last").itertuples(index=False)
    }
    return by_cc_yr, by_cc_latest, by_gw_yr, by_gw_latest


def extract_eusanct_dyads(
    eus: pd.DataFrame,
    states: pd.DataFrame,
    mode: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Expand EUSANCT dyad rows into directed state-pair events.

    mode:
      - 'sanction': dyad-years with ``sanction_dyad == 1`` -> uiw_tier=2, source='EUSANCT'
      - 'threat': dyad-years with ``threat_dyad == 1`` and ``sanction_dyad != 1`` -> uiw_tier=1, source='EUSANCT_THREAT'
    """
    if mode == "sanction":
        sub = eus[eus["sanction_dyad"] == 1].copy()
        tier, tier_label, src, basis = 2, "T2-Economic/Display", "EUSANCT", None
    elif mode == "threat":
        sub = eus[(eus["threat_dyad"] == 1) & (eus["sanction_dyad"].fillna(0) != 1)].copy()
        tier, tier_label, src, basis = 1, "T1-Diplomatic Crisis", "EUSANCT_THREAT", "EUSANCT sanction threat"
    else:
        raise ValueError(f"Unknown mode: {mode}")

    by_cc_yr, by_cc_latest, by_gw_yr, by_gw_latest = _state_lookups(states)
    out_rows: list[dict] = []
    log_rows: list[dict] = []

    for _, r in sub.iterrows():
        year = int(r["year"])
        tgt_ccode = int(r["ccodecow"]) if pd.notna(r["ccodecow"]) else None
        sender = r["sender"]
        tgt_name_eus = r.get("cname", "")
        caseid = str(r["caseid"]) if "caseid" in r and pd.notna(r["caseid"]) else ""

        tgt_info = None
        if tgt_ccode is not None:
            tgt_info = by_cc_yr.get((year, tgt_ccode)) or by_cc_latest.get(tgt_ccode)
        if tgt_info is None:
            tgt_name_fallback = name_for(tgt_ccode) if tgt_ccode is not None else None
            if tgt_name_fallback is not None:
                tgt_info = (tgt_ccode, tgt_name_fallback)
        if tgt_info is None:
            log_rows.append({
                "year": year,
                "sender": sender,
                "target_ccode": tgt_ccode,
                "target_eus_name": tgt_name_eus,
                "status": "unmapped_target",
            })
            continue
        tgt_gwno, tgt_name_cd = tgt_info

        if sender == "US":
            us_ccode, us_name = by_gw_yr.get((year, 2)) or by_gw_latest.get(2, (2, "United States of America"))
            if tgt_ccode != us_ccode:
                out_rows.append({
                    "year": year,
                    "initiator": us_name,
                    "target": tgt_name_cd,
                    "initiator_ccode": us_ccode,
                    "target_ccode": tgt_ccode,
                    "initiator_gwno": 2,
                    "target_gwno": tgt_gwno,
                    "uiw_tier": tier,
                    "tier_label": tier_label,
                    "source": src,
                    "t1_basis": basis,
                    "event_ref": f"EUSANCT:{caseid}" if caseid else "EUSANCT",
                })
            log_rows.append({
                "year": year,
                "sender": sender,
                "target_ccode": tgt_ccode,
                "target_eus_name": tgt_name_eus,
                "status": "ok_us",
            })
        elif sender == "EU":
            members_added = 0
            for mem_gwno, acc in EU_ACCESSION.items():
                if year < acc:
                    continue
                mem_info = by_gw_yr.get((year, mem_gwno)) or by_gw_latest.get(mem_gwno)
                if mem_info is None:
                    mem_name = name_for(mem_gwno)
                    if mem_name is None:
                        continue
                    mem_ccode = mem_gwno
                else:
                    mem_ccode, mem_name = mem_info
                if mem_ccode == tgt_ccode:
                    continue
                out_rows.append({
                    "year": year,
                    "initiator": mem_name,
                    "target": tgt_name_cd,
                    "initiator_ccode": mem_ccode,
                    "target_ccode": tgt_ccode,
                    "initiator_gwno": mem_gwno,
                    "target_gwno": tgt_gwno,
                    "uiw_tier": tier,
                    "tier_label": tier_label,
                    "source": src,
                    "t1_basis": basis,
                    "event_ref": f"EUSANCT:{caseid}" if caseid else "EUSANCT",
                })
                members_added += 1
            log_rows.append({
                "year": year,
                "sender": sender,
                "target_ccode": tgt_ccode,
                "target_eus_name": tgt_name_eus,
                "status": f"ok_eu_{members_added}",
            })
        elif sender == "UN":
            log_rows.append({
                "year": year,
                "sender": sender,
                "target_ccode": tgt_ccode,
                "target_eus_name": tgt_name_eus,
                "status": "skipped_un",
            })
        else:
            log_rows.append({
                "year": year,
                "sender": sender,
                "target_ccode": tgt_ccode,
                "target_eus_name": tgt_name_eus,
                "status": "unknown_sender",
            })

    cols = [
        "year", "initiator", "target", "initiator_ccode", "target_ccode",
        "initiator_gwno", "target_gwno", "uiw_tier", "tier_label", "source",
        "t1_basis", "event_ref",
    ]
    df = pd.DataFrame(out_rows, columns=cols) if out_rows else pd.DataFrame(columns=cols)
    df = df.drop_duplicates(subset=["year", "initiator_gwno", "target_gwno", "uiw_tier", "source"])
    return df, pd.DataFrame(log_rows)


def main() -> int:
    t0 = time.time()
    states = load_state_system()
    eus = pd.read_excel(SRC_EUS)
    print(f"EUSANCT raw: {len(eus):,} rows in {time.time()-t0:.1f}s")
    print(f"  sanction_dyad==1 rows: {int((eus['sanction_dyad'] == 1).sum()):,}")
    print(f"  threat_dyad==1 (unimposed) rows: {int(((eus['threat_dyad'] == 1) & (eus['sanction_dyad'] != 1)).sum()):,}")

    t2_df, log_df = extract_eusanct_dyads(eus, states, mode="sanction")
    t1_df, _ = extract_eusanct_dyads(eus, states, mode="threat")
    print(f"\nMapped T2 events (sanction_dyad==1): {len(t2_df):,}")
    print(f"Mapped T1 events (threat_dyad==1, not imposed): {len(t1_df):,}")

    t1_df.to_csv(OUT_EUS_THREATS, index=False)
    print(f"Wrote {OUT_EUS_THREATS}")

    # Preserve conflict_dyads_eus.csv schema expected by downstream callers
    eus_cd = t2_df[["year", "initiator", "target", "initiator_gwno", "target_gwno", "uiw_tier", "tier_label", "source"]].copy()
    eus_cd["hostlev"] = 3
    for c in (
        "conflict_id", "dyad_id", "side_backed", "intensity_level", "D_k",
        "attribution", "selective", "targeted", "corroborated",
        "incompatibility", "territory_name", "region", "n_conflicts_aggregated",
    ):
        eus_cd[c] = ""
    eus_cd["in_conflict"] = True
    if os.path.exists(SRC_CD):
        cd = pd.read_csv(SRC_CD, dtype={"year": int})
        eus_cd = eus_cd[list(cd.columns)]
    eus_cd.to_csv(OUT_EUS, index=False)
    print(f"Wrote {OUT_EUS}")

    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    log_df.to_csv(LOG, index=False)
    print(f"Wrote {LOG}")
    print("\nMapping status counts:")
    print(log_df.status.value_counts().head(10).to_string())

    if os.path.exists(SRC_CD):
        combined = pd.concat([cd, eus_cd], ignore_index=True)
        combined = combined.sort_values(["year", "initiator", "target", "uiw_tier"], kind="stable").reset_index(drop=True)
        combined.to_csv(OUT_COMBINED, index=False)
        print(f"\nWrote {OUT_COMBINED} ({os.path.getsize(OUT_COMBINED)/1e6:.1f} MB, {len(combined):,} rows)")
    print(f"\nTotal runtime: {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
