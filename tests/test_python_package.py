from __future__ import annotations

from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import zipfile

KIT = Path(__file__).resolve().parents[1]
PYTHON = os.environ.get("GAJAESTACK_PYTHON")
WHEELHOUSE = os.environ.get("GAJAESTACK_PYTHON_WHEELHOUSE")
GJC = os.environ.get("GAJAESTACK_GJC")

LICENSE_FILES = ("LICENSE", "THIRD_PARTY_NOTICES")


@unittest.skipUnless(
    PYTHON and WHEELHOUSE,
    "set GAJAESTACK_PYTHON and GAJAESTACK_PYTHON_WHEELHOUSE for offline package acceptance",
)
class PythonPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name)
        cls.dist = cls.base / "dist"
        cls.dist.mkdir()
        cls.stage = cls.base / "source"
        cls.stage.mkdir()
        for name in (
            "pyproject.toml",
            "README.md",
            "AGENTS.md",
            "package.json",
            "MANIFEST.in",
            "LICENSE",
            "THIRD_PARTY_NOTICES",
        ):
            if (KIT / name).exists():
                shutil.copyfile(KIT / name, cls.stage / name)
        for name in ("python", "skills", "docs"):
            shutil.copytree(
                KIT / name,
                cls.stage / name,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
        # Deliberately poison the build tree: package inventory must exclude these.
        (cls.stage / ".private-token").write_text("never distribute")
        (cls.stage / "python/__pycache__").mkdir()
        (cls.stage / "python/__pycache__/private.pyc").write_bytes(b"private")
        cls.run_command(
            [
                PYTHON,
                "-B",
                "-c",
                "import setuptools.build_meta as b; b.build_sdist('"
                + str(cls.dist)
                + "')",
            ],
            cls.stage,
        )
        cls.sdist = next(cls.dist.glob("*.tar.gz"))
        cls.run_command(
            [
                PYTHON,
                "-B",
                "-m",
                "pip",
                "wheel",
                "--no-index",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(cls.dist),
                str(cls.sdist),
            ],
            cls.base,
        )
        cls.wheel = next(cls.dist.glob("*.whl"))

    @staticmethod
    def run_command(command, cwd, env=None, expected=0):
        result = subprocess.run(
            command, cwd=cwd, env=env, text=True, capture_output=True, timeout=180
        )
        if result.returncode != expected:
            raise AssertionError(
                f"{command}: {result.returncode}\n{result.stdout}\n{result.stderr}"
            )
        return result

    def test_inventory_native_entrypoints_and_version(self):
        with tarfile.open(self.sdist) as archive:
            source_names = archive.getnames()
            metadata_name = next(
                name
                for name in source_names
                if name.count("/") == 1 and name.endswith("/PKG-INFO")
            )
            source_metadata = Parser().parsestr(
                archive.extractfile(metadata_name).read().decode()
            )
            source_root = metadata_name.rsplit("/", 1)[0]
            self.assertCountEqual(
                [name for name in source_names if Path(name).name in LICENSE_FILES],
                [f"{source_root}/{name}" for name in LICENSE_FILES],
            )
            sdist_licenses = {
                name: archive.extractfile(f"{source_root}/{name}").read()
                for name in LICENSE_FILES
            }
        with zipfile.ZipFile(self.wheel) as archive:
            names = archive.namelist()
            metadata_name = next(
                name for name in names if name.endswith(".dist-info/METADATA")
            )
            metadata = archive.read(metadata_name).decode()
            wheel_metadata = Parser().parsestr(metadata)
            license_root = metadata_name.rsplit("/", 1)[0] + "/licenses"
            self.assertCountEqual(
                [name for name in names if Path(name).name in LICENSE_FILES],
                [f"{license_root}/{name}" for name in LICENSE_FILES],
            )
            entrypoints = archive.read(
                next(
                    name
                    for name in names
                    if name.endswith(".dist-info/entry_points.txt")
                )
            ).decode()
            wheel_licenses = {
                name: archive.read(f"{license_root}/{name}") for name in LICENSE_FILES
            }
            self.assertNotIn("Requires-Dist:", metadata)
            self.assertNotIn("pytest11", entrypoints)
            for command in (
                "gajaestack-python-check",
                "gajaestack-imports",
                "gajaestack-routing",
            ):
                self.assertIn(command, entrypoints)
            self.assertIn(
                "Version: " + json.loads((KIT / "package.json").read_text())["version"],
                metadata,
            )
        for parsed_metadata in (source_metadata, wheel_metadata):
            self.assertEqual(parsed_metadata.get_all("License-Expression"), ["MIT"])
            self.assertCountEqual(
                parsed_metadata.get_all("License-File", []), LICENSE_FILES
            )
        for licenses in (sdist_licenses, wheel_licenses):
            self.assertEqual(set(licenses), set(LICENSE_FILES))
            for name in LICENSE_FILES:
                self.assertEqual(licenses[name], (KIT / name).read_bytes(), name)
        for name in source_names + names:
            for forbidden in (
                "__pycache__",
                ".pyc",
                ".private",
                "node_modules",
                ".gjc/",
                "ownership.json",
            ):
                self.assertNotIn(forbidden, name)
        for name in (
            "gajaestack/pytest_guard.py",
            "gajaestack/pytest_required_ruff.py",
            "gajaestack/check_changed_python.py",
            "gajaestack/ruff.toml",
            "gajaestack/mypy.ini",
            "gajaestack/test_percent_decoder_properties.py",
        ):
            self.assertIn(name, names)
        self.assertEqual(sum(name.endswith("SKILL.md") for name in names), 3)
        self.assertFalse(any(name.endswith(".ts") for name in names))

    def test_clean_hash_pinned_install_upgrade_and_removal_without_bun(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            venv = root / ".venv"
            self.run_command([PYTHON, "-B", "-m", "venv", str(venv)], root)
            python = str(venv / "bin/python")
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)
            env["PATH"] = str(venv / "bin") + ":/usr/bin:/bin"
            env["PIP_NO_INDEX"] = "1"
            self.assertIsNone(shutil.which("bun", path=env["PATH"]))
            lock = root / "requirements.txt"
            lock.write_text(
                f"gajaestack @ {self.wheel.as_uri()} --hash=sha256:{hashlib.sha256(self.wheel.read_bytes()).hexdigest()}\n"
            )
            install = [
                python,
                "-B",
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                "--no-compile",
                "--require-hashes",
                "-r",
                str(lock),
            ]
            self.run_command(install, root, env)
            initial_lock = lock.read_bytes()
            self.run_command(install + ["--force-reinstall"], root, env)
            self.assertEqual(initial_lock, lock.read_bytes())
            probe = self.run_command(
                [
                    python,
                    "-B",
                    "-c",
                    "import importlib.util; assert importlib.util.find_spec('pytest') is None; from gajaestack import __version__; print(__version__)",
                ],
                root,
                env,
            )
            self.assertEqual(probe.stdout.strip(), "0.1.0")
            self.run_command(
                [str(venv / "bin/gajaestack-imports"), "tomllib"], root, env
            )
            missing = subprocess.run(
                [str(venv / "bin/gajaestack-python-check"), "--full"],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("facts", missing.stdout + missing.stderr)
            # Ruff-only completion runs without pytest: provision Ruff from the
            # existing environment and complete --full over declared facts.
            host_ruff = Path(shutil.which(PYTHON) or PYTHON).parent / "ruff"
            self.assertTrue(
                host_ruff.is_file(),
                f"missing ruff executable beside GAJAESTACK_PYTHON: {host_ruff}",
            )
            shutil.copy2(host_ruff, venv / "bin" / "ruff")
            (root / ".gajaestack").mkdir()
            (root / ".gajaestack/routing.toml").write_text(
                'required = ["ruff-check"]\n'
                '[fact]\nschema_version = 1\nselected_components = ["ruff"]\n'
                'test_command = "gajaestack-python-check --full"\n'
                "[python]\nschema_version = 1\n"
                'ruff_paths = ["example.py"]\nruff_config = "ruff.toml"\n'
            )
            (root / "ruff.toml").write_text(
                'target-version = "py312"\n[lint]\nselect = ["E4", "E7", "E9", "F"]\n'
            )
            (root / "example.py").write_text("value = 1\n")
            ruff_only = subprocess.run(
                [str(venv / "bin/gajaestack-python-check"), "--full"],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(
                ruff_only.returncode, 0, ruff_only.stdout + ruff_only.stderr
            )
            self.assertIn("Full selected scope: 1 file(s)", ruff_only.stdout)
            self.run_command(
                [
                    python,
                    "-B",
                    "-c",
                    "import importlib.util; assert importlib.util.find_spec('pytest') is None",
                ],
                root,
                env,
            )
            # Reject and recover while pytest is still absent.
            (root / "example.py").write_text("import os\nvalue = 1\n")
            rejected_lint = subprocess.run(
                [str(venv / "bin/gajaestack-python-check"), "--full"],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
            )
            rejected_text = rejected_lint.stdout + rejected_lint.stderr
            self.assertNotEqual(rejected_lint.returncode, 0, rejected_text)
            self.assertIn("Full selected scope: 1 file(s)", rejected_text)
            self.assertIn("F401", rejected_text)
            (root / "example.py").write_text("value = 1\n")
            recovered_lint = subprocess.run(
                [str(venv / "bin/gajaestack-python-check"), "--full"],
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
            )
            recovered_text = recovered_lint.stdout + recovered_lint.stderr
            self.assertEqual(recovered_lint.returncode, 0, recovered_text)
            self.assertIn("Full selected scope: 1 file(s)", recovered_text)
            # Native tool provisioning is explicit and offline, separate from kit install.
            self.run_command(
                [
                    python,
                    "-B",
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--find-links",
                    WHEELHOUSE,
                    "pytest==9.1.1",
                ],
                root,
                env,
            )
            (root / "test_native.py").write_text(
                "def test_native():\n    assert 2 + 2 == 4\n"
            )
            # Merely installing the kit does not activate any checks.
            self.run_command(
                [python, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                root,
                env,
            )
            version_file = self.stage / "python/__init__.py"
            original = version_file.read_text()
            skill_file = self.stage / "skills/native-quality/SKILL.md"
            original_skill = skill_file.read_text()
            skill_root = Path(
                self.run_command(
                    [
                        python,
                        "-B",
                        "-c",
                        "import gajaestack_guidance; print(next(iter(gajaestack_guidance.__path__)))",
                    ],
                    root,
                    env,
                ).stdout.strip()
            )
            (root / ".gjc").mkdir()
            (root / ".gjc/skills").mkdir()
            consumer_skill = root / ".gjc/skills/consumer-notes/SKILL.md"
            consumer_skill.parent.mkdir()
            consumer_skill.write_text(
                "---\n"
                "name: consumer-notes\n"
                "description: Consumer-owned skill retained through kit discovery.\n"
                "---\n\nConsumer skill body.\n"
            )
            consumer_before = consumer_skill.read_bytes()
            host_config = root / ".gjc/config.yml"
            host_config.write_text(
                "configSchemaVersion: 2\nskills:\n  customDirectories:\n    - "
                + os.path.relpath(skill_root, root)
                + "\n"
                + "  ignoredSkills:\n    - type-discipline\n    - verify-change\n"
            )
            host_before = host_config.read_bytes()
            if GJC:
                self.run_command(["git", "init", "-q"], root, env)
                discovered = self.run_command(
                    [GJC, "skills", "discover", "--source", "all", "--json"],
                    root,
                    env,
                )
                candidates = json.loads(discovered.stdout)["candidates"]
                kit_paths = {
                    Path(item["path"])
                    for item in candidates
                    if str(skill_root) in item["path"]
                }
                self.assertEqual(kit_paths, {skill_root / "native-quality/SKILL.md"})
                self.assertTrue(
                    any(
                        item["path"].endswith(".gjc/skills/consumer-notes/SKILL.md")
                        for item in candidates
                    ),
                    "consumer-owned skill was not retained",
                )
                # Candidates are catalog evidence, not prompt proof; diagnostics leak names.
                selected = next(
                    item
                    for item in candidates
                    if Path(item["path"]) == skill_root / "native-quality/SKILL.md"
                )
                self.assertIn(
                    selected["description"],
                    (skill_root / "native-quality/SKILL.md").read_text(
                        encoding="utf-8"
                    ),
                )
            try:
                version_file.write_text(
                    original.replace("0.1.0", "0.1.1")
                    + '\nUPGRADE_MARKER = "distinct-local-release"\n'
                )
                skill_file.write_text(
                    original_skill
                    + "\nLocal upgrade verification marker: distinct-guidance-release.\n"
                )
                manifest = self.stage / "package.json"
                document = json.loads(manifest.read_text())
                document["version"] = "0.1.1"
                manifest.write_text(json.dumps(document))
                self.run_command(
                    [
                        PYTHON,
                        "-B",
                        "-m",
                        "pip",
                        "wheel",
                        "--no-index",
                        "--no-deps",
                        "--no-build-isolation",
                        "--wheel-dir",
                        str(self.dist),
                        str(self.stage),
                    ],
                    root,
                )
                upgraded = next(self.dist.glob("gajaestack-0.1.1-*.whl"))
                self.assertNotEqual(upgraded.read_bytes(), self.wheel.read_bytes())
                lock.write_text(
                    f"gajaestack @ {upgraded.as_uri()} --hash=sha256:{hashlib.sha256(upgraded.read_bytes()).hexdigest()}\n"
                )
                self.run_command(install, root, env)
                result = self.run_command(
                    [
                        python,
                        "-B",
                        "-c",
                        "from gajaestack import __version__, UPGRADE_MARKER; print(__version__, UPGRADE_MARKER)",
                    ],
                    root,
                    env,
                )
                self.assertEqual(result.stdout.strip(), "0.1.1 distinct-local-release")
                self.assertIn(
                    "distinct-guidance-release",
                    (skill_root / "native-quality/SKILL.md").read_text(),
                )
                self.assertEqual(host_config.read_bytes(), host_before)
                if GJC:
                    # Selection and consumer-owned bytes survive a distinct pinned upgrade.
                    reobserved = self.run_command(
                        [GJC, "skills", "discover", "--source", "all", "--json"],
                        root,
                        env,
                    )
                    reobserved_candidates = json.loads(reobserved.stdout)["candidates"]
                    reobserved_kit_paths = {
                        Path(item["path"])
                        for item in reobserved_candidates
                        if str(skill_root) in item["path"]
                    }
                    self.assertEqual(
                        reobserved_kit_paths, {skill_root / "native-quality/SKILL.md"}
                    )
                    reobserved_selected = next(
                        item
                        for item in reobserved_candidates
                        if Path(item["path"]) == skill_root / "native-quality/SKILL.md"
                    )
                    self.assertIn(
                        reobserved_selected["description"],
                        (skill_root / "native-quality/SKILL.md").read_text(
                            encoding="utf-8"
                        ),
                    )
                    reobserved_names = {item["name"] for item in reobserved_candidates}
                    self.assertIn("consumer-notes", reobserved_names)
                    self.assertEqual(consumer_skill.read_bytes(), consumer_before)
                    self.assertEqual(host_config.read_bytes(), host_before)
                self.run_command(install + ["--force-reinstall"], root, env)
            finally:
                version_file.write_text(original)
                skill_file.write_text(original_skill)
            self.run_command(
                [python, "-B", "-m", "pip", "uninstall", "-y", "gajaestack"], root, env
            )
            self.run_command(
                [
                    python,
                    "-B",
                    "-c",
                    "import importlib.util; assert importlib.util.find_spec('gajaestack') is None",
                ],
                root,
                env,
            )
            self.run_command(
                [python, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                root,
                env,
            )

    def test_optional_resources_execute_without_source_adoption(self):
        """Exercise the RERG-shaped example against an isolated application fixture."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "consumer"
            root.mkdir()
            site = base / "site"
            self.run_command(
                [
                    PYTHON,
                    "-B",
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--no-deps",
                    "--no-compile",
                    "--target",
                    str(site),
                    str(self.wheel),
                ],
                root,
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(site) + os.pathsep + str(root)
            env["HYPOTHESIS_STORAGE_DIRECTORY"] = str(base / "hypothesis")
            application = root / "rerg"
            application.mkdir()
            (application / "__init__.py").write_text("")
            decoder = application / "raw_derivation.py"
            decoder.write_text(
                "from urllib.parse import unquote_to_bytes\n"
                "def _percent_decode(value: str) -> str:\n"
                "    return unquote_to_bytes(value).decode('utf-8', errors='replace')\n"
            )
            (application / "path_query.py").write_text(
                "def segment_count(path: str) -> int:\n"
                "    return len([part for part in path.split('/') if part])\n"
            )
            mypy = [
                PYTHON,
                "-B",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy-cache"),
                "--config-file",
                str(site / "gajaestack/mypy.ini"),
            ]
            self.run_command(mypy, root, env)
            properties = [
                PYTHON,
                "-B",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                str(site / "gajaestack/test_percent_decoder_properties.py"),
            ]
            self.run_command(properties, root, env)
            decoder.write_text(
                "def _percent_decode(value: str) -> str:\n    return 0\n"
            )
            rejected_type = subprocess.run(
                mypy, cwd=root, env=env, text=True, capture_output=True
            )
            self.assertNotEqual(rejected_type.returncode, 0)
            self.assertIn("return-value", rejected_type.stdout)
            decoder.write_text(
                "def _percent_decode(value: str) -> str:\n    return ''\n"
            )
            rejected_property = subprocess.run(
                properties, cwd=root, env=env, text=True, capture_output=True
            )
            self.assertNotEqual(rejected_property.returncode, 0)
            self.assertIn("AssertionError: assert '' ==", rejected_property.stdout)
            self.assertIn(
                "test_percent_decoder_matches_unquote", rejected_property.stdout
            )
            self.assertFalse((root / ".hypothesis").exists())
            self.assertFalse((root / ".mypy_cache").exists())
            self.assertFalse((root / ".pytest_cache").exists())

    def contributor_fixture(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        repository = Path(temporary.name) / "repository"
        root = repository / "consumer"
        root.mkdir(parents=True)
        site = root / ".venv/lib/site-packages"
        self.run_command(
            [
                PYTHON,
                "-B",
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                "--no-compile",
                "--target",
                str(site),
                str(self.wheel),
            ],
            root,
        )
        env = dict(os.environ, PYTHONPATH=str(site), PYTHONDONTWRITEBYTECODE="1")
        env["PATH"] = str(Path(PYTHON).parent) + os.pathsep + env["PATH"]
        env.update(
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_AUTHOR_NAME="test",
            GIT_AUTHOR_EMAIL="test@example.invalid",
            GIT_COMMITTER_NAME="test",
            GIT_COMMITTER_EMAIL="test@example.invalid",
        )
        (root / ".gitignore").write_text(".venv/\nignored.py\n")
        (root / ".gajaestack").mkdir()
        (root / ".gajaestack/routing.toml").write_text(
            '[python]\nschema_version=1\nruff_paths=["src"]\nruff_config="ruff.toml"\n'
        )
        (root / "ruff.toml").write_text('exclude=["excluded.py"]\n')
        (root / "src").mkdir()
        for name in ("a.py", "old.py", "deleted.py"):
            (root / "src" / name).write_text("value = 1\n")
        (root / "src/untouched.py").write_text("value = undefined_name\n")
        self.run_command(["git", "init", "-q", str(repository)], root, env)
        self.run_command(["git", "add", "."], root, env)
        self.run_command(["git", "commit", "-qm", "base"], root, env)
        command = [PYTHON, "-B", str(site / "bin/gajaestack-python-check")]
        return repository, root, env, command

    def test_installed_contributor_net_scope_failure_recovery_and_expansion(self):
        repository, root, env, command = self.contributor_fixture()

        def git(*args):
            return self.run_command(["git", *args], root, env).stdout.strip()

        base = git("rev-parse", "HEAD")
        git("config", "diff.relative", "true")
        git("branch", "target")
        git("checkout", "-qb", "topic")
        (root / "src/a.py").write_text("value = 2\n")
        git("add", ".")
        git("commit", "-qm", "topic")
        git("checkout", "target")
        (root / "src/reference-only.py").write_text("bad = undefined_name\n")
        git("add", ".")
        git("commit", "-qm", "diverged target")
        target = git("rev-parse", "HEAD")
        git("checkout", "topic")
        git("mv", "src/old.py", "src/renamed 한 글.py")
        (root / "src/deleted.py").unlink()
        (root / "src/staged.py").write_text("value = 3\n")
        git("add", "src/staged.py")
        (root / "src/local\n한 글.py").write_text("value = 4\n")
        (root / "src/a.py").write_text("value = 5\n")
        (root / "src/ignored.py").write_text("bad = undefined_name\n")
        (root / "src/excluded.py").write_text("bad = undefined_name\n")
        (root / "outside.py").write_text("bad = undefined_name\n")
        selected = [*command, "--reference-branch", "target"]
        passed = self.run_command(selected, root, env)
        report = passed.stdout
        baseline = json.loads(
            next(
                line.split(": ", 1)[1]
                for line in report.splitlines()
                if line.startswith("Contributor baseline:")
            )
        )
        self.assertEqual((baseline["resolved"], baseline["merge_base"]), (target, base))
        paths = json.loads(
            next(
                line.split(": ", 1)[1]
                for line in report.splitlines()
                if line.startswith("Contributor lint paths")
            )
        )
        self.assertCountEqual(
            paths,
            [
                "src/a.py",
                "src/renamed 한 글.py",
                "src/staged.py",
                "src/local\n한 글.py",
                "src/excluded.py",
            ],
        )
        self.assertNotIn("scope expanded", report)
        self.assertNotIn(
            str(root / "src/excluded.py"), report.split("Native Ruff scope", 1)[1]
        )
        (root / "src/a.py").write_text("bad = undefined_name\n")
        rejected = self.run_command(selected, root, env, expected=1)
        self.assertIn("F821", rejected.stdout)
        (root / "src/a.py").write_text("value = 5\n")
        self.run_command(selected, root, env)
        # Reverted current bytes do not replay a committed or staged edit.
        (root / "src/a.py").write_text("value = 1\n")
        reverted = self.run_command(selected, root, env)
        paths = json.loads(
            next(
                line.split(": ", 1)[1]
                for line in reverted.stdout.splitlines()
                if line.startswith("Contributor lint paths")
            )
        )
        self.assertNotIn("src/a.py", paths)
        (root / "ruff.toml").write_text('exclude=["excluded.py"]\n# changed policy\n')
        expanded = self.run_command(selected, root, env, expected=1)
        self.assertIn("scope expanded", expanded.stdout)
        self.assertIn("src/untouched.py", expanded.stdout)
        git("add", ".")
        git("commit", "-qm", "current")
        empty = self.run_command([*command, "--baseline-commit", "HEAD"], root, env)
        self.assertIn("No coverage", empty.stdout)
        self.assertNotIn("All checks passed", empty.stdout)
        full = self.run_command([*command, "--full"], root, env, expected=1)
        self.assertIn("untouched.py", full.stdout)

    def test_installed_contributor_rejects_invalid_and_ambiguous_history(self):
        repository, root, env, command = self.contributor_fixture()

        def git(*args):
            return self.run_command(["git", *args], root, env).stdout.strip()

        git("branch", "ambiguous")
        git("tag", "ambiguous")
        for args in (
            ["--reference-branch", "absent"],
            ["--reference-branch", "ambiguous"],
            ["--baseline-commit", "absent"],
            ["--baseline-commit", ""],
            ["--reference-branch", "HEAD", "--baseline-commit", "HEAD"],
            ["--full", "--reference-branch", "HEAD"],
        ):
            with self.subTest(args=args):
                self.run_command([*command, *args], root, env, expected=2)
        tree = git("rev-parse", "HEAD^{tree}")
        unrelated = git("commit-tree", tree, "-m", "unrelated")
        result = subprocess.run(
            [*command, "--reference-branch", unrelated],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        base = git("rev-parse", "HEAD")
        left = git("commit-tree", tree, "-p", base, "-m", "left")
        right = git("commit-tree", tree, "-p", base, "-m", "right")
        merge_left = git(
            "commit-tree", tree, "-p", left, "-p", right, "-m", "merge left"
        )
        merge_right = git(
            "commit-tree", tree, "-p", right, "-p", left, "-m", "merge right"
        )
        git("update-ref", "refs/heads/criss-cross", merge_left)
        git("checkout", "criss-cross")
        ambiguous = self.run_command(
            [*command, "--reference-branch", merge_right], root, env, expected=2
        )
        self.assertIn("exactly one merge base", ambiguous.stderr)
        shallow = repository.parent / "shallow"
        self.run_command(
            ["git", "clone", "-q", "--depth=1", repository.as_uri(), str(shallow)],
            root,
            env,
        )
        error = self.run_command(
            [*command, "--reference-branch", "HEAD"],
            shallow / "consumer",
            env,
            expected=2,
        )
        self.assertIn("non-shallow", error.stderr)
        outside = repository.parent / "outside"
        outside.mkdir()
        result = subprocess.run(
            [*command, "--reference-branch", "HEAD"],
            cwd=outside,
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a git repository", result.stderr)

    def test_contributor_deleted_declared_file_and_native_exclusion_have_no_coverage(
        self,
    ):
        repository, root, env, command = self.contributor_fixture()
        facts = root / ".gajaestack/routing.toml"
        facts.write_text(
            '[python]\nschema_version=1\nruff_paths=["src/old.py"]\nruff_config="ruff.toml"\n'
        )
        self.run_command(["git", "add", "."], root, env)
        self.run_command(["git", "commit", "-qm", "file scope"], root, env)
        (root / "src/old.py").unlink()
        result = self.run_command([*command, "--baseline-commit", "HEAD"], root, env)
        self.assertIn("No coverage", result.stdout)
        (root / "src/old.py").write_text("value = 1\n")
        facts.write_text(
            '[python]\nschema_version=1\nruff_paths=["."]\nruff_config="ruff.toml"\n'
        )
        self.run_command(["git", "add", "."], root, env)
        self.run_command(["git", "commit", "-qm", "root scope"], root, env)
        # Ignored installed package traversal must not leak into root scope.
        (root / ".venv/escape.py").symlink_to("/dev/null")
        (root / "src/excluded.py").write_text("bad = undefined_name\n")
        result = self.run_command(
            [*command, "--baseline-commit", "HEAD", "--timing"], root, env
        )
        self.assertIn("native Ruff exclusions select no files", result.stdout)
        self.assertNotIn("All checks passed", result.stdout)
        self.assertRegex(result.stderr, r"timing: ruff: .*files=0, exit=0")
        (root / ".gitignore").write_text(".venv/\nignored.py\n.local-ruff.toml\n")
        (root / ".local-ruff.toml").write_text('exclude=["excluded.py"]\n')
        (root / "ruff.toml").write_text('extend=".local-ruff.toml"\n')
        self.run_command(["git", "add", "."], root, env)
        self.run_command(
            ["git", "commit", "-qm", "ignored policy dependency"], root, env
        )
        (root / "src/a.py").write_text("value = 2\n")
        result = self.run_command(
            [*command, "--baseline-commit", "HEAD"], root, env, expected=1
        )
        self.assertIn("unenumerable Ruff config dependencies", result.stdout)
        self.assertIn("src/untouched.py", result.stdout)

    def test_installed_routing_scb_check_advisory_selection_validation(self):
        """scb-check is consumer-selected advisory; installing the kit installs no scb-check."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "consumer"
            root.mkdir()
            site = base / "site"
            self.run_command(
                [
                    PYTHON,
                    "-B",
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--no-deps",
                    "--no-compile",
                    "--target",
                    str(site),
                    str(self.wheel),
                ],
                root,
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(site)
            # The kit ships no scb-check module, entry point, or executable.
            with zipfile.ZipFile(self.wheel) as archive:
                wheel_names = archive.namelist()
                entrypoints = archive.read(
                    next(
                        name
                        for name in wheel_names
                        if name.endswith(".dist-info/entry_points.txt")
                    )
                ).decode()
            self.assertFalse(any("scb" in name.lower() for name in wheel_names))
            self.assertNotIn("scb", entrypoints.lower())
            routing = site / "bin" / "gajaestack-routing"
            self.assertTrue(routing.is_file())
            self.assertFalse(
                any("scb" in path.name.lower() for path in (site / "bin").iterdir())
            )
            self.run_command(
                [
                    PYTHON,
                    "-B",
                    "-S",
                    "-c",
                    "import importlib.util; "
                    "assert importlib.util.find_spec('scb_check') is None; "
                    "assert importlib.util.find_spec('scb') is None",
                ],
                root,
                env,
            )
            # Installed guidance exposes the scb-check command and advisory meaning.
            for guidance in (
                site / "gajaestack" / "routing" / "AGENTS.md",
                site / "gajaestack_guidance" / "native-quality" / "SKILL.md",
            ):
                text = guidance.read_text(encoding="utf-8").lower()
                self.assertIn("scb-check", text, str(guidance))
                self.assertIn("advisory", text, str(guidance))
                self.assertIn("scb_check_command", text, str(guidance))
            example = site / "gajaestack" / "routing.toml"
            self.assertTrue(example.is_file())
            facts_dir = root / ".gajaestack"
            facts_dir.mkdir()
            routing_toml = facts_dir / "routing.toml"

            def route(text):
                routing_toml.write_text(text, encoding="utf-8")
                return subprocess.run(
                    [str(routing), "--root", str(root)],
                    cwd=root,
                    env=env,
                    text=True,
                    capture_output=True,
                )

            # Absence of scb-check selection keeps the packaged example valid.
            default = route(example.read_text(encoding="utf-8"))
            self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
            self.assertIn(" (valid)", default.stdout)
            # Selection reuses the packaged facts example, replacing the unrelated
            # components and dropping their commands.
            base_facts = (
                example.read_text(encoding="utf-8")
                .replace(
                    'advisory = ["ruff-format", "mypy"]', 'advisory = ["scb-check"]'
                )
                .replace(
                    'selected_components = ["mypy", "routing", "ruff"]',
                    'selected_components = ["scb-check"]\n'
                    'scb_check_command = "scb-check check src"',
                )
            )
            facts_text = "".join(
                line
                for line in base_facts.splitlines(keepends=True)
                if not line.startswith(
                    ("ruff_command", "ruff_format_command", "mypy_command")
                )
            )
            self.assertIn('advisory = ["scb-check"]', facts_text)
            self.assertIn('selected_components = ["scb-check"]', facts_text)
            self.assertIn('scb_check_command = "scb-check check src"', facts_text)
            self.assertIn('python_version = "3.12"', facts_text)
            selected = route(facts_text)
            self.assertEqual(selected.returncode, 0, selected.stdout + selected.stderr)
            self.assertIn(" (valid)", selected.stdout)
            # Selection without the command fact is a consumer action, not a rewrite.
            missing_command = "".join(
                line
                for line in facts_text.splitlines(keepends=True)
                if not line.startswith("scb_check_command")
            )
            rejected_command = route(missing_command)
            rejected_command_text = rejected_command.stdout + rejected_command.stderr
            self.assertEqual(rejected_command.returncode, 1, rejected_command_text)
            self.assertIn("scb", rejected_command_text.lower())
            # A pre-3.12 runtime cannot run the selected advisory command.
            old_python = facts_text.replace(
                'python_version = "3.12"', 'python_version = "3.11"'
            )
            rejected_python = route(old_python)
            rejected_python_text = rejected_python.stdout + rejected_python.stderr
            self.assertEqual(rejected_python.returncode, 1, rejected_python_text)
            self.assertIn("scb", rejected_python_text.lower())
            # scb-check is advisory-only: required-category selection is rejected.
            misplaced = facts_text.replace(
                'advisory = ["scb-check"]', "advisory = []"
            ).replace(
                'required = ["pytest", "ruff-check"]',
                'required = ["pytest", "ruff-check", "scb-check"]',
            )
            self.assertIn('required = ["pytest", "ruff-check", "scb-check"]', misplaced)
            rejected_required = route(misplaced)
            rejected_required_text = rejected_required.stdout + rejected_required.stderr
            self.assertEqual(rejected_required.returncode, 1, rejected_required_text)
            self.assertIn("scb", rejected_required_text.lower())


if __name__ == "__main__":
    unittest.main()
