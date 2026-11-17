"""Build the rivalry table from the directed MID events (proposal section 2.6).

Definition
----------
Rivalry is directed. State i's rivalry toward state j in year T is the
recency-decayed history of j's militarised actions against i:

    Omega_{i<-j}(T) = min(1, sum_{t <= T} w_{j->i}(t) * exp(-LAMBDA * (T - t)))

so a state that has been threatened or attacked treats the other as a rival
whether or not it ever acted itself. One-sided rivalry is intended.

  w_{j->i}(t)  the weight of the hostility level j directed at i in year t,
               summed over the disputes active that year. The level is j's
               own MID hostility level, lowered to a display of force where
               the event builder found no evidence that j's force was aimed
               at i (`build_mid_dyads.py`, coalition rule).
  LAMBDA       0.10 per year, a half-life of about seven years.

Forecast origin. A row for year T uses events up to and including year T and
is used to forecast the tier in year T + 1. Nothing from T + 1 enters.

History. Events from 1900 on are used, so rivalries do not start from zero
in 1946. A state keeps its history across a change of code (Germany, Yemen,
Serbia) through `history_id`.

Columns, on the row (initiator = i, target = j):

  rivalry_omega      Omega_{i<-j}: the initiator's rivalry toward the target
  rivalry_omega_b    Omega_{j<-i}: the target's rivalry toward the initiator
  conflict_history   the same decayed sum over both directions together, a
                     shared measure of how much the pair has fought

Only rows with a non-zero value are written; absent rows mean no history.

Input:  data/processed/mid_dyad_events.csv, data/processed/state_system.csv
Output: data/processed/rivalry_omega.csv, keyed on COW codes
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from state_system import cow_to_gw, load_state_system

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
MID_EVENTS_CSV = os.path.join(DATA_PROCESSED, "mid_dyad_events.csv")
OUT_CSV = os.path.join(DATA_PROCESSED, "rivalry_omega.csv")

HISTORY_LO = 1900            # first year of events used as history
YEAR_LO, YEAR_HI = 1946, 2014
LAMBDA = 0.10                # recency decay; half-life ~ 7 years
MIN_VALUE = 1e-4             # values below this are written as no history

# Weight by MID hostility level: 2 threat, 3 display, 4 use of force, 5 war.
HOSTLEV_WEIGHT = {2: 0.25, 3: 0.50, 4: 0.75, 5: 1.00}


def history_id(ccode: int, year: int) -> int:
    """An identifier that follows a state through a change of country code.

    Gleditsch-Ward numbers keep Germany (260) and Yemen (678) continuous
    across unification where COW starts a new code; COW keeps Serbia (345)
    continuous across 2006 where Gleditsch-Ward does not.
    """
    if ccode == 345:
        return 345
    return cow_to_gw(int(ccode), int(year))


def directed_weights(events: pd.DataFrame) -> pd.DataFrame:
    """Return `year, actor, target, weight` summed over the disputes of a year.

    `actor` is the state that acted and `target` the state acted against,
    both as history ids.
    """
    ev = events[["year", "initiator_ccode", "target_ccode", "uiw_tier", "hostlev"]].copy()
    # A row capped to T1 by the coalition rule keeps the participant's own
    # hostility level; what was aimed at this target is at most a display.
    level = np.where(ev["uiw_tier"] == 1, np.minimum(ev["hostlev"], 3), ev["hostlev"])
    ev["weight"] = pd.Series(level, index=ev.index).map(HOSTLEV_WEIGHT).fillna(0.0)
    ev["actor"] = [history_id(c, y) for c, y in zip(ev["initiator_ccode"], ev["year"], strict=True)]
    ev["target"] = [history_id(c, y) for c, y in zip(ev["target_ccode"], ev["year"], strict=True)]
    ev = ev[ev["actor"] != ev["target"]]
    return ev.groupby(["year", "actor", "target"], as_index=False)["weight"].sum()


def decayed_history(weights: pd.DataFrame, year_lo: int, year_hi: int, lam: float = LAMBDA) -> pd.DataFrame:
    """Decayed running sum per (actor, target), one column per year `year_lo..year_hi`.

    `value[T] = value[T - 1] * exp(-lam) + weight[T]`, which equals
    `sum_{t <= T} weight[t] * exp(-lam * (T - t))`. Not clipped.
    """
    first = int(min(weights["year"].min(), year_lo)) if len(weights) else year_lo
    years = list(range(first, year_hi + 1))
    wide = (
        weights.pivot_table(index=["actor", "target"], columns="year", values="weight", aggfunc="sum")
        .reindex(columns=years)
        .fillna(0.0)
    )
    decay = float(np.exp(-lam))
    vals = wide.to_numpy(dtype=float)
    out = np.zeros_like(vals)
    running = np.zeros(vals.shape[0])
    for col in range(vals.shape[1]):
        running = running * decay + vals[:, col]
        out[:, col] = running
    res = pd.DataFrame(out, index=wide.index, columns=years)
    return res[[y for y in years if y >= year_lo]]


def build_rivalry(events: pd.DataFrame, states: pd.DataFrame,
                  year_lo: int = YEAR_LO, year_hi: int = YEAR_HI, lam: float = LAMBDA) -> pd.DataFrame:
    """Return the sparse rivalry table for member pairs in `year_lo..year_hi`."""
    weights = directed_weights(events[events["year"] <= year_hi])
    hist = decayed_history(weights, year_lo, year_hi, lam)
    acted = (
        hist.stack().rename("acted").reset_index()
        .rename(columns={"level_2": "year"})
    )
    acted.columns = ["actor", "target", "year", "acted"]
    acted = acted[acted["acted"] > 0.0]

    # On the row (i, j): what j did to i is `received`, what i did to j is `sent`.
    received = acted.rename(columns={"actor": "h_j", "target": "h_i", "acted": "received"})
    sent = acted.rename(columns={"actor": "h_i", "target": "h_j", "acted": "sent"})
    pair = received.merge(sent, on=["year", "h_i", "h_j"], how="outer").fillna(0.0)

    pair["rivalry_omega"] = np.minimum(pair["received"], 1.0)
    pair["rivalry_omega_b"] = np.minimum(pair["sent"], 1.0)
    pair["conflict_history"] = np.minimum(pair["received"] + pair["sent"], 1.0)

    # Attach the COW code each state carries in that year; pairs in which
    # either state is not a member that year drop out.
    s = states[(states["year"] >= year_lo) & (states["year"] <= year_hi)][["year", "ccode"]].copy()
    s["h"] = [history_id(c, y) for c, y in zip(s["ccode"], s["year"], strict=True)]
    out = pair.merge(
        s.rename(columns={"h": "h_i", "ccode": "initiator_ccode"}), on=["year", "h_i"], how="inner"
    ).merge(
        s.rename(columns={"h": "h_j", "ccode": "target_ccode"}), on=["year", "h_j"], how="inner"
    )
    cols = ["rivalry_omega", "rivalry_omega_b", "conflict_history"]
    out = out[(out[cols] >= MIN_VALUE).any(axis=1)]
    out = out[["year", "initiator_ccode", "target_ccode"] + cols].astype({"year": int})
    out[cols] = out[cols].round(6)
    out = out.sort_values(["year", "initiator_ccode", "target_ccode"]).reset_index(drop=True)
    if out.duplicated(["year", "initiator_ccode", "target_ccode"]).any():
        raise ValueError("rivalry: duplicate directed dyad-year")
    return out


def main() -> int:
    events = pd.read_csv(MID_EVENTS_CSV)
    events = events[events["year"] >= HISTORY_LO]
    states = load_state_system()
    out = build_rivalry(events, states)
    out.to_csv(OUT_CSV, index=False)
    last = out[out["year"] == YEAR_HI]
    print(f"Rivalry -> {OUT_CSV} ({len(out):,} directed dyad-years with history, "
          f"{YEAR_LO}-{YEAR_HI}; events from {int(events['year'].min())})")
    print(f"  {YEAR_HI}: {len(last):,} directed pairs; "
          f"one-sided (one direction zero): "
          f"{int(((last.rivalry_omega < MIN_VALUE) ^ (last.rivalry_omega_b < MIN_VALUE)).sum()):,}")
    print(f"  median {out.rivalry_omega[out.rivalry_omega > 0].median():.3f}, "
          f"share at the cap of 1.0: {(out.rivalry_omega >= 1.0).mean():.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
