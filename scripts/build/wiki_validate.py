"""Back-compat shim.

The validation/diagnostics logic for the v2 Wikipedia pipeline lives
in `wiki_cross_dataset_validate.py` (stage 7). This file exists
only so that legacy callers (and `wiki_pipeline.py` stage 9 in the
old orchestrator) that import `wiki_validate.main()` still work.

In the v2 pipeline, stage 7's child module is
`wiki_cross_dataset_validate`. This shim simply forwards to it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wiki_cross_dataset_validate as _impl


def main() -> int:
    return _impl.main()


if __name__ == "__main__":
    raise SystemExit(main())
