"""Explicit full-selected Ruff-before-pytest binding; never implied by installation."""
from __future__ import annotations

from pathlib import Path

import pytest

from gajaestack import check_changed_python as helper


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config, parser, args):
    guard = early_config.pluginmanager.get_plugin("gajaestack.pytest_guard")
    if guard is None:
        raise pytest.UsageError(
            "required-ruff binding requires the loaded gajaestack.pytest_guard plugin"
        )
    try:
        guard.ensure_prerequisites(early_config)
    except guard.PrerequisiteError as error:
        raise pytest.UsageError(f"gajaestack prerequisites: {error}") from error
    root = Path(early_config.rootpath).resolve()
    try:
        files, config = helper.full_scope(root, root / ".gajaestack/routing.toml")
    except helper.ScopeError as error:
        raise pytest.UsageError(f"gajaestack required Ruff scope: {error}") from error
    print(f"gajaestack: required Ruff full selected scope ({len(files)} files)")
    status = helper.ruff_check(root, config, files)
    if status:
        pytest.exit("gajaestack required Ruff rejected collection", returncode=status)
