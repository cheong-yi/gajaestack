#!/usr/bin/env python3
"""Check selected Python files with Ruff: quick changed-path mode or full scope.

Usage in a consumer checkout after selecting the ``ruff`` component::

    # quick mode (default): changed Python files in the Git worktree
    python .gajaestack/scripts/check_changed_python.py [--config PATH] \
        [--path REPOSITORY_PATH]... [--impact REPOSITORY_PATH]... \
        [--facts PATH]

    # full mode: the complete selected scope declared in the facts file
    python .gajaestack/scripts/check_changed_python.py --full [--config PATH] \
        [--facts PATH]

Quick mode discovers ``.py`` files with staged or unstaged tracked changes
plus untracked non-ignored files in the current Git worktree, skips deleted
paths, and runs ``ruff check`` from the repository root as
``ruff check --no-cache --config PATH -- <files>``. Commands are built as argument
arrays without a shell, so filenames containing spaces are handled safely.
Repeated ``--path`` arguments (files or directories) restrict the selection
to the intersection of changed files and those repository-relative paths.

Quick mode expands to the full selected scope whenever a shared policy path
changed: the selected ``--config`` file, this helper script itself (when it
lives inside the repository), or any repeated ``--impact`` path (shared
policy paths such as routing facts or AGENTS guidance). Expansion loads the
full scope from the facts file and rejects visibly if that scope cannot be
resolved; a quick invocation with no matching targets reports no coverage
and exits 0 (a no-op, never lint proof).

Full mode never consults Git status: it reads ``[python]`` from the facts
file (default ``.gajaestack/routing.toml``), requires ``schema_version = 1``,
and checks exactly the declared ``ruff_paths`` (repo-relative files or
directories, expanded recursively to ``*.py``) with ``ruff_config``. An
empty scope, a missing/escaping target, a missing config file, missing
facts, or a working directory that differs from a declared ``root`` reject
with exit status 2. If ``--config`` is given explicitly it overrides
``[python].ruff_config`` in full mode.

Exit status:

* ``0`` — quick no-op (no coverage reported) or Ruff found no problems;
* Ruff's own nonzero exit status when Ruff fails;
* ``2`` — invalid arguments or an unusable full selected scope;
* ``127`` — the ``git`` or ``ruff`` executable was not found;
* Git's nonzero exit status when Git cannot report the changed files.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tomllib
from pathlib import Path

DEFAULT_CONFIG = ".gajaestack/python-trial/ruff.toml"
DEFAULT_FACTS = ".gajaestack/routing.toml"
MISSING_EXECUTABLE = 127
INVALID_SCOPE = 2


class GitError(RuntimeError):
    """Git could not report the changed files."""

    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code


class ScopeError(RuntimeError):
    """The full selected scope declared by the facts file is unusable."""


def git_output(*args: str, cwd: Path | None = None) -> bytes:
    try:
        completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    except FileNotFoundError:
        raise GitError("git executable not found", MISSING_EXECUTABLE) from None
    if completed.returncode != 0:
        detail = os.fsdecode(completed.stderr).strip() or f"git {' '.join(args)} failed"
        raise GitError(detail, completed.returncode)
    return completed.stdout


def repository_root() -> Path:
    output = git_output("rev-parse", "--show-toplevel")
    if output.endswith(b"\n"):
        output = output[:-1]
    return Path(os.fsdecode(output))


def changed_paths(root: Path) -> list[str]:
    """Return repository-relative paths from NUL-terminated porcelain status."""
    status = git_output("status", "--porcelain", "-z", "--untracked-files=all", cwd=root)
    entries = status.split(b"\0")
    paths: list[str] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], os.fsdecode(entry[3:])
        paths.append(path)
        if b"R" in code or b"C" in code:
            index += 1  # rename/copy entries are followed by the original path.
    return paths


def changed_python_files(root: Path) -> list[str]:
    """Return changed ``.py`` paths that still exist in the worktree."""
    return [
        path
        for path in changed_paths(root)
        if path.endswith(".py") and (root / path).is_file()
    ]


def ruff_check(root: Path, config: str, files: list[str]) -> int:
    if not files:
        print("error: empty Ruff scope; no coverage", file=sys.stderr)
        return INVALID_SCOPE
    command = ["ruff", "check", "--no-cache", "--config", config, "--", *files]
    try:
        completed = subprocess.run(command, cwd=root)
    except FileNotFoundError:
        print("error: ruff executable not found", file=sys.stderr)
        return MISSING_EXECUTABLE
    return completed.returncode


def read_facts(facts_path: Path) -> dict:
    """Parse the consumer facts TOML file, rejecting unusable input."""
    try:
        with facts_path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        raise ScopeError(f"facts file not found: {facts_path}") from None
    except tomllib.TOMLDecodeError as error:
        raise ScopeError(f"malformed facts file {facts_path}: {error}") from error
    except OSError as error:
        raise ScopeError(f"cannot read facts file {facts_path}: {error}") from error


def full_scope(
    root: Path, facts_path: Path, config_override: str | None = None
) -> tuple[list[str], str]:
    """Resolve the full selected scope declared in ``[python]`` of the facts.

    Returns ``(files, config)`` where ``files`` are repository-relative
    POSIX paths. Raises :class:`ScopeError` for missing facts, an
    unsupported schema, an empty or missing scope, missing or escaping
    targets, a missing config file, or a working directory that differs
    from a declared ``root``.
    """
    data = read_facts(facts_path)
    python = data.get("python")
    if not isinstance(python, dict):
        raise ScopeError(f"missing [python] table in {facts_path}")
    if type(python.get("schema_version")) is not int or python["schema_version"] != 1:
        raise ScopeError(
            f"unsupported [python].schema_version in {facts_path}: expected 1"
        )

    root_resolved = root.resolve()
    declared_root = python.get("root")
    if declared_root is not None:
        if not isinstance(declared_root, str) or not declared_root:
            raise ScopeError(f"[python].root in {facts_path} must be a path string")
        expected = Path(declared_root)
        if not expected.is_absolute():
            expected = root / expected
        if expected.resolve() != root_resolved:
            raise ScopeError(
                f"working directory {root_resolved} is not the declared root "
                f"{expected.resolve()}"
            )

    declared = python.get("ruff_paths")
    if not isinstance(declared, list):
        raise ScopeError(
            f"missing [python].ruff_paths in {facts_path}; full selected scope is empty"
        )
    if not declared:
        raise ScopeError(
            f"empty [python].ruff_paths in {facts_path}; full selected scope is empty"
        )
    if not all(isinstance(item, str) and item for item in declared):
        raise ScopeError(
            f"[python].ruff_paths in {facts_path} must contain "
            "repository-relative path strings"
        )

    facts_config = python.get("ruff_config")
    if config_override is None:
        if not isinstance(facts_config, str) or not facts_config:
            raise ScopeError(f"missing [python].ruff_config in {facts_path}")
        config = facts_config
    else:
        config = config_override
    config_path = Path(config)
    if not config_path.is_absolute():
        config_path = root / config_path
    if not config_path.is_file():
        raise ScopeError(f"ruff config not found: {config}")
    if not config_path.resolve().is_relative_to(root_resolved):
        raise ScopeError("ruff config escapes the repository root")

    files: list[str] = []
    for target in declared:
        target_path = Path(target)
        if target_path.is_absolute():
            raise ScopeError(
                f"declared ruff target must be repository-relative: {target}"
            )
        resolved = (root / target_path).resolve()
        if resolved != root_resolved and root_resolved not in resolved.parents:
            raise ScopeError(f"declared ruff target escapes the repository root: {target}")
        if not resolved.exists():
            raise ScopeError(f"declared ruff target does not exist: {target}")
        if resolved.is_dir():
            for path in sorted(resolved.rglob("*.py")):
                if not path.is_file():
                    continue
                if not path.resolve().is_relative_to(root_resolved):
                    raise ScopeError(f"declared scope contains an escaping symlink: {path}")
                relative = path.relative_to(root_resolved)
                if ".git" in relative.parts:
                    continue
                files.append(relative.as_posix())
        else:
            if resolved.suffix != ".py":
                raise ScopeError(f"declared Ruff target is not a Python file: {target}")
            files.append(resolved.relative_to(root_resolved).as_posix())

    unique = list(dict.fromkeys(files))
    if not unique:
        raise ScopeError(
            "full selected scope is empty: no Python files under [python].ruff_paths"
        )
    return unique, config


def _matches(paths: list[str], selector: str) -> bool:
    """True when any path equals the selector or lies beneath it."""
    selector = Path(selector).as_posix()
    if selector == ".":
        return bool(paths)
    return any(
        path == selector or path.startswith(selector + "/") for path in paths
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "Ruff configuration file (quick default: "
            f"{DEFAULT_CONFIG}; full default: [python].ruff_config)"
        ),
    )
    parser.add_argument(
        "--facts",
        default=DEFAULT_FACTS,
        help=f"consumer facts file (default: {DEFAULT_FACTS})",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help=(
            "only check changed repository-relative Python files beneath this "
            "file or directory (repeatable)"
        ),
    )
    parser.add_argument(
        "--impact",
        action="append",
        default=[],
        help=(
            "shared policy path (file or directory) whose change expands quick "
            "mode to the full selected scope (repeatable)"
        ),
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="run the full selected scope declared in [python] of the facts file",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.full and args.path:
        parser.error("--full selects the declared scope and cannot be combined with --path")
    for selector in [*args.path, *args.impact]:
        if not selector or Path(selector).is_absolute() or ".." in Path(selector).parts:
            parser.error("selectors must be repository-relative paths without '..'")

    facts_path = Path(args.facts)
    if not facts_path.is_absolute():
        facts_path = Path.cwd() / facts_path

    if args.full:
        try:
            files, config = full_scope(Path.cwd(), facts_path, args.config)
        except ScopeError as error:
            print(f"error: {error}", file=sys.stderr)
            return INVALID_SCOPE
        print(f"Full selected scope: {len(files)} file(s) from {facts_path}")
        return ruff_check(Path.cwd(), config, files)

    quick_config = args.config if args.config is not None else DEFAULT_CONFIG

    try:
        root = repository_root()
        changed = changed_paths(root)
    except GitError as error:
        print(f"error: {error}", file=sys.stderr)
        return error.code

    # Shared policy paths whose changes invalidate changed-only scope: the
    # selected config, this helper (when inside the repository), and every
    # declared --impact path.
    triggers = {quick_config, *args.impact}
    if Path(quick_config).is_absolute():
        try:
            triggers.discard(quick_config)
            triggers.add(Path(quick_config).resolve().relative_to(root.resolve()).as_posix())
        except ValueError:
            pass
    try:
        triggers.add(facts_path.resolve().relative_to(root.resolve()).as_posix())
    except ValueError:
        pass
    try:
        triggers.add(
            Path(__file__).resolve().relative_to(root.resolve()).as_posix()
        )
    except ValueError:
        pass  # The helper lives outside this repository; it cannot change here.
    matched = sorted(
        trigger for trigger in triggers if trigger and _matches(changed, trigger)
    )
    if matched:
        print(f"Quick scope expanded to full selected scope: changed {', '.join(matched)}")
        try:
            files, config = full_scope(root, facts_path, args.config)
        except ScopeError as error:
            print(f"error: {error}", file=sys.stderr)
            return INVALID_SCOPE
        print(f"Full selected scope: {len(files)} file(s) from {facts_path}")
        return ruff_check(root, config, files)

    files = [
        path
        for path in changed
        if path.endswith(".py") and (root / path).is_file()
    ]

    if args.path:
        files = [path for path in files if any(
            _matches([path], selector) for selector in args.path
        )]
        if not files:
            print("No changed Python files match the requested paths; nothing to check.")
            print("No coverage; this no-op is not a lint pass.")
            return 0

    if not files:
        print("No changed Python files; nothing to check.")
        print("No coverage; this no-op is not a lint pass.")
        return 0

    return ruff_check(root, quick_config, files)


if __name__ == "__main__":
    raise SystemExit(main())
