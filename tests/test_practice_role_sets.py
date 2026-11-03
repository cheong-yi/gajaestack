"""Vendored pstack role sets stay byte-identical to the pinned upstream files.

Every full upstream copy is anchored to its git blob id at pstack revision
12d587dfb20741cafc376c42c696c5f6e2a64487; derived bodies are compared with the
anchored full copy, so the test needs no network or local pin.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
PLUGIN = KIT_ROOT / "plugins/practice-role-sets"
OVERLAYS = KIT_ROOT / "overlays"

EXECUTOR = (
    "principle-subtract-before-you-add",
    "principle-model-the-domain",
    "principle-boundary-discipline",
    "principle-type-system-discipline",
    "principle-test-behavior-not-implementation",
    "principle-prove-it-works",
    "principle-encode-lessons-in-structure",
    "principle-fix-root-causes",
    "principle-sequence-verifiable-units",
)
CRITIC = ("no-comments",)
SYSTEM = ("unslop",)
AGREED = {"executor": EXECUTOR, "critic": CRITIC}
EXCLUDED = (
    "architect",
    "planner",
    "poteto-mode",
    "setup-pstack",
    "interrogate",
    "reflect",
    "tdd",
    "principle-outcome-oriented-execution",
    "typescript-best-practices",
    "create-verification-skill",
    "maintain-verification-skill",
)
APPENDIX_LIMIT = 8192
AGENT_TOTAL_LIMIT = 32768

# Git blob ids of upstream pstack files at the pinned revision.
SKILL_BLOBS = {
    "no-comments": "3b3e76295a7ad66806dcc683e4de92fb25690f8b",
    "principle-boundary-discipline": "dfe9a6fb0e5acd6ae43a41437ee0951adfe839cb",
    "principle-encode-lessons-in-structure": "df9cd5ff2fb3c18267349cc6aecd8121848ef834",
    "principle-fix-root-causes": "7e5a419aeec97b4076fa517865013677428a9fa3",
    "principle-model-the-domain": "e1d664a19243c90a84e5e7a816e9e05146c88720",
    "principle-prove-it-works": "5dc14a3b06f9d579e5c17cd8a7242f432ddb3125",
    "principle-sequence-verifiable-units": "986371260ebccd9a5a6818c9561e88c1d270d0ee",
    "principle-subtract-before-you-add": "d28770cf47a5798d0250a25ad494aedfecad154e",
    "principle-test-behavior-not-implementation": "42de6f8f7cab01b9f67aa28bd59b128f7574fbab",
    "principle-type-system-discipline": "6030f171bee0d1902cf7ca91f06225e09f0f5433",
    "unslop": "229a090708710c36caa0017f8d33e90880dc6846",
    "create-verification-skill": "f869e26122991252373d5b8f6357e5b9ff195a00",
    "maintain-verification-skill": "a2680b91fead45a0b4963d8c367a854956bea59d",
    "typescript-best-practices": "2c0279d9a5f800192605e47b55cae4e75a17ec27",
}
ON_DEMAND = {
    "skills/create-verification-skill/SKILL.md": SKILL_BLOBS["create-verification-skill"],
    "skills/maintain-verification-skill/SKILL.md": SKILL_BLOBS[
        "maintain-verification-skill"
    ],
    "skills/create-verification-skill/references/feature-map-example/README.md": (
        "fb64570cfab3bbe672fe80925651933ebd57aa33"
    ),
    "skills/create-verification-skill/references/feature-map-example/create-note.md": (
        "21357566b69223a503d6780a04fb90ce540eae22"
    ),
    "skills/create-verification-skill/references/feature-map-example/search.md": (
        "1f8e57d3aaf19cf27a9464d55fa72e46bcbc8b0f"
    ),
}


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def body_after_frontmatter(source: bytes) -> bytes:
    if not source.startswith(b"---\n"):
        raise AssertionError("upstream file has no opening frontmatter fence")
    closing = source.index(b"\n---\n", 4)
    return source[closing + len(b"\n---\n") :]


def pinned_source(path: Path, name: str) -> bytes:
    data = path.read_bytes()
    if git_blob_id(data) != SKILL_BLOBS[name]:
        raise AssertionError(f"{path} differs from pinned upstream {name}")
    return data


def manifest() -> dict:
    return json.loads((PLUGIN / "gajae-plugin.json").read_text(encoding="utf-8"))


class PracticeRoleSetTests(unittest.TestCase):
    def test_manifest_names_only_the_agreed_agents_and_files(self) -> None:
        document = manifest()
        self.assertEqual(document["kind"], "gajae-code-plugin")
        self.assertEqual(
            set(document), {"name", "version", "kind", "system_appendix", "agent-appendix"}
        )
        system = document["system_appendix"]
        self.assertEqual([entry["name"] for entry in system], list(SYSTEM))
        for entry in system:
            self.assertNotIn("agent", entry)
            self.assertNotIn("content", entry)
            self.assertEqual(entry["path"], f"appendices/system/{entry['name']}.md")
        declared: dict[str, list[str]] = {"executor": [], "critic": []}
        for entry in document["agent-appendix"]:
            self.assertIn(entry["agent"], declared, entry)
            self.assertNotIn("content", entry)
            self.assertEqual(
                entry["path"], f"appendices/{entry['agent']}/{entry['name']}.md"
            )
            declared[entry["agent"]].append(entry["name"])
        self.assertEqual({agent: tuple(names) for agent, names in declared.items()}, AGREED)
        appendix_files = {
            path.relative_to(PLUGIN).as_posix()
            for path in (PLUGIN / "appendices").rglob("*")
            if path.is_file()
        }
        self.assertEqual(
            appendix_files,
            {entry["path"] for entry in system + document["agent-appendix"]},
        )
        upstream_files = {path.name for path in (PLUGIN / "upstream").iterdir()}
        self.assertEqual(
            upstream_files,
            {f"{name}.md" for name in set(EXECUTOR) | set(CRITIC) | set(SYSTEM)},
        )

    def test_appendix_bodies_match_upstream_after_frontmatter(self) -> None:
        document = manifest()
        for entry in document["system_appendix"] + document["agent-appendix"]:
            with self.subTest(name=entry["name"], agent=entry.get("agent", "system")):
                appendix = (PLUGIN / entry["path"]).read_bytes()
                source = pinned_source(
                    PLUGIN / "upstream" / f"{entry['name']}.md", entry["name"]
                )
                self.assertEqual(appendix, body_after_frontmatter(source))
                self.assertEqual(entry["sha256"], hashlib.sha256(appendix).hexdigest())

    def test_rendered_appendices_fit_the_shared_cap(self) -> None:
        document = manifest()
        plugin = document["name"]
        total = 0
        for entry in document["system_appendix"]:
            body = (PLUGIN / entry["path"]).read_text(encoding="utf-8")
            block = (
                f'<gjc-plugin-system-appendix plugin="{plugin}" name="{entry["name"]}" '
                f'sha256="{entry["sha256"]}" authority="appendix-lower-than-system">\n'
                f"{body}\n</gjc-plugin-system-appendix>"
            )
            size = len(block.encode())
            self.assertLess(size, APPENDIX_LIMIT, entry["path"])
            total += size
        for entry in document["agent-appendix"]:
            body = (PLUGIN / entry["path"]).read_text(encoding="utf-8")
            block = (
                f'<gjc-plugin-agent-appendix plugin="{plugin}" agent="{entry["agent"]}" '
                f'name="{entry["name"]}" sha256="{entry["sha256"]}" '
                f'authority="appendix-lower-than-agent">\n{body}\n'
                f"</gjc-plugin-agent-appendix>"
            )
            size = len(block.encode())
            self.assertLess(size, APPENDIX_LIMIT, entry["path"])
            total += size
        self.assertLess(total, AGENT_TOTAL_LIMIT)
        self.assertGreater(total, 20_000)

    def test_no_excluded_skill_in_plugin_directory(self) -> None:
        for path in PLUGIN.rglob("*"):
            relative = path.relative_to(PLUGIN).as_posix()
            text = path.read_text(encoding="utf-8") if path.is_file() else ""
            for name in EXCLUDED:
                with self.subTest(path=relative, excluded=name):
                    self.assertNotIn(name, relative)
                    if path.name == "gajae-plugin.json":
                        self.assertNotIn(name, text)

    def test_on_demand_copies_are_full_upstream_files(self) -> None:
        for relative, blob in ON_DEMAND.items():
            with self.subTest(path=relative):
                self.assertEqual(git_blob_id((KIT_ROOT / relative).read_bytes()), blob)

    def test_typescript_fragment_is_exactly_the_upstream_body(self) -> None:
        source = pinned_source(
            OVERLAYS / "upstream/typescript-best-practices.md",
            "typescript-best-practices",
        )
        fragment = (OVERLAYS / "typescript-best-practices.md").read_bytes()
        self.assertEqual(fragment, body_after_frontmatter(source))
        fragments = {
            path.relative_to(OVERLAYS).as_posix()
            for path in OVERLAYS.rglob("*.md")
            if path.name != "README.md"
        }
        self.assertEqual(
            fragments,
            {
                "typescript-best-practices.md",
                "upstream/typescript-best-practices.md",
            },
        )


if __name__ == "__main__":
    unittest.main()
