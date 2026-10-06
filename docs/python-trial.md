# Selectable native quality checks

One source-asset adopter serves Python and TypeScript. Reuse consumer tools, configs, tests and domain oracles; this is not a runner, installer framework or consumer adoption grant. RERG and Gajaeway source/configuration remain unchanged by this kit increment.

## Selection and ownership

The adoption host requires Python 3.11+ (standard library only). TypeScript-only consumption requires **no Python runtime** after adoption. No command downloads or provisions dependencies.

```sh
# Preview first; --apply performs only the displayed selected asset changes.
python3 /path/to/gajaestack/scripts/adopt_python_trial.py \
  --root /path/to/consumer --component ruff --component guard
python3 /path/to/gajaestack/scripts/adopt_python_trial.py \
  --root /path/to/consumer --component ruff --component guard --apply
# TypeScript uses the SAME adopter, not a recipe fork.
python3 /path/to/gajaestack/scripts/adopt_python_trial.py \
  --root /path/to/consumer --component typescript
```

| Component | Managed destination / purpose |
| --- | --- |
| `ruff` | `.gajaestack/python-trial/ruff.toml`, `.gajaestack/scripts/check_changed_python.py` |
| `guard` | `.gajaestack/python/pytest_guard.py`: early pytest prerequisites, no Ruff dependency |
| `required-ruff` | `.gajaestack/python/pytest_required_ruff.py`: explicit required Ruff binding; requires `guard` and `ruff` |
| `mypy` | `.gajaestack/python-trial/mypy.ini`: advisory RERG-shaped scope |
| `hypothesis` | `tests/rerg/test_percent_decoder_properties.py`: separately selected RERG property example |
| `typescript` | `.gajaestack/typescript/check.ts`: selected native tsc/Biome checks hosted by Bun |
| `typescript-guard` | `.gajaestack/typescript/preload.ts`: separately adopted Bun test binding; requires `typescript` |
| `typescript-config` | `.gajaestack/typescript/tsconfig.json`: optional baseline to extend, never replaces root tsconfig |
| `routing` | A delimited root `AGENTS.md` addendum, and an absent-only RERG-shaped facts template |

The adopter never edits `package.json`, `tsconfig.json`, `biome.json`, `bunfig.toml`, pytest configuration or existing consumer facts. Review and explicitly adopt native wiring separately. For TypeScript, supply reviewed facts before selecting `routing`; the absent-only template is Python/RERG-shaped, not a portable auto-configuration.

`.gajaestack/routing.toml` is the single consumer-owned facts authority. The helper validates existing facts without rewriting them. Component metadata does not install assets. Binding adoption requires declared prerequisites; prerequisite removal is refused while its binding asset remains. Remove the binding explicitly and remove its native wiring as a reviewed consumer change; stale wiring fails rather than silently becoming a pass.

`.gajaestack/ownership.json` has schema `gajaestack-adoption-ownership-v1` and an `assets` map keyed by exact destination. Each entry contains the kit-relative `source`, reviewed `version`, and `hash` (`sha256-` plus 64 hex digits). Development assets identify as `unreleased-overlay`, not a published release. Updates/removal validate recorded prior hashes, so old unedited versions can update and edited assets are refused. Identical unowned bytes are not ownership evidence: reviewed historical source/version/hash inventory is required. Unknown paths, mixed sources and symlinks are refused.

`--remove` previews removal; `--remove --apply` removes only selected owned assets or the managed AGENTS span. Facts and unrelated AGENTS bytes survive; AGENTS itself is never deleted. Malformed/duplicate markers and edited spans are refused. This is not a multi-file transaction or a hostile-concurrency security boundary; I/O failures may leave partial changes and report completed paths.

## Python: quick feedback versus completion

Provision the selected Python interpreter, pytest and (only when selected) Ruff through the consumer's existing environment. The bundled Ruff config targets Python 3.12 E4/E7/E9/F correctness, not style. Choose consumer-specific paths explicitly:

