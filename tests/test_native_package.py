"""Acceptance for the shipped Bun package consumed from real repository bytes.

Unlike the source-mode fixture tests in ``test_typescript_mechanical.py`` (which
run a *copied* checker from ``.gajaestack/typescript`` as internal unit tests of
changed-file scope logic only, never as a consumer adoption path), every check
here runs through the packaged surface a consumer actually gets:

* the archive produced by ``bun pm pack --ignore-scripts`` from the repo itself,
* ``bun add --dev --exact --offline --ignore-scripts --backend=copyfile`` of that tarball,
* the package exports ``gajaestack/check``, ``gajaestack/preload`` and
  ``gajaestack/tsconfig`` (consumer ``extends``),
* the bin entry point ``bun run gajaestack-check [--quick] [--timing]``,
* the consumer ``bunfig.toml`` ``[test] preload = ["gajaestack/preload"]``.

Installs are ``--offline`` from local
tarballs, and tsc/Biome are symlinked from the env-provided
``GAJAESTACK_TS_NODE_MODULES`` toolchain (never stubbed or downloaded here).
Registry/proxy settings additionally reject ordinary remote package requests;
they are not a network sandbox for arbitrary subprocesses.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = KIT / "package.json"
README_PATH = KIT / "README.md"

BUN = os.environ.get("GAJAESTACK_BUN", "")
NODE_MODULES = os.environ.get("GAJAESTACK_TS_NODE_MODULES", "")
GJC = os.environ.get("GAJAESTACK_GJC", "")
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

TIMEOUT = 240
GIT_AVAILABLE = shutil.which("git") is not None
REQUIRES_GIT_REASON = (
    PREREQ_REASON if not NATIVE_TOOLS else "git executable is required for quick-mode tests"
)
requires_native_git = unittest.skipUnless(
    NATIVE_TOOLS and GIT_AVAILABLE, REQUIRES_GIT_REASON
)

# Reject ordinary registry/proxy requests in addition to native offline installs.
UNROUTABLE = "http://127.0.0.1:1/"

BIN_ENTRY = "gajaestack-check"
USAGE_TEXT = "usage: bun run gajaestack-check [--quick] [--timing]"
PACKAGE_NAME = "gajaestack"
PINNED_VERSION = "0.1.0"
UPGRADE_VERSION = "0.1.1"

GOOD_TS = 'export const answer: number = 42;\n'
OTHER_TS = 'export const other: number = 7;\n'
TYPE_ERROR_TS = 'export const wrong: number = "not a number";\n'
LINT_ERROR_TS = "export function observe(): void {\n\tdebugger;\n}\n"
UPGRADE_MARKER = "// gajaestack pinned upgrade marker 0.1.1"
UPGRADE_SKILL = "skills/type-discipline/SKILL.md"
SKILL_MARKER = "Staged prose marker distinguishing the packaged 0.1.1 artifact."
INSTALLED_SOURCE_MARKER = "// locally modified installed dependency source"

EXPECTED_EXPORTS = {
    "./check": "./typescript/check.ts",
    "./preload": "./typescript/preload.ts",
    "./tsconfig": "./typescript/tsconfig.json",
}
EXPECTED_BIN = {BIN_ENTRY: "./typescript/check.ts"}
EXPECTED_FILES = {
    "typescript/check.ts",
    "typescript/preload.ts",
    "typescript/tsconfig.json",
    "skills/*/SKILL.md",
    "python/routing/AGENTS.md",
    "docs/python-trial.md",
    "docs/scope-invariant.md",
    "AGENTS.md",
}
EXPECTED_MEMBERS = {
    "package/package.json",
    "package/README.md",
    "package/AGENTS.md",
    "package/docs/python-trial.md",
    "package/docs/scope-invariant.md",
    "package/python/routing/AGENTS.md",
    "package/skills/native-quality/SKILL.md",
    "package/skills/type-discipline/SKILL.md",
    "package/skills/verify-change/SKILL.md",
    "package/typescript/check.ts",
    "package/typescript/preload.ts",
    "package/typescript/tsconfig.json",
}
# Caches, private agent state, evidence trees and Python implementation are
# never shipped into the Bun package; static guidance under python/ is allowed.
FORBIDDEN_COMPONENTS = {
    ".git",
    ".gjc",
    ".ruff_cache",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "evidence",
}
IMPLEMENTATION_SUFFIXES = (".py", ".pyc", ".pyo", ".pyd")

FACT_TABLE = (
    "[fact]\n"
    "schema_version = 1\n"
    'selected_components = ["typescript", "typescript-guard"]\n'
    "\n"
)
TYPESCRIPT_TABLE = (
    "[typescript]\n"
    "schema_version = 1\n"
    "typecheck = true\n"
    "lint = true\n"
    'tsconfig = "tsconfig.json"\n'
    'biome_config = "biome.json"\n'
    'paths = ["src"]\n'
)
REQUIRED_LINE = 'required = ["ts-typecheck", "ts-lint"]\n\n'
ROUTING_TOML = REQUIRED_LINE + FACT_TABLE + TYPESCRIPT_TABLE
NO_FACT_ROUTING_TOML = REQUIRED_LINE + TYPESCRIPT_TABLE

SENTINEL_SOURCE = (
    'import { writeFileSync } from "node:fs";\n'
    'import { test } from "bun:test";\n'
    "\n"
    'writeFileSync(`${import.meta.dir}/sentinel.txt`, "imported");\n'
    "\n"
    'test("sentinel ran", () => {});\n'
)


def offline_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for every subprocess: remote registries and proxies unreachable."""
    env = dict(os.environ)
    env["BUN_CONFIG_REGISTRY"] = UNROUTABLE
    env["http_proxy"] = UNROUTABLE
    env["https_proxy"] = UNROUTABLE
    env["all_proxy"] = UNROUTABLE
    if extra:
        env.update(extra)
    return env


