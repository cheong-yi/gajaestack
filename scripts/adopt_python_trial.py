#!/usr/bin/env python3
"""Preview, adopt, or safely remove selected gajaestack Python trial files."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
COMPONENT_FILES = {
    "ruff": (Path("python/ruff.toml"), Path(".gajaestack/python-trial/ruff.toml")),
    "mypy": (Path("python/mypy.ini"), Path(".gajaestack/python-trial/mypy.ini")),
    "hypothesis": (
        Path("python/test_percent_decoder_properties.py"),
        Path("tests/rerg/test_percent_decoder_properties.py"),
    ),
}


class AdoptionError(ValueError):
    """The requested selection cannot be changed without touching user data."""


@dataclass(frozen=True)
class Change:
    destination: Path
    content: bytes


def _changes(root: Path, components: list[str]) -> list[Change]:
    unknown = sorted(set(components) - COMPONENT_FILES.keys())
    if unknown:
        raise AdoptionError(f"unknown component(s): {', '.join(unknown)}")
    if len(components) != len(set(components)):
        raise AdoptionError("components must not be repeated")

    changes = []
    for component in components:
        source_relative, destination_relative = COMPONENT_FILES[component]
        source = KIT_ROOT / source_relative
        destination = root / destination_relative
        try:
            content = source.read_bytes()
        except OSError as error:
            raise AdoptionError(
                f"cannot read kit component {source}: {error}"
            ) from error
        changes.append(Change(destination, content))
    return changes


def _check_destination(root: Path, destination: Path) -> None:
    try:
        relative = destination.relative_to(root)
    except ValueError as error:
        raise AdoptionError(
            f"destination escapes consumer root: {destination}"
        ) from error
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise AdoptionError(f"refusing symlinked destination directory: {current}")
        if current.exists() and not current.is_dir():
            raise AdoptionError(f"destination parent is not a directory: {current}")
    if destination.is_symlink():
        raise AdoptionError(f"refusing symlink destination: {destination}")


def prepare(root: Path, components: list[str], *, remove: bool = False) -> list[Change]:
    root = root.resolve()
    if not root.is_dir():
        raise AdoptionError(f"consumer root is not a directory: {root}")
    changes = _changes(root, components)
    for change in changes:
        _check_destination(root, change.destination)
        destination = change.destination
        if destination.exists() and not destination.is_file():
            raise AdoptionError(f"refusing non-file destination: {destination}")
        if destination.exists():
            try:
                existing = destination.read_bytes()
            except OSError as error:
                raise AdoptionError(
                    f"cannot inspect existing destination {destination}: {error}"
                ) from error
            if remove and existing != change.content:
                raise AdoptionError(
                    f"refusing to remove locally changed file: {destination}"
                )
            if not remove and existing != change.content:
                raise AdoptionError(
                    f"refusing to overwrite existing file: {destination}"
                )
    return changes


def apply(root: Path, components: list[str], *, remove: bool = False) -> list[Path]:
    changes = prepare(root, components, remove=remove)
    changed = []
    for change in changes:
        destination = change.destination
        if remove:
            if destination.exists():
                destination.unlink()
                changed.append(destination)
        elif not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                with destination.open("xb") as output:
                    output.write(change.content)
            except FileExistsError as error:
                raise AdoptionError(
                    f"refusing concurrent destination creation: {destination}"
                ) from error
            changed.append(destination)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, required=True, help="consumer repository root"
    )
    parser.add_argument(
        "--component", action="append", required=True, choices=sorted(COMPONENT_FILES)
    )
    parser.add_argument(
        "--apply", action="store_true", help="apply the previewed action"
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="preview removal; combine with --apply to remove",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    try:
        changes = prepare(args.root, args.component, remove=args.remove)
        if args.apply:
            changed = apply(args.root, args.component, remove=args.remove)
            action = "Removed" if args.remove else "Adopted"
            for destination in changed:
                print(f"{action}: {destination}")
            if not changed:
                print("No changes required.")
        else:
            action = "remove" if args.remove else "adopt"
            for change in changes:
                print(f"Would {action}: {change.destination}")
            if not changes:
                print("No changes required.")
    except AdoptionError as error:
        print(f"Python trial adoption refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
