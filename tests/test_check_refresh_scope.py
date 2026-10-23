import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.check_refresh_scope import check, main

class RefreshScopeTests(unittest.TestCase):
    def test_exact_paths_only(self):
        self.assertEqual(check(["data/status.json"], ["data/status.json"]), [])
        self.assertEqual(check(["data/status.json", "scripts/x.py"], ["data/status.json"]), ["scripts/x.py"])
        self.assertEqual(check(["data/status.json.bak"], ["data/status.json"]), ["data/status.json.bak"])
        with self.assertRaises(ValueError):
            check(["data/status.json"], ["../data/status.json"])

    def test_staged_git_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            for key, value in [("user.email", "test@example.invalid"), ("user.name", "Test")]:
                subprocess.run(["git", "config", key, value], cwd=root, check=True)
            (root / "data").mkdir()
            (root / "scripts").mkdir()
            (root / "data/status.json").write_text("before")
            (root / "scripts/x.py").write_text("before")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            (root / "data/status.json").write_text("after")
            subprocess.run(["git", "add", "data/status.json"], cwd=root, check=True)
            self.assertEqual(main(["--repo", str(root), "data/status.json"]), 0)
            (root / "scripts/x.py").write_text("unauthorized")
            subprocess.run(["git", "add", "scripts/x.py"], cwd=root, check=True)
            self.assertEqual(main(["--repo", str(root), "data/status.json"]), 1)

if __name__ == "__main__":
    unittest.main()