```sh
# Working-tree feedback, including staged/unstaged/untracked Python files.
python .gajaestack/scripts/check_changed_python.py \
  --path rerg/raw_derivation.py --path tests/rerg/test_percent_decoder.py
# Completion: full selected scope, independent of Git changes/commit state.
python .gajaestack/scripts/check_changed_python.py --full
```

Full mode reads `[python].ruff_paths` and `ruff_config` from the facts below; `--path` cannot narrow completion. Quick mode's no-target result is **no coverage**, not lint success. Shared config/helper/facts changes and declared `--impact` paths expand quick checking to the full declared scope, not the whole repository. Full mode refuses empty/missing/escaping targets and preserves native Ruff failures. Paths outside selected scope remain unchecked. Ruff runs with `--no-cache` so the prerequisite itself does not create a checkout cache. The helper does not format or infer affected tests.

### Explicit native pytest binding

This is an example for a disposable or separately approved consumer, not authorization to change RERG. Use the consumer's approved interpreter from its declared root. Extend existing pytest configuration rather than replacing it. On the observed pytest 9.1.1 startup path, `pythonpath` is configured before explicit plugin loading:

```ini
[pytest]
pythonpath = .gajaestack/python .
addopts = --disable-plugin-autoload -p pytest_guard -p pytest_required_ruff -p no:cacheprovider
testpaths = tests
```

For **guard-only**, omit `-p pytest_required_ruff`; merely installing Ruff and guard does not bind them. Facts retain the existing required/advisory/on_demand and four conditional policy fields. Relevant Python facts are:

```toml
[fact]
schema_version = 1
selected_components = ["guard", "ruff", "required-ruff"]
required_ruff_before_pytest = "active"
python_version = "3.12"
test_command = "python -B -m pytest"
affected_test_command = "python -B -m pytest tests/test_example.py"
ruff_command = "python .gajaestack/scripts/check_changed_python.py --path example.py"
ruff_format_command = "ruff format --check example.py"
ci_jobs_added = false
pcd_is_enforcement = false

[python]
schema_version = 1
python_version = "3.12"
imports = []
executables = []
ruff_paths = ["example.py", "tests/test_example.py"]
ruff_config = ".gajaestack/python-trial/ruff.toml"
```

Optional `[python]` fields `root`, `source_root`, `prefix`, `base_prefix` declare actual identity constraints (paths resolve relative to the consumer root); `[python.module_origins]` maps names from `imports` to approved exact files or containing directories. The guard inspects filesystem package chains before importing their parents, checks all declared origins before initializing those imports, and rejects protected source modules already imported at guard time. It cannot undo earlier imports. Do not copy another repository's host paths. Declare only dependencies needed by the selected test surface; optional property/build dependencies do not belong in every focused invocation. A binding additionally requires `ruff-check` in `required`. Stale `"pending"` activation metadata is rejected for explicit consumer review.

Supported configured entry points are `python -B -m pytest`, a focused file/nodeid, and `--collect-only`. Initial prerequisite and explicitly bound full Ruff checks run before consumer conftest/test imports, not from a late fixture. Missing prerequisites or lint failures reject collection; subsequent native test failures remain failures. Approved imports can themselves have effects; the guard is not a sandbox.

Trusted startup includes Python site initialization, pytest itself and earlier plugins. Disabling/replacing configuration (`-c`, `-o addopts=`, `-p no:...`), injected/preloaded code, `pytest.main`, IDE adapters and different working directories are not an immutable admission boundary. Do not claim all plugin effects are prevented or unchecked merging impossible. Direct console-script startup and other pytest versions need separate evidence. No-bytecode launch and disabled cache prevent those checkout writes; arbitrary consumer tests/builds can still write. Use native external disposable temp/build directories and reviewed no-write assertions for any broader claim.

Formatting and mypy remain advisory:

```sh
ruff format --check --config .gajaestack/python-trial/ruff.toml <selected-paths>
mypy --config-file .gajaestack/python-trial/mypy.ini
```

Do not run RERG's illustrative bare commands in its actual checkout: its existing documented environment/canary contract remains authoritative until separately approved native adoption replaces it.

