import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GolfTourCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.season_map = json.loads((ROOT / "data" / "catalog-season-map.json").read_text(encoding="utf-8"))
        cls.schedule = json.loads((ROOT / "data" / "global-schedule.json").read_text(encoding="utf-8"))

    def test_every_approved_tour_has_a_populated_dropdown_calendar(self):
        golf = next(sport for sport in self.season_map["sports"] if sport["sport"] == "Golf")
        approved_tours = [event for group in golf["groups"] for event in group["events"]
                          if event.get("category") == "Approved Tours"]
        calendars = {calendar["source_id"]: calendar for calendar in self.schedule["tour_calendars"]}
        self.assertEqual(12, len(approved_tours))
        for tour in approved_tours:
            with self.subTest(tour=tour["catalog_event"]):
                self.assertIn("source_id", tour)
                self.assertIn(tour["source_id"], calendars)
                self.assertGreater(len(calendars[tour["source_id"]]["events"]), 0)

    def test_presidents_cup_is_a_pga_tour_event_not_a_catalog_row(self):
        pga = next(calendar for calendar in self.schedule["tour_calendars"]
                   if calendar["source_id"] == "golf-pga-tour")
        presidents_cup = next(event for event in pga["events"]
                              if event["display_name"] == "Presidents Cup")
        self.assertEqual("Golf → PGA TOUR → Presidents Cup", presidents_cup["approval_path"])
        self.assertEqual("Created, controlled, and operated by the PGA TOUR", presidents_cup["governance"])
        self.assertEqual("https://www.presidentscup.com/", presidents_cup["source_url"])
        golf = next(sport for sport in self.season_map["sports"] if sport["sport"] == "Golf")
        catalog_names = {event["catalog_event"] for group in golf["groups"] for event in group["events"]}
        self.assertNotIn("Presidents Cup", catalog_names)


if __name__ == "__main__":
    unittest.main()
