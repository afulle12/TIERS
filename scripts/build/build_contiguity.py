"""Build a per-dyad contiguity and centroid-distance table from CShapes 2.0.

For each year in the data window, union all active polygons per state to get a
single geometry, then for every directed pair (i, j) record:

  - contiguity_xi    in {0, 0.5, 1}
                       1   = land borders touch (polygons intersect)
                       0.5 = separated by <= 24 nautical miles (~ 0.444 km)
                             maritime adjacency (CShapes default convention)
                       0   = otherwise
  - distance_km      great-circle distance between polygon centroids
  - fma              First-Mover Advantage, [0,1]
                     fma = 1 / (1 + distance_km / d_scale)
                     with d_scale chosen so that a contiguous dyad (Xi >= 1)
                     has fma in [0.6, 1.0] and a non-contiguous, far-apart
                     dyad has fma in [0, 0.1].

Output: data/processed/contiguity_xi.csv with columns
    year, initiator_gwno, target_gwno, contiguity_xi, distance_km, fma

Reads: data/raw/CShapes-2.0.csv
Writes: data/processed/contiguity_xi.csv
"""
from __future__ import annotations

import os
import sys
import warnings
from collections import defaultdict

import numpy as np
import pandas as pd
from shapely import wkt
from shapely.errors import ShapelyError
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")

YEAR_LO, YEAR_HI = 1946, 2019

# Scale for FMA: distance in km at which FMA drops to 0.5
FMA_D_SCALE_KM = 1500.0
# Maritime adjacency threshold in km
MARITIME_KM = 24 * 1.852  # 24 nautical miles


def _strip_srid(wkt_str: str) -> str:
    """Strip the SRID=4326; prefix that CShapes prepends to the_geom."""
    s = wkt_str.strip()
    if s.startswith("SRID="):
        s = s.split(";", 1)[1]
    return s


def load_cshapes() -> pd.DataFrame:
    """Read CShapes 2.0, return a frame with parsed geometry per row."""
    path = os.path.join(DATA_RAW, "CShapes-2.0.csv")
    df = pd.read_csv(
        path,
        usecols=["cntry_name", "gwcode", "gwsyear", "gweyear", "caplong", "caplat", "the_geom"],
    )
    df = df.dropna(subset=["the_geom", "gwcode", "gwsyear", "gweyear"])
    df["gwcode"] = df["gwcode"].astype(int)
    df["gwsyear"] = df["gwsyear"].astype(int)
    df["gweyear"] = df["gweyear"].fillna(YEAR_HI).astype(int)

    def _parse(wkt_str):
        try:
            return wkt.loads(_strip_srid(wkt_str))
        except ShapelyError:
            return None

    df["geom"] = df["the_geom"].apply(_parse)
    df = df[df["geom"].notna()].copy()
    return df


def active_polygons_by_year(cshapes: pd.DataFrame) -> dict:
    """For each year, return a dict {gwcode: union_of_polygons}."""
    out: dict = {}
    for year in range(YEAR_LO, YEAR_HI + 1):
        sel = cshapes[(cshapes["gwsyear"] <= year) & (cshapes["gweyear"] >= year)]
        if sel.empty:
            out[year] = {}
            continue
        by_gw: dict = {}
        for gw, grp in sel.groupby("gwcode"):
            geoms = [g for g in grp["geom"] if g is not None and not g.is_empty]
            if not geoms:
                continue
            try:
                merged = unary_union(geoms)
            except Exception:
                merged = geoms[0]
            if merged.is_empty:
                continue
            by_gw[int(gw)] = merged
        out[year] = by_gw
    return out


def _haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in km between two (lon, lat) points."""
    r = 6371.0088
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return float(2 * r * np.arcsin(np.sqrt(a)))


def _fma_from_distance(km: float) -> float:
    """FMA in [0,1] from great-circle distance."""
    if not np.isfinite(km):
        return 0.0
    return float(1.0 / (1.0 + km / FMA_D_SCALE_KM))


def compute_contiguity_for_year(year: int, by_gw: dict) -> list:
    """For a single year, compute directed (i, j) rows for every live pair."""
    rows = []
    gwcodes = sorted(by_gw.keys())
    centroids = {}
    for gw, geom in by_gw.items():
        c = geom.representative_point()  # always inside the polygon
        centroids[gw] = (c.x, c.y)

    for i in gwcodes:
        gi = by_gw[i]
        ci = centroids[i]
        for j in gwcodes:
            if i == j:
                continue
            gj = by_gw[j]
            cj = centroids[j]
            try:
                touches = gi.intersects(gj) and not gi.touches(gj) is None
            except Exception:
                touches = False
            if gi.intersects(gj):
                xi = 1.0
            else:
                d_km = _haversine_km(ci[0], ci[1], cj[0], cj[1])
                xi = 0.5 if d_km <= MARITIME_KM else 0.0
            d_km = _haversine_km(ci[0], ci[1], cj[0], cj[1])
            fma = _fma_from_distance(d_km)
            rows.append((year, i, j, xi, d_km, fma))
    return rows


def main() -> int:
    out_path = os.path.join(DATA_PROCESSED, "contiguity_xi.csv")

    print("Loading CShapes 2.0...")
    cshapes = load_cshapes()
    print(f"  {len(cshapes):,} geometry rows")

    print(f"Building per-year active polygons for {YEAR_LO}-{YEAR_HI}...")
    by_year = active_polygons_by_year(cshapes)

    print("Computing directed contiguity + distance per year...")
    all_rows: list = []
    n_states = []
    for year in range(YEAR_LO, YEAR_HI + 1):
        by_gw = by_year[year]
        n_states.append(len(by_gw))
        if len(by_gw) < 2:
            continue
        rows = compute_contiguity_for_year(year, by_gw)
        all_rows.extend(rows)
        if (year - YEAR_LO) % 10 == 0:
            print(f"  {year}: {len(by_gw):,} live states -> {len(rows):,} directed pairs")

    df = pd.DataFrame(
        all_rows,
        columns=["year", "initiator_gwno", "target_gwno", "contiguity_xi", "distance_km", "fma"],
    )
    df["contiguity_xi"] = df["contiguity_xi"].astype(np.float32)
    df["distance_km"] = df["distance_km"].astype(np.float32)
    df["fma"] = df["fma"].astype(np.float32)
    df.to_csv(out_path, index=False)
    print(f"\nWrote {len(df):,} directed rows -> {out_path}")
    print(f"  mean live states per year: {np.mean(n_states):.1f}")
    print(f"  Xi=1 (land):    {(df.contiguity_xi == 1.0).sum():,}")
    print(f"  Xi=0.5 (marit): {(df.contiguity_xi == 0.5).sum():,}")
    print(f"  Xi=0 (none):    {(df.contiguity_xi == 0.0).sum():,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
