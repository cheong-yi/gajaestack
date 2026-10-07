#!/usr/bin/env python3
"""Check bundled-skill metadata, version metadata, routing policy, and local Markdown links."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
REQUIRED_FRONTMATTER = {
    "name",
    "description",
    "problem",
    "use_when",
    "when_to_run",
}
IGNORED_DIRS = {".git", ".gjc", "__pycache__"}

# Routing facts validation lives in the installed ``gajaestack.routing`` module
# (python/routing.py in a checkout); load it from source so this checker works
# without installation.
_ROUTING_SOURCE = Path(__file__).resolve().parents[1] / "python" / "routing.py"


def _load_routing():
    spec = importlib.util.spec_from_file_location(
        "gajaestack_routing_source", _ROUTING_SOURCE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load routing module from {_ROUTING_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


routing = _load_routing()


def markdown_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.md")
        if not any(part in IGNORED_DIRS for part in path.relative_to(root).parts)
    )


def skill_errors(skill_file: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [f"{skill_file}: cannot read UTF-8 skill file ({error})"]

    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return [f"{skill_file}: missing opening frontmatter delimiter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return [f"{skill_file}: missing closing frontmatter delimiter"]

    fields: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not separator or not key or not value:
            errors.append(f"{skill_file}:{line_number}: expected a non-empty metadata field")
        elif key in fields:
            errors.append(f"{skill_file}:{line_number}: duplicate metadata field {key!r}")
        else:
            fields[key] = value

    for key in sorted(REQUIRED_FRONTMATTER - fields.keys()):
        errors.append(f"{skill_file}: missing required metadata field {key!r}")
    if fields.get("name") and fields["name"] != skill_file.parent.name:
        errors.append(
            f"{skill_file}: skill name {fields['name']!r} does not match directory "
            f"{skill_file.parent.name!r}"
        )
    if not any(line.strip() for line in lines[end + 1 :]):
        errors.append(f"{skill_file}: skill body is empty")
    return errors


def link_errors(root: Path, markdown_file: Path) -> list[str]:
    try:
        text = markdown_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [f"{markdown_file}: cannot read UTF-8 Markdown ({error})"]

    errors: list[str] = []
    for match in MARKDOWN_LINK.finditer(text):
        target = match.group(1).strip()
        if target.startswith("<") and ">" in target:
            target = target[1 : target.index(">")]
        else:
            target = target.split(maxsplit=1)[0]
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue

        destination = (markdown_file.parent / unquote(parsed.path)).resolve()
        try:
            destination.relative_to(root)
        except ValueError:
            errors.append(f"{markdown_file}: local link escapes repository: {target!r}")
            continue
        if not destination.exists():
            errors.append(f"{markdown_file}: broken local link: {target!r}")
    return errors


def check(root: Path) -> list[str]:
    root = root.resolve()
    if not root.is_dir():
        return [f"repository root is not a directory: {root}"]

    errors: list[str] = []
    for markdown_file in markdown_files(root):
        errors.extend(link_errors(root, markdown_file))
    for skill_file in sorted((root / "skills").glob("*/SKILL.md")):
        errors.extend(skill_errors(skill_file))
    errors.extend(routing.routing_policy_errors(root))
    errors.extend(version_errors(root))
    return errors


def version_errors(root: Path) -> list[str]:
    """Require package.json ``version`` to equal the Python package ``__version__``."""
    package_json = root / "package.json"
    if not package_json.is_file():
        return [f"{package_json}: missing native package version metadata"]
    try:
        document = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"{package_json}: cannot read package version metadata ({error})"]
    if (
        not isinstance(document, dict)
        or not isinstance(document.get("version"), str)
        or not document["version"].strip()
    ):
        return [f"{package_json}: package version must be a non-empty string"]
    package_version = document["version"].strip()
    version_file = root / "python/__init__.py"
    try:
        source = version_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [f"{version_file}: cannot read Python package version ({error})"]
    match = re.search(r'^__version__\s*=\s*(["\'])([^"\']+)\1', source, re.MULTILINE)
    if match is None:
        return [f"{version_file}: missing __version__ declaration"]
    if match.group(2) != package_version:
        return [
            f"version mismatch: package.json declares {package_version!r} but "
            f"{version_file} declares {match.group(2)!r}"
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print("usage: python scripts/check_repo.py [repository-root]", file=sys.stderr)
        return 2
    root = Path(args[0]) if args else Path(__file__).resolve().parents[1]
    errors = check(root)
    if errors:
        print("Repository quality checks failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        "Repository quality checks passed (skill metadata, version metadata, routing policy, "
        "and local Markdown links)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