## TypeScript: Bun hosts real typechecking and lint

Use the consumer's existing local `node_modules/.bin/tsc` and `node_modules/.bin/biome`. Bun invokes their actual JS launchers, so Node is not silently required. No `bunx` fallback or downloads occur. Existing native tsconfig/Biome configs remain authoritative; the optional baseline is not a mandatory config migration.

Supply full routing categories and conditional policies, then relevant facts such as:

```toml
[fact]
schema_version = 1
selected_components = ["typescript", "typescript-guard"]
test_command = "bun test"
affected_test_command = "bun .gajaestack/typescript/check.ts --quick"
ci_jobs_added = false
pcd_is_enforcement = false

[typescript]
schema_version = 1
typecheck = true
lint = true
tsconfig = "tsconfig.json"
biome_config = "biome.json"
paths = ["src"]
```

Required preload checks must also appear in `required` as `ts-typecheck` and/or `ts-lint`. Quick and completion commands:

```sh
bun .gajaestack/typescript/check.ts --quick  # selected lint, NOT changed-only or typecheck
bun .gajaestack/typescript/check.ts          # selected tsc --noEmit, then lint
bun test                                   # configured native test boundary
```

For a bound consumer, `bun test` is the completion command: do not chain the standalone check first, which would repeat type/lint checks in the preload. Use the standalone completion check when no native test binding is adopted.

Typechecking uses the complete tsconfig file selection, not just lint paths. `--showConfig` establishes non-empty selected files; `--noEmit --incremental false` prevents compiler emission/build-info output. Composite projects incompatible with these flags fail natively rather than being rewritten. Biome uses explicit selected source files, does not format/write and does not hide unmatched-file failures. Missing tools, invalid configuration and empty selected scope fail visibly. No lint selected in quick mode means no coverage, not a typecheck pass.

To explicitly bind checks before Bun test imports, merge this native setting into existing `bunfig.toml` only with consumer adoption approval:

```toml
[test]
preload = ["./.gajaestack/typescript/preload.ts"]
```

No preload is installed into consumer config automatically. Both source assets installed but no native preload means no automatic checks. Preserve existing preloads and assess their order: earlier startup/preload effects are trusted. Replacing config/preload or invoking another test path can bypass local integration. This guard does not bind Bun build/transpilation or merge admission. A passing Bun build is not a required typecheck result. Selected checks and native test failures retain their failure statuses.

## Native verification, six capabilities, and evidence limits

Do not invent a build/CLI wrapper. Consumer facts name native test commands and scopes; native tests retain their independent domain oracles. Schema rejection, admission-before-dispatch, CLI outcomes and artifact contents are different claims: verify each through its relevant native tests, and do not treat unpacked-artifact CLI checks as installed-console proof.

Run build tests on an **owned external source snapshot/build workspace**: the existing setuptools backend fixture can write build metadata in its source directory even when wheel output is external. Check the declared backend requirement before invoking it, propagate no-bytecode settings to children, and compare original source/dependency trees when claiming they were untouched. No backend/download is provisioned by these assets. Consumer fixture repair or actual consumer integration remains separately approved; this kit does not silently mutate it.

Report actual commands, scope, native exit status, test counts, deliberate rejection cases, skips/not-run reasons and permitted evidence location. A test that correctly asserts rejection passes; a failed guard is a rejection, not a successful check. Empty selections and missing tools are not coverage. Preserve owned evidence; clean only task-owned disposable state.

The six capabilities remain distinct: native quality gains bounded native guards; type discipline gains selected compiler rejection rather than a new type framework; verify-change reuses native schema/CLI/build oracles. Cleanup-learning removes repeated manual startup/scoping rituals only after their replacements are proven. Focused review and hotspot investigation remain selective/on-demand guidance (profiling or property tests for a concrete question); no automatic review panel, mutation dependency or universal runner is added. Formatting/mypy are not promoted to required. All-six delivery, RERG/Gajaeway adoption, broader host/version support, CI/merge enforcement, new runners and immutable non-skippability are **not claimed**.
