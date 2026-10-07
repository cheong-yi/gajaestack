#!/usr/bin/env python3
"""Read-only routing facts validation and static-guidance resource discovery.

Console contract (installed entry point ``gajaestack-routing`` maps to
``gajaestack.routing:main``; in a source checkout run ``python3 python/routing.py``):

- no arguments: print the named resource list as ``<name>: <path>`` lines
  (``guidance`` = the static shared routing guidance, ``facts-example`` = the
  checked schema-valid facts example);
- ``--guidance``: print only the static guidance resource path with no label or
  decoration, so shell bindings can consume it directly (for example
  ``gjc --append-system-prompt "$(gajaestack-routing --guidance)"``);
- ``--root DIR``: validate consumer-owned facts at ``DIR/.gajaestack/routing.toml``.
  Absent facts report the unconfigured state and exit 2 as a coverage failure;
  valid facts exit 0; invalid facts print every error and exit 1; unusable
  arguments exit 2.

The console never creates, rewrites, or copies anything. Routing guidance is a
static packaged resource, not a rendered template. A TypeScript-only consumer
needs no Python: installed host guidance reads ``.gajaestack/routing.toml``
directly, and this module is only the optional Python-side validation and
discovery convenience.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
GUIDANCE_RESOURCE = PACKAGE_DIR / "routing" / "AGENTS.md"
FACTS_EXAMPLE = PACKAGE_DIR / "routing.toml"
CONSUMER_FACTS_RELATIVE = Path(".gajaestack/routing.toml")

KNOWN_CHECKS = {
    "ts-test",
    "ts-typecheck",
    "ts-lint",
    "pytest",
    "ruff-check",
    "ruff-format",
    "mypy",
    "mutation-testing",
    "profiling",
    "adversarial-review",
}
FACT_SCHEMA_VERSION = 1
KNOWN_COMPONENTS = (
    "guard", "hypothesis", "mypy", "routing", "ruff", "required-ruff",
    "typescript", "typescript-guard", "typescript-config",
)
BINDING_FIELD = "required_ruff_before_pytest"
CORE_FACT_STRINGS = ("affected_test_command", "test_command")
OPTIONAL_FACT_STRINGS = ("mypy_command",)
RUFF_FACT_STRINGS = ("ruff_command", "ruff_format_command")
COMPLETION_TIMEOUT_FIELD = "completion_timeout_seconds"
COMPLETION_TIMEOUT_MAX = 9007199254740991
FACT_CORE_ERROR = (
    "fact must state quick and full local commands, Python version, no CI jobs, "
    "and no PCD enforcement"
)


def routing_policy_errors(root: Path) -> list[str]:
    return routing_policy_file_errors(root / "python/routing.toml")


def routing_policy_file_errors(policy_file: Path) -> list[str]:
    try:
        policy = tomllib.loads(policy_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        return [f"{policy_file}: cannot read routing policy TOML ({error})"]

    errors: list[str] = []
    categories = ("required", "advisory", "on_demand")
    selections: dict[str, list[str]] = {}
    for category in categories:
        value = policy.get(category)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            errors.append(f"{policy_file}: {category} must be an array of strings")
        else:
            selections[category] = value
            if category == "required" and not value:
                errors.append(f"{policy_file}: {category} must not be empty")
            if len(value) != len(set(value)):
                errors.append(f"{policy_file}: {category} contains duplicates")
    if len(selections) == len(categories):
        owners: dict[str, str] = {}
        for category, items in selections.items():
            for item in items:
                if item not in KNOWN_CHECKS:
                    errors.append(f"{policy_file}: unknown check {item!r} in {category}")
                if item in owners:
                    errors.append(
                        f"{policy_file}: {item!r} appears in both {owners[item]} and {category}"
                    )
                owners[item] = category

    conditional = policy.get("conditional")
    expected_triggers = {
        "input_parsing",
        "authorization_decisions",
        "file_writes_deletion",
        "external_commands",
    }
    if (
        not isinstance(conditional, dict)
        or set(conditional) != expected_triggers
        or any(not isinstance(value, str) or not value.strip() for value in conditional.values())
    ):
        errors.append(
            f"{policy_file}: conditional triggers must define the four named non-empty policies"
        )

    required_checks = set(selections.get("required", ()))
    errors.extend(_fact_errors(policy_file, policy.get("fact"), required_checks))
    for error in completion_budget_errors(policy):
        errors.append(f"{policy_file}: {error}")
    facts = policy.get("fact", {})
    components = facts.get("selected_components", []) if isinstance(facts, dict) else []
    if isinstance(components, list) and ("guard" in components or "ruff" in components):
        options = policy.get("python")
        if (
            not isinstance(options, dict)
            or type(options.get("schema_version")) is not int
            or options["schema_version"] != 1
        ):
            errors.append(f"{policy_file}: Python checks require [python] schema_version=1")
        else:
            if options.get("python_version") != facts.get("python_version"):
                errors.append(f"{policy_file}: Python version facts disagree")
            for field in (("imports", "executables") if "guard" in components else ()):
                value = options.get(field)
                if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
                    errors.append(f"{policy_file}: python.{field} must be an array of names")
            if "ruff" in components:
                paths = options.get("ruff_paths")
                if not isinstance(paths, list) or not paths or any(not isinstance(path, str) or not path for path in paths):
                    errors.append(f"{policy_file}: Ruff needs non-empty python.ruff_paths")
                if not isinstance(options.get("ruff_config"), str) or not options["ruff_config"]:
                    errors.append(f"{policy_file}: Ruff needs python.ruff_config")
    if isinstance(components, list) and "typescript" in components:
        options = policy.get("typescript")
        if (
            not isinstance(options, dict)
            or type(options.get("schema_version")) is not int
            or options["schema_version"] != 1
            or type(options.get("typecheck")) is not bool
            or type(options.get("lint")) is not bool
        ):
            errors.append(f"{policy_file}: [typescript] needs schema_version=1 and typecheck/lint booleans")
        else:
            for enabled, field in (("typecheck", "tsconfig"), ("lint", "biome_config")):
                if options[enabled] and (
                    not isinstance(options.get(field), str) or not options[field].strip()
                ):
                    errors.append(f"{policy_file}: typescript.{field} is required")
            paths = options.get("paths")
            if options["lint"] and (
                not isinstance(paths, list) or not paths
                or any(not isinstance(path, str) or not path.strip() for path in paths)
            ):
                errors.append(f"{policy_file}: typescript.paths must name non-empty lint scope")
            if "typescript-guard" in components:
                if not options["typecheck"] and not options["lint"]:
                    errors.append(f"{policy_file}: TypeScript binding selects no checks")
                for enabled, check in (("typecheck", "ts-typecheck"), ("lint", "ts-lint")):
                    if options[enabled] != (check in required_checks):
                        errors.append(f"{policy_file}: TypeScript binding requires {check!r} selection to match required")
    if isinstance(components, list) and "typescript-guard" in components and "typescript" not in components:
        errors.append(f"{policy_file}: typescript-guard requires typescript")
    return errors


def completion_budget_errors(policy: dict) -> list[str]:
    """Pure completion-budget checks; caller supplies any file/path prefix."""
    errors: list[str] = []
    for place in _misplaced_completion_budget(policy, ()):
        errors.append(
            f"{COMPLETION_TIMEOUT_FIELD} is supported only as a direct [fact] key "
            f"(found at {'.'.join(place)})"
        )
    fact = policy.get("fact")
    if isinstance(fact, dict) and COMPLETION_TIMEOUT_FIELD in fact:
        value = fact[COMPLETION_TIMEOUT_FIELD]
        if type(value) is not int or not 1 <= value <= COMPLETION_TIMEOUT_MAX:
            errors.append(
                f"fact.{COMPLETION_TIMEOUT_FIELD} must be an integer from 1 to "
                f"{COMPLETION_TIMEOUT_MAX} when present"
            )
        test_command = fact.get("test_command")
        if not isinstance(test_command, str) or not test_command.strip():
            errors.append(
                f"fact.{COMPLETION_TIMEOUT_FIELD} requires a nonblank fact.test_command"
            )
    return errors


def _misplaced_completion_budget(
    node: object, path: tuple[str, ...]
) -> list[tuple[str, ...]]:
    places: list[tuple[str, ...]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == COMPLETION_TIMEOUT_FIELD and path != ("fact",):
                places.append((*path, key))
            places.extend(_misplaced_completion_budget(value, (*path, key)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            places.extend(_misplaced_completion_budget(item, (*path, str(index))))
    return places


def _fact_errors(policy_file: Path, facts: object, required_checks: set[str]) -> list[str]:
    if not isinstance(facts, dict):
        return [f"{policy_file}: {FACT_CORE_ERROR}"]
    if "schema_version" not in facts:
        return [
            f"{policy_file}: action-required: fact.schema_version = {FACT_SCHEMA_VERSION} "
            "must be declared; existing consumer facts are preserved, not rewritten"
        ]
    if (
        type(facts["schema_version"]) is not int
        or facts["schema_version"] != FACT_SCHEMA_VERSION
    ):
        return [
            f"{policy_file}: action-required: unsupported fact.schema_version "
            f"{facts['schema_version']!r}; consumer facts require review "
            f"(only integer {FACT_SCHEMA_VERSION} is supported)"
        ]

    errors: list[str] = []
    if (
        any(
            not isinstance(facts.get(field), str) or not facts[field].strip()
            for field in CORE_FACT_STRINGS
        )
        or facts.get("ci_jobs_added") is not False
        or facts.get("pcd_is_enforcement") is not False
    ):
        errors.append(f"{policy_file}: {FACT_CORE_ERROR}")

    for field in OPTIONAL_FACT_STRINGS:
        value = facts.get(field)
        if field in facts and (not isinstance(value, str) or not value.strip()):
            errors.append(
                f"{policy_file}: fact.{field} must be a non-empty string when present"
            )

    components: set[str] | None = None
    raw_components = facts.get("selected_components")
    if (
        not isinstance(raw_components, list)
        or not raw_components
        or any(not isinstance(item, str) for item in raw_components)
    ):
        errors.append(
            f"{policy_file}: fact.selected_components must be a non-empty array of strings"
        )
    else:
        if len(raw_components) != len(set(raw_components)):
            errors.append(f"{policy_file}: fact.selected_components contains duplicates")
        unknown = sorted(set(raw_components) - set(KNOWN_COMPONENTS))
        if unknown:
            errors.append(
                f"{policy_file}: fact.selected_components contains unknown component(s): "
                f"{', '.join(repr(item) for item in unknown)}; supported: "
                f"{', '.join(KNOWN_COMPONENTS)}"
            )
        components = set(raw_components)

    if components and components.intersection({"guard", "hypothesis", "mypy", "ruff"}):
        if not isinstance(facts.get("python_version"), str) or not facts["python_version"].strip():
            errors.append(f"{policy_file}: fact.python_version must name the Python runtime")

    ruff_selected = components is not None and "ruff" in components
    for field in sorted(RUFF_FACT_STRINGS):
        value = facts.get(field)
        if ruff_selected and field not in facts:
            errors.append(
                f"{policy_file}: fact must state {' and '.join(RUFF_FACT_STRINGS)} "
                "while component 'ruff' is selected"
            )
            break
        if field in facts and (not isinstance(value, str) or not value.strip()):
            errors.append(
                f"{policy_file}: fact.{field} must be a non-empty string when present"
            )

    if components is not None and "required-ruff" in components and BINDING_FIELD not in facts:
        errors.append(f"{policy_file}: required-ruff needs {BINDING_FIELD} = 'active'")
    if BINDING_FIELD in facts:
        value = facts[BINDING_FIELD]
        if value == "active":
            unmet = [
                f"component {name!r}"
                for name in ("ruff", "guard", "required-ruff")
                if components is None or name not in components
            ]
            if "ruff-check" not in required_checks:
                unmet.append("required check 'ruff-check'")
            if unmet:
                errors.append(
                    f"{policy_file}: action-required: {BINDING_FIELD} is selected but "
                    f"prerequisite(s) not satisfied: {', '.join(unmet)}"
                )
        else:
            errors.append(
                f"{policy_file}: action-required: unsupported {BINDING_FIELD} value "
                f"{value!r}; only 'active' with explicit required-ruff selection is supported; "
                "remove stale pending declarations or review native binding adoption"
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gajaestack-routing",
        description="Read-only routing resource discovery and consumer facts validation.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--guidance",
        action="store_true",
        help="print the static shared routing guidance resource path",
    )
    group.add_argument(
        "--root",
        type=Path,
        metavar="DIR",
        help=f"validate consumer facts at DIR/{CONSUMER_FACTS_RELATIVE.as_posix()}",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    if args.guidance:
        print(GUIDANCE_RESOURCE)
        return 0

    if args.root is not None:
        root = args.root.expanduser().resolve()
        if not root.is_dir():
            print(f"root is not a directory: {root}", file=sys.stderr)
            return 2
        facts_path = root / CONSUMER_FACTS_RELATIVE
        if not facts_path.exists():
            print(f"facts: {facts_path} (absent; unconfigured)")
            return 2
        errors = routing_policy_file_errors(facts_path)
        if errors:
            for error in errors:
                print(error)
            return 1
        print(f"facts: {facts_path} (valid)")
        return 0

    print(f"guidance: {GUIDANCE_RESOURCE}")
    print(f"facts-example: {FACTS_EXAMPLE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
