#!/usr/bin/env python3
"""Run the seeded TypeScript checker regressions; a skip is a failure, not a pass.

Runs the existing seeded cases in ``tests/test_typescript_mechanical.py``: a
type error must fail the full ``gajaestack-check`` and a ``debugger`` lint error
must fail ``--quick``. Exit ``0`` only when both ran and passed; ``1`` when a
case failed, errored or skipped; ``2`` when a prerequisite is missing.
"""

from __future__ import annotations

import os
import shutil
import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1] / "tests"
SEEDED_CASES = (
    "test_typescript_mechanical.TypeScriptCheckEntryTests."
    "test_type_failure_matches_native_status_and_fails_fast",
    "test_typescript_mechanical.TypeScriptCheckEntryTests."
    "test_lint_failure_matches_native_status_in_quick_mode",
)


def missing_prerequisites() -> list[str]:
    missing = []
    bun = os.environ.get("GAJAESTACK_BUN", "")
    if not bun:
        missing.append("GAJAESTACK_BUN is not set (path to the Bun executable)")
    elif shutil.which(bun) is None:
        missing.append(f"GAJAESTACK_BUN is not an executable: {bun}")
    node_modules = os.environ.get("GAJAESTACK_TS_NODE_MODULES", "")
    if not node_modules:
        missing.append(
            "GAJAESTACK_TS_NODE_MODULES is not set "
            "(node_modules providing .bin/tsc and .bin/biome)"
        )
    else:
        for tool in ("tsc", "biome"):
            if not (Path(node_modules) / ".bin" / tool).exists():
                missing.append(f"GAJAESTACK_TS_NODE_MODULES lacks .bin/{tool}: {node_modules}")
    if shutil.which("git") is None:
        missing.append("git executable is not on PATH (required by the quick-mode case)")
    return missing


def main() -> int:
    missing = missing_prerequisites()
    if missing:
        for reason in missing:
            print(f"seeded regressions: missing prerequisite: {reason}", file=sys.stderr)
        return 2

    sys.path.insert(0, str(TESTS))
    suite = unittest.defaultTestLoader.loadTestsFromNames(SEEDED_CASES)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        for test, reason in result.skipped:
            print(f"seeded regressions: skipped is not a pass: {test.id()}: {reason}", file=sys.stderr)
        return 1
    if result.testsRun != len(SEEDED_CASES) or not result.wasSuccessful():
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
