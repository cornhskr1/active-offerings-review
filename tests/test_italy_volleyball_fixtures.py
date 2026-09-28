import datetime
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from italy_volleyball_fixtures import parse_serie_a1, parse_superlega


class ItalyVolleyballFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {s["id"]: s for s in json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]}
        cls.men = (ROOT / "tests/fixtures/italy_superlega_2026.html").read_text()
        cls.women = (ROOT / "tests/fixtures/italy_serie_a1_2026.html").read_text()
        cls.today, cls.end = datetime.date(2026, 9, 28), datetime.date(2026, 10, 5)

    def test_exact_first_leg_and_first_five_rounds(self):
        men = parse_superlega(self.men, self.sources["volleyball-italy-superlega"], self.today, self.end)
        women = parse_serie_a1(self.women, self.sources["volleyball-italy-serie-a1-women"], self.today, self.end)
        self.assertEqual((len(men), len(women)), (66, 35))
        self.assertEqual(men[0]["start_time"], "2026-10-17T16:00:00Z")
        self.assertEqual(women[0]["start_time"], "2026-10-03T18:30:00Z")
        self.assertEqual(len([x for x in women if x["start_time"][:10] in ("2026-10-03", "2026-10-04")]), 7)
        self.assertEqual(len({x["id"] for x in men + women}), 101)

    def test_wrong_division_missing_round_and_stale_horizon_fail_closed(self):
        men = self.sources["volleyball-italy-superlega"]
        women = self.sources["volleyball-italy-serie-a1-women"]
        with self.assertRaises(ValueError):
            parse_superlega(self.men.replace('selected value="999"', 'selected value="1000"'), men, self.today, self.end)
        with self.assertRaises(ValueError):
            parse_serie_a1(self.women.replace("5^ Giornata", "6^ Giornata"), women, self.today, self.end)
        with self.assertRaises(ValueError):
            parse_serie_a1(self.women, women, datetime.date(2026, 10, 27), datetime.date(2026, 11, 3))
        with self.assertRaises(ValueError):
            parse_superlega(self.men, men, datetime.date(2026, 12, 19), datetime.date(2026, 12, 26))


if __name__ == "__main__":
    unittest.main()
