# gajaestack

A modular repo-quality kit: practical agent guidance, reusable checks, and repeatable verification.

Start with [AGENTS.md](AGENTS.md), the agent entry point. The canonical design is [issue #1](https://github.com/cheong-yi/gajaestack/issues/1); the [scope invariant](docs/scope-invariant.md) summarizes its intended product scope without claiming every capability is delivered.

## Discovery

List components and their managed destinations, then preview a selection before applying. Preview states each change's content, source, and destination; `--apply` replans and revalidates the selected asset changes against current bytes — the earlier preview is not an immutable transaction:

```sh
python3 /path/to/gajaestack/scripts/gajaestack.py list
python3 /path/to/gajaestack/scripts/gajaestack.py adopt ruff guard --root /path/to/consumer
python3 /path/to/gajaestack/scripts/gajaestack.py adopt ruff guard --root /path/to/consumer --apply
```

Selections never expand dependencies implicitly, and bindings require reviewed facts that already exist; facts templates are explicit and absent-only (`--facts-template python|typescript`). The [selectable native checks guide](docs/python-trial.md) is the authoritative walkthrough of the five-step journey, native wiring, removal, and bypass limits. Dependency installs and CI changes remain explicitly approved steps.

Optional `[fact].completion_timeout_seconds` declares a project-owned outer budget for `test_command`; absent means unconfigured. Preview and managed guidance expose it, but the calling launcher must honour it: this kit does not override execution-tool or CI timeouts. See the [budget contract](docs/python-trial.md#project-owned-outer-completion-budget).

Preview and the managed `AGENTS.md` addendum name the one completion command your facts already declare (`test_command`) with their declared binding and required checks — copied bytes are not activation, no runner or cache is invented, and no wiring is proven. `--timing` / `GAJAESTACK_TIMING=1` reports phase timing (elapsed, counts, exit) on stderr for the Python and TypeScript check helpers, and TypeScript `--quick` is a changed-file lint intersection that expands to the full declared lint scope on facts/Biome configuration/checker changes; no coverage means no coverage.

Preview separates copied from configured from demonstrated: a selected TypeScript binding gets a read-only `bunfig.toml` status (manual-only when unselected, not configured, configured-but-not-demonstrated, or unverified when unreadable) with manual remedies, a selected check no declared binding covers is named as the standalone check to run explicitly, and preview ends with separate instructions to explicitly review facts and native wiring — native configuration is never edited, no automatic repair happens, and no runtime proof is claimed. Re-running the same preview and `--apply` is the update procedure: unedited owned assets refresh to current kit bytes under the existing version/hash record, edited or unowned files are refused, and there is no separate updater.

## Skills

Select each skill independently; none requires another:
- `native-quality` — problem: unsuitable or overstated checks; use when selecting native checks or focused regression tests; run before choosing verification commands.
- `type-discipline` — problem: invalid states crossing boundaries; use when changing types, states, identifiers, or input validation; run during design and implementation.
- `verify-change` — problem: checks that do not observe changed behavior; use for behavior changes needing evidence; run before claiming completion.

Skill guidance helps agents reason; it does not enforce behavior by itself. The existing selective source adopter serves Python and TypeScript without overwriting consumer native configurations. Adoption requires Python 3.11+ **on the adoption host**; adopted TypeScript checks require Bun and selected local tsc/Biome tools, not Python. No dependencies are downloaded.

To inspect or selectively adopt skills through the external Skills CLI, Node.js/npm are required. The following commands follow that CLI's documented interface; execution and GJC skill loading remain unverified:

```sh
npx skills add cheong-yi/gajaestack --list
npx skills add cheong-yi/gajaestack --skill type-discipline
npx skills add cheong-yi/gajaestack --skill verify-change
npx skills add cheong-yi/gajaestack --skill native-quality
```

For a local clone, substitute its location:

```sh
npx skills add /path/to/gajaestack --skill type-discipline
```

For GJC, selectively copy a skill into the consumer repository (replace the source path). Selective copying has been checked in an isolated consumer; loading the copied skill in GJC and use through the external Skills CLI remain unverified:

```sh
mkdir -p .gjc/skills
cp -R /path/to/gajaestack/skills/type-discipline .gjc/skills/
```

## Local repository checks

Run from a gajaestack checkout. The checker validates bundled-skill metadata, routing-policy structure, and local Markdown links; it uses the Python 3.11+ standard-library `tomllib` module. Its tests cover the checker's failure cases; these local commands do not validate consumer applications or imply CI execution:

```sh
python3 scripts/check_repo.py
python3 -m unittest discover -s tests
```

The optional Python import-prerequisite helper checks whether named import modules are discoverable. It does not install packages, establish version compatibility, prove successful module initialization, or replace running the selected check. Name only imports required by that check; build backends and parser plugins are independent prerequisites:

```sh
python3 scripts/check_python_imports.py setuptools tree_sitter tree_sitter_javascript tree_sitter_typescript
```

Consumer-owned `.gajaestack/routing.toml` remains the single facts authority; `routing` manages only a short delimited soft-guidance addendum and never deletes `AGENTS.md`; version/hash ownership protects shared assets and the addendum, not arbitrary consumer content. Copying assets does not wire native configuration, guards enforce only at their documented collection/import boundary, actual RERG/Gajaeway adoption, CI/merge enforcement, runners, deployment and downloads remain separately authorized, none of these bounded mechanisms delivers all six capabilities, and missing selected tools and failed checks remain failures, not passes or silent skips.

## Reference bank

- [gdp-ts](https://github.com/rauchg/gdp-ts) — TypeScript library, lint presets and agent guidance for APIs that require evidence of an authorization check tied to the specific caller/resource. Consider for sensitive TypeScript boundaries where callers can omit or mix up checks; not a Python RERG dependency or an adopted component. Trusted check implementations still need tests, linting discourages proof forgery, and transactions or runtime constraints remain necessary where permissions can become stale.

The type-design and runtime-verification guidance draws on Lauren/Poteto's [pstack](https://github.com/cursor/plugins/tree/main/pstack), expressed in original wording. MIT is the intended project license; a license file is not yet installed or legally verified.