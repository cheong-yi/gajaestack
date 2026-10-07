from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from python.check_changed_python import ScopeError, full_scope, ruff_check

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
        cls.artifacts = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.artifacts.cleanup)
        stage = Path(cls.artifacts.name) / "source"
        stage.mkdir()
        for name in ("pyproject.toml", "README.md", "package.json", "MANIFEST.in"):
            if (KIT / name).exists():
                shutil.copyfile(KIT / name, stage / name)
        for name in ("python", "skills"):
            shutil.copytree(KIT / name, stage / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        subprocess.run(
            [PYTHON, "-B", "-m", "pip", "wheel", "--no-index", "--no-deps",
             "--no-build-isolation", "--wheel-dir", cls.artifacts.name, str(stage)],
            check=True, capture_output=True, text=True,
        )
        cls.wheel = next(Path(cls.artifacts.name).glob("*.whl"))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "consumer"
        self.root.mkdir()
        self.site = self.base / "site"
        subprocess.run(
            [PYTHON, "-B", "-m", "pip", "install", "--no-index", "--no-deps",
             "--no-compile", "--target", str(self.site), str(self.wheel)],
            check=True, capture_output=True, text=True,
        )
        (self.root / ".gajaestack").mkdir()
        (self.root / "ruff.toml").write_text('lint.select = ["E", "F"]\n')
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
            "ruff_config": "ruff.toml",
        }
        self.selected = ["guard", "ruff", "required-ruff"]
        self.origins = {}
        self.env = os.environ.copy()
        self.env.pop("PYTHONHOME", None)
        self.env["PYTHONPATH"] = str(self.site)
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.env["PATH"] = RUFF_BIN + os.pathsep + self.env["PATH"]
        self.configure()
        self.facts()

    def configure(self, bound=True, guard=True):
        plugins = (" -p gajaestack.pytest_guard" if guard else "") + (" -p gajaestack.pytest_required_ruff" if bound else "")
        (self.root / "pytest.ini").write_text(
            "[pytest]\npythonpath = .\n"
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

    def facts_with_budget(self, snippet: str) -> None:
        """Insert extra lines at the head of the fixture's [fact] table."""
        path = self.root / ".gajaestack/routing.toml"
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace("[fact]\n", "[fact]\n" + snippet, 1), encoding="utf-8"
        )

    def run_native(self, *args, helper=False):
        command = [PYTHON, "-B"]
        command += ["-m", "gajaestack.check_changed_python"] if helper else ["-m", "pytest", "-q", "-s"]
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

    def test_no_write_boundary_overrides_ruff_fix_and_output_defaults(self):
        original = (self.root / "app.py").read_bytes()
        cases = (
            ("fix", 'fix = true\nlint.select = ["F"]\n', b"\nimport os\n"),
            ("fix-only", 'fix-only = true\nlint.select = ["F"]\n',
             b"\ndef bad():\n    return undefined_name\n"),
            ("output-file", 'lint.select = ["F"]\n',
             b"\ndef bad():\n    return undefined_name\n"),
        )
        for name, config, seed in cases:
            for helper in (True, False):
                with self.subTest(setting=name, helper=helper):
                    bad = original + seed
                    (self.root / "app.py").write_bytes(bad)
                    (self.root / "ruff.toml").write_text(config)
                    for marker in ("conftest-imported", "test-imported"):
                        (self.root / marker).unlink(missing_ok=True)
                    output = self.root / "unexpected-report.txt"
                    output.unlink(missing_ok=True)
                    self.env.pop("RUFF_OUTPUT_FILE", None)
                    if name == "output-file":
                        self.env["RUFF_OUTPUT_FILE"] = str(output)
                    result = self.run_native(*(["--full"] if helper else []), helper=helper)
                    self.assertEqual((self.root / "app.py").read_bytes(), bad)
                    self.assertFalse(output.exists())
                    self.assert_rejected_before_import(result)

    def test_no_write_quick_discovery_preserves_git_index(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        index = self.root / ".git/index"
        before = index.read_bytes()
        app = self.root / "app.py"
        status = app.stat()
        os.utime(app, ns=(status.st_atime_ns, status.st_mtime_ns + 2_000_000_000))
        result = self.run_native(helper=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(index.read_bytes(), before)

    def test_native_timing_preserves_rejection_and_checkout_bytes(self):
        self.env["GAJAESTACK_TIMING"] = "1"
        (self.root / "app.py").write_text("bad = undefined_name\n")
        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        result = self.run_native()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assert_rejected_before_import(result)
        self.assertIn("F821", result.stdout + result.stderr)
        self.assertIn("scope", result.stderr)
        self.assertIn("ruff", result.stderr.lower())
        self.assertIn("elapsed", result.stderr)
        self.assertEqual(before, {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        })

    def test_native_timing_pass_does_not_add_guard_writes(self):
        self.env["GAJAESTACK_TIMING"] = "1"
        (self.root / "conftest.py").write_text("")
        (self.root / "tests/test_app.py").write_text(
            "from app import twice\n"
            "def test_positive():\n    assert twice(3) == 6\n"
        )
        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        result = self.run_native()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("elapsed", result.stderr)
        self.assertEqual(before, {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        })

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

    def test_bytecode_and_cache_prerequisites_reject_before_import(self):
        env = self.env.copy()
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        result = subprocess.run(
            [PYTHON, "-m", "pytest", "-q"], cwd=self.root, env=env,
            text=True, capture_output=True, timeout=45,
        )
        self.assert_rejected_before_import(result)
        self.assertIn("launch Python with -B", result.stdout + result.stderr)
        config = self.root / "pytest.ini"
        config.write_text(config.read_text().replace("-p no:cacheprovider", ""))
        result = self.run_native()
        self.assert_rejected_before_import(result)
        self.assertIn("disable pytest cacheprovider", result.stdout + result.stderr)
        self.assertFalse((self.root / ".pytest_cache").exists())
        self.configure()
        self.assertEqual(self.run_native().returncode, 0)

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
        self.facts_with_budget(
            'completion_timeout_seconds = 1\ntest_command = "python -B -m pytest"\n'
        )
        result = self.run_native()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue((self.root / "conftest-imported").exists())
        self.assertIn("native-test-seed", result.stdout)

    def test_missing_assets_and_facts_fail_closed(self):
        for path in (self.root / ".gajaestack/routing.toml", self.site / "gajaestack/pytest_guard.py", self.site / "gajaestack/check_changed_python.py"):
            with self.subTest(path=path):
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

    def test_installed_quick_uses_consumer_cwd_beneath_git_root(self):
        subprocess.run(["git", "init", "-q"], cwd=self.base, check=True)
        (self.base / "ruff.toml").write_text('lint.select = ["E", "F"]\n')
        (self.base / "app.py").write_text("parent_bad = missing_name\n")
        (self.base / "tests").mkdir()
        (self.base / "tests/test_parent.py").write_text("parent_bad = missing_name\n")
        full = self.run_native("--full", helper=True)
        self.assertEqual(full.returncode, 0, full.stdout + full.stderr)
        quick = self.run_native(helper=True)
        self.assertEqual(quick.returncode, 0, quick.stdout + quick.stderr)
        self.assertIn("2 file(s)", quick.stdout)
        self.assertNotIn("parent_bad", quick.stdout + quick.stderr)

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

    def test_completion_budget_valid_when_absent_or_configured(self):
        self.configure(bound=False)
        self.selected = ["guard"]
        for snippet in (
            None,
            'completion_timeout_seconds = 600\ntest_command = "python -m pytest"\n',
        ):
            with self.subTest(snippet=snippet):
                self.facts()
                if snippet is not None:
                    self.facts_with_budget(snippet)
                result = self.run_native()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(
                    "prerequisites passed before protected collection",
                    result.stdout,
                )

    def test_invalid_completion_budget_rejects_before_protected_imports(self):
        (self.root / "protected_module.py").write_text(
            'from pathlib import Path\nPath("required-imported").write_text("yes")\n'
        )
        self.options["imports"] = ["protected_module"]
        for value in (
            "true",
            "false",
            "0",
            "-1",
            '"600"',
            "1.5",
            "1.0",
            "nan",
            "inf",
            "9007199254740992",
            "18446744073709551616",
        ):
            with self.subTest(value=value):
                self.facts()
                self.facts_with_budget(
                    f"completion_timeout_seconds = {value}\n"
                    'test_command = "python -m pytest"\n'
                )
                result = self.run_native()
                self.assert_rejected_before_import(result)
                self.assertFalse((self.root / "required-imported").exists())
                self.assertIn(
                    "completion_timeout_seconds must be an integer",
                    result.stdout + result.stderr,
                )

    def test_completion_budget_requires_nonblank_test_command(self):
        for snippet in (
            "completion_timeout_seconds = 600\n",
            'completion_timeout_seconds = 600\ntest_command = "   "\n',
        ):
            with self.subTest(snippet=snippet):
                self.facts()
                self.facts_with_budget(snippet)
                result = self.run_native()
                self.assert_rejected_before_import(result)
                self.assertIn(
                    "requires a nonblank fact.test_command",
                    result.stdout + result.stderr,
                )

    def test_completion_budget_outside_fact_rejects_before_protected_imports(self):
        path = self.root / ".gajaestack/routing.toml"
        original = path.read_text(encoding="utf-8")
        cases = {
            "root": original.replace(
                "[fact]\n", "completion_timeout_seconds = 600\n[fact]\n", 1
            ),
            "python": original.replace(
                "[python]\n", "[python]\ncompletion_timeout_seconds = 600\n", 1
            ),
            "nested": original.replace(
                "[python]\n",
                "[fact.extra]\ncompletion_timeout_seconds = 600\n[python]\n",
                1,
            ),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                path.write_text(text, encoding="utf-8")
                result = self.run_native()
                self.assert_rejected_before_import(result)
                self.assertIn(
                    "only as a direct [fact] key", result.stdout + result.stderr
                )
        path.write_text(original, encoding="utf-8")

    def test_full_scope_validates_completion_budget_before_dispatch(self):
        for snippet, needle in (
            (
                'completion_timeout_seconds = 0\ntest_command = "python -m pytest"\n',
                "completion_timeout_seconds must be an integer",
            ),
            (
                "completion_timeout_seconds = 600\n",
                "requires a nonblank fact.test_command",
            ),
        ):
            with self.subTest(snippet=snippet):
                self.facts()
                self.facts_with_budget(snippet)
                result = self.run_native("--full", helper=True)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(needle, result.stdout + result.stderr)
        self.facts()
        path = self.root / ".gajaestack/routing.toml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "[python]\n", "[python]\ncompletion_timeout_seconds = 600\n", 1
            ),
            encoding="utf-8",
        )
        result = self.run_native("--full", helper=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("only as a direct [fact] key", result.stdout + result.stderr)

    def test_installed_quick_mode_always_validates_facts(self):
        facts = self.root / ".gajaestack/routing.toml"
        facts.write_text(
            facts.read_text(encoding="utf-8").replace(
                "[fact]\n", "[fact]\ncompletion_timeout_seconds = 0\n", 1
            ),
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(
            [
                "git",
                "-c", "user.name=gajaestack-test",
                "-c", "user.email=gajaestack-test@example.invalid",
                "-c", "commit.gpgsign=false",
                "commit", "-qm", "seed",
            ],
            cwd=self.root,
            check=True,
        )
        # Installed code is not tracked by consumer Git: always validate full facts.
        result = self.run_native(helper=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("completion_timeout_seconds", result.stdout + result.stderr)
        # Touching the facts file expands quick mode; the read rejects the budget.
        facts.write_text(
            facts.read_text(encoding="utf-8") + "# touched\n", encoding="utf-8"
        )
        result = self.run_native(helper=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("completion_timeout_seconds", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
