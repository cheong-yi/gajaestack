# gajaestack

A modular repo-quality kit: practical agent guidance, reusable checks, and repeatable verification.

Start with [AGENTS.md](AGENTS.md), the agent entry point. The canonical design is [issue #1](https://github.com/cheong-yi/gajaestack/issues/1); the [scope invariant](docs/scope-invariant.md) summarizes its intended product scope without claiming every capability is delivered.

## Quick start: contributor lint

Choose the smallest useful selection; this example is **TypeScript lint only**, not a universal runner. Prerequisites: Bun >= 1.4.2, Git with the explicit contribution target and sufficient history, an existing local `node_modules/.bin/biome`, consumer-owned `biome.json`, and real `src` files. Reuse existing tools/configuration; the kit provisions none. Python-only users instead follow the independent [Ruff selection](docs/python-trial.md#python-quick-feedback-versus-completion), with Python >=3.11 and Ruff but no Bun or pytest requirement.

**Release prerequisite:** contributor selectors below describe the current source checkout, including uncommitted changes, not proven contents of retained `0.1.0` artifacts. Maintainers must first review and commit the feature, choose a new version if replacing an accepted release, then [build once and retain](docs/python-trial.md#maintainer-build-once-and-retain). Consumers install reviewed artifacts; they do not rebuild the kit.

With installation separately approved, set `artifacts` to the retained absolute version directory and `version` to its reviewed version. Verify its recorded SHA-256 before the pinned devDependency install:

```sh
bun add --dev --exact --offline --ignore-scripts --backend=copyfile \
  "gajaestack@$artifacts/gajaestack-$version.tgz"
```

Track the reviewed `package.json` and `bun.lock`, consumer `.gajaestack/routing.toml`, and native configuration; keep installed `node_modules/` (or Python `.venv/`) ignored. Save the guide's complete [minimal lint selection](docs/python-trial.md#minimal-typescript-lint-selection), adjusting paths and commands to actual consumer facts without replacing unrelated settings. Installation alone activates nothing: preloads, pytest plugins and skills are independent optional selections. [Install/replay, upgrades and removal](docs/python-trial.md#install-from-local-artifacts-no-registry) remain native package-manager operations.

Routine contributor feedback has one native entrypoint per selected language. Set `TARGET` to the actual contribution target, never an inferred tracking branch:

```sh
bun run gajaestack-check --quick --reference-branch "$TARGET"
# Python alternative, only when Ruff is selected:
PYTHONDONTWRITEBYTECODE=1 gajaestack-python-check --reference-branch "$TARGET"
```

This lints current whole files with net changes since the target's merge base with HEAD: committed, staged, unstaged and non-ignored untracked work, intersected with declared lint scope. Policy changes can expand scope. It is not changed-line or last-push tracking. [Selectors, defaults and edge cases](docs/python-trial.md#contributor-lint-scope) remain explicit; no checker default changes.

Full lint is separately available: `bun run gajaestack-check` for the lint-only selection, or `PYTHONDONTWRITEBYTECODE=1 gajaestack-python-check --full` for Ruff. Enabling TypeScript typechecking also makes the non-quick command run full-tsconfig `tsc --noEmit`; quick never typechecks. Behavioral tests, formatting, other typechecks and existing CI remain distinct obligations, not results implied by lint. Run the declared completion boundary before claiming completion.

Read scope and diagnostics, not just exit status: missing selected tools, invalid facts/configuration/references and native errors fail; native warnings are not automatically promoted to errors. An empty quick/contributor intersection can exit `0` while explicitly reporting **no coverage**, never a lint pass; full empty scope fails. See [result semantics](docs/python-trial.md#contributor-lint-results). Demonstrate each adopted check with nonempty valid scope and a seeded rejection. Consumer wiring, adoption and CI changes require separate approval.

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
