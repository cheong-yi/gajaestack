# Agent entry point

The canonical north star is [gajaestack issue #1](https://github.com/cheong-yi/gajaestack/issues/1).

- Keep guidance modular: skills are independently selectable; never import or bundle every skill by default.
- Prefer existing repository tools, recipes, harnesses, tests, and evidence practices. Prune duplicated guidance rather than adding parallel conventions.
- Validate execution claims against actual commands and observed behavior. Distinguish code-enforced behavior from agent guidance, which cannot enforce itself.
- Do not modify consumer configuration without an explicitly scoped request.
- Onboarding or adoption advice starts by reading this entry point, [README.md](README.md), and the [selectable native checks guide](docs/python-trial.md), then inspecting the consumer's existing tools and test entrypoints; recommend the smallest useful selection and distinguish copied assets, activated automatic checks, and advisory guidance.
- Preview before `--apply`, preserve existing consumer configuration, and treat dependency installs and CI changes as explicitly approved steps.
