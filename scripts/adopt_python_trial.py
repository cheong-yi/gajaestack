#!/usr/bin/env python3
"""Preview, adopt, update, or safely remove selected gajaestack source assets.

Shared assets (Ruff, mypy, Hypothesis) are governed by a strict per-asset
source/version/hash record at ``.gajaestack/ownership.json``; identical
current kit bytes never imply ownership, and unclaimed files require an
explicitly reviewed source/version/hash inventory entry. The ``routing``
component manages only a delimited, version/hash-stamped addendum span in the
consumer's root ``AGENTS.md`` (never the file itself) and creates
``.gajaestack/routing.toml`` facts only when absent, validating existing
facts through the repository policy validator without rewriting them.
Unrelated bytes are preserved throughout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

KIT_ROOT = Path(__file__).resolve().parents[1]
KIT_VERSION = "unreleased-overlay"
OWNERSHIP_RELATIVE = Path(".gajaestack/ownership.json")
OWNERSHIP_SCHEMA = "gajaestack-adoption-ownership-v1"

SHARED_ASSETS: dict[str, tuple[tuple[Path, Path], ...]] = {
    "guard": (
        (Path("python/pytest_guard.py"), Path(".gajaestack/python/pytest_guard.py")),
    ),
    "required-ruff": (
        (Path("python/pytest_required_ruff.py"), Path(".gajaestack/python/pytest_required_ruff.py")),
    ),
    "typescript": (
        (Path("typescript/check.ts"), Path(".gajaestack/typescript/check.ts")),
    ),
    "typescript-guard": (
        (Path("typescript/preload.ts"), Path(".gajaestack/typescript/preload.ts")),
    ),
    "typescript-config": (
        (Path("typescript/tsconfig.json"), Path(".gajaestack/typescript/tsconfig.json")),
    ),
    "ruff": (
        (Path("python/ruff.toml"), Path(".gajaestack/python-trial/ruff.toml")),
        (
            Path("scripts/check_changed_python.py"),
            Path(".gajaestack/scripts/check_changed_python.py"),
        ),
    ),
    "mypy": ((Path("python/mypy.ini"), Path(".gajaestack/python-trial/mypy.ini")),),
    "hypothesis": (
        (
            Path("python/test_percent_decoder_properties.py"),
            Path("tests/rerg/test_percent_decoder_properties.py"),
        ),
    ),
}
FACTS_SOURCE = Path("python/routing.toml")
FACTS_DESTINATION = Path(".gajaestack/routing.toml")
ADDENDUM_SOURCE = Path("python/routing/AGENTS.md")
AGENTS_DESTINATION = Path("AGENTS.md")
COMPONENTS: tuple[str, ...] = (*SHARED_ASSETS, "routing")
DEPENDENCIES = {
    "typescript-guard": ("typescript",),
    "required-ruff": ("guard", "ruff"),
}

KNOWN_SOURCES: dict[str, str] = {
    destination.as_posix(): source.as_posix()
    for assets in SHARED_ASSETS.values()
    for source, destination in assets
}

ADDENDUM_BEGIN = b"<!-- gajaestack:routing-addendum begin"
ADDENDUM_END = b"<!-- gajaestack:routing-addendum end"
ADDENDUM_END_LINE = b"<!-- gajaestack:routing-addendum end -->"
ADDENDUM_RESERVED = b"gajaestack:routing-addendum"
BEGIN_PATTERN = re.compile(
    rb"<!-- gajaestack:routing-addendum begin version=(\S+) sha256=([0-9a-f]{64}) -->"
)
HASH_PATTERN = re.compile(r"sha256-[0-9a-f]{64}")


class AdoptionError(ValueError):
    """The requested selection cannot be changed without touching user data."""


@dataclass(frozen=True)
class Change:
    destination: Path
    content: bytes | None  # ``None`` removes the destination file.
    action: str
    exclusive: bool = False


def _read_kit(source_relative: Path) -> bytes:
    source = KIT_ROOT / source_relative
    try:
        return source.read_bytes()
    except OSError as error:
        raise AdoptionError(f"cannot read kit component {source}: {error}") from error


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _record_hash(entry: dict[str, str]) -> str:
    return entry["hash"].removeprefix("sha256-")


def _inventory_required(destination: Path) -> AdoptionError:
    return AdoptionError(
        f"action required: {destination} matches the kit bytes but has no ownership "
        f"record; review it manually and add an explicitly reviewed source/version/hash "
        f"inventory entry to {OWNERSHIP_RELATIVE.as_posix()} before adoption, update, or "
        f"removal (identical current bytes are not ownership evidence)"
    )


def _check_destination(root: Path, destination: Path) -> None:
    try:
        relative = destination.relative_to(root)
    except ValueError as error:
        raise AdoptionError(f"destination escapes consumer root: {destination}") from error
    current = root
    for part in relative.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise AdoptionError(f"refusing symlinked destination directory: {current}")
        if current.exists() and not current.is_dir():
            raise AdoptionError(f"destination parent is not a directory: {current}")
    if destination.is_symlink():
        raise AdoptionError(f"refusing symlink destination: {destination}")


def _require_file_destination(destination: Path) -> None:
    if destination.exists() and not destination.is_file():
        raise AdoptionError(f"refusing non-file destination: {destination}")


def _read_destination(destination: Path) -> bytes:
    try:
        return destination.read_bytes()
    except OSError as error:
        raise AdoptionError(
            f"cannot inspect existing destination {destination}: {error}"
        ) from error


def _resolve_root(root: Path) -> Path:
    if root.is_symlink():
        raise AdoptionError(f"refusing symlinked consumer root: {root}")
    resolved = root.resolve()
    if not resolved.is_dir():
        raise AdoptionError(f"consumer root is not a directory: {root}")
    return resolved


def _load_ownership(
    root: Path,
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], bool]:
    """Return (assets, snapshot, record_exists) from the strict ownership record."""
    record_path = root / OWNERSHIP_RELATIVE
    _check_destination(root, record_path)
    if not record_path.exists():
        return {}, {}, False
    if not record_path.is_file():
        raise AdoptionError(f"refusing non-file ownership record: {record_path}")
    try:
        raw = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AdoptionError(
            f"refusing malformed ownership record {record_path}: {error}"
        ) from error
    if not isinstance(raw, dict) or set(raw) != {"schema", "assets"}:
        raise AdoptionError(
            f"refusing malformed ownership record {record_path}: expected exactly the "
            f"keys 'schema' and 'assets'"
        )
    if raw["schema"] != OWNERSHIP_SCHEMA:
        raise AdoptionError(
            f"refusing malformed ownership record {record_path}: schema must be "
            f"{OWNERSHIP_SCHEMA!r}"
        )
    entries = raw["assets"]
    if not isinstance(entries, dict):
        raise AdoptionError(
            f"refusing malformed ownership record {record_path}: 'assets' must be an "
            f"object keyed by consumer-root-relative destinations"
        )

    assets: dict[str, dict[str, str]] = {}
    for destination_key, entry in entries.items():
        relative = PurePosixPath(destination_key)
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in ("", ".", "..") for part in relative.parts)
        ):
            raise AdoptionError(
                f"refusing unsafe ownership record path {destination_key!r} in "
                f"{record_path}"
            )
        expected_source = KNOWN_SOURCES.get(destination_key)
        if expected_source is None:
            raise AdoptionError(
                f"refusing ownership record entry for unknown destination "
                f"{destination_key!r} in {record_path}"
            )
        if not isinstance(entry, dict) or set(entry) != {"source", "version", "hash"}:
            raise AdoptionError(
                f"refusing malformed ownership record {record_path}: entry for "
                f"{destination_key} must contain exactly 'source', 'version', and 'hash'"
            )
        source = entry["source"]
        version = entry["version"]
        digest = entry["hash"]
        if not all(isinstance(value, str) for value in (source, version, digest)):
            raise AdoptionError(
                f"refusing malformed ownership record {record_path}: entry fields for "
                f"{destination_key} must be strings"
            )
        if source != expected_source:
            raise AdoptionError(
                f"refusing mixed source identity for {destination_key}: ownership record "
                f"names {source!r} but the kit source is {expected_source!r}"
            )
        if not version or any(character.isspace() for character in version):
            raise AdoptionError(
                f"refusing malformed ownership record {record_path}: entry for "
                f"{destination_key} needs a non-empty version token; missing or invalid "
                f"versions require explicit consumer review"
            )
        if HASH_PATTERN.fullmatch(digest) is None:
            raise AdoptionError(
                f"refusing malformed ownership record {record_path}: entry for "
                f"{destination_key} needs hash 'sha256-' plus 64 hex digits"
            )
        assets[destination_key] = {"source": source, "version": version, "hash": digest}
    return assets, dict(assets), True


def _serialize_ownership(assets: dict[str, dict[str, str]]) -> bytes:
    document = {"schema": OWNERSHIP_SCHEMA, "assets": assets}
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _routing_fact_errors(path: Path) -> list[str]:
    if __package__:
        from scripts.check_repo import routing_policy_file_errors
    else:
        from check_repo import routing_policy_file_errors

    return routing_policy_file_errors(path)


@dataclass(frozen=True)
class _Addendum:
    marked: bool
    version: str = ""
    digest: str = ""
    body: bytes = b""
    prefix: bytes = b""
    suffix: bytes = b""


def _marker_error(path: Path, detail: str) -> AdoptionError:
    return AdoptionError(
        f"refusing malformed or duplicate addendum markers in {path}: {detail}"
    )


def _parse_addendum(content: bytes, path: Path) -> _Addendum:
    reserved = content.count(ADDENDUM_RESERVED)
    if reserved == 0:
        return _Addendum(marked=False)
    begins = content.count(ADDENDUM_BEGIN)
    ends = content.count(ADDENDUM_END)
    if reserved != begins + ends:
        raise _marker_error(path, "malformed reserved addendum marker")
    if begins == 0:
        raise _marker_error(path, "end marker without begin marker")
    if ends == 0:
        raise _marker_error(path, "begin marker without end marker")
    if begins > 1:
        raise _marker_error(path, f"duplicate begin markers ({begins})")
    if ends > 1:
        raise _marker_error(path, f"duplicate end markers ({ends})")

    begin_index = content.index(ADDENDUM_BEGIN)
    end_index = content.index(ADDENDUM_END)
    if end_index < begin_index:
        raise _marker_error(path, "end marker precedes begin marker")
    if begin_index > 0 and content[begin_index - 1] != 0x0A:
        raise _marker_error(path, "begin marker does not start a line")
    line_end = content.find(b"\n", begin_index)
    if line_end < 0:
        raise _marker_error(path, "unterminated begin marker line")
    match = BEGIN_PATTERN.fullmatch(content[begin_index:line_end])
    if match is None:
        raise _marker_error(path, "begin marker must declare version and sha256")
    body_start = line_end + 1
    if end_index < body_start:
        raise _marker_error(path, "end marker does not start a line")
    if end_index > 0 and content[end_index - 1] != 0x0A:
        raise _marker_error(path, "end marker does not start a line")
    end_line_end = content.find(b"\n", end_index)
    if end_line_end < 0:
        raise _marker_error(path, "unterminated end marker line")
    if content[end_index:end_line_end] != ADDENDUM_END_LINE:
        raise _marker_error(path, "trailing content on end marker line")
    return _Addendum(
        marked=True,
        version=match.group(1).decode("utf-8", "replace"),
        digest=match.group(2).decode("ascii"),
        body=content[body_start:end_index],
        prefix=content[:begin_index],
        suffix=content[end_line_end + 1 :],
    )


def _verified_span(addendum: _Addendum, path: Path) -> _Addendum:
    if _sha256(addendum.body) != addendum.digest:
        raise AdoptionError(
            f"refusing edited addendum span in {path}: recorded sha256 does not match "
            f"span content"
        )
    return addendum


def _addendum_body() -> bytes:
    body = _read_kit(ADDENDUM_SOURCE)
    if not body.endswith(b"\n"):
        body += b"\n"
    return body


def _span_bytes(body: bytes) -> bytes:
    header = (
        f"<!-- gajaestack:routing-addendum begin version={KIT_VERSION} "
        f"sha256={_sha256(body)} -->\n"
    )
    return header.encode("ascii") + body + ADDENDUM_END_LINE + b"\n"


def prepare(root: Path, components: list[str], *, remove: bool = False) -> list[Change]:
    unknown = sorted(set(components) - set(COMPONENTS))
    if unknown:
        raise AdoptionError(f"unknown component(s): {', '.join(unknown)}")
    if len(components) != len(set(components)):
        raise AdoptionError("components must not be repeated")

    root = _resolve_root(root)
    _check_bindings(root, components, remove=remove)
    changes: list[Change] = []
    ownership: dict[str, dict[str, str]] | None = None
    original: dict[str, dict[str, str]] | None = None
    record_exists = False

    for component in components:
        if component in SHARED_ASSETS:
            if ownership is None:
                ownership, original, record_exists = _load_ownership(root)
            for source_relative, destination_relative in SHARED_ASSETS[component]:
                destination = root / destination_relative
                _check_destination(root, destination)
                _require_file_destination(destination)
                key = destination_relative.as_posix()
                entry = ownership.get(key)
                if remove:
                    if destination.exists():
                        current = _read_destination(destination)
                        if entry is None:
                            if current == _read_kit(source_relative):
                                raise _inventory_required(destination)
                            raise AdoptionError(
                                f"refusing to remove unowned destination: {destination}"
                            )
                        if _sha256(current) != _record_hash(entry):
                            raise AdoptionError(
                                f"refusing to remove locally changed file: {destination}"
                            )
                        changes.append(Change(destination, None, "remove"))
                    if entry is not None:
                        ownership.pop(key)
                    continue
                kit_content = _read_kit(source_relative)
                if destination.exists():
                    current = _read_destination(destination)
                    if entry is None:
                        if current == kit_content:
                            raise _inventory_required(destination)
                        raise AdoptionError(
                            f"refusing to overwrite unowned destination: {destination}"
                        )
                    if _sha256(current) != _record_hash(entry):
                        raise AdoptionError(
                            f"refusing to overwrite locally changed file: {destination}"
                        )
                    if current == kit_content and entry["version"] == KIT_VERSION:
                        continue
                    changes.append(Change(destination, kit_content, "update"))
                else:
                    changes.append(
                        Change(destination, kit_content, "adopt", exclusive=True)
                    )
                ownership[key] = {
                    "source": source_relative.as_posix(),
                    "version": KIT_VERSION,
                    "hash": f"sha256-{_sha256(kit_content)}",
                }
        elif component == "routing":
            facts = root / FACTS_DESTINATION
            _check_destination(root, facts)
            _require_file_destination(facts)
            if facts.exists():
                errors = _routing_fact_errors(facts)
                if errors:
                    raise AdoptionError(
                        f"action required: incompatible routing facts at {facts}: "
                        + "; ".join(errors)
                        + " (the helper validates consumer facts but never rewrites them)"
                    )
            elif not remove:
                changes.append(
                    Change(facts, _read_kit(FACTS_SOURCE), "adopt", exclusive=True)
                )

            agents = root / AGENTS_DESTINATION
            _check_destination(root, agents)
            _require_file_destination(agents)
            content = _read_destination(agents) if agents.exists() else b""
            addendum = _parse_addendum(content, agents)
            if remove:
                if addendum.marked:
                    _verified_span(addendum, agents)
                    changes.append(
                        Change(agents, addendum.prefix + addendum.suffix, "remove addendum")
                    )
            else:
                body = _addendum_body()
                if not addendum.marked:
                    changes.append(
                        Change(
                            agents,
                            _span_bytes(body) + content,
                            "adopt addendum",
                            exclusive=not agents.exists(),
                        )
                    )
                else:
                    _verified_span(addendum, agents)
                    if addendum.version != KIT_VERSION or addendum.body != body:
                        changes.append(
                            Change(
                                agents,
                                addendum.prefix + _span_bytes(body) + addendum.suffix,
                                "update addendum",
                            )
                        )

    if ownership is not None and original is not None and ownership != original:
        record_path = root / OWNERSHIP_RELATIVE
        if not ownership:
            if record_exists:
                changes.append(Change(record_path, None, "remove"))
        else:
            changes.append(
                Change(
                    record_path,
                    _serialize_ownership(ownership),
                    "update" if record_exists else "adopt",
                    exclusive=not record_exists,
                )
            )
    return changes


def _check_bindings(root: Path, components: list[str], *, remove: bool) -> None:
    """Require explicit binding prerequisites without editing consumer configuration."""
    requested = set(components)
    declared: set[str] = set()
    facts_path = root / FACTS_DESTINATION
    prerequisites = {name for names in DEPENDENCIES.values() for name in names}
    if remove and requested.intersection(prerequisites) and facts_path.is_file():
        try:
            facts = tomllib.loads(facts_path.read_text(encoding="utf-8")).get("fact", {})
            raw = facts.get("selected_components", []) if isinstance(facts, dict) else []
            if isinstance(raw, list) and all(isinstance(item, str) for item in raw):
                declared = set(raw)
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
            raise AdoptionError(f"cannot inspect binding selection before removal: {error}") from error
    for binding, dependencies in DEPENDENCIES.items():
        binding_path = root / SHARED_ASSETS[binding][0][1]
        present = binding_path.exists() or binding in declared
        remains = (present and binding not in requested) if remove else (present or binding in requested)
        if not remains:
            continue
        for dependency in dependencies:
            available = all((root / destination).is_file() for _, destination in SHARED_ASSETS[dependency])
            available = (available and dependency not in requested) if remove else (available or dependency in requested)
            if not available:
                raise AdoptionError(
                    f"binding {binding!r} requires component {dependency!r}; "
                    "remove the binding explicitly before its prerequisites"
                )
        if not remove and binding in requested:
            facts = root / FACTS_DESTINATION
            _check_destination(root, facts)
            _require_file_destination(facts)
            errors = _routing_fact_errors(facts)
            if errors:
                raise AdoptionError("binding requires reviewed consumer facts: " + "; ".join(errors))
            policy = tomllib.loads(facts.read_text(encoding="utf-8"))
            if binding not in policy["fact"]["selected_components"]:
                raise AdoptionError(f"consumer facts must explicitly select binding {binding!r}")


def _changed_so_far(changed: list[Path]) -> str:
    return ", ".join(str(path) for path in changed) if changed else "none"


def apply(root: Path, components: list[str], *, remove: bool = False) -> list[Path]:
    changes = prepare(root, components, remove=remove)
    changed: list[Path] = []
    for change in changes:
        destination = change.destination
        try:
            if change.content is None:
                if destination.exists():
                    destination.unlink()
                    changed.append(destination)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            if change.exclusive:
                try:
                    with destination.open("xb") as output:
                        output.write(change.content)
                except FileExistsError as error:
                    raise AdoptionError(
                        f"refusing concurrent destination creation: {destination}; "
                        f"changed paths so far: {_changed_so_far(changed)}; "
                        f"the failed destination may be partially written"
                    ) from error
            else:
                destination.write_bytes(change.content)
            changed.append(destination)
        except AdoptionError:
            raise
        except OSError as error:
            raise AdoptionError(
                f"I/O error during {change.action} of {destination}: {error}; "
                f"changed paths so far: {_changed_so_far(changed)}; "
                f"the failed destination may be partially written "
                f"(no rollback attempted)"
            ) from error
    return changed


_PAST_ACTIONS = {"adopt": "Adopted", "update": "Updated", "remove": "Removed"}


def _describe_past(action: str) -> str:
    verb, _, rest = action.partition(" ")
    past = _PAST_ACTIONS.get(verb, "Applied")
    return f"{past} {rest}".rstrip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="consumer repository root")
    parser.add_argument(
        "--component", action="append", required=True, choices=sorted(COMPONENTS)
    )
    parser.add_argument("--apply", action="store_true", help="apply the previewed action")
    parser.add_argument(
        "--remove",
        action="store_true",
        help="preview removal; combine with --apply to remove",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    try:
        changes = prepare(args.root, args.component, remove=args.remove)
        if args.apply:
            actions = {change.destination: change.action for change in changes}
            changed = apply(args.root, args.component, remove=args.remove)
            for destination in changed:
                print(f"{_describe_past(actions.get(destination, 'apply'))}: {destination}")
            if not changed:
                print("No changes required.")
        else:
            for change in changes:
                print(f"Would {change.action}: {change.destination}")
            if not changes:
                print("No changes required.")
    except AdoptionError as error:
        print(f"Python trial adoption refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
