"""Offline tests for manual private data consumption without using credentials."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts.fetch_private_data_candidate import fetch_candidate, COMMIT

class Response:
    def __init__(self, url, body):
        self.url, self.body = url, body
    def geturl(self):
        return self.url
    def read(self, size=-1):
        return self.body[:size]
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

class PrivateFetchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "candidate"
        self.raw = {
            "data/status.json": b'{"generated_at":"synthetic","sources":[]}',
            "data/review-data.json": b'{"generated_at":"synthetic","schema_version":1,"events":[]}',
        }
        hashes = {k: hashlib.sha256(v).hexdigest() for k,v in self.raw.items()}
        self.raw["manifest.json"] = json.dumps({"schema_version":1,"files":hashes}).encode()

    def opener(self, request, timeout=20):
        name = request.full_url.split("/published/pilot/")[1].split("?")[0]
        return Response(request.full_url, json.dumps({
            "type":"file", "path":"published/pilot/"+name, "encoding":"base64",
            "content":base64.b64encode(self.raw[name]).decode()
        }).encode())

    def test_valid_private_candidate(self):
        self.assertEqual(fetch_candidate(self.root, "synthetic-token", opener=self.opener),
                         ["data/review-data.json","data/status.json"])

    def test_missing_token(self):
        with self.assertRaisesRegex(ValueError,"credential"):
            fetch_candidate(self.root, "", opener=self.opener)

    def test_tampered_file(self):
        original = self.raw["data/status.json"]
        self.raw["data/status.json"] = original + b' '
        with self.assertRaisesRegex(ValueError,"integrity"):
            fetch_candidate(self.root,"synthetic-token",opener=self.opener)

    def test_bad_commit(self):
        with self.assertRaisesRegex(ValueError,"commit"):
            fetch_candidate(self.root,"synthetic-token",commit="main",opener=self.opener)

if __name__ == "__main__":
    unittest.main()
