import datetime
import json
import unittest

from scripts.oefb_fixture_adapter import current_and_next_rounds, parse_round, round_url


SOURCE = {
    "id": "uefa-soccer-austria-austrian-frauen-bundesliga-women",
    "sport": "Soccer", "league": "Austrian Frauen-Bundesliga | Women",
    "region": "Austria", "catalog_terms": ["Austrian Frauen-Bundesliga | Women"],
}
TITLE = "ADMIRAL Frauen Bundesliga - Grunddurchgang"


def page():
    data = {"id": "232361", "title": TITLE, "runden": [
        {"runde": 8, "aktuell": True}, {"runde": 9, "aktuell": False},
        {"runde": 10, "aktuell": False}]}
    return ('SG.container.deliveryInfo.project = {"oid":"1469066385635312874"};'
            + "SG.container.appPreloads['fixtures']=" + json.dumps([data]) + ";")


def fixture(n, *, midnight=False):
    instant = datetime.datetime(2026, 10, 2 if midnight else 3, 22 if midnight else 12,
                                tzinfo=datetime.timezone.utc)
    return {
        "heimMannschaft": f"Club {n}", "gastMannschaft": f"Visitor {n}",
        "heimMannschaftId": f"home-{n}", "gastMannschaftId": f"away-{n}",
        "runde": 9, "bewerb": TITLE, "spielart": "Meisterschaft",
        "teamType": "KM Frauen", "status": "offen",
        "anstoss": int(instant.timestamp() * 1000),
        "actionLink": f"https://www.oefb.at/oefb/Spiel/4000{n}/?match",
    }


class OefbFixtureTests(unittest.TestCase):
    def test_selects_current_and_next_verified_round(self):
        self.assertEqual(current_and_next_rounds(page(), SOURCE), [8, 9])
        self.assertIn("spielplanBewerbByPublicUid%2F232361%3Brunde%3D9", round_url(SOURCE, 9, page()))

    def test_exact_senior_pairings_and_midnight_hold(self):
        payload = {"id": "232361", "title": TITLE,
                   "spiele": [fixture(1), fixture(2), fixture(3), fixture(4), fixture(5, midnight=True)],
                   "ergebnisse": []}
        events, held, total = parse_round(payload, SOURCE, 9)
        self.assertEqual((len(events), held, total), (4, 1, 5))
        self.assertEqual(events[0]["start_time"], "2026-10-03T12:00:00Z")
        self.assertEqual(events[0]["source_id"], SOURCE["id"])

    def test_rejects_wrong_competition_and_incomplete_round(self):
        payload = {"id": "232361", "title": TITLE,
                   "spiele": [fixture(1)], "ergebnisse": []}
        with self.assertRaisesRegex(ValueError, "expected 5"):
            parse_round(payload, SOURCE, 9)
        payload["spiele"] = [fixture(n) for n in range(1, 6)]
        payload["spiele"][2]["teamType"] = "U19 Frauen"
        with self.assertRaisesRegex(ValueError, "senior scope"):
            parse_round(payload, SOURCE, 9)


if __name__ == "__main__":
    unittest.main()
