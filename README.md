# gajaestack

A modular repo-quality kit: practical agent guidance, reusable checks, and repeatable verification.

Start with [AGENTS.md](AGENTS.md), the agent entry point. The canonical design is [issue #1](https://github.com/cheong-yi/gajaestack/issues/1); the [scope invariant](docs/scope-invariant.md) summarizes its intended product scope without claiming every capability is delivered.

## Skills

Select each skill independently; none requires another:
- `native-quality` — select suitable native checks and focused regression tests without imposing a tool migration.
- `type-discipline` — choose clear, useful types and model valid states.
- `verify-change` — verify a change through a reproducible user path.

Skill guidance helps agents reason; it does not enforce behavior by itself. The repository provides a dependency-free Python helper for previewing, adopting, and removing selected Python-trial files, plus a local checker for bundled-skill metadata and Markdown links. These tools cover only their documented file behavior and metadata/link checks; they do not enforce consumer type systems, runtime behavior, or the full gajaestack scope.

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

Run from a gajaestack checkout. The checker validates bundled-skill metadata and local Markdown links. Its tests cover the checker's failure cases; these commands do not validate consumer applications:

```sh
python3 scripts/check_repo.py
python3 -m unittest discover -s tests
```

The optional Python import-prerequisite helper checks whether named import modules are discoverable. It does not install packages, establish version compatibility, prove successful module initialization, or replace running the selected check. Name only imports required by that check; build backends and parser plugins are independent prerequisites:

```sh
python3 scripts/check_python_imports.py setuptools tree_sitter tree_sitter_javascript tree_sitter_typescript
```

The [selectable Python trial](docs/python-trial.md) documents the adoption helper, native command examples, prerequisites, pilot-specific configuration limits, and safe removal. Adoption does not install dependencies or create CI jobs.

The type-design and runtime-verification guidance draws on Lauren/Poteto's [pstack](https://github.com/cursor/plugins/tree/main/pstack), expressed in original wording. MIT is the intended project license; a license file is not yet installed or legally verified.