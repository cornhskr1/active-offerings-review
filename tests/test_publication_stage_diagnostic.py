import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
class PublicationDiagnosticTests(unittest.TestCase):
    def test_failure_reports_location_without_exception_text(self):
        secret="SYNTHETIC-SECRET-MUST-NOT-APPEAR"
        code="import sys,runpy; from unittest.mock import patch; from pathlib import Path; sys.argv=['restore','--root','.','--stage','unused','--previous','unused']; " + "\nwith patch.object(Path,'read_bytes',side_effect=ValueError("+repr(secret)+")): runpy.run_module('scripts.restore_public_snapshot',run_name='__main__')"
        env={**os.environ,'GITHUB_REPOSITORY':'cornhskr1/active-offerings-review'}
        result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Publication diagnostic: ValueError at ',result.stderr)
        self.assertIn('Complete private publication blocked',result.stderr)
        self.assertNotIn(secret,result.stdout+result.stderr)
