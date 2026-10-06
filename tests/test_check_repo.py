from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.check_repo import check, main, routing_policy_errors, routing_policy_file_errors


CORE_FACTS = (
    'python_version = "3.12"',
    'test_command = "python -m pytest"',
    'affected_test_command = "python -m pytest tests/rerg/test_percent_decoder.py"',
    'mypy_command = "mypy --config-file .gajaestack/python-trial/mypy.ini"',
    "ci_jobs_added = false",
    "pcd_is_enforcement = false",
)
RUFF_FACTS = (
    'ruff_command = "python .gajaestack/scripts/check_changed_python.py"',
    'ruff_format_command = "ruff format --check --config .gajaestack/python-trial/ruff.toml rerg/raw_derivation.py tests/rerg/test_percent_decoder.py"',
)


class CheckRepoTests(unittest.TestCase):
    def make_repo(
        self, root: Path, *, metadata: str | None = None, link: str = "README.md"
    ) -> None:
        skills = root / "skills" / "example"
        skills.mkdir(parents=True)
        frontmatter = (
            metadata
            or "---\nname: example\ndescription: Example skill.\nproblem: Example problem.\nuse_when: Example use case.\nwhen_to_run: Example timing.\n---\n\nBody.\n"
        )
        (skills / "SKILL.md").write_text(frontmatter, encoding="utf-8")
        (root / "README.md").write_text(f"[Example]({link})\n", encoding="utf-8")
        (root / "python").mkdir()
        (root / "python/routing.toml").write_bytes(
            (Path(__file__).resolve().parents[1] / "python/routing.toml").read_bytes()
        )

    def write_facts(
        self,
        root: Path,
        facts: list[str],
        *,
        without_ruff_categories: bool = False,
    ) -> None:
        policy_path = root / "python/routing.toml"
        policy = policy_path.read_text(encoding="utf-8")
        head, marker, _ = policy.partition("[fact]")
        if without_ruff_categories:
            head = head.replace('required = ["pytest", "ruff-check"]', 'required = ["pytest"]')
            head = head.replace('advisory = ["ruff-format", "mypy"]', 'advisory = []')
            head = head.replace(
                'on_demand = ["mutation-testing", "profiling", "adversarial-review"]',
                "on_demand = []",
            )
        runtime = ""
        if any('"guard"' in line or '"ruff"' in line for line in facts):
            runtime = (
                '\n[python]\nschema_version = 1\npython_version = "3.12"\n'
                'imports = []\nexecutables = []\nruff_paths = ["app.py"]\n'
                'ruff_config = ".gajaestack/python-trial/ruff.toml"\n'
            )
        policy_path.write_text(
            head + marker + "\n" + "".join(f"{line}\n" for line in facts) + runtime,
            encoding="utf-8",
        )

    def test_accepts_valid_skill_and_local_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.assertEqual(check(root), [])

    def test_typescript_only_facts_need_no_python_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.write_facts(root, [
                "schema_version = 1",
                'selected_components = ["typescript", "typescript-guard"]',
                'test_command = "bun test"',
                'affected_test_command = "bun .gajaestack/typescript/check.ts --quick"',
                "ci_jobs_added = false", "pcd_is_enforcement = false",
                "[typescript]", "schema_version = 1",
                "typecheck = true", "lint = false", 'tsconfig = "tsconfig.json"',
            ], without_ruff_categories=True)
            policy = root / "python/routing.toml"
            text = policy.read_text().replace('required = ["pytest"]', 'required = ["ts-typecheck"]')
            policy.write_text(text)
            self.assertEqual(check(root), [])
            policy.write_text(text.replace("typecheck = true", "typecheck = false"))
            self.assertTrue(any("selects no checks" in error for error in check(root)))

    def test_rejects_missing_skill_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, metadata="---\nname: example\n---\n\nBody.\n")
            errors = check(root)
            self.assertTrue(any("missing required metadata field 'problem'" in e for e in errors))

    def test_rejects_overlapping_routing_policy_categories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            policy = (Path(__file__).resolve().parents[1] / "python/routing.toml").read_text()
            (root / "python/routing.toml").write_text(
                policy.replace('advisory = ["ruff-format", "mypy"]', 'advisory = ["ruff-check"]'),
                encoding="utf-8",
            )
            self.assertTrue(
                any("appears in both required and advisory" in error for error in check(root))
            )

    def test_rejects_missing_conditional_trigger_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            policy = (Path(__file__).resolve().parents[1] / "python/routing.toml").read_text()
            (root / "python/routing.toml").write_text(
                policy.replace(
                    'external_commands = "Changed subprocess or executable invocation: test arguments, failures, and prohibited execution paths."\n',
                    "",
                ),
                encoding="utf-8",
            )
            self.assertTrue(
                any("conditional triggers must define" in error for error in check(root))
            )

    def test_rejects_missing_affected_test_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            policy_path = root / "python/routing.toml"
            policy_path.write_text(
                policy_path.read_text(encoding="utf-8").replace(
                    'affected_test_command = "python -m pytest tests/rerg/test_percent_decoder.py"\n',
                    "",
                ),
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "fact must state quick and full local commands" in error
                    for error in check(root)
                )
            )

    def test_rejects_unknown_policy_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            policy = (Path(__file__).resolve().parents[1] / "python/routing.toml").read_text()
            (root / "python/routing.toml").write_text(
                policy.replace('"ruff-check"', '"invented-check"', 1),
                encoding="utf-8",
            )
            self.assertTrue(any("unknown check 'invented-check'" in error for error in check(root)))

    def test_rejects_broken_local_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, link="missing.md")
            self.assertTrue(any("broken local link" in error for error in check(root)))

    def test_rejects_local_link_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, link="../outside.md")
            self.assertTrue(any("escapes repository" in error for error in check(root)))

    def test_cli_returns_failure_for_invalid_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, link="missing.md")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main([str(root)])
            self.assertEqual(result, 1)
            self.assertIn("broken local link", output.getvalue())

    def test_routing_policy_file_errors_exposed_and_root_delegates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            policy_file = root / "python/routing.toml"
            self.assertEqual(routing_policy_file_errors(policy_file), [])
            policy_file.write_text(
                policy_file.read_text(encoding="utf-8").replace(
                    'affected_test_command = "python -m pytest tests/rerg/test_percent_decoder.py"\n',
                    "",
                ),
                encoding="utf-8",
            )
            direct = routing_policy_file_errors(policy_file)
            self.assertTrue(
                any("fact must state quick and full local commands" in e for e in direct)
            )
            self.assertEqual(routing_policy_errors(root), direct)

    def test_guard_only_facts_omit_ruff_and_mypy_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.write_facts(
                root,
                [
                    "schema_version = 1",
                    'selected_components = ["guard"]',
                    *[fact for fact in CORE_FACTS if not fact.startswith("mypy_command")],
                ],
                without_ruff_categories=True,
            )
            self.assertEqual(check(root), [])

    def test_ruff_component_requires_ruff_facts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.write_facts(
                root,
                ["schema_version = 1", 'selected_components = ["ruff"]', *CORE_FACTS],
            )
            errors = check(root)
            self.assertTrue(
                any(
                    "fact must state ruff_command and ruff_format_command" in e
                    and "component 'ruff' is selected" in e
                    for e in errors
                )
            )

    def test_both_components_alone_do_not_activate_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            both = [
                "schema_version = 1",
                'selected_components = ["ruff", "guard"]',
                *CORE_FACTS,
                *RUFF_FACTS,
            ]
            self.write_facts(root, both)
            self.assertEqual(check(root), [])
            self.write_facts(root, [*both, 'required_ruff_before_pytest = "enabled"'])
            errors = check(root)
            self.assertTrue(any("action-required" in e and "pending" in e for e in errors))

    def test_binding_activation_requires_explicit_binding_component(self) -> None:
        for activation in (
            'required_ruff_before_pytest = "active"',
            'required_ruff_before_pytest = "running"',
            "required_ruff_before_pytest = true",
        ):
            with self.subTest(activation=activation):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.make_repo(root)
                    self.write_facts(
                        root,
                        [
                            "schema_version = 1",
                            'selected_components = ["ruff", "guard"]',
                            *CORE_FACTS,
                            *RUFF_FACTS,
                            activation,
                        ],
                    )
                    errors = check(root)
                    self.assertTrue(
                        any(
                            "action-required" in e
                            and ("prerequisite" in e or "unsupported" in e)
                            for e in errors
                        )
                    )

    def test_active_binding_requires_ruff_and_guard_prerequisites(self) -> None:
        cases = (
            ('selected_components = ["guard"]', "'ruff'"),
            ('selected_components = ["ruff"]', "'guard'"),
        )
        for components, missing in cases:
            with self.subTest(components=components):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.make_repo(root)
                    self.write_facts(
                        root,
                        [
                            "schema_version = 1",
                            components,
                            *CORE_FACTS,
                            *RUFF_FACTS,
                            'required_ruff_before_pytest = "active"',
                        ],
                    )
                    errors = check(root)
                    self.assertTrue(
                        any(
                            "action-required" in e
                            and "prerequisite(s) not satisfied" in e
                            and missing in e
                            for e in errors
                        )
                    )

    def test_binding_requires_required_ruff_check_prerequisite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.write_facts(
                root,
                [
                    "schema_version = 1",
                    'selected_components = ["ruff", "guard"]',
                    *CORE_FACTS,
                    *RUFF_FACTS,
                    'required_ruff_before_pytest = "active"',
                ],
                without_ruff_categories=True,
            )
            errors = check(root)
            self.assertTrue(
                any(
                    "action-required" in e
                    and "prerequisite(s) not satisfied" in e
                    and "'ruff-check'" in e
                    for e in errors
                )
            )

    def test_active_binding_with_all_components_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.write_facts(
                root,
                [
                    "schema_version = 1",
                    'selected_components = ["ruff", "guard", "required-ruff"]',
                    *CORE_FACTS,
                    *RUFF_FACTS,
                    'required_ruff_before_pytest = "active"',
                ],
            )
            self.assertEqual(check(root), [])

    def test_unsupported_schema_version_requires_consumer_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.write_facts(
                root,
                [
                    "schema_version = 2",
                    'selected_components = ["ruff"]',
                    *CORE_FACTS,
                    *RUFF_FACTS,
                ],
            )
            errors = check(root)
            self.assertTrue(
                any("action-required" in e and "schema_version" in e for e in errors)
            )

    def test_missing_schema_version_requires_consumer_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.write_facts(root, [*CORE_FACTS, *RUFF_FACTS])
            errors = check(root)
            self.assertTrue(
                any("action-required" in e and "schema_version" in e for e in errors)
            )


if __name__ == "__main__":
    unittest.main()
