"""v26.1 snapshot: tier distribution and year-over-year transition risk.

Reads data/processed/conflict_dyads_full.csv (T0-T5, 1900-2025) and writes:
  output/analysis/v26_tier_distribution_by_decade.csv
  output/analysis/v26_tier_transition_risk.csv
  output/charts/v26_tiers_overview.png

Tier scheme:
  T0 No Conflict/Peace  T1 Diplomatic Crisis
  T2 Economic/Display   T3 Proxy/Indirect Military
  T4 Limited Military   T5 Strategic War
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "data", "processed", "conflict_dyads_full.csv")
OUT_DIST = os.path.join(ROOT, "output", "analysis", "v26_tier_distribution_by_decade.csv")
OUT_RISK = os.path.join(ROOT, "output", "analysis", "v26_tier_transition_risk.csv")
OUT_CHART = os.path.join(ROOT, "output", "charts", "v26_tiers_overview.png")

TIERS = [
    (0, "T0 Peace"),
    (1, "T1 Diplomatic Crisis"),
    (2, "T2 Economic/Display"),
    (3, "T3 Proxy Military"),
    (4, "T4 Limited Military"),
    (5, "T5 Strategic War"),
]
TIER_COLOURS = {
    0: "#d9d9d9",
    1: "#fdae61",
    2: "#fee08b",
    3: "#abdda4",
    4: "#74add1",
    5: "#d53e4f",
}


def load_dyad_year() -> pd.DataFrame:
    df = pd.read_csv(SRC, dtype={"year": int}, usecols=["year", "initiator", "target", "uiw_tier"])
    dy = (
        df.groupby(["initiator", "target", "year"])["uiw_tier"]
        .max()
        .reset_index()
        .sort_values(["initiator", "target", "year"])
    )
    return dy


def distribution_by_decade(dy: pd.DataFrame) -> pd.DataFrame:
    dy = dy.copy()
    dy["decade"] = (dy["year"] // 10) * 10
    counts = dy.groupby(["decade", "uiw_tier"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=[t for t, _ in TIERS], fill_value=0)
    counts.columns = [name for _, name in TIERS]
    counts["total"] = counts.sum(axis=1)
    active_total = counts[[name for _, name in TIERS if _ != 0]].sum(axis=1).replace(0, pd.NA)
    for _, name in TIERS:
        counts[f"{name} share"] = counts[name] / active_total
    counts = counts.fillna(0)
    return counts.reset_index()


def transition_risk(dy: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (init, tgt), g in dy.groupby(["initiator", "target"], sort=False):
        g = g.sort_values("year")
        t = g["uiw_tier"].to_numpy()
        if len(t) < 2:
            continue
        deltas = t[1:] - t[:-1]
        for fr, d in zip(t[:-1], deltas):
            rows.append((int(fr), int(d)))
    tr = pd.DataFrame(rows, columns=["t_from", "delta"])
    out = []
    for code, name in TIERS:
        sub = tr[tr["t_from"] == code]
        n = len(sub)
        if n == 0:
            out.append({"tier": name, "code": code, "n": 0,
                        "p_escalate": np.nan, "p_stable": np.nan,
                        "p_deescalate": np.nan, "mean_delta": np.nan,
                        "p_reach_T5": np.nan})
            continue
        n_e = int((sub.delta > 0).sum())
        n_s = int((sub.delta == 0).sum())
        n_d = int((sub.delta < 0).sum())
        p_t5 = float(((sub.delta > 0) & (np.arange(n) >= 0)).sum())  # placeholder, replaced below
        # p_reach_T5 = fraction whose next-year tier is 5
        # We need the actual t_to, recompute:
        pass
        out.append({"tier": name, "code": code, "n": n,
                    "p_escalate": n_e / n, "p_stable": n_s / n,
                    "p_deescalate": n_d / n, "mean_delta": float(sub.delta.mean()),
                    "p_reach_T5": np.nan})
    # Recompute p_reach_T5 properly with t_to:
    rows2 = []
    for (init, tgt), g in dy.groupby(["initiator", "target"], sort=False):
        g = g.sort_values("year")
        t = g["uiw_tier"].to_numpy()
        if len(t) < 2:
            continue
        for fr, to in zip(t[:-1], t[1:]):
            rows2.append((int(fr), int(to)))
    tr2 = pd.DataFrame(rows2, columns=["t_from", "t_to"])
    for code, name in TIERS:
        sub = tr2[tr2["t_from"] == code]
        if len(sub):
            out[code]["p_reach_T5"] = float((sub.t_to == 5).mean())
    return pd.DataFrame(out)


def make_chart(dist: pd.DataFrame, risk: pd.DataFrame, out_path: str) -> None:
    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [1.2, 1]})

    # Left: stacked share by decade (excluding T0 for readability of conflict tiers).
    decades = dist["decade"].tolist()
    conflict_tiers = [n for c, n in TIERS if c != 0]
    conflict_codes = [c for c, _ in TIERS if c != 0]
    bottom = np.zeros(len(decades))
    for code, name in zip(conflict_codes, conflict_tiers):
        share = dist[f"{name} share"].to_numpy()
        ax_l.bar(decades, share, bottom=bottom, color=TIER_COLOURS[code], label=name, width=8)
        bottom += share
    ax_l.set_title("Conflict-tier composition by decade (v26.1)\nshare of active (T1-T5) dyad-years")
    ax_l.set_xlabel("Decade")
    ax_l.set_ylabel("Share of active dyad-years")
    ax_l.set_ylim(0, 1)
    ax_l.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax_l.set_xticks(decades)
    ax_l.set_xticklabels([f"{d}s" for d in decades], rotation=45, ha="right")
    ax_l.grid(axis="y", alpha=0.3)

    # Right: per-tier transition probabilities (T0 omitted -- nearly all stable).
    conflict_risk = risk[risk["code"] != 0].copy()
    x = np.arange(len(conflict_risk))
    w = 0.27
    ax_r.bar(x - w, conflict_risk["p_escalate"], w, color="#d53e4f", label="P(escalate)")
    ax_r.bar(x, conflict_risk["p_stable"], w, color="#999999", label="P(stable)")
    ax_r.bar(x + w, conflict_risk["p_deescalate"], w, color="#74add1", label="P(de-escalate)")
    for i, (esc, stb, dee) in enumerate(zip(
        conflict_risk["p_escalate"], conflict_risk["p_stable"], conflict_risk["p_deescalate"]
    )):
        ax_r.text(i - w, esc + 0.01, f"{esc:.0%}", ha="center", fontsize=8)
        ax_r.text(i, stb + 0.01, f"{stb:.0%}", ha="center", fontsize=8)
        ax_r.text(i + w, dee + 0.01, f"{dee:.0%}", ha="center", fontsize=8)
    ax_r.set_xticks(x)
    ax_r.set_xticklabels([t.split(" ", 1)[1] for t in conflict_risk["tier"]], rotation=20, ha="right", fontsize=9)
    ax_r.set_ylim(0, 1.05)
    ax_r.set_ylabel("Year-over-year transition probability")
    ax_r.set_title("Year-over-year escalation / stable / de-escalation\nby source tier (v26.1, 1900-2025)")
    ax_r.legend(loc="upper right", fontsize=9)
    ax_r.grid(axis="y", alpha=0.3)

    fig.suptitle("UCDP Dyadic v26.1 -- tier distribution & transition risk", fontsize=13, y=1.00)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    dy = load_dyad_year()
    print(f"Distinct (dyad, year) observations: {len(dy):,}")

    dist = distribution_by_decade(dy)
    dist.to_csv(OUT_DIST, index=False)
    print(f"\nWrote tier distribution by decade -> {OUT_DIST}")
    print(dist.to_string(index=False))

    risk = transition_risk(dy)
    risk.to_csv(OUT_RISK, index=False)
    print(f"\nWrote per-tier transition risk -> {OUT_RISK}")
    print(risk.to_string(index=False))

    make_chart(dist, risk, OUT_CHART)
    print(f"\nWrote chart -> {OUT_CHART}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
