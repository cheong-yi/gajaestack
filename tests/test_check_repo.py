from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.check_repo import check, main


class CheckRepoTests(unittest.TestCase):
    def make_repo(
        self, root: Path, *, metadata: str | None = None, link: str = "README.md"
    ) -> None:
        skills = root / "skills" / "example"
        skills.mkdir(parents=True)
        frontmatter = (
            metadata
            or "---\nname: example\ndescription: Example skill.\n---\n\nBody.\n"
        )
        (skills / "SKILL.md").write_text(frontmatter, encoding="utf-8")
        (root / "README.md").write_text(f"[Example]({link})\n", encoding="utf-8")

    def test_accepts_valid_skill_and_local_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root)
            self.assertEqual(check(root), [])

    def test_rejects_missing_skill_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_repo(root, metadata="---\nname: example\n---\n\nBody.\n")
            errors = check(root)
            self.assertTrue(
                any(
                    "missing required metadata field 'description'" in e for e in errors
                )
            )

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


if __name__ == "__main__":
    unittest.main()
