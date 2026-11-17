"""Orchestrator for the Wikipedia tier-extraction pipeline (v2).

Runs the seven pipeline stages in order, with consistent logging, a
JSON manifest, a JSON state file, and a final summary. Stages 3, 4,
and 6 call Ollama over HTTP; the orchestrator itself stays on the
TIERS box.

Stages:
  1. gwn_map            — CShapes -> Wikipedia API -> GWN code map
  2. filter             — DuckDB country scan + Python bilateral gate
  3. t01_filter         — LLM 0/1 (is this article an interstate conflict?)
  4. t45_extract        — LLM per-article extraction (tier, countries,
                          duration, explanation, directed pairs)
  5. aggregate          — Pure Python. Expand duration to per-year rows,
                          GWN-resolve, max-tier-per-dyad-year.
  6. country_resolve    — LLM. Resolve unmapped country names against
                          the canonical list; preserve raw in parens.
  7. validate           — Cross-dataset comparison + diagnostics report.

Subcommands:
  run        Execute all stages in order. Always re-runs; no skip
             logic. Optional --stages 1-7 to restrict.
  status     Show which outputs exist on disk, their sizes/mtimes, and
             the last run's manifest summary. No side effects.
  clean      Remove intermediates. Optional --stages 1-7 or --all.

Configuration is read from environment variables:
  OLLAMA_BASE_URL         default http://192.168.86.18:1234/v1
  OLLAMA_MODEL            default nemotron-3-nano:4b
  OLLAMA_N_PARALLEL       default 5
  OLLAMA_BATCH_SIZE       default 3   (LLM 0/1 filter)
  PIPELINE_MIN_CONFIDENCE default 0.7
  PIPELINE_MAX_ARTICLES   default 0  (no cap)
  PIPELINE_LOG            default tmp/wiki_pipeline.log

  (For backward compat, the legacy LMSTUDIO_* env vars are also read as
   fallbacks when OLLAMA_* is unset.)

Outputs:
  tmp/wiki_pipeline.log            one line per stage event
  tmp/wiki_pipeline_manifest.json  per-stage outputs, timestamps, byte sizes
  tmp/wiki_pipeline_state.json     per-stage config fingerprint (display only)
  tmp/wiki_pipeline_run.json       final run summary

The child scripts are imported and their `main()` is called with
sys.argv re-bound for the duration of the call. This keeps the
orchestrator fast (no per-stage Python startup) and gives proper
exception propagation.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp"
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
OUT_ANALYSIS = ROOT / "output" / "analysis"

LOG_FILE = TMP / "wiki_pipeline.log"
MANIFEST_JSON = TMP / "wiki_pipeline_manifest.json"
STATE_JSON = TMP / "wiki_pipeline_state.json"
RUN_SUMMARY_JSON = TMP / "wiki_pipeline_run.json"

# External Python packages required by individual stages. Checked at
# orchestrator startup so the user gets a single clear error pointing
# at the venv if anything is missing, instead of failing deep in
# stage 1.
REQUIRED_PACKAGES: dict[str, str] = {
    "pandas": "data processing",
    "pyarrow": "parquet I/O",
    "duckdb": "DuckDB columnar filter (stage 2)",
    "openai": "Ollama client (stages 3, 4, 6)",
}


def _check_dependencies(logger: logging.Logger | None = None) -> list[str]:
    """Return the names of any required packages that are not currently
    importable in the running Python interpreter. Empty list means all
    packages are present."""
    missing: list[str] = []
    for name in REQUIRED_PACKAGES:
        try:
            importlib.import_module(name)
        except ImportError:
            missing.append(name)
    return missing


def _venv_hint() -> str:
    """If a venv exists in the project root, suggest the user activate
    it. Otherwise point at the README's install section."""
    venv = ROOT / ".venv"
    if venv.exists() and (venv / "bin" / "python").exists():
        return (
            f"A virtual environment exists at {venv}.\n"
            f"  Activate it:  source {venv}/bin/activate\n"
            f"  Or run:       {venv}/bin/python scripts/build/wiki_pipeline.py ..."
        )
    return (
        "No .venv found. Create one and install the requirements:\n"
        "  uv venv && uv pip install -r requirements.txt\n"
        "  # or:\n"
        "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt\n"
        f"See {ROOT / 'README.md'} for details."
    )


