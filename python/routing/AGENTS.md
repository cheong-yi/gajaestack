### Selected gajaestack guidance

Keep quick iteration and completion checks distinct. Run ONE completion command: `{{test_command}}`, the native test command your reviewed facts already declare in `.gajaestack/routing.toml`, exactly as declared. This kit adds no second completion path, no runner, and no cache.

Outer completion budget: {{completion_budget}} for the declared command's full scope ([fact].completion_timeout_seconds). The calling launcher must honour it, preserve logs, and report outer timeouts as incomplete verification, distinct from native failures. Unconfigured means no kit default: report the launcher's actual limit. This kit changes neither launcher limits nor native test/check deadlines.

What your facts declare: declared binding `{{declared_binding}}`; facts-declared required checks `{{declared_checks}}`. When activated in reviewed native configuration, the declared binding runs its checks inside the completion command, so do not run a separate full lint or typecheck before it. Declaration alone is not activation: without activation the command covers only what your existing native configuration runs there, never standalone selected lint/typecheck outside that wiring, and no coverage is not a pass.

Read consumer-owned `.gajaestack/routing.toml` for scopes, quick commands, and conditional policies; use the consumer's existing harness and prerequisites. Report native failures and checks not run; missing tools or empty targets are not passes.

This is soft guidance, not enforcement or a runtime guard. Copying this addendum is not activation: adoption copies bytes, edits no native configuration, and proves no wiring. Components remain independently selected; installing Ruff and a guard does not activate a Ruff-before-pytest binding. Preserve consumer instructions and facts; change them only within explicitly approved scope.
