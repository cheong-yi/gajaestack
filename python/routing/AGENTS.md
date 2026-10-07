### Selected gajaestack routing guidance

Read consumer-owned `.gajaestack/routing.toml` from the consumer working directory. These facts, scopes and policies belong to the consumer, not this installed dependency. Follow only explicitly selected components and conditional policies; installation alone activates no checks.

Keep quick iteration and completion distinct. Use `[fact].test_command` as the one completion command. Required checks run within that command only when the corresponding native pytest plugin or Bun test preload is actually configured. Inspect native wiring; a declaration is not proof of activation. Report selected but unbound checks separately rather than claiming completion covered them. This kit adds no runner or second completion path.

The optional `[fact].completion_timeout_seconds` is the consumer's outer completion budget, not a check timeout. The calling launcher must honour it and preserve failures and logs; an outer timeout means incomplete verification. Absence means unconfigured, not an invented default. The package does not alter launcher limits.

Use declared paths and the consumer's existing tools and harnesses. Missing prerequisites, empty scopes and failed native checks are not passes. Installed quick checks conservatively cover the full declared lint scope because ignored dependency code cannot be proven unchanged without a stored baseline; quick mode does not replace full completion.

This is explicitly selected soft guidance, not enforcement. Host loading and native guard activation are separate. Preserve existing consumer instructions and configuration; change them only within approved scope. Update shared logic and guidance by upgrading the pinned native dependency, not by editing or re-copying installed files.
