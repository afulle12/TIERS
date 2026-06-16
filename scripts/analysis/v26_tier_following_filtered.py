"""Coverage-aware transition matrix (v26.1).

Source dataset coverage (years where the dataset legitimately records that tier):
  T0 Peace               1900-2025   inferred from country-pair grid
  T1 Diplomatic Crisis   1903-2014   MIDB only
  T2 Economic/Display    1900-2015   MIDB (1900-2014) + EUSANCT (1989-2015)
  T3 Proxy Military      1946-2025   UCDP Dyadic v26.1 (supporter->host)
  T4 Limited Military    1900-2014   MIDB only
  T5 Strategic War       1900-2003   MIDB only

A year-over-year transition (t_from, t_to, y_from, y_to) is considered
"observable" only if both endpoints fall within their tier's coverage.
"Spurious" transitions (e.g. T4 -> T0 in 2015 because MIDB ends, T5 -> T0
in 2004, T4 -> T0 in 2014 because MIDB ends) are dropped.

Outputs:
  output/analysis/v26_coverage_summary.csv
  output/analysis/v26_tier_following_distribution_filtered.csv
  output/analysis/v26_tier_following_distribution_counts_filtered.csv
  output/analysis/v26_tier_following_distribution_fullycovered.csv
  output/analysis/v26_tier_following_distribution_counts_fullycovered.csv
  output/charts/v26_tier_transition_heatmap_filtered.png
  output/charts/v26_tier_transition_coverage_compare.png
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "output", "analysis", "tier_transitions_full.csv")
OUT_DIR = os.path.join(ROOT, "output", "analysis")
OUT_CHART_DIR = os.path.join(ROOT, "output", "charts")

TIERS = [
    (0, "T0 Peace"),
    (1, "T1 Diplomatic Crisis"),
    (2, "T2 Economic/Display"),
    (3, "T3 Proxy Military"),
    (4, "T4 Limited Military"),
    (5, "T5 Strategic War"),
]
SHORT = {c: n for c, n in TIERS}

TIER_COVERAGE = {
    0: (1900, 2025),
    1: (1903, 2014),
    2: (1900, 2015),
    3: (1946, 2025),
    4: (1900, 2014),
    5: (1900, 2003),
}
TIER_SOURCE = {
    0: "inferred (grid)",
    1: "MIDB",
    2: "MIDB+EUSANCT",
    3: "UCDP Dyadic v26.1",
    4: "MIDB",
    5: "MIDB",
}

# Per-source dataset active years (used to drop boundary artefacts).
SOURCE_YEARS = {
    "MIDB": (1900, 2014),
    "EUSANCT": (1989, 2015),
    "UCDP": (1946, 2025),
    "CShapes": (1946, 2019),
}


def source_for_tier(t: int) -> list[str]:
    if t == 0:
        return []
    if t == 1:
        return ["MIDB"]
    if t == 2:
        return ["MIDB", "EUSANCT"]
    if t == 3:
        return ["UCDP"]
    if t == 4:
        return ["MIDB"]
    if t == 5:
        return ["MIDB"]
    return []


def source_active(src: str, y: int) -> bool:
    lo, hi = SOURCE_YEARS[src]
    return lo <= y <= hi


def tier_observed(t: int, y: int) -> bool:
    if t == 0:
        return any(source_active(s, y) for s in ("MIDB", "UCDP", "EUSANCT"))
    lo, hi = TIER_COVERAGE[t]
    return lo <= y <= hi and any(source_active(s, y) for s in source_for_tier(t))


# Years where every T1-T5 source is simultaneously active.
FULLY_COVERED_YEARS = (1946, 2014)


def observable(t: int, y: int) -> bool:
    return tier_observed(t, y)


def main() -> int:
    tr = pd.read_csv(SRC, usecols=["y_from", "y_to", "t_from", "t_to"])
    print(f"Loaded {len(tr):,} transitions (unfiltered)")

    # Coverage filter (vectorised):
    # A transition is "valid" only if the source dataset that recorded t_from
    # in y_from is *also* active in y_to (otherwise we can't tell whether the
    # dyad genuinely de-escalated or whether its data source simply ended).
    def tier_active_in(t: int, y: pd.Series) -> pd.Series:
        if t == 0:
            return ((y >= 1900) & (y <= 2014)) | ((y >= 1946) & (y <= 2025)) | ((y >= 1989) & (y <= 2015))
        srcs = source_for_tier(t)
        mask = pd.Series(False, index=y.index)
        for s in srcs:
            lo, hi = SOURCE_YEARS[s]
            mask = mask | ((y >= lo) & (y <= hi))
        lo, hi = TIER_COVERAGE[t]
        return mask & (y >= lo) & (y <= hi)

    keep_from = pd.Series(True, index=tr.index)
    keep_to = pd.Series(True, index=tr.index)
    src_alive_in_yto = pd.Series(False, index=tr.index)
    for t in (1, 2, 3, 4, 5):
        m = tr["t_from"] == t
        keep_from &= tier_active_in(t, tr["y_from"]) | ~m
        for s in source_for_tier(t):
            lo, hi = SOURCE_YEARS[s]
            src_alive_in_yto |= ((tr["y_to"] >= lo) & (tr["y_to"] <= hi)) & m
    keep_to &= tier_active_in(0, tr["y_to"])  # T0 destination
    for t in (1, 2, 3, 4, 5):
        m = tr["t_to"] == t
        keep_to &= tier_active_in(t, tr["y_to"]) | ~m
    keep = keep_from & keep_to & ((tr["t_from"] == 0) | src_alive_in_yto)
    tr_f = tr[keep].copy()
    print(f"After per-tier coverage filter (source still active in y_to): {len(tr_f):,} ({len(tr_f)/len(tr):.1%})")
    n_dropped = len(tr) - len(tr_f)
    print(f"  dropped: {n_dropped:,}")
    # Show what was dropped by category
    dropped = tr[~keep]
    if len(dropped) > 0:
        breakdown = dropped.groupby(["t_from", "t_to"]).size().sort_values(ascending=False).head(15)
        print("  top dropped (t_from -> t_to):")
        print(breakdown.to_string())

    # Fully-covered subset
    lo, hi = FULLY_COVERED_YEARS
    tr_full = tr_f[(tr_f.y_from >= lo) & (tr_f.y_to <= hi)].copy()
    print(f"Within fully-covered years {lo}-{hi}: {len(tr_full):,}")

    # Coverage summary per tier per year
    cov_rows = []
    for code, name in TIERS:
        ylo, yhi = TIER_COVERAGE[code]
        for y in range(1900, 2026):
            cov_rows.append({"year": y, "tier": name, "code": code,
                             "source": TIER_SOURCE[code],
                             "covered": int(observable(code, y))})
    cov = pd.DataFrame(cov_rows)
    cov.to_csv(os.path.join(OUT_DIR, "v26_coverage_summary.csv"), index=False)
    print(f"Wrote coverage summary -> v26_coverage_summary.csv")

    def write_matrices(tr_sub: pd.DataFrame, tag: str) -> None:
        cnt = pd.crosstab(tr_sub["t_from"], tr_sub["t_to"]).reindex(
            index=range(6), columns=range(6), fill_value=0
        )
        prob = cnt.div(cnt.sum(axis=1), axis=0).fillna(0).round(4)
        cnt_named = cnt.copy()
        prob_named = prob.copy()
        cnt_named.index = [SHORT[c] for c in cnt_named.index]
        cnt_named.columns = [SHORT[c] for c in cnt_named.columns]
        prob_named.index = [SHORT[c] for c in prob_named.index]
        prob_named.columns = [SHORT[c] for c in prob_named.columns]
        cnt_named.to_csv(os.path.join(OUT_DIR, f"v26_tier_following_distribution_counts_{tag}.csv"))
        prob_named.to_csv(os.path.join(OUT_DIR, f"v26_tier_following_distribution_{tag}.csv"))
        print(f"\n--- {tag} ---")
        print(f"Counts:\n{cnt_named.to_string()}")
        print(f"\nProbabilities:\n{(prob_named * 100).round(2).astype(str) + '%'}")

    write_matrices(tr_f, "filtered")
    write_matrices(tr_full, "fullycovered")

    # Comparison heatmap: unfiltered vs filtered
    def matrix(tr_sub):
        cnt = pd.crosstab(tr_sub["t_from"], tr_sub["t_to"]).reindex(
            index=range(6), columns=range(6), fill_value=0
        )
        return cnt.div(cnt.sum(axis=1), axis=0).fillna(0)

    prob_raw = matrix(tr)
    prob_filt = matrix(tr_f)
    prob_full = matrix(tr_full)

    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    labels = [SHORT[c] for c in range(6)]
    for ax, data, title in (
        (axes[0], prob_raw.values, f"Unfiltered (1900-2025, n={len(tr):,})"),
        (axes[1], prob_filt.values, f"Per-tier coverage filter\n(n={len(tr_f):,})"),
        (axes[2], prob_full.values, f"Fully-covered {FULLY_COVERED_YEARS[0]}-{FULLY_COVERED_YEARS[1]}\n(n={len(tr_full):,})"),
    ):
        im = ax.imshow(data, cmap="YlOrRd", vmin=0, vmax=1)
        ax.set_xticks(range(6))
        ax.set_yticks(range(6))
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Next-year tier", fontsize=9)
        ax.set_ylabel("This-year tier", fontsize=9)
        ax.set_title(title, fontsize=10)
        for i in range(6):
            for j in range(6):
                v = data[i, j]
                if v == 0:
                    continue
                ax.text(j, i, f"{v:.0%}", ha="center", va="center",
                        fontsize=7, color=("white" if v > 0.55 else "black"))
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle("UCDP Dyadic v26.1 -- tier transition matrix: coverage effects", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_CHART_DIR, "v26_tier_transition_coverage_compare.png"),
                dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"\nWrote comparison chart -> v26_tier_transition_coverage_compare.png")

    # Transitions per year by source tier (active only, T0 dropped -- otherwise T0 dominates)
    yr_from = tr[tr.t_from != 0].groupby(["y_from", "t_from"]).size().unstack(fill_value=0)
    yr_from = yr_from.reindex(columns=[1, 2, 3, 4, 5], fill_value=0)
    yr_from = yr_from.reindex(range(1900, 2026), fill_value=0)

    fig, ax = plt.subplots(figsize=(13, 5.5))
    palette = {0: "#d9d9d9", 1: "#fdae61", 2: "#fee08b", 3: "#abdda4", 4: "#74add1", 5: "#d53e4f"}
    bottom = np.zeros(len(yr_from))
    for t in [1, 2, 3, 4, 5]:
        ax.bar(yr_from.index, yr_from[t].values, bottom=bottom, color=palette[t],
               label=SHORT[t], width=1.0)
        bottom += yr_from[t].values
    # Source coverage lines + per-tier coverage end
    coverage_lines = [
        (2003.5, "T5 coverage ends 2003", "#d53e4f"),
        (2014.5, "MIDB ends 2014 (T1/T4)", "#333"),
        (2015.5, "EUSANCT ends 2015 (T2)", "#666"),
        (2019.5, "CShapes ends 2019 (country list)", "#999"),
    ]
    ymax = bottom.max()
    for x, label, c in coverage_lines:
        ax.axvline(x, color=c, linestyle="--", linewidth=1.1, alpha=0.8)
        ax.text(x, ymax * 0.97, label, rotation=90, va="top", ha="right",
                fontsize=8, color=c)
    ax.set_xlim(1900, 2026)
    ax.set_ylim(0, ymax * 1.05)
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of active-tier year-over-year transitions")
    ax.set_title("Active-tier transition volume by year (T0 peace excluded)\nDashed lines = data-source coverage cutoffs")
    ax.legend(loc="upper left", fontsize=9, ncol=5)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_CHART_DIR, "v26_transitions_by_year.png"),
                dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote transitions-by-year chart -> v26_transitions_by_year.png")

    # "Active tier" transitions only (excluding T0 from the from side)
    # Shows what % of T1-T5 dyads do various things year-over-year
    tr_active = tr[tr.t_from != 0].copy()
    tr_active_full = tr_active[
        (tr_active.y_from >= FULLY_COVERED_YEARS[0]) &
        (tr_active.y_to <= FULLY_COVERED_YEARS[1])
    ]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, sub, ttl in (
        (axes[0], tr_active, "Unfiltered 1900-2025"),
        (axes[1], tr_active_full, f"Fully-covered {FULLY_COVERED_YEARS[0]}-{FULLY_COVERED_YEARS[1]}"),
    ):
        cnt = pd.crosstab(sub["t_from"], sub["t_to"]).reindex(
            index=[1, 2, 3, 4, 5], columns=[0, 1, 2, 3, 4, 5], fill_value=0
        )
        prob = cnt.div(cnt.sum(axis=1), axis=0).fillna(0)
        labels_left = ["T1\nDiplomatic", "T2\nEconomic", "T3\nProxy", "T4\nLimited", "T5\nStrategic"]
        labels_bot = ["T0\nPeace", "T1", "T2", "T3", "T4", "T5"]
        im = ax.imshow(prob.values, cmap="YlOrRd", vmin=0, vmax=0.6)
        ax.set_xticks(range(6))
        ax.set_yticks(range(5))
        ax.set_xticklabels(labels_bot, fontsize=9)
        ax.set_yticklabels(labels_left, fontsize=9)
        ax.set_xlabel("Next-year tier", fontsize=10)
        ax.set_ylabel("This-year tier (active only)", fontsize=10)
        ax.set_title(f"Active-tier transitions: {ttl}\n(n={len(sub):,})", fontsize=11)
        for i in range(5):
            for j in range(6):
                v = prob.values[i, j]
                if v == 0:
                    continue
                ax.text(j, i, f"{v:.0%}", ha="center", va="center",
                        fontsize=9, color=("white" if v > 0.35 else "black"))
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("Active tier -> next tier (T0 peace excluded as source)", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_CHART_DIR, "v26_active_tier_transitions.png"),
                dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote active-tier transitions chart -> v26_active_tier_transitions.png")

    # Filtered-only heatmap
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    for ax, data, title, fmt in (
        (axes[0], prob_filt.values, f"P(t_to | t_from) -- per-tier coverage filter (n={len(tr_f):,})", "{:.1%}"),
        (axes[1], prob_full.values, f"P(t_to | t_from) -- fully-covered {FULLY_COVERED_YEARS[0]}-{FULLY_COVERED_YEARS[1]} (n={len(tr_full):,})", "{:.1%}"),
    ):
        im = ax.imshow(data, cmap="YlOrRd", vmin=0, vmax=1)
        ax.set_xticks(range(6))
        ax.set_yticks(range(6))
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel("Next-year tier", fontsize=10)
        ax.set_ylabel("This-year tier", fontsize=10)
        ax.set_title(title, fontsize=11)
        for i in range(6):
            for j in range(6):
                v = data[i, j]
                if v == 0:
                    continue
                ax.text(j, i, fmt.format(v), ha="center", va="center",
                        fontsize=8, color=("white" if v > 0.55 else "black"))
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("UCDP Dyadic v26.1 -- coverage-filtered transition matrices", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_CHART_DIR, "v26_tier_transition_heatmap_filtered.png"),
                dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote filtered heatmap -> v26_tier_transition_heatmap_filtered.png")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
