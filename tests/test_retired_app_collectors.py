"""Actual app retirement gate, separate from preserved historical policy tests."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from tests import retired_workflow_policy as policy

class RetiredAppCollectorTests(unittest.TestCase):
    def test_exact_seventeen_actual_workflows_are_read_only_noop(self):
        manifest=policy.verify_retirement()
        self.assertEqual(17,len(manifest['workflows']))
        for name in manifest['workflows']:
            raw=(policy.ROOT/'.github/workflows'/name).read_text()
            for forbidden in ('schedule:','push:','workflow_run:','workflow_call:','contents: write','uses:','secrets.','python','git push'):
                self.assertNotIn(forbidden,raw,name)
            self.assertIn('contents: read',raw)
    def test_any_restored_or_modified_actual_writer_fails_closed(self):
        original=Path.read_bytes
        target=policy.ROOT/'.github/workflows/refresh-data.yml'
        def altered(path):
            if path==target:return original(path)+b'\n# changed entry point\n'
            return original(path)
        with patch.object(Path,'read_bytes',altered):
            with self.assertRaisesRegex(AssertionError,'retirement bytes changed'):
                policy.historical_workflow_path('update-catalog.yml')
    def test_historical_fixture_tampering_fails_closed(self):
        original=Path.read_bytes
        target=policy.FIXTURES/'update-catalog.yml'
        def altered(path):
            if path==target:return original(path)+b'\n# modified policy\n'
            return original(path)
        with patch.object(Path,'read_bytes',altered):
            with self.assertRaisesRegex(AssertionError,'Historical policy fixture changed'):
                policy.verify_retirement()
