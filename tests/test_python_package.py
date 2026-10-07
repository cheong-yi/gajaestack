from __future__ import annotations

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


@unittest.skipUnless(PYTHON and WHEELHOUSE, "set GAJAESTACK_PYTHON and GAJAESTACK_PYTHON_WHEELHOUSE for offline package acceptance")
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
        for name in ("pyproject.toml", "README.md", "AGENTS.md", "package.json", "MANIFEST.in"):
            if (KIT / name).exists():
                shutil.copyfile(KIT / name, cls.stage / name)
        for name in ("python", "skills", "docs"):
            shutil.copytree(KIT / name, cls.stage / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        # Deliberately poison the build tree: package inventory must exclude these.
        (cls.stage / ".private-token").write_text("never distribute")
        (cls.stage / "python/__pycache__").mkdir()
        (cls.stage / "python/__pycache__/private.pyc").write_bytes(b"private")
        cls.run_command([PYTHON, "-B", "-c", "import setuptools.build_meta as b; b.build_sdist('" + str(cls.dist) + "')"], cls.stage)
        cls.sdist = next(cls.dist.glob("*.tar.gz"))
        cls.run_command([PYTHON, "-B", "-m", "pip", "wheel", "--no-index", "--no-deps", "--no-build-isolation", "--wheel-dir", str(cls.dist), str(cls.sdist)], cls.base)
        cls.wheel = next(cls.dist.glob("*.whl"))

    @staticmethod
    def run_command(command, cwd, env=None, expected=0):
        result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, timeout=180)
        if result.returncode != expected:
            raise AssertionError(f"{command}: {result.returncode}\n{result.stdout}\n{result.stderr}")
        return result

    def test_inventory_native_entrypoints_and_version(self):
        with tarfile.open(self.sdist) as archive:
            source_names = archive.getnames()
        with zipfile.ZipFile(self.wheel) as archive:
            names = archive.namelist()
            metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
            metadata = archive.read(metadata_name).decode()
            entrypoints = archive.read(next(name for name in names if name.endswith(".dist-info/entry_points.txt"))).decode()
            self.assertNotIn("Requires-Dist:", metadata)
            self.assertNotIn("pytest11", entrypoints)
            for command in ("gajaestack-python-check", "gajaestack-imports", "gajaestack-routing"):
                self.assertIn(command, entrypoints)
            self.assertIn("Version: " + json.loads((KIT / "package.json").read_text())["version"], metadata)
        for name in source_names + names:
            for forbidden in ("__pycache__", ".pyc", ".private", "node_modules", ".gjc/", "ownership.json"):
                self.assertNotIn(forbidden, name)
        for name in ("gajaestack/pytest_guard.py", "gajaestack/pytest_required_ruff.py", "gajaestack/check_changed_python.py", "gajaestack/ruff.toml", "gajaestack/mypy.ini", "gajaestack/test_percent_decoder_properties.py"):
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
            lock.write_text(f"gajaestack @ {self.wheel.as_uri()} --hash=sha256:{hashlib.sha256(self.wheel.read_bytes()).hexdigest()}\n")
            install = [python, "-B", "-m", "pip", "install", "--no-index", "--no-deps", "--no-compile", "--require-hashes", "-r", str(lock)]
            self.run_command(install, root, env)
            initial_lock = lock.read_bytes()
            self.run_command(install + ["--force-reinstall"], root, env)
            self.assertEqual(initial_lock, lock.read_bytes())
            probe = self.run_command([python, "-B", "-c", "import importlib.util; assert importlib.util.find_spec('pytest') is None; from gajaestack import __version__; print(__version__)"], root, env)
            self.assertEqual(probe.stdout.strip(), "0.1.0")
            self.run_command([str(venv / "bin/gajaestack-imports"), "tomllib"], root, env)
            missing = subprocess.run([str(venv / "bin/gajaestack-python-check"), "--full"], cwd=root, env=env, text=True, capture_output=True)
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
                cwd=root, env=env, text=True, capture_output=True,
            )
            self.assertEqual(
                ruff_only.returncode, 0, ruff_only.stdout + ruff_only.stderr
            )
            self.assertIn("Full selected scope: 1 file(s)", ruff_only.stdout)
            self.run_command(
                [python, "-B", "-c", "import importlib.util; assert importlib.util.find_spec('pytest') is None"],
                root, env,
            )
            # Native tool provisioning is explicit and offline, separate from kit install.
            self.run_command([python, "-B", "-m", "pip", "install", "--no-index", "--find-links", WHEELHOUSE, "pytest==9.1.1"], root, env)
            (root / "test_native.py").write_text("def test_native():\n    assert 2 + 2 == 4\n")
            # Merely installing the kit does not activate any checks.
            self.run_command([python, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"], root, env)
            version_file = self.stage / "python/__init__.py"
            original = version_file.read_text()
            skill_file = self.stage / "skills/native-quality/SKILL.md"
            original_skill = skill_file.read_text()
            skill_root = Path(self.run_command(
                [python, "-B", "-c", "import gajaestack_guidance; print(next(iter(gajaestack_guidance.__path__)))"],
                root, env,
            ).stdout.strip())
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
            host_config = root / ".gjc/config.yml"
            host_config.write_text(
                "configSchemaVersion: 2\nskills:\n  customDirectories:\n    - "
                + os.path.relpath(skill_root, root) + "\n"
                + "  ignoredSkills:\n    - type-discipline\n    - verify-change\n"
            )
            host_before = host_config.read_bytes()
            if GJC:
                self.run_command(["git", "init", "-q"], root, env)
                discovered = self.run_command(
                    [GJC, "skills", "discover", "--source", "all", "--json"],
                    root, env,
                )
                candidates = json.loads(discovered.stdout)["candidates"]
                kit_paths = {
                    Path(item["path"])
                    for item in candidates
                    if str(skill_root) in item["path"]
                }
                self.assertEqual(
                    kit_paths, {skill_root / "native-quality/SKILL.md"}
                )
                self.assertTrue(
                    any(
                        item["path"].endswith(
                            ".gjc/skills/consumer-notes/SKILL.md"
                        )
                        for item in candidates
                    ),
                    "consumer-owned skill was not retained",
                )
            try:
                version_file.write_text(original.replace('0.1.0', '0.1.1') + '\nUPGRADE_MARKER = "distinct-local-release"\n')
                skill_file.write_text(original_skill + "\nLocal upgrade verification marker: distinct-guidance-release.\n")
                manifest = self.stage / "package.json"
                document = json.loads(manifest.read_text())
                document["version"] = "0.1.1"
                manifest.write_text(json.dumps(document))
                self.run_command([PYTHON, "-B", "-m", "pip", "wheel", "--no-index", "--no-deps", "--no-build-isolation", "--wheel-dir", str(self.dist), str(self.stage)], root)
                upgraded = next(self.dist.glob("gajaestack-0.1.1-*.whl"))
                lock.write_text(f"gajaestack @ {upgraded.as_uri()} --hash=sha256:{hashlib.sha256(upgraded.read_bytes()).hexdigest()}\n")
                self.run_command(install, root, env)
                result = self.run_command([python, "-B", "-c", "from gajaestack import __version__, UPGRADE_MARKER; print(__version__, UPGRADE_MARKER)"], root, env)
                self.assertEqual(result.stdout.strip(), "0.1.1 distinct-local-release")
                self.assertIn("distinct-guidance-release", (skill_root / "native-quality/SKILL.md").read_text())
                self.assertEqual(host_config.read_bytes(), host_before)
                self.run_command(install + ["--force-reinstall"], root, env)
            finally:
                version_file.write_text(original)
                skill_file.write_text(original_skill)
            self.run_command([python, "-B", "-m", "pip", "uninstall", "-y", "gajaestack"], root, env)
            self.run_command([python, "-B", "-c", "import importlib.util; assert importlib.util.find_spec('gajaestack') is None"], root, env)
            self.run_command([python, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"], root, env)

    def test_optional_resources_execute_without_source_adoption(self):
        """Exercise the RERG-shaped example against an isolated application fixture."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "consumer"
            root.mkdir()
            site = base / "site"
            self.run_command(
                [PYTHON, "-B", "-m", "pip", "install", "--no-index", "--no-deps",
                 "--no-compile", "--target", str(site), str(self.wheel)], root,
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
            mypy = [PYTHON, "-B", "-m", "mypy", "--cache-dir", str(base / "mypy-cache"),
                    "--config-file", str(site / "gajaestack/mypy.ini")]
            self.run_command(mypy, root, env)
            properties = [
                PYTHON, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                str(site / "gajaestack/test_percent_decoder_properties.py"),
            ]
            self.run_command(properties, root, env)
            decoder.write_text("def _percent_decode(value: str) -> str:\n    return 0\n")
            rejected_type = subprocess.run(mypy, cwd=root, env=env, text=True, capture_output=True)
            self.assertNotEqual(rejected_type.returncode, 0)
            self.assertIn("return-value", rejected_type.stdout)
            decoder.write_text("def _percent_decode(value: str) -> str:\n    return ''\n")
            rejected_property = subprocess.run(properties, cwd=root, env=env, text=True, capture_output=True)
            self.assertNotEqual(rejected_property.returncode, 0)
            self.assertIn("AssertionError: assert '' ==", rejected_property.stdout)
            self.assertIn("test_percent_decoder_matches_unquote", rejected_property.stdout)
            self.assertFalse((root / ".hypothesis").exists())
            self.assertFalse((root / ".mypy_cache").exists())
            self.assertFalse((root / ".pytest_cache").exists())


if __name__ == "__main__":
    unittest.main()
