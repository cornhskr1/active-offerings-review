"""Regression coverage for the GitHub Pages publication boundary."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stage_odds_pages import is_public_asset, stage


class PublicPublicationTests(unittest.TestCase):
    def test_only_explicit_public_roots(self):
        allowed = ("index.html", "_headers", "assets/catalog-health-summary.js",
                   "data/catalog.json", "data/subdir/file.json")
        denied = ("README.md", "scripts/refresh_odds_api_events.py",
                  "tests/test_stage_publication.py", ".github/workflows/deploy-pages.yml",
                  "DEPLOYMENT_CHECKLIST.txt", "notes/file.txt", "../outside.txt")
        for name in allowed:
            with self.subTest(name=name):
                self.assertTrue(is_public_asset(name))
        for name in denied:
            with self.subTest(name=name):
                self.assertFalse(is_public_asset(name))

    def test_staging_does_not_publish_internal_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            output = Path(temporary) / "publication"
            names = ["index.html", "_headers", "assets/catalog-health-summary.js",
                     "data/catalog.json", "scripts/internal.py",
                     "README.md", ".github/workflows/deploy-pages.yml"]
            for name in names:
                source = root / name
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text(name)
            with patch("stage_odds_pages.subprocess.check_output",
                       return_value=("\0".join(names) + "\0").encode()):
                stage(root, output)
            self.assertEqual(
                {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()},
                set(names[:4]),
            )

    def test_public_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            outside = Path(temporary) / "secret"
            outside.write_text("confidential")
            data = root / "data"
            data.mkdir()
            (data / "link.json").symlink_to(outside)
            with patch("stage_odds_pages.subprocess.check_output",
                       return_value=b"data/link.json\0"):
                with self.assertRaises(ValueError):
                    stage(root, Path(temporary) / "publication")


if __name__ == "__main__":
    unittest.main()
