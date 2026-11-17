"""Build the canonical country-name list for the Wikipedia tier-extraction pipeline.

This is a one-shot helper. It produces `data/processed/wiki_country_canonical.csv`,
which is consumed by:

  - `wiki_filter_candidates.py` (stage 3, broad country+keyword filter)
  - `wiki_aggregate_dyads.py` (stage 7, country name -> GWN resolution)
  - `wiki_extract_llm_t123.py` (stage 6, optional: post-LLM GWN backfill)

Three input sources are unioned:

  1. **CShapes-2.0** (`data/raw/CShapes-2.0.csv`)
       252 unique cntry_name values, with year-ranges (`gwsyear`/`gweyear`)
       per state. Includes historical entities (Prussia, Newfoundland,
       Cape Colony, Victoria, Queensland, Transvaal, Bosnia-Herzegovina,
       Rhodesias, etc.).

  2. **wiki_gwn_map** (`data/processed/wiki_gwn_map.csv`)
       234 QID->GWN rows for modern sovereign states. Provides a
       wikidata_qid backstop for any country CShapes doesn't have.

  3. **Hand-curated alias dict** (encoded in this file, ~60 entries)
       Common synonyms: russia <-> ussr <-> soviet union, myanmar <-> burma,
       sri lanka <-> ceylon, eswatini <-> swaziland, etc.

Output schema (`wiki_country_canonical.csv`):

  canonical_name,aliases,gwcode,wikidata_qid,start_year,end_year,source

where `aliases` is a pipe-separated list of lowercase alternative names
that the filter will treat as equivalent to `canonical_name`. The
filter matches on the *alias* (lowercased, whole-word) and resolves to
the canonical row for GWN/QID lookup.

Run:
  python scripts/build/build_country_canonical.py
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
TMP = ROOT / "tmp"

CSHAPES_CSV = DATA_RAW / "CShapes-2.0.csv"
GWN_MAP_CSV = DATA_PROCESSED / "wiki_gwn_map.csv"
OUT_CSV = DATA_PROCESSED / "wiki_country_canonical.csv"
OUT_META = TMP / "wiki_country_canonical_run.json"

# ---------------------------------------------------------------------------
# Hand-curated alias expansions.
#
# Each key is the canonical_name we want to use. The value is a tuple of:
#   (gwcode_or_None, wikidata_qid_or_None, start_year, end_year, alias_list)
#
# Aliases are case-insensitive, whole-word matched by the filter. We are
# generous on purpose; false positives (matching a name that isn't really
# a country) are caught by the bilateral gate (>=2 countries required)
# and the tier-keyword narrowing.
# ---------------------------------------------------------------------------
ALIAS_DICT: dict[str, tuple[int | None, str | None, int, int, list[str]]] = {
    "Russia": (365, "Q34266", 1547, 2099,
               ["russia", "russian federation", "ussr", "u.s.s.r.", "soviet union", "the soviet union",
                "the russian federation"]),
    "United States of America": (2, "Q30", 1776, 2099,
                                 ["united states", "united states of america", "u.s.", "u.s.a.", "usa", "us",
                                  "the united states", "the united states of america", "america", "american"]),
    "United Kingdom": (200, "Q145", 1707, 2099,
                       ["united kingdom", "u.k.", "uk", "great britain", "britain", "the united kingdom",
                        "british"]),
    "China": (710, "Q148", 1644, 2099,
              ["china", "prc", "people's republic of china", "republic of china", "taiwan", "chinese",
               "mainland china"]),
    "South Korea": (732, "Q884", 1948, 2099,
                    ["south korea", "republic of korea", "rok", "korea (south)", "korea, south",
                     "korean republic"]),
    "North Korea": (731, "Q423", 1948, 2099,
                    ["north korea", "dprk", "democratic people's republic of korea", "korea (north)",
                     "korea, north"]),
    "Japan": (740, "Q17", 660, 2099, ["japan", "japanese"]),
    "Germany": (255, "Q183", 962, 2099,
                ["germany", "federal republic of germany", "west germany", "east germany", "gdr",
                 "frg", "german empire", "weimar germany", "prussia", "german", "the german empire"]),
    "France": (220, "Q142", 843, 2099, ["france", "french", "the french"]),
    "Italy": (325, "Q38", 476, 2099, ["italy", "italian", "sardinia"]),
    "Spain": (230, "Q29", 1479, 2099, ["spain", "spanish"]),
    "Portugal": (235, "Q45", 1139, 2099, ["portugal", "portuguese"]),
    "Netherlands": (210, "Q55", 1581, 2099,
                    ["netherlands", "the netherlands", "holland", "dutch republic"]),
    "Belgium": (211, "Q31", 1830, 2099, ["belgium", "belgian"]),
    "Switzerland": (225, "Q39", 1291, 2099, ["switzerland", "swiss"]),
    "Austria": (240, "Q40", 976, 2099,
                ["austria", "austria-hungary", "habsburg", "austro-hungarian", "austrian"]),
    "Hungary": (310, "Q28", 1867, 2099, ["hungary", "hungarian"]),
    "Poland": (290, "Q36", 1025, 2099, ["poland", "polish", "polish-lithuanian"]),
    "Czechoslovakia": (315, "Q33946", 1918, 1992,
                       ["czechoslovakia", "czech", "czechoslovak"]),
    "Czech Republic": (316, "Q213", 1993, 2099, ["czech republic", "czechia"]),
    "Slovakia": (317, "Q214", 1993, 2099, ["slovakia", "slovak"]),
    "Yugoslavia": (345, "Q36704", 1918, 2003,
                   ["yugoslavia", "yugoslav", "serbia and montenegro"]),
    "Serbia": (340, "Q403", 2006, 2099, ["serbia", "serbian"]),
    "Croatia": (344, "Q224", 1991, 2099, ["croatia", "croatian"]),
    "Slovenia": (349, "Q215", 1991, 2099, ["slovenia", "slovenian"]),
    "Bosnia and Herzegovina": (346, "Q225", 1992, 2099,
                               ["bosnia", "bosnia and herzegovina", "bosnia-herzegovina",
                                "herzegovina", "bosnian"]),
    "Albania": (339, "Q222", 1912, 2099, ["albania", "albanian"]),
    "Greece": (350, "Q41", 1822, 2099, ["greece", "greek"]),
    "Turkey": (640, "Q43", 1299, 2099,
               ["turkey", "ottoman empire", "the ottoman empire", "turkish", "ottoman"]),
    "Egypt": (651, "Q79", 1805, 2099, ["egypt", "egyptian", "united arab republic"]),
    "Libya": (620, "Q1016", 1951, 2099, ["libya", "libyan"]),
    "Tunisia": (616, "Q948", 1956, 2099, ["tunisia", "tunisian"]),
    "Algeria": (615, "Q262", 1962, 2099, ["algeria", "algerian"]),
    "Morocco": (600, "Q1028", 1956, 2099, ["morocco", "moroccan"]),
    "Sudan": (625, "Q1049", 1956, 2099, ["sudan", "sudanese"]),
    "South Sudan": (626, "Q958", 2011, 2099, ["south sudan", "south sudanese"]),
    "Ethiopia": (530, "Q115", 1941, 2099,
                 ["ethiopia", "ethiopian", "abyssinia"]),
    "Somalia": (520, "Q1045", 1960, 2099, ["somalia", "somali"]),
    "Kenya": (501, "Q114", 1963, 2099, ["kenya", "kenyan"]),
    "Tanzania": (510, "Q924", 1964, 2099, ["tanzania", "tanzanian", "tanganyika"]),
    "Uganda": (500, "Q1036", 1962, 2099, ["uganda", "ugandan"]),
    "Rwanda": (517, "Q1037", 1962, 2099, ["rwanda", "rwandan"]),
    "Burundi": (516, "Q967", 1962, 2099, ["burundi", "burundian"]),
    "Congo (DRC)": (490, "Q974", 1960, 2099,
                     ["democratic republic of the congo", "dr congo", "drc", "congo-kinshasa",
                      "zaire", "congo (kinshasa)", "congo"]),
    "Congo (Republic)": (484, "Q971", 1960, 2099,
                         ["republic of the congo", "congo-brazzaville", "congo (brazzaville)",
                          "congo"]),
    "Nigeria": (475, "Q1033", 1960, 2099, ["nigeria", "nigerian"]),
    "Ghana": (452, "Q117", 1957, 2099, ["ghana", "ghanaian", "gold coast"]),
    "Senegal": (433, "Q1031", 1960, 2099, ["senegal", "senegalese"]),
    "Mali": (432, "Q912", 1960, 2099, ["mali", "malian"]),
    "Niger": (436, "Q1032", 1960, 2099, ["niger", "nigerien"]),
    "Chad": (483, "Q657", 1960, 2099, ["chad", "chadian"]),
    "Cameroon": (471, "Q1009", 1960, 2099, ["cameroon", "cameroonian"]),
    "Angola": (540, "Q916", 1975, 2099, ["angola", "angolan"]),
    "Mozambique": (541, "Q1029", 1975, 2099, ["mozambique", "mozambican"]),
    "Zimbabwe": (552, "Q954", 1980, 2099, ["zimbabwe", "zimbabwean", "rhodesia", "southern rhodesia"]),
    "Zambia": (551, "Q953", 1964, 2099, ["zambia", "zambian", "northern rhodesia"]),
    "South Africa": (560, "Q258", 1910, 2099,
                     ["south africa", "south african", "the union of south africa", "the republic of south africa"]),
    "Namibia": (565, "Q1030", 1990, 2099, ["namibia", "namibian", "south west africa"]),
    "Botswana": (571, "Q963", 1966, 2099, ["botswana", "botswanan", "bechuanaland"]),
    "Madagascar": (580, "Q1019", 1960, 2099, ["madagascar", "malagasy"]),
    "India": (750, "Q668", 1947, 2099, ["india", "indian"]),
    "Pakistan": (770, "Q843", 1947, 2099, ["pakistan", "pakistani"]),
    "Bangladesh": (771, "Q902", 1971, 2099, ["bangladesh", "bangladeshi", "east pakistan"]),
    "Sri Lanka": (780, "Q854", 1948, 2099, ["sri lanka", "ceylon", "sri lankan"]),
    "Myanmar": (775, "Q836", 1948, 2099, ["myanmar", "burma", "burmese"]),
    "Thailand": (776, "Q869", 1851, 2099, ["thailand", "thai", "siam"]),
    "Vietnam": (818, "Q881", 1945, 2099, ["vietnam", "vietnamese", "south vietnam", "north vietnam",
                                            "republic of vietnam", "democratic republic of vietnam"]),
    "Cambodia": (811, "Q424", 1953, 2099, ["cambodia", "khmer", "khmer republic", "cambodian"]),
    "Laos": (812, "Q819", 1953, 2099, ["laos", "lao", "laotian"]),
    "Malaysia": (820, "Q833", 1957, 2099, ["malaysia", "malaysian", "malayan", "federation of malaya"]),
    "Singapore": (830, "Q334", 1965, 2099, ["singapore", "singaporean"]),
    "Indonesia": (850, "Q252", 1945, 2099, ["indonesia", "indonesian", "dutch east indies"]),
    "Philippines": (840, "Q928", 1946, 2099, ["philippines", "philippine", "filipino"]),
    "Afghanistan": (700, "Q889", 1747, 2099, ["afghanistan", "afghan"]),
    "Iran": (630, "Q794", 1501, 2099,
             ["iran", "iranian", "persia", "the persian empire"]),
    "Iraq": (645, "Q796", 1932, 2099, ["iraq", "iraqi"]),
    "Syria": (652, "Q858", 1946, 2099, ["syria", "syrian"]),
    "Lebanon": (660, "Q822", 1943, 2099, ["lebanon", "lebanese"]),
    "Jordan": (663, "Q810", 1946, 2099, ["jordan", "jordanian", "transjordan"]),
    "Israel": (666, "Q801", 1948, 2099, ["israel", "israeli"]),
    "Palestine": (667, "Q23792", 1988, 2099, ["palestine", "palestinian", "plo", "palestinian authority"]),
    "Saudi Arabia": (670, "Q851", 1932, 2099, ["saudi arabia", "saudi", "saudi arabian"]),
    "Yemen": (678, "Q805", 1918, 2099, ["yemen", "yemeni", "north yemen", "south yemen"]),
    "Oman": (698, "Q842", 1970, 2099, ["oman", "omani"]),
    "United Arab Emirates": (696, "Q878", 1971, 2099,
                             ["united arab emirates", "uae", "emirates", "the emirates"]),
    "Qatar": (694, "Q846", 1971, 2099, ["qatar", "qatari"]),
    "Bahrain": (692, "Q398", 1971, 2099, ["bahrain", "bahraini"]),
    "Kuwait": (690, "Q817", 1961, 2099, ["kuwait", "kuwaiti"]),
    "Australia": (900, "Q408", 1901, 2099, ["australia", "australian"]),
    "New Zealand": (920, "Q664", 1907, 2099, ["new zealand", "new zealander", "kiwi"]),
    "Canada": (20, "Q16", 1867, 2099, ["canada", "canadian"]),
    "Mexico": (70, "Q96", 1821, 2099, ["mexico", "mexican"]),
    "Cuba": (40, "Q241", 1902, 2099, ["cuba", "cuban"]),
    "Haiti": (41, "Q790", 1804, 2099, ["haiti", "haitian"]),
    "Dominican Republic": (42, "Q786", 1844, 2099, ["dominican republic", "dominican"]),
    "Jamaica": (51, "Q766", 1962, 2099, ["jamaica", "jamaican"]),
    "Guatemala": (90, "Q774", 1838, 2099, ["guatemala", "guatemalan"]),
    "Honduras": (91, "Q783", 1838, 2099, ["honduras", "honduran"]),
    "El Salvador": (92, "Q792", 1841, 2099, ["el salvador", "salvadoran"]),
    "Nicaragua": (93, "Q811", 1838, 2099, ["nicaragua", "nicaraguan"]),
    "Costa Rica": (94, "Q800", 1838, 2099, ["costa rica", "costa rican"]),
    "Panama": (95, "Q804", 1903, 2099, ["panama", "panamanian"]),
    "Colombia": (100, "Q739", 1819, 2099, ["colombia", "colombian"]),
    "Venezuela": (101, "Q717", 1811, 2099, ["venezuela", "venezuelan"]),
    "Ecuador": (130, "Q736", 1830, 2099, ["ecuador", "ecuadorian", "ecuadorean"]),
    "Peru": (135, "Q419", 1821, 2099, ["peru", "peruvian"]),
    "Bolivia": (145, "Q750", 1825, 2099, ["bolivia", "bolivian"]),
    "Brazil": (140, "Q155", 1822, 2099, ["brazil", "brazilian"]),
    "Chile": (155, "Q298", 1818, 2099, ["chile", "chilean"]),
    "Argentina": (160, "Q414", 1816, 2099, ["argentina", "argentine", "argentinian"]),
    "Uruguay": (165, "Q77", 1828, 2099, ["uruguay", "uruguayan"]),
    "Paraguay": (150, "Q733", 1811, 2099, ["paraguay", "paraguayan"]),
    "Belarus": (370, "Q184", 1991, 2099, ["belarus", "belarusian", "byelorussia"]),
    "Ukraine": (369, "Q212", 1991, 2099, ["ukraine", "ukrainian"]),
    "Moldova": (359, "Q217", 1991, 2099, ["moldova", "moldovan"]),
    "Georgia": (372, "Q230", 1991, 2099, ["georgia", "georgian"]),
    "Armenia": (371, "Q399", 1991, 2099, ["armenia", "armenian"]),
    "Azerbaijan": (373, "Q227", 1991, 2099, ["azerbaijan", "azerbaijani"]),
    "Kazakhstan": (705, "Q232", 1991, 2099, ["kazakhstan", "kazakh", "kazakhstani"]),
    "Uzbekistan": (704, "Q265", 1991, 2099, ["uzbekistan", "uzbek"]),
    "Turkmenistan": (701, "Q874", 1991, 2099, ["turkmenistan", "turkmen"]),
    "Kyrgyzstan": (703, "Q813", 1991, 2099, ["kyrgyzstan", "kyrgyz", "kirghiz", "kirgizia"]),
    "Tajikistan": (702, "Q863", 1991, 2099, ["tajikistan", "tajik"]),
    "Mongolia": (712, "Q711", 1924, 2099, ["mongolia", "mongolian"]),
    "Taiwan": (713, "Q865", 1949, 2099, ["taiwan", "taiwanese", "republic of china"]),
    "Romania": (360, "Q218", 1859, 2099, ["romania", "romanian", "rumania"]),
    "Bulgaria": (355, "Q219", 1878, 2099, ["bulgaria", "bulgarian"]),
    "Finland": (375, "Q33", 1917, 2099, ["finland", "finnish"]),
    "Sweden": (380, "Q34", 1523, 2099, ["sweden", "swedish"]),
    "Norway": (385, "Q20", 1905, 2099, ["norway", "norwegian"]),
    "Denmark": (390, "Q35", 1814, 2099, ["denmark", "danish"]),
    "Iceland": (395, "Q189", 1944, 2099, ["iceland", "icelandic"]),
    "Ireland": (205, "Q27", 1922, 2099, ["ireland", "irish", "republic of ireland"]),
    "Estonia": (366, "Q191", 1991, 2099, ["estonia", "estonian"]),
    "Latvia": (367, "Q211", 1991, 2099, ["latvia", "latvian"]),
    "Lithuania": (368, "Q37", 1991, 2099, ["lithuania", "lithuanian"]),
    "Argentina": (160, "Q414", 1816, 2099, ["argentina", "argentine", "argentinian"]),
    "Bahrain": (692, "Q398", 1971, 2099, ["bahrain", "bahraini"]),
    "Barbados": (53, "Q244", 1966, 2099, ["barbados", "barbadian"]),
    "Botswana": (571, "Q963", 1966, 2099, ["botswana", "botswanan", "bechuanaland"]),
    "Burkina Faso": (439, "Q965", 1960, 2099, ["burkina faso", "burkinabe", "upper volta"]),
    "Burundi": (516, "Q967", 1962, 2099, ["burundi", "burundian"]),
    "Cape Verde": (402, "Q1011", 1975, 2099, ["cape verde", "cabo verde", "cape verdian"]),
    "Central African Republic": (482, "Q929", 1960, 2099,
                                  ["central african republic", "car"]),
    "Comoros": (581, "Q970", 1975, 2099, ["comoros", "comorian"]),
    "Congo (DRC)": (490, "Q974", 1960, 2099,
                     ["democratic republic of the congo", "dr congo", "drc", "congo-kinshasa",
                      "zaire", "congo (kinshasa)", "congo"]),
    "Djibouti": (522, "Q977", 1977, 2099, ["djibouti", "djiboutian", "french somaliland"]),
    "Equatorial Guinea": (420, "Q983", 1968, 2099, ["equatorial guinea", "equatoguinean"]),
    "Eritrea": (531, "Q986", 1993, 2099, ["eritrea", "eritrean"]),
    "Eswatini": (572, "Q1050", 1968, 2099, ["eswatini", "swaziland"]),
    "Fiji": (950, "Q712", 1970, 2099, ["fiji", "fijian"]),
    "Gabon": (481, "Q1000", 1960, 2099, ["gabon", "gabonese"]),
    "Gambia": (420, "Q1005", 1965, 2099, ["gambia", "gambian"]),
    "Guinea": (438, "Q1006", 1958, 2099, ["guinea", "guinean"]),
    "Guinea-Bissau": (404, "Q1007", 1974, 2099, ["guinea-bissau", "guinean"]),
    "Ivory Coast": (437, "Q1008", 1960, 2099,
                    ["ivory coast", "cote d'ivoire", "cote d ivoire", "ivorian"]),
    "Lesotho": (570, "Q1013", 1966, 2099, ["lesotho", "basutoland"]),
    "Liberia": (450, "Q1014", 1847, 2099, ["liberia", "liberian"]),
    "Malawi": (553, "Q1020", 1964, 2099, ["malawi", "malawian", "nyasaland"]),
    "Maldives": (781, "Q826", 1965, 2099, ["maldives", "maldivian"]),
    "Mali": (432, "Q912", 1960, 2099, ["mali", "malian"]),
    "Mauritania": (435, "Q1025", 1960, 2099, ["mauritania", "mauritanian"]),
    "Mauritius": (590, "Q1027", 1968, 2099, ["mauritius", "mauritian"]),
    "Papua New Guinea": (910, "Q691", 1975, 2099, ["papua new guinea", "png"]),
    "Sao Tome and Principe": (403, "Q1039", 1975, 2099, ["sao tome and principe"]),
    "Senegal": (433, "Q1031", 1960, 2099, ["senegal", "senegalese"]),
    "Seychelles": (591, "Q1042", 1976, 2099, ["seychelles", "seychellois"]),
    "Sierra Leone": (451, "Q1034", 1961, 2099, ["sierra leone", "sierra leonean"]),
    "Solomon Islands": (940, "Q685", 1978, 2099, ["solomon islands", "solomon islander"]),
    "Somalia": (520, "Q1045", 1960, 2099, ["somalia", "somali"]),
    "South Africa": (560, "Q258", 1910, 2099,
                     ["south africa", "south african", "the union of south africa", "the republic of south africa"]),
    "Sudan": (625, "Q1049", 1956, 2099, ["sudan", "sudanese"]),
    "Suriname": (115, "Q730", 1975, 2099, ["suriname", "surinamese", "surinam"]),
    "Togo": (461, "Q945", 1960, 2099, ["togo", "togolese"]),
    "Tonga": (955, "Q678", 1970, 2099, ["tonga", "tongan"]),
    "Trinidad and Tobago": (52, "Q754", 1962, 2099, ["trinidad and tobago", "trinidadian"]),
    "Tuvalu": (947, "Q672", 1978, 2099, ["tuvalu", "tuvaluan"]),
    "Vanuatu": (935, "Q686", 1980, 2099, ["vanuatu", "ni-vanuatu", "new hebrides"]),
    "Western Samoa": (990, "Q683", 1962, 2099, ["samoa", "samoan", "western samoa"]),
    "North Macedonia": (343, "Q221", 1991, 2099,
                        ["north macedonia", "macedonia", "republic of north macedonia",
                         "fyr macedonia", "macedonian"]),
    "Kosovo": (347, "Q3028", 2008, 2099, ["kosovo", "kosovar"]),
    "Montenegro": (341, "Q236", 2006, 2099, ["montenegro", "montenegrin"]),
    "Timor-Leste": (860, "Q574", 2002, 2099, ["timor-leste", "east timor"]),
    "Aland Islands": (2901, "Q5689", 1921, 2099, ["aland islands", "aland"]),
    "Denmark": (390, "Q35", 1814, 2099, ["denmark", "danish"]),
    "France": (220, "Q142", 843, 2099, ["france", "french", "the french"]),
    "Greenland": (3951, "Q223", 1814, 2099, ["greenland", "greenlandic"]),
    "French Guiana": (3952, "Q3769", 1814, 2099, ["french guiana"]),
    "Guadeloupe": (3953, "Q17012", 1814, 2099, ["guadeloupe"]),
    "Martinique": (3954, "Q17054", 1814, 2099, ["martinique"]),
    "New Caledonia": (3960, "Q33788", 1853, 2099, ["new caledonia"]),
    "French Polynesia": (3961, "Q30971", 1843, 2099, ["french polynesia", "tahiti"]),
    "Puerto Rico": (3956, "Q1183", 1898, 2099, ["puerto rico", "puerto rican"]),
    "Alaska": (3962, "Q797", 1867, 1959, ["alaska", "alaskan"]),
    "Hawaii": (3963, "Q782", 1898, 1959, ["hawaii", "hawaiian"]),
    "Newfoundland": (3964, "Q1035", 1907, 1949, ["newfoundland"]),
    "Bosnia-Herzegovina": (346, "Q225", 1992, 2099,
                           ["bosnia and herzegovina", "bosnia-herzegovina", "herzegovina", "bosnian"]),
}


# ---------------------------------------------------------------------------
# Load + assemble
# ---------------------------------------------------------------------------

def _load_cshapes() -> dict[tuple[str, int], dict]:
    """Return {(lowercase cntry_name, gwcode): {start_year, end_year, name}}."""
    out: dict[tuple[str, int], dict] = {}
    if not CSHAPES_CSV.exists():
        return out
    csv.field_size_limit(sys.maxsize)
    with open(CSHAPES_CSV, "r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            try:
                gw = int(float(r["gwcode"]))
            except (KeyError, ValueError):
                continue
            try:
                start = int(r["gwsyear"])
            except (KeyError, ValueError):
                start = 1816
            try:
                end = int(r["gweyear"])
            except (KeyError, ValueError):
                end = 2099
            name = (r.get("cntry_name") or "").strip()
            if not name:
                continue
            key = (name.lower(), gw)
            if key not in out:
                out[key] = {"start_year": start, "end_year": end, "name": name}
    return out


def _load_gwn_map() -> dict[str, dict]:
    """Return {lowercase country_name: {gwcode, qid, name}}."""
    out: dict[str, dict] = {}
    if not GWN_MAP_CSV.exists():
        return out
    with open(GWN_MAP_CSV, "r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            gw = (r.get("gwno") or "").strip()
            qid = (r.get("wikidata_qid") or "").strip()
            name = (r.get("country_name") or "").strip()
            if not name or not gw:
                continue
            try:
                gw_i = int(gw)
            except ValueError:
                continue
            out[name.lower()] = {"gwcode": gw_i, "qid": qid, "name": name}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cshapes", default=str(CSHAPES_CSV))
    parser.add_argument("--gwn-map", default=str(GWN_MAP_CSV))
    parser.add_argument("--out", default=str(OUT_CSV))
    parser.add_argument("--meta-out", default=str(OUT_META))
    args = parser.parse_args()

    print("[1/6] Loading CShapes...")
    cshapes = _load_cshapes()
    print(f"        {len(cshapes):,} (name, gwcode) entries from CShapes")
    print("[2/6] Loading wiki_gwn_map...")
    gwn_map = _load_gwn_map()
    print(f"        {len(gwn_map):,} entries from wiki_gwn_map")
    print("[3/6] Loading hand-curated alias dict...")
    print(f"        {len(ALIAS_DICT):,} canonical entries in alias dict")
    print("[4/6] Building canonical rows from alias dict...")
    rows: list[dict] = []
    seen_keys: set[tuple[str, int]] = set()
    alias_coverage: dict[str, set[str]] = {}
    for canonical, (gw, qid, start, end, aliases) in ALIAS_DICT.items():
        # Drop the redundant literal canonical from the alias list (we will
        # add it as the first alias for ease of matching).
        aliases_clean = sorted(set(a.lower().strip() for a in aliases))
        key = (canonical.lower(), gw or -1)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        rows.append(
            {
                "canonical_name": canonical,
                "aliases": "|".join([canonical.lower()] + aliases_clean),
                "gwcode": gw if gw is not None else "",
                "wikidata_qid": qid or "",
                "start_year": start,
                "end_year": end,
                "source": "alias_dict",
            }
        )
        alias_coverage[canonical] = set(aliases_clean)
    print(f"        {len(rows):,} canonical rows from alias dict")

    print("[5/6] Augmenting with CShapes entries not yet in alias dict...")
    added_cshapes = 0
    for (name_lc, gw), meta in cshapes.items():
        key = (name_lc, gw)
        if key in seen_keys:
            continue
        # If the canonical_name matches an existing one, merge.
        merged = False
        for r in rows:
            if r["canonical_name"].lower() == name_lc:
                r["start_year"] = min(r["start_year"], meta["start_year"])
                r["end_year"] = max(r["end_year"], meta["end_year"])
                merged = True
                break
        if merged:
            continue
        seen_keys.add(key)
        rows.append(
            {
                "canonical_name": meta["name"],
                "aliases": name_lc,
                "gwcode": gw,
                "wikidata_qid": "",
                "start_year": meta["start_year"],
                "end_year": meta["end_year"],
                "source": "cshapes",
            }
        )
        added_cshapes += 1
    print(f"        {added_cshapes:,} additional rows from CShapes")

    print("[6/6] Augmenting with wiki_gwn_map entries not yet covered...")
    added_gwn = 0
    for name_lc, meta in gwn_map.items():
        key = (name_lc, meta["gwcode"])
        if key in seen_keys:
            continue
        merged = False
        for r in rows:
            if r["canonical_name"].lower() == name_lc:
                if r["wikidata_qid"] == "" and meta["qid"]:
                    r["wikidata_qid"] = meta["qid"]
                merged = True
                break
        if merged:
            continue
        seen_keys.add(key)
        rows.append(
            {
                "canonical_name": meta["name"],
                "aliases": name_lc,
                "gwcode": meta["gwcode"],
                "wikidata_qid": meta["qid"],
                "start_year": 1816,
                "end_year": 2099,
                "source": "wiki_gwn_map",
            }
        )
        added_gwn += 1
    print(f"        {added_gwn:,} additional rows from wiki_gwn_map")

    # Sort: modern sovereigns first (gwcode present + end_year >= 2020),
    # then by canonical_name.
    rows.sort(key=lambda r: (-(1 if (r["end_year"] >= 2020 and r["gwcode"] != "") else 0), r["canonical_name"].lower()))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["canonical_name", "aliases", "gwcode", "wikidata_qid", "start_year", "end_year", "source"],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"\nWrote {out_path} ({len(rows):,} rows)")

    n_with_gw = sum(1 for r in rows if r["gwcode"] != "")
    n_modern = sum(1 for r in rows if r["end_year"] >= 2020 and r["gwcode"] != "")
    n_with_qid = sum(1 for r in rows if r["wikidata_qid"] != "")
    meta = {
        "n_rows": len(rows),
        "n_with_gwcode": n_with_gw,
        "n_modern_sovereigns": n_modern,
        "n_with_qid": n_with_qid,
        "n_from_alias_dict": sum(1 for r in rows if r["source"] == "alias_dict"),
        "n_from_cshapes_only": sum(1 for r in rows if r["source"] == "cshapes"),
        "n_from_gwn_only": sum(1 for r in rows if r["source"] == "wiki_gwn_map"),
        "rows": [r["canonical_name"] for r in rows],
    }
    meta_path = Path(args.meta_out)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)
    print(f"Metadata -> {meta_path}")
    print()
    print(f"Summary:")
    print(f"  total canonical rows:   {len(rows):,}")
    print(f"  with GWN code:          {n_with_gw:,}")
    print(f"  modern sovereigns:      {n_modern:,}")
    print(f"  with Wikidata QID:      {n_with_qid:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
