import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_tennis_review", ROOT / "scripts" / "build_tennis_review.py"
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def season_map(*source_ids):
    return {"sports": [{"sport": "Tennis", "groups": [{"events": [
        {"source_id": source_id} for source_id in source_ids
    ]}]}]}


CONFIG = {
    "mode": "shadow",
    "active_field_types": ["ACTIVE_DRAW", "MAIN_DRAW", "ORDER_OF_PLAY"],
    "tour_approval_map": {"itf-men": "tennis-itf-world-tour"},
    "guardrails": {"active_field_only": True}
}


class TennisReviewTests(unittest.TestCase):
    def registry(self):
        return {"verified_u18": [{"name": "Alex Junior", "age": 17}],
                "junior_targeted_candidates": [{"name": "Taylor Maybe"}]}

    def tournament(self, **updates):
        row = {"id": "t1", "tour_id": "itf-men", "tour": "ITF",
               "tournament": "Test Open", "start_date": "2026-09-20",
               "end_date": "2026-09-25", "participant_field_type": "ACTIVE_DRAW",
               "participants": [{"name": "Alex Junior"}]}
        row.update(updates)
        return row

    def build(self, tournament, approved=True):
        smap = season_map("tennis-itf-world-tour") if approved else season_map("other")
        return MOD.build_review({"tournaments": [tournament]}, self.registry(), smap, CONFIG)

    def test_verified_u18_in_active_draw_is_red(self):
        out = self.build(self.tournament())
        self.assertEqual(out["summary"]["verified_u18_alerts"], 1)
        self.assertEqual(out["alerts"][0]["severity"], "RED")

    def test_acceptance_pool_never_creates_alert(self):
        out = self.build(self.tournament(participant_field_type="ACCEPTANCE_POOL"))
        self.assertEqual(out["alerts"], [])
        self.assertEqual(out["summary"]["field_pending"], 1)

    def test_schedule_does_not_create_ghost_approval(self):
        out = self.build(self.tournament(), approved=False)
        self.assertEqual(out["alerts"], [])
        self.assertEqual(out["summary"]["blocked_unapproved_or_unmapped"], 1)

    def test_targeted_identity_in_active_draw_is_amber(self):
        out = self.build(self.tournament(participants=[{"name": "Taylor Maybe"}]))
        self.assertEqual(out["summary"]["identity_reviews"], 1)
        self.assertEqual(out["alerts"][0]["severity"], "AMBER")

    def test_unknown_player_creates_no_alert(self):
        out = self.build(self.tournament(participants=[{"name": "Adult Unknown"}]))
        self.assertEqual(out["alerts"], [])

    def test_draw_label_without_extracted_players_remains_pending(self):
        out = self.build(self.tournament(participants=[], confirmed_u18=[], verified_u18=[]))
        self.assertEqual(out["summary"]["active_fields_screened"], 0)
        self.assertEqual(out["summary"]["field_pending"], 1)


if __name__ == "__main__":
    unittest.main()
