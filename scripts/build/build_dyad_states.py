"""Build the dyad-year state table: one tier per pair of existing states per year.

This replaces the model path through `build_combined_dyads.py` and
`build_t0_dyads.py` (proposal sections 2.1, 2.2 and 2.4).

Inputs
------
  data/processed/mid_dyad_events.csv   T1, T4, T5 from MID 5.0 (build_mid_dyads.py)
  data/raw/T3_broad_v26_1.csv          T3 proxy support, UCDP, supporter -> host
  data/raw/T4_interstate_v26_1.csv     T4 interstate armed conflict, UCDP
  data/processed/conflict_dyads_eus.csv  T2 sanctions, EUSANCT, sender -> target
  data/processed/state_system.csv      which states exist in which year

Rules
-----
- Population. A directed row exists for every ordered pair of states that are
  both members of the state system in that year. A state with no recorded
  event is still present; a state that did not exist is not.
- Highest tier. When several events fall in one directed dyad-year, the
  highest tier is the state of that direction. Every event is kept, with its
  source, in the events table.
- Shared tier. `uiw_tier` is the higher of the two directions, because one
  state is enough to start a conflict. `directed_tier` keeps what the row's
  own initiator did, so the model can still ask which side moved.
- Duration. `d_k_years` counts the years the pair has already spent at its
  current shared tier (0 in the first year).
- Coverage. `unobserved_tiers` marks the tiers with no source in that year
  (`source_coverage.py`). Before 1989 there is no sanctions source, so a
  recorded T0 or T1 then means "no sanctions data", not "no sanctions".
- T1 basis. `t1_basis` says what a shared T1 rests on.

Outputs
-------
  data/processed/dyad_events.csv       every contributing event, with source
  data/processed/dyad_states.parquet   the resolved directed dyad-year grid
  output/analysis/dyad_states_dropped.csv  events lost to the membership filter
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
from source_coverage import unobserved_bitmask
from state_system import cow_to_gw, load_state_system

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
MID_EVENTS_CSV = os.path.join(DATA_PROCESSED, "mid_dyad_events.csv")
T3_CSV = os.path.join(DATA_RAW, "T3_broad_v26_1.csv")
T4_INTERSTATE_CSV = os.path.join(DATA_RAW, "T4_interstate_v26_1.csv")
EUS_CSV = os.path.join(DATA_PROCESSED, "conflict_dyads_eus.csv")
T1_UNION_CSV = os.path.join(DATA_PROCESSED, "t1_union_events.csv")
MCT_CSV = os.path.join(DATA_RAW, "t1_sources", "mct_dataset_v09.csv")
OUT_EVENTS = os.path.join(DATA_PROCESSED, "dyad_events.csv")
OUT_STATES = os.path.join(DATA_PROCESSED, "dyad_states.parquet")
OUT_DROPPED = os.path.join(OUT_ANALYSIS, "dyad_states_dropped.csv")

YEAR_LO, YEAR_HI = 1946, 2014

TIER_LABELS = {
    0: "T0-No Conflict/Peace",
    1: "T1-Diplomatic Crisis",
    2: "T2-Economic Coercion",
    3: "T3-Proxy/Indirect Military",
    4: "T4-Limited Military",
    5: "T5-Strategic War",
}
EVENT_COLUMNS = [
    "year", "initiator", "target", "initiator_ccode", "target_ccode",
    "initiator_gwno", "target_gwno", "uiw_tier", "tier_label", "source",
    "attribution", "event_ref", "t1_basis",
]

# What a T1 row rests on (proposal section 2.8). Every T1 source added later
# gets its own label here, so T1 can be reported by source.
T1_BASIS_MID = {2: "MID threat", 3: "MID display", 4: "MID force, target unconfirmed",
                5: "MID force, target unconfirmed"}


def _attach_by_gwno(ev: pd.DataFrame, states: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map GW-keyed events onto system members; return `(kept, dropped)`.

    Some upstream rows carry a COW code where a GW number is expected (Yemen
    679, Yugoslavia 345 after 2006), so codes pass through `cow_to_gw` first.
    The two systems agree everywhere else, which makes this a no-op for them.
    """
    ev = ev.copy()
    for col in ("initiator_gwno", "target_gwno"):
        ev[col] = [cow_to_gw(c, y) for c, y in zip(ev[col], ev["year"], strict=True)]
    key = states[["year", "gwno", "ccode", "name"]]
    out = ev.merge(
        key.rename(columns={"gwno": "initiator_gwno", "ccode": "initiator_ccode", "name": "initiator"}),
        on=["year", "initiator_gwno"], how="left",
    ).merge(
        key.rename(columns={"gwno": "target_gwno", "ccode": "target_ccode", "name": "target"}),
        on=["year", "target_gwno"], how="left",
    )
    member = out["initiator_ccode"].notna() & out["target_ccode"].notna()
    member &= out["initiator_gwno"] != out["target_gwno"]
    kept = out[member].copy()
    kept["initiator_ccode"] = kept["initiator_ccode"].astype(int)
    kept["target_ccode"] = kept["target_ccode"].astype(int)
    return kept, out[~member].copy()


