"""Publisher calendars must keep exact series scope and reject missing structure."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from official_motorsports_calendar import PARSERS


class OfficialMotorsportsCalendarTests(unittest.TestCase):
    def test_configured_sources_and_inventory(self):
        sources = json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]
        configs = {s["id"]: s for s in sources if s.get("source_type") == "official-motorsports-calendar"}
        self.assertEqual({"motorsports-motogp": "motogp", "motorsports-nhra": "nhra",
                          "motorsports-supercars": "supercars", "motorsports-formula-e": "formula-e"},
                         {key: s["calendar_format"] for key, s in configs.items()})
        inventory = json.loads((ROOT / "data/priority2-coverage-inventory.json").read_text())
        for row in inventory["identities"]:
            if any(s["id"] in configs for s in row["sources"]):
                self.assertEqual("ADAPTER_CONFIGURED", row["coverage_state"])

    def test_motogp_requires_senior_2026_gp_events(self):
        def row(year, kind):
            return (f'<div data-widget="structured-data-event/structured-data-event" '
                    f'data-structured-title="Japanese Grand Prix" data-structured-year="{year}" '
                    f'data-structured-kind="{kind}" data-structured-start-date="2026-10-02T08:00:00+09:00" '
                    f'data-structured-end-date="2026-10-04T18:00:00+09:00" '
                    f'data-structured-country="Japan"></div>')
        events = PARSERS["motogp"](row("2026", "GP") * 15 + row("2027", "GP") + row("2026", "JUNIOR"), "https://motogp.com")
        self.assertEqual(15, len(events))
        self.assertEqual("2026-10-02", str(events[0]["start"]))
        with self.assertRaises(ValueError):
            PARSERS["motogp"](row("2027", "GP") * 20, "https://motogp.com")

    def test_nhra_only_mission_foods_and_detail_end_fallback(self):
        def row(number, series="nhra-mission-foods-drag-racing-series", end=True):
            end_tag = '<div property="endDate" content="2026-10-04T22:00:00-0700"></div>' if end else ''
            return (f'<div class="views-row" property="itemListElement" typeof="ListItem Event">'
                    f'<div property="startDate" content="2026-10-02T06:00:00-0700"></div>{end_tag}'
                    f'<h3 property="name"><a href="/schedule/2026/{series}/race-{number}">Race {number}</a></h3></div>')
        events = PARSERS["nhra"](''.join(row(i, end=i != 19) for i in range(20)) + row(21, "other-series"), "https://www.nhra.com/schedule/2026")
        self.assertEqual(20, len(events))
        self.assertIsNone(events[-1]["end"])
        with self.assertRaises(ValueError):
            PARSERS["nhra"](row(1, "other-series") * 20, "https://www.nhra.com/schedule/2026")

    def test_supercars_deduplicates_featured_and_requires_2026(self):
        rows = [{"title": f"2026 Race {i}", "slug": f"2026-race-{i}",
                 "startDate": "2026-10-08T06:00:00+11:00",
                 "endDate": "2026-10-11T18:00:00+11:00", "location": "Bathurst, NSW"} for i in range(14)]
        flight = '9:{"featuredEvents":' + json.dumps(rows[:2]) + ',"events":' + json.dumps(rows) + '}'
        page = '<script>self.__next_f.push([1,' + json.dumps(flight) + '])</script>'
        events = PARSERS["supercars"](page, "https://www.supercars.com/calendar")
        self.assertEqual(14, len(events))
        self.assertEqual("https://www.supercars.com/events/2026-race-0", events[0]["url"])

    def test_formula_e_holds_unlocated_round(self):
        rows = [{"position": i, "item": {"startDate": "2027-02-06", "endDate": "2027-02-06",
                 "location": {"name": "Americas" if i == 4 else "Jeddah"}}} for i in range(1, 22)]
        schema = {"@type": "ItemList", "numberOfItems": 21, "itemListElement": rows}
        page = '<script type="application/ld+json" id="calendar-schema">' + json.dumps(schema) + '</script>'
        events = PARSERS["formula-e"](page, "https://www.fiaformulae.com/en/calendar")
        self.assertEqual(20, len(events))
        self.assertFalse(any(event["id"].endswith("r04") for event in events))
        self.assertEqual("Formula E Round 1 · Jeddah", events[0]["name"])


if __name__ == "__main__":
    unittest.main()
