---
name: type-discipline
description: Use when adding or changing types, state models, identifiers, or data boundaries; choose the smallest representation that makes meaningful invalid states difficult to express.
---

# Type discipline

Apply this guidance to the change at hand; do not add types for their own sake.

- Choose the smallest useful representation that communicates the domain and supports the behavior. Prefer established patterns already used in this repository.
- Model mutually exclusive states as discriminated unions rather than independent flags when combinations would permit invalid states.
- Give values semantic, distinct ID types only when confusing them is a meaningful risk. Avoid branding every primitive.
- Parse and validate untrusted data at boundaries, then use the validated representation internally. Derive types from authoritative schemas where available; do not create a competing schema.
- Keep boundary input checks explicit: distinguish missing, malformed, out-of-range and valid-but-non-actionable values when those cases have different behavior. Reject invalid input before side effects, and do not turn a parse/type assertion into validation.
- Keep raw boundary values separate from validated domain values when that distinction prevents accidental use. Use the smallest validated representation that lets downstream code rely on the checked invariant.
- Handle every union variant explicitly. Use the language's exhaustive checking pattern already established in the codebase.
- Avoid unnecessary casts, assertions, generic machinery, and type gymnastics. A cast should have a clear boundary invariant that ordinary types cannot express.

For example, independent flags allow impossible combinations:

```ts
type Job = { running: boolean; failed: boolean; result?: string };
```

Represent the actual alternatives instead:

```ts
type Job =
  | { state: "running" }
  | { state: "failed"; error: Error }
  | { state: "complete"; result: string };
```

Adapt names and variant details to the real domain and existing project conventions. This is guidance, not executable enforcement; validate the change with the repository's normal checks.
