from pathlib import Path
import subprocess
import unittest
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"index.html").read_text()
def source(name):
    start=HTML.index("function "+name+"(")
    end=HTML.index("\nfunction ",start+10)
    return HTML[start:end]
class U18VerificationDateTests(unittest.TestCase):
    def test_recorded_date_survives_grouping_and_missing_date_is_honest(self):
        script="""
const assert=require('node:assert/strict');
const DATA={known:{records:[{athlete:'General Athlete',sport:'Soccer'}]},
 tennisRegistry:{verified_u18:[{name:'Tennis Athlete',age:17,last_verified:'2026-09-09T07:00:00Z'}]},
 tennisCache:{records:{}}};
const tennisRegistryIdentity=r=>r.name;
const preferredRegistryName=names=>[...names][0];
"""+"\n".join(source(n) for n in ['registryNameKey','combinedKnownU18Rows','u18LastVerifiedLabel'])+"""
const rows=combinedKnownU18Rows().rows;
assert.equal(u18LastVerifiedLabel(rows[0].last_verified),'Not recorded');
assert.equal(u18LastVerifiedLabel(rows[1].last_verified),'2026-09-09');
assert.equal(u18LastVerifiedLabel('invalid'),'Not recorded');
assert.equal(u18LastVerifiedLabel('2026-09-09T07:00:00Z'),'2026-09-09');
"""
        subprocess.run(['node','-e',script],cwd=ROOT,check=True)
        self.assertIn('Last verified: ${esc(u18LastVerifiedLabel(x.last_verified))}',HTML)
