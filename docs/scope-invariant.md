# Scope invariant

The canonical design record is [gajaestack issue #1](https://github.com/cheong-yi/gajaestack/issues/1). This document summarizes the intended product scope; it is not a claim that every capability is implemented, installed, validated in a pilot, or legally reviewed. Guidance, executable safeguards, observed scenario evidence, and remaining scope must be distinguished.

## Six capabilities

Gajaestack is a lightweight, selectively adoptable repository-quality kit covering:

1. Mechanical checks and enforcement.
2. Type and boundary discipline.
3. Repeatable runtime verification and execution-specific evidence.
4. Scoped code cleanup and protection of unrelated work.
5. Focused and adversarial review, invoked explicitly or through adopted risk triggers.
6. Structural learning and pruning: turn recurring corrections into verified types, tests, lint rules, scripts, or canonical helpers where useful, and remove redundant guidance.

Develop these capabilities incrementally across mechanical foundations, thin guidance and repeatable verification, and selective deeper checks. Pilots and passing test suites prove bounded observations; they do not redefine or shrink the scope or establish delivery of consumer safeguards. Keep planned, conditional, and deferred outcomes visible. Generalize failure mechanisms and intervention rules rather than one repository's architecture. Fix defects at the responsible implementation boundary; shared verification is not a substitute for correct application behavior. Material scope or architecture changes require an explicit owner decision.

## Ownership and adoption

Components are individually selectable and work independently where possible. Suggested combinations install nothing implicitly. Unselected components add no dependencies, active checks, or agent-context cost. Required dependencies are explicit and minimal; components can be removed without disrupting unrelated selections. Modularity does not require a plugin framework, registry, dependency resolver, or blanket dependency bundle.

Shared component logic, integrations, verification lifecycle, evidence requirements, cleanup safeguards, and necessary extensions are centrally maintained under one gajaestack release version. Consumers select components and supply explicit declarative application inputs—such as facts, paths, scenarios, oracles, and policies—instead of maintaining recipe forks. Add centrally maintained extensions only when a demonstrated need cannot be expressed by inputs.

Preserve suitable native tools and harnesses. Recommend small default toolsets without imposing migrations or identical native-tool versions. Reuse selected established tools before adding machinery for a demonstrated gap. Do not require an orchestration engine, universal runner, multi-model panel, rewrite loop, or new package manager.

Updates are coordinated through pinned native Bun dependencies and Python distributions sharing one release version. Review release and lock changes, validate affected behavior before adoption, and keep project facts and native wiring consumer-owned. Do not edit installed shared code or automatically track latest. There is no separate kit updater or copied-source ownership manager.

Proven mechanical checks may block failures; new or noisy checks begin advisory. Each consumer explicitly adopts deeper-review triggers relevant to its risks. Cleanup remains scoped, preserves evidence, and may correctly conclude no change is needed. Cleanup owns only its processes and test state and does not touch unrelated resources. A recipe, harness, regression test, and evidence artifact serve different purposes; one scenario does not establish whole-product coverage.

Gajaestack declares download requirements; network policy remains with the consuming repository or host. Component selection never implicitly authorizes downloads, firewall changes, or public publication.

## Intended choices and open work

The intended license is MIT; it is not yet installed as a license file or legally verified. Retain required notices for copied or substantially adapted upstream material, including attribution and applicable notices for Lauren/Poteto's original `cursor/plugins/pstack`.

Initial languages are Python and TypeScript; a third language waits for a concrete consumer. RERG is the intended Python pilot, followed by validating transfer to gajaeway for TypeScript. These choices do not establish that either pilot or all intended agent environments are supported. Portable content alone does not establish support for other hosts.

Native Bun and Python packaging is the approved local implementation direction; publication and real-consumer migration remain separate approvals. Concrete target scenarios, per-consumer inputs and contracts, exact recommended tools, review triggers and false-positive policy, host support beyond verified loading paths, and proportionate success baselines remain evidence-driven work. A new manager is not presumed. Public material should be independently shareable and omit private repository context and raw verification artifacts.