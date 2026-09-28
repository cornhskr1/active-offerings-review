import unittest

from scripts.liga_portugal_2_calendar import parse_calendar


SOURCE = {"id": "uefa-soccer-portugal-liga-portugal-2-men", "catalog_terms": ["Liga Portugal 2 | Men"],
          "league": "Liga Portugal 2 | Men", "sport": "Soccer", "region": "Portugal"}


def event(number, home, away, start, end):
    url = f"https://www.ligaportugal.pt/match/20262027/ligaportugalmeusuper/5/{number}"
    return "\n".join(["BEGIN:VEVENT", f"UID:00000000-0000-4000-8000-{number:012d}",
        "CATEGORIES:Liga Portugal", "CATEGORIES:2026-2027", "CATEGORIES:Liga Portugal Meu Super",
        f"CATEGORIES:{home}", f"CATEGORIES:{away}", "CLASS:PUBLIC",
        f"DESCRIPTION:Liga Portugal Meu Super\\, jornada 5\\nUrl: {url}",
        f"DTSTART:{start}", f"DTEND:{end}", "LOCATION:Estádio Exemplo",
        f"SUMMARY:{home} - {away}", f"URL:{url}", "END:VEVENT"])


class LigaPortugalCalendarTest(unittest.TestCase):
    def test_exact_fixture_and_explicit_holds(self):
        payload = "\n".join(["BEGIN:VCALENDAR", "VERSION:2.0",
            "PRODID://Liga Portuguesa de Futebol Profissional//Calendário de jogos Liga Portugal Meu Super - 2026-2027//PT",
            event(1, "SC Farense", "GD Chaves", "20261004T100000Z", "20261004T114500Z"),
            event(2, "Benfica B", "GD Chaves", "20261004T100000Z", "20261004T114500Z"),
            event(3, "SC Farense", "GD Chaves", "20270103T000000Z", "20270103T014500Z"),
            "END:VCALENDAR"])
        events, placeholders, reserves, total = parse_calendar(payload, SOURCE)
        self.assertEqual((placeholders, reserves, total), (1, 1, 3))
        self.assertEqual([(e["name"], e["start_time"]) for e in events],
                         [("GD Chaves at SC Farense", "2026-10-04T10:00:00Z")])

    def test_wrong_competition_fails_closed(self):
        payload = "\n".join(["BEGIN:VCALENDAR", "VERSION:2.0",
            "PRODID://Liga Portuguesa de Futebol Profissional//Calendário de jogos Liga Portugal Meu Super - 2026-2027//PT",
            event(1, "SC Farense", "GD Chaves", "20261004T100000Z", "20261004T114500Z")
                .replace("CATEGORIES:Liga Portugal Meu Super", "CATEGORIES:Liga Portugal Betclic"),
            "END:VCALENDAR"])
        with self.assertRaises(ValueError):
            parse_calendar(payload, SOURCE)


if __name__ == "__main__":
    unittest.main()
