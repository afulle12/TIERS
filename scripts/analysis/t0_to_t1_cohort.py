"""Empirical T0 -> T1 cohort analysis.

Reads the year-on-year tier transition log
(output/analysis/tier_transitions_full.csv), filters to the cohort of
directed dyad-years that were at T0 (peace) in year t and T1
(diplomatic crisis) in year t+1, enriches each row with the T1 event
metadata from data/processed/conflict_dyads.csv, and writes:

    output/analysis/t0_to_t1_cohort.csv
    output/analysis/t0_to_t1_by_decade.csv
    output/analysis/t0_to_t1_top_initiators.csv
    output/analysis/t0_to_t1_top_dyads.csv
    output/analysis/t0_to_t1_hostlev_source.csv
    output/charts/t0_to_t1_by_decade.png
    output/analysis/t0_to_t1_report.md
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TR_PATH = os.path.join(ROOT, "output", "analysis", "tier_transitions_full.csv")
CONFLICT_PATH = os.path.join(ROOT, "data", "processed", "conflict_dyads.csv")
TOP_INITIATORS_PATH = os.path.join(
    ROOT, "output", "analysis", "t1_top_initiators.csv"
)
OUT_ANALYSIS = os.path.join(ROOT, "output", "analysis")
OUT_CHARTS = os.path.join(ROOT, "output", "charts")
CHUNK = 500_000


def load_cohort() -> pd.DataFrame:
    """Stream tier_transitions_full.csv and return rows where t_from=0, t_to=1."""
    pieces = []
    n_t0_total = 0
    for chunk in pd.read_csv(
        TR_PATH,
        chunksize=CHUNK,
        dtype={"y_from": int, "y_to": int, "t_from": int, "t_to": int, "delta": int},
    ):
        n_t0_total += int((chunk["t_from"] == 0).sum())
        pieces.append(chunk[(chunk["t_from"] == 0) & (chunk["t_to"] == 1)])
    cohort = pd.concat(pieces, ignore_index=True)
    return cohort, n_t0_total


def enrich(cohort: pd.DataFrame) -> pd.DataFrame:
    """Join the T1 event metadata from conflict_dyads.csv on (initiator, target, year=y_to)."""
    conflict = pd.read_csv(
        CONFLICT_PATH,
        dtype={"year": int},
        usecols=[
            "year", "initiator", "target", "hostlev", "uiw_tier", "tier_label",
            "initiator_gwno", "target_gwno", "source", "region",
        ],
    )
    t1_events = conflict[conflict["tier_label"] == "T1-Diplomatic Crisis"].copy()
    t1_events = t1_events.rename(columns={"year": "y_to"})
    merged = cohort.merge(
        t1_events,
        on=["initiator", "target", "y_to"],
        how="left",
        validate="one_to_one",
    )
    return merged


def write_outputs(cohort: pd.DataFrame, n_t0_total: int) -> dict:
    os.makedirs(OUT_ANALYSIS, exist_ok=True)
    os.makedirs(OUT_CHARTS, exist_ok=True)

    cohort_path = os.path.join(OUT_ANALYSIS, "t0_to_t1_cohort.csv")
    cohort.to_csv(cohort_path, index=False)

    cohort_enriched = cohort.dropna(subset=["hostlev"]).copy()
    cohort_enriched["decade"] = (cohort_enriched["y_to"] // 10) * 10

    by_decade = (
        cohort_enriched.groupby("decade")
        .size()
        .rename("n_t0_to_t1")
        .reset_index()
        .sort_values("decade")
    )
    by_decade.to_csv(
        os.path.join(OUT_ANALYSIS, "t0_to_t1_by_decade.csv"), index=False
    )

    top_init = (
        cohort_enriched.groupby("initiator")
        .size()
        .sort_values(ascending=False)
        .head(20)
        .rename("n_t0_to_t1")
        .reset_index()
    )
    top_init.to_csv(
        os.path.join(OUT_ANALYSIS, "t0_to_t1_top_initiators.csv"), index=False
    )

    top_dyads = (
        cohort_enriched.groupby(["initiator", "target"])
        .size()
        .sort_values(ascending=False)
        .head(20)
        .rename("n_t0_to_t1")
        .reset_index()
    )
    top_dyads.to_csv(
        os.path.join(OUT_ANALYSIS, "t0_to_t1_top_dyads.csv"), index=False
    )

    crosstab = pd.crosstab(
        cohort_enriched["hostlev"].fillna(-1).astype(int),
        cohort_enriched["source"].fillna("UNKNOWN"),
        dropna=False,
    )
    crosstab.index.name = "hostlev"
    crosstab.to_csv(
        os.path.join(OUT_ANALYSIS, "t0_to_t1_hostlev_source.csv")
    )

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(by_decade["decade"], by_decade["n_t0_to_t1"], width=8, color="#d53e4f")
    ax.set_title(
        f"T0 -> T1 transitions by decade (n={len(cohort_enriched):,})"
    )
    ax.set_xlabel("Decade (year t+1)")
    ax.set_ylabel("T0 -> T1 transitions")
    ax.set_xticks(range(1900, 2030, 10))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    chart_path = os.path.join(OUT_CHARTS, "t0_to_t1_by_decade.png")
    fig.savefig(chart_path, dpi=130)
    plt.close(fig)

    return {
        "cohort": cohort_enriched,
        "n_t0_total": n_t0_total,
        "by_decade": by_decade,
        "top_init": top_init,
        "top_dyads": top_dyads,
        "crosstab": crosstab,
        "chart_path": chart_path,
    }


def write_report(stats: dict) -> str:
    cohort = stats["cohort"]
    n_t0_total = stats["n_t0_total"]
    by_decade = stats["by_decade"]
    top_init = stats["top_init"]
    top_dyads = stats["top_dyads"]
    crosstab = stats["crosstab"]

    n_cohort = len(cohort)
    base_rate_per_100k = n_cohort / n_t0_total * 100_000 if n_t0_total else float("nan")

    n_unmatched = int(stats["cohort"]["hostlev"].isna().sum()) if "hostlev" in cohort else 0
    year_min = int(cohort["y_to"].min()) if n_cohort else None
    year_max = int(cohort["y_to"].max()) if n_cohort else None

    top_init_set = set(top_init["initiator"].head(10))
    try:
        ref_top = pd.read_csv(TOP_INITIATORS_PATH)
        ref_top_set = set(ref_top["initiator"].head(10))
    except FileNotFoundError:
        ref_top_set = set()
    overlap = sorted(top_init_set & ref_top_set)

    def df_to_md(df: pd.DataFrame) -> str:
        if len(df) == 0:
            return "_(empty)_"
        cols = [str(c) for c in df.columns]
        rows = [[str(v) for v in row] for row in df.itertuples(index=False, name=None)]
        widths = [
            max(len(cols[i]), *(len(r[i]) for r in rows)) for i in range(len(cols))
        ]
        header = "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)) + " |"
        sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
        body = "\n".join(
            "| " + " | ".join(r[i].ljust(widths[i]) for i in range(len(cols))) + " |"
            for r in rows
        )
        return f"{header}\n{sep}\n{body}"

    lines = []
    lines.append("# T0 -> T1 cohort report")
    lines.append("")
    lines.append(
        "Source: `output/analysis/tier_transitions_full.csv` (4,394,503 "
        "year-on-year directed dyad transitions, derived from the full "
        "T0-T5 grid in `data/processed/conflict_dyads_full.csv`)."
    )
    lines.append("")
    lines.append("## 1. Headline numbers")
    lines.append("")
    lines.append(f"- T0 -> T1 transitions observed: **{n_cohort:,}**")
    lines.append(f"- Total T0 dyad-year transitions (denominator): {n_t0_total:,}")
    lines.append(f"- Base rate: **{base_rate_per_100k:.2f} per 100,000 T0 dyad-years**")
    if year_min is not None:
        lines.append(f"- Year range (year t+1): {year_min}-{year_max}")
    if n_unmatched:
        lines.append(
            f"- Rows not matched to a T1 event in `conflict_dyads.csv`: {n_unmatched}"
        )
    lines.append("")
    lines.append(
        "Note: the model's single global beta is calibrated to the observed "
        "T0 -> T1+ rate (`CHANGELOG.md:215`). v21 backtest AUC for the same "
        "target is 0.30, v27.0 spec is 0.63 "
        "(`output/analysis/model_calibration_summary*.md`)."
    )
    lines.append("")
    lines.append("## 2. Top 5 initiators")
    lines.append("")
    lines.append(df_to_md(top_init.head(5)))
    lines.append("")
    lines.append("## 3. Top 5 dyads (recurring escalations)")
    lines.append("")
    lines.append(df_to_md(top_dyads.head(5)))
    lines.append("")
    lines.append("## 4. By decade")
    lines.append("")
    lines.append(df_to_md(by_decade))
    lines.append("")
    lines.append("## 5. What kind of T1 was reached (hostlev x source)")
    lines.append("")
    lines.append("`hostlev` is the MIDB hostility level: 1 = no militarized action")
    lines.append("(diplomatic originator), 2 = threat to use force.")
    lines.append("")
    lines.append(df_to_md(crosstab.reset_index()))
    lines.append("")
    lines.append("## 6. Sanity check")
    lines.append("")
    if ref_top_set:
        lines.append(
            f"Top-10 T0 -> T1 initiators overlap with top-10 overall T1 "
            f"initiators (`t1_top_initiators.csv`): **{len(overlap)}/10**."
        )
        if overlap:
            lines.append("")
            lines.append("Shared: " + ", ".join(overlap))
    else:
        lines.append(
            "Reference file `t1_top_initiators.csv` not found - overlap check skipped."
        )
    lines.append("")
    lines.append("![T0 -> T1 by decade](../../output/charts/t0_to_t1_by_decade.png)")
    lines.append("")

    text = "\n".join(lines)
    report_path = os.path.join(OUT_ANALYSIS, "t0_to_t1_report.md")
    with open(report_path, "w") as f:
        f.write(text)
    return report_path


def main() -> int:
    cohort, n_t0_total = load_cohort()
    cohort = enrich(cohort)
    stats = write_outputs(cohort, n_t0_total)
    report_path = write_report(stats)
    print(f"Cohort rows: {len(cohort):,}")
    print(f"T0 transitions (denominator): {n_t0_total:,}")
    print(f"Report -> {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