@dataclass
class PipelineConfig:
    """Resolved configuration for one pipeline run."""

    ollama_base_url: str
    ollama_model: str
    n_parallel: int
    batch_size: int
    min_confidence: float
    max_articles: int
    log_file: Path
    root: Path

    @classmethod
    def from_env(cls, root: Path) -> "PipelineConfig":
        # Prefer OLLAMA_* env vars, fall back to LMSTUDIO_* for backward compat
        base_url = (
            os.environ.get("OLLAMA_BASE_URL")
            or os.environ.get("LMSTUDIO_BASE_URL")
            or "http://192.168.86.18:1234/v1"
        )
        model = (
            os.environ.get("OLLAMA_MODEL")
            or os.environ.get("LMSTUDIO_MODEL")
            or os.environ.get("LMSTUDIO_MODEL_NAME")
            or "nemotron-3-nano:4b"
        )
        n_parallel = int(
            os.environ.get("OLLAMA_N_PARALLEL")
            or os.environ.get("LMSTUDIO_N_PARALLEL")
            or "5"
        )
        batch_size = int(os.environ.get("OLLAMA_BATCH_SIZE", "3"))
        return cls(
            ollama_base_url=base_url,
            ollama_model=model,
            n_parallel=n_parallel,
            batch_size=batch_size,
            min_confidence=float(os.environ.get("PIPELINE_MIN_CONFIDENCE", "0.7")),
            max_articles=int(os.environ.get("PIPELINE_MAX_ARTICLES", "0")),
            log_file=Path(os.environ.get("PIPELINE_LOG", str(LOG_FILE))),
            root=root,
        )

    def fingerprint(self) -> str:
        """Stable hash of the config that affects pipeline output."""
        canonical = json.dumps(
            {
                "ollama_base_url": self.ollama_base_url,
                "ollama_model": self.ollama_model,
                "n_parallel": self.n_parallel,
                "batch_size": self.batch_size,
                "min_confidence": self.min_confidence,
                "max_articles": self.max_articles,
            },
            sort_keys=True,
        )
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()[:16]


@dataclass
class StageDef:
    """One stage of the pipeline."""

    number: int
    name: str
    child_module: str
    description: str
    outputs: list[Path]
    build_args: Callable[[PipelineConfig], list[str]]


def _stage_outputs(root: Path) -> dict[int, list[Path]]:
    # v2 pipeline: 7 stages. The user provides the Wiki export under
    # data/raw/structured-wikipedia/<name>/data/; the filter (stage 2)
    # auto-discovers the parquet shards.
    return {
        1: [
            DATA_PROCESSED / "wiki_gwn_map.csv",
            DATA_PROCESSED / "wiki_gwn_overrides.csv",
            TMP / "wiki_gwn_map_diag.json",
        ],
        2: [
            TMP / "wiki_tier_candidates.parquet",
            TMP / "wiki_filter_stats.json",
        ],
        3: [
            TMP / "wiki_t01_filter_kept.jsonl",
            TMP / "wiki_t01_filter_rejected.jsonl",
            TMP / "wiki_t01_filter_run.json",
        ],
        4: [
            TMP / "wiki_t45_extracted.jsonl",
            TMP / "wiki_t45_failed.jsonl",
            TMP / "wiki_t45_run.json",
        ],
        5: [
            DATA_PROCESSED / "conflict_dyads_wikipedia.csv",
            DATA_PROCESSED / "conflict_dyads_wikipedia.parquet",
            TMP / "wiki_year_tier_counts.csv",
            TMP / "wiki_mismatch_pairs.jsonl",
            TMP / "wiki_unresolved_pairs.log",
        ],
        6: [
            DATA_PROCESSED / "conflict_dyads_wikipedia.csv",  # rewritten in place
            TMP / "wiki_country_resolution.json",
            TMP / "wiki_country_resolution_run.json",
        ],
        7: [
            DATA_PROCESSED / "conflict_dyads_wikipedia.csv",  # rewritten in place
            OUT_ANALYSIS / "wiki_validation_report.md",
            OUT_ANALYSIS / "wiki_mismatch_table.csv",
            OUT_ANALYSIS / "wiki_extraction_diagnostics.md",
            OUT_ANALYSIS / "wiki_extraction_diagnostics.csv",
        ],
    }


