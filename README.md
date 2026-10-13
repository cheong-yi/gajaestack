# gajaestack

A modular repo-quality kit: practical agent guidance, reusable checks, and repeatable verification.

Start with [AGENTS.md](AGENTS.md), the agent entry point. The canonical design is [issue #1](https://github.com/cheong-yi/gajaestack/issues/1); the [scope invariant](docs/scope-invariant.md) summarizes its intended product scope without claiming every capability is delivered.

## Install: pinned local artifacts

Use the authoritative [native artifact recipe](docs/python-trial.md#install-from-local-artifacts-no-registry) for maintainer build-once, consumer installation, upgrades and rollback. One kit version (`0.1.0` currently) covers the Python wheel and Bun tarball. Record reviewed source commit, version and SHA-256; retain the exact artifacts at durable, version-specific immutable locations and reuse them across approved consumers. Hashes identify bytes, not trusted source. There is no registry, updater, ordinary-run network check or silent tracking of latest.

Python-only consumption needs no Bun; TypeScript-only consumption needs no Python unless the independent [scb-check advisory](#optional-advisory-scb-check) is selected. Packages add no dependencies, install scripts/hooks or pytest11 autoload; selected checks use consumer-provisioned tools. pip/Bun own installation, while facts, native wiring and host configuration remain consumer-owned and separately approved.

Use the reviewed [deselection and removal lifecycle](docs/python-trial.md#deselect-or-remove): retire applicable facts/native/host bindings, remove authoritative dependency pins, uninstall natively, and verify offline replay without disturbing unrelated selections. Uninstalling does not unload guidance already in a host session.

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

Quick is conservative when installed: both runtimes cover the **full declared lint scope on every invocation**, because ignored dependency code has no tracked baseline. Source behavior differs: TypeScript intersects changes with declared lint paths; ordinary Python source quick checks changed `.py` files, narrowed only by explicit `--path`, using bundled Ruff config unless `--config` is supplied. Policy changes can expand either to full declared scope; see [Python scope and command advice](docs/python-trial.md#python-quick-feedback-versus-completion). Empty quick scope is **no coverage**, not a pass; quick never typechecks.

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

A guard-only consumer follows the [complete facts and plugin delta](docs/python-trial.md#guard-only-delta), not just plugin removal. Write and review consumer-owned `.gajaestack/routing.toml` using the [selection contracts](docs/python-trial.md#facts-selections); no command creates or rewrites it, and examples are starting points, not truth. Optional `[fact].completion_timeout_seconds` declares a project-owned outer budget for `test_command`, honoured by your launcher and not imposed by this kit — see the [budget contract](docs/python-trial.md#project-owned-outer-completion-budget). Demonstration is a valid pass plus a deliberately seeded rejection; native test failures, missing tools and empty selections stay failures.

## Optional advisory: scb-check

[scb-check](https://github.com/gabeorlanski/scb-check) `0.2.0` optionally supplements lint with advisory clone, structural, and complexity review. Select it independently in consumer facts and install its pinned upstream artifact separately; it adds no default dependency, copied rules, wrapper, mandatory gate, autorewrite, or score target. Existing completion checks stay unchanged. Selected use requires Python 3.12+ even for TypeScript; unselected TypeScript still needs no Python. The [recipe](docs/python-trial.md#optional-advisory-scb-check) specifies the source pin, exact command, native configuration, language limits, and incomplete-scan/error handling. Runtime and agent-judgment acceptance remain unverified.

## Skills (GJC)

Skill guidance helps agents reason; it does not enforce behavior by itself. The skills ship inside both packages. Adding the package root alone exposes all three skills' metadata. GJC 0.18.7 native name filters narrow discovery candidates without a global allowlist. Gajaestack acceptance uses ordinary skill selection and accepts the host limitation that diagnostics may expose excluded skill names and paths; complete model-context isolation is not an acceptance gate.

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

The configured entry must be the **parent root** containing the skill directories, not a direct skill leaf. Use Bun's native `--backend=copyfile` on install, upgrade and replay when selecting GJC guidance: GJC 0.18.7 rejects multiply linked skill files, including Bun's default cache hardlinks, with “Skill path is not a regular file.” This is native dependency installation, not manually re-copying shared source. No guidance symlink is needed; an existing `.gjc/skills` directory stays untouched. Filters match names globally, not package paths: before adding an exclusion, check discovery for an unrelated consumer skill with the same name and flag any collision for a consumer-owned decision—never hide the consumer skill to fit this recipe. Keep unrelated skills and existing filters intact.

For ordinary skill-selection acceptance, inspect unfiltered discovery: selected kit skills and unrelated skills must remain candidates, and excluded kit skills must not be candidates. Verify loading the selected installed body and repeat after a distinct pinned upgrade using the [native recipe](docs/python-trial.md#upgrade-and-rollback). Excluded names and paths in diagnostics do not block acceptance. This does not authorize loading or running excluded skills. Discovery listings, body invocations and agent assertions alone do not prove complete model-context isolation.

Observed with installed Python and Bun packages on GJC 0.18.7: filtered `candidates` retain the selected kit skill and unrelated skills, but `diagnostics` still expose excluded names and installed `SKILL.md` paths. The owner accepted this diagnostic exposure as a host limitation, not a Gajaestack acceptance blocker. Complete model-visible prompt exclusion remains **unverified**; separate GJC isolation changes and captured isolation trials are outside this scope. No kit loader workaround or copied source is introduced. Other hosts and unlisted loading paths remain unclaimed. This host-specific acceptance exception qualifies issue #1's intended zero context cost for unselected components; the canonical issue records this exception as decision 1A.

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

## License

Original Gajaestack contributions are licensed under [MIT](LICENSE), copyright Cheong Yi. The type-design and runtime-verification guidance draws on Lauren/Poteto's [pstack](https://github.com/cursor/plugins/tree/main/pstack); its full MIT notice and pinned source references are retained in [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES). Both notices ship in the Python and TypeScript distributions and must accompany redistributed material as applicable. This records the owner's license grant and known upstream notice, not a legal opinion or proof of third-party ownership.
