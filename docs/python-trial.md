# Selectable native quality checks

One source-asset CLI serves Python and TypeScript. Reuse consumer tools, configs, tests and domain oracles; this is not a runner, installer framework or consumer adoption grant. RERG and Gajaeway source/configuration remain unchanged by this kit increment.

## The five-step journey

1. **Inspect.** Read the [entry point](../AGENTS.md), the [README](../README.md) and this guide, run `list`, and inspect the consumer's existing tools, native configuration and test entrypoints before recommending anything.
2. **Select.** Recommend the smallest useful selection. Components stay independent: prerequisites are checked and refused when unmet, never expanded implicitly.
3. **Reviewed facts, then preview.** Supply reviewed consumer facts first (templates are explicit and absent-only, described below), then run `adopt` without `--apply` and review each change's content, source and destination. Preview also names the one completion command your facts already declare (`[fact].test_command`) with their declared binding and required checks (bound checks count as covered only when the declared binding is activated in reviewed native configuration), and the managed `AGENTS.md` addendum span is rendered from those same facts so copied guidance carries that same command — copied bytes stay distinguishable from activation, no runner or cache is invented, and no wiring is claimed.
4. **Approved assets, plus separately reviewed native wiring.** `--apply` replans and revalidates the selected asset changes against current bytes; the earlier preview is not an immutable transaction. Binding them into native configuration — pytest options/plugins, `bunfig.toml` preloads — is a separate, explicitly reviewed consumer change.
5. **Valid pass and seeded rejection.** Run the configured native entrypoints: a valid pass over real scope, plus a deliberately seeded rejection proving the guard refuses what it should. A correctly asserted rejection passes; missing tools, empty scope and failed checks remain failures.

**Copied, activated, demonstrated.** *Copied* means shared asset bytes placed at the documented destination and recorded with source, version and hash in `.gajaestack/ownership.json`; copying guard assets alone does not activate their native bindings. *Activated* means your reviewed native configuration binds the copied guard and consumer facts declare the selection — a separate, explicitly approved consumer change. The optional Hypothesis example is different: its test destination may already be discovered by the existing test harness, so review its imports and domain assumptions before copying. *Demonstrated* means the native-run evidence of step 5; only demonstration shows behavior.

## Selection and ownership

The adoption host requires Python 3.11+ (standard library only). TypeScript-only consumption requires **no Python runtime** after adoption. No command downloads or provisions dependencies.