def _build_stage_defs(root: Path) -> list[StageDef]:
    outputs = _stage_outputs(root)
    return [
        StageDef(
            number=1,
            name="gwn_map",
            child_module="wiki_build_gwn_map",
            description="Query Wikidata for CShapes country names -> GWN codes; write wiki_gwn_map.csv.",
            outputs=outputs[1],
            build_args=lambda _c: [],
        ),
        StageDef(
            number=2,
            name="filter",
            child_module="wiki_filter_candidates",
            description="Two-stage filter: DuckDB country-only + Python bilateral gate. Auto-discovers parquet shards under data/raw/structured-wikipedia/<name>/data/. Outputs ~50-60k LLM-path articles.",
            outputs=outputs[2],
            build_args=lambda c: (["--max-rows", str(c.max_articles)] if c.max_articles else []),
        ),
        StageDef(
            number=3,
            name="t01_filter",
            child_module="wiki_extract_llm_t01_filter",
            description="Batched LLM 0/1 filter (3 articles per prompt, Ollama). Asks whether each bilateral article contains a conflict or dispute between nation states. Broadened from the legacy t123 filter to admit diplomatic friction alongside wars.",
            outputs=outputs[3],
            build_args=lambda c: [
                "--base-url", c.ollama_base_url,
                "--model", c.ollama_model,
                "--n-parallel", str(c.n_parallel),
                "--batch-size", str(c.batch_size),
                *(["--max-articles", str(c.max_articles)] if c.max_articles else []),
            ],
        ),
        StageDef(
            number=4,
            name="t45_extract",
            child_module="wiki_extract_llm_t45",
            description="Per-article LLM extraction (1-article/prompt, Ollama). Emits tier, start_year, end_year, explanation, and a list of directed (initiator, target, confidence, implied) pairs. Replaces the legacy tier-classifier + event-extractor + correlate steps with a single call.",
            outputs=outputs[4],
            build_args=lambda c: [
                "--base-url", c.ollama_base_url,
                "--model", c.ollama_model,
                "--n-parallel", str(c.n_parallel),
                *(["--max-articles", str(c.max_articles)] if c.max_articles else []),
            ],
        ),
        StageDef(
            number=5,
            name="aggregate",
            child_module="wiki_aggregate_dyads",
            description="Pure-Python aggregation. For each article: drop low-confidence pairs, apply -0.2 discount to implied pairs, resolve country names to GWN codes, expand [start_year, end_year] into one row per year, pick max tier per (year, ig, tg). Emits year_status='' for normal, 'unknown_start' / 'unknown_end' / 'unknown' for sentinels.",
            outputs=outputs[5],
            build_args=lambda c: ["--min-confidence", str(c.min_confidence)],
        ),
        StageDef(
            number=6,
            name="country_resolve",
            child_module="wiki_resolve_unmapped_countries",
            description="LLM pass over unresolved country names from stage 5. Maps each to a canonical name; writes the result as 'Resolved (raw: Original)' in the original column, with downstream consumers treating the parenthetical as if it does not exist. Only runs when stage 5 emitted unresolved rows.",
            outputs=outputs[6],
            build_args=lambda c: [
                "--base-url", c.ollama_base_url,
                "--model", c.ollama_model,
                "--n-parallel", str(c.n_parallel),
            ],
        ),
        StageDef(
            number=7,
            name="validate",
            child_module="wiki_cross_dataset_validate",
            description="Cross-dataset comparison (agreement/disagreement/new vs conflict_dyads_full.csv, compound sources split on `_`) + diagnostics (per-year P/R/F1, per-tier metrics, source counts, GWN resolution, top dyads, transitions). Writes three new columns to conflict_dyads_wikipedia.csv: agreement_datasets, disagreement_datasets, is_new.",
            outputs=outputs[7],
            build_args=lambda _c: [],
        ),
    ]


