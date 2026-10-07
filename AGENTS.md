# Agent entry point

The canonical north star is [gajaestack issue #1](https://github.com/cheong-yi/gajaestack/issues/1).

- Keep guidance modular: skills are independently selectable; never import or bundle every skill by default.
- Prefer existing repository tools, recipes, harnesses, tests, and evidence practices. Prune duplicated guidance rather than adding parallel conventions.
- Validate execution claims against actual commands and observed behavior. Distinguish code-enforced behavior from agent guidance, which cannot enforce itself.
- For Markdown changes or moves/deletions of files linked from Markdown, prefer running `seiso check --no-cache` from the repository root once after the final edits. Skip for code-only changes that cannot affect documentation links. This is advisory, not a completion gate: review findings, fix clear issues introduced by your changes within scope, and report unrelated findings or an unavailable tool without blocking the task. Do not suppress rules merely to clear the check. Seiso checks documentation structure and links, not factual correctness; no hooks or CI gates are enabled.
- Do not modify consumer configuration without an explicitly scoped request.
- Onboarding or adoption advice starts by reading this entry point, [README.md](README.md), and the [selectable native checks guide](docs/python-trial.md), then inspecting the consumer's existing tools and test entrypoints; recommend the smallest useful selection and distinguish installed dependencies, activated automatic checks, and advisory guidance.
- Inspect the selected native package and declared consumer facts before installation; preserve existing consumer configuration and treat dependency installs, host wiring, and CI changes as explicitly approved steps. Shared logic upgrades through pinned native dependencies, not copied source assets.
