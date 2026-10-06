from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts.check_changed_python import ScopeError, full_scope, ruff_check

KIT = Path(__file__).resolve().parents[1]
PYTHON = os.environ.get("GAJAESTACK_PYTHON")
RUFF_BIN = os.environ.get("GAJAESTACK_RUFF_BIN")


@unittest.skipUnless(PYTHON and RUFF_BIN, "set GAJAESTACK_PYTHON and GAJAESTACK_RUFF_BIN to installed real tools")
class PythonMechanicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.version = subprocess.check_output(
            [PYTHON, "-B", "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"], text=True
        ).strip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "consumer"
        self.root.mkdir()
        for source, destination in (
            ("python/pytest_guard.py", ".gajaestack/python/pytest_guard.py"),
            ("python/pytest_required_ruff.py", ".gajaestack/python/pytest_required_ruff.py"),
            ("scripts/check_changed_python.py", ".gajaestack/scripts/check_changed_python.py"),
            ("python/ruff.toml", ".gajaestack/python-trial/ruff.toml"),
        ):
            target = self.root / destination
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(KIT / source, target)
        (self.root / "app.py").write_text("def twice(value):\n    return value * 2\n")
        (self.root / "tests").mkdir()
        (self.root / "conftest.py").write_text(
            'from pathlib import Path\nPath("conftest-imported").write_text("yes")\n'
        )
        (self.root / "tests/test_app.py").write_text(
            'from pathlib import Path\nfrom app import twice\n'
            'Path("test-imported").write_text("yes")\n'
            'def test_positive():\n    assert twice(3) == 6\n'
            'def test_zero():\n    assert twice(0) == 0\n'
        )
        self.options = {
            "schema_version": 1, "python_version": self.version,
            "imports": [], "executables": [], "root": str(self.root),
            "ruff_paths": ["app.py", "tests"],
            "ruff_config": ".gajaestack/python-trial/ruff.toml",
        }
        self.selected = ["guard", "ruff", "required-ruff"]
        self.origins = {}
        self.env = os.environ.copy()
        self.env.pop("PYTHONHOME", None)
        self.env.pop("PYTHONPATH", None)
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.env["PATH"] = RUFF_BIN + os.pathsep + self.env["PATH"]
        self.configure()
        self.facts()

    def configure(self, bound=True, guard=True):
        plugins = (" -p pytest_guard" if guard else "") + (" -p pytest_required_ruff" if bound else "")
        (self.root / "pytest.ini").write_text(
            "[pytest]\npythonpath = .gajaestack/python .\n"
            f"addopts = --disable-plugin-autoload -p no:cacheprovider{plugins}\n"
            "testpaths = tests\n"
        )

    def facts(self):
        text = 'required = ["ruff-check"]\n[fact]\nschema_version = 1\n'
        text += f"python_version = {json.dumps(self.version)}\nselected_components = {json.dumps(self.selected)}\n"
        if "required-ruff" in self.selected:
            text += 'required_ruff_before_pytest = "active"\n'
        text += "[python]\n" + "".join(f"{key} = {json.dumps(value)}\n" for key, value in self.options.items())
        if self.origins:
            text += "[python.module_origins]\n" + "".join(f"{json.dumps(key)} = {json.dumps(value)}\n" for key, value in self.origins.items())
        (self.root / ".gajaestack/routing.toml").write_text(text)

    def run_native(self, *args, helper=False):
        command = [PYTHON, "-B"]
        command += [".gajaestack/scripts/check_changed_python.py"] if helper else ["-m", "pytest", "-q", "-s"]
        return subprocess.run(command + list(args), cwd=self.root, env=self.env, text=True, capture_output=True, timeout=45)

    def assert_rejected_before_import(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.root / "conftest-imported").exists(), result.stdout + result.stderr)
        self.assertFalse((self.root / "test-imported").exists())

    def test_focused_full_and_collect_only_are_guarded(self):
        for args in ((), ("tests/test_app.py::test_positive",), ("--collect-only",)):
            with self.subTest(args=args):
                result = self.run_native(*args)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(result.stdout.count("required Ruff full selected scope"), 1)
                self.assertEqual(result.stdout.count("prerequisites passed before protected collection"), 1)
                self.assertTrue((self.root / "conftest-imported").exists())
                self.assertTrue((self.root / "test-imported").exists())
                self.assertFalse((self.root / ".ruff_cache").exists())
                self.assertFalse((self.root / ".pytest_cache").exists())
                self.assertFalse((self.root / "__pycache__").exists())

    def test_ruff_failure_prevents_protected_imports_and_keeps_exit(self):
        (self.root / "app.py").write_text("bad = undefined_name\n")
        direct = self.run_native("--full", helper=True)
        result = self.run_native()
        self.assertEqual(direct.returncode, 1, direct.stdout + direct.stderr)
        self.assertEqual(result.returncode, direct.returncode)
        self.assert_rejected_before_import(result)

    def test_guard_only_and_both_unbound_do_not_require_ruff(self):
        self.configure(bound=False)
        self.env["PATH"] = "/usr/bin:/bin"
        (self.root / "app.py").write_text("import os\ndef twice(value):\n    return value * 2\n")
        (self.root / "unselected.py").write_text("bad = undefined_name\n")
        for selected in (["guard"], ["guard", "ruff"]):
            self.selected = selected
            self.facts()
            result = self.run_native()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("required Ruff", result.stdout)

    def test_missing_executable_and_import_fail_before_collection(self):
        for field, value in (("executables", ["gajaestack_missing_executable_179126"]), ("imports", ["gajaestack_missing_module_179126"])):
            with self.subTest(field=field):
                self.options[field] = value
                self.facts()
                result = self.run_native()
                self.assert_rejected_before_import(result)
                self.assertIn("missing", result.stdout + result.stderr)
                self.options[field] = []

    def test_initialization_failure_is_not_discovery_success(self):
        (self.root / "broken.py").write_text('raise RuntimeError("seeded initialization failure")\n')
        self.options["imports"] = ["broken"]
        self.origins = {"broken": "broken.py"}
        self.facts()
        result = self.run_native()
        self.assert_rejected_before_import(result)
        self.assertIn("initialization failed", result.stdout + result.stderr)

    def test_shadow_dotted_package_parent_is_not_executed(self):
        (self.root / "shadow").mkdir()
        (self.root / "shadow/__init__.py").write_text('from pathlib import Path\nPath("shadow-effect").write_text("bad")\n')
        (self.root / "shadow/child.py").write_text("value = 1\n")
        (self.root / "approved").mkdir()
        (self.root / "approved/child.py").write_text("value = 1\n")
        self.options["imports"] = ["shadow.child"]
        self.origins = {"shadow.child": "approved/child.py"}
        self.facts()
        result = self.run_native()
        self.assert_rejected_before_import(result)
        self.assertFalse((self.root / "shadow-effect").exists())
        self.assertIn("unexpected import origin", result.stdout + result.stderr)

    def test_runtime_root_and_prefix_mismatches_reject(self):
        for field in ("python_version", "root", "prefix", "base_prefix", "source_root"):
            with self.subTest(field=field):
                original = self.options.get(field)
                self.options[field] = "0.0" if field == "python_version" else str(self.base / "wrong")
                self.facts()
                self.assert_rejected_before_import(self.run_native())
                if original is None:
                    self.options.pop(field)
                else:
                    self.options[field] = original

    def test_native_test_failure_is_not_hidden(self):
        (self.root / "tests/test_app.py").write_text("def test_fail():\n    assert False, 'native-test-seed'\n")
        result = self.run_native()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue((self.root / "conftest-imported").exists())
        self.assertIn("native-test-seed", result.stdout)

    def test_missing_assets_and_facts_fail_closed(self):
        for name in (".gajaestack/routing.toml", ".gajaestack/python/pytest_guard.py", ".gajaestack/scripts/check_changed_python.py"):
            with self.subTest(name=name):
                path = self.root / name
                content = path.read_bytes()
                path.unlink()
                self.assert_rejected_before_import(self.run_native())
                path.write_bytes(content)

    def test_binding_requires_loaded_guard_and_explicit_selection(self):
        self.configure(guard=False)
        self.assert_rejected_before_import(self.run_native())
        self.configure()
        self.selected = ["guard", "ruff"]
        self.facts()
        self.assert_rejected_before_import(self.run_native())
        self.configure(bound=False)
        self.selected = ["guard", "ruff", "required-ruff"]
        (self.root / "effect.py").write_text('from pathlib import Path\nPath("policy-effect").write_text("bad")\n')
        self.options["imports"] = ["effect"]
        self.facts()
        self.assert_rejected_before_import(self.run_native())
        self.assertFalse((self.root / "policy-effect").exists())

    def test_unsafe_basetemp_preserves_existing_content(self):
        target = self.base / "retained"
        target.mkdir()
        (target / "keep").write_text("preserved")
        for path in (target, self.root / "temporary"):
            result = self.run_native("--basetemp", str(path))
            self.assert_rejected_before_import(result)
        self.assertEqual((target / "keep").read_text(), "preserved")

    def test_full_scope_does_not_need_git_and_excludes_unselected_errors(self):
        (self.root / "unselected.py").write_text("bad = undefined_name\n")
        self.assertFalse((self.root / ".git").exists())
        result = self.run_native("--full", helper=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("2 file(s)", result.stdout)
        self.env["PATH"] = "/usr/bin:/bin"
        result = self.run_native("--full", helper=True)
        self.assertEqual(result.returncode, 127, result.stdout + result.stderr)

    def test_empty_missing_and_escaping_scope_reject(self):
        for paths in ([], ["absent.py"], ["../escape.py"]):
            self.options["ruff_paths"] = paths
            self.facts()
            result = self.run_native("--full", helper=True)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        with self.assertRaises(ScopeError):
            full_scope(self.root, self.root / ".gajaestack/routing.toml")
        self.assertEqual(ruff_check(self.root, "missing", []), 2)

    def test_changed_shared_policy_expands_to_full_selected_scope(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / "app.py").write_text("bad = undefined_name\n")
        result = self.run_native("--path", "tests", helper=True)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("expanded to full selected scope", result.stdout)
        self.assertIn("app.py", result.stdout)


if __name__ == "__main__":
    unittest.main()
