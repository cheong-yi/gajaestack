---
name: native-quality
description: Choose and apply the repository's suitable native formatter, linter, compiler, validator, and focused tests without imposing a tool migration.
---

# Native quality checks

Use this skill when selecting or running mechanical repository checks.

- Inspect the repository's documented commands and existing configuration first. Prefer the native tools already adopted there; do not add a dependency or change consumer configuration just to standardize tool versions.
- Select only checks that observe the changed behavior. Run formatting separately from lint/type/test checks, and never describe guidance or a command suggestion as an enforcing safeguard.
- New or noisy checks begin advisory. Make a check blocking only after a representative seeded failure demonstrates the adopted failure behavior without suppressing warnings or unrelated findings.
- Keep checks independently selectable. An unselected check must not add a dependency or cost to unrelated work.
- For a failure fix, add a focused regression case at the layer that catches the defect. Include a meaningful failing/invalid input control; a passing example alone does not prove the check detects the problem.
- Report exact commands, observed exit/status, exercised paths and remaining unverified scope. A narrow pass is not whole-repository or host support.

This repository's local `python scripts/check_repo.py` check validates bundled-skill metadata and local Markdown link targets. It is a project-local safeguard, not a consumer toolchain or a universal runner.
