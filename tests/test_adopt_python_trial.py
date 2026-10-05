from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.adopt_python_trial import AdoptionError, apply, main, prepare


class PythonTrialAdoptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_selection_preview_and_apply_touch_only_selected_component(self) -> None:
        changes = prepare(self.root, ["ruff"])
        self.assertEqual(len(changes), 1)
        self.assertFalse(changes[0].destination.exists())

        adopted = apply(self.root, ["ruff"])
        self.assertEqual(adopted, [self.root / ".gajaestack/python-trial/ruff.toml"])
        self.assertFalse((self.root / ".gajaestack/python-trial/mypy.ini").exists())
        self.assertFalse(
            (self.root / "tests/rerg/test_percent_decoder_properties.py").exists()
        )

    def test_reapplying_is_idempotent_and_hypothesis_is_separately_selected(
        self,
    ) -> None:
        adopted = apply(self.root, ["ruff"])
        original = adopted[0].read_bytes()
        self.assertEqual(apply(self.root, ["ruff"]), [])
        self.assertEqual(adopted[0].read_bytes(), original)

        property_test = apply(self.root, ["hypothesis"])
        self.assertEqual(
            property_test,
            [self.root / "tests/rerg/test_percent_decoder_properties.py"],
        )
        self.assertFalse((self.root / ".gajaestack/python-trial/mypy.ini").exists())

    def test_existing_different_file_refuses_without_partial_writes(self) -> None:
        existing = self.root / ".gajaestack/python-trial/ruff.toml"
        existing.parent.mkdir(parents=True)
        existing.write_text("owner config\n", encoding="utf-8")

        with self.assertRaisesRegex(AdoptionError, "refusing to overwrite"):
            apply(self.root, ["mypy", "ruff"])

        self.assertEqual(existing.read_text(encoding="utf-8"), "owner config\n")
        self.assertFalse((self.root / ".gajaestack/python-trial/mypy.ini").exists())

    def test_directory_at_file_destination_is_a_collision(self) -> None:
        destination = self.root / ".gajaestack/python-trial/ruff.toml"
        destination.mkdir(parents=True)

        with self.assertRaisesRegex(AdoptionError, "non-file destination"):
            apply(self.root, ["ruff"])

        self.assertTrue(destination.is_dir())

    def test_remove_preserves_locally_changed_file(self) -> None:
        adopted = apply(self.root, ["ruff"])[0]
        adopted.write_text("locally customized\n", encoding="utf-8")

        with self.assertRaisesRegex(
            AdoptionError, "refusing to remove locally changed"
        ):
            apply(self.root, ["ruff"], remove=True)

        self.assertEqual(adopted.read_text(encoding="utf-8"), "locally customized\n")

    def test_removing_one_component_preserves_another_selection(self) -> None:
        apply(self.root, ["ruff", "mypy"])
        mypy = self.root / ".gajaestack/python-trial/mypy.ini"

        apply(self.root, ["ruff"], remove=True)

        self.assertFalse((self.root / ".gajaestack/python-trial/ruff.toml").exists())
        self.assertTrue(mypy.is_file())

    def test_symlink_destination_refuses_to_follow_target(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.write_text("keep\n", encoding="utf-8")
        self.addCleanup(outside.unlink, missing_ok=True)
        self.root.joinpath(".gajaestack").mkdir()
        self.root.joinpath(".gajaestack/python-trial").symlink_to(
            outside.parent, target_is_directory=True
        )

        with self.assertRaisesRegex(AdoptionError, "symlinked destination directory"):
            apply(self.root, ["ruff"])
        self.assertEqual(outside.read_text(encoding="utf-8"), "keep\n")

    def test_cli_defaults_to_preview_and_rejects_unknown_selection(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["--root", str(self.root), "--component", "ruff"])
        self.assertEqual(result, 0)
        self.assertIn("Would adopt", output.getvalue())
        self.assertFalse((self.root / ".gajaestack/python-trial/ruff.toml").exists())

        apply(self.root, ["ruff"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(
                [
                    "--root",
                    str(self.root),
                    "--component",
                    "ruff",
                    "--remove",
                ]
            )
        self.assertEqual(result, 0)
        self.assertIn("Would remove", output.getvalue())
        self.assertTrue((self.root / ".gajaestack/python-trial/ruff.toml").exists())

        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            result = main(
                [
                    "--root",
                    str(self.root),
                    "--component",
                    "ruff",
                    "--component",
                    "ruff",
                    "--apply",
                ]
            )
        self.assertEqual(result, 1)
        self.assertIn("must not be repeated", error.getvalue())


if __name__ == "__main__":
    unittest.main()
