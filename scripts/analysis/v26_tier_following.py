"""Tier -> next-tier distribution (v26.1, 1900-2025).

Reads the per-transition log produced by tier_transition_risk_full.py and writes:
  output/analysis/v26_tier_following_distribution.csv   (row-normalised matrix)
  output/analysis/v26_tier_following_distribution_counts.csv
  output/charts/v26_tier_transition_heatmap.png
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "output", "analysis", "tier_transitions_full.csv")
OUT_PROB = os.path.join(ROOT, "output", "analysis", "v26_tier_following_distribution.csv")
OUT_CNT = os.path.join(ROOT, "output", "analysis", "v26_tier_following_distribution_counts.csv")
OUT_CHART = os.path.join(ROOT, "output", "charts", "v26_tier_transition_heatmap.png")

TIERS = [
    (0, "T0\nPeace"),
    (1, "T1\nDiplomatic Crisis"),
    (2, "T2\nEconomic/Display"),
    (3, "T3\nProxy Military"),
    (4, "T4\nLimited Military"),
    (5, "T5\nStrategic War"),
]
SHORT = {c: n.replace("\n", " ") for c, n in TIERS}


def main() -> int:
    tr = pd.read_csv(SRC, usecols=["t_from", "t_to"])
    print(f"Loaded {len(tr):,} year-over-year transitions")

    cnt = pd.crosstab(tr["t_from"], tr["t_to"]).reindex(
        index=range(6), columns=range(6), fill_value=0
    )
    prob = cnt.div(cnt.sum(axis=1), axis=0).fillna(0).round(4)

    cnt_named = cnt.copy()
    prob_named = prob.copy()
    cnt_named.index = [SHORT[c] for c in cnt_named.index]
    cnt_named.columns = [SHORT[c] for c in cnt_named.columns]
    prob_named.index = [SHORT[c] for c in prob_named.index]
    prob_named.columns = [SHORT[c] for c in prob_named.columns]

    cnt_named.to_csv(OUT_CNT)
    prob_named.to_csv(OUT_PROB)
    print(f"\nCounts -> {OUT_CNT}")
    print(cnt_named.to_string())
    print(f"\nRow-normalised (what follows each tier) -> {OUT_PROB}")
    print((prob_named * 100).round(2).astype(str) + "%")

    # Heatmap
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    labels = [SHORT[c] for c in range(6)]
    cmap = "YlOrRd"
    vmax = 1.0

    for ax, data, title, fmt in (
        (axes[0], prob.values, "Transition probability P(t_to | t_from)", "{:.1%}"),
        (axes[1], cnt.values, "Transition counts (year-over-year)", "{:,.0f}"),
    ):
        im = ax.imshow(data, cmap=cmap, vmin=0, vmax=vmax if ax is axes[0] else data.max())
        ax.set_xticks(range(6))
        ax.set_yticks(range(6))
        ax.set_xticklabels(labels, rotation=0, fontsize=9)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel("Next-year tier", fontsize=10)
        ax.set_ylabel("This-year tier", fontsize=10)
        ax.set_title(title, fontsize=11)
        for i in range(6):
            for j in range(6):
                v = data[i, j]
                if v == 0:
                    continue
                txt = fmt.format(v)
                colour = "white" if (vmax if ax is axes[0] else data.max()) > 0 and v > 0.55 * (vmax if ax is axes[0] else data.max()) else "black"
                ax.text(j, i, txt, ha="center", va="center", fontsize=8, color=colour)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle("UCDP Dyadic v26.1 -- what tier follows each tier? (1900-2025)", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(OUT_CHART, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"\nHeatmap -> {OUT_CHART}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
