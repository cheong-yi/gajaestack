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
GIT_AVAILABLE = shutil.which("git") is not None
REQUIRES_GIT_REASON = (
    PREREQ_REASON
    if not NATIVE_TOOLS
    else "git executable is required for quick-mode tests"
)
requires_native_git = unittest.skipUnless(
    NATIVE_TOOLS and GIT_AVAILABLE, REQUIRES_GIT_REASON
)

GOOD_TS = 'export const answer: number = 42;\n'
TYPE_ERROR_TS = 'export const wrong: number = "not a number";\n'
LINT_ERROR_TS = "export function observe(): void {\n\tdebugger;\n}\n"

ENTRY_PATH = ".gajaestack/typescript/check.ts"
USAGE_TEXT = "usage: bun .gajaestack/typescript/check.ts [--quick] [--timing]"


def toml_list(items: list[str]) -> str:
    return "[" + ", ".join(f'"{item}"' for item in items) + "]"


def routing_text(
    *,
    selected: list[str] | None = None,
    required: list[str] | None = None,
    typecheck: bool = True,
    lint: bool = True,
    paths: list[str] | None = None,
    biome_config: str = "biome.json",
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
        f'biome_config = "{biome_config}"\n'
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


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT,
        check=False,
        env=env,
    )


def run_entry(root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return _run([BUN, ENTRY_PATH, *args], root, env=env)


def run_guard(root: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return _run([BUN, "test"], root, env=env)


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


def git_env() -> dict[str, str]:
    """Isolated git configuration so host identity or hooks cannot skew status."""
    env = dict(os.environ)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    return env


def git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd, env=git_env())


def git_init_baseline(root: Path) -> None:
    """Commit the whole consumer state so quick mode starts from a clean status."""
    steps = (
        ("init", "-q"),
        ("add", "-A"),
        (
            "-c",
            "user.name=gajaestack-test",
            "-c",
            "user.email=gajaestack-tests@example.invalid",
            "commit",
            "-q",
            "-m",
            "baseline",
        ),
    )
    for args in steps:
        result = git(*args, cwd=root)
        if result.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed: {combined(result)}")


def tree_snapshot(root: Path) -> set[str]:
    """Files and directories under root except .git; index refresh is asserted separately."""
    return {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if ".git" not in path.relative_to(root).parts
    }


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
    def test_completion_clean_pass(self) -> None:
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

    @requires_native_git
    def test_lint_failure_matches_native_status_in_quick_mode(self) -> None:
        build_consumer(self.root, sources={"index.ts": GOOD_TS})
        git_init_baseline(self.root)
        (self.root / "src" / "bad-lint.ts").write_text(LINT_ERROR_TS, encoding="utf-8")
        native = direct_lint(self.root)
        self.assertNotEqual(native.returncode, 0, combined(native))

        entry = run_entry(self.root, "--quick")
        text = combined(entry)
        self.assertEqual(entry.returncode, native.returncode, text)
        self.assertNotEqual(entry.returncode, 0, text)
        self.assertIn("bad-lint", text)
        self.assertIn("Lint: 1 selected source files", text)
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
        for args in (
            ["--bogus"],
            ["--quick", "extra"],
            ["--quick", "--quick"],
            ["--timing", "--timing"],
        ):
            with self.subTest(args=args):
                process = run_entry(self.root, *args)
                text = combined(process)
                self.assertEqual(process.returncode, 2, text)
                self.assertIn(USAGE_TEXT, text)

    @requires_native_git
    def test_quick_lints_only_changed_declared_files(self) -> None:
        build_consumer(self.root, sources={"index.ts": GOOD_TS, "other.ts": GOOD_TS})
        git_init_baseline(self.root)
        (self.root / "src" / "index.ts").write_text(GOOD_TS + "// touched\n", encoding="utf-8")
        index_state = (self.root / ".git" / "index").stat().st_mtime_ns
        process = run_entry(self.root, "--quick")
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        lint = re.search(r"Lint: (\d+) selected source files", text)
        self.assertIsNotNone(lint, text)
        self.assertEqual(int(lint.group(1)), 1, text)
        self.assertNotIn("Typecheck:", text)
        self.assertNotIn("Quick scope expanded", text)
        self.assertEqual(
            index_state,
            (self.root / ".git" / "index").stat().st_mtime_ns,
            "quick mode must not refresh the git index",
        )

    @requires_native_git
    def test_quick_without_changed_files_reports_no_coverage(self) -> None:
        build_consumer(self.root, sources={"index.ts": GOOD_TS, "other.ts": GOOD_TS})
        git_init_baseline(self.root)
        process = run_entry(self.root, "--quick")
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertIn("No changed files; nothing to check.", text)
        self.assertIn("No coverage; this no-op is not a lint pass.", text)
        self.assertNotIn("Quick scope expanded", text)
        self.assertNotIn("Lint:", text)
        self.assertNotIn("Typecheck:", text)

    @requires_native_git
    def test_quick_ignores_changed_files_outside_declared_paths(self) -> None:
        build_consumer(self.root, sources={"index.ts": GOOD_TS, "other.ts": GOOD_TS})
        git_init_baseline(self.root)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "note.ts").write_text(LINT_ERROR_TS, encoding="utf-8")
        process = run_entry(self.root, "--quick")
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertIn(
            "No changed files match the selected lint paths; nothing to check.", text
        )
        self.assertIn("No coverage; this no-op is not a lint pass.", text)
        self.assertNotIn("Quick scope expanded", text)
        self.assertNotIn("Lint:", text)

    @requires_native_git
    def test_quick_expands_to_full_scope_on_invalidating_changes(self) -> None:
        sources = {"index.ts": GOOD_TS, "other.ts": GOOD_TS}
        cases = (
            "routing facts",
            "biome config",
            "checker script",
            "biome config dependency",
            "unenumerable biome config",
        )
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    routing = (
                        routing_text(biome_config="biome.jsonc")
                        if case == "unenumerable biome config"
                        else routing_text()
                    )
                    build_consumer(root, routing=routing, sources=sources)
                    if case == "biome config dependency":
                        (root / "biome.json").write_text(
                            json.dumps(
                                {
                                    "linter": {"enabled": True},
                                    "formatter": {"enabled": False},
                                    "extends": ["./biome.base.json"],
                                }
                            )
                            + "\n",
                            encoding="utf-8",
                        )
                        (root / "biome.base.json").write_text("{}\n", encoding="utf-8")
                    if case == "unenumerable biome config":
                        (root / "biome.jsonc").write_text(
                            "// comments keep JSON.parse from reading this config\n"
                            '{"linter": {"enabled": true}, "formatter": {"enabled": false}}\n',
                            encoding="utf-8",
                        )
                    git_init_baseline(root)
                    if case == "routing facts":
                        target = root / ".gajaestack" / "routing.toml"
                        target.write_text(
                            target.read_text(encoding="utf-8") + "# touched\n",
                            encoding="utf-8",
                        )
                        trigger = ".gajaestack/routing.toml"
                    elif case == "biome config":
                        target = root / "biome.json"
                        target.write_text(
                            json.dumps(json.loads(target.read_text(encoding="utf-8")), indent=4)
                            + "\n",
                            encoding="utf-8",
                        )
                        trigger = "biome.json"
                    elif case == "checker script":
                        target = root / ".gajaestack" / "typescript" / "check.ts"
                        target.write_text(
                            target.read_text(encoding="utf-8") + "\n// touched\n",
                            encoding="utf-8",
                        )
                        trigger = ".gajaestack/typescript/check.ts"
                    elif case == "biome config dependency":
                        (root / "biome.base.json").write_text(
                            '{"linter": {"enabled": true}}\n', encoding="utf-8"
                        )
                        trigger = "biome.base.json"
                    else:
                        (root / "src" / "index.ts").write_text(
                            GOOD_TS + "// touched\n", encoding="utf-8"
                        )
                        trigger = "unenumerable Biome config dependencies"
                    process = run_entry(root, "--quick")
                    text = combined(process)
                    self.assertEqual(process.returncode, 0, text)
                    self.assertIn("Quick scope expanded to full selected scope", text)
                    self.assertIn(trigger, text)
                    self.assertIn("Lint: 2 selected source files", text)
                    self.assertNotIn("Typecheck:", text)

    @requires_native_git
    def test_quick_expands_on_changed_nested_biome_named_config(self) -> None:
        build_consumer(self.root, sources={"index.ts": GOOD_TS, "other.ts": GOOD_TS})
        nested = self.root / "src" / "nested"
        nested.mkdir()
        (nested / "biome.json").write_text("{}\n", encoding="utf-8")
        git_init_baseline(self.root)
        (nested / "biome.json").write_text('{"linter": {"enabled": true}}\n', encoding="utf-8")
        process = run_entry(self.root, "--quick")
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertIn("Quick scope expanded to full selected scope", text)
        self.assertIn("src/nested/biome.json", text)
        self.assertIn("Lint: 2 selected source files", text)

    @requires_native_git
    def test_quick_expands_when_a_biome_named_config_is_renamed_away(self) -> None:
        build_consumer(self.root, sources={"index.ts": GOOD_TS, "other.ts": GOOD_TS})
        nested = self.root / "src" / "nested"
        nested.mkdir()
        (nested / "biome.json").write_text("{}\n", encoding="utf-8")
        git_init_baseline(self.root)
        moved = git("mv", "src/nested/biome.json", "src/nested/renamed.json", cwd=self.root)
        self.assertEqual(moved.returncode, 0, combined(moved))
        process = run_entry(self.root, "--quick")
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertIn("Quick scope expanded to full selected scope", text)
        self.assertIn("src/nested/biome.json", text)
        self.assertIn("Lint: 2 selected source files", text)

    @requires_native_git
    def test_quick_expands_on_local_plugin_dependency_change(self) -> None:
        build_consumer(self.root, sources={"index.ts": GOOD_TS, "other.ts": GOOD_TS})
        (self.root / "plugins").mkdir()
        (self.root / "plugins" / "local.grit").write_text(
            "pattern stale { `foo` }\n", encoding="utf-8"
        )
        (self.root / "biome.json").write_text(
            json.dumps(
                {
                    "linter": {"enabled": True},
                    "formatter": {"enabled": False},
                    "plugins": ["./plugins/local.grit"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        native = run_tool(
            self.root,
            "biome",
            "lint",
            f"--config-path={self.root / 'biome.json'}",
            str(self.root / "src" / "index.ts"),
        )
        self.assertNotEqual(native.returncode, 0, combined(native))
        git_init_baseline(self.root)
        (self.root / "plugins" / "local.grit").write_text(
            "pattern changed { `bar` }\n", encoding="utf-8"
        )
        process = run_entry(self.root, "--quick")
        text = combined(process)
        self.assertEqual(process.returncode, native.returncode, text)
        self.assertIn("Quick scope expanded to full selected scope", text)
        self.assertIn("plugins/local.grit", text)
        self.assertIn("Lint: 2 selected source files", text)
        self.assertIn("Grit", text)

    @requires_native_git
    def test_quick_and_timing_flags_combine(self) -> None:
        build_consumer(self.root, sources={"index.ts": GOOD_TS})
        git_init_baseline(self.root)
        process = run_entry(self.root, "--quick", "--timing")
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertIn("No changed files; nothing to check.", text)
        self.assertRegex(text, r"gajaestack timing: lint-scope files=0 status=0 elapsed_ms=\d+")
        self.assertNotIn("gajaestack timing: lint ", text)
        self.assertRegex(text, r"gajaestack timing: total status=0 elapsed_ms=\d+")

    def test_quick_without_git_fails_without_coverage_claim(self) -> None:
        build_consumer(self.root, sources={"index.ts": GOOD_TS})
        env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(self.root.parent))
        process = run_entry(self.root, "--quick", "--timing", env=env)
        text = combined(process)
        self.assertIn(process.returncode, (127, 128), text)
        self.assertIn("no Git fallback", text)
        self.assertNotIn("Lint:", text)
        self.assertNotIn("No coverage", text)
        self.assertNotIn("No changed files", text)
        self.assertRegex(
            process.stderr,
            rf"gajaestack timing: lint-scope status={process.returncode} elapsed_ms=\d+",
        )
        self.assertNotIn("gajaestack timing: lint ", process.stderr)
        self.assertRegex(
            process.stderr,
            rf"gajaestack timing: total status={process.returncode} elapsed_ms=\d+",
        )

    def test_timing_flag_reports_distinct_scope_and_check_phases(self) -> None:
        build_consumer(self.root, sources={"index.ts": GOOD_TS, "other.ts": GOOD_TS})
        before = tree_snapshot(self.root)
        process = run_entry(self.root, "--timing")
        after = tree_snapshot(self.root)
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertEqual(before, after, "timing runs must not write files")
        self.assertIn("Typecheck:", process.stdout)
        self.assertIn("Lint: 2 selected source files", process.stdout)
        self.assertNotIn("gajaestack timing:", process.stdout)
        self.assertRegex(
            process.stderr,
            r"gajaestack timing: typecheck-scope files=2 status=0 elapsed_ms=\d+",
        )
        self.assertRegex(
            process.stderr, r"gajaestack timing: typecheck files=2 status=0 elapsed_ms=\d+"
        )
        self.assertRegex(
            process.stderr, r"gajaestack timing: lint-scope files=2 status=0 elapsed_ms=\d+"
        )
        self.assertRegex(process.stderr, r"gajaestack timing: lint files=2 status=0 elapsed_ms=\d+")
        self.assertRegex(process.stderr, r"gajaestack timing: total status=0 elapsed_ms=\d+")

        clean_env = {
            key: value for key, value in os.environ.items() if key != "GAJAESTACK_TIMING"
        }
        plain = run_entry(self.root, env=clean_env)
        self.assertEqual(plain.returncode, 0, combined(plain))
        self.assertNotIn("gajaestack timing:", plain.stderr)

        env = dict(os.environ, GAJAESTACK_TIMING="1")
        via_env = run_entry(self.root, env=env)
        self.assertEqual(via_env.returncode, 0, combined(via_env))
        self.assertRegex(via_env.stderr, r"gajaestack timing: total status=0 elapsed_ms=\d+")

    def test_timing_reports_distinct_phases_on_native_failure(self) -> None:
        build_consumer(
            self.root,
            sources={"index.ts": GOOD_TS, "bad.ts": TYPE_ERROR_TS, "bad-lint.ts": LINT_ERROR_TS},
        )
        native = direct_typecheck(self.root)
        self.assertNotEqual(native.returncode, 0, combined(native))

        process = run_entry(self.root, "--timing")
        text = combined(process)
        self.assertEqual(process.returncode, native.returncode, text)
        self.assertIn("error TS", text)
        self.assertIn("Typecheck:", process.stdout)
        self.assertNotIn("Lint:", text)
        self.assertRegex(
            process.stderr, r"gajaestack timing: typecheck-scope files=3 status=0 elapsed_ms=\d+"
        )
        self.assertRegex(
            process.stderr,
            rf"gajaestack timing: typecheck files=3 status={native.returncode} elapsed_ms=\d+",
        )
        self.assertNotIn("gajaestack timing: lint-scope", process.stderr)
        self.assertNotIn("gajaestack timing: lint ", process.stderr)
        self.assertRegex(
            process.stderr,
            rf"gajaestack timing: total status={native.returncode} elapsed_ms=\d+",
        )


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

    def test_guard_timing_env_reports_phases_and_keeps_sentinel(self) -> None:
        build_consumer(self.root, bunfig=True, sentinel=True)
        env = dict(os.environ, GAJAESTACK_TIMING="1")
        process = run_guard(self.root, env=env)
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertTrue((self.root / "sentinel.txt").exists(), text)
        self.assertRegex(text, r"\b1 pass\b")
        self.assertRegex(
            text, r"gajaestack timing: typecheck-scope files=\d+ status=0 elapsed_ms=\d+"
        )
        self.assertRegex(
            text, r"gajaestack timing: typecheck files=\d+ status=0 elapsed_ms=\d+"
        )
        self.assertRegex(
            text, r"gajaestack timing: lint-scope files=\d+ status=0 elapsed_ms=\d+"
        )
        self.assertRegex(text, r"gajaestack timing: lint files=\d+ status=0 elapsed_ms=\d+")
        self.assertRegex(text, r"gajaestack timing: total status=0 elapsed_ms=\d+")

    def test_guard_timing_env_lint_failure_blocks_sentinel(self) -> None:
        build_consumer(
            self.root,
            sources={"index.ts": GOOD_TS, "bad-lint.ts": LINT_ERROR_TS},
            bunfig=True,
            sentinel=True,
        )
        native = direct_lint(self.root)
        self.assertNotEqual(native.returncode, 0, combined(native))

        env = dict(os.environ, GAJAESTACK_TIMING="1")
        process = run_guard(self.root, env=env)
        text = combined(process)
        self.assertEqual(process.returncode, native.returncode, text)
        self.assertFalse((self.root / "sentinel.txt").exists(), text)
        self.assertNotIn("sentinel ran", text)
        self.assertIn("bad-lint", text)
        self.assertRegex(text, r"gajaestack timing: lint-scope files=2 status=0 elapsed_ms=\d+")
        self.assertRegex(
            text,
            rf"gajaestack timing: lint files=2 status={native.returncode} elapsed_ms=\d+",
        )
        self.assertRegex(
            text, rf"gajaestack timing: total status={native.returncode} elapsed_ms=\d+"
        )


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
        self.assertIn("[--timing]", text)

    def test_entry_declares_timing_and_git_lock_contracts(self) -> None:
        text = (ASSET_SOURCE / "check.ts").read_text(encoding="utf-8")
        self.assertIn("GAJAESTACK_TIMING", text)
        self.assertIn("--no-optional-locks", text)
        self.assertIn("fatal: true", text)


if __name__ == "__main__":
    unittest.main()
