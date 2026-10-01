---
name: verify-change
description: Use when implementing or changing behavior to choose and run a reproducible user-facing verification path, inspect its side effects, and report evidence and limits.
---

# Verify a change

1. Inspect the changed behavior, relevant existing tests, and documented commands or harnesses. Reuse the project's recipes, harnesses, test conventions, and evidence format; do not generate new docs or harnesses for every change.
2. Select a reproducible path a user would take. State the expected observations, relevant side effects, and negative or failure cases before running it. Include a health check or launch step when the path requires one.
3. Run the actual path, not only a substitute or a check that cannot observe the changed behavior. Use processes and test state isolated to this verification; avoid interfering with existing processes or shared state.
4. Capture the actions and results as evidence. Clean up only resources created by this verification, and preserve useful results after safe cleanup. Never invent or imply proof that was not observed.
5. Report the exercised scope, observed results, limitations, and blockers. Do not turn a narrow pass into a blanket claim of success.

Use existing feature maps when the repository maintains them: update affected entries with the change and evidence, keeping the map aligned with actual behavior. Do not create a feature map where none exists just to satisfy this guidance.

Never perform sweeping mutations. Do not write to external systems or services without explicit approval; use an authorized, isolated local or test path instead. If a safe, representative path cannot be run, say exactly what was inspected and what remains unverified.
