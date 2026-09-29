"""Published seasons must not masquerade as today's scheduled events."""

import datetime
import json
import unittest
from pathlib import Path
from sys import path as sys_path


ROOT = Path(__file__).resolve().parents[1]
sys_path.insert(0, str(ROOT / "scripts"))
from official_window_activity import reviewable_window_start  # noqa: E402


class OfficialWindowActivityTests(unittest.TestCase):
    def test_current_published_seasons_do_not_create_review_today_cards(self):
        today = datetime.date(2026, 9, 28)
        review_end = today + datetime.timedelta(days=7)
        sources = json.loads((ROOT / "data" / "global-schedule-sources.json").read_text())["sources"]
        current = []
        for source in sources:
            if source.get("source_type") != "official-event-window":
                continue
            for event in source.get("official_events", []):
                start = datetime.date.fromisoformat(event["start_date"])
                end = datetime.date.fromisoformat(event.get("end_date") or event["start_date"])
                if start <= review_end and end >= today:
                    current.append((event["source_id"], start, end))
        self.assertEqual(11, len(current))
        self.assertIn("basketball-euroleague", {sid for sid, _, _ in current})
        self.assertIn("surfing-wsl-championship-tour-women", {sid for sid, _, _ in current})
        self.assertFalse(any(reviewable_window_start(start, end, today, review_end)
                             for _, start, end in current))

    def test_short_published_event_is_reviewable_only_on_its_opening_day(self):
        today = datetime.date(2026, 9, 28)
        opening = datetime.date(2026, 10, 1)
        closing = datetime.date(2026, 10, 4)
        self.assertTrue(reviewable_window_start(opening, closing, today, today + datetime.timedelta(days=7)))
        self.assertFalse(reviewable_window_start(opening, closing, opening + datetime.timedelta(days=1),
                                                 opening + datetime.timedelta(days=8)))
        self.assertFalse(reviewable_window_start(opening, closing, today, today + datetime.timedelta(days=2)))


if __name__ == "__main__":
    unittest.main()
