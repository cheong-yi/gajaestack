---
name: native-quality
description: Choose and apply the repository's suitable native formatter, linter, compiler, validator, and focused tests without imposing a tool migration.
problem: Changes miss useful native checks or introduce unnecessary tool migration and enforcement claims.
use_when: Selecting checks or focused regression tests for a repository change.
when_to_run: Before choosing verification commands and when reporting their enforcement status.
---

# Native quality checks

Use this skill when selecting or running mechanical repository checks.

- Inspect the repository's documented commands and existing configuration first. Prefer the native tools already adopted there; do not add a dependency or change consumer configuration just to standardize tool versions.
- Select only checks that observe the changed behavior. Run formatting separately from lint/type/test checks, and never describe guidance or a command suggestion as an enforcing safeguard.
- New or noisy checks begin advisory. Make a check blocking only after a representative seeded failure demonstrates the adopted failure behavior without suppressing warnings or unrelated findings.
- Keep checks independently selectable. An unselected check must not add a dependency or cost to unrelated work.
- For a failure fix, add a focused regression case at the layer that catches the defect. Include a meaningful failing/invalid input control; a passing example alone does not prove the check detects the problem.
- Report exact commands, observed exit/status, exercised paths and remaining unverified scope. A narrow pass is not whole-repository or host support.

This repository's local `python3 scripts/check_repo.py` validates bundled-skill metadata, routing facts and local Markdown links. The [selectable native checks](../../docs/python-trial.md) provide scoped full/quick Ruff, early pytest prerequisites and separately bound required Ruff, plus Bun-hosted tsc/Biome and a separate test preload. Consumer native configuration and explicit selections activate those boundaries; copying assets or installing guidance does not. Mypy/format remain advisory; deeper review and hotspot work stay on-demand.
