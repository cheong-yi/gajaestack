import importlib.util
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SCRIPT = KIT / "scripts" / "check_seeded_regressions.py"


def load_script():
    spec = importlib.util.spec_from_file_location("check_seeded_regressions", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SeededPrerequisiteTests(unittest.TestCase):
    def test_explicit_bad_bun_is_not_replaced(self) -> None:
        script = load_script()
        bun, _modules, missing = script.resolve_prerequisites(
            {"GAJAESTACK_BUN": "/missing/bun"}, Path("/tmp")
        )
        self.assertEqual(bun, "/missing/bun")
        self.assertTrue(any("not an executable" in item for item in missing))

    def test_node_modules_walk_stops_at_the_first_complete_tree(self) -> None:
        script = load_script()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "repo" / "lane"
            modules = root / "node_modules" / ".bin"
            modules.mkdir(parents=True)
            nested.mkdir(parents=True)
            for tool in ("tsc", "biome"):
                (modules / tool).write_text("#!/bin/sh\n")
            self.assertEqual(script.find_node_modules(nested), root / "node_modules")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incomplete = root / "node_modules" / ".bin"
            incomplete.mkdir(parents=True)
            (incomplete / "tsc").write_text("#!/bin/sh\n")
            self.assertIsNone(script.find_node_modules(root))
