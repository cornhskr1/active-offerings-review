import ast
from pathlib import Path
import re
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "refresh_tennis_intelligence.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
FUNCTIONS = {node.name: node for node in TREE.body if isinstance(node, ast.FunctionDef)}
NAMESPACE = {"re": re}
for name in ("norm", "registry_identity", "merge_registry_records"):
    module = ast.Module(body=[FUNCTIONS[name]], type_ignores=[])
    exec(compile(module, str(SOURCE), "exec"), NAMESPACE)
MOD = types.SimpleNamespace(**NAMESPACE)


class TennisRegistryMergeTests(unittest.TestCase):
    def test_same_official_player_id_collapses_name_variants(self):
        rows = [
            {
                "name": "A. Player",
                "source_url": "https://www.itftennis.com/en/players/alex-player/800123456/usa/jt/s/",
                "age_status": "VERIFIED U18",
            },
            {
                "name": "Alex Player (WC)",
                "source_url": "https://www.itftennis.com/en/players/alex-player/800123456/usa/wt/s/",
                "age": 17,
                "age_status": "VERIFIED U18",
            },
        ]
        merged = MOD.merge_registry_records(rows)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["name"], "Alex Player")
        self.assertIn("A. Player", merged[0]["aliases"])

    def test_exposure_matches_any_alias(self):
        rows = [{
            "name": "Alexandra Player",
            "aliases": ["A. Player"],
            "age_status": "VERIFIED U18",
        }]
        merged = MOD.merge_registry_records(rows, {MOD.norm("A. Player")})
        self.assertTrue(merged[0]["current_exposure"])


if __name__ == "__main__":
    unittest.main()
