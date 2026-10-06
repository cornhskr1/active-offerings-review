import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from nzr_farah_palmer_fixture_adapter import CLUBS, parse_semifinals


SOURCE = {"id": "rugby-nzr-farah-palmer-2026", "sport": "Rugby",
          "league": "Farah Palmer Cup | Women", "region": "New Zealand",
          "catalog_terms": ["Farah Palmer Cup | Women"],
          "endpoint": "https://www.provincial.rugby/farah-palmer-cup/where-to-watch-the-farah-palmer-cup"}


def row(home, away, stamp, watch="Livestream"):
    return f"<tr><td>{home}</td><td>{away}</td><td>{stamp}</td><td>{watch}</td></tr>"


def section(name, rows):
    return f'<section class="fixtures-table"><h4>{name}</h4><table><tbody>{rows}</tbody></table></section>'


def page():
    clubs = sorted(CLUBS)
    rounds = "".join(section(name, "".join(
        row(clubs[i], clubs[i + 1], f"Saturday {day} {month}, 2:05pm")
        for i in range(0, 12, 2))) for name, day, month in (
            ("Round One", 29, "August"), ("Round Two", 5, "September"),
            ("Round Three", 12, "September"), ("Round Four", 19, "September"),
            ("Round Five", 26, "September")))
    semifinal = section("Semi-Finals", row("Championship", "", "", "") +
        row("Northland Kauri", "Otago Spirit", "Saturday 3 October, 2:05pm") +
        row("Wellington Pride", "Hawke's Bay Tui", "Saturday 3 October, 2:05pm") +
        row("Premiership", "", "", "") +
        row("Auckland Storm", "Waitomo Waikato", "Saturday 3 October, 2:05pm") +
        row("Canterbury", "Manawatū Cyclones", "Sunday 4 October, 2:05pm"))
    final = section("Grand Finals", row("Championship", "", "", "") +
        row("TBC", "TBC", "") + row("Premiership", "", "", "") + row("TBC", "TBC", ""))
    return ("<meta charset=\"utf-8\"><h1>Where to watch the Farah Palmer Cup, presented by Hilux</h1>" +
            rounds + semifinal + final).encode()


class FarahPalmerAdapterTests(unittest.TestCase):
    def test_publisher_semifinals_are_scoped_and_timed(self):
        events, regular, finals_held = parse_semifinals(page(), SOURCE)
        self.assertEqual((4, 30, 2), (len(events), regular, finals_held))
        self.assertEqual("2026-10-03T01:05:00Z", events[0]["start_time"])
        self.assertEqual("Otago Spirit at Northland Kauri", events[0]["name"])

    def test_unresolved_semifinal_is_not_published(self):
        unresolved = page().replace(b"Northland Kauri</td><td>Otago Spirit",
                                    b"Northland Kauri</td><td>TBC", 1)
        with self.assertRaisesRegex(ValueError, "pairing"):
            parse_semifinals(unresolved, SOURCE)

    def test_wrong_year_weekday_is_not_published(self):
        changed = page().replace(b"Saturday 3 October", b"Sunday 3 October", 1)
        with self.assertRaisesRegex(ValueError, "weekday"):
            parse_semifinals(changed, SOURCE)

    def test_live_published_finals_and_new_zealand_clock(self):
        raw=(Path(__file__).parent/'fixtures/nzr-fpc-finals-20261006.html').read_bytes()
        events,regular,held=parse_semifinals(raw,SOURCE)
        finals=[e for e in events if e['season_stage']=='FINAL']
        self.assertEqual((6,30,0),(len(events),regular,held))
        self.assertEqual(['Northland Kauri at Wellington Pride','Auckland Storm at Canterbury'],[e['name'] for e in finals])
        self.assertEqual(['2026-10-09T23:05:00Z','2026-10-11T03:05:00Z'],[e['start_time'] for e in finals])

    def test_final_scope_and_partial_pairings_are_held(self):
        raw=(Path(__file__).parent/'fixtures/nzr-fpc-finals-20261006.html').read_bytes()
        for altered in [raw.replace(b'>Northland<',b'>Auckland<'),raw.replace(b'12.05pm',b'13.05pm'),raw.replace(b'Saturday 10 October',b'Sunday 10 October')]:
            with self.subTest(altered=altered[-100:]),self.assertRaises(ValueError):
                parse_semifinals(altered,SOURCE)
        events,_,held=parse_semifinals(raw.replace(b'>Northland<',b'>TBC<'),SOURCE)
        self.assertEqual((5,1),(len(events),held))

    def test_final_kickoff_change_preserves_publisher_slot_identity(self):
        raw=(Path(__file__).parent/'fixtures/nzr-fpc-finals-20261006.html').read_bytes()
        before=parse_semifinals(raw,SOURCE)[0][-2]
        after=parse_semifinals(raw.replace(b'12.05pm',b'1.05pm'),SOURCE)[0][-2]
        self.assertEqual(before['id'],after['id'])
        self.assertEqual('2026-10-10T00:05:00Z',after['start_time'])


if __name__ == "__main__":
    unittest.main()
