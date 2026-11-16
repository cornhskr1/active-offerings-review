import copy
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_tennis_review import build_review
from build_catalog_change_queue import build_catalog_changes

class Wta125ApprovalTests(unittest.TestCase):
    def test_distinct_identity_unknown_dates_and_queue_mapping(self):
        season=json.loads((ROOT/"data/catalog-season-map.json").read_text())
        events=[e for s in season["sports"] if s["sport"]=="Tennis" for g in s["groups"] for e in g["events"]]
        wta=next(e for e in events if e["key"]=="tennis-wta-125")
        self.assertEqual(wta["catalog_event"], "WTA 125 | Women")
        self.assertNotEqual(wta["source_id"],next(e for e in events if e["key"]=="tennis-wta-tour")["source_id"])
        self.assertFalse(wta["season_window_complete"])
        self.assertNotIn("season_start_date",wta)
        self.assertNotIn("season_end_date",wta)
        catalog={"sections":[{"sport":"Tennis","lines":["Women’s Tennis Association (WTA)","WTA 125 | Women"]}]}
        self.assertFalse(any(x.get("title")=="WTA 125 | Women" and x.get("item_type")=="catalog-addition" for x in build_catalog_changes(catalog,season)))
        ledger=json.loads((ROOT/"data/catalog-season-verification-ledger.json").read_text())
        self.assertEqual(ledger["completion_reconciliation"]["pending_count"],1)
        self.assertFalse(ledger["completion_reconciliation"]["first_pass_complete"])

    def test_tour_approval_never_approves_125_or_clears_age(self):
        config=json.loads((ROOT/"data/tennis-v2-config.json").read_text())
        tournament={"id":"synthetic-125","tour_id":"wta-125","tournament":"Synthetic 125","participant_field_type":"ACTIVE_DRAW","participants":[{"name":"Unknown Player"}]}
        def smap(sid): return {"sports":[{"sport":"Tennis","groups":[{"events":[{"source_id":sid}]}]}]}
        out=build_review({"tournaments":[tournament]}, {}, smap("wta-tennis"), config)
        self.assertEqual(out["summary"]["blocked_unapproved_or_unmapped"],1)
        out=build_review({"tournaments":[tournament]}, {}, smap("tennis-wta-125"), config)
        self.assertEqual(out["alerts"],[])
        self.assertEqual(out["coverage"][0]["source_id"],"tennis-wta-125")
