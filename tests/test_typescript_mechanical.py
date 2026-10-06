from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
ASSET_SOURCE = KIT / "typescript"

BUN = os.environ.get("GAJAESTACK_BUN", "")
NODE_MODULES = os.environ.get("GAJAESTACK_TS_NODE_MODULES", "")
MISSING_PREREQS = [
    name
    for name, value in (
        ("GAJAESTACK_BUN", BUN),
        ("GAJAESTACK_TS_NODE_MODULES", NODE_MODULES),
    )
    if not value
]
PREREQ_REASON = (
    "real native prerequisites are passed via environment and are absent; missing: "
    + ", ".join(MISSING_PREREQS)
)
NATIVE_TOOLS = not MISSING_PREREQS
NODE_MODULES_PATH = Path(NODE_MODULES).resolve() if NODE_MODULES else None

TIMEOUT = 180

GOOD_TS = 'export const answer: number = 42;\n'
TYPE_ERROR_TS = 'export const wrong: number = "not a number";\n'
LINT_ERROR_TS = "export function observe(): void {\n\tdebugger;\n}\n"

ENTRY_PATH = ".gajaestack/typescript/check.ts"
USAGE_TEXT = "usage: bun .gajaestack/typescript/check.ts [--quick]"


def toml_list(items: list[str]) -> str:
    return "[" + ", ".join(f'"{item}"' for item in items) + "]"


def routing_text(
    *,
    selected: list[str] | None = None,
    required: list[str] | None = None,
    typecheck: bool = True,
    lint: bool = True,
    paths: list[str] | None = None,
) -> str:
    selected = ["typescript", "typescript-guard"] if selected is None else selected
    required = ["ts-typecheck", "ts-lint"] if required is None else required
    paths = ["src"] if paths is None else paths
    return (
        f"required = {toml_list(required)}\n"
        "\n"
        "[fact]\n"
        "schema_version = 1\n"
        f"selected_components = {toml_list(selected)}\n"
        "\n"
        "[typescript]\n"
        "schema_version = 1\n"
        f"typecheck = {'true' if typecheck else 'false'}\n"
        f"lint = {'true' if lint else 'false'}\n"
        'tsconfig = "tsconfig.json"\n'
        'biome_config = "biome.json"\n'
        f"paths = {toml_list(paths)}\n"
    )


def build_consumer(
    root: Path,
    *,
    routing: str | None | object = ...,
    sources: dict[str, str] | None = None,
    include: tuple[str, ...] = ("src",),
    bunfig: bool = False,
    sentinel: bool = False,
    failing: bool = False,
    tools: tuple[str, ...] = ("tsc", "biome"),
) -> None:
    """Create an isolated consumer with adopted assets at .gajaestack/typescript."""
    root = Path(root)
    assets = root / ".gajaestack" / "typescript"
    assets.mkdir(parents=True)
    for name in ("check.ts", "preload.ts", "tsconfig.json"):
        shutil.copy(ASSET_SOURCE / name, assets / name)
    if routing is None:
        pass
    elif routing is ...:
        (root / ".gajaestack" / "routing.toml").write_text(routing_text(), encoding="utf-8")
    else:
        (root / ".gajaestack" / "routing.toml").write_text(routing, encoding="utf-8")

    src = root / "src"
    src.mkdir()
    for name, body in (sources or {"index.ts": GOOD_TS}).items():
        (src / name).write_text(body, encoding="utf-8")

    project = {
        "compilerOptions": {
            "strict": True,
            "noEmit": True,
            "target": "ES2024",
            "module": "ESNext",
            "moduleResolution": "Bundler",
            "skipLibCheck": True,
            "types": [],
        },
        "include": list(include),
    }
    (root / "tsconfig.json").write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    (root / "biome.json").write_text(
        json.dumps(
            {"linter": {"enabled": True}, "formatter": {"enabled": False}}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )

    bins = root / "node_modules" / ".bin"
    bins.mkdir(parents=True)
    for tool in ("tsc", "biome"):
        if tool in tools:
            (bins / tool).symlink_to(NODE_MODULES_PATH / ".bin" / tool)

    if bunfig:
        (root / "bunfig.toml").write_text(
            '[test]\npreload = ["./.gajaestack/typescript/preload.ts"]\n', encoding="utf-8"
        )
    if sentinel:
        (root / "sentinel.test.ts").write_text(
            'import { writeFileSync } from "node:fs";\n'
            'import { test } from "bun:test";\n'
            "\n"
            'writeFileSync(`${import.meta.dir}/sentinel.txt`, "imported");\n'
            "\n"
            'test("sentinel ran", () => {});\n',
            encoding="utf-8",
        )
    if failing:
        (root / "failing.test.ts").write_text(
            'import { test } from "bun:test";\n'
            "\n"
            'test("native failure", () => {\n'
            '\tthrow new Error("deliberate native test failure");\n'
            "});\n",
            encoding="utf-8",
        )


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT,
        check=False,
    )


