"""Validate and compare T1 (Diplomatic Crisis) before vs after MIDB_T1 build.

Compares:
  - Old T1 (hostlev=2 only, 46 rows) vs New T1 (hostlev=2 + diplomatic originators)
  - Decade distribution before/after
  - Transition matrix row before/after
  - Top initiators before/after

Inputs:
  - data/raw/T1_directed_v5.csv       (new T1 dataset)
  - data/processed/conflict_dyads.csv (combined data after pipeline)
  - output/analysis/tier_transitions_full.csv (transition log)

Outputs:
  - output/analysis/t1_validation_summary.csv
  - output/charts/t1_old_vs_new.png
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_RAW = os.path.join(ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(ROOT, "data", "processed")
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
OUT_CHARTS = os.path.join(ROOT, "output", "charts")

TIER_ORDER = [
    "T1-Diplomatic Crisis",
    "T2-Economic/Display",
    "T3-Proxy/Indirect Military",
    "T4-Limited Military",
    "T5-Strategic War",
]
TIER_SHORT = {t: t.split("-")[0] for t in TIER_ORDER}


def main() -> int:
    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    os.makedirs(OUT_CHARTS, exist_ok=True)

    # -----------------------------------------------------------------
    # 1. Load new T1 and the combined dataset
    # -----------------------------------------------------------------
    t1 = pd.read_csv(os.path.join(DATA_RAW, "T1_directed_v5.csv"), dtype={"year": int})
    combined = pd.read_csv(os.path.join(DATA_PROCESSED, "conflict_dyads.csv"), dtype={"year": int})

    t1_new = combined[combined["tier_label"] == "T1-Diplomatic Crisis"].copy()

    # "Old" T1: the MIDB-sourced rows (before MIDB_T1) - we can approximate from
    # the backup file
    backup_path = os.path.join(DATA_PROCESSED, "conflict_dyads_midb_only.csv")
    if os.path.exists(backup_path):
        midb_only = pd.read_csv(backup_path, dtype={"year": int})
        t1_old = midb_only[midb_only["tier_label"] == "T1-Diplomatic Crisis"].copy()
    else:
        t1_old = pd.DataFrame(columns=t1_new.columns)
    print(f"Old T1 rows (MIDB-only): {len(t1_old):,}")
    print(f"New T1 rows (combined):  {len(t1_new):,}")
    print(f"  of which hostlev=1:    {len(t1_new[t1_new['hostlev'] == 1]):,}")
    print(f"  of which hostlev=2:    {len(t1_new[t1_new['hostlev'] == 2]):,}")
    print(f"Raw T1 dataset rows:     {len(t1):,}")
    print(f"Unique dyads in new T1: {t1_new.groupby(['initiator', 'target']).ngroups:,}")

    # -----------------------------------------------------------------
    # 2. Decade distribution (old vs new T1)
    # -----------------------------------------------------------------
    def decade_counts(df: pd.DataFrame) -> pd.Series:
        if len(df) == 0:
            return pd.Series(dtype=int)
        return ((df["year"] // 10) * 10).value_counts().sort_index()

    old_dec = decade_counts(t1_old)
    new_dec = decade_counts(t1_new)
    dec_all = pd.DataFrame({"old": old_dec, "new": new_dec}).fillna(0).astype(int)
    dec_all.index.name = "decade"
    dec_all.to_csv(os.path.join(OUT_ANALYSIS, "t1_decade_comparison.csv"))
    print("\nDecade comparison:")
    print(dec_all.to_string())

    # -----------------------------------------------------------------
    # 3. Top initiators (new T1)
    # -----------------------------------------------------------------
    top = t1_new.groupby("initiator").size().sort_values(ascending=False).head(20)
    top_df = pd.DataFrame(top).reset_index()
    top_df.columns = ["initiator", "n_T1_events"]
    top_df.to_csv(os.path.join(OUT_ANALYSIS, "t1_top_initiators.csv"), index=False)
    print("\nTop 20 T1 initiators:")
    print(top_df.to_string(index=False))

    # -----------------------------------------------------------------
    # 4. Transition matrix row for T1 (from tier_transitions_full.csv)
    # -----------------------------------------------------------------
    tr_path = os.path.join(OUT_ANALYSIS, "tier_transitions_full.csv")
    if os.path.exists(tr_path):
        tr = pd.read_csv(tr_path)
        t1_trans = tr[tr["t_from"] == 1]
        if len(t1_trans):
            counts = t1_trans.groupby("t_to").size().reindex(range(6), fill_value=0)
            probs = counts / counts.sum()
            trans_df = pd.DataFrame({
                "t_to": [f"T{i}" for i in range(6)],
                "count": counts.values,
                "probability": probs.values.round(4),
            })
            trans_df.to_csv(os.path.join(OUT_ANALYSIS, "t1_transition_row.csv"), index=False)
            print(f"\nT1 transition row (n={len(t1_trans)}):")
            print(trans_df.to_string(index=False))

    # -----------------------------------------------------------------
    # 5. Chart: old vs new T1 by decade
    # -----------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    # Left: old T1 by decade
    ax = axes[0]
    if len(old_dec):
        ax.bar(old_dec.index, old_dec.values, color="#fdae61", width=8)
    ax.set_title(f"Old T1: hostlev=2 only\n{len(t1_old):,} rows")
    ax.set_xlabel("Decade")
    ax.set_ylabel("T1 dyad-years")
    ax.set_xticks(range(1900, 2030, 10))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)

    # Right: new T1 by decade
    ax = axes[1]
    if len(new_dec):
        ax.bar(new_dec.index, new_dec.values, color="#d53e4f", alpha=0.8, width=8,
               label="hostlev=2 (threats)")
        # Overlay hostlev=1 portion
        t1_hl1 = t1_new[t1_new["hostlev"] == 1]
        if len(t1_hl1):
            hl1_dec = ((t1_hl1["year"] // 10) * 10).value_counts().sort_index()
            ax.bar(hl1_dec.index, hl1_dec.values, color="#fdae61", alpha=0.9, width=8,
                   label="hostlev=1 (diplomatic originator)")
        ax.legend(fontsize=8)
    ax.set_title(f"New T1: threats + diplomatic originators\n{len(t1_new):,} rows")
    ax.set_xlabel("Decade")
    ax.set_ylabel("T1 dyad-years")
    ax.set_xticks(range(1900, 2030, 10))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("T1 (Diplomatic Crisis): old MIDB-only vs new MIDB_T1 build", fontsize=12)
    fig.tight_layout()
    out_path = os.path.join(OUT_CHARTS, "t1_old_vs_new.png")
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"\nChart -> {out_path}")

    # -----------------------------------------------------------------
    # 6. Validation summary
    # -----------------------------------------------------------------
    summary_rows = [
        ("old_t1_rows", len(t1_old)),
        ("new_t1_rows", len(t1_new)),
        ("new_t1_hostlev1", len(t1_new[t1_new["hostlev"] == 1])),
        ("new_t1_hostlev2", len(t1_new[t1_new["hostlev"] == 2])),
        ("new_t1_unique_dyads", t1_new.groupby(["initiator", "target"]).ngroups),
        ("new_t1_year_min", int(t1_new["year"].min())),
        ("new_t1_year_max", int(t1_new["year"].max())),
        ("new_t1_unique_initiators", t1_new["initiator"].nunique()),
        ("new_t1_unique_targets", t1_new["target"].nunique()),
    ]
    summary_df = pd.DataFrame(summary_rows, columns=["metric", "value"])
    summary_df.to_csv(os.path.join(OUT_ANALYSIS, "t1_validation_summary.csv"), index=False)
    print(f"\nSummary -> {OUT_ANALYSIS}/t1_validation_summary.csv")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
