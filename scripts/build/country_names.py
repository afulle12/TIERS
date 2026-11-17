"""Shared country-name normalization utilities.

Single source of truth for converting legacy "Country, X of" forms to
natural-language "X of Country" forms (e.g. "Korea, Republic of" ->
"Republic of Korea") plus a small set of canonical aliases.

This module is imported by:
  - scripts/build/build_combined_dyads.py
  - scripts/build/refresh_country_registry.py

The rules are:

  1. Strip a leading "Government of " prefix.
  2. Collapse runs of whitespace.
  3. Rewrite "Country, X of" -> "X of Country" (preserving any trailing
     parenthetical), where X is one of: Democratic Republic, People's
     Republic, Republic.
  4. Apply CANONICAL_NAME_OVERRIDES (covers historical / common variants
     that don't fit the comma-pattern rewrite).

These rules are intentionally identical to what was previously duplicated
in build_combined_dyads.py and refresh_country_registry.py.
"""
from __future__ import annotations

import re

GOV_PREFIX_RE = re.compile(r"^Government of\s+")

COMMA_FORM_RE = re.compile(
    r"^(?P<country>[^,]+?),\s+"
    r"(?P<modifier>Democratic Republic|People's Republic|Republic)\s+of"
    r"(?P<paren>\s*\(.*?\))?$"
)

CANONICAL_NAME_OVERRIDES = {
    "Russia": "Russia (Soviet Union)",
    "Soviet Union": "Russia (Soviet Union)",
    "USSR": "Russia (Soviet Union)",
    "Germany": "Germany (Prussia)",
    "Prussia": "Germany (Prussia)",
    "Turkey": "Turkey (Ottoman Empire)",
    "Ottoman Empire": "Turkey (Ottoman Empire)",
    "Yugoslavia": "Serbia (Yugoslavia)",
    "Burma": "Myanmar (Burma)",
    "Zaire": "Democratic Republic of Congo (Zaire)",
    "DR Congo": "Democratic Republic of Congo (Zaire)",
    "DR Congo (Zaire)": "Democratic Republic of Congo (Zaire)",
    "Democratic Republic of Congo": "Democratic Republic of Congo (Zaire)",
    "Kampuchea": "Cambodia (Kampuchea)",
    "Ivory Coast": "Cote d'Ivoire",
    "Czechoslovakia": "Czech Republic",
    "Bosnia": "Bosnia-Herzegovina",
    "Macedonia": "Macedonia (FYROM)",
    "East Timor": "Timor-Leste",
    "Swaziland": "Eswatini (Swaziland)",
}


def _rewrite_comma_form(s: str) -> str:
    """Rewrite 'Country, X of' -> 'X of Country', preserving any trailing parenthetical."""
    m = COMMA_FORM_RE.match(s)
    if not m:
        return s
    country = m.group("country").strip()
    modifier = m.group("modifier")
    paren = (m.group("paren") or "").strip()
    out = f"{modifier} of {country}"
    if paren:
        out = f"{out} {paren}"
    return out


def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return name
    s = name.strip()
    s = GOV_PREFIX_RE.sub("", s)
    s = re.sub(r"\s+", " ", s)
    s = _rewrite_comma_form(s)
    return CANONICAL_NAME_OVERRIDES.get(s, s)