def run_entry(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run([BUN, ENTRY_PATH, *args], root)


def run_guard(root: Path) -> subprocess.CompletedProcess[str]:
    return _run([BUN, "test"], root)


def run_tool(root: Path, tool: str, *args: str) -> subprocess.CompletedProcess[str]:
    return _run([BUN, str(root / "node_modules" / ".bin" / tool), *args], root)


def direct_typecheck(root: Path) -> subprocess.CompletedProcess[str]:
    return run_tool(
        root, "tsc", "--noEmit", "--incremental", "false", "--project", str(root / "tsconfig.json")
    )


def direct_show_config(root: Path) -> subprocess.CompletedProcess[str]:
    return run_tool(root, "tsc", "--project", str(root / "tsconfig.json"), "--showConfig")


def direct_lint(root: Path) -> subprocess.CompletedProcess[str]:
    extensions = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"}
    files = sorted(
        str(path)
        for path in (root / "src").rglob("*")
        if path.is_file() and path.suffix in extensions
    )
    return run_tool(root, "biome", "lint", f"--config-path={root / 'biome.json'}", *files)


def combined(process: subprocess.CompletedProcess[str]) -> str:
    return process.stdout + process.stderr


@unittest.skipUnless(NATIVE_TOOLS, PREREQ_REASON)
class NativeConsumerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not NATIVE_TOOLS:
            return
        missing = [
            str(NODE_MODULES_PATH / ".bin" / tool)
            for tool in ("tsc", "biome")
            if not (NODE_MODULES_PATH / ".bin" / tool).exists()
        ]
        if missing:
            raise AssertionError(
                f"GAJAESTACK_TS_NODE_MODULES does not provide required local executables: {missing}"
            )
        if os.sep in BUN and not Path(BUN).exists():
            raise AssertionError(f"GAJAESTACK_BUN does not exist: {BUN}")


class TypeScriptCheckEntryTests(NativeConsumerTestCase):
    def test_completion_clean_pass_and_quick_lint_only(self) -> None:
        build_consumer(self.root)
        full = run_entry(self.root)
        text = combined(full)
        self.assertEqual(full.returncode, 0, text)
        typecheck = re.search(r"Typecheck: (\d+) project files", text)
        lint = re.search(r"Lint: (\d+) selected source files", text)
        self.assertIsNotNone(typecheck, text)
        self.assertIsNotNone(lint, text)
        self.assertGreater(int(typecheck.group(1)), 0, text)
        self.assertGreater(int(lint.group(1)), 0, text)

        quick = run_entry(self.root, "--quick")
        quick_text = combined(quick)
        self.assertEqual(quick.returncode, 0, quick_text)
        quick_lint = re.search(r"Lint: (\d+) selected source files", quick_text)
        self.assertIsNotNone(quick_lint, quick_text)
        self.assertNotIn("Typecheck:", quick_text)

    def test_type_failure_matches_native_status_and_fails_fast(self) -> None:
        build_consumer(
            self.root,
            sources={"index.ts": GOOD_TS, "bad.ts": TYPE_ERROR_TS, "bad-lint.ts": LINT_ERROR_TS},
        )
        native = direct_typecheck(self.root)
        self.assertNotEqual(native.returncode, 0, combined(native))
        skipped = direct_lint(self.root)
        self.assertNotEqual(skipped.returncode, 0, combined(skipped))

        entry = run_entry(self.root)
        text = combined(entry)
        self.assertEqual(entry.returncode, native.returncode, text)
        self.assertIn("error TS", text)
        self.assertIn("Typecheck:", text)
        self.assertNotIn("Lint:", text)

    def test_lint_failure_matches_native_status_in_quick_mode(self) -> None:
        build_consumer(self.root, sources={"index.ts": GOOD_TS, "bad-lint.ts": LINT_ERROR_TS})
        native = direct_lint(self.root)
        self.assertNotEqual(native.returncode, 0, combined(native))

        entry = run_entry(self.root, "--quick")
        text = combined(entry)
        self.assertEqual(entry.returncode, native.returncode, text)
        self.assertNotEqual(entry.returncode, 0, text)
        self.assertIn("bad-lint", text)
        self.assertIn("Lint:", text)
        self.assertNotIn("Typecheck:", text)

    def test_missing_or_malformed_config_rejected(self) -> None:
        build_consumer(self.root, routing=None)
        missing = run_entry(self.root)
        self.assertEqual(missing.returncode, 2, combined(missing))
        self.assertIn("gajaestack:", combined(missing))

        (self.root / ".gajaestack" / "routing.toml").write_text("[[[ not toml", encoding="utf-8")
        malformed = run_entry(self.root)
        self.assertEqual(malformed.returncode, 2, combined(malformed))
        self.assertIn("gajaestack:", combined(malformed))

    def test_missing_local_executable_reports_127(self) -> None:
        for missing_tool in ("biome", "tsc"):
            with self.subTest(missing=missing_tool):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    build_consumer(root)
                    (root / "node_modules" / ".bin" / missing_tool).unlink()
                    process = run_entry(root)
                    text = combined(process)
                    self.assertEqual(process.returncode, 127, text)
                    self.assertIn("missing executable:", text)
                    if missing_tool == "tsc":
                        self.assertNotIn("Typecheck:", text)
                    else:
                        self.assertIn("Typecheck:", text)
                        self.assertNotIn("Lint:", text)

    def test_unselected_typescript_component_runs_no_checks(self) -> None:
        build_consumer(self.root, routing=routing_text(selected=["routing"]))
        process = run_entry(self.root)
        text = combined(process)
        self.assertEqual(process.returncode, 2, text)
        self.assertIn("selected component typescript", text)
        self.assertNotIn("Typecheck:", text)
        self.assertNotIn("Lint:", text)
        self.assertNotIn("no coverage", text)

    def test_quick_with_lint_unselected_reports_no_coverage(self) -> None:
        build_consumer(self.root, routing=routing_text(lint=False))
        process = run_entry(self.root, "--quick")
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertIn("No checks selected for this mode; no coverage (not a check pass).", text)
        self.assertNotIn("Typecheck:", text)
        self.assertNotIn("Lint:", text)

    def test_empty_or_missing_lint_targets_rejected(self) -> None:
        cases = [
            (routing_text(paths=[]), "lint paths must not be empty"),
            (
                routing_text(paths=["src", "missing-scope"]),
                "lint path does not exist: missing-scope",
            ),
        ]
        for routing, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    build_consumer(root, routing=routing)
                    process = run_entry(root)
                    text = combined(process)
                    self.assertEqual(process.returncode, 2, text)
                    self.assertIn(expected, text)
                    self.assertIn("Typecheck:", text)
                    self.assertNotIn("Lint:", text)

    def test_tsconfig_without_inputs_reports_native_status(self) -> None:
        build_consumer(self.root, include=("no-such-dir",))
        native = direct_show_config(self.root)
        self.assertNotEqual(native.returncode, 0, combined(native))

        entry = run_entry(self.root)
        text = combined(entry)
        self.assertEqual(entry.returncode, native.returncode, text)
        self.assertIn("TS18003", text)
        self.assertNotIn("Lint:", text)

    def test_unknown_argument_rejected_with_usage(self) -> None:
        build_consumer(self.root)
        for args in (["--bogus"], ["--quick", "extra"]):
            with self.subTest(args=args):
                process = run_entry(self.root, *args)
                text = combined(process)
                self.assertEqual(process.returncode, 2, text)
                self.assertIn(USAGE_TEXT, text)


class TypeScriptPreloadGuardTests(NativeConsumerTestCase):
    def test_clean_guard_imports_tests_and_writes_sentinel(self) -> None:
        build_consumer(self.root, bunfig=True, sentinel=True)
        process = run_guard(self.root)
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertTrue((self.root / "sentinel.txt").exists(), text)
        self.assertRegex(text, r"\b1 pass\b")

    def test_failing_typecheck_blocks_test_imports(self) -> None:
        build_consumer(
            self.root,
            sources={"index.ts": GOOD_TS, "bad.ts": TYPE_ERROR_TS},
            bunfig=True,
            sentinel=True,
        )
        native = direct_typecheck(self.root)
        self.assertNotEqual(native.returncode, 0, combined(native))

        process = run_guard(self.root)
        text = combined(process)
        self.assertEqual(process.returncode, native.returncode, text)
        self.assertFalse((self.root / "sentinel.txt").exists(), text)
        self.assertNotIn("sentinel ran", text)
        self.assertIn("error TS", text)

    def test_native_test_failure_surfaces_while_guard_passes(self) -> None:
        build_consumer(self.root, bunfig=True, sentinel=True, failing=True)
        process = run_guard(self.root)
        text = combined(process)
        self.assertNotEqual(process.returncode, 0, text)
        self.assertTrue((self.root / "sentinel.txt").exists(), text)
        self.assertIn("deliberate native test failure", text)

    def test_guard_refuses_without_explicit_binding(self) -> None:
        cases = [
            (
                routing_text(selected=["typescript"]),
                "Bun preload requires explicit typescript-guard selection",
            ),
            (
                routing_text(selected=["typescript-guard"]),
                "selected component typescript",
            ),
            (
                routing_text(
                    selected=["typescript", "typescript-guard"], required=["ts-typecheck"]
                ),
                "preload checks must be explicitly listed in required",
            ),
            (
                routing_text(typecheck=False, lint=False),
                "required Bun preload has no selected checks",
            ),
            (
                routing_text(typecheck=False, lint=True),
                "preload checks must be explicitly listed in required",
            ),
        ]
        for routing, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    build_consumer(root, routing=routing, bunfig=True, sentinel=True)
                    process = run_guard(root)
                    text = combined(process)
                    self.assertEqual(process.returncode, 2, text)
                    self.assertIn(expected, text)
                    self.assertFalse((root / "sentinel.txt").exists(), text)
                    self.assertNotIn("Typecheck:", text)
                    self.assertNotIn("Lint:", text)

    def test_missing_config_blocks_test_imports(self) -> None:
        build_consumer(self.root, routing=None, bunfig=True, sentinel=True)
        process = run_guard(self.root)
        text = combined(process)
        self.assertEqual(process.returncode, 2, text)
        self.assertIn("gajaestack:", text)
        self.assertFalse((self.root / "sentinel.txt").exists(), text)


class TypeScriptAssetContractTests(unittest.TestCase):
    def test_assets_declare_no_python_runtime_dependency(self) -> None:
        for name in ("check.ts", "preload.ts", "tsconfig.json"):
            text = (ASSET_SOURCE / name).read_text(encoding="utf-8")
            self.assertNotIn("python", text.lower(), f"{name} must not require a Python runtime")

    def test_entry_usage_names_gajaestack_typescript_destination(self) -> None:
        text = (ASSET_SOURCE / "check.ts").read_text(encoding="utf-8")
        self.assertIn(ENTRY_PATH, text)
        self.assertIn("usage:", text)
        self.assertIn("[--quick]", text)


if __name__ == "__main__":
    unittest.main()
