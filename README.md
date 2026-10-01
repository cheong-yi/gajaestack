# gajaestack
A modular repo-quality kit: practical agent guidance, reusable checks, and repeatable verification.

Start with [AGENTS.md](AGENTS.md), the agent entry point. The canonical north star is [issue #1](https://github.com/cheong-yi/gajaestack/issues/1).

## Skills

Select either skill independently; neither requires the other:
- `type-discipline` — choose clear, useful types and model valid states.
- `verify-change` — verify a change through a reproducible user path.

Guidance helps agents reason; it is not executable enforcement. Node.js/npm are required for the Skills CLI (the interactive CLI lets you choose project-local agents). These commands follow its documentation; CLI execution has not been verified here:

```sh
npx skills add cheong-yi/gajaestack --list
npx skills add cheong-yi/gajaestack --skill type-discipline
npx skills add cheong-yi/gajaestack --skill verify-change
```

For a local clone, substitute its location:

```sh
npx skills add /path/to/gajaestack --skill type-discipline
```

For GJC, copy only the selected skill into the consumer repo (replace the source path):

```sh
mkdir -p .gjc/skills
cp -R /path/to/gajaestack/skills/type-discipline .gjc/skills/
```

Selective copying has been verified in an isolated consumer. GJC support in the external Skills CLI and agent loading remain unverified.

The type-design and runtime-verification guidance draws on Lauren/Poteto's [pstack](https://github.com/cursor/plugins/tree/main/pstack), expressed in original wording. No project license has been selected.
