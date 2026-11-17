"""Download the wikimedia/structured-wikipedia Parquet snapshot to local disk.

Source: https://huggingface.co/datasets/wikimedia/structured-wikipedia

By default only the English subset (`enwiki_namespace_0`, ~35 GB across
86 Parquet shards) is downloaded; the French subset (`frwiki_namespace_0`,
~10 GB) is opt-in via --include-french. The snapshot is versioned and
self-describing, so re-running this script will reuse any shards already
present in the destination directory.

Files written:
  - data/raw/structured-wikipedia/enwiki/data/*.parquet  (default)
  - data/raw/structured-wikipedia/frwiki/data/*.parquet  (--include-french)
  - data/raw/structured-wikipedia/enwiki/schema.json     (default)
  - data/raw/structured-wikipedia/frwiki/schema.json     (--include-french)
  - tmp/wiki_acquire.json   (download metadata)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "data" / "raw" / "structured-wikipedia"
TMP = ROOT / "tmp"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--include-french",
        action="store_true",
        help="Also download the French subset (~10 GB).",
    )
    p.add_argument(
        "--repo-id",
        default="wikimedia/structured-wikipedia",
        help="HuggingFace dataset repo id.",
    )
    p.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Concurrent shard downloads.",
    )
    return p.parse_args()


def _ensure_huggingface_hub() -> None:
    try:
        from huggingface_hub import snapshot_download  # noqa: F401
    except ImportError as e:
        print(
            "huggingface_hub is required. Install with:\n"
            "  pip install 'huggingface_hub>=0.20,<1.0'",
            file=sys.stderr,
        )
        raise SystemExit(1) from e


def main() -> int:
    args = _parse_args()
    _ensure_huggingface_hub()

    from huggingface_hub import snapshot_download

    TMP.mkdir(parents=True, exist_ok=True)
    DEST.mkdir(parents=True, exist_ok=True)

    allow_patterns = ["enwiki/data/*.parquet", "enwiki/schema.json"]
    if args.include_french:
        allow_patterns += ["frwiki/data/*.parquet", "frwiki/schema.json"]

    t0 = time.time()
    print(f"Downloading {args.repo_id} -> {DEST}")
    print(f"  patterns: {allow_patterns}")
    print(f"  max_workers: {args.max_workers}")

    try:
        local_path = snapshot_download(
            repo_id=args.repo_id,
            repo_type="dataset",
            local_dir=str(DEST),
            allow_patterns=allow_patterns,
            max_workers=args.max_workers,
        )
    except Exception as e:
        print(f"\nDownload failed: {e}", file=sys.stderr)
        raise

    en_dir = Path(local_path) / "enwiki" / "data"
    n_shards = sum(1 for _ in en_dir.glob("*.parquet")) if en_dir.exists() else 0
    total_bytes = sum(p.stat().st_size for p in en_dir.glob("*.parquet")) if en_dir.exists() else 0
    elapsed = time.time() - t0

    meta = {
        "repo_id": args.repo_id,
        "destination": str(DEST),
        "n_shards_en": n_shards,
        "bytes_en_parquet": total_bytes,
        "include_french": args.include_french,
        "elapsed_seconds": round(elapsed, 1),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open(TMP / "wiki_acquire.json", "w") as f:
        json.dump(meta, f, indent=2)
    print()
    print(f"Done in {elapsed:.1f}s")
    print(f"  enwiki shards: {n_shards}  ({total_bytes/1e9:.2f} GB)")
    print(f"  metadata -> {TMP / 'wiki_acquire.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
