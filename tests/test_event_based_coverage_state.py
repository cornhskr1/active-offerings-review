"""Bout authorities and promotions do not acquire synthetic season windows."""

import json
import subprocess
import unittest
from pathlib import Path

from scripts.audit_priority2_coverage import season_state


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class EventBasedCoverageStateTests(unittest.TestCase):
    def test_all_boxing_and_combat_approvals_are_event_based(self):
        season_map = json.loads((DATA / "catalog-season-map.json").read_text())
        inventory = json.loads((DATA / "priority2-coverage-inventory.json").read_text())
        rows = {r["identity_key"]: r for r in inventory["identities"]}
        approvals = [e for sport in season_map["sports"] if sport["sport"] in {"Boxing", "Combat Sports"}
                     for group in sport["groups"] for e in group["events"]]
        self.assertEqual(24, len(approvals))
        self.assertEqual(25, inventory["summary"]["season_states"]["EVENT_BASED_APPROVAL"])
        self.assertEqual("EVENT_BASED_APPROVAL", rows["cricket-int-odi"]["season_state"])
        self.assertNotIn("NO_WINDOW", inventory["summary"]["season_states"])
        for approval in approvals:
            self.assertTrue(approval["nonseasonal"])
            self.assertEqual("EVENT_BASED_APPROVAL", season_state(approval))
            self.assertEqual("EVENT_BASED_APPROVAL", rows[approval["key"]]["season_state"])
            self.assertNotIn("season_start_date", approval)
            self.assertNotIn("season_end_date", approval)

    def test_nonseasonal_approval_cannot_show_in_season_from_legacy_status(self):
        html = (ROOT / "index.html").read_text()
        start = html.index("function mappedSeasonStatus(")
        end = html.index("\nfunction mappedCatalogEventForSource(", start)
        script = """
const assert=require('node:assert/strict');
const DATA={global:{sources:[]}};
function exactSeasonStatus(){return null}
function annualSeasonStatus(){return null}
function eventSourceIds(){return []}
""" + html[start:end] + """
assert.equal(mappedSeasonStatus({nonseasonal:true,season_status:'in'}),null);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main()
