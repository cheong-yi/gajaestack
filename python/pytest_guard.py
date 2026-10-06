"""Early pytest prerequisites under trusted Python/pytest/plugin startup.

Load explicitly with native pytest configuration. This is not a sandbox or a
protection against disabling the plugin. Consumer facts remain editable.
"""
from __future__ import annotations

import importlib
from importlib.machinery import PathFinder, BuiltinImporter, FrozenImporter
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

import pytest


class PrerequisiteError(ValueError):
    """The declared native test prerequisites are not satisfied."""


def _strings(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise PrerequisiteError(f"{field} must be an array of non-empty strings")
    return value


def _path(value: object, root: Path, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise PrerequisiteError(f"{field} must be a path string")
    return (root / value).resolve()


def _spec_without_import(name: str):
    """Inspect ordinary filesystem package chains without importing their parents."""
    search = None
    spec = None
    parts = name.split(".")
    for index in range(len(parts)):
        fullname = ".".join(parts[:index + 1])
        spec = PathFinder.find_spec(fullname, search)
        if spec is None and index == 0:
            spec = BuiltinImporter.find_spec(fullname) or FrozenImporter.find_spec(fullname)
        if spec is None:
            raise PrerequisiteError(f"required import is missing: {fullname}")
        if index < len(parts) - 1:
            search = spec.submodule_search_locations
            if search is None:
                raise PrerequisiteError(f"required parent is not a package: {fullname}")
    return spec


def _origin_matches(origin: object, expected: Path) -> bool:
    if not isinstance(origin, str) or origin in ("built-in", "frozen"):
        return False
    actual = Path(origin).resolve()
    return actual.is_relative_to(expected) if expected.is_dir() else actual == expected


def ensure_prerequisites(config) -> dict:
    """Validate once before conftest/test imports; return the authoritative facts."""
    cached = getattr(config, "_gajaestack_prerequisites", None)
    if cached is not None:
        return cached
    root = Path(config.rootpath).resolve()
    if Path.cwd().resolve() != root:
        raise PrerequisiteError(f"launch from the declared pytest root: {root}")
    try:
        policy = tomllib.loads((root / ".gajaestack/routing.toml").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise PrerequisiteError(f"cannot read consumer routing facts: {error}") from error
    fact = policy.get("fact")
    if not isinstance(fact, dict) or type(fact.get("schema_version")) is not int or fact["schema_version"] != 1:
        raise PrerequisiteError("[fact] schema_version=1 is required")
    selected = _strings(fact.get("selected_components"), "fact.selected_components")
    if "guard" not in selected:
        raise PrerequisiteError("pytest_guard requires explicit guard selection")
    required = _strings(policy.get("required"), "required")
    bound = config.pluginmanager.hasplugin("pytest_required_ruff")
    if bound or "required-ruff" in selected or "required_ruff_before_pytest" in fact:
        if (
            not bound
            or not all(name in selected for name in ("guard", "ruff", "required-ruff"))
            or fact.get("required_ruff_before_pytest") != "active"
            or "ruff-check" not in required
        ):
            raise PrerequisiteError(
                "required-ruff needs the loaded binding, guard/ruff/required-ruff "
                "selections, active declaration and required ruff-check"
            )
    options = policy.get("python")
    if not isinstance(options, dict) or type(options.get("schema_version")) is not int or options["schema_version"] != 1:
        raise PrerequisiteError("[python] schema_version=1 is required")
    version = options.get("python_version")
    if version != f"{sys.version_info.major}.{sys.version_info.minor}":
        raise PrerequisiteError(f"Python major.minor mismatch: required {version!r}")
    if fact.get("python_version") != version:
        raise PrerequisiteError("fact.python_version and python.python_version disagree")
    for field, actual in (("root", root), ("prefix", Path(sys.prefix).resolve()), ("base_prefix", Path(sys.base_prefix).resolve())):
        if field in options and _path(options[field], root, field) != actual:
            raise PrerequisiteError(f"{field} identity mismatch: observed {actual}")
    source_root = _path(options.get("source_root", "."), root, "source_root")
    if not source_root.is_dir() or not source_root.is_relative_to(root):
        raise PrerequisiteError("source_root must be an existing directory inside the repository")
    if not sys.dont_write_bytecode:
        raise PrerequisiteError("launch Python with -B (no bytecode writes)")
    if config.pluginmanager.hasplugin("cacheprovider"):
        raise PrerequisiteError("disable pytest cacheprovider with -p no:cacheprovider")
    basetemp = getattr(config.known_args_namespace, "basetemp", None)
    temp = Path(basetemp).absolute() if basetemp else Path(tempfile.gettempdir()).resolve()
    if temp.resolve().is_relative_to(root) or temp.is_symlink():
        raise PrerequisiteError("pytest temporary storage must be external to the repository and not a symlink")
    if basetemp and temp.exists() and (not temp.is_dir() or any(temp.iterdir())):
        raise PrerequisiteError("explicit basetemp must be absent or an empty owned external directory")
    for executable in _strings(options.get("executables"), "python.executables"):
        if shutil.which(executable) is None:
            raise PrerequisiteError(f"required executable is missing: {executable}")
    imports = _strings(options.get("imports"), "python.imports")
    origins = options.get("module_origins", {})
    if not isinstance(origins, dict) or any(name not in imports for name in origins):
        raise PrerequisiteError("module_origins must map declared imports to approved files/directories")
    expected = {name: _path(value, root, f"module_origins.{name}") for name, value in origins.items()}
    for name in imports:
        if not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", name):
            raise PrerequisiteError(f"invalid import name: {name!r}")
        if name in expected and expected[name].is_relative_to(source_root):
            for index in range(1, len(name.split(".")) + 1):
                prefix = ".".join(name.split(".")[:index])
                if prefix in sys.modules:
                    raise PrerequisiteError(f"protected source module was imported before the guard: {prefix}")
        spec = _spec_without_import(name)
        if name in expected and not _origin_matches(spec.origin, expected[name]):
            raise PrerequisiteError(f"unexpected import origin for {name}: {spec.origin}")
    # All specified origins are inspected before initializing any declared module.
    for name in imports:
        try:
            module = importlib.import_module(name)
        except Exception as error:
            raise PrerequisiteError(f"required import initialization failed: {name}: {error}") from error
        if name in expected and not _origin_matches(getattr(module, "__file__", None), expected[name]):
            raise PrerequisiteError(f"initialized module has unexpected origin: {name}")
    config._gajaestack_prerequisites = policy
    print("gajaestack: Python prerequisites passed before protected collection")
    return policy


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config, parser, args):
    try:
        ensure_prerequisites(early_config)
    except PrerequisiteError as error:
        raise pytest.UsageError(f"gajaestack prerequisites: {error}") from error
