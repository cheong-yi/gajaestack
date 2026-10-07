from __future__ import annotations

import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from collections.abc import Callable, Iterator
from pathlib import Path
from unittest import mock

from scripts.check_changed_python import (
    DEFAULT_CONFIG,
    MISSING_EXECUTABLE,
    ScopeError,
    changed_python_files,
    full_scope,
    main,
    ruff_check,
)


@contextlib.contextmanager
def in_directory(path: Path) -> Iterator[Path]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield path
    finally:
        os.chdir(previous)


class CheckChangedPythonTests(unittest.TestCase):
    def git(self, root: Path, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def write_files(self, root: Path, files: dict[str, str]) -> None:
        for name, content in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def make_repo(self, root: Path, files: dict[str, str]) -> None:
        subprocess.run(
            ["git", "init", "-q", str(root)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.git(root, "config", "user.email", "tests@example.com")
        self.git(root, "config", "user.name", "Check Changed Python")
        self.git(root, "config", "commit.gpgsign", "false")
        self.write_files(root, files)
        self.git(root, "add", "-A")
        self.git(root, "commit", "-qm", "base")

    @contextlib.contextmanager
    def fake_ruff(
        self, handler: Callable[..., subprocess.CompletedProcess[str]] | None = None
    ) -> Iterator[list[list[str]]]:
        """Patch subprocess.run so real Git keeps working while Ruff is faked."""
        real_run = subprocess.run
        commands: list[list[str]] = []

        def fake_run(command: list[str], **kwargs: object) -> object:
            if command and command[0] == "ruff":
                commands.append(list(command))
                if handler is None:
                    return subprocess.CompletedProcess(command, 0)
                return handler(command, **kwargs)
            return real_run(command, **kwargs)

        with mock.patch(
            "scripts.check_changed_python.subprocess.run", side_effect=fake_run
        ):
            yield commands

    def test_discovers_staged_unstaged_and_untracked_python_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(
                root,
                {
                    "tracked.py": "value = 1\n",
                    "notes.txt": "text\n",
                    ".gitignore": "ignored*.py\n",
                },
            )
            self.write_files(root, {"tracked.py": "value = 2\n"})
            self.write_files(root, {"staged.py": "value = 3\n"})
            self.git(root, "add", "staged.py")
            self.write_files(root, {"untracked.py": "value = 4\n"})
            self.write_files(root, {"ignored_secret.py": "value = 5\n"})
            self.assertCountEqual(
                changed_python_files(root),
                ["staged.py", "tracked.py", "untracked.py"],
            )

    def test_excludes_non_python_and_deleted_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(
                root,
                {
                    "keep.py": "keep = 1\n",
                    "old.py": "old = 1\n",
                    "notes.txt": "text\n",
                },
            )
            self.write_files(root, {"keep.py": "keep = 2\n"})
            self.write_files(root, {"notes.txt": "changed text\n"})
            (root / "old.py").unlink()
            self.assertEqual(changed_python_files(root), ["keep.py"])

    def test_discovers_untracked_python_file_with_spaces(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"base.py": "base = 1\n"})
            self.write_files(root, {"two words.py": "spaced = 1\n"})
            self.assertEqual(changed_python_files(root), ["two words.py"])

    def test_preserves_carriage_return_and_non_utf8_filename_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"base.py": "base = 1\n"})
            carriage_name = "carriage\rreturn.py"
            invalid_utf8_name = os.fsdecode(b"invalid-\xff.py")
            self.write_files(
                root,
                {carriage_name: "carriage = 1\n", invalid_utf8_name: "encoded = 1\n"},
            )
            self.assertCountEqual(
                changed_python_files(root), [carriage_name, invalid_utf8_name]
            )

    def test_preserves_repository_root_ending_in_space(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo "
            root.mkdir()
            self.make_repo(root, {"base.py": "base = 1\n"})
            self.write_files(root, {"base.py": "base = 2\n"})

            with self.fake_ruff() as commands:
                with in_directory(root):
                    with contextlib.redirect_stdout(io.StringIO()):
                        result = main([])

            self.assertEqual(result, 0)
            self.assertEqual(commands[0][-1], "base.py")

    def test_cli_runs_ruff_with_config_separator_and_spaced_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"base.py": "base = 1\n"})
            self.write_files(root, {"two words.py": "spaced = 1\n"})
            ruff_cwds: list[Path] = []

            def succeed(
                command: list[str], **kwargs: object
            ) -> subprocess.CompletedProcess[str]:
                cwd = kwargs.get("cwd")
                assert isinstance(cwd, Path)
                ruff_cwds.append(cwd)
                return subprocess.CompletedProcess(command, 0)

            with self.fake_ruff(succeed) as commands:
                with in_directory(root):
                    with contextlib.redirect_stdout(io.StringIO()):
                        result = main([])

            self.assertEqual(result, 0)
            self.assertEqual(
                commands,
                [
                    [
                        "ruff",
                        "check",
                        "--no-cache",
                        "--config",
                        DEFAULT_CONFIG,
                        "--",
                        "two words.py",
                    ]
                ],
            )
            self.assertEqual(ruff_cwds, [root.resolve()])

    def test_no_changed_python_files_reports_noop_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"base.py": "base = 1\n", "notes.txt": "text\n"})
            self.write_files(root, {"notes.txt": "changed text\n"})

            def must_not_run(
                command: list[str], **kwargs: object
            ) -> subprocess.CompletedProcess[str]:
                raise AssertionError("ruff must not run without changed Python files")

            with self.fake_ruff(must_not_run):
                with in_directory(root):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        result = main([])

            self.assertEqual(result, 0)
            self.assertIn("No changed Python files; nothing to check.", output.getvalue())

    def test_allowlist_with_no_changed_targets_reports_noop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"changed.py": "value = 1\n", "other.py": "other = 1\n"})
            self.write_files(root, {"changed.py": "value = 2\n"})

            def must_not_run(
                command: list[str], **kwargs: object
            ) -> subprocess.CompletedProcess[str]:
                raise AssertionError("ruff must not run without matching changed targets")

            with self.fake_ruff(must_not_run):
                with in_directory(root):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        result = main(["--path", "other.py"])

            self.assertEqual(result, 0)
            self.assertIn(
                "No changed Python files match the requested paths", output.getvalue()
            )

    def test_propagates_ruff_nonzero_exit_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"base.py": "base = 1\n"})
            self.write_files(root, {"base.py": "base = 2\n"})

            def fail(
                command: list[str], **kwargs: object
            ) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(command, 1)

            with self.fake_ruff(fail):
                with in_directory(root):
                    with contextlib.redirect_stdout(io.StringIO()):
                        result = main([])

            self.assertEqual(result, 1)

    def test_reports_missing_ruff_executable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"base.py": "base = 1\n"})
            self.write_files(root, {"base.py": "base = 2\n"})

            def missing(
                command: list[str], **kwargs: object
            ) -> subprocess.CompletedProcess[str]:
                raise FileNotFoundError("ruff")

            with self.fake_ruff(missing):
                with in_directory(root):
                    error = io.StringIO()
                    with contextlib.redirect_stdout(io.StringIO()):
                        with contextlib.redirect_stderr(error):
                            result = main([])

            self.assertEqual(result, MISSING_EXECUTABLE)
            self.assertIn("ruff executable not found", error.getvalue())

    def test_reports_missing_git_executable(self) -> None:
        error = io.StringIO()
        with mock.patch(
            "scripts.check_changed_python.subprocess.run",
            side_effect=FileNotFoundError("git"),
        ):
            with contextlib.redirect_stderr(error):
                result = main([])

        self.assertEqual(result, MISSING_EXECUTABLE)
        self.assertIn("git executable not found", error.getvalue())

    def test_reports_git_discovery_failure(self) -> None:
        def failing(
            command: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                command, 128, stdout=b"", stderr=b"fatal: not a git repository\n"
            )

        error = io.StringIO()
        with mock.patch(
            "scripts.check_changed_python.subprocess.run", side_effect=failing
        ):
            with contextlib.redirect_stderr(error):
                result = main([])

        self.assertEqual(result, 128)
        self.assertIn("not a git repository", error.getvalue())

    def test_cli_accepts_custom_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"base.py": "base = 1\n"})
            self.write_files(root, {"base.py": "base = 2\n"})

            with self.fake_ruff() as commands:
                with in_directory(root):
                    with contextlib.redirect_stdout(io.StringIO()):
                        result = main(["--config", "configs/ruff.toml"])

            self.assertEqual(result, 0)
            self.assertEqual(
                commands,
                [["ruff", "check", "--no-cache", "--config", "configs/ruff.toml", "--", "base.py"]],
            )

    def test_cli_limits_ruff_to_changed_requested_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(
                root,
                {"target.py": "target = 1\n", "unrelated.py": "unrelated = 1\n"},
            )
            self.write_files(
                root,
                {
                    "target.py": "target = 2\n",
                    "unrelated.py": "unrelated = 2\n",
                    "new target.py": "new_target = 3\n",
                },
            )

            with self.fake_ruff() as commands:
                with in_directory(root):
                    with contextlib.redirect_stdout(io.StringIO()):
                        result = main(
                            [
                                "--path",
                                "target.py",
                                "--path",
                                "new target.py",
                            ]
                        )

            self.assertEqual(result, 0)
            self.assertEqual(
                commands,
                [
                    [
                        "ruff",
                        "check",
                        "--no-cache",
                        "--config",
                        DEFAULT_CONFIG,
                        "--",
                        "target.py",
                        "new target.py",
                    ]
                ],
            )

    def test_timing_flag_reports_scope_discovery_and_ruff_phases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"base.py": "base = 1\n"})
            self.write_files(root, {"base.py": "base = 2\n"})

            with self.fake_ruff() as commands:
                with in_directory(root):
                    output = io.StringIO()
                    error = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        with contextlib.redirect_stderr(error):
                            result = main(["--timing"])

            self.assertEqual(result, 0)
            self.assertEqual(
                commands,
                [
                    [
                        "ruff",
                        "check",
                        "--no-cache",
                        "--config",
                        DEFAULT_CONFIG,
                        "--",
                        "base.py",
                    ]
                ],
            )
            self.assertNotIn("timing:", output.getvalue())
            stderr = error.getvalue()
            self.assertRegex(
                stderr,
                r"timing: scope discovery: elapsed=\d+\.\d{3}s \(files=1, exit=0\)",
            )
            self.assertRegex(
                stderr, r"timing: ruff: elapsed=\d+\.\d{3}s \(files=1, exit=0\)"
            )
            self.assertEqual(stderr.count("timing:"), 2)

    def test_timing_reports_ruff_failure_exit_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"base.py": "base = 1\n"})
            self.write_files(root, {"base.py": "base = 2\n"})

            def fail(
                command: list[str], **kwargs: object
            ) -> subprocess.CompletedProcess[str]:
                return subprocess.CompletedProcess(command, 3)

            with self.fake_ruff(fail):
                with in_directory(root):
                    error = io.StringIO()
                    with contextlib.redirect_stdout(io.StringIO()):
                        with contextlib.redirect_stderr(error):
                            result = main(["--timing"])

            self.assertEqual(result, 3)
            stderr = error.getvalue()
            self.assertRegex(
                stderr,
                r"timing: scope discovery: elapsed=\d+\.\d{3}s \(files=1, exit=0\)",
            )
            self.assertRegex(
                stderr, r"timing: ruff: elapsed=\d+\.\d{3}s \(files=1, exit=3\)"
            )

    def test_timing_no_scope_reports_discovery_phase_without_ruff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"base.py": "base = 1\n", "notes.txt": "text\n"})
            self.write_files(root, {"notes.txt": "changed text\n"})

            def must_not_run(
                command: list[str], **kwargs: object
            ) -> subprocess.CompletedProcess[str]:
                raise AssertionError("ruff must not run without changed Python files")

            with self.fake_ruff(must_not_run):
                with in_directory(root):
                    output = io.StringIO()
                    error = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        with contextlib.redirect_stderr(error):
                            result = main(["--timing"])

            self.assertEqual(result, 0)
            self.assertIn(
                "No changed Python files; nothing to check.", output.getvalue()
            )
            self.assertNotIn("timing:", output.getvalue())
            stderr = error.getvalue()
            self.assertRegex(
                stderr,
                r"timing: scope discovery: elapsed=\d+\.\d{3}s \(files=0, exit=0\)",
            )
            self.assertNotIn("timing: ruff", stderr)
            self.assertEqual(stderr.count("timing:"), 1)

    def test_timing_full_mode_reports_scope_discovery_and_ruff_phases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(
                root,
                {
                    "base.py": "base = 1\n",
                    "ruff.toml": "\n",
                    ".gajaestack/routing.toml": (
                        "[python]\n"
                        "schema_version = 1\n"
                        'ruff_paths = ["base.py"]\n'
                        'ruff_config = "ruff.toml"\n'
                    ),
                },
            )

            with self.fake_ruff() as commands:
                with in_directory(root):
                    output = io.StringIO()
                    error = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        with contextlib.redirect_stderr(error):
                            result = main(["--full", "--timing"])

            self.assertEqual(result, 0)
            self.assertIn("Full selected scope: 1 file(s)", output.getvalue())
            self.assertEqual(commands[0][-1], "base.py")
            stderr = error.getvalue()
            self.assertRegex(
                stderr,
                r"timing: scope discovery: elapsed=\d+\.\d{3}s \(files=1, exit=0\)",
            )
            self.assertRegex(
                stderr, r"timing: ruff: elapsed=\d+\.\d{3}s \(files=1, exit=0\)"
            )
            self.assertEqual(stderr.count("timing:"), 2)

    def test_completion_budget_does_not_change_native_ruff_status(self) -> None:
        for budget in (None, "1", "600", "9007199254740991"):
            with self.subTest(budget=budget), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                fact = '[fact]\ntest_command = "python -B -m pytest"\n'
                if budget is not None:
                    fact += f"completion_timeout_seconds = {budget}\n"
                self.write_files(root, {
                    "base.py": "base = 1\n",
                    "ruff.toml": "\n",
                    ".gajaestack/routing.toml": fact + (
                        "[python]\nschema_version = 1\n"
                        'ruff_paths = ["base.py"]\nruff_config = "ruff.toml"\n'
                    ),
                })

                def native_failure(command, **kwargs):
                    self.assertNotIn("timeout", kwargs)
                    return subprocess.CompletedProcess(command, 37)

                with self.fake_ruff(native_failure) as commands, in_directory(root):
                    with contextlib.redirect_stdout(io.StringIO()):
                        result = main(["--full"])
                self.assertEqual(result, 37)
                self.assertEqual(len(commands), 1)
                self.assertEqual(commands[0][-1], "base.py")

    def test_invalid_completion_budget_stops_before_ruff(self) -> None:
        for budget in (
            "true", "false", "0", "-1", '"600"', "1.5", "1.0",
            "inf", "nan", "9007199254740992", "18446744073709551616",
        ):
            with self.subTest(budget=budget), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write_files(root, {
                    ".gajaestack/routing.toml": (
                        '[fact]\ntest_command = "python -B -m pytest"\n'
                        f"completion_timeout_seconds = {budget}\n"
                        "[python]\nschema_version = 1\n"
                        'ruff_paths = ["missing.py"]\nruff_config = "missing.toml"\n'
                    ),
                })
                error = io.StringIO()
                with self.fake_ruff() as commands, in_directory(root):
                    with contextlib.redirect_stderr(error):
                        result = main(["--full"])
                self.assertEqual(result, 2)
                self.assertIn("completion_timeout_seconds", error.getvalue())
                self.assertEqual(commands, [])

    def test_completion_budget_requires_command_and_direct_fact_placement(self) -> None:
        for facts in (
            "completion_timeout_seconds = 60\n",
            "[python]\ncompletion_timeout_seconds = 60\n",
            "[typescript]\ncompletion_timeout_seconds = 60\n",
            "[fact.nested]\ncompletion_timeout_seconds = 60\n",
            "[[custom]]\ncompletion_timeout_seconds = 60\n",
            "[[fact]]\ncompletion_timeout_seconds = 60\n",
            "[fact]\ncompletion_timeout_seconds = 60\n",
            '[fact]\ntest_command = " "\ncompletion_timeout_seconds = 60\n',
        ):
            with self.subTest(facts=facts), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.write_files(root, {".gajaestack/routing.toml": facts})
                with self.assertRaisesRegex(ScopeError, "completion_timeout_seconds"):
                    full_scope(root, root / ".gajaestack/routing.toml")

    def test_timing_env_times_direct_scope_and_ruff_calls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_files(
                root,
                {
                    "base.py": "base = 1\n",
                    "ruff.toml": "\n",
                    ".gajaestack/routing.toml": (
                        "[python]\n"
                        "schema_version = 1\n"
                        'ruff_paths = ["base.py"]\n'
                        'ruff_config = "ruff.toml"\n'
                    ),
                },
            )

            error = io.StringIO()
            with mock.patch.dict(os.environ, {"GAJAESTACK_TIMING": "1"}):
                with self.fake_ruff():
                    with contextlib.redirect_stderr(error):
                        files, config = full_scope(
                            root, root / ".gajaestack/routing.toml"
                        )
                        status = ruff_check(root, config, files)

            self.assertEqual(status, 0)
            stderr = error.getvalue()
            self.assertRegex(
                stderr,
                r"timing: scope discovery: elapsed=\d+\.\d{3}s \(files=1, exit=0\)",
            )
            self.assertRegex(
                stderr, r"timing: ruff: elapsed=\d+\.\d{3}s \(files=1, exit=0\)"
            )
            self.assertEqual(stderr.count("timing:"), 2)

    def test_timing_scope_failure_reports_status_for_bound_calls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            error = io.StringIO()
            with mock.patch.dict(os.environ, {"GAJAESTACK_TIMING": "1"}):
                with contextlib.redirect_stderr(error):
                    with self.assertRaises(ScopeError):
                        full_scope(root, root / ".gajaestack/routing.toml")

            stderr = error.getvalue()
            self.assertRegex(
                stderr,
                r"timing: scope discovery: elapsed=\d+\.\d{3}s \(files=0, exit=2\)",
            )
            self.assertEqual(stderr.count("timing:"), 1)

    def test_timing_is_opt_in_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, {"base.py": "base = 1\n"})
            self.write_files(root, {"base.py": "base = 2\n"})

            error = io.StringIO()
            with mock.patch.dict(os.environ):
                os.environ.pop("GAJAESTACK_TIMING", None)
                with self.fake_ruff():
                    with in_directory(root):
                        with contextlib.redirect_stdout(io.StringIO()):
                            with contextlib.redirect_stderr(error):
                                result = main([])

            self.assertEqual(result, 0)
            self.assertEqual(error.getvalue(), "")

    def test_timing_env_value_other_than_one_is_inert(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_files(
                root,
                {
                    "base.py": "base = 1\n",
                    "ruff.toml": "\n",
                    ".gajaestack/routing.toml": (
                        "[python]\n"
                        "schema_version = 1\n"
                        'ruff_paths = ["base.py"]\n'
                        'ruff_config = "ruff.toml"\n'
                    ),
                },
            )

            error = io.StringIO()
            with mock.patch.dict(os.environ, {"GAJAESTACK_TIMING": "0"}):
                with self.fake_ruff():
                    with contextlib.redirect_stderr(error):
                        files, config = full_scope(
                            root, root / ".gajaestack/routing.toml"
                        )
                        status = ruff_check(root, config, files)

            self.assertEqual(status, 0)
            self.assertEqual(error.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
