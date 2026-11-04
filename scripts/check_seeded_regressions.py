#!/usr/bin/env python3
"""Run the seeded TypeScript checker regressions; a skip is a failure, not a pass.

Runs the existing seeded cases in ``tests/test_typescript_mechanical.py``: a
type error must fail the full ``gajaestack-check`` and a ``debugger`` lint error
must fail ``--quick``. Exit ``0`` only when both ran and passed; ``1`` when a
case failed, errored or skipped; ``2`` when a prerequisite is missing.

An explicit ``GAJAESTACK_BUN`` or ``GAJAESTACK_TS_NODE_MODULES`` is used as
given and is not replaced. When either is unset, Bun is taken from ``PATH``
and ``node_modules`` is the nearest directory at or above the working directory
that contains both ``.bin/tsc`` and ``.bin/biome``. A miss still exits ``2``.
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


def find_node_modules(start: Path) -> Path | None:
    current = start.resolve()
    while True:
        candidate = current / "node_modules"
        if all((candidate / ".bin" / tool).exists() for tool in ("tsc", "biome")):
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def resolve_prerequisites(
    environ: dict[str, str], start: Path
) -> tuple[str, str, list[str]]:
    missing: list[str] = []
    bun = environ.get("GAJAESTACK_BUN", "")
    if bun:
        if shutil.which(bun) is None:
            missing.append(f"GAJAESTACK_BUN is not an executable: {bun}")
    else:
        found = shutil.which("bun")
        if found is None:
            missing.append("bun is not on PATH and GAJAESTACK_BUN is not set")
        else:
            bun = found
    node_modules = environ.get("GAJAESTACK_TS_NODE_MODULES", "")
    if node_modules:
        for tool in ("tsc", "biome"):
            if not (Path(node_modules) / ".bin" / tool).exists():
                missing.append(
                    f"GAJAESTACK_TS_NODE_MODULES lacks .bin/{tool}: {node_modules}"
                )
    else:
        found_modules = find_node_modules(start)
        if found_modules is None:
            missing.append(
                "no node_modules with .bin/tsc and .bin/biome at or above "
                f"{start}, and GAJAESTACK_TS_NODE_MODULES is not set"
            )
        else:
            node_modules = str(found_modules)
    if shutil.which("git") is None:
        missing.append("git executable is not on PATH (required by the quick-mode case)")
    return bun, node_modules, missing


def main() -> int:
    bun, node_modules, missing = resolve_prerequisites(os.environ, Path.cwd())
    if missing:
        for reason in missing:
            print(f"seeded regressions: missing prerequisite: {reason}", file=sys.stderr)
        return 2
    os.environ["GAJAESTACK_BUN"] = bun
    os.environ["GAJAESTACK_TS_NODE_MODULES"] = node_modules
    print(
        f"seeded regressions: bun={bun} node_modules={node_modules}",
        file=sys.stderr,
    )
    sys.path.insert(0, str(TESTS))
    suite = unittest.defaultTestLoader.loadTestsFromNames(SEEDED_CASES)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        for test, reason in result.skipped:
            print(
                f"seeded regressions: skipped is not a pass: {test.id()}: {reason}",
                file=sys.stderr,
            )
        return 1
    if result.testsRun != len(SEEDED_CASES) or not result.wasSuccessful():
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