def load_events(states: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Collect every directed event from the four sources."""
    frames, dropped = [], []

    mid = pd.read_csv(MID_EVENTS_CSV)
    mid["attribution"] = np.nan
    mid["event_ref"] = "MID:" + mid["dispnum"].astype(str)
    mid["t1_basis"] = np.where(mid["uiw_tier"] == 1, mid["hostlev"].map(T1_BASIS_MID), None)
    frames.append(mid[EVENT_COLUMNS])

    t3 = pd.read_csv(T3_CSV).dropna(subset=["supporter_gwno", "host_gwno"])
    t3 = pd.DataFrame({
        "year": t3["year"].astype(int),
        "initiator_gwno": t3["supporter_gwno"].astype(int),
        "target_gwno": t3["host_gwno"].astype(int),
        "uiw_tier": 3,
        "source": "UCDP_T3",
        "attribution": t3["attribution"].astype(float),
        "event_ref": "UCDP:" + t3["conflict_id"].astype(str),
    })
    kept, drop = _attach_by_gwno(t3, states)
    frames.append(kept)
    dropped.append(drop.assign(reason="T3 non-member or self"))

    t4 = pd.read_csv(T4_INTERSTATE_CSV).dropna(subset=["initiator_gwno", "target_gwno"])
    t4 = pd.DataFrame({
        "year": t4["year"].astype(int),
        "initiator_gwno": t4["initiator_gwno"].astype(int),
        "target_gwno": t4["target_gwno"].astype(int),
        "uiw_tier": 4,
        "source": "UCDP_INTERSTATE",
        "attribution": np.nan,
        "event_ref": "UCDP:" + t4["conflict_id"].astype(str),
    })
    kept, drop = _attach_by_gwno(t4, states)
    frames.append(kept)
    dropped.append(drop.assign(reason="UCDP interstate non-member"))

    eus = pd.read_csv(EUS_CSV).dropna(subset=["initiator_gwno", "target_gwno"])
    eus = pd.DataFrame({
        "year": eus["year"].astype(int),
        "initiator_gwno": eus["initiator_gwno"].astype(int),
        "target_gwno": eus["target_gwno"].astype(int),
        "uiw_tier": 2,
        "source": "EUSANCT",
        "attribution": np.nan,
        "event_ref": "EUSANCT",
    })
    kept, drop = _attach_by_gwno(eus, states)
    frames.append(kept)
    dropped.append(drop.assign(reason="EUSANCT non-member or self"))

    if os.path.exists(T1_UNION_CSV):
        t1 = pd.read_csv(T1_UNION_CSV)
        base_t3 = pd.concat(frames, ignore_index=True, sort=False)
        base_t3 = base_t3[base_t3["uiw_tier"] >= 3]
        t3_pairs = set(zip(
            base_t3["year"].astype(int),
            base_t3[["initiator_ccode", "target_ccode"]].min(axis=1).astype(int),
            base_t3[["initiator_ccode", "target_ccode"]].max(axis=1).astype(int),
            strict=True,
        ))
        is_icb = t1["source"] == "ICB"
        if is_icb.any():
            icb_keys = list(zip(
                t1["year"].astype(int),
                t1[["initiator_ccode", "target_ccode"]].min(axis=1).astype(int),
                t1[["initiator_ccode", "target_ccode"]].max(axis=1).astype(int),
                strict=True,
            ))
            icb_ge_t3 = is_icb & pd.Series([k in t3_pairs for k in icb_keys], index=t1.index)
            if icb_ge_t3.any():
                icb_drop = t1.loc[icb_ge_t3, ["year", "initiator_ccode", "target_ccode", "source"]].copy()
                icb_drop["reason"] = "ICB filtered: pair already >= T3"
                dropped.append(icb_drop)
                t1 = t1.loc[~icb_ge_t3].copy()
        frames.append(t1[EVENT_COLUMNS])

    events = pd.concat(frames, ignore_index=True, sort=False)
    if "t1_basis" not in events.columns:
        events["t1_basis"] = None
    events["tier_label"] = events["uiw_tier"].map(TIER_LABELS)
    events = events[EVENT_COLUMNS].sort_values(
        ["year", "initiator", "target", "uiw_tier", "source"]
    ).reset_index(drop=True)
    return events, pd.concat(dropped, ignore_index=True, sort=False)


def member_grid(states: pd.DataFrame, year_lo: int = YEAR_LO, year_hi: int = YEAR_HI) -> pd.DataFrame:
    """Every ordered pair of states that both exist in a year."""
    s = states[(states.year >= year_lo) & (states.year <= year_hi)][["year", "ccode", "gwno", "name"]]
    a = s.rename(columns={"ccode": "initiator_ccode", "gwno": "initiator_gwno", "name": "initiator"})
    b = s.rename(columns={"ccode": "target_ccode", "gwno": "target_gwno", "name": "target"})
    grid = a.merge(b, on="year")
    return grid[grid["initiator_ccode"] != grid["target_ccode"]].reset_index(drop=True)


def _join_sources(values: pd.Series) -> str:
    return "_".join(sorted(set(values)))


def resolve_states(grid: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Apply the highest-tier and shared-tier rules to the member grid."""
    key = ["year", "initiator_ccode", "target_ccode"]
    ev = events[(events.year >= grid.year.min()) & (events.year <= grid.year.max())]

    directed = ev.groupby(key, as_index=False)["uiw_tier"].max().rename(columns={"uiw_tier": "directed_tier"})
    attribution = (
        ev[ev.uiw_tier == 3].groupby(key, as_index=False)["attribution"].max()
    )

    out = grid.merge(directed, on=key, how="left").merge(attribution, on=key, how="left")
    out["directed_tier"] = out["directed_tier"].fillna(0).astype(int)

    reverse = out[["year", "initiator_ccode", "target_ccode", "directed_tier"]].rename(columns={
        "initiator_ccode": "target_ccode", "target_ccode": "initiator_ccode",
        "directed_tier": "reverse_tier",
    })
    out = out.merge(reverse, on=key, how="left")
    out["reverse_tier"] = out["reverse_tier"].fillna(0).astype(int)
    out["uiw_tier"] = out[["directed_tier", "reverse_tier"]].max(axis=1).astype(int)
    out["tier_label"] = out["uiw_tier"].map(TIER_LABELS)
    out["in_conflict"] = out["uiw_tier"] > 0

    # Sources of the events that set the shared tier, from either direction.
    lo = ev[["initiator_ccode", "target_ccode"]].min(axis=1)
    hi = ev[["initiator_ccode", "target_ccode"]].max(axis=1)
    pair_ev = ev.assign(cc_lo=lo, cc_hi=hi)
    top = pair_ev.groupby(["year", "cc_lo", "cc_hi"])["uiw_tier"].transform("max")
    src = (
        pair_ev[pair_ev["uiw_tier"] == top]
        .groupby(["year", "cc_lo", "cc_hi"])["source"].agg(_join_sources)
        .rename("source").reset_index()
    )
    out["cc_lo"] = out[["initiator_ccode", "target_ccode"]].min(axis=1)
    out["cc_hi"] = out[["initiator_ccode", "target_ccode"]].max(axis=1)
    out = out.merge(src, on=["year", "cc_lo", "cc_hi"], how="left")
    out["source"] = out["source"].fillna("INFERRED")

    # What a shared T1 rests on, from either direction.
    t1 = pair_ev[(pair_ev["uiw_tier"] == 1) & pair_ev["t1_basis"].notna()]
    basis = (
        t1.groupby(["year", "cc_lo", "cc_hi"])["t1_basis"].agg(lambda v: "; ".join(sorted(set(v))))
        .rename("t1_basis").reset_index()
    )
    out = out.merge(basis, on=["year", "cc_lo", "cc_hi"], how="left")
    out["t1_basis"] = out["t1_basis"].where(out["uiw_tier"] == 1, None)

    # Tiers with no source in this year (bit u set = tier u unobserved). A
    # dyad recorded below such a tier may really be at it.
    out["unobserved_tiers"] = out["year"].map({y: unobserved_bitmask(int(y)) for y in out["year"].unique()}).astype(int)

    # Attribution only modifies proxy conflict; elsewhere it is inactive.
    out["attribution"] = np.where(out["uiw_tier"] == 3, out["attribution"].fillna(0.0), 0.0)

    out = out.sort_values(["cc_lo", "cc_hi", "initiator_ccode", "year"]).reset_index(drop=True)
    out["d_k_years"] = _years_at_current_tier(out)
    out = out.drop(columns=["cc_lo", "cc_hi"])

    cols = [
        "year", "initiator", "target", "initiator_gwno", "target_gwno",
        "initiator_ccode", "target_ccode", "uiw_tier", "directed_tier", "reverse_tier",
        "tier_label", "source", "t1_basis", "unobserved_tiers", "attribution", "d_k_years", "in_conflict",
    ]
    out = out[cols].sort_values(["year", "initiator", "target"]).reset_index(drop=True)
    if out.duplicated(["year", "initiator_ccode", "target_ccode"]).any():
        raise ValueError("dyad_states: duplicate directed dyad-year")
    if out.duplicated(["year", "initiator", "target"]).any():
        raise ValueError("dyad_states: duplicate directed dyad-year by name")
    return out


def _years_at_current_tier(df: pd.DataFrame) -> np.ndarray:
    """Years already spent at the current shared tier, per directed pair.

    `df` must be sorted by directed pair then year. A run restarts when the
    tier changes or when the pair skips a calendar year.
    """
    pair = df["initiator_ccode"].to_numpy() * 100000 + df["target_ccode"].to_numpy()
    year = df["year"].to_numpy()
    tier = df["uiw_tier"].to_numpy()
    new_run = np.ones(len(df), dtype=bool)
    same = (pair[1:] == pair[:-1]) & (year[1:] == year[:-1] + 1) & (tier[1:] == tier[:-1])
    new_run[1:] = ~same
    run_id = np.cumsum(new_run)
    run_start = pd.Series(year).groupby(run_id).transform("min").to_numpy()
    return (year - run_start).astype(float)


def check_mct_coverage(
    dyad_states: pd.DataFrame,
    mct_path: str = MCT_CSV,
) -> dict[str, int]:
    """Validate that in-window Sechser MCT episodes land at uiw_tier >= 1.

    Returns counts for `(in_window_dyad_years, episodes_checked, dyad_years_at_t1_plus, missed)`.
    """
    mct = pd.read_csv(mct_path, usecols=["mct_code", "ccode_a", "ccode_b", "year"])
    mct = mct[(mct["year"] >= YEAR_LO) & (mct["year"] <= YEAR_HI)].copy()
    state_tiers = dyad_states.set_index(["year", "initiator_ccode", "target_ccode"])["uiw_tier"]

    checked = 0
    matched = 0
    missed_codes: list[str] = []
    ep_ok: dict[str, bool] = {}
    for r in mct.itertuples(index=False):
        key = (int(r.year), int(r.ccode_a), int(r.ccode_b))
        if key not in state_tiers.index:
            continue
        checked += 1
        tier = int(state_tiers.loc[key])
        ok = tier >= 1
        ep_ok[r.mct_code] = ep_ok.get(r.mct_code, False) or ok
        if ok:
            matched += 1
        else:
            missed_codes.append(f"{r.mct_code}({r.year}:{r.ccode_a}-{r.ccode_b})")
    return {
        "in_window_dyad_years": checked,
        "episodes_checked": len(ep_ok),
        "episodes_at_t1_plus": sum(ep_ok.values()),
        "dyad_years_at_t1_plus": matched,
        "missed": len(missed_codes),
        "missed_examples": missed_codes[:10],
    }


def main() -> int:
    states = load_state_system()
    events, dropped = load_events(states)
    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    events.to_csv(OUT_EVENTS, index=False)
    dropped.to_csv(OUT_DROPPED, index=False)
    print(f"Events -> {OUT_EVENTS} ({len(events):,} rows)")
    print("  by source:", events["source"].value_counts().to_dict())
    print("  dropped by membership filter:", dropped["reason"].value_counts().to_dict())

    grid = member_grid(states)
    out = resolve_states(grid, events)
    out.to_parquet(OUT_STATES, index=False)
    print(f"Dyad states -> {OUT_STATES} ({len(out):,} directed dyad-years, "
          f"{out.year.min()}-{out.year.max()})")
    print("  directed rows by shared tier:", out["uiw_tier"].value_counts().sort_index().to_dict())
    und = out[out["initiator_ccode"] < out["target_ccode"]]
    print("  pair-years by shared tier:", und["uiw_tier"].value_counts().sort_index().to_dict())
    print("  T1 pair-years by basis:", und.loc[und.uiw_tier == 1, "t1_basis"].value_counts().to_dict())
    hidden = und[und["unobserved_tiers"] != 0]
    if len(hidden):
        print(f"  pair-years with a tier unobserved: {len(hidden):,} "
              f"({hidden.year.min()}-{hidden.year.max()}, sanctions have no source)")
    if os.path.exists(MCT_CSV):
        mct_res = check_mct_coverage(out, MCT_CSV)
        print(f"  MCT check (1946-2014): {mct_res['dyad_years_at_t1_plus']}/{mct_res['in_window_dyad_years']} "
              f"dyad-years at T1+ ({mct_res['episodes_at_t1_plus']}/{mct_res['episodes_checked']} episodes; "
              f"missed={mct_res['missed']} {mct_res['missed_examples']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
