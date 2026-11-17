"""Stage 7 of the Wikipedia tier-extraction pipeline: cross-dataset
validation + diagnostics.

Two passes:

  1. Cross-dataset comparison. For each row in the Wikipedia output,
     look up the (year, initiator_gwno, target_gwno) tuple in the
     combined ground truth (`conflict_dyads_full.csv`). Classify each
     row as:

       - agreement: at least one ground-truth dataset has the same
         (year, ig, tg, tier).
       - disagreement: at least one dataset has (year, ig, tg) at a
         different tier (and at least one at any tier at all).
       - new: not in any ground-truth dataset.

     Splits compound ground-truth sources on `_` so e.g.
     `MIDB_EUSANCT` contributes to both the MIDB and EUSANCT lists.

  2. Diagnostics. Per-tier, per-year, and per-source rollups, plus
     the GWN-resolution rate, top dyads, and transition distribution.

Outputs:

  - `data/processed/conflict_dyads_wikipedia.csv` (overwritten with
    three new columns: `agreement_datasets`, `disagreement_datasets`,
    `is_new`)
  - `output/analysis/wiki_validation_report.md`
  - `output/analysis/wiki_extraction_diagnostics.{md,csv}`
  - `output/analysis/wiki_mismatch_table.csv` (the long-form table
    the validator builds, useful for spot-checking)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = ROOT / "data" / "processed"
TMP = ROOT / "tmp"
OUT = ROOT / "output" / "analysis"

WIKI_CSV = DATA_PROCESSED / "conflict_dyads_wikipedia.csv"
GT_CSV = DATA_PROCESSED / "conflict_dyads_full.csv"
REPORT_MD = OUT / "wiki_validation_report.md"
DIAG_MD = OUT / "wiki_extraction_diagnostics.md"
DIAG_CSV = OUT / "wiki_extraction_diagnostics.csv"
MISMATCH_CSV = OUT / "wiki_mismatch_table.csv"

TIER_RANK = {"T1": 1, "T2": 2, "T3": 3, "T4": 4, "T5": 5}
TIER_LABEL = {
    "T1": "T1-Diplomatic Crisis",
    "T2": "T2-Economic Coercion",
    "T3": "T3-Proxy/Indirect Military",
    "T4": "T4-Limited Military",
    "T5": "T5-Strategic War",
}

# The wiki CSV columns (must match stage 5/6)
WIKI_COLUMNS = [
    "year", "initiator", "target", "hostlev", "uiw_tier", "tier_label",
    "initiator_gwno", "target_gwno", "source", "conflict_id", "dyad_id",
    "in_conflict", "side_backed", "intensity_level", "D_k", "attribution",
    "selective", "targeted", "corroborated", "incompatibility",
    "territory_name", "region", "n_conflicts_aggregated", "explanation",
    "start_year", "end_year", "year_status", "pair_confidence",
    "n_pairs_in_conflict", "article_id", "unresolved",
]
# Three new columns
NEW_COLUMNS = ["agreement_datasets", "disagreement_datasets", "is_new"]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wiki", default=str(WIKI_CSV))
    p.add_argument("--ground-truth", default=str(GT_CSV))
    p.add_argument("--report", default=str(REPORT_MD))
    p.add_argument("--diagnostics-md", default=str(DIAG_MD))
    p.add_argument("--diagnostics-csv", default=str(DIAG_CSV))
    p.add_argument("--mismatch-out", default=str(MISMATCH_CSV))
    p.add_argument("--year-min", type=int, default=2010)
    p.add_argument("--year-max", type=int, default=2014)
    return p.parse_args()


def _display_path(path: str) -> str:
    """Show repo-relative paths in generated reports when possible."""
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def _load_csv(path: str) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _coerce_int(v) -> int | None:
    if v is None or v == "":
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return int(float(s))
        except (TypeError, ValueError):
            return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _coerce_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes"}
    if isinstance(v, (int, float)):
        return bool(v)
    return False


def _tier_from_label(label: str) -> str | None:
    if not label:
        return None
    for t in TIER_RANK:
        if label.startswith(t + "-") or label == t:
            return t
    return None


def _split_compound_source(source: str) -> list[str]:
    """Split a ground-truth source like 'MIDB_EUSANCT' into
    ['MIDB', 'EUSANCT']."""
    if not source:
        return []
    return [s.strip() for s in source.replace("-", "_").split("_") if s.strip()]


def main() -> int:
    args = _parse_args()

    print("=" * 72)
    print("Wikipedia cross-dataset validation + diagnostics (stage 7)")
    print("=" * 72)

    if not Path(args.wiki).exists():
        print(f"Missing input: {args.wiki}", file=sys.stderr)
        return 1
    if not Path(args.ground_truth).exists():
        print(f"Missing input: {args.ground_truth}", file=sys.stderr)
        return 1

    print(f"[1] Loading Wikipedia output from {args.wiki}...")
    wiki_rows = _load_csv(args.wiki)
    print(f"    {len(wiki_rows):,} rows")

    print(f"[2] Loading ground truth from {args.ground_truth}...")
    gt_rows = _load_csv(args.ground_truth)
    print(f"    {len(gt_rows):,} rows")

    # ------------------------------------------------------------------
    # Build ground-truth lookup: (year, ig, tg) -> {datasets: {tier: set}}
    # Splits compound sources per the spec.
    # ------------------------------------------------------------------
    print(f"[3] Building ground-truth lookup (splitting compound sources on `_`)...")
    gt_lookup: dict[tuple, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for r in gt_rows:
        y = _coerce_int(r.get("year"))
        ig = _coerce_int(r.get("initiator_gwno"))
        tg = _coerce_int(r.get("target_gwno"))
        tier = _tier_from_label(r.get("tier_label", ""))
        src = (r.get("source") or "").strip()
        if None in (y, ig, tg) or tier is None or ig == tg:
            continue
        for ds in _split_compound_source(src):
            if not ds:
                continue
            gt_lookup[(y, ig, tg)][ds].add(tier)
    print(f"    unique (year, ig, tg) keys: {len(gt_lookup):,}")

    # ------------------------------------------------------------------
    # Classify each wiki row
    # ------------------------------------------------------------------
    print(f"[4] Classifying wiki rows against ground truth...")
    n_agreement = 0
    n_disagreement = 0
    n_new = 0
    n_unresolvable_year = 0
    wiki_with_diag: list[dict] = []
    for r in wiki_rows:
        # Parse year - might be sentinel int or unknown-year string
        # (stage 5 emits -1 for both-years-unknown)
        y_raw = r.get("year", "")
        try:
            y = int(y_raw)
        except (TypeError, ValueError):
            y = None
        ig = _coerce_int(r.get("initiator_gwno"))
        tg = _coerce_int(r.get("target_gwno"))
        w_tier = _tier_from_label(r.get("tier_label", ""))

        if y is None or ig is None or tg is None or w_tier is None:
            # Can't cross-validate this row (sentinel year or unresolved)
            r["agreement_datasets"] = ""
            r["disagreement_datasets"] = ""
            r["is_new"] = ""
            n_unresolvable_year += 1
            wiki_with_diag.append(r)
            continue

        gt_at_key = gt_lookup.get((y, ig, tg), {})
        if not gt_at_key:
            # New: not in any ground-truth dataset
            r["agreement_datasets"] = ""
            r["disagreement_datasets"] = ""
            r["is_new"] = "True"
            n_new += 1
        else:
            agreeing = sorted([ds for ds, tiers in gt_at_key.items() if w_tier in tiers])
            contradicting = sorted([ds for ds, tiers in gt_at_key.items() if w_tier not in tiers])
            r["agreement_datasets"] = ";".join(agreeing)
            r["disagreement_datasets"] = ";".join(contradicting)
            if agreeing:
                n_agreement += 1
            elif contradicting:
                n_disagreement += 1
            else:
                # Shouldn't reach here, but be defensive
                n_new += 1
            r["is_new"] = "False"
        wiki_with_diag.append(r)

    n_classified = n_agreement + n_disagreement + n_new
    print(f"    agreement:    {n_agreement:>6,} ({100*n_agreement/max(n_classified,1):.1f}%)")
    print(f"    disagreement: {n_disagreement:>6,} ({100*n_disagreement/max(n_classified,1):.1f}%)")
    print(f"    new:          {n_new:>6,} ({100*n_new/max(n_classified,1):.1f}%)")
    print(f"    unresolvable (sentinel year or missing gwno): {n_unresolvable_year:,}")

    # ------------------------------------------------------------------
    # Write wiki CSV with the three new columns
    # ------------------------------------------------------------------
    print()
    print(f"[5] Writing updated {args.wiki}...")
    out_cols = WIKI_COLUMNS + NEW_COLUMNS
    Path(args.wiki).parent.mkdir(parents=True, exist_ok=True)
    with open(args.wiki, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_cols)
        w.writeheader()
        for r in wiki_with_diag:
            w.writerow({k: r.get(k, "") for k in out_cols})
    print(f"    Wrote {args.wiki}")

    # ------------------------------------------------------------------
    # Build the per-year P/R/F1 against ground truth (legacy validation)
    # ------------------------------------------------------------------
    print()
    print(f"[6] Per-year P/R/F1 for {args.year_min}-{args.year_max}...")
    wiki_window = [r for r in wiki_rows if (
        (lambda y: y is not None and args.year_min <= y <= args.year_max)(
            _coerce_int(r.get("year"))
        )
    )]
    gt_window = [r for r in gt_rows if (
        (lambda y: y is not None and args.year_min <= y <= args.year_max)(
            _coerce_int(r.get("year"))
        )
        and _tier_from_label(r.get("tier_label", "")) is not None
    )]
    print(f"    wiki rows in window: {len(wiki_window):,}")
    print(f"    GT conflict rows in window: {len(gt_window):,}")

    wiki_keys = {
        (_coerce_int(r["year"]), _coerce_int(r["initiator_gwno"]),
         _coerce_int(r["target_gwno"]), _tier_from_label(r.get("tier_label", "")))
        for r in wiki_window
        if _coerce_int(r.get("year")) is not None
        and _coerce_int(r.get("initiator_gwno")) is not None
        and _coerce_int(r.get("target_gwno")) is not None
    }
    gt_keys = {
        (_coerce_int(r["year"]), _coerce_int(r["initiator_gwno"]),
         _coerce_int(r["target_gwno"]), _tier_from_label(r.get("tier_label", "")))
        for r in gt_window
        if _coerce_int(r.get("year")) is not None
        and _coerce_int(r.get("initiator_gwno")) is not None
        and _coerce_int(r.get("target_gwno")) is not None
    }

    per_year_metrics: dict[int, dict] = {}
    for year in range(args.year_min, args.year_max + 1):
        wy = {k for k in wiki_keys if k[0] == year}
        gy = {k for k in gt_keys if k[0] == year}
        tp = len(wy & gy)
        fp = len(wy - gy)
        fn = len(gy - wy)
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-9)
        per_year_metrics[year] = {
            "wiki_n": len(wy), "gt_n": len(gy), "tp": tp, "fp": fp, "fn": fn,
            "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
        }
        print(f"    {year}: P={prec:.3f} R={rec:.3f} F1={f1:.3f} (TP={tp}, FP={fp}, FN={fn})")

    # Per-tier metrics
    per_tier: dict[str, dict] = {}
    for tier in TIER_RANK:
        wt = {k for k in wiki_keys if k[3] == tier}
        gt = {k for k in gt_keys if k[3] == tier}
        tp = len(wt & gt)
        fp = len(wt - gt)
        fn = len(gt - wt)
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-9)
        per_tier[tier] = {
            "tier": tier, "label": TIER_LABEL[tier],
            "n_wiki": len(wt), "n_gt": len(gt),
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
        }

    # ------------------------------------------------------------------
    # Write the validation report
    # ------------------------------------------------------------------
    print()
    print(f"[7] Writing {args.report}...")
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "# Wikipedia tier extraction — validation report",
        "",
        f"**Window for per-year P/R/F1:** {args.year_min} - {args.year_max}",
        "",
        f"**Wikipedia output:** `{_display_path(args.wiki)}` (v27.0 scheme)",
        f"**Ground truth:** `{_display_path(args.ground_truth)}`",
        "",
        "## Tier crosswalk (v27.0)",
        "",
        "| Tier | v27.0 label | hostlev |",
        "|---|---|---|",
        "| T1 | T1-Diplomatic Crisis | 1 |",
        "| T2 | T2-Economic Coercion | 2 |",
        "| T3 | T3-Proxy/Indirect Military | 3 |",
        "| T4 | T4-Limited Military | 4 |",
        "| T5 | T5-Strategic War | 5 |",
        "",
        "## Per-year metrics (v27.0 Wikipedia vs. ground truth)",
        "",
        "| Year | Wikipedia | GT | TP | FP | FN | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for year in range(args.year_min, args.year_max + 1):
        m = per_year_metrics[year]
        lines.append(
            f"| {year} | {m['wiki_n']} | {m['gt_n']} | {m['tp']} | {m['fp']} | {m['fn']} | "
            f"{m['precision']} | {m['recall']} | {m['f1']} |"
        )
    lines += [
        "",
        "## Per-tier metrics (window-wide)",
        "",
        "| Tier | Wikipedia | GT | TP | FP | FN | Precision | Recall | F1 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for t, m in per_tier.items():
        lines.append(
            f"| {t} ({m['label']}) | {m['n_wiki']} | {m['n_gt']} | {m['tp']} | {m['fp']} | {m['fn']} | "
            f"{m['precision']} | {m['recall']} | {m['f1']} |"
        )

    lines += [
        "",
        "## Cross-dataset comparison (Wikipedia vs ground truth, all years)",
        "",
        "Each Wikipedia row is compared against the ground truth by "
        "(year, initiator_gwno, target_gwno). Compound ground-truth "
        "sources (e.g. `MIDB_EUSANCT`) are split on `_` so each "
        "contributing dataset is listed independently.",
        "",
        f"- Total classified rows: {n_classified:,}",
        f"- Agreement:   {n_agreement:,} ({100*n_agreement/max(n_classified,1):.1f}%)",
        f"- Disagreement: {n_disagreement:,} ({100*n_disagreement/max(n_classified,1):.1f}%)",
        f"- New:         {n_new:,} ({100*n_new/max(n_classified,1):.1f}%)",
        f"- Unresolvable (sentinel year or missing gwno): {n_unresolvable_year:,}",
        "",
        "### Per-tier breakdown",
        "",
        "| Tier | n | agreement | disagreement | new |",
        "|------|---|-----------|--------------|-----|",
    ]
    # Per-tier breakdown of agreement/disagreement/new
    tier_breakdown: dict[str, dict] = {t: {"n": 0, "agree": 0, "disagree": 0, "new": 0} for t in TIER_RANK}
    for r in wiki_with_diag:
        w_tier = _tier_from_label(r.get("tier_label", ""))
        if w_tier is None:
            continue
        # Skip unresolvable rows
        if r.get("is_new") == "" and r.get("agreement_datasets") == "" and r.get("disagreement_datasets") == "":
            continue
        tier_breakdown[w_tier]["n"] += 1
        if r.get("is_new") == "True":
            tier_breakdown[w_tier]["new"] += 1
        elif r.get("agreement_datasets"):
            tier_breakdown[w_tier]["agree"] += 1
        elif r.get("disagreement_datasets"):
            tier_breakdown[w_tier]["disagree"] += 1
    for t in TIER_RANK:
        b = tier_breakdown[t]
        lines.append(f"| {t} | {b['n']} | {b['agree']} | {b['disagree']} | {b['new']} |")

    lines += [
        "",
        "### Top 20 disagreements",
        "",
        "Rows where Wikipedia's tier differs from at least one ground-truth dataset.",
        "",
        "| Year | Initiator | Target | Wiki tier | Datasets agreeing | Datasets disagreeing |",
        "|---|---|---|---|---|---|",
    ]
    disagree_rows = [r for r in wiki_with_diag if r.get("disagreement_datasets") and r.get("is_new") == "False"]
    disagree_rows.sort(key=lambda r: (
        _coerce_int(r.get("year")) or 9999,
        r.get("tier_label") or "",
        r.get("initiator") or "",
        r.get("target") or "",
    ))
    for r in disagree_rows[:20]:
        lines.append(
            f"| {r.get('year','')} | {r.get('initiator','')} | {r.get('target','')} | "
            f"{r.get('tier_label','')} | {r.get('agreement_datasets','') or '(none)'} | "
            f"{r.get('disagreement_datasets','')} |"
        )

    lines += [
        "",
        "## Notes",
        "",
        "- Agreement = at least one ground-truth dataset has the same (year, ig, tg, tier).",
        "- Disagreement = (year, ig, tg) is in at least one dataset but at a different tier.",
        "- New = (year, ig, tg) is not in any ground-truth dataset.",
        "- Compound source values (e.g. `MIDB_EUSANCT`) are split on `_` so each contributing dataset is listed.",
        "- Wiki rows with sentinel year values (e.g. `unknown start year`) or missing gwno codes cannot be cross-validated; they are counted separately as `unresolvable`.",
        "",
    ]
    with open(args.report, "w") as f:
        f.write("\n".join(lines))
    print(f"    Wrote {args.report}")

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    print()
    print(f"[8] Writing {args.diagnostics_md} and {args.diagnostics_csv}...")

    # Per-source counts
    source_counts: Counter = Counter()
    for r in wiki_rows:
        source_counts[r.get("source", "UNKNOWN")] += 1

    # GWN resolution rate per tier
    gwn_resolution: dict[str, dict] = {}
    for tier in TIER_RANK:
        tier_rows = [r for r in wiki_rows if _tier_from_label(r.get("tier_label", "")) == tier]
        if not tier_rows:
            gwn_resolution[tier] = {"n": 0, "n_resolved": 0, "rate": 0.0}
            continue
        n_resolved = sum(
            1 for r in tier_rows
            if _coerce_int(r.get("initiator_gwno")) is not None
            and _coerce_int(r.get("target_gwno")) is not None
        )
        gwn_resolution[tier] = {
            "n": len(tier_rows),
            "n_resolved": n_resolved,
            "rate": round(n_resolved / len(tier_rows), 3),
        }

    # Top 20 dyads per tier
    top_dyads: dict[str, Counter] = {}
    for tier in TIER_RANK:
        c: Counter = Counter()
        for r in wiki_rows:
            if _tier_from_label(r.get("tier_label", "")) == tier:
                c[(r.get("initiator", ""), r.get("target", ""))] += 1
        top_dyads[tier] = c

    # Year-over-year transition distribution
    dyad_tier_seq: dict[tuple, list[tuple[int, str]]] = defaultdict(list)
    for r in wiki_rows:
        y = _coerce_int(r.get("year"))
        i = r.get("initiator", "")
        t = r.get("target", "")
        tier = _tier_from_label(r.get("tier_label", ""))
        if y is not None and i and t and tier and y >= args.year_min and y <= args.year_max:
            dyad_tier_seq[(i, t)].append((y, tier))
    transitions: list[str] = []
    for seq in dyad_tier_seq.values():
        seq = sorted(seq)
        for (y1, t1), (y2, t2) in zip(seq, seq[1:]):
            if y2 - y1 != 1:
                continue
            if TIER_RANK[t2] > TIER_RANK[t1]:
                transitions.append("escalate")
            elif TIER_RANK[t2] < TIER_RANK[t1]:
                transitions.append("deescalate")
            else:
                transitions.append("persist")
    trans_counter = Counter(transitions)
    n_total_trans = sum(trans_counter.values())

    diag_lines = [
        "# Wikipedia extraction diagnostics",
        "",
        "## Per-source row counts (all years)",
        "",
        "| Source | Rows |",
        "|---|---|",
    ]
    for s, n in sorted(source_counts.items(), key=lambda x: -x[1]):
        diag_lines.append(f"| {s} | {n:,} |")
    diag_lines += [
        "",
        "## GWN resolution rate per tier (all years)",
        "",
        "| Tier | Resolved | Total | Rate |",
        "|---|---|---|---|",
    ]
    for t, m in gwn_resolution.items():
        diag_lines.append(f"| {t} | {m['n_resolved']:,} | {m['n']:,} | {m['rate']*100:.1f}% |")
    diag_lines += [
        "",
        "## Top 20 dyads per tier (all years)",
        "",
    ]
    for tier in TIER_RANK:
        diag_lines.append(f"### {tier} ({TIER_LABEL[tier]})")
        diag_lines.append("")
        diag_lines.append("| Initiator | Target | Events |")
        diag_lines.append("|---|---|---|")
        for (i, t), n in top_dyads[tier].most_common(20):
            diag_lines.append(f"| {i} | {t} | {n} |")
        diag_lines.append("")

    diag_lines += [
        "## Year-over-year transition distribution (Wikipedia extraction, in window)",
        "",
        f"- Total dyad-year transitions: {n_total_trans:,}",
    ]
    for k in ("escalate", "persist", "deescalate"):
        n = trans_counter.get(k, 0)
        diag_lines.append(f"- {k}: {n:,} ({n/max(n_total_trans,1)*100:.1f}%)")
    diag_lines.append("")

    with open(args.diagnostics_md, "w") as f:
        f.write("\n".join(diag_lines))
    print(f"    Wrote {args.diagnostics_md}")

    with open(args.diagnostics_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["section", "key", "value"])
        for year in range(args.year_min, args.year_max + 1):
            m = per_year_metrics[year]
            w.writerow(["per_year", str(year), json.dumps(m)])
        for t, m in per_tier.items():
            w.writerow(["per_tier", t, json.dumps(m)])
        for s, n in source_counts.items():
            w.writerow(["source_count", s, n])
        for t, m in gwn_resolution.items():
            w.writerow(["gwn_resolution", t, json.dumps(m)])
        for k, n in trans_counter.items():
            w.writerow(["transition", k, n])
    print(f"    Wrote {args.diagnostics_csv}")

    # ------------------------------------------------------------------
    # Mismatch table
    # ------------------------------------------------------------------
    print()
    print(f"[9] Writing {args.mismatch_out}...")
    Path(args.mismatch_out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.mismatch_out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "wiki_year", "wiki_initiator", "wiki_target", "wiki_tier",
            "gt_year", "gt_initiator", "gt_target", "gt_tier",
            "tier_match", "mismatch_kind", "notes",
        ])
        w.writeheader()
        # Build GT key -> row lookup for the validation window
        gt_window_by_key = {}
        for r in gt_window:
            y = _coerce_int(r.get("year"))
            ig = _coerce_int(r.get("initiator_gwno"))
            tg = _coerce_int(r.get("target_gwno"))
            tier = _tier_from_label(r.get("tier_label", ""))
            if None in (y, ig, tg) or tier is None:
                continue
            gt_window_by_key[(y, ig, tg)] = (tier, r.get("tier_label", ""))
        # Walk the union of wiki-window keys and GT-window keys
        wiki_window_keys = {
            (
                _coerce_int(r.get("year")),
                _coerce_int(r.get("initiator_gwno")),
                _coerce_int(r.get("target_gwno")),
            )
            for r in wiki_window
            if _coerce_int(r.get("year")) is not None
            and _coerce_int(r.get("initiator_gwno")) is not None
            and _coerce_int(r.get("target_gwno")) is not None
        }
        gt_window_keys = set(gt_window_by_key.keys())
        for k in sorted(wiki_window_keys | gt_window_keys):
            w_tier = None
            for r in wiki_window:
                rk = (
                    _coerce_int(r.get("year")),
                    _coerce_int(r.get("initiator_gwno")),
                    _coerce_int(r.get("target_gwno")),
                )
                if rk == k:
                    w_tier = _tier_from_label(r.get("tier_label", ""))
                    break
            g_info = gt_window_by_key.get(k)
            g_tier = g_info[0] if g_info else None
            g_label = g_info[1] if g_info else ""
            if w_tier is None and g_tier is not None:
                kind = "only_in_ground_truth"
                tier_match = None
                notes = "no Wikipedia event in the validation window"
            elif g_tier is None and w_tier is not None:
                kind = "only_in_wiki"
                tier_match = None
                notes = "no ground-truth event in the validation window"
            else:
                tier_match = (w_tier == g_tier)
                if tier_match:
                    kind = "match"
                elif TIER_RANK[w_tier] > TIER_RANK[g_tier]:
                    kind = "tier_over"
                else:
                    kind = "tier_under"
                notes = f"v27.0={w_tier}, legacy={g_tier}"
            w.writerow({
                "wiki_year": k[0] if w_tier is not None else "",
                "wiki_initiator": k[1] if w_tier is not None else "",
                "wiki_target": k[2] if w_tier is not None else "",
                "wiki_tier": w_tier or "",
                "gt_year": k[0] if g_tier is not None else "",
                "gt_initiator": k[1] if g_tier is not None else "",
                "gt_target": k[2] if g_tier is not None else "",
                "gt_tier": g_tier or "",
                "tier_match": tier_match if tier_match is not None else "",
                "mismatch_kind": kind,
                "notes": notes,
            })
    print(f"    Wrote {args.mismatch_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
