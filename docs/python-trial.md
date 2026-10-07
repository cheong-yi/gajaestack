# Selectable native quality checks

Two native packages built from one source serve Python and TypeScript: the `gajaestack` wheel/sdist and the `gajaestack` Bun package, both version `0.1.0`. Reuse consumer tools, configs, tests and domain oracles; this is not a runner, installer framework or adoption grant. RERG and Gajaeway source/configuration remain unchanged by this kit increment. There is no adoption or ownership CLI: native installation writes dependency directories and locks, not consumer facts or check configuration.

## The five-step journey

1. **Inspect.** Read the [entry point](../AGENTS.md), the [README](../README.md) and this guide, and inspect the consumer's existing tools, native configuration and test entrypoints before recommending anything.
2. **Select.** Recommend the smallest useful selection. Components stay independent: prerequisites are named explicitly and never expanded implicitly.
3. **Reviewed facts.** Write `.gajaestack/routing.toml` yourself and review it: it is the single facts authority and no command creates or rewrites it. It names the one completion command (`[fact].test_command`) and the selection; the complete examples below are starting points, not truth. Optional `[fact].completion_timeout_seconds` budgets that command — see the [budget contract](#project-owned-outer-completion-budget).
4. **Pinned install, then separately reviewed native wiring.** Build and install the pinned local artifacts (below); binding them into native configuration — pytest options/plugins, `bunfig.toml` preload — is a separate, explicitly reviewed consumer change.
5. **Valid pass and seeded rejection.** Run the configured native entrypoints: a valid pass over real scope, plus a deliberately seeded rejection proving the guard refuses what it should. A correctly asserted rejection passes; missing tools, empty scope and failed checks remain failures.

**Installed, wired, demonstrated.** *Installed* means the pinned package is present in the consumer environment. *Wired* means your reviewed native configuration binds the guard and consumer facts declare the selection; file presence proves no runtime behavior. *Demonstrated* means the native-run evidence of step 5; only demonstration shows behavior. The optional property-test example ships inside the wheel and is executed as an installed resource — `python -B -m pytest --pyargs gajaestack.test_percent_decoder_properties` — never by copying shared source into the consumer; it imports `rerg.raw_derivation`, so a RERG-shaped application with pytest and Hypothesis installed is an explicit prerequisite, and an unresolved import is a failure, not a skip. Alternatively pass its `importlib.resources` path (below) to a test collection that accepts file paths.

## Install from local artifacts (no registry)

No registry publication is assumed and nothing is downloaded: build from a gajaestack source checkout, then install the exact pinned file. Python-only consumption needs no Bun; TypeScript-only consumption needs no Python.

For Python, activate the consumer's existing approved environment first (for a `.venv` consumer, `. .venv/bin/activate`) so `python` and selected executables such as Ruff resolve from that environment. This is not permission to create an environment or provision tools. Facts should name the actual native commands and existing application paths; the guard checks the running interpreter's no-bytecode state, not the spelling of `test_command`.

```sh
# Python — the wheel build requires an environment with setuptools >= 77;
# --no-index and --no-build-isolation keep it offline:
python -m pip wheel --no-index --no-deps --no-build-isolation \
  --wheel-dir /tmp/artifacts /path/to/gajaestack
python -m pip install --no-index --no-deps --no-compile \
  /tmp/artifacts/gajaestack-0.1.0-*.whl
# Recommendation: pin the wheel's SHA-256 in a reviewed requirements file
# (pip --require-hashes) rather than trusting a path alone.
# Upgrade/reinstall (example: 0.1.0 -> 0.1.1): rebuild into a new directory —
# never reuse the old artifact path — then force-reinstall that exact wheel.
python -m pip wheel --no-index --no-deps --no-build-isolation \
  --wheel-dir /tmp/artifacts-0.1.1 /path/to/reviewed-0.1.1-source
python -m pip install --no-index --no-deps --no-compile --force-reinstall \
  /tmp/artifacts-0.1.1/gajaestack-0.1.1-*.whl

# TypeScript:
bun pm pack --ignore-scripts --destination /tmp/artifacts
bun add --dev --exact --offline gajaestack@/tmp/artifacts/gajaestack-0.1.0.tgz --ignore-scripts --backend=copyfile
# Commit package.json and bun.lock through normal review; reproduce offline with
#   bun install --frozen-lockfile --offline --ignore-scripts --backend=copyfile
# Upgrade: retain the explicit name and use a distinct reviewed artifact:
#   bun add --dev --exact --offline --ignore-scripts --backend=copyfile gajaestack@/absolute/gajaestack-0.1.1.tgz
```

The native `copyfile` backend keeps installed guidance singly linked for GJC 0.18.7; Bun's default cache hardlinks are rejected by that host. See the [selective skills recipe](../README.md#skills-gjc) and its prompt-context acceptance limit.

For a hash-pinned Python install, use `python -m pip hash /tmp/artifacts/gajaestack-0.1.0-py3-none-any.whl`, then add the reviewed artifact URL and digest to the consumer's existing requirements lock:

```text
gajaestack @ file:///tmp/artifacts/gajaestack-0.1.0-py3-none-any.whl --hash=sha256:<reviewed-digest>
```

Install/reproduce with `python -m pip install --no-index --no-deps --no-compile --require-hashes -r requirements-dev.txt`; `--force-reinstall` reinstalls those same pinned bytes. Upgrade by reviewing the new artifact and changing its URL and digest together. Keep the artifacts available at the locked paths. A rebuild does not increment a version: the `0.1.1` example requires source with reviewed `0.1.1` metadata, not unchanged `0.1.0` source.

The Bun package bundles no dependencies and runs no install scripts or hooks; its checks invoke the consumer's existing local `node_modules/.bin/tsc` and `node_modules/.bin/biome` (Bun invokes the actual JS launchers, so Node is not silently required; no `bunx` fallback or downloads occur), and installing or upgrading those tools is separately authorized. The Python distribution declares no install dependencies and registers no pytest11 autoload entry points — its plugins load only from your explicit `-p` selections. Existing native tsconfig/Biome/pytest configs remain authoritative; `gajaestack/tsconfig` is an optional `"extends"` baseline, never automatic configuration.

## Facts selections

Facts are runtime declarations only; the checks read them from the consumer's working directory.

| Selection | Activates (your reviewed wiring) |
| --- | --- |
| `guard` | `-p gajaestack.pytest_guard` in pytest configuration: early pytest prerequisites before test imports |
| `ruff` | `gajaestack-python-check` (quick/full) over `[python].ruff_paths` and `[python].ruff_config` |
| `required-ruff` | `-p gajaestack.pytest_required_ruff`; requires `guard`, `ruff`, and `ruff-check` in `required` |
| `typescript` | `bun run gajaestack-check`: selected tsc/Biome checks over consumer cwd configs/executables |
| `typescript-guard` | `gajaestack/preload` in `bunfig.toml` `[test].preload`; requires `typescript` |

`ruff_config` names a **consumer-owned** config file; the package never copies configuration into your repository. Packaged example assets are read in place:

```sh
python -B -c 'from importlib.resources import files; print(files("gajaestack").joinpath("ruff.toml"))'
```

`mypy.ini`, the property-test example and `routing/AGENTS.md` resolve the same way; the Bun package carries its files under `node_modules/gajaestack/`. Use packaged resources in place rather than copying shared source: run the property test via `--pyargs` (above), and run the optional advisory check against the packaged config directly — `mypy --config-file "$(python -B -c 'from importlib.resources import files; print(files("gajaestack").joinpath("mypy.ini"))')"`. An example is not truth, `ruff_config` stays a consumer-owned file (write and review your own), and a mixed Python/TypeScript consumer keeps one reviewed facts file. For GJC skill discovery/body loading and the `--append-system-prompt` routing recipes with their verified boundaries, use the [README](../README.md).

## Project-owned outer completion budget

Optionally set `completion_timeout_seconds` directly in `[fact]`, alongside the existing `test_command`, in consumer-owned `.gajaestack/routing.toml`. It budgets that one completion command's entire declared scope, including startup and bound checks, not the quick command or individual tests. The value must be a positive finite integer number of seconds from **1 through 9007199254740991** (the exact integer range shared by Python and JavaScript); use TOML integer notation. A specified budget also requires a nonblank `test_command`. Boolean, zero, negative, string, fractional, nonfinite and out-of-range values, and placement anywhere other than directly under `[fact]`, are rejected at the facts-validation boundaries. Omission means **unconfigured**, never an implicit 300s or 600s policy.

Numeric parsing boundary: facts validation requires a TOML integer. Bun exposes TOML integers and floats as JavaScript numbers, so its native check validates the parsed safe-integer value; integral float syntax such as `1.0` is indistinguishable from `1` there. Use integer notation for consistent validation across both runtimes.

For example, a project could provisionally choose `completion_timeout_seconds = 600` after observing a 339.36s full-suite run. That is a project-specific headroom decision, not a measured universal policy or a template default; review it when the declared command/scope changes. Existing facts are preserved: consumers supply values, not recipe forks.

The facts file carries the configured seconds or its explicit unconfigured state alongside the completion command. The **calling launcher must honour the outer budget**, preserve logs, and report an outer timeout as **incomplete verification**, distinct from a native test/check failure. When unconfigured, report that fact and the launcher's actual limit rather than claiming unlimited execution. Re-read the facts after changing them; guidance rendered earlier is only a snapshot.

This kit validates the fact at its native check boundaries; it does not launch the completion command, change agent bash-tool/CI limits, or guarantee that an external launcher accepts every schema-valid value. The launcher must read current facts and explicitly set a supported execution limit; unsupported limits require an explicit report, not silent clamping or retries. External launcher integration and consumer/CI adoption remain separately scoped work. There is no second runner, command registry, adaptive ratchet, cache or concurrency policy.

An outer command budget is separate from Bun's per-test `--timeout` in milliseconds, pytest's native faulthandler settings or a timeout plugin's test deadlines, and native-check subprocess timing/`--timing` diagnostics. None of those defaults or native exit statuses changes. Invalid specified budgets fail at facts validation and, on configured native guard paths, before protected test imports. Quick checks that do not otherwise load facts do not gain a new facts dependency.

## Python: quick feedback versus completion

Provision the selected Python interpreter and (only when selected) Ruff through the consumer's existing environment. A Ruff-only selection needs no pytest: pytest is a prerequisite only when the selection activates the pytest integration (`guard`/`required-ruff`) or a run executes consumer pytest tests. The packaged Ruff example targets Python 3.12 E4/E7/E9/F correctness, not style. Choose consumer-specific paths explicitly in facts:

```sh
gajaestack-python-check --full   # completion: full declared scope, independent of working-tree state
gajaestack-python-check          # quick (no flag)
```

Full mode reads `[python].ruff_paths` and `[python].ruff_config` from the facts below and cannot be narrowed; it refuses empty/missing/escaping targets and preserves native Ruff failures. Quick intersects staged, unstaged and untracked changes with the declared `ruff_paths`, expanding to the full declared scope when shared config/helper/facts inputs change; an empty intersection is **no coverage**, not a lint pass. **From an installed package, quick conservatively runs the full declared lint scope on every invocation**: installed code is invisible to the consumer's Git and no persistent baseline/cache is written to prove it unchanged, so budget a full lint pass per quick run. Quick never replaces `--full`. Paths outside the selected scope remain unchecked, and the check does not format or infer affected tests. Missing tools, invalid configuration and empty selected scope fail visibly.

Quick mode retains its Git prerequisite; `--full` and the pytest binding do not require Git.

The setuptools console entrypoint does not add `-B`: when bytecode writes into a consumer-local `.venv` must be avoided, run `PYTHONDONTWRITEBYTECODE=1 gajaestack-python-check ...` (or `python -B -m gajaestack.check_changed_python ...`). The pytest guard binding already requires `-B` or the environment equivalent, the documented install uses `--no-compile`, and no bare console startup is claimed never to write bytecode. The check itself runs Ruff with `--no-cache`.

The shared Ruff boundary forces `--no-cache --no-fix --no-fix-only` and ignores `RUFF_OUTPUT_FILE`, preserving lint policy without allowing check-time edits or report-file writes. Quick discovery disables Git's optional index writes. Installed quick checks resolve the declared scope from consumer cwd even inside an enclosing Git worktree.

`gajaestack-imports <importname>...` reports import discoverability only: it does not install packages, establish version compatibility, prove successful module initialization, or replace the selected check. Name only imports required by that check; build backends and parser plugins are independent prerequisites.

When the explicit native pytest binding below is active, the configured native test launch (`python -B -m pytest`) is the completion command: the bound full Ruff check runs before collection, so chaining `gajaestack-python-check --full` first repeats completed lint work. Use `--full` as the completion check when no native test binding is adopted.

### Explicit native pytest binding

This is an example for a disposable or separately approved consumer, not authorization to change RERG. Use the consumer's approved interpreter from its declared root. Preserve existing pytest options and plugins: merge the binding lines into the consumer's current configuration rather than replacing it (the example shows the merge), and assess what `--disable-plugin-autoload` would stop loading in a consumer that relies on autoloaded plugins:

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
pythonpath = .
addopts = -q --strict-markers -p existing_plugin -p gajaestack.pytest_guard -p gajaestack.pytest_required_ruff -p no:cacheprovider
testpaths = tests
```

The guard requires no-bytecode execution (`python -B` in `test_command`) and a disabled pytest cacheprovider (`-p no:cacheprovider`); review that explicit cache-plugin change as part of native wiring, especially if existing tests depend on it. Other existing plugins/options remain intact. For **guard-only**, select only `-p gajaestack.pytest_guard`; merely installing the distribution does not bind it, and no entry-point autoload loads these plugins implicitly. Facts retain the required/advisory/on_demand categories and the four conditional policies. A complete, schema-valid Python facts example (full file, not a fragment; template examples are starting points, not truth):

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
ruff_command = "gajaestack-python-check"
ruff_format_command = "ruff format --check example.py"
ci_jobs_added = false
pcd_is_enforcement = false

[python]
schema_version = 1
python_version = "3.12"
imports = []
executables = []
ruff_paths = ["example.py", "tests/test_example.py"]
ruff_config = "ruff.toml"
```

Optional `[python]` fields `root`, `source_root`, `prefix`, `base_prefix` declare actual identity constraints (paths resolve relative to the consumer root); `[python.module_origins]` maps names from `imports` to approved exact files or containing directories. The guard inspects filesystem package chains before importing their parents, checks all declared origins before initializing those imports, and rejects protected source modules already imported at guard time. It cannot undo earlier imports. Do not copy another repository's host paths. Declare only dependencies needed by the selected test surface; optional property/build dependencies do not belong in every focused invocation. A binding additionally requires `ruff-check` in `required`.

Supported configured entry points are `python -B -m pytest`, a focused file/nodeid, and `--collect-only`. Initial prerequisite and explicitly bound full Ruff checks run before consumer conftest/test imports, not from a late fixture. Missing prerequisites or lint failures reject collection; subsequent native test failures remain failures. Approved imports can themselves have effects; the guard is not a sandbox.

Trusted startup includes Python site initialization, pytest itself and earlier plugins. Disabling/replacing configuration (`-c`, `-o addopts=`, `-p no:...`), injected/preloaded code, `pytest.main`, IDE adapters and different working directories are not an immutable admission boundary. Do not claim all plugin effects are prevented or unchecked merging impossible. Direct console-script startup and other pytest versions need separate evidence. No-bytecode launch and disabled cache prevent those checkout writes; arbitrary consumer tests/builds can still write. Use native external disposable temp/build directories and reviewed no-write assertions for any broader claim.

Formatting and mypy remain advisory. Ruff formatting runs against your consumer-owned `ruff.toml`; the optional advisory mypy run can point at the packaged config resource directly (no copy):

```sh
ruff format --check --config ruff.toml <selected-paths>
mypy --config-file "$(python -B -c 'from importlib.resources import files; print(files("gajaestack").joinpath("mypy.ini"))')"
```

Do not run RERG's illustrative bare commands in its actual checkout: its existing documented environment/canary contract remains authoritative until separately approved native adoption replaces it.

## TypeScript: Bun hosts real typechecking and lint

Use the consumer's existing local `node_modules/.bin/tsc` and `node_modules/.bin/biome`. Bun invokes their actual JS launchers, so Node is not silently required. No `bunx` fallback or downloads occur. Existing native tsconfig/Biome configs remain authoritative; the packaged baseline is optional (`"extends": "gajaestack/tsconfig"` in the consumer tsconfig) and is never applied automatically. The `[typescript]` paths below resolve against the consumer's working directory.

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
affected_test_command = "bun run gajaestack-check --quick"
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
bun run gajaestack-check --quick  # quick: changed-file lint intersection from a source checkout,
                                  # full declared lint scope from an installed package; never typechecks
bun run gajaestack-check          # completion: selected tsc --noEmit, then lint
bun run gajaestack-check --timing # phase timing on stderr; also GAJAESTACK_TIMING=1
bun test                          # configured native test boundary
```

For a bound consumer, `bun test` is the completion command: do not chain the standalone check first, which would repeat type/lint checks in the preload. Use the standalone completion check when no native test binding is adopted.

Quick mode is a changed-file lint intersection: existing staged, unstaged, and untracked files intersected with the declared lint paths, and it never typechecks. Changes to the facts, the Biome configuration, or the checker itself expand a quick run to the full declared lint scope, so quick feedback cannot hide a policy-wide regression. **From an installed package, quick conservatively covers the full declared lint scope on every invocation**: installed shared code is ignored by consumer Git — including locally modified bytes and dependency upgrades — and without a written baseline/cache it cannot be proven unchanged; budget a full lint pass per quick run. An empty intersection is **no coverage**, not a lint pass. The checker accepts `--timing` / `GAJAESTACK_TIMING=1`: phase elapsed time, counts, and exit status on stderr, informational only (the preload passes no arguments, so the environment form is the one that works under the native binding).

Quick discovery requires Git and fails visibly if changes cannot be read, including filenames that cannot be decoded as UTF-8; completion does not require Git. Rename origins participate in policy invalidation, while deleted files are not lint targets. Nested `biome.json`/`biome.jsonc` changes and tracked local `extends`/plugin dependencies invalidate the selection. Config dependencies that cannot be enumerated conservatively (including commented JSONC or package references) expand any changed working tree to full declared lint scope rather than guessing native config semantics.

Typechecking uses the complete tsconfig file selection, not just lint paths. `--showConfig` establishes non-empty selected files; `--noEmit --incremental false` prevents compiler emission/build-info output. Composite projects incompatible with these flags fail natively rather than being rewritten. Biome uses explicit selected source files, does not format/write and does not hide unmatched-file failures. Missing tools, invalid configuration and empty selected scope fail visibly. No lint selected in quick mode means no coverage, not a typecheck pass.

To explicitly bind checks before Bun test imports, merge this native setting into existing `bunfig.toml` only with consumer approval. For a project already loading `existing-preload.ts`, preserve it and its position:

```toml
[test]
preload = ["./existing-preload.ts", "gajaestack/preload"]
```

No preload is installed into consumer config automatically: installing the package without the native preload means no automatic checks. Preserve existing preloads and assess their order: earlier startup/preload effects are trusted. Replacing config/preload or invoking another test path can bypass local integration. This guard does not bind Bun build/transpilation or merge admission. A passing Bun build is not a required typecheck result. Selected checks and native test failures retain their failure statuses.

Configuration presence proves no runtime behavior: demonstrate by running the declared test command plus a seeded rejection (for example a type error or lint violation that `bun run gajaestack-check` and the bound `bun test` must refuse). When no declared binding covers a selected check, run the standalone check explicitly (`bun run gajaestack-check` or `gajaestack-python-check --full`) and review consumer facts and native wiring yourself; this kit reads or edits no native configuration and offers no preview, adoption or repair command.

## Native verification, six capabilities, and evidence limits

Do not invent a build/CLI wrapper. Consumer facts name native test commands and scopes; native tests retain their independent domain oracles. Schema rejection, admission-before-dispatch, CLI outcomes and artifact contents are different claims: verify each through its relevant native tests, and do not treat unpacked-artifact CLI checks as installed-console proof.

Run build tests on an **owned external source snapshot/build workspace**: the setuptools build (including the offline `pip wheel` command above) can write build metadata such as `.egg-info` into its source directory even when wheel output is external. Check the declared backend requirement before invoking it, propagate no-bytecode settings to children, and compare original source/dependency trees when claiming they were untouched. No backend/download is provisioned by these commands. Consumer fixture repair or actual consumer integration remains separately approved; this kit does not silently mutate it.

Report actual commands, scope, native exit status, test counts, deliberate rejection cases, skips/not-run reasons and permitted evidence location. A test that correctly asserts rejection passes; a failed guard is a rejection, not a successful check. Empty selections and missing tools are not coverage. Preserve owned evidence; clean only task-owned disposable state.

The six capabilities remain distinct: native quality gains bounded native guards; type discipline gains selected compiler rejection rather than a new type framework; verify-change reuses native schema/CLI/build oracles. Cleanup-learning removes repeated manual startup/scoping rituals only after their replacements are proven. Focused review and hotspot investigation remain selective/on-demand guidance (profiling or property tests for a concrete question); no automatic review panel, mutation dependency or universal runner is added. Formatting/mypy are not promoted to required. All-six delivery, RERG/Gajaeway adoption, broader host/version support, CI/merge enforcement, new runners and immutable non-skippability are **not claimed**.
