from __future__ import annotations

import contextlib
import io
import unittest

from scripts.check_python_imports import main, missing_imports


class CheckPythonImportsTests(unittest.TestCase):
    def test_accepts_available_imports(self) -> None:
        self.assertEqual(missing_imports(["math"], lambda _name: object()), [])

    def test_reports_missing_or_unresolvable_imports(self) -> None:
        def find_spec(name: str) -> object | None:
            if name == "unavailable":
                return None
            raise ModuleNotFoundError(name)

        self.assertEqual(
            missing_imports(["unavailable", "parent.child"], find_spec),
            ["unavailable", "parent.child"],
        )

    def test_cli_passes_and_fails_explicit_prerequisites(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["math"]), 0)
        self.assertIn("discoverable", output.getvalue())

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["gajaestack_deliberately_missing_import"]), 1)
        self.assertIn("gajaestack_deliberately_missing_import", output.getvalue())


if __name__ == "__main__":
    unittest.main()
