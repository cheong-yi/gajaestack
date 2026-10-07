from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

import python.routing as routing

KIT_ROOT = Path(__file__).resolve().parents[1]
GUIDANCE = KIT_ROOT / "python/routing/AGENTS.md"
FACTS_EXAMPLE = KIT_ROOT / "python/routing.toml"


class RoutingValidationTests(unittest.TestCase):
    def test_checked_example_facts_validate_clean(self) -> None:
        self.assertEqual(routing.routing_policy_file_errors(FACTS_EXAMPLE), [])

    def test_root_delegate_reads_python_routing_toml(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "python").mkdir()
            policy = root / "python/routing.toml"
            policy.write_bytes(FACTS_EXAMPLE.read_bytes())
            self.assertEqual(routing.routing_policy_errors(root), [])
            policy.write_text(
                policy.read_text(encoding="utf-8").replace(
                    'test_command = "python -m pytest"\n', ""
                ),
                encoding="utf-8",
            )
            errors = routing.routing_policy_errors(root)
            self.assertTrue(
                any("fact must state quick and full local commands" in e for e in errors)
            )

    def test_missing_facts_report_read_error_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = sorted(path.name for path in root.iterdir())
            errors = routing.routing_policy_errors(root)
            self.assertTrue(any("cannot read routing policy TOML" in e for e in errors))
            self.assertEqual(sorted(path.name for path in root.iterdir()), before)

    def test_malformed_toml_reports_read_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory) / "routing.toml"
            policy.write_text("[[[ not toml", encoding="utf-8")
            errors = routing.routing_policy_file_errors(policy)
            self.assertEqual(len(errors), 1)
            self.assertIn("cannot read routing policy TOML", errors[0])


class RoutingResourceTests(unittest.TestCase):
    def test_guidance_resource_is_static_not_rendered(self) -> None:
        text = GUIDANCE.read_text(encoding="utf-8")
        self.assertTrue(text.strip())
        self.assertNotIn("{{", text)
        self.assertNotIn("}}", text)
        self.assertIn(".gajaestack/routing.toml", text)

    def test_static_guidance_references_upgrade_not_copy(self) -> None:
        text = GUIDANCE.read_text(encoding="utf-8")
        self.assertIn("upgrading the pinned native dependency", text)
        self.assertIn("not by editing or re-copying installed files", text)


class RoutingConsoleTests(unittest.TestCase):
    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = routing.main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_default_lists_labeled_named_resources(self) -> None:
        code, out, _ = self.run_main([])
        self.assertEqual(code, 0)
        lines = out.splitlines()
        labels = {}
        for line in lines:
            name, separator, path = line.partition(": ")
            self.assertTrue(separator, line)
            labels[name] = path
        self.assertEqual(set(labels), {"guidance", "facts-example"})
        self.assertEqual(labels["guidance"], str(GUIDANCE))
        self.assertEqual(labels["facts-example"], str(FACTS_EXAMPLE))
        self.assertTrue(Path(labels["guidance"]).is_file())
        self.assertTrue(Path(labels["facts-example"]).is_file())

    def test_guidance_prints_raw_path_only(self) -> None:
        code, out, _ = self.run_main(["--guidance"])
        self.assertEqual(code, 0)
        self.assertEqual(out, f"{GUIDANCE}\n")

    def test_root_absent_facts_fails_as_coverage_gap_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = sorted(path.name for path in root.iterdir())
            code, out, _ = self.run_main(["--root", str(root)])
            self.assertEqual(code, 2)
            self.assertIn("absent; unconfigured", out)
            self.assertIn(str(root / routing.CONSUMER_FACTS_RELATIVE), out)
            self.assertEqual(sorted(path.name for path in root.iterdir()), before)

    def test_root_valid_facts_pass_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            facts_dir = root / ".gajaestack"
            facts_dir.mkdir()
            facts = facts_dir / "routing.toml"
            facts.write_bytes(FACTS_EXAMPLE.read_bytes())
            before = facts.read_bytes()
            code, out, _ = self.run_main(["--root", str(root)])
            self.assertEqual(code, 0)
            self.assertIn("(valid)", out)
            self.assertEqual(facts.read_bytes(), before)
            self.assertEqual(sorted(path.name for path in root.iterdir()), [".gajaestack"])

    def test_root_invalid_facts_exit_one_with_errors_and_no_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            facts_dir = root / ".gajaestack"
            facts_dir.mkdir()
            facts = facts_dir / "routing.toml"
            facts.write_text(
                FACTS_EXAMPLE.read_text(encoding="utf-8").replace(
                    'test_command = "python -m pytest"\n', ""
                ),
                encoding="utf-8",
            )
            before = facts.read_bytes()
            code, out, _ = self.run_main(["--root", str(root)])
            self.assertEqual(code, 1)
            self.assertIn("fact must state quick and full local commands", out)
            self.assertEqual(facts.read_bytes(), before)

    def test_root_must_be_a_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            code, _, err = self.run_main(["--root", str(missing)])
            self.assertEqual(code, 2)
            self.assertIn("root is not a directory", err)

    def test_guidance_and_root_are_mutually_exclusive(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            self.run_main(["--guidance", "--root", "."])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