def _setup_logging(log_file: Path) -> logging.Logger:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("wiki_pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s  %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def _format_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def _format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"


def _path_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "bytes": 0, "mtime": None}
    stat = path.stat()
    if path.is_dir():
        total = 0
        try:
            for child in path.rglob("*"):
                if child.is_file():
                    total += child.stat().st_size
        except OSError:
            total = 0
        # mtime of the most recently modified file
        try:
            mtime = max(
                (child.stat().st_mtime for child in path.rglob("*") if child.is_file()),
                default=stat.st_mtime,
            )
        except (OSError, ValueError):
            mtime = stat.st_mtime
        return {"exists": True, "bytes": total, "mtime": mtime, "is_dir": True}
    return {
        "exists": True,
        "bytes": stat.st_size,
        "mtime": stat.st_mtime,
        "is_dir": False,
    }


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


@dataclass
class StageResult:
    stage: StageDef
    started_at: str
    finished_at: str
    duration_s: float
    exit_code: int
    output_bytes: int
    output_paths_existing: list[str]
    error: str | None = None


class WikiPipeline:
    """Coordinator for the six-stage Wikipedia tier pipeline."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = _setup_logging(config.log_file)
        self.stages = _build_stage_defs(config.root)
        self.stages_by_number = {s.number: s for s in self.stages}

    def _run_child(self, stage: StageDef) -> int:
        """Import the child module and call its main() with the
        configured CLI args. Returns the child's exit code."""
        args = stage.build_args(self.config)
        self.logger.info("  cmd: python -m scripts.build.%s %s", stage.child_module, " ".join(args))
        orig_argv = sys.argv
        try:
            sys.path.insert(0, str(ROOT / "scripts" / "build"))
            sys.argv = [stage.child_module + ".py", *args]
            mod = importlib.import_module(stage.child_module)
            return int(mod.main() or 0)
        finally:
            sys.argv = orig_argv
            if str(ROOT / "scripts" / "build") in sys.path:
                sys.path.remove(str(ROOT / "scripts" / "build"))

    def status(self) -> list[dict[str, Any]]:
        manifest = _load_json(MANIFEST_JSON, {"stages": {}})
        out: list[dict[str, Any]] = []
        for s in self.stages:
            statuses = [_path_status(p) for p in s.outputs]
            total_bytes = sum(st["bytes"] for st in statuses if st["exists"])
            mtime = max(
                (st["mtime"] for st in statuses if st["mtime"] is not None),
                default=None,
            )
            manifest_entry = manifest.get("stages", {}).get(str(s.number))
            out.append(
                {
                    "number": s.number,
                    "name": s.name,
                    "description": s.description,
                    "outputs": [
                        {
                            "path": str(p),
                            **st,
                        }
                        for p, st in zip(s.outputs, statuses)
                    ],
                    "total_bytes": total_bytes,
                    "most_recent_mtime": mtime,
                    "last_run": manifest_entry,
                }
            )
        return out

    def run(self, stages: list[int], *, dry_run: bool) -> int:
        stages_to_run = [self.stages_by_number[n] for n in stages]
        if not stages_to_run:
            self.logger.error("No stages selected.")
            return 1
        self.logger.info("Pipeline starting (stages: %s)", [s.number for s in stages_to_run])
        self.logger.info("  config fingerprint: %s", self.config.fingerprint())
        if dry_run:
            self.logger.info("  DRY RUN: no stages will be executed.")
            for s in stages_to_run:
                self.logger.info("  would run stage %d (%s): %s", s.number, s.name, s.description)
            return 0

        manifest = _load_json(MANIFEST_JSON, {"stages": {}})
        state = _load_json(STATE_JSON, {"stages": {}})
        run_started = time.time()
        run_started_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(run_started))
        results: list[StageResult] = []

        for s in stages_to_run:
            self.logger.info("=" * 72)
            self.logger.info("[stage %d] %s starting", s.number, s.name)
            t0 = time.time()
            started_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
            error: str | None = None
            exit_code = 0
            try:
                exit_code = self._run_child(s)
                if exit_code != 0:
                    error = f"exit_code={exit_code}"
            except SystemExit as e:
                exit_code = int(e.code) if e.code is not None else 1
                error = f"SystemExit({exit_code})"
            except BaseException as e:
                exit_code = 1
                error = f"{type(e).__name__}: {e}"
                self.logger.exception("[stage %d] failed", s.number)
            elapsed = time.time() - t0
            finished_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0 + elapsed))

            if error is not None:
                self.logger.error(
                    "[stage %d] %s FAILED in %s: %s",
                    s.number, s.name, _format_duration(elapsed), error,
                )
                self._write_run_summary(results, run_started_iso, error_stage=s.number)
                return 1

            output_statuses = [_path_status(p) for p in s.outputs]
            total_bytes = sum(st["bytes"] for st in output_statuses if st["exists"])
            existing_paths = [str(p) for p, st in zip(s.outputs, output_statuses) if st["exists"]]
            self.logger.info(
                "[stage %d] %s done in %s (%s)",
                s.number, s.name, _format_duration(elapsed), _format_bytes(total_bytes),
            )
            results.append(
                StageResult(
                    stage=s,
                    started_at=started_iso,
                    finished_at=finished_iso,
                    duration_s=round(elapsed, 1),
                    exit_code=exit_code,
                    output_bytes=total_bytes,
                    output_paths_existing=existing_paths,
                )
            )
            manifest_entry = {
                "started_at": started_iso,
                "finished_at": finished_iso,
                "duration_s": round(elapsed, 1),
                "output_paths": [str(p) for p in s.outputs],
                "output_paths_existing": existing_paths,
                "output_bytes": total_bytes,
                "exit_code": exit_code,
                "config_fingerprint": self.config.fingerprint(),
            }
            manifest.setdefault("stages", {})[str(s.number)] = manifest_entry
            _save_json(MANIFEST_JSON, manifest)

            state_entry = {
                "config_fingerprint": self.config.fingerprint(),
                "last_run_at": finished_iso,
            }
            state.setdefault("stages", {})[str(s.number)] = state_entry
            _save_json(STATE_JSON, state)

        self._write_run_summary(results, run_started_iso, error_stage=None)
        self._print_summary(results, run_started)
        return 0

    def _write_run_summary(
        self,
        results: list[StageResult],
        run_started_iso: str,
        error_stage: int | None,
    ) -> None:
        summary = {
            "started_at": run_started_iso,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "config_fingerprint": self.config.fingerprint(),
            "stages": [
                {
                    "number": r.stage.number,
                    "name": r.stage.name,
                    "started_at": r.started_at,
                    "finished_at": r.finished_at,
                    "duration_s": r.duration_s,
                    "output_bytes": r.output_bytes,
                    "exit_code": r.exit_code,
                }
                for r in results
            ],
            "error_stage": error_stage,
        }
        _save_json(RUN_SUMMARY_JSON, summary)

    def _print_summary(self, results: list[StageResult], run_started: float) -> None:
        total = time.time() - run_started
        self.logger.info("=" * 72)
        self.logger.info("Pipeline finished in %s", _format_duration(total))
        for r in results:
            self.logger.info(
                "  stage %d  %-10s  %-12s  %s",
                r.stage.number,
                r.stage.name,
                _format_duration(r.duration_s),
                _format_bytes(r.output_bytes),
            )
        if results:
            last = results[-1]
            self.logger.info("  output: data/processed/conflict_dyads_wikipedia.csv")
            self.logger.info("  report: output/analysis/wiki_validation_report.md")
            self.logger.info("  manifest: %s", MANIFEST_JSON)

    def clean(self, stages: list[int], *, also_outputs: bool) -> int:
        for n in stages:
            s = self.stages_by_number[n]
            for p in s.outputs:
                if p.is_dir():
                    self._rm_tree(p)
                elif p.exists():
                    p.unlink()
                    self.logger.info("removed %s", p)
        # Always wipe the manifest/state files for cleaned stages
        manifest = _load_json(MANIFEST_JSON, {"stages": {}})
        state = _load_json(STATE_JSON, {"stages": {}})
        for n in stages:
            manifest.get("stages", {}).pop(str(n), None)
            state.get("stages", {}).pop(str(n), None)
        _save_json(MANIFEST_JSON, manifest)
        _save_json(STATE_JSON, state)
        return 0

    @staticmethod
    def _rm_tree(p: Path) -> None:
        import shutil

        if p.exists():
            shutil.rmtree(p)


