#!/usr/bin/env python3
"""Check discoverability of explicitly named Python imports for a selected check."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Callable


def missing_imports(
    modules: list[str],
    find_spec: Callable[[str], object | None] = importlib.util.find_spec,
) -> list[str]:
    missing: list[str] = []
    for module in modules:
        try:
            available = find_spec(module) is not None
        except (ImportError, ValueError):
            available = False
        if not available:
            missing.append(module)
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "modules", nargs="+", help="explicit Python import names required by a check"
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    missing = missing_imports(args.modules)
    if missing:
        print("Missing Python imports required by this check:")
        for module in missing:
            print(f"- {module}")
        return 1
    print("Required Python imports are discoverable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