def _run(
    cmd: list[str], cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT,
        check=False,
        env=offline_env(env),
    )


def combined(process: subprocess.CompletedProcess[str]) -> str:
    return process.stdout + process.stderr


def pack_kit(source: Path, destination: Path) -> Path:
    """Pack ``source`` bytes into exactly one tarball inside ``destination``."""
    destination.mkdir(parents=True, exist_ok=True)
    process = _run(
        [BUN, "pm", "pack", "--ignore-scripts", "--destination", str(destination)], source
    )
    if process.returncode != 0:
        raise AssertionError(f"bun pm pack failed: {combined(process)}")
    tarballs = sorted(destination.glob("*.tgz"))
    if len(tarballs) != 1:
        raise AssertionError(f"expected one tarball in {destination}, found {tarballs}")
    return tarballs[0]


def archive_inventory(tarball: Path) -> tuple[list[tarfile.TarInfo], dict[str, bytes]]:
    with tarfile.open(tarball, "r:gz") as archive:
        members = archive.getmembers()
        payloads: dict[str, bytes] = {}
        for member in members:
            if not member.isfile():
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                raise AssertionError(f"unreadable archive member: {member.name}")
            payloads[member.name] = extracted.read()
        return members, payloads


def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def stage_kit(destination: Path) -> Path:
    """Copy the shipped manifest, its files allowlist and README into a staging tree.

    Only the staging copy is edited (version bump, marker); the repository
    package.json is never mutated.
    """
    destination.mkdir(parents=True, exist_ok=True)
    for entry in ["package.json", *manifest()["files"], "README.md"]:
        candidates = sorted(KIT.glob(entry)) if "*" in entry else [KIT / entry]
        matches = [path for path in candidates if path.is_file()]
        if not matches:
            raise AssertionError(f"no repository source for manifest files entry: {entry}")
        for match in matches:
            target = destination / match.relative_to(KIT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(match, target)
    return destination


def install_tarball(root: Path, tarball: Path) -> None:
    process = _run(
        [BUN, "add", "--dev", "--exact", "--offline", "--ignore-scripts", "--backend=copyfile", f"{PACKAGE_NAME}@{tarball}"], root
    )
    if process.returncode != 0:
        raise AssertionError(f"bun add {tarball} failed: {combined(process)}")
    if not (root / "node_modules" / PACKAGE_NAME / "package.json").is_file():
        raise AssertionError(f"bun add left {PACKAGE_NAME} uninstalled in {root}")


def link_tools(root: Path) -> None:
    bins = root / "node_modules" / ".bin"
    bins.mkdir(parents=True, exist_ok=True)
    for tool in ("tsc", "biome"):
        (bins / tool).symlink_to(NODE_MODULES_PATH / ".bin" / tool)


def build_consumer(
    root: Path,
    tarball: Path,
    *,
    routing: str | None = ROUTING_TOML,
    sources: dict[str, str] | None = None,
    extends: bool = True,
    bunfig: bool = False,
    sentinel: bool = False,
    baseline: bool = False,
) -> None:
    """Clean consumer that installs the tarball; no checker assets are copied in."""
    root = Path(root)
    (root / "package.json").write_text(
        json.dumps({"name": "consumer", "version": "0.0.0", "private": True}, indent=2) + "\n",
        encoding="utf-8",
    )
    install_tarball(root, tarball)
    link_tools(root)

    src = root / "src"
    src.mkdir()
    for name, body in (sources or {"index.ts": GOOD_TS, "other.ts": OTHER_TS}).items():
        (src / name).write_text(body, encoding="utf-8")

    project = (
        {"extends": "gajaestack/tsconfig", "include": ["src"]}
        if extends
        else {
            "compilerOptions": {
                "strict": True,
                "noEmit": True,
                "target": "ES2024",
                "module": "ESNext",
                "moduleResolution": "Bundler",
                "skipLibCheck": True,
                "types": [],
            },
            "include": ["src"],
        }
    )
    (root / "tsconfig.json").write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    (root / "biome.json").write_text(
        json.dumps({"linter": {"enabled": True}, "formatter": {"enabled": False}}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (root / ".gajaestack").mkdir()
    if routing is not None:
        (root / ".gajaestack" / "routing.toml").write_text(routing, encoding="utf-8")
    # Keeps the installed dependency out of git status so "clean git" is honest.
    (root / ".gitignore").write_text("node_modules/\nsentinel.txt\n", encoding="utf-8")

    if bunfig:
        (root / "bunfig.toml").write_text(
            '[test]\npreload = ["gajaestack/preload"]\n', encoding="utf-8"
        )
    if sentinel:
        (root / "sentinel.test.ts").write_text(SENTINEL_SOURCE, encoding="utf-8")
    if baseline:
        git_init_baseline(root)


def run_bin(
    root: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return _run([BUN, "run", BIN_ENTRY, *args], root, env=env)


def run_guard(root: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return _run([BUN, "test"], root, env=env)


def run_tool(root: Path, tool: str, *args: str) -> subprocess.CompletedProcess[str]:
    return _run([BUN, str(root / "node_modules" / ".bin" / tool), *args], root)


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
    """Files and directories under root except .git; checks must not write any."""
    return {
        str(path.relative_to(root))
        for path in root.rglob("*")
        if ".git" not in path.relative_to(root).parts
    }


class PackageManifestContractTests(unittest.TestCase):
    """Static root-manifest boundaries that need no native toolchain."""

    def test_root_manifest_pins_version_and_declares_exact_exports_and_bin(self) -> None:
        package = manifest()
        self.assertEqual(package["name"], PACKAGE_NAME)
        self.assertEqual(package["version"], PINNED_VERSION)
        self.assertEqual(package["type"], "module")
        self.assertEqual(package["exports"], EXPECTED_EXPORTS)
        self.assertEqual(package["bin"], EXPECTED_BIN)

    def test_files_allowlist_ships_assets_and_static_guidance_only(self) -> None:
        files = manifest()["files"]
        self.assertEqual(set(files), EXPECTED_FILES)
        for entry in files:
            with self.subTest(entry=entry):
                self.assertFalse(entry.endswith(IMPLEMENTATION_SUFFIXES), entry)
                self.assertFalse(entry.startswith((".gjc/", "scripts/", "tests/")), entry)
                if "*" in entry:
                    self.assertTrue(list(KIT.glob(entry)), f"files glob matches nothing: {entry}")
                else:
                    self.assertTrue(
                        (KIT / entry).is_file(), f"files entry missing from repository: {entry}"
                    )

    def test_readme_relative_links_resolve_inside_packaged_files(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        files = set(manifest()["files"])
        targets = {
            match.split("#", 1)[0]
            for match in re.findall(r"\]\((?!https?://)([^)\s]+)\)", readme)
            if match.split("#", 1)[0]
        }
        self.assertIn("docs/python-trial.md", targets)
        self.assertIn("docs/scope-invariant.md", targets)
        for target in sorted(targets):
            with self.subTest(link=target):
                self.assertIn(target, files, f"README link is not packaged: {target}")


@unittest.skipUnless(NATIVE_TOOLS, PREREQ_REASON)
class NativePackageTestCase(unittest.TestCase):
    """Packs the real repository once per class and validates the native toolchain."""

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
        cls.packing = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.packing.cleanup)
        cls.pack_dir = Path(cls.packing.name)
        cls.tarball = pack_kit(KIT, cls.pack_dir)

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)


class PackageArchiveInventoryTests(NativePackageTestCase):
    def test_pack_writes_single_tarball_named_from_manifest(self) -> None:
        self.assertEqual(self.tarball.name, f"{PACKAGE_NAME}-{PINNED_VERSION}.tgz")
        self.assertEqual(self.tarball.parent, self.pack_dir)
        self.assertGreater(self.tarball.stat().st_size, 0)

    def test_inventory_is_allowlisted_without_caches_private_or_python_implementation(
        self,
    ) -> None:
        members, payloads = archive_inventory(self.tarball)
        for member in members:
            with self.subTest(member=member.name):
                self.assertTrue(
                    member.isfile(),
                    f"only plain files may ship: {member.name} is dir/link/device",
                )
                parts = Path(member.name).parts
                self.assertFalse(member.name.startswith("/"), member.name)
                self.assertNotIn("..", parts, member.name)
                self.assertTrue(
                    member.name.startswith("package/"), f"member outside package/: {member.name}"
                )
                self.assertFalse(
                    FORBIDDEN_COMPONENTS.intersection(parts), f"forbidden path in {member.name}"
                )
                self.assertFalse(
                    member.name.endswith(IMPLEMENTATION_SUFFIXES),
                    f"Python implementation shipped: {member.name}",
                )
        names = {member.name for member in members}
        self.assertEqual(names, EXPECTED_MEMBERS)
        self.assertEqual(
            {name for name in names if name.startswith("package/python/")},
            {"package/python/routing/AGENTS.md"},
            "python/ may contribute static guidance only",
        )
        self.assertEqual(len(payloads), len(names))

    def test_packed_bytes_are_the_repository_bytes(self) -> None:
        _, payloads = archive_inventory(self.tarball)
        self.assertEqual(set(payloads), EXPECTED_MEMBERS)
        for name, payload in payloads.items():
            with self.subTest(member=name):
                source = KIT / name.removeprefix("package/")
                self.assertTrue(source.is_file(), f"packed member has no repository source: {name}")
                self.assertEqual(payload, source.read_bytes(), name)

    def test_packed_manifest_keeps_version_exports_and_bin(self) -> None:
        _, payloads = archive_inventory(self.tarball)
        packed = json.loads(payloads["package/package.json"])
        self.assertEqual(packed["version"], PINNED_VERSION)
        self.assertEqual(packed["exports"], EXPECTED_EXPORTS)
        self.assertEqual(packed["bin"], EXPECTED_BIN)
        self.assertEqual(set(packed["files"]), EXPECTED_FILES)


class InstalledPackageCheckTests(NativePackageTestCase):
    def test_native_removal_preserves_tools_and_requires_explicit_unbinding(self) -> None:
        build_consumer(self.root, self.tarball, extends=False, bunfig=True, sentinel=True)
        facts = (self.root / ".gajaestack/routing.toml").read_bytes()
        removed = _run([BUN, "remove", "--offline", "--ignore-scripts", PACKAGE_NAME], self.root)
        self.assertEqual(removed.returncode, 0, combined(removed))
        self.assertFalse((self.root / "node_modules/gajaestack").exists())
        still_bound = run_guard(self.root)
        self.assertNotEqual(still_bound.returncode, 0)
        self.assertFalse((self.root / "sentinel.txt").exists())
        # Native managers do not silently rewrite consumer test policy.
        (self.root / "bunfig.toml").write_text("[test]\ntimeout = 12000\n")
        unbound = run_guard(self.root)
        self.assertEqual(unbound.returncode, 0, combined(unbound))
        self.assertEqual((self.root / ".gajaestack/routing.toml").read_bytes(), facts)
        native = run_tool(self.root, "tsc", "--noEmit", "--project", "tsconfig.json")
        self.assertEqual(native.returncode, 0, combined(native))

    @unittest.skipUnless(GJC, "set GAJAESTACK_GJC for native host discovery")
    def test_native_host_additional_directory_preserves_existing_skills(self) -> None:
        build_consumer(self.root, self.tarball)
        git("init", "-q", cwd=self.root)
        existing = self.root / ".gjc/skills"
        existing.mkdir(parents=True)
        (existing / "keep.txt").write_text("existing consumer skill root")
        consumer_skill = existing / "consumer-guidance"
        consumer_skill.mkdir()
        consumer_skill.joinpath("SKILL.md").write_text(
            "---\nname: consumer-guidance\ndescription: Existing consumer guidance\n"
            "---\nPreserve this consumer guidance.\n"
        )
        config = self.root / ".gjc/config.yml"
        config.write_text(
            "configSchemaVersion: 2\nskills:\n  customDirectories:\n"
            "    - node_modules/gajaestack/skills\n"
            "  ignoredSkills:\n    - type-discipline\n    - verify-change\n"
        )
        before = config.read_bytes()
        discovered = _run(
            [GJC, "skills", "discover", "--source", "all", "--json"],
            self.root,
        )
        self.assertEqual(discovered.returncode, 0, combined(discovered))
        candidates = json.loads(discovered.stdout)["candidates"]
        names = {candidate["name"] for candidate in candidates}
        self.assertIn("consumer-guidance", names)
        self.assertEqual(
            names & {"native-quality", "type-discipline", "verify-change"},
            {"native-quality"},
        )
        selected = next(c for c in candidates if c["name"] == "native-quality")
        self.assertEqual(
            (self.root / "node_modules/gajaestack/skills/native-quality/SKILL.md").stat().st_nlink,
            1,
        )
        self.assertEqual(
            Path(selected["path"]),
            self.root / "node_modules/gajaestack/skills/native-quality/SKILL.md",
        )
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual((existing / "keep.txt").read_text(), "existing consumer skill root")

    def test_native_check_and_preload_need_neither_python_nor_node(self) -> None:
        build_consumer(self.root, self.tarball, bunfig=True, sentinel=True)
        commands = self.root / "runtime-bin"
        commands.mkdir()
        (commands / "bun").symlink_to(Path(BUN).resolve())
        env = offline_env({"PATH": str(commands)})
        for name in ("python", "python3", "node"):
            self.assertIsNone(shutil.which(name, path=env["PATH"]))
        checked = run_bin(self.root, env=env)
        self.assertEqual(checked.returncode, 0, combined(checked))
        guarded = run_guard(self.root, env=env)
        self.assertEqual(guarded.returncode, 0, combined(guarded))
        self.assertTrue((self.root / "sentinel.txt").exists())

    def test_bin_full_check_passes_without_copied_assets(self) -> None:
        build_consumer(self.root, self.tarball)
        installed = self.root / "node_modules" / PACKAGE_NAME
        self.assertTrue((installed / "typescript" / "check.ts").is_file())
        self.assertTrue((self.root / "node_modules" / ".bin" / BIN_ENTRY).exists())
        # Package adoption ships code through the dependency, never a copied asset tree.
        self.assertEqual(
            sorted(path.name for path in (self.root / ".gajaestack").iterdir()),
            ["routing.toml"],
        )

        process = run_bin(self.root)
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertIn("Typecheck: 2 project files", text)
        self.assertIn("Lint: 2 selected source files", text)
        self.assertNotIn("Quick scope expanded", text)

    def test_bin_rejects_unknown_argument_with_package_usage(self) -> None:
        build_consumer(self.root, self.tarball)
        for args in (["--bogus"], ["--quick", "extra"], ["--timing", "--timing"]):
            with self.subTest(args=args):
                process = run_bin(self.root, *args)
                text = combined(process)
                self.assertEqual(process.returncode, 2, text)
                self.assertIn(USAGE_TEXT, text)
                self.assertNotIn("Typecheck:", text)

    def test_optional_tsconfig_export_extends_resolves_through_native_tsc(self) -> None:
        build_consumer(self.root, self.tarball, extends=True)
        shown = run_tool(
            self.root,
            "tsc",
            "--project",
            str(self.root / "tsconfig.json"),
            "--showConfig",
        )
        text = combined(shown)
        self.assertEqual(shown.returncode, 0, text)
        # Both base options live only in the packaged gajaestack/tsconfig.
        self.assertIn('"forceConsistentCasingInFileNames": true', text)
        self.assertIn('"verbatimModuleSyntax": true', text)
        self.assertIn('"./src/index.ts"', text)

        typecheck = run_tool(
            self.root,
            "tsc",
            "--noEmit",
            "--incremental",
            "false",
            "--project",
            str(self.root / "tsconfig.json"),
        )
        self.assertEqual(typecheck.returncode, 0, combined(typecheck))

    @requires_native_git
    def test_quick_passes_with_full_installed_scope_on_clean_git(self) -> None:
        build_consumer(self.root, self.tarball, baseline=True)
        status = git("status", "--porcelain", cwd=self.root)
        self.assertEqual(combined(status).strip(), "", "consumer baseline must be clean")

        process = run_bin(self.root, "--quick")
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertIn(
            "Quick scope expanded to full selected scope: changed installed shared package",
            text,
        )
        self.assertIn("installed shared package (no tracked code baseline)", text)
        # Conservative full scope, not a changed-file intersection and not a no-op.
        self.assertIn("Lint: 2 selected source files", text)
        self.assertNotIn("No changed files", text)
        self.assertNotIn("Typecheck:", text)

    @requires_native_git
    def test_dependency_source_modification_cannot_escape_quick(self) -> None:
        build_consumer(
            self.root,
            self.tarball,
            sources={"index.ts": GOOD_TS, "other.ts": OTHER_TS, "bad-lint.ts": LINT_ERROR_TS},
            baseline=True,
        )
        status = git("status", "--porcelain", cwd=self.root)
        self.assertEqual(combined(status).strip(), "", "committed lint error leaves clean status")

        installed_check = self.root / "node_modules" / PACKAGE_NAME / "typescript" / "check.ts"
        original = installed_check.read_bytes()
        installed_check.write_bytes(original + f"\n{INSTALLED_SOURCE_MARKER}\n".encode("utf-8"))
        self.assertIn(INSTALLED_SOURCE_MARKER, installed_check.read_text(encoding="utf-8"))

        process = run_bin(self.root, "--quick")
        text = combined(process)
        self.assertNotEqual(process.returncode, 0, text)
        self.assertIn("noDebugger", text)
        self.assertIn("bad-lint", text)
        self.assertIn("Quick scope expanded to full selected scope", text)
        self.assertIn("Lint: 3 selected source files", text)
        self.assertNotIn("No changed files", text)
        self.assertNotIn("Typecheck:", text)

    def test_exports_import_runs_checker_from_installed_package(self) -> None:
        build_consumer(self.root, self.tarball)
        script = self.root / "use-exports.ts"
        script.write_text(
            'import { check } from "gajaestack/check";\n'
            "\n"
            "const status = await check();\n"
            'console.log(`check status ${status}`);\n',
            encoding="utf-8",
        )
        process = _run([BUN, "run", script.name], self.root)
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)
        self.assertIn("check status 0", text)
        self.assertIn("Typecheck: 2 project files", text)
        self.assertIn("Lint: 2 selected source files", text)
        self.assertEqual(
            sorted(path.name for path in (self.root / ".gajaestack").iterdir()),
            ["routing.toml"],
        )

    def test_type_failure_blocks_sentinel_import_then_recovers(self) -> None:
        build_consumer(self.root, self.tarball, bunfig=True, sentinel=True)
        failing = self.root / "src" / "bad.ts"
        failing.write_text(TYPE_ERROR_TS, encoding="utf-8")
        native = run_tool(
            self.root,
            "tsc",
            "--noEmit",
            "--incremental",
            "false",
            "--project",
            str(self.root / "tsconfig.json"),
        )
        self.assertNotEqual(native.returncode, 0, combined(native))

        process = run_guard(self.root)
        text = combined(process)
        self.assertEqual(process.returncode, native.returncode, text)
        self.assertIn("error TS", text)
        self.assertFalse((self.root / "sentinel.txt").exists(), text)
        self.assertNotIn("sentinel ran", text)

        failing.unlink()
        recovered = run_guard(self.root)
        recovered_text = combined(recovered)
        self.assertEqual(recovered.returncode, 0, recovered_text)
        self.assertIn("Typecheck: 2 project files", recovered_text)
        self.assertIn("Lint: 2 selected source files", recovered_text)
        self.assertTrue((self.root / "sentinel.txt").exists(), recovered_text)
        self.assertRegex(recovered_text, r"\b1 pass\b")

    def test_lint_failure_blocks_sentinel_import_then_recovers(self) -> None:
        build_consumer(
            self.root,
            self.tarball,
            sources={"index.ts": GOOD_TS, "other.ts": OTHER_TS, "bad-lint.ts": LINT_ERROR_TS},
            bunfig=True,
            sentinel=True,
        )
        native = run_tool(
            self.root,
            "biome",
            "lint",
            f"--config-path={self.root / 'biome.json'}",
            str(self.root / "src" / "bad-lint.ts"),
        )
        self.assertNotEqual(native.returncode, 0, combined(native))

        process = run_guard(self.root)
        text = combined(process)
        self.assertEqual(process.returncode, native.returncode, text)
        self.assertIn("noDebugger", text)
        self.assertFalse((self.root / "sentinel.txt").exists(), text)
        self.assertNotIn("sentinel ran", text)

        (self.root / "src" / "bad-lint.ts").unlink()
        recovered = run_guard(self.root)
        recovered_text = combined(recovered)
        self.assertEqual(recovered.returncode, 0, recovered_text)
        self.assertTrue((self.root / "sentinel.txt").exists(), recovered_text)
        self.assertRegex(recovered_text, r"\b1 pass\b")

    def test_missing_tool_facts_and_config_fail_with_native_status_then_recover(self) -> None:
        # (case, native status, message, typecheck phase reached before the failure)
        cases = (
            ("missing tsc", 127, "missing executable:", False),
            ("missing biome", 127, "missing executable:", True),
            ("missing facts", 2, "fact must be a table", False),
            ("missing config", 2, "gajaestack:", False),
        )
        for case, status, message, typecheck_reached in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    routing = {"missing config": None, "missing facts": NO_FACT_ROUTING_TOML}.get(
                        case, ROUTING_TOML
                    )
                    build_consumer(root, self.tarball, routing=routing)
                    tool = case.split()[1] if case in ("missing tsc", "missing biome") else None
                    if tool:
                        (root / "node_modules" / ".bin" / tool).unlink()

                    failed = run_bin(root)
                    text = combined(failed)
                    self.assertEqual(failed.returncode, status, text)
                    self.assertIn(message, text)
                    self.assertEqual(
                        "Typecheck:" in text,
                        typecheck_reached,
                        f"{case} phase boundary in output: {text}",
                    )
                    self.assertNotIn("Lint:", text)

                    if tool:
                        (root / "node_modules" / ".bin" / tool).symlink_to(
                            NODE_MODULES_PATH / ".bin" / tool
                        )
                    else:
                        (root / ".gajaestack" / "routing.toml").write_text(
                            ROUTING_TOML, encoding="utf-8"
                        )
                    recovered = run_bin(root)
                    recovered_text = combined(recovered)
                    self.assertEqual(recovered.returncode, 0, recovered_text)
                    self.assertIn("Typecheck: 2 project files", recovered_text)
                    self.assertIn("Lint: 2 selected source files", recovered_text)

    @requires_native_git
    def test_checks_leave_consumer_tree_unchanged(self) -> None:
        build_consumer(self.root, self.tarball, baseline=True)
        before = tree_snapshot(self.root)
        full = run_bin(self.root, "--timing")
        quick = run_bin(self.root, "--quick", "--timing")
        after = tree_snapshot(self.root)
        self.assertEqual(full.returncode, 0, combined(full))
        self.assertEqual(quick.returncode, 0, combined(quick))
        self.assertIn("Lint: 2 selected source files", combined(full))
        self.assertIn("Quick scope expanded", combined(quick))
        self.assertRegex(combined(quick), r"timing: lint files=2 status=0 elapsed_ms=\d+")
        self.assertEqual(before, after, "checks must not write consumer files")
        self.assertFalse((self.root / "tsconfig.tsbuildinfo").exists())


class InstalledPinnedUpgradeTests(NativePackageTestCase):
    def test_pinned_0_1_1_upgrade_and_frozen_offline_reinstall(self) -> None:
        build_consumer(self.root, self.tarball)
        installed = self.root / "node_modules" / PACKAGE_NAME
        baseline_installed = (installed / "typescript" / "check.ts").read_bytes()
        baseline_skill = (installed / UPGRADE_SKILL).read_bytes()
        installed_manifest = json.loads((installed / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(installed_manifest["version"], PINNED_VERSION)

        holding = tempfile.TemporaryDirectory()
        self.addCleanup(holding.cleanup)
        staging = stage_kit(Path(holding.name) / "staging")
        staged_manifest = staging / "package.json"
        staged = json.loads(staged_manifest.read_text(encoding="utf-8"))
        staged["version"] = UPGRADE_VERSION
        staged_manifest.write_text(json.dumps(staged, indent=2) + "\n", encoding="utf-8")
        staged_check = staging / "typescript" / "check.ts"
        staged_check.write_text(
            staged_check.read_text(encoding="utf-8") + f"\n{UPGRADE_MARKER}\n", encoding="utf-8"
        )
        staged_skill = staging / UPGRADE_SKILL
        staged_skill.write_text(
            staged_skill.read_text(encoding="utf-8") + f"\n{SKILL_MARKER}\n", encoding="utf-8"
        )
        self.assertNotEqual(staged_skill.read_bytes(), (KIT / UPGRADE_SKILL).read_bytes())

        upgrade_tarball = pack_kit(staging, Path(holding.name) / "upgrade-pack")
        self.assertEqual(upgrade_tarball.name, f"{PACKAGE_NAME}-{UPGRADE_VERSION}.tgz")
        self.assertNotEqual(upgrade_tarball.read_bytes(), self.tarball.read_bytes())
        # The repository manifest is never mutated to produce the second tarball.
        self.assertEqual(manifest()["version"], PINNED_VERSION)
        members, _ = archive_inventory(upgrade_tarball)
        self.assertEqual({member.name for member in members}, EXPECTED_MEMBERS)

        process = _run(
            [
                BUN,
                "add",
                "--dev",
                "--exact",
                "--offline",
                "--ignore-scripts",
                "--backend=copyfile",
                f"{PACKAGE_NAME}@{upgrade_tarball}",
            ],
            self.root,
        )
        text = combined(process)
        self.assertEqual(process.returncode, 0, text)

        consumer = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(consumer["devDependencies"][PACKAGE_NAME], str(upgrade_tarball))
        self.assertEqual(
            json.loads((installed / "package.json").read_text())["version"], UPGRADE_VERSION
        )
        upgraded_code = (installed / "typescript" / "check.ts").read_text(encoding="utf-8")
        self.assertIn(UPGRADE_MARKER, upgraded_code)
        self.assertNotEqual(upgraded_code.encode("utf-8"), baseline_installed)
        # Only the staged bytes differ: bun's own install path refreshes the
        # dependency in place; this test never re-copies files into node_modules.
        upgraded_skill = (installed / UPGRADE_SKILL).read_bytes()
        self.assertIn(SKILL_MARKER.encode("utf-8"), upgraded_skill)
        self.assertNotEqual(upgraded_skill, baseline_skill, "installed skill bytes must change")

        lock = self.root / "bun.lock"
        lock_before = lock.read_bytes()
        # The named native upgrade must leave one workspace pin and one package
        # entry, not a duplicate key or a superseded artifact reference.
        self.assertNotIn(str(self.tarball).encode(), lock_before)
        self.assertEqual(lock_before.count(b'"gajaestack":'), 2)
        self.assertIn(f'"gajaestack@{upgrade_tarball}"', lock_before.decode("utf-8"))

        shutil.rmtree(self.root / "node_modules")
        reinstall = _run(
            [BUN, "install", "--offline", "--frozen-lockfile", "--ignore-scripts", "--backend=copyfile"], self.root
        )
        self.assertEqual(reinstall.returncode, 0, combined(reinstall))
        self.assertEqual(
            lock.read_bytes(), lock_before, "frozen reinstall must not rewrite the lock"
        )
        self.assertEqual(
            json.loads((installed / "package.json").read_text())["version"], UPGRADE_VERSION
        )
        self.assertIn(UPGRADE_MARKER, (installed / "typescript" / "check.ts").read_text("utf-8"))
        self.assertEqual(
            (installed / UPGRADE_SKILL).read_bytes(),
            upgraded_skill,
            "frozen reinstall must reproduce the upgraded skill bytes",
        )

        link_tools(self.root)
        checked = run_bin(self.root)
        checked_text = combined(checked)
        self.assertEqual(checked.returncode, 0, checked_text)
        self.assertIn("Typecheck: 2 project files", checked_text)
        self.assertIn("Lint: 2 selected source files", checked_text)
        self.assertEqual(manifest()["version"], PINNED_VERSION)
        # The repository skill keeps its original bytes: only staging was edited.
        source_skill = (KIT / UPGRADE_SKILL).read_bytes()
        self.assertNotIn(SKILL_MARKER.encode("utf-8"), source_skill)
        self.assertNotEqual(source_skill, upgraded_skill)


if __name__ == "__main__":
    unittest.main()
