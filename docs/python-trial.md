# Selectable Python quality trial

This page describes an optional Python trial, not a mandatory toolchain or a supported-version guarantee. Preserve a consumer's existing test harness and suitable native tools. The reusable part is the selection helper and centrally maintained configuration files; the file paths, source selection, test target, and sample commands below reflect a RERG decoder example and must be adapted for another repository.

## Select and remove components

Run the helper from a gajaestack checkout. It uses only the Python standard library and does not install dependencies, edit the consumer's project configuration, or add CI jobs. Preview is the default; inspect the proposed paths before applying:

```sh
python3 /path/to/gajaestack/scripts/adopt_python_trial.py \
  --root /path/to/consumer --component ruff --component mypy
python3 /path/to/gajaestack/scripts/adopt_python_trial.py \
  --root /path/to/consumer --component ruff --component mypy --apply
```

Available selections are `ruff`, `mypy`, and `hypothesis`. Ruff and mypy select centrally maintained configuration files under `.gajaestack/python-trial/`. The Hypothesis component copies a bounded RERG-specific property test into `tests/rerg/`; it is not a generic property-test suite. `pytest` is the consumer's native test runner, not a helper-managed component.

The helper refuses existing different files and symlinked destinations. Applying an unchanged selection is safe to repeat. Removal is preview-first; add `--remove --apply` only after reviewing the exact selected files. It removes only byte-identical files provided by the kit, including the selected Hypothesis test, and does not remove packages, directories, unrelated consumer configuration or tests, or modified files. Remove any consumer-authored selection notes separately.

The consumer is responsible for provisioning the selected executables and Python dependencies in its normal development environment. No command here installs Ruff, mypy, pytest, Hypothesis, or their dependencies. Install only the tools and dependencies actually selected, using the consumer's established dependency-management process. Missing tools should fail visibly rather than silently skip checks.

## Native command examples

These direct commands illustrate the RERG trial. Adjust paths, test selection, configuration, and options for the target project and installed tool versions; confirm syntax against those versions' documentation before relying on it. No hosted workflow is supplied.

```sh
# Existing consumer regression suite; retain its own pytest configuration.
python -m pytest

# RERG-scoped formatting and correctness lint; format check does not modify files.
ruff format --check --config .gajaestack/python-trial/ruff.toml \
  rerg/raw_derivation.py tests/rerg/test_percent_decoder.py
ruff check --config .gajaestack/python-trial/ruff.toml \
  rerg/raw_derivation.py tests/rerg/test_percent_decoder.py

# Advisory RERG configuration; includes the selected source modules.
mypy --config-file .gajaestack/python-trial/mypy.ini

# Optional RERG property test; requires Hypothesis to be explicitly installed.
python -m pytest tests/rerg/test_percent_decoder_properties.py
```

The supplied Ruff configuration targets Python 3.12 and enables only E4/E7/E9/F correctness rules; it is not a general style policy. The mypy configuration selects `rerg/raw_derivation.py` and `rerg/path_query.py`, so it is not portable as-is to other module layouts or Python versions. Both configurations are pilot-specific starting points. The RERG Hypothesis example bounds generated input length and example count; review whether those bounds and the property fit the consumer's behavior. Treat newly adopted or noisy checks as advisory until their signal and cost are established; do not suppress findings merely to make a trial pass.

Python's built-in profiler can be used for a measured performance question, but the following target is RERG-specific and profiling is not a gate:

```sh
python -m cProfile -s cumulative -m pytest -q tests/rerg/test_percent_decoder.py \
  -k bounded_deterministic_corpus
```

## Optional deeper checks

Mutation testing with mutmut is an optional candidate, not a delivered or required component. No mutmut configuration, dependency installation, or mutation run is provided here. If evaluating it, check current release documentation, provision it separately, select a narrow source and test target, and run it in a disposable copy; do not infer a supported command or configuration from the RERG example above.

These examples provide neither consumer enforcement nor evidence that every target project's tests or type checks pass. Adapt and verify the native commands in the consumer environment before making them blocking.