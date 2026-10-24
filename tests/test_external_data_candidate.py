"""Synthetic fail-closed checks for the future deployment-side data gate."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.verify_external_data_candidate import verify_candidate

class ExternalDataGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = {
            "data/status.json": {"generated_at": "synthetic", "sources": []},
            "data/review-data.json": {"generated_at": "synthetic", "schema_version": 1, "events": []},
        }
        self.rebuild()

    def rebuild(self):
        hashes = {}
        for name, obj in self.files.items():
            file = self.root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            raw = json.dumps(obj).encode()
            file.write_bytes(raw)
            hashes[name] = hashlib.sha256(raw).hexdigest()
        (self.root / "manifest.json").write_text(json.dumps({"schema_version": 1, "files": hashes}))

    def test_valid_candidate(self):
        self.assertEqual(verify_candidate(self.root), sorted(self.files))

    def test_integrity_tamper_rejected(self):
        (self.root / "data/status.json").write_text('{"generated_at":"changed","sources":[]}')
        with self.assertRaisesRegex(ValueError, "integrity"):
            verify_candidate(self.root)

    def test_extra_file_rejected(self):
        (self.root / "unexpected.py").write_text("print(1)")
        with self.assertRaisesRegex(ValueError, "extra"):
            verify_candidate(self.root)

    def test_missing_field_rejected(self):
        self.files["data/status.json"] = {"sources": []}
        self.rebuild()
        with self.assertRaisesRegex(ValueError, "schema"):
            verify_candidate(self.root)

    def test_symlink_rejected(self):
        target = self.root / "data/status.json"
        target.unlink()
        target.symlink_to(self.root / "data/review-data.json")
        with self.assertRaises(ValueError):
            verify_candidate(self.root)

if __name__ == "__main__":
    unittest.main()
