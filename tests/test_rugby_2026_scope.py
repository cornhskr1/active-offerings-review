"""The 2026 provincial calendars must not imply a Rugby Championship edition or fixture feed."""

import json
import subprocess
import unittest
from pathlib import Path

from scripts.audit_priority2_coverage import build


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


class Rugby2026ScopeTests(unittest.TestCase):
    def test_edition_windows_remain_separate_from_unattended_fixtures(self):
        season_map = json.loads((DATA / "catalog-season-map.json").read_text())
        rugby = next(sport for sport in season_map["sports"] if sport["sport"] == "Rugby")
        mapped = {event["key"]: event for group in rugby["groups"] for event in group["events"]}
        rows = {row["identity_key"]: row for row in build()["identities"]}
        for key, start, end in (
            ("rugby-nz-npc", "2026-07-30", "2026-10-25"),
            ("rugby-nz-heartland", "2026-08-15", "2026-10-18"),
            ("rugby-nz-farah-palmer", "2026-08-29", "2026-10-11"),
        ):
            with self.subTest(key=key):
                event = mapped[key]
                self.assertEqual((start, end), (event["season_start_date"], event["season_end_date"]))
                self.assertEqual("rugby-nzr", event["source_id"])
                self.assertEqual(("DATED_WINDOW", "ADAPTER_GAP", 0),
                                 (rows[key]["season_state"], rows[key]["coverage_state"],
                                  rows[key]["events_in_window"]))

        championship = mapped["rugby-intl-rugby-championship"]
        self.assertEqual(("out", 2026, True),
                         (championship["season_status"], championship["season_status_year"],
                          championship["season_hold"]))
        self.assertNotIn("season_start", championship)
        self.assertNotIn("season_start_date", championship)
        self.assertEqual(("DOCUMENTED_HOLD", "ADAPTER_GAP"),
                         (rows[championship["key"]]["season_state"],
                          rows[championship["key"]]["coverage_state"]))

    def test_no_2026_status_does_not_carry_into_2027(self):
        html = (ROOT / "index.html").read_text()
        start = html.index("function mappedSeasonStatus(")
        end = html.index("\nfunction mappedCatalogEventForSource(", start)
        script = """
const assert=require('node:assert/strict');
let current='2026-09-27';
const todayKey=()=>current;
const DATA={global:{sources:[{id:'rugby-sanzaar',events:20}]}};
function exactSeasonStatus(){return null}
function annualSeasonStatus(){return null}
function eventSourceIds(event){return [event.source_id]}
""" + html[start:end] + """
const event={source_id:'rugby-sanzaar',season_hold:true,season_status:'out',season_status_year:2026};
assert.equal(mappedSeasonStatus(event),'out');
current='2027-09-27';
assert.equal(mappedSeasonStatus(event),null);
"""
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)


if __name__ == "__main__":
    unittest.main()
