"""Explicit full-selected Ruff-before-pytest binding; never implied by installation."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config, parser, args):
    guard = early_config.pluginmanager.get_plugin("pytest_guard")
    if guard is None:
        raise pytest.UsageError("required-ruff binding requires the loaded pytest_guard plugin")
    try:
        guard.ensure_prerequisites(early_config)
    except guard.PrerequisiteError as error:
        raise pytest.UsageError(f"gajaestack prerequisites: {error}") from error
    root = Path(early_config.rootpath).resolve()
    helper_path = root / ".gajaestack/scripts/check_changed_python.py"
    if not helper_path.is_file() or not helper_path.resolve().is_relative_to(root):
        raise pytest.UsageError("required-ruff selected helper is missing or outside the repository")
    spec = importlib.util.spec_from_file_location("_gajaestack_selected_ruff", helper_path)
    if spec is None or spec.loader is None:
        raise pytest.UsageError("cannot load selected Ruff helper")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    try:
        files, config = helper.full_scope(root, root / ".gajaestack/routing.toml")
    except helper.ScopeError as error:
        raise pytest.UsageError(f"gajaestack required Ruff scope: {error}") from error
    print(f"gajaestack: required Ruff full selected scope ({len(files)} files)")
    status = helper.ruff_check(root, config, files)
    if status:
        pytest.exit("gajaestack required Ruff rejected collection", returncode=status)