```sh
# Discovery: list components and their managed destinations.
python3 /path/to/gajaestack/scripts/gajaestack.py list
# Preview first; --apply replans and revalidates the selected changes against
# current bytes.
python3 /path/to/gajaestack/scripts/gajaestack.py adopt ruff guard \
  --root /path/to/consumer
python3 /path/to/gajaestack/scripts/gajaestack.py adopt ruff guard \
  --root /path/to/consumer --apply
# TypeScript uses the SAME CLI, not a recipe fork; the facts template is an
# explicit, absent-only opt-in.
python3 /path/to/gajaestack/scripts/gajaestack.py adopt typescript \
  --root /path/to/consumer --facts-template typescript
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
| `routing` | A delimited root `AGENTS.md` addendum rendered from reviewed facts to carry the declared completion command and binding/checks; validates existing facts without rewriting them |

The CLI never edits `package.json`, `tsconfig.json`, `biome.json`, `bunfig.toml`, pytest configuration or existing consumer facts. Review and explicitly adopt native wiring separately as an approved consumer change. Facts templates are explicit and absent-only: `--facts-template python` or `--facts-template typescript` writes a complete, schema-valid example only when `.gajaestack/routing.toml` does not exist, never overwriting or merging existing facts. The examples in this guide are complete files, not fragments — but a template example is not truth: consumer facts remain the single authority and must be reviewed for the consumer. A mixed Python/TypeScript selection needs one reviewed combined facts file; applying both templates in sequence is not a valid path. Bindings require prior facts: adopting `required-ruff` or `typescript-guard` validates existing facts first (the `_check_bindings` prerequisite check) and refuses when facts are absent, invalid, or do not explicitly select the binding.

The CLI templates start unbound, with no outer completion budget configured. The complete examples below instead illustrate reviewed binding selections; they are not byte-for-byte template output. The Python CLI template retains explicitly labeled RERG example paths, which must be reviewed rather than assumed to exist.

The `routing` addendum source stores `{{test_command}}`, `{{completion_budget}}`, `{{declared_binding}}`, and `{{declared_checks}}` as template placeholders: read them as template tokens rendered from reviewed facts at adoption, never as executable facts, and adoption refuses to copy a source whose placeholders are missing or left unrendered. The addendum is a rendered snapshot: current consumer facts remain authoritative. After changing those facts, preview and explicitly re-adopt `routing` to refresh the managed command/budget/check description without rewriting the facts.

`.gajaestack/routing.toml` is the single consumer-owned facts authority. The helper validates existing facts without rewriting them. Component metadata does not install assets. Binding adoption requires declared prerequisites, which are never expanded implicitly — name `guard` and `ruff` (or `typescript`) in the same selection yourself, unless already adopted. Prerequisite removal is refused while its binding asset remains. Remove the binding explicitly and remove its native wiring as a reviewed consumer change; stale wiring fails rather than silently becoming a pass.

`.gajaestack/ownership.json` has schema `gajaestack-adoption-ownership-v1` and an `assets` map keyed by exact destination. Each entry contains the kit-relative `source`, reviewed `version`, and `hash` (`sha256-` plus 64 hex digits). Development assets identify as `unreleased-overlay`, not a published release. Updates/removal validate recorded prior hashes, so old unedited versions can update and edited assets are refused. Identical unowned bytes are not ownership evidence: reviewed historical source/version/hash inventory is required. Unknown paths, mixed sources and symlinks are refused. Source and destination identities are preserved: preview, apply and removal re-check each recorded source/destination pair and hash before any change.

**Repeat adoption is the exact update procedure.** To move adopted assets to newer kit bytes, run the same `adopt <components> --root /path/to/consumer` preview again, review each planned change's content, source and destination, then re-run it with `--apply`. There is no separate updater: apply replans against current state and revalidates each recorded source/version/hash pair, so an unedited previously adopted asset updates in place and its `.gajaestack/ownership.json` entry refreshes, while locally edited, unowned, mixed-source or symlinked destinations are refused rather than overwritten. Re-adopting `routing` the same way refreshes the managed `AGENTS.md` addendum span from the current facts without rewriting them. This procedure changes only kit-owned assets and the managed span — adoption of this kit is not RERG or Gajaeway adoption, and it protects neither build nor merge.

`--remove` previews removal; `--remove --apply` removes only selected owned assets or the managed AGENTS span. Preview reports each change's content, source and destination, and `--apply` replans and revalidates the selected asset changes against current bytes at apply time; the earlier preview is never an immutable transaction. Removal never extends to native wiring or facts: removing wiring (pytest options/plugins, Bun preloads) and cleaning up or deleting facts are separately reviewed consumer changes and are never automated. Facts and unrelated AGENTS bytes survive; AGENTS itself is never deleted. Malformed/duplicate markers and edited spans are refused. This is not a multi-file transaction or a hostile-concurrency security boundary; concurrent creation is refused, and I/O failures may leave partial changes and report completed paths.

Before removing a prerequisite, separately review removal of the binding's declaration from `fact.selected_components` (and `required_ruff_before_pytest` for Python) as well as its native wiring. A stale facts declaration can still block prerequisite removal after the binding asset is gone. Do not delete facts needed by remaining selections.

## Project-owned outer completion budget

Optionally set `completion_timeout_seconds` directly in `[fact]`, alongside the existing `test_command`, in consumer-owned `.gajaestack/routing.toml`. It budgets that one completion command's entire declared scope, including startup and bound checks, not the quick command or individual tests. The value must be a positive finite integer number of seconds from **1 through 9007199254740991** (the exact integer range shared by Python and JavaScript); use TOML integer notation. A specified budget also requires a nonblank `test_command`. Boolean, zero, negative, string, fractional, nonfinite and out-of-range values, and placement anywhere other than directly under `[fact]`, are rejected at the existing facts-validation boundaries. Omission means **unconfigured**, never an implicit 300s or 600s policy.

Numeric parsing boundary: Python/adoption require a TOML integer. Bun exposes TOML integers and floats as JavaScript numbers, so its native check validates the parsed safe-integer value; integral float syntax such as `1.0` is indistinguishable from `1` there. Use integer notation for consistent validation across both runtimes.

For example, a project could provisionally choose `completion_timeout_seconds = 600` after observing a 339.36s full-suite run. That is a project-specific headroom decision, not a measured universal policy or a template default; review it when the declared command/scope changes. Existing facts are preserved during adoption, updates and removal. Shared validation and guidance stay centrally maintained; consumers supply values, not recipe forks.

Preview and managed guidance expose the configured seconds or explicitly say unconfigured alongside the completion command. The **calling launcher must honour the outer budget**, preserve logs, and report an outer timeout as **incomplete verification**, distinct from a native test/check failure. When unconfigured, report that fact and the launcher's actual limit rather than claiming unlimited execution. Re-adopt `routing` after reviewing facts changes to refresh its snapshot.

This kit validates and exposes the fact; it does not launch the completion command, change agent bash-tool/CI limits, or guarantee that an external launcher accepts every schema-valid value. The launcher must read current facts and explicitly set a supported execution limit; unsupported limits require an explicit report, not silent clamping or retries. External launcher integration and consumer/CI adoption remain separately scoped work. There is no second runner, command registry, adaptive ratchet, cache or concurrency policy.

An outer command budget is separate from Bun's per-test `--timeout` in milliseconds, pytest's native faulthandler settings or a timeout plugin's test deadlines, and native-check subprocess timing/`--timing` diagnostics. None of those defaults or native exit statuses changes. Invalid specified budgets fail before adoption writes and, on configured native guard paths, before protected test imports. Quick checks that do not otherwise load facts do not gain a new facts dependency.

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

Both modes accept `--timing` and honor `GAJAESTACK_TIMING=1`: phase elapsed time, counts, and exit status are reported on stderr. Timing is informational — it never changes which checks run, coverage, or exit status — and the environment form is the one that works under a native binding where no extra flag can be passed. Phase timing on stderr is the contract; exact line formatting is not.

When the explicit native pytest binding below is active, the configured native test launch (`python -B -m pytest`) is the completion command: the bound full Ruff check runs before collection, so chaining `check_changed_python.py --full` first repeats completed lint work. Use `--full` as the completion check when no native test binding is adopted.

### Explicit native pytest binding

This is an example for a disposable or separately approved consumer, not authorization to change RERG. Use the consumer's approved interpreter from its declared root. Preserve existing pytest options and plugins: merge the binding lines into the consumer's current configuration rather than replacing it (the example shows the merge), and assess what `--disable-plugin-autoload` would stop loading in a consumer that relies on autoloaded plugins. On the observed pytest 9.1.1 startup path, `pythonpath` is configured before explicit plugin loading:

```ini
# Before — the consumer's existing pytest settings:
[pytest]
pythonpath = .
addopts = -q --strict-markers -p existing_plugin
testpaths = tests
```

```ini
# After — merged: every existing option is preserved, binding options are added.
[pytest]
pythonpath = .gajaestack/python .
addopts = -q --strict-markers -p existing_plugin -p pytest_guard -p pytest_required_ruff -p no:cacheprovider
testpaths = tests
```

The guard requires no-bytecode execution and a disabled pytest cacheprovider; review that explicit cache-plugin change as part of native wiring, especially if existing tests depend on it. Other existing plugins/options remain intact. For **guard-only**, omit `-p pytest_required_ruff`; merely installing Ruff and guard does not bind them. Facts retain the required/advisory/on_demand categories and the four conditional policies. A complete, schema-valid Python facts example (full file, not a fragment; template examples are starting points, not truth):

```toml
required = ["pytest", "ruff-check"]
advisory = ["ruff-format", "mypy"]
on_demand = ["mutation-testing", "profiling", "adversarial-review"]

