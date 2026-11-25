"""Vendored pstack role sets stay byte-identical to their upstream files.

Each full copy is anchored to its git blob id. Unchanged files still match
revision 12d587dfb20741cafc376c42c696c5f6e2a64487. Files refreshed from
c742dd61706f or 005d8f6e8ec0 use that revision's blob id. Derived bodies are compared with
the anchored full copy, so the test needs no network. LOCAL_EDITS lists the
few files changed here on purpose, each with its pinned upstream blob.
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
    "correct",
    "principle-sequence-verifiable-units",
    "principle-attack-the-premise",
    "principle-build-the-lever",
    "principle-make-operations-idempotent",
    "principle-separate-before-serializing-shared-state",
    "principle-explain-the-number",
    "principle-minimize-reader-load",
)
SYSTEM = ("unslop",)
OWNED_SYSTEM = ("loc-polsia",)
AGREED = {"executor": EXECUTOR}
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
    "create-formal-verification-skill",
    "maintain-formal-verification-skill",
    "statechart",
    "in-your-own-words",
)
APPENDIX_LIMIT = 8192
AGENT_TOTAL_LIMIT = 32768

# Git blob ids of upstream pstack files at the pinned revision.
SKILL_BLOBS = {
    "no-comments": "1789564454c627cb8d4ee8580822d7e368cef122",
    "principle-boundary-discipline": "95b2209ce7d15ddbca7c2bf6ef3626ffdc8d595e",
    "principle-encode-lessons-in-structure": "4a96f77fe70e36cb030f9c5efa142f66877bf58a",
    "principle-fix-root-causes": "b5e41168eb5944f583cf1d225e39552a48473dfe",
    "principle-model-the-domain": "88ba012f47bd51b2db0758c657610d56f871e1ba",
    "principle-prove-it-works": "1c293b3c3ad0f7cb021858b17e7588d30a0a1acb",
    "principle-sequence-verifiable-units": "3998185a29f287f6f30f0909c98ac4e2af5ddb97",
    "principle-subtract-before-you-add": "b8740ba6f06922d8e7ef3b23f9fb16e0fc4a876f",
    "principle-test-behavior-not-implementation": "094b9427aa64294afd64d83e9495a5ee303631e0",
    "principle-type-system-discipline": "852aab0340246c0d0dfd59ea6be962ce40a31272",
    "unslop": "583fe48499c8f8f71bd2deef4228d1f0129c03c7",
    "principle-attack-the-premise": "5ee25b02e701ca3e304122248a412d2372ab097c",
    "principle-build-the-lever": "8f9b5a931b10839ad5ef71ce43d5411c2c7a1f6b",
    "principle-make-operations-idempotent": "7c61fe4b203bfae1de7db570af4c57fd0ba0a3d3",
    "principle-separate-before-serializing-shared-state": "6a4c3b876b694097a12003996588f557d2b55d0e",
    "principle-explain-the-number": "7ff00fcf8805872cfb500308ed2bdf5fdd5d6b8b",
    "principle-minimize-reader-load": "19dd4876d6e92c04caa2729d37ac87ac126d20ed",
    "correct": "c45e06f48a0982ae19f92c6e83a8cd05988097a3",
    "create-verification-skill": "140d033a001e8d27acd14b06004506c43053b199",
    "maintain-verification-skill": "a2680b91fead45a0b4963d8c367a854956bea59d",
    "typescript-best-practices": "e1e5aa7c97ed39c425d60d933a96424a3f14539e",
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
    "skills/create-formal-verification-skill/SKILL.md": "92f7aa4fa966b857dd7fcc994b3c59650767c878",
    "skills/maintain-formal-verification-skill/SKILL.md": "5d2f7f2228a3b771ca5b03124fc265ddfc53c5fc",
    "skills/in-your-own-words/SKILL.md": "4b2a476a9017863032c8dba9d12f0a2026943292",
    "skills/blast-radius/SKILL.md": "1f5c95140597b8aa42fadf165e1aa0bca01639ff",
    "skills/tdd/SKILL.md": "ca6f24c963001d9d518db2936dfe3d12f29b4e94",
    "skills/benchmark-checklist/SKILL.md": "88546fa684c003625a13d61b975ced97b8fcb90e",
    "skills/no-comments/comment-sicko.md": "14c2402f3d8c81b39d75747d6eb892f343e6a903",
}

# Files edited here on purpose: path -> (upstream blob, local blob, text removed).
LOCAL_EDITS = {
    "skills/no-comments/SKILL.md": (
        "1789564454c627cb8d4ee8580822d7e368cef122",
        "6be56945b0b494e877c68ec7d7d5f5ba028c7731",
        "Pick each subagent's reasoning level for the job, per the Subagents "
        "section of the **poteto-mode** skill.",
    ),
}
# Appendix bodies that differ from the upstream body after the frontmatter.
BODY_EDITS = {
    "principle-type-system-discipline": (b"", b"\nDo not lie to the compiler.\n"),
    "principle-explain-the-number": (
        b"[benchmark-checklist](../benchmark-checklist/SKILL.md) skill",
        b"**benchmark-checklist** skill",
    ),
}


STATECHART_BLOBS = {
    "skills/statechart/SKILL.md": "18d653a810dfbb3ea35a6ed88bcfe8cb84f0a893",
    "skills/statechart/references/render.md": "5ef0519d6f7ae97ef7befceaf174f94f52dd42f5",
    "skills/statechart/scripts/backends/cfg.ts": "dec8b2f6671f2d110cd880f7af8d2c714cdf23a3",
    "skills/statechart/scripts/backends/mermaid.ts": "21ad39cb1efe72e4507df5c7599f32596612545f",
    "skills/statechart/scripts/backends/plain-text.ts": "1ece33e8c45995493e84bc948ad613fce15481ab",
    "skills/statechart/scripts/backends/report.ts": "62e2a853375a1141491ef54fed8fd0d81a1bcd3c",
    "skills/statechart/scripts/frontends/config.ts": "4f6ade5a9a74c8e74a58125dc7a5d035ea2ca36b",
    "skills/statechart/scripts/frontends/dot.ts": "09d5481e70d9cf911dc16ddf655c91c197ff1fac",
    "skills/statechart/scripts/frontends/marks.ts": "9b1eda59f12861b8fb981d6046741417cd1be667",
    "skills/statechart/scripts/frontends/messages.ts": "e835b065e775a1b822eede5b1515d0401ce8356b",
    "skills/statechart/scripts/frontends/spec.ts": "3fbe34f1a6b344c56cfd5afba3b90fe9a397c405",
    "skills/statechart/scripts/frontends/trace.ts": "43387c12b314c343d7a046de2fd095a3950b0026",
    "skills/statechart/scripts/frontends/value.ts": "d73ddec9ee3fa6077c644625002707a96d0938a1",
    "skills/statechart/scripts/frontends/verdict.ts": "4f2ddd925332773b68918c40e62fc79a3a32571b",
    "skills/statechart/scripts/frontends/view.ts": "ed8a1b5f9f0b4104a901a966bdfd66f13102d5ce",
    "skills/statechart/scripts/ir.ts": "80fd403fe3c231b0986f239ba8c74a60b52c05f7",
    "skills/statechart/scripts/janitor.ts": "5e69fb316c9e6bd4bc1de68781b43c345381188b",
    "skills/statechart/scripts/kill.ts": "014d7c35049a8786359264cb4489c0c5e0a7ff1d",
    "skills/statechart/scripts/package.json": "16bd68507bac879f00d9efb90f6a5df689dbbd3a",
    "skills/statechart/scripts/passes/annotate.ts": "7d95d4fb57311c26bbbaca42eb283421f56140e0",
    "skills/statechart/scripts/passes/label.ts": "cc8c197726137a0875462702e39cd07cbf55d547",
    "skills/statechart/scripts/passes/lift.ts": "15db7deda016faee9c0da33c2c419be51e528ed6",
    "skills/statechart/scripts/passes/loop-check.ts": "7e5a3825adde46e8a625ad9e167cb0ce6b712174",
    "skills/statechart/scripts/passes/paths.ts": "632a5c4ae6d6101c89f46803605c09b6a96f9b6f",
    "skills/statechart/scripts/passes/reach.ts": "d5b6a521dc970f888d615d41caf692d0f7bcb2ec",
    "skills/statechart/scripts/passes/region-check.ts": "ae499230f5ba441d704386bd24df73cad3c92af7",
    "skills/statechart/scripts/passes/regions.ts": "bb7aea062410be42c25c779ca748c2b52c3e5a82",
    "skills/statechart/scripts/pipeline.ts": "f12a2e07f6e4fe283cfd1b2fc0d3f83dd3d75758",
    "skills/statechart/scripts/run.ts": "45e13dcb4d4ee41d4437ed64e3177fe1a412ae56",
    "skills/statechart/scripts/statechart": "7d3aeb8c219bf20aea4cbc321892fca9cbd582f1",
    "skills/statechart/scripts/statechart.ts": "43ee983edfa7b1fa76ddab07e0e99cba897373b9",
    "skills/statechart/scripts/tsconfig.json": "9b16905d0a049715f942bdbe4bf3a3a80be02bad",
    "skills/statechart/scripts/worker.ts": "9559314668f6573e17db7c278d05f5776b235ebc",
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
        self.assertEqual([entry["name"] for entry in system], list(SYSTEM + OWNED_SYSTEM))
        self.assertEqual(document["version"], "0.1.5")
        for entry in system:
            self.assertNotIn("agent", entry)
            self.assertNotIn("content", entry)
            self.assertEqual(entry["path"], f"appendices/system/{entry['name']}.md")
        declared: dict[str, list[str]] = {agent: [] for agent in AGREED}
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
            {f"{name}.md" for name in set(EXECUTOR) | set(SYSTEM)},
        )

    def test_appendix_bodies_match_upstream_after_frontmatter(self) -> None:
        document = manifest()
        for entry in document["system_appendix"] + document["agent-appendix"]:
            with self.subTest(name=entry["name"], agent=entry.get("agent", "system")):
                appendix = (PLUGIN / entry["path"]).read_bytes()
                self.assertEqual(entry["sha256"], hashlib.sha256(appendix).hexdigest())
                if entry["name"] in OWNED_SYSTEM:
                    self.assertNotIn(
                        f"{entry['name']}.md",
                        {path.name for path in (PLUGIN / "upstream").iterdir()},
                    )
                    self.assertIn(b"Canonical doctrine:", appendix)
                    continue
                source = pinned_source(
                    PLUGIN / "upstream" / f"{entry['name']}.md", entry["name"]
                )
                expected = body_after_frontmatter(source)
                if entry["name"] in BODY_EDITS:
                    old, new = BODY_EDITS[entry["name"]]
                    if old:
                        self.assertEqual(expected.count(old), 1)
                        expected = expected.replace(old, new)
                    else:
                        expected = expected + new
                self.assertEqual(appendix, expected)

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
        self.assertGreater(total, 19_000)

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

    def test_local_edits_are_pinned_and_remove_only_their_text(self) -> None:
        for relative, (_upstream, local, removed) in LOCAL_EDITS.items():
            with self.subTest(path=relative):
                data = (KIT_ROOT / relative).read_bytes()
                self.assertEqual(git_blob_id(data), local)
                self.assertNotIn(removed.encode(), data)
                self.assertNotIn(b"poteto-mode", data)

    def test_statechart_runtime_matches_upstream_and_omits_the_corpus(self) -> None:
        root = KIT_ROOT / "skills/statechart"
        found = {
            path.relative_to(KIT_ROOT).as_posix()
            for path in root.rglob("*")
            if path.is_file() and path.name != "HOST.md"
        }
        self.assertEqual(found, set(STATECHART_BLOBS))
        for relative, expected in STATECHART_BLOBS.items():
            with self.subTest(path=relative):
                self.assertEqual(git_blob_id((KIT_ROOT / relative).read_bytes()), expected)
                self.assertNotIn("/scripts/test/", relative)

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