def _print_status(pipeline: WikiPipeline) -> None:
    rows = pipeline.status()
    print(f"{'#':>2}  {'name':<10}  {'description':<60}  {'status'}")
    print("-" * 100)
    for r in rows:
        all_present = all(o["exists"] for o in r["outputs"])
        any_present = any(o["exists"] for o in r["outputs"])
        if all_present:
            status = f"ok ({_format_bytes(r['total_bytes'])})"
        elif any_present:
            status = f"partial ({_format_bytes(r['total_bytes'])})"
        else:
            status = "missing"
        desc = r["description"]
        if len(desc) > 58:
            desc = desc[:55] + "..."
        print(f"{r['number']:>2}  {r['name']:<10}  {desc:<60}  {status}")
    print()
    print("Last manifest:", MANIFEST_JSON)
    print("Last state:   ", STATE_JSON)
    print("Last summary: ", RUN_SUMMARY_JSON)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Execute pipeline stages (default: all 7).")
    p_run.add_argument(
        "--stages",
        default="1,2,3,4,5,6,7",
        help="Comma-separated stage numbers to run (default: all 7).",
    )
    p_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be run without invoking any child script.",
    )

    sub.add_parser("status", help="Show what artifacts exist on disk and the last-run manifest summary.")

    p_clean = sub.add_parser("clean", help="Remove intermediates for the specified stages.")
    p_clean.add_argument(
        "--stages",
        default="1,2,3,4,5,6,7",
        help="Comma-separated stage numbers to clean (default: all).",
    )
    p_clean.add_argument(
        "--all",
        action="store_true",
        help="Also remove the final outputs in data/processed/ and output/analysis/.",
    )

    return p.parse_args(argv)


def _parse_stage_list(s: str) -> list[int]:
    out: list[int] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part)
        except ValueError:
            raise SystemExit(f"Invalid stage number: {part!r}")
        if not 1 <= n <= 7:
            raise SystemExit(f"Stage number out of range: {part} (must be 1-7)")
        out.append(n)
    if not out:
        raise SystemExit("No stages specified.")
    return out


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    missing = _check_dependencies()
    if missing:
        sys.stderr.write(
            "Missing required Python packages for the Wikipedia pipeline:\n"
        )
        for name in missing:
            purpose = REQUIRED_PACKAGES.get(name, "")
            sys.stderr.write(f"  - {name}  ({purpose})\n")
        sys.stderr.write("\n")
        sys.stderr.write(_venv_hint() + "\n")
        return 2
    config = PipelineConfig.from_env(ROOT)
    pipeline = WikiPipeline(config)
    if args.cmd == "run":
        stages = _parse_stage_list(args.stages)
        return pipeline.run(stages, dry_run=args.dry_run)
    if args.cmd == "status":
        _print_status(pipeline)
        return 0
    if args.cmd == "clean":
        stages = _parse_stage_list(args.stages)
        return pipeline.clean(stages, also_outputs=args.all)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