[conditional]
input_parsing = "Changed parsing of externally supplied values: exercise valid, malformed, and boundary inputs."
authorization_decisions = "Changed a decision about permission, eligibility, or authority: test allow and deny boundaries."
file_writes_deletion = "Changed filesystem mutation behavior: test target confinement, refusal cases, and no partial side effects."
external_commands = "Changed subprocess or executable invocation: test arguments, failures, and prohibited execution paths."

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

A complete, schema-valid TypeScript facts example (full file, not a fragment; template examples are starting points, not truth):

```toml
required = ["ts-test", "ts-typecheck", "ts-lint"]
advisory = []
on_demand = ["mutation-testing", "profiling", "adversarial-review"]

[conditional]
input_parsing = "Changed parsing of externally supplied values: exercise valid, malformed, and boundary inputs."
authorization_decisions = "Changed a decision about permission, eligibility, or authority: test allow and deny boundaries."
file_writes_deletion = "Changed filesystem mutation behavior: test target confinement, refusal cases, and no partial side effects."
external_commands = "Changed subprocess or executable invocation: test arguments, failures, and prohibited execution paths."

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

Required preload checks must also appear in `required` as `ts-typecheck` and/or `ts-lint`, as shown. Quick and completion commands:

```sh
bun .gajaestack/typescript/check.ts --quick  # changed-file lint intersection; expands on facts/Biome config/checker changes; never typecheck
bun .gajaestack/typescript/check.ts          # selected tsc --noEmit, then lint
bun test                                   # configured native test boundary
```

For a bound consumer, `bun test` is the completion command: do not chain the standalone check first, which would repeat type/lint checks in the preload. Use the standalone completion check when no native test binding is adopted.
Quick mode is a changed-file lint intersection: existing staged, unstaged, and untracked files intersected with the declared lint paths, and it never typechecks. Changes to the facts, the Biome configuration, or the checker itself expand a quick run to the full declared lint scope, so quick feedback cannot hide a policy-wide regression. An empty intersection is **no coverage**, not a lint pass. The checker accepts the same `--timing` / `GAJAESTACK_TIMING=1` contract as the Python helper: phase elapsed time, counts, and exit status on stderr, informational only.

Quick discovery requires Git and fails visibly if changes cannot be read, including filenames that cannot be decoded as UTF-8; completion does not require Git. Rename origins participate in policy invalidation, while deleted files are not lint targets. Nested `biome.json`/`biome.jsonc` changes and tracked local `extends`/plugin dependencies invalidate the selection. Config dependencies that cannot be enumerated conservatively (including commented JSONC or package references) expand any changed working tree to full declared lint scope rather than guessing native config semantics.

Typechecking uses the complete tsconfig file selection, not just lint paths. `--showConfig` establishes non-empty selected files; `--noEmit --incremental false` prevents compiler emission/build-info output. Composite projects incompatible with these flags fail natively rather than being rewritten. Biome uses explicit selected source files, does not format/write and does not hide unmatched-file failures. Missing tools, invalid configuration and empty selected scope fail visibly. No lint selected in quick mode means no coverage, not a typecheck pass.

To explicitly bind checks before Bun test imports, merge this native setting into existing `bunfig.toml` only with consumer adoption approval. For a project already loading `existing-preload.ts`, preserve it and its position:

```toml
[test]
preload = ["./existing-preload.ts", "./.gajaestack/typescript/preload.ts"]
```

No preload is installed into consumer config automatically. Both source assets installed but no native preload means no automatic checks. Preserve existing preloads and assess their order: earlier startup/preload effects are trusted. Replacing config/preload or invoking another test path can bypass local integration. This guard does not bind Bun build/transpilation or merge admission. A passing Bun build is not a required typecheck result. Selected checks and native test failures retain their failure statuses.

Preview separates copied from configured from demonstrated for this binding with a read-only `bunfig.toml` status: **manual-only** when `typescript-guard` is absent from `fact.selected_components` (no diagnostic, no automatic binding); **not configured** when `bunfig.toml` or the `./.gajaestack/typescript/preload.ts` entry is missing, with the merge remedy above as your own reviewed change; **configured, not demonstrated** when the entry is found — file presence proves no runtime behavior, so run the declared test command plus a seeded rejection to demonstrate; and **unverified** when `bunfig.toml` is malformed or unreadable, which you must review or repair yourself. The status reads only and never writes or repairs native configuration. When no declared binding covers a selected check, preview also names the standalone selected check (`python .gajaestack/scripts/check_changed_python.py --full` or `bun .gajaestack/typescript/check.ts`) to run explicitly, and every preview ends with separate instructions to explicitly review consumer facts and native wiring.

## Native verification, six capabilities, and evidence limits

Do not invent a build/CLI wrapper. Consumer facts name native test commands and scopes; native tests retain their independent domain oracles. Schema rejection, admission-before-dispatch, CLI outcomes and artifact contents are different claims: verify each through its relevant native tests, and do not treat unpacked-artifact CLI checks as installed-console proof.

Run build tests on an **owned external source snapshot/build workspace**: the existing setuptools backend fixture can write build metadata in its source directory even when wheel output is external. Check the declared backend requirement before invoking it, propagate no-bytecode settings to children, and compare original source/dependency trees when claiming they were untouched. No backend/download is provisioned by these assets. Consumer fixture repair or actual consumer integration remains separately approved; this kit does not silently mutate it.

Report actual commands, scope, native exit status, test counts, deliberate rejection cases, skips/not-run reasons and permitted evidence location. A test that correctly asserts rejection passes; a failed guard is a rejection, not a successful check. Empty selections and missing tools are not coverage. Preserve owned evidence; clean only task-owned disposable state.

The six capabilities remain distinct: native quality gains bounded native guards; type discipline gains selected compiler rejection rather than a new type framework; verify-change reuses native schema/CLI/build oracles. Cleanup-learning removes repeated manual startup/scoping rituals only after their replacements are proven. Focused review and hotspot investigation remain selective/on-demand guidance (profiling or property tests for a concrete question); no automatic review panel, mutation dependency or universal runner is added. Formatting/mypy are not promoted to required. All-six delivery, RERG/Gajaeway adoption, broader host/version support, CI/merge enforcement, new runners and immutable non-skippability are **not claimed**.
