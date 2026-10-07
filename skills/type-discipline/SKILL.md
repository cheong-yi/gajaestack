---
name: type-discipline
description: Use when adding or changing types, state models, identifiers, or data boundaries; choose the smallest representation that makes meaningful invalid states difficult to express.
problem: Ambiguous or unvalidated values allow invalid states to cross domain boundaries.
use_when: Changing type boundaries, state models, identifiers, or external-input validation.
when_to_run: During design and implementation of a change whose correctness depends on represented states or validated inputs.
---

# Type discipline

Apply this guidance to the change at hand; do not add types for their own sake.

- Choose the smallest useful representation that communicates the domain and supports the behavior. Prefer established patterns already used in this repository. Subtract before abstracting: remove the redundant representation or misplaced responsibility first; add a shared type, generic, or helper only when concrete callers demonstrate the same recurring need.
- Reuse the canonical representation already accepted at a boundary instead of introducing a parallel one.
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

Adapt names and variant details to the real domain and existing project conventions. This is guidance, not executable enforcement; validate the change with the repository's normal checks, exercising the failure cases the boundary contract promises to reject before side effects.
