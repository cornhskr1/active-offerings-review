import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.preview_private_data_overlay import overlay

class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.site, self.candidate, self.preview = root / "site", root / "candidate", root / "preview"
        for folder in (self.site, self.candidate):
            (folder / "data").mkdir(parents=True)
        (self.site / "index.html").write_text("<title>Active Offerings</title>")
        self.raw = {
            "data/status.json": b'{"generated_at":"synthetic","sources":[]}',
            "data/review-data.json": b'{"generated_at":"synthetic","schema_version":1,"events":[]}',
        }
        digests = {}
        for name, raw in self.raw.items():
            (self.site / name).write_bytes(b'{"original":true}')
            (self.candidate / name).write_bytes(raw)
            digests[name] = hashlib.sha256(raw).hexdigest()
        (self.candidate / "manifest.json").write_text(json.dumps({"schema_version":1,"files":digests}))

    def test_valid_overlay_keeps_original_intact(self):
        overlay(self.site, self.candidate, self.preview)
        self.assertEqual((self.preview / "data/status.json").read_bytes(), self.raw["data/status.json"])
        self.assertEqual((self.site / "data/status.json").read_bytes(), b'{"original":true}')
        self.assertEqual((self.preview / "index.html").read_bytes(), (self.site / "index.html").read_bytes())

    def test_tampered_data_blocks_preview(self):
        (self.candidate / "data/status.json").write_bytes(b'{"changed":true}')
        with self.assertRaisesRegex(ValueError, "integrity"):
            overlay(self.site, self.candidate, self.preview)
        self.assertFalse(self.preview.exists())

    def test_unlisted_payload_blocks_preview(self):
        (self.candidate / "evil.py").write_text("print(1)")
        with self.assertRaisesRegex(ValueError, "extra"):
            overlay(self.site, self.candidate, self.preview)
        self.assertFalse(self.preview.exists())

    def test_failed_candidate_preserves_last_known_good_site(self):
        prior = {
            name: (self.site / name).read_bytes()
            for name in ("index.html", "data/status.json", "data/review-data.json")
        }
        (self.candidate / "data/status.json").write_bytes(b'{"modified":true}')
        with self.assertRaisesRegex(ValueError, "integrity"):
            overlay(self.site, self.candidate, self.preview)
        self.assertFalse(self.preview.exists())
        for name, raw in prior.items():
            self.assertEqual((self.site / name).read_bytes(), raw)

    def test_invalid_candidate_cannot_overwrite_last_good_preview(self):
        overlay(self.site, self.candidate, self.preview)
        previous = {
            name: (self.preview / name).read_bytes()
            for name in ("index.html", "data/status.json", "data/review-data.json")
        }
        (self.candidate / "data/status.json").write_bytes(b'{"tampered":true}')
        with self.assertRaisesRegex(ValueError, "must not already"):
            overlay(self.site, self.candidate, self.preview)
        for name, raw in previous.items():
            self.assertEqual((self.preview / name).read_bytes(), raw)

    def test_existing_preview_rejected(self):
        self.preview.mkdir()
        with self.assertRaisesRegex(ValueError, "must not already"):
            overlay(self.site, self.candidate, self.preview)

if __name__ == "__main__":
    unittest.main()
