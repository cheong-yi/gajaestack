# Selectable native quality checks

Two native packages built from one source serve Python and TypeScript: the `gajaestack` wheel and Bun tarball, both version `0.1.0`. Reuse consumer tools, configs, tests and domain oracles; this is not a runner, installer framework or adoption grant. RERG and Gajaeway source/configuration remain unchanged by this kit increment. There is no adoption or ownership CLI: native installation writes dependency directories and locks, not consumer facts or check configuration.

## The five-step journey

1. **Inspect.** Read the [entry point](../AGENTS.md), the [README](../README.md) and this guide, and inspect the consumer's existing tools, native configuration and test entrypoints before recommending anything.
2. **Select.** Recommend the smallest useful selection. Components stay independent: prerequisites are named explicitly and never expanded implicitly.
3. **Reviewed facts.** Write `.gajaestack/routing.toml` yourself and review it: it is the single facts authority and no command creates or rewrites it. It names the one completion command (`[fact].test_command`) and the selection; the complete examples below are starting points, not truth. Optional `[fact].completion_timeout_seconds` budgets that command — see the [budget contract](#project-owned-outer-completion-budget).
4. **Pinned install, then separately reviewed native wiring.** Install the retained maintainer-built artifacts using the [native recipe](#install-from-local-artifacts-no-registry); binding them into native configuration — pytest options/plugins, `bunfig.toml` preload — is a separate, explicitly reviewed consumer change.
5. **Valid pass and seeded rejection.** Run the configured native entrypoints: a valid pass over real scope, plus a deliberately seeded rejection proving the selected guard or check refuses what it should. A correctly asserted rejection passes; missing tools, empty scope and failed checks remain failures.

**Installed, wired, demonstrated.** *Installed* means the pinned package is present in the consumer environment. *Wired* means your reviewed native configuration binds the guard and consumer facts declare the selection; file presence proves no runtime behavior. *Demonstrated* means the native-run evidence of step 5; only demonstration shows behavior. The optional property-test example ships inside the wheel and is executed as an installed resource — `python -B -m pytest --pyargs gajaestack.test_percent_decoder_properties` — never by copying shared source into the consumer; it imports `rerg.raw_derivation`, so a RERG-shaped application with pytest and Hypothesis installed is an explicit prerequisite, and an unresolved import is a failure, not a skip. Alternatively pass its `importlib.resources` path (below) to a test collection that accepts file paths.

## Install from local artifacts (no registry)

This is the single installation/upgrade recipe. Maintainers build each native artifact **once from reviewed source**, record its identity, and retain those exact bytes for reuse across approved consumers. Consumers install, not rebuild. One kit version covers both packages; consumer tool versions remain independent. No registry/publication service, release helper, package manager, updater, ordinary-run network check or silent latest is introduced.

Python-only consumers need no Bun; TypeScript-only consumers need no Python unless they independently select the [scb-check advisory](#optional-advisory-scb-check), which requires Python 3.12+. Building both artifacts requires both build runtimes; that is not a consumer prerequisite.

### Maintainer: build once and retain

Review source and version metadata (`python/__init__.py` and `package.json` must agree), selected-component changes and artifact contents. Use an owned external source snapshot: setuptools may write build metadata into its input tree. The following uses a **reviewed commit**, not uncommitted checkout contents. Set `source_repo`, `reviewed_commit`, `build_root` (an owned empty directory), and `artifact_root` (an approved durable absolute directory) explicitly. No command below authorizes publication or provisioning missing prerequisites.

```sh
set -eu
version=0.1.0
commit=$(git -C "$source_repo" rev-parse --verify "$reviewed_commit^{commit}")
artifacts="$artifact_root/$version"
# Fail if this version already exists; never overwrite a retained release.
mkdir "$artifacts"
git -C "$source_repo" archive --format=tar --output="$build_root/source.tar" "$commit"
mkdir "$build_root/source"
tar -xf "$build_root/source.tar" -C "$build_root/source"
printf 'version=%s\nsource_commit=%s\n' "$version" "$commit" > "$artifacts/SOURCE"

# Approved Python build environment: pip and setuptools >= 77 already present.
PYTHONDONTWRITEBYTECODE=1 python -m pip wheel --no-index --no-deps --no-build-isolation \
  --wheel-dir "$artifacts" "$build_root/source"
# Bun packs from its working directory.
(cd "$build_root/source" && bun pm pack --ignore-scripts --destination "$artifacts")
(cd "$artifacts" && sha256sum \
  "gajaestack-$version-py3-none-any.whl" "gajaestack-$version.tgz" > SHA256SUMS)
```

Stop on any failed command. Inspect built metadata and inventories before accepting the record: verify the MIT license declaration and byte-for-byte inclusion of `LICENSE` and `THIRD_PARTY_NOTICES` in the wheel's `.dist-info/licenses/` directory, the Bun tarball's package root, and any source distribution's root. Retain `SOURCE`, `SHA256SUMS` and both artifacts under the version-specific location with owner-controlled write protection; the commands do **not** enforce immutability. Do not replace an accepted artifact in place or rebuild it separately per consumer. A failed/unaccepted build is not a release; review its disposition before retrying. SHA-256 detects changed bytes relative to the reviewed record, not source trust, authorship or reproducible builds. Record build-tool versions with the review evidence (`python --version`, `python -m pip --version`, `python -c 'import setuptools; print(setuptools.__version__)'`, `bun --version`).

Choose a durable location using existing approved storage, not `/tmp`, an expiring cache or this disposable build workspace. No hosting service is prescribed. Approved transfers must preserve bytes and verify against the retained digest; consumers need stable accessible paths, including in CI. An unavailable artifact is a blocker, not permission to rebuild, download or substitute latest. Retain prior releases for rollback.

### Consumer: install the exact artifact

Dependency installation, consumer pin updates, native wiring, host settings and CI changes each require explicitly scoped approval. Inspect selected prerequisites and existing facts/configuration first; this recipe grants none of those approvals. Preserve unrelated selections and configuration. For Python, activate the existing approved environment (for example `. .venv/bin/activate`); this is not permission to create one or provision tools. Facts name actual commands and paths; the guard checks the running interpreter's no-bytecode state, not command spelling.

Set `artifacts` to the approved retained version directory. Verify the selected artifact against its reviewed `SHA256SUMS` entry before installation (for the complete retained directory, `(cd "$artifacts" && sha256sum -c SHA256SUMS)`). Copying an untrusted digest alongside an artifact does not establish trust.

For Python, `python -m pip hash "$artifacts/gajaestack-0.1.0-py3-none-any.whl"` prints the native hash form. Review the exact URL and digest in the consumer's existing requirements lock; the following is a placeholder, not a usable pin:

```text
gajaestack @ file:///absolute/retained/0.1.0/gajaestack-0.1.0-py3-none-any.whl --hash=sha256:<reviewed-digest>
```

```sh
# Python: requirements-dev.txt denotes the consumer's reviewed lock.
python -m pip install --no-index --no-deps --no-compile --require-hashes \
  -r requirements-dev.txt

# Bun: run in the approved consumer root; preserve its existing manifest.
bun add --dev --exact --offline --ignore-scripts --backend=copyfile \
  "gajaestack@$artifacts/gajaestack-0.1.0.tgz"
# Review package.json and bun.lock together; replay their exact retained path:
bun install --frozen-lockfile --offline --ignore-scripts --backend=copyfile
```

`--no-deps` does not provision missing Python prerequisites; `--require-hashes` applies to every requirement in the supplied lock. Bun replay also needs all other locked dependencies already available offline. The separately recorded SHA-256 is the tarball identity check; do not assume a local-path pin alone verifies it. The native `copyfile` backend keeps installed guidance singly linked for GJC 0.18.7; see [selective skills](../README.md#skills-gjc) for the host limitation and selection acceptance.

### Upgrade and rollback

For an approved `0.1.0` → `0.1.1` upgrade, maintainers first review **both** source version declarations as `0.1.1`, then build once into a new retained `0.1.1` directory using the maintainer recipe. Rebuilding unchanged `0.1.0` source does not create `0.1.1`. Review affected selections and unexpected installed-file edits before replacement; preserve evidence and resolve local edits with the consumer owner rather than silently overwriting them.

Consumers verify the new artifacts, review the Python URL and hash together or run the Bun add command with the explicit `gajaestack@` name and new `0.1.1` tarball path, then review the resulting manifest/lock delta. For Python, use the install command above with `--force-reinstall` to ensure the reviewed bytes replace the installed copy. No shared recipes or installed guidance are edited/copied into consumers. Facts and native configuration change only when separately approved.

Before accepting the upgrade, run each affected selected boundary over valid, nonempty scope and a deliberate seeded rejection; restore the seed and observe recovery. Use the declared completion command when it binds those checks, otherwise the selected standalone check. Repeat installed skill discovery/body-loading acceptance when guidance changes, preserving unrelated candidates and the documented diagnostics exception. Record old/new source commit, kit version, artifact path and SHA-256, consumer pin delta, exact commands/statuses and limitations. Missing prerequisites or failed checks block acceptance, not silently pass.

Rollback uses **retained prior artifacts**, not a rebuild: review restoring the prior Python URL/hash and force-reinstall, or use the same explicit Bun add command with the prior tarball and review both manifest and lock. Restore any separately approved affected wiring/facts changes without reverting unrelated consumer work. Re-run the affected valid-pass/rejection/recovery checks and guidance acceptance; record the actual restored version and digest. Native managers do not decide consumer policy or automatically undo configuration changes.

The Bun package bundles no dependencies and runs no install scripts or hooks; its checks invoke the consumer's existing local `node_modules/.bin/tsc` and `node_modules/.bin/biome` (Bun invokes the actual JS launchers, so Node is not silently required; no `bunx` fallback or downloads occur), and installing or upgrading those tools is separately authorized. The Python distribution declares no install dependencies and registers no pytest11 autoload entry points — its plugins load only from your explicit `-p` selections. Existing native tsconfig/Biome/pytest configs remain authoritative; `gajaestack/tsconfig` is an optional `"extends"` baseline, never automatic configuration.

### Deselect or remove

Review the scope first: deselecting one component need not remove the shared package or independent tools. Preserve unrelated consumer facts, commands, configuration and dependencies throughout.

1. Remove the deselected component and attributable check labels/commands from facts. Adjust dependent selections together: for example, retiring `required-ruff` removes its active binding declaration; retiring `scb-check` removes both selections and `scb_check_command`. Keep Ruff, mypy or other tools/commands when independently used. If no kit components remain, retire the kit facts file rather than leave an invalid empty selection; preserve any unrelated data.
2. Remove only the corresponding native bindings: explicit pytest plugins, Bun preload, package config extension or package-backed scripts, as applicable. Before whole-package removal, none may still reference it. Native managers do not rewrite policy; leaving a guard bound to an absent dependency rejects startup rather than safely completing deselection.
3. Review host bindings separately: remove attributable installed skill-directory entries and `--append-system-prompt` file bindings from the consumer's launch settings. Reverse only kit-attributable global skill-filter edits after checking name collisions and existing policy; never remove unrelated filters or hide unrelated skills. Dependency removal does **not** unload already-read guidance or Python modules. Use a fresh host session for post-removal discovery; verify unrelated candidates remain and kit candidates are absent from the removed binding. Other configured kit copies may still expose them; do not remove those without scope approval. No complete context-erasure claim follows.
4. For whole-package removal, remove its pin from the authoritative Python requirements/lock **and any input that regenerates it**, then run `python -m pip uninstall gajaestack` in the approved environment. Uninstall alone leaves a pin that reinstalls on replay. For Bun, `bun remove --offline --ignore-scripts gajaestack` removes the dependency and updates native manifest/lock; review both and any higher-level dependency inputs. Preserve unrelated entries; retain release artifacts for approved rollback.
5. Replay the consumer's normal reviewed environment setup without downloads (Python's hash-pinned offline install or Bun's frozen offline install above), preferably also in an owned fresh fixture. pip install is not a synchronizer: absence from a requirements file does not remove an already installed distribution. Verify the kit stays absent after replay (`python -m pip show gajaestack` should report not found; for Bun check no manifest/lock dependency or `node_modules/gajaestack` remains). Run remaining selected checks over valid scope and affected seeded rejections where feasible. Report missing offline prerequisites or unavailable host verification as limits, not successful removal proof.

## Facts selections

Facts are declarations read from consumer cwd, not automatic activation. These **native facts selections** are separate from GJC's independently selected `native-quality`, `type-discipline` and `verify-change` guidance; skill names are not `selected_components` values. Choose only needed components, not the whole table.

For a complete facts file accepted by `gajaestack-routing --root .`, the common contract is:

- Top-level `required`, `advisory`, `on_demand`: arrays of unique check labels, with no label repeated across categories; `required` is nonempty. Supported labels are `pytest`, `ruff-check`, `ruff-format`, `mypy`, `ts-test`, `ts-typecheck`, `ts-lint`, `scb-check`, `mutation-testing`, `profiling`, `adversarial-review`. Labels describe consumer policy, not executable names or automatic bindings; `scb-check` is advisory-only.
- `[conditional]`: exactly the four nonblank policy strings `input_parsing`, `authorization_decisions`, `file_writes_deletion`, `external_commands`; the complete runtime examples below show their shape.
- `[fact]`: integer `schema_version = 1`, nonempty unique `selected_components` from the table, nonblank `test_command` (completion) and `affected_test_command` (focused feedback), plus literal `ci_jobs_added = false` and `pcd_is_enforcement = false`. These record this kit's boundary, not a ban on pre-existing consumer CI. Optional `mypy_command` must be nonblank if present; it is not schema-required by selecting `mypy`. The optional completion budget has its [own contract](#project-owned-outer-completion-budget).

The table adds each selection's minimum facts to that common contract. Native execution also needs the named tools, real paths and wiring; individual check boundaries validate their own subsets, not necessarily the whole routing schema.

| Selection | Additional facts and explicit use |
| --- | --- |
| `guard` | `fact.python_version` and matching `python.python_version`; `[python]` integer `schema_version = 1`, `imports` and `executables` arrays (may be empty). Bind `-p gajaestack.pytest_guard`; actual Python `major.minor` must match. See [pytest binding](#explicit-native-pytest-binding) for no-bytecode/cache/temp prerequisites. |
| `ruff` | Nonblank `fact.python_version`, `ruff_command`, `ruff_format_command`; `[python]` integer `schema_version = 1`, matching `python_version`, nonempty `ruff_paths` and `ruff_config`. `gajaestack-python-check --full` uses that scope; [source quick mode differs](#python-quick-feedback-versus-completion). Declaring a format command does not make formatting required. |
| `required-ruff` | Also select `guard` and `ruff`, include `ruff-check` in `required`, set `fact.required_ruff_before_pytest = "active"` and load `-p gajaestack.pytest_required_ruff` alongside the guard. No pending/inactive value is supported; omit the field when deselected. |
| `hypothesis` | Nonblank `fact.python_version`; no extra command field or `[python]` table is required by this selection alone. Explicitly run selected property tests with their application imports, pytest and Hypothesis already provisioned; the bundled percent-decoder example is RERG-specific. Selection alone runs nothing. |
| `mypy` | Nonblank `fact.python_version`; optional nonblank `fact.mypy_command` records the reviewed advisory invocation. Use consumer-owned config, runtime and paths; no plugin binds it automatically. See [advisory configuration](#advisory-python-configuration). |
| `routing` | No additional facts beyond the common contract. Explicitly append packaged routing guidance through the [host recipe](../README.md#routing-guidance); selection does not load it. The optional Python routing console validates facts, not check execution. |
| `typescript` | `[typescript]` integer `schema_version = 1`, boolean `typecheck` and `lint`; enabled typecheck needs nonblank `tsconfig`, enabled lint needs nonblank `biome_config` and nonempty `paths`. Run `bun run gajaestack-check`; no Python runtime fact is required by this selection. |
| `typescript-guard` | Also select `typescript`, enable at least one check, and make `ts-typecheck`/`ts-lint` membership in `required` match their respective booleans. Explicitly bind `gajaestack/preload` in Bun test configuration. |
| `typescript-config` | No additional facts beyond the common contract. Explicitly select `"extends": "gajaestack/tsconfig"` in consumer tsconfig if appropriate; this optional baseline neither selects nor runs typechecking. |
| `scb-check` | Also include `scb-check` in `advisory`; nonblank `fact.scb_check_command` and numeric `fact.python_version` >= 3.12, including TypeScript consumers. Explicit invocation only; see the [independent advisory contract](#optional-advisory-scb-check). |

`ruff_config` names a **consumer-owned** config file; the package never copies configuration into your repository. Packaged example assets are read in place:

```sh
python -B -c 'from importlib.resources import files; print(files("gajaestack").joinpath("ruff.toml"))'
```

The property-test example and `routing/AGENTS.md` resolve the same way; use shared resources in place, not copied source. Packaged `mypy.ini` is **RERG-specific**: Python 3.12 and `rerg/raw_derivation.py,rerg/path_query.py`, not a generic baseline. Other consumers use reviewed consumer-owned mypy configuration, paths and runtime; see [advisory configuration](#advisory-python-configuration). A mixed Python/TypeScript consumer keeps one reviewed facts file. The Bun package carries its static resources under `node_modules/gajaestack/`; GJC skill and routing loading remain explicit [host selections](../README.md#skills-gjc).

## Optional advisory: scb-check

[scb-check](https://github.com/gabeorlanski/scb-check) `0.2.0`, pinned source commit [`a8618228939def726c2ec48b354693e5aa1999d5`](https://github.com/gabeorlanski/scb-check/commit/a8618228939def726c2ec48b354693e5aa1999d5), supplements lint with clone, structural, and complexity review. Findings are heuristic and need judgment; prune the selection when its noise and cost outweigh its value. Nothing activates by default: this kit ships no scb-check dependency, extra, copied rule, wrapper, CI job, autorewrite, or metric target. The recipe is based on pinned upstream documentation and source review; **native CLI and agent-judgment acceptance remain unverified**.

**Dependency (separately approved).** Pin `scb-check==0.2.0` independently of Gajaestack. Review a local artifact built from the pinned source and its SHA-256; use a reviewed lock containing local artifact URLs and hashes for scb-check **and every prerequisite**, or separately verify those prerequisites are already installed. Upstream's exported `requirements.lock` is a dependency-review input, not the scb-check artifact pin. No digest is supplied here. With the approved Python 3.12+ environment active, install offline:

```sh
python -m pip install --no-index --no-deps --no-compile --require-hashes \
  -r /path/to/reviewed-local-scb-lock.txt
python -m pip check
```

The lock must name existing local artifacts; `--no-deps` deliberately does not resolve or provision omitted dependencies. Missing artifacts or prerequisites are blockers, not permission to download. Upstream declares its own dependencies, including `ast-grep-cli==0.42.1`; Gajaestack's packages remain dependency-free, and unselected TypeScript needs no Python. Upgrade the source/version and artifact hashes together through review; deselection removes both facts selections and the command, without changing unrelated dependencies or completion checks.

**Selection contract (facts-owned and independent).** `scb-check` is selected **iff** the top-level `advisory` list includes `scb-check` and `fact.selected_components` includes it — never `required`, never `on_demand`, and both lists must agree in either direction. Selecting requires a nonblank `fact.scb_check_command` naming the exact command (e.g. `scb-check check src`) and a `fact.python_version` naming a numeric runtime of at least `3.12` (`"3.12"`, `"3.13.1"`) — **even in a TypeScript-only consumer**, where selecting the review is what makes Python a prerequisite; unselected TypeScript still needs no Python. Unselected facts must omit `scb_check_command`: a stale command is rejected. Facts validation reads these values as schema data and never executes the command; `[fact].test_command`, quick, and completion behavior stay unchanged in both states.

**Exact command and native settings.** Run exactly what the consumer's `.gajaestack/routing.toml` declares in `fact.scb_check_command` — read it from the facts at the working directory, not a remembered spelling. Upstream rule settings (`exclude`, `context`, `low-use-short-function` budgets) live only in consumer-owned `scb-check.toml` or `[tool.scb-check]` in `pyproject.toml` (upstream also folds `[tool.ruff].exclude`, `[tool.ruff].extend-exclude`, and `[tool.ty.src].exclude` into its excludes when a `pyproject.toml` is picked up, walking upward from the current directory to the `.git` root) — never in Gajaestack facts or packaged resources, which copy no upstream configuration.

**Status semantics (upstream-documented and source-reviewed; not trial-run here).**

- Default human output prints detailed findings; a clean run legitimately prints no findings, so empty human stdout is neither required nor an error.
- `--output-format json` (or `--report`) produces aggregate metrics only — verbosity/erosion scores and counts — not finding records; review the human output for the findings themselves.
- `0` means clean **only over a nonempty intended scan scope**; an empty or wrong scope is no coverage.
- `1` means findings are reported (clones, ast-grep hits, structural findings, or high-complexity functions): neither clean nor an infrastructure failure — but never assume `1` alone means usable findings without reviewing the output.
- `2` is documented usage/path/configuration/directive errors (bad path, missing config, invalid `scbc` directives).
- A missing or non-executable `scb-check`, a failed process, a missing or invalid report when JSON output was requested, or any other unexpected status is an **incomplete run, never a silent pass**; upstream may surface further infrastructure failures, which classify as incomplete — not as findings, not as clean.
- **Retain and read stderr.** Upstream's ast-grep stage returns no findings when every `sg` attempt fails and drops malformed hit lines with warnings, while its logging defaults to WARNING on stderr — so scb-check can exit `0` (or `1`) with incomplete ast-grep coverage. Treat missing/failed `sg` or malformed-output warnings as **incomplete coverage even on status `0`/`1`**, never as proven clean; exit status alone proves nothing. This advisory review is human-owned and does not fail closed on its own coverage gaps.
- **`sg` resolution is not hermetic.** Upstream prefers global `sg`, then tries `sg` / `ast-grep` beside its Python interpreter when the global command is missing or fails. A PATH `sg` can instead be util-linux's unrelated command. Inspect resolved executables, versions, and the environment: pinning scb-check does not pin the executable that actually runs. This fallback is upstream behavior, not a Gajaestack wrapper.

**Scope, languages, and review judgment.** There is no diff/changed-files mode: scan a broad enough project scope that clone partners and call-site context are present (directory discovery respects `.gitignore`; `--include-all` extends discovery to gitignored supported files), then review only the findings pertinent to the changed code. Ast-grep slop rules, structural rules, and `scbc` source directives are **Python-only** (invalid directives fail with exit `2`; clone and erosion findings are not suppressible). `.ts` participates in non-Python clone and complexity metrics only — no JSX/TSX support is claimed. Upstream walks Python, Rust, JavaScript, TypeScript, Zig, Haskell, and C++ sources; Gajaestack recommends this review only for its Python and TypeScript surfaces. When a finding is a false positive, retain the justified abstraction or boundary and state the reason — there is no refactor obligation.

The packaged facts example and complete examples below stay unselected. To select, both lists must gain `"scb-check"` and `[fact]` must declare the command:

```toml
# [fact] — scb-check recipe, deliberately unselected in these examples:
#   selected_components = [..., "scb-check"]   # and top-level advisory must
#     include "scb-check" too (never required/on_demand; both must agree)
#   scb_check_command = "scb-check check src"  # exact command; nonblank when
#     selected, rejected as stale when unselected
#   python_version = "3.12"                    # numeric runtime >= 3.12,
#     required even in a TypeScript-only consumer
# Upstream rule settings stay in scb-check.toml or [tool.scb-check], never here.
```

## Project-owned outer completion budget

Optionally set `completion_timeout_seconds` directly in `[fact]`, alongside the existing `test_command`, in consumer-owned `.gajaestack/routing.toml`. It budgets that one completion command's entire declared scope, including startup and bound checks, not the quick command or individual tests. The value must be a positive finite integer number of seconds from **1 through 9007199254740991** (the exact integer range shared by Python and JavaScript); use TOML integer notation. A specified budget also requires a nonblank `test_command`. Boolean, zero, negative, string, fractional, nonfinite and out-of-range values, and placement anywhere other than directly under `[fact]`, are rejected at the facts-validation boundaries. Omission means **unconfigured**, never an implicit 300s or 600s policy.

Numeric parsing boundary: facts validation requires a TOML integer. Bun exposes TOML integers and floats as JavaScript numbers, so its native check validates the parsed safe-integer value; integral float syntax such as `1.0` is indistinguishable from `1` there. Use integer notation for consistent validation across both runtimes.

For example, a project could provisionally choose `completion_timeout_seconds = 600` after observing a 339.36s full-suite run. That is a project-specific headroom decision, not a measured universal policy or a template default; review it when the declared command/scope changes. Existing facts are preserved: consumers supply values, not recipe forks.

The facts file carries the configured seconds or its explicit unconfigured state alongside the completion command. The **calling launcher must honour the outer budget**, preserve logs, and report an outer timeout as **incomplete verification**, distinct from a native test/check failure. When unconfigured, report that fact and the launcher's actual limit rather than claiming unlimited execution. Re-read the facts after changing them; guidance rendered earlier is only a snapshot.

This kit validates the fact at its native check boundaries; it does not launch the completion command, change agent bash-tool/CI limits, or guarantee that an external launcher accepts every schema-valid value. The launcher must read current facts and explicitly set a supported execution limit; unsupported limits require an explicit report, not silent clamping or retries. External launcher integration and consumer/CI adoption remain separately scoped work. There is no second runner, command registry, adaptive ratchet, cache or concurrency policy.

An outer command budget is separate from Bun's per-test `--timeout` in milliseconds, pytest's native faulthandler settings or a timeout plugin's test deadlines, and native-check subprocess timing/`--timing` diagnostics. None of those defaults or native exit statuses changes. Invalid specified budgets fail at facts validation and, on configured native guard paths, before protected test imports. Quick checks that do not otherwise load facts do not gain a new facts dependency.

## Python: quick feedback versus completion

Provision Python >=3.11 and (only when selected) Ruff through the consumer's existing environment. A Ruff-only selection needs no pytest: pytest is a prerequisite only when the selection activates the pytest integration (`guard`/`required-ruff`) or a run executes consumer pytest tests. The packaged Ruff example targets Python 3.12 E4/E7/E9/F correctness, not style. Choose consumer-specific paths explicitly in facts:

```sh
gajaestack-python-check --full   # completion: full declared scope, independent of working-tree state
gajaestack-python-check          # quick (no flag)
```

Full mode reads `[python].ruff_paths` and `[python].ruff_config` from facts; `--path` cannot narrow it, while an explicit `--config` overrides the configuration. It refuses empty/missing/escaping targets and preserves native Ruff failures. **Without a contributor selector, installed quick conservatively runs the full declared lint scope**: ignored dependency code has no tracked baseline. Budget full lint cost for that unchanged default; quick still needs Git and never replaces `--full`. For the suggested contributor iteration command, see [contributor lint scope](#contributor-lint-scope).

**Ordinary Python source quick mode is different:** it checks all existing staged, unstaged and untracked non-ignored changed `.py` files in the Git worktree, narrowed only by optional repeated `--path` arguments — not by facts `ruff_paths`. It uses the helper's adjacent `python/ruff.toml` unless `--config` is supplied; it does not ordinarily read facts. For source use with consumer policy, explicitly pass `--config /absolute/consumer/ruff.toml` and any intended repository-relative `--path` filters. Do not assume source quick inherits the full-mode config/scope.

Changes to the selected quick config, helper (when inside the repository), facts file or explicit `--impact` paths expand source quick to the full facts-declared scope; `--path` does not constrain that expansion. An empty ordinary quick selection exits `0` with **no coverage**, not a lint pass; invalid/empty expanded scope fails. Paths outside the actual selected scope remain unchecked. Neither mode formats, typechecks or infers affected tests. TypeScript's source changed-file intersection is a separate contract below.

Quick mode retains its Git prerequisite; `--full` and the pytest binding do not require Git.

The setuptools console entrypoint does not add `-B`: when bytecode writes into a consumer-local `.venv` must be avoided, run `PYTHONDONTWRITEBYTECODE=1 gajaestack-python-check ...` (or `python -B -m gajaestack.check_changed_python ...`). The pytest guard binding already requires `-B` or the environment equivalent, the documented install uses `--no-compile`, and no bare console startup is claimed never to write bytecode. The check itself runs Ruff with `--no-cache`.

The shared Ruff boundary forces `--no-cache --no-fix --no-fix-only` and ignores `RUFF_OUTPUT_FILE`, preserving lint policy without allowing check-time edits or report-file writes. Quick discovery disables Git's optional index writes. Installed quick checks resolve the declared scope from consumer cwd even inside an enclosing Git worktree.

`gajaestack-imports <importname>...` reports import discoverability only: it does not install packages, establish version compatibility, prove successful module initialization, or replace the selected check. Name only imports required by that check; build backends and parser plugins are independent prerequisites.

When the explicit native pytest binding below is active, the configured native test launch (`python -B -m pytest`) is the completion command: the bound full Ruff check runs before collection, so chaining `gajaestack-python-check --full` first repeats completed lint work. Use `--full` as the completion check when no native test binding is adopted.

### Contributor lint scope

**Source versus release:** these selectors describe current checkout code, including uncommitted work; existing retained `0.1.0` artifacts are not claimed to contain it. Before consumer use, review and commit that implementation and use the [maintainer build recipe](#maintainer-build-once-and-retain) with an appropriately versioned reviewed commit. Do not overwrite retained releases or mistake an archive of HEAD for a build of dirty changes.

The default **suggestion for contributor iteration**, not a changed command default, is an explicit contribution target:

```sh
gajaestack-python-check --reference-branch TARGET
bun run gajaestack-check --quick --reference-branch TARGET
# Deliberate alternative: use a specific baseline instead of a merge base.
gajaestack-python-check --baseline-commit COMMIT
bun run gajaestack-check --quick --baseline-commit COMMIT
```

Replace `TARGET` with the branch being contributed against. A configured tracking branch is not necessarily that target; neither checker guesses one, assumes `origin/main`, fetches, or tracks the last push. The selectors are mutually exclusive. `--reference-branch` resolves the reference to a commit and requires exactly one merge base with HEAD; `--baseline-commit` resolves the supplied commit directly. Unknown or ambiguous references, absent or multiple merge bases, shallow history and non-Git working directories fail explicitly instead of falling back to whole-tree lint.

Selection is rooted at the consumer working directory and its declared lint paths/configuration, including when shared code is installed in ignored `site-packages` or `node_modules`. Git's NUL-delimited paths identify current net differences from the baseline plus non-ignored untracked files. Existing supported files are deduplicated and intersected with declared scope; deleted files are not linted, rename destinations are candidates and origins still participate in policy invalidation. Spaces and Unicode are supported. This checks whole current files, not historical contents or only changed lines. Native linter ignore/configuration rules remain authoritative.

The checker reports the resolved reference/hash/baseline, actual lint selection, and any conservative policy-expansion reason. Configuration, facts and other tracked policy inputs can expand to full declared scope under the existing invalidation rules. Unlike legacy installed quick mode, merely living in an ignored dependency directory does not force this explicit contributor selection to full scope; it does not prove ignored installed package bytes unchanged. An empty selection is **no coverage**, never clean proof.

Python selectors are lint-only and cannot accompany `--full`; full Python checks and selected type checks remain full. TypeScript selectors narrow only lint: without `--quick`, selected typechecking still covers the full tsconfig. Existing no-argument behavior, native test bindings and full completion commands are unchanged. Run the full completion boundary before claiming completion.

### Contributor lint results

- A nonempty lint run preserves the native linter's status and diagnostics. Errors fail; warnings follow native configuration and are not universally promoted to failures by this kit. Review them even on exit `0`; a successful lint invocation proves neither type safety nor behavioral correctness.
- Missing selected tools, malformed facts/configuration, unusable references/history and subprocess failures are failures, not silent skips. A no-op may return before invoking a linter, so it does not prove that tool is available.
- An empty quick/contributor intersection exits `0` with an explicit **no coverage** message, not a lint pass. Python contributor mode also reports no coverage when native Ruff exclusions select nothing. Biome unmatched-file failures are not hidden.
- Invalid or empty full declared scope fails. Conservative policy expansion is a scope diagnostic, not itself a failure; read the resulting file selection and native result.
- Quick lint never formats, typechecks or runs behavioral tests. Full TypeScript checking runs typechecking only when selected; full Python checking is Ruff lint. Existing CI and the consumer's declared completion command retain their independent responsibilities.

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

The guard requires no-bytecode execution (`python -B` in `test_command`) and a disabled pytest cacheprovider (`-p no:cacheprovider`); review that explicit cache-plugin change as part of native wiring, especially if existing tests depend on it. Other existing plugins/options remain intact. Merely installing the distribution binds nothing; no entry-point autoload loads these plugins. The following complete facts example selects **guard plus required Ruff**, not guard-only; apply the [guard-only delta](#guard-only-delta) when that is the intended selection. Template examples are starting points, not truth:

The guard also requires pytest temporary storage outside the consumer repository. Without `--basetemp`, it checks the resolved Python temporary directory (`tempfile.gettempdir()`, influenced by `TMPDIR`); a repository-local temporary directory is rejected. An explicit `--basetemp /absolute/owned/external/path` must be absent or an empty owned directory, outside the repository and not a symlink. Never point it at retained artifacts, evidence or other existing content: pytest may clear its base directory. Review the actual environment and include any approved `--basetemp` argument in the declared test command.

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

Optional `[python]` fields `root`, `source_root`, `prefix`, `base_prefix` declare actual identity constraints (paths resolve relative to the consumer root); `[python.module_origins]` maps names from `imports` to approved exact files or containing directories. The guard inspects filesystem package chains before importing their parents, checks all declared origins before initializing those imports, and rejects protected source modules already imported at guard time. It cannot undo earlier imports. Do not copy another repository's host paths. Declare only dependencies needed by the selected test surface; optional property/build dependencies do not belong in every focused invocation. The **required-Ruff** binding additionally requires `ruff-check` in `required`; guard-only does not.

Supported configured entry points are `python -B -m pytest`, a focused file/nodeid, and `--collect-only`. Initial prerequisite and explicitly bound full Ruff checks run before consumer conftest/test imports, not from a late fixture. Missing prerequisites or lint failures reject collection; subsequent native test failures remain failures. Approved imports can themselves have effects; the guard is not a sandbox.

`tests/test_python_package.py` reproduces standalone installed-package acceptance, including native pass/rejection and package upgrade/removal checks, when its approved offline prerequisites are available. Its pytest invocations use **pytest 9.1.1** without activating the kit's prerequisite-guard or required-Ruff plugins; package inventory assertions do not prove those bindings. Installed pytest binding activation, pre-collection rejection and recovery still require separate acceptance evidence. This does not establish support for every pytest release or real-consumer adoption.

Trusted startup includes Python site initialization, pytest itself and earlier plugins. Disabling/replacing configuration (`-c`, `-o addopts=`, `-p no:...`), injected/preloaded code, `pytest.main`, IDE adapters and different working directories are not an immutable admission boundary. Do not claim all plugin effects are prevented or unchecked merging impossible. Direct console-script startup and other pytest versions need separate evidence. No-bytecode launch and disabled cache prevent those checkout writes; arbitrary consumer tests/builds can still write. Use native external disposable temp/build directories and reviewed no-write assertions for any broader claim.

### Guard-only delta

Starting from the combined example above, make all these reviewed changes together:

- Native pytest configuration keeps `-p gajaestack.pytest_guard` and `-p no:cacheprovider`, but removes `-p gajaestack.pytest_required_ruff`. Preserve unrelated options/plugins and the `python -B -m pytest` launch.
- Remove `required-ruff` from `fact.selected_components` and **delete** `fact.required_ruff_before_pytest`; neither a stale `"active"` declaration nor an invented `"inactive"` value is valid.
- For only the prerequisite guard, set `selected_components = ["guard"]`, retain `required = ["pytest"]`, and remove the example's `ruff-check`/`ruff-format` labels, `ruff_command`, `ruff_format_command`, `python.ruff_paths` and `python.ruff_config`. Keep `ruff` and these fields/labels only if Ruff is independently selected; without its binding, its completion check must be run explicitly.
- Retain the common facts contract, both matching Python version fields, `[python].schema_version = 1`, `imports` and `executables` (empty arrays are valid), and any actual guard identity constraints. Preserve applicable conditional policies and unrelated advisory/on-demand selections; the example's `mypy` label is not a guard prerequisite.

Validate the revised facts and run the native command over valid scope plus a seeded missing prerequisite; restoring it must recover. Removing only the Ruff plugin while leaving its active facts fails closed.

### Advisory Python configuration

Formatting and mypy remain advisory. Generic consumers use their own reviewed Ruff/mypy configuration, selected paths and Python runtime. For example, with those consumer files already present:

```sh
ruff format --check --config ruff.toml <selected-paths>
mypy --config-file mypy.ini
```

Here `mypy.ini` means the **consumer's** file, declaring its intended paths/runtime, not the packaged resource. Packaged `gajaestack/mypy.ini` instead targets Python 3.12 and exactly `rerg/raw_derivation.py,rerg/path_query.py`; use that resource in place only for a separately approved matching RERG scenario, never as generic onboarding. Do not run RERG's illustrative bare commands in its actual checkout: its existing documented environment/canary contract remains authoritative until separately approved native adoption replaces it.

## TypeScript: Bun hosts real typechecking and lint

Use the consumer's existing local `node_modules/.bin/tsc` and `node_modules/.bin/biome`. Bun invokes their actual JS launchers, so Node is not silently required. No `bunx` fallback or downloads occur. Existing native tsconfig/Biome configs remain authoritative; the packaged baseline is optional (`"extends": "gajaestack/tsconfig"` in the consumer tsconfig) and is never applied automatically. The `[typescript]` paths below resolve against the consumer's working directory.

### Minimal TypeScript lint selection

For the README quick start, save this complete, schema-valid example as `.gajaestack/routing.toml` in the consumer root. It selects only standalone lint, not a preload, typechecking, tests or skills. Replace paths with existing consumer paths and `TARGET` in the recorded feedback command with the actual contribution target. These are declarations, not a command launcher; preserve unrelated facts when merging into an existing file.

```toml
required = ["ts-lint"]
advisory = []
on_demand = []

[conditional]
input_parsing = "Changed parsing of externally supplied values: exercise valid, malformed, and boundary inputs."
authorization_decisions = "Changed a decision about permission, eligibility, or authority: test allow and deny boundaries."
file_writes_deletion = "Changed filesystem mutation behavior: test target confinement, refusal cases, and no partial side effects."
external_commands = "Changed subprocess or executable invocation: test arguments, failures, and prohibited execution paths."

[fact]
schema_version = 1
selected_components = ["typescript"]
test_command = "bun run gajaestack-check"
affected_test_command = "bun run gajaestack-check --quick --reference-branch TARGET"
ci_jobs_added = false
pcd_is_enforcement = false

[typescript]
schema_version = 1
typecheck = false
lint = true
biome_config = "biome.json"
paths = ["src"]
```

Here the schema's `test_command` names completion of the selected lint boundary, not behavioral test execution. Preserve the consumer's existing broader completion command when applicable. Track facts, manifest/lock and consumer configuration in Git; ignore installed dependency directories. The native checker does not write these files. Bun >= 1.4.2 and an existing local Biome installation/configuration are required; no Python, `tsc`, test preload or optional packaged tsconfig baseline is needed for this selection.

For separately approved typechecking, set `typecheck = true`, add `tsconfig = "tsconfig.json"` pointing to the existing consumer config and add `ts-typecheck` to `required`; local `node_modules/.bin/tsc` must already exist. For a test preload, additionally select `typescript-guard`, declare `test_command = "bun test"` and include `ts-test` in `required`, then merge the native binding below. Required preload checks must appear in `required` as `ts-typecheck` and/or `ts-lint`, matching the enabled booleans. Neither selection installs tools or edits native configuration.

### TypeScript modes and optional test binding

Quick and completion commands:

```sh
bun run gajaestack-check --quick  # quick: changed-file lint intersection from a source checkout,
                                  # full declared lint scope from an installed package; never typechecks
bun run gajaestack-check          # completion: selected tsc --noEmit, then lint
bun run gajaestack-check --timing # phase timing on stderr; also GAJAESTACK_TIMING=1
bun test                          # configured native test boundary
```

For a bound consumer, `bun test` is the completion command: do not chain the standalone check first, which would repeat type/lint checks in the preload. Use the standalone completion check when no native test binding is adopted.

Without a contributor selector, source quick mode intersects existing staged, unstaged, and untracked files with declared lint paths, and never typechecks. Changes to facts, Biome configuration, or the checker expand a quick run to full declared lint scope. **Without a contributor selector, installed quick conservatively covers the full declared lint scope**: ignored shared code cannot be proven unchanged without a stored baseline. Budget a full lint pass for that unchanged default; use the explicit [contributor lint scope](#contributor-lint-scope) for suggested iteration feedback. An empty intersection is **no coverage**, not a lint pass. The checker accepts `--timing` / `GAJAESTACK_TIMING=1`: phase elapsed time, counts, and exit status on stderr, informational only (the preload passes no arguments, so use the environment form under the native binding).

Quick and contributor discovery require Git and fail visibly if changes cannot be read, including filenames that cannot be decoded as UTF-8; completion without a contributor selector does not require Git. Rename origins participate in policy invalidation, while deleted files are not lint targets. Nested `biome.json`/`biome.jsonc` changes and tracked local `extends`/plugin dependencies invalidate the selection. Config dependencies that cannot be enumerated conservatively (including commented JSONC or package references) expand any changed working tree to full declared lint scope rather than guessing native config semantics.

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

Build tests follow the [external snapshot and prerequisite boundaries](#maintainer-build-once-and-retain) above; propagate no-bytecode settings to children and compare original source/dependency trees when claiming they were untouched. Consumer fixture repair or actual consumer integration remains separately approved.

Report actual commands, scope, native exit status, test counts, deliberate rejection cases, skips/not-run reasons and permitted evidence location. A test that correctly asserts rejection passes; a failed guard is a rejection, not a successful check. Empty selections and missing tools are not coverage. Preserve owned evidence; clean only task-owned disposable state.

The six capabilities remain distinct: native quality gains bounded native guards; type discipline gains selected compiler rejection rather than a new type framework; verify-change reuses native schema/CLI/build oracles. Cleanup-learning removes repeated manual startup/scoping rituals only after their replacements are proven. Focused review and hotspot investigation remain selective/on-demand guidance (profiling or property tests for a concrete question); no automatic review panel, mutation dependency or universal runner is added. Formatting/mypy are not promoted to required. All-six delivery, RERG/Gajaeway adoption, broader host/version support, CI/merge enforcement, new runners and immutable non-skippability are **not claimed**.
