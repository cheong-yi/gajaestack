# Changelog

## 2026-11-25

The vendored pstack files are refreshed to `005d8f6e8ec0`. The plugin is `0.1.5`. The executor now also gets `principle-explain-the-number` and `principle-minimize-reader-load`. That reverses the 2026-11-04 call on minimize-reader-load. The explain-the-number appendix names the benchmark-checklist skill instead of linking to it.

`no-comments` is no longer a critic appendix. The critic's tool list has no `task` or edit tool, so it could not spawn Comment Sicko or apply fixes. It is now the on-demand skill `skills/no-comments/`, without the sentence that pointed at poteto-mode, and its `comment-sicko` agent sits beside it. `blast-radius`, `tdd`, and `benchmark-checklist` are new on-demand skills. These four live only in the checkout, not in the packages. `interrogate` and `arena` are not taken.

## 2026-11-06

Loc-polsia is now a required system appendix in `plugins/practice-role-sets`. A new session that has that plugin enabled receives the short kernel that fits the loader cap. The longer projection does not fit unless an existing appendix is removed, and the loader drops overflow instead of shortening it. The text does not enforce itself. Package install still does not install the plugin, and the Python and TypeScript packages stay at `0.1.3`. The plugin version is `0.1.4` because its contents changed. The retained `0.1.0` artifact is unchanged. Issue #1 still records the older selectable-components rule. This checkout does not edit that issue.

## 2026-11-04

Seven pstack principles were left out of the plugin on this date. This is a decision from that day, not a standing ban. It can change.

- `principle-foundational-thinking` repeats model-the-domain, type discipline, sequence, and the prompt line about growing in layers.
- `principle-minimize-reader-load` adds a reader test, but subtract and boundary already push that way.
- `principle-guard-the-context-window` is thinner than the parent tool rules, which already say to read sections and keep large payloads out of the assignment.
- `principle-experience-first` is product taste, not a code check.
- `principle-exhaust-the-design-space` says to build prototypes. The GJC prompt says to avoid speculative work.
- `principle-outcome-oriented-execution` allows a broken middle. The prompt says not to accept a stopgap.
- `principle-redesign-from-first-principles` fights the smallest-change rule.

The recorded quick command no longer contains the word TARGET. `test_command` remains the completion command. The seeded checker command finds Bun on PATH and a nearby node_modules when those variables are unset. A miss still exits 2. It is a kit check, not a command for every lane.

The six on-demand skills now ship in the Python and TypeScript packages. They still run only when someone invokes them. Package install still does not install the plugin.

The source version is `0.1.3`, the same number as the practice-role-sets plugin. The retained `0.1.0` artifact is unchanged.

Links in the two executor principles now point at the principle files in this repo. Names of principles that were not taken are plain text, not links. Seiso checks those files again.
