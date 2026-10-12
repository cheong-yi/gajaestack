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


class ScbCheckRoutingTests(unittest.TestCase):
    """scb-check is an advisory-only independent component/check selection."""

    def validate(self, text: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            policy = Path(directory) / "routing.toml"
            policy.write_text(text, encoding="utf-8")
            return routing.routing_policy_file_errors(policy)

    def selected_policy(self) -> str:
        text = FACTS_EXAMPLE.read_text(encoding="utf-8")
        text = text.replace(
            'advisory = ["ruff-format", "mypy"]',
            'advisory = ["ruff-format", "mypy", "scb-check"]',
        )
        text = text.replace(
            'selected_components = ["mypy", "routing", "ruff"]',
            'selected_components = ["mypy", "routing", "ruff", "scb-check"]',
        )
        return text.replace(
            'test_command = "python -m pytest"\n',
            'test_command = "python -m pytest"\nscb_check_command = "scb run --native"\n',
        )

    def runtime_policy(self, version: str) -> str:
        return self.selected_policy().replace(
            'python_version = "3.12"', f'python_version = "{version}"'
        )

    def test_valid_independent_advisory_selection(self) -> None:
        self.assertEqual(self.validate(self.selected_policy()), [])

    def test_selected_requires_nonblank_command(self) -> None:
        text = self.selected_policy().replace(
            'scb_check_command = "scb run --native"\n', ""
        )
        errors = self.validate(text)
        self.assertTrue(
            any(
                "fact.scb_check_command must be a non-empty string" in error
                for error in errors
            ),
            errors,
        )
        for command in ("", "   "):
            with self.subTest(command=command):
                text = self.selected_policy().replace(
                    'scb_check_command = "scb run --native"\n',
                    f'scb_check_command = "{command}"\n',
                )
                errors = self.validate(text)
                self.assertTrue(
                    any(
                        "fact.scb_check_command must be a non-empty string" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_scb_check_is_advisory_only_category(self) -> None:
        for category in ("required", "on_demand"):
            with self.subTest(category=category):
                text = FACTS_EXAMPLE.read_text(encoding="utf-8").replace(
                    f"{category} = [", f'{category} = ["scb-check", '
                )
                errors = self.validate(text)
                self.assertTrue(
                    any(
                        "check 'scb-check' is advisory-only" in error
                        and f"remove it from {category}" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_python_version_boundaries(self) -> None:
        for version in ("3.12", "3.12.1", "3.13", "4.1"):
            with self.subTest(version=version):
                self.assertEqual(self.validate(self.runtime_policy(version)), [])
        rejected = (
            "3.11",
            "3.9",
            "latest",
            "3.12rc1",
            "3",
            "3.12.1.5",
            "9" * 20 + ".12",
        )
        for version in rejected:
            with self.subTest(version=version):
                errors = self.validate(self.runtime_policy(version))
                self.assertTrue(
                    any(
                        "fact.python_version must name a numeric Python runtime >= 3.12"
                        in error
                        for error in errors
                    ),
                    errors,
                )

    def test_advisory_and_component_selection_must_agree(self) -> None:
        text = self.selected_policy().replace(
            'selected_components = ["mypy", "routing", "ruff", "scb-check"]',
            'selected_components = ["mypy", "routing", "ruff"]',
        )
        errors = self.validate(text)
        self.assertTrue(
            any(
                "advisory selects 'scb-check' but fact.selected_components omits it"
                in error
                for error in errors
            ),
            errors,
        )
        text = (
            FACTS_EXAMPLE.read_text(encoding="utf-8")
            .replace(
                'selected_components = ["mypy", "routing", "ruff"]',
                'selected_components = ["mypy", "routing", "ruff", "scb-check"]',
            )
            .replace(
                'test_command = "python -m pytest"\n',
                'test_command = "python -m pytest"\n'
                'scb_check_command = "scb run --native"\n',
            )
        )
        errors = self.validate(text)
        self.assertTrue(
            any(
                "fact.selected_components selects 'scb-check' but advisory omits it"
                in error
                for error in errors
            ),
            errors,
        )

    def test_stale_command_rejected_and_deselection_restores_clean(self) -> None:
        text = FACTS_EXAMPLE.read_text(encoding="utf-8").replace(
            'test_command = "python -m pytest"\n',
            'scb_check_command = "stale command"\ntest_command = "python -m pytest"\n',
        )
        errors = self.validate(text)
        self.assertTrue(
            any("fact.scb_check_command must be removed" in error for error in errors),
            errors,
        )
        self.assertEqual(
            self.validate(text.replace('scb_check_command = "stale command"\n', "")),
            [],
        )


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
