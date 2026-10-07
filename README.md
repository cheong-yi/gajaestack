# gajaestack

A modular repo-quality kit: practical agent guidance, reusable checks, and repeatable verification.

Start with [AGENTS.md](AGENTS.md), the agent entry point. The canonical design is [issue #1](https://github.com/cheong-yi/gajaestack/issues/1); the [scope invariant](docs/scope-invariant.md) summarizes its intended product scope without claiming every capability is delivered.

## Install: pinned local artifacts

No registry publication is assumed and no command downloads anything: build each artifact from a gajaestack source checkout, then install that exact pinned file. Both packages are version `0.1.0`. Python-only consumption needs no Bun; TypeScript-only consumption needs no Python.

```sh
# Python: build the wheel (setuptools >= 77 must already be installed; the
# flags below keep the build offline), then install the pinned wheel.
python -m pip wheel --no-index --no-deps --no-build-isolation \
  --wheel-dir /tmp/artifacts /path/to/gajaestack
python -m pip install --no-index --no-deps --no-compile \
  /tmp/artifacts/gajaestack-0.1.0-*.whl

# Upgrade/reinstall (example: 0.1.0 → 0.1.1): rebuild into a new directory —
# never reuse the old artifact path — then force-reinstall that exact wheel.
python -m pip wheel --no-index --no-deps --no-build-isolation \
  --wheel-dir /tmp/artifacts-0.1.1 /path/to/reviewed-0.1.1-source
python -m pip install --no-index --no-deps --no-compile --force-reinstall \
  /tmp/artifacts-0.1.1/gajaestack-0.1.1-*.whl

# TypeScript: pack the tarball from the source checkout, then add it as an
# exact dev dependency with scripts disabled.
bun pm pack --ignore-scripts --destination /tmp/artifacts
bun add --dev --exact --offline gajaestack@/tmp/artifacts/gajaestack-0.1.0.tgz --ignore-scripts --backend=copyfile
```

Pin the wheel by SHA-256 in a reviewed requirements file using pip `--require-hashes`; the [guide](docs/python-trial.md) shows the native commands. Commit `package.json` and `bun.lock` through normal review; reproduce offline with `bun install --frozen-lockfile --offline --ignore-scripts --backend=copyfile`. Upgrade on either runtime with a **distinct** artifact path per version: pack reviewed new-version source and use `bun add --dev --exact --offline --ignore-scripts --backend=copyfile gajaestack@/absolute/new-artifact.tgz`, or install its new wheel. Keep the explicit package name when changing the tarball pin. Rebuilding unchanged `0.1.0` source does not create `0.1.1`. The packages install no dependencies and run no install scripts or hooks: the Bun checks invoke the consumer's own local `tsc`/`Biome` (installed only when separately authorized), and the Python distribution registers no pytest11 autoload — its plugins load only from your explicit `-p` selections.

Deselect components by reviewing their facts and native bindings, preserving unrelated selections. Before removing the whole dependency, remove its explicit preload/plugins, optional config extension and host-directory entry; then use `bun remove --offline --ignore-scripts gajaestack` or `python -m pip uninstall gajaestack`. Native managers do not rewrite consumer policy: removing a still-bound dependency fails closed rather than silently dropping the guard.

## Check and test

```sh
bun run gajaestack-check             # completion: tsc --noEmit over the full tsconfig selection, then lint
bun run gajaestack-check --quick     # quick: lint only, never typechecks
bun run gajaestack-check --timing    # phase timing on stderr; also GAJAESTACK_TIMING=1
bun -e 'import {check} from "gajaestack/check"; process.exit(await check())'   # installed-export check
gajaestack-python-check --full       # Python completion: full declared scope
gajaestack-python-check              # Python quick (no flag)
gajaestack-imports setuptools        # import discoverability only: no install, no version-compatibility or init proof
```

The setuptools console entrypoint does not add `-B`: when bytecode writes into a consumer-local `.venv` must be avoided, run `PYTHONDONTWRITEBYTECODE=1 gajaestack-python-check ...` (or `python -B -m gajaestack.check_changed_python ...`). The pytest guard binding already requires `-B` or the environment equivalent, installs are documented with `--no-compile`, and no bare console startup is claimed never to write bytecode. The Python check itself runs Ruff with `--no-cache`.

Quick is conservative when installed: from an installed package, quick covers the **full declared lint scope on every invocation** — installed shared code is ignored by the consumer's Git (including local edits and dependency upgrades) and no persistent baseline/cache exists to prove it unchanged — so budget a full lint pass per quick run. From a source checkout quick stays a changed-file lint intersection (staged, unstaged, untracked), expanding to the full declared scope when facts, Biome configuration, or the checker itself change; an empty intersection is **no coverage**, not a pass. Quick never typechecks in either mode.

Installing the package activates nothing. Bind the guards yourself as a reviewed configuration change:

```toml
# bunfig.toml — preserve your existing preloads and their order.
[test]
preload = ["./existing-preload.ts", "gajaestack/preload"]
```

```ini
# pytest.ini — explicit selection; nothing autoloads.
[pytest]
addopts = -q --strict-markers -p gajaestack.pytest_guard -p gajaestack.pytest_required_ruff -p no:cacheprovider
```

A guard-only consumer selects just `-p gajaestack.pytest_guard`. Facts: write and review your own `.gajaestack/routing.toml` — no command creates or rewrites it — and treat the complete examples in the [guide](docs/python-trial.md) as starting points, not truth. Facts remain the single runtime authority (e.g. `selected_components = ["typescript", "typescript-guard"]` or `["guard", "ruff", "required-ruff"]`). Optional `[fact].completion_timeout_seconds` declares a project-owned outer budget for `test_command`, honoured by your launcher and not imposed by this kit — see the [budget contract](docs/python-trial.md#project-owned-outer-completion-budget). Demonstration is a valid pass plus a deliberately seeded rejection; native test failures, missing tools and empty selections stay failures.

## Skills (GJC)

Skill guidance helps agents reason; it does not enforce behavior by itself. The skills ship inside both packages. Adding the package root alone exposes **all three skills' metadata**, even when only one body is invoked: that is not selective context loading. For GJC 0.18.7, the following native name-filter recipe selects `native-quality` for discovery without a global allowlist:

```yaml
# .gjc/config.yml — merge into the existing config: preserve current
# customDirectories entries and ignoredSkills entries. Preserve any existing
# includeSkills policy, ensuring it admits native-quality.
# Do not replace a consumer's lists with this example.
configSchemaVersion: 2
skills:
  customDirectories:
    - node_modules/gajaestack/skills
  ignoredSkills:
    - type-discipline
    - verify-change
```

```sh
# Python consumer — configure the installed guidance root instead; resolve it
# with the interpreter that has gajaestack installed (a Python version change
# may require rebinding this path; an ordinary package upgrade keeps it):
.venv/bin/python -B -c 'import gajaestack_guidance; print(next(iter(gajaestack_guidance.__path__)))'
# List that printed path under skills.customDirectories above.

gjc skills discover --source all --json   # unfiltered; page with --offset if truncated
# In an approved consumer-scoped session, invoke /skill:native-quality.
```

The configured entry must be the **parent root** containing the skill directories, not a direct skill leaf. Use Bun's native `--backend=copyfile` on install, upgrade and replay when selecting GJC guidance: GJC 0.18.7 rejects multiply linked skill files, including Bun's default cache hardlinks, with “Skill path is not a regular file.” This is native dependency installation, not manually re-copying shared source. No guidance symlink is needed; an existing `.gjc/skills` directory stays untouched. Filters match names globally, not package paths: inspect collisions before adding exclusions, and do not hide an unrelated consumer skill with the same name. Keep unrelated skills and existing filters intact; a conflicting policy needs a consumer-owned decision.

Acceptance requires both unfiltered discovery (only selected kit metadata, unrelated skills preserved) **and actual session prompt-context evidence**, followed by loading the selected installed body. A queried catalog or a successful body invocation alone does not prove absence of unselected context. Selective prompt-context loading is not yet verified by this recipe; do not treat discovery filtering as completed host acceptance. Other hosts and unlisted loading paths remain unclaimed.

## Routing guidance

The static packaged resource `python/routing/AGENTS.md` (present in both runtimes) is included explicitly — never automatically — by appending it to the existing system prompt from the consumer's working directory:

```sh
# TypeScript — no Python needed:
gjc --append-system-prompt "$PWD/node_modules/gajaestack/python/routing/AGENTS.md" \
  --print 'quote the optional completion timeout sentence'
# Python:
gjc --append-system-prompt "$(python -B -c 'from importlib.resources import files; print(files("gajaestack").joinpath("routing/AGENTS.md"))')" \
  --print 'quote the optional completion timeout sentence'
```

`--append-system-prompt` appends the file and preserves the existing prompt; nothing is templated or written into the repository, and consumer facts are read at the cwd. The optional read-only `gajaestack-routing` console belongs to the **Python distribution only**; TypeScript checks validate their facts natively and need no Python console. It prints labeled guidance/facts-example paths; `gajaestack-routing --guidance` prints the raw guidance resource path for safe shell substitution, and `gajaestack-routing --root .` validates consumer facts at the given root — exit `0` valid, `1` invalid, `2` absent/unconfigured or bad root.

## Local repository checks

Run from a gajaestack checkout — these source-only commands validate the kit itself (bundled-skill metadata, routing-policy structure, local Markdown links) with the Python 3.11+ standard-library `tomllib` module, and do not validate consumer applications or imply CI execution:

```sh
python3 scripts/check_repo.py
python3 -m unittest discover -s tests
seiso check --no-cache  # optional advisory stable rules; no hooks or CI
```

The source helper `python3 -B -m python.check_python_imports` (source file `python/check_python_imports.py`) checks import discoverability inside a checkout; installed consumers use `gajaestack-imports` instead. It does not install packages, establish version compatibility, prove successful module initialization, or replace running the selected check. Name only imports required by that check; build backends and parser plugins are independent prerequisites.

Consumer-owned `.gajaestack/routing.toml` remains the single facts authority; no CLI manages assets, ownership records, or an `AGENTS.md` addendum. Installing anything does not wire native configuration: guards enforce only at their documented collection/import or preload boundary, and this kit never edits or repairs native configuration. Actual RERG/Gajaeway adoption, CI/merge enforcement, runners, deployment and downloads remain separately authorized, none of these bounded mechanisms delivers all six capabilities, and missing selected tools and failed checks remain failures, not passes or silent skips.

## Reference bank

- [gdp-ts](https://github.com/rauchg/gdp-ts) — TypeScript library, lint presets and agent guidance for APIs that require evidence of an authorization check tied to the specific caller/resource. Consider for sensitive TypeScript boundaries where callers can omit or mix up checks; not a Python RERG dependency or an adopted component. Trusted check implementations still need tests, linting discourages proof forgery, and transactions or runtime constraints remain necessary where permissions can become stale.

The type-design and runtime-verification guidance draws on Lauren/Poteto's [pstack](https://github.com/cursor/plugins/tree/main/pstack), expressed in original wording. MIT is the intended project license; a license file is not yet installed or legally verified.
