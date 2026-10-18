"""AUF rolling senior phases retain competition, edition and matchup identity."""

import copy
import sys
import unittest
from pathlib import Path

from lxml import html

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from auf_fixture_adapter import SOURCES, parse_fixtures

WOMEN = "conmebol-soccer-uruguay-campeonato-femenino-women"
CUP = "conmebol-soccer-uruguay-copa-uruguay-men"
FIXTURES = Path(__file__).parent / "fixtures"


def source(key):
    return {"id": key, "league": SOURCES[key]["league"],
            "catalog_terms": [SOURCES[key]["league"]],
            "endpoint": "https://www.auf.org.uy/"}


def page(key):
    kind = "women" if key == WOMEN else "cup"
    return (FIXTURES / f"auf-{kind}-20261018.html").read_text()


def blocks(doc):
    return doc.xpath('//*[@class="cont-fixture_campeonato"]')


def serialize(doc):
    return html.tostring(doc, encoding="unicode")


class AufFixtureAdapterTests(unittest.TestCase):
    def test_womens_current_phase_recovery(self):
        diagnostics = {}
        events, count, held = parse_fixtures(page(WOMEN), source(WOMEN), diagnostics=diagnostics)
        self.assertEqual({"undated_pairings_held": 4}, diagnostics)
        self.assertEqual((1, 101, 0), (len(events), count, held))
        self.assertEqual("Wanderers at Danubio", events[0]["name"])
        self.assertEqual("2026-10-18T21:00Z", events[0]["start_time"])
        with self.assertRaisesRegex(ValueError, "page identity"):
            parse_fixtures(page(CUP), source(WOMEN))

    def test_cup_professional_second_phase_holds_all_amateur_phases(self):
        events, count, held = parse_fixtures(page(CUP), source(CUP))
        self.assertEqual((2, 56, 12), (len(events), count, held))
        self.assertEqual([("Cerro Largo at Liverpool", "2026-10-21T19:00Z"),
                          ("M.C. Torque at Peñarol", "2026-10-27T23:00Z")],
                         [(e["name"], e["start_time"]) for e in events])

    def test_phase_reordering_does_not_change_event_identity(self):
        for key in (CUP, WOMEN):
            doc = html.fromstring(page(key))
            for block in reversed(blocks(doc)):
                doc.append(block)
            before = parse_fixtures(page(key), source(key))[0]
            after = parse_fixtures(serialize(doc), source(key))[0]
            self.assertEqual(sorted(before, key=lambda e: e["id"]),
                             sorted(after, key=lambda e: e["id"]))

    def test_rolling_page_can_remove_completed_rounds(self):
        for key in (CUP, WOMEN):
            doc = html.fromstring(page(key))
            for block in blocks(doc)[:-1]:
                block.getparent().remove(block)
            self.assertEqual(parse_fixtures(page(key), source(key))[0],
                             parse_fixtures(serialize(doc), source(key))[0])

    def test_next_womens_round_gains_exact_published_kickoff(self):
        doc = html.fromstring(page(WOMEN))
        row = blocks(doc)[-1].xpath('.//*[contains(@class,"item-fixture")]')[6]
        stamp = row.xpath('.//strong')[0]
        self.assertFalse((stamp.text or "").strip())
        stamp.text = "25/10/2026 - 17:30 h"
        events = parse_fixtures(serialize(doc), source(WOMEN))[0]
        self.assertEqual(2, len(events))
        self.assertEqual(("Danubio at Canadian", "2026-10-25T20:30Z"),
                         (events[1]["name"], events[1]["start_time"]))

    def test_next_professional_phase_and_fewer_published_rows(self):
        doc = html.fromstring(page(CUP))
        for block in blocks(doc)[:-1]:
            block.getparent().remove(block)
        block = blocks(doc)[0]
        block.xpath('./h3')[0].text = "Tercera Fase - FASE III ELIM PROF"
        for row in block.xpath('.//*[contains(@class,"item-fixture")]')[:-2]:
            row.getparent().remove(row)
        events, count, held = parse_fixtures(serialize(doc), source(CUP))
        self.assertEqual((2, 2, 0), (len(events), count, held))

    def test_unknown_phase_and_mixed_eliminations_rejected(self):
        for replacement in ("GRUPO 9", "SUB 20", "FASE II ELIM MIXTA"):
            with self.subTest(replacement=replacement), self.assertRaisesRegex(ValueError, "phases changed"):
                parse_fixtures(page(CUP).replace("GRUPO 3", replacement), source(CUP))

    def test_duplicate_fixture_or_conflicting_time_rejected(self):
        for altered in (False, True):
            doc = html.fromstring(page(CUP))
            block = blocks(doc)[-1]
            row = copy.deepcopy(block.xpath('.//*[contains(@class,"item-fixture")]')[-1])
            if altered:
                row.xpath('.//strong')[0].text = "27/10/2026 - 21:00 h"
            block.append(row)
            with self.assertRaisesRegex(ValueError, "duplicate fixture"):
                parse_fixtures(serialize(doc), source(CUP))

    def test_duplicate_phase_rejected(self):
        doc = html.fromstring(page(CUP))
        doc.append(copy.deepcopy(blocks(doc)[-1]))
        with self.assertRaisesRegex(ValueError, "duplicate phase"):
            parse_fixtures(serialize(doc), source(CUP))

    def test_competition_gender_edition_and_senior_scope_rejected(self):
        for original, replacement in (("Campeonato Femenino A - AUF", "Campeonato Femenino B - AUF"),
                                      ("2026", "2027"),
                                      ("/ff-danubio/", "/danubio-futbol-club/"),
                                      ("/ff-danubio/", "/ff-sub-20-danubio/")):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                parse_fixtures(page(WOMEN).replace(original, replacement), source(WOMEN))
        with self.assertRaisesRegex(ValueError, "kickoff format"):
            parse_fixtures(page(CUP).replace("2026", "2025"), source(CUP))
        wrong = source(CUP)
        wrong["league"] = SOURCES[WOMEN]["league"]
        with self.assertRaisesRegex(ValueError, "approval scope"):
            parse_fixtures(page(CUP), wrong)

    def test_malformed_and_ambiguous_kickoff_rejected(self):
        for stamp in ("21/10/2026 - TBD", "21/10/2026 - 25:00 h"):
            with self.assertRaises(ValueError):
                parse_fixtures(page(CUP).replace("21/10/2026 - 16:00 h", stamp), source(CUP))
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            parse_fixtures(page(CUP).replace("21/10/2026 - 16:00 h</strong>",
                "21/10/2026 - 16:00 h</strong><strong>22/10/2026 - 16:00 h</strong>"), source(CUP))

    def test_matchup_label_and_path_identity_must_agree(self):
        with self.assertRaisesRegex(ValueError, "participant scope"):
            parse_fixtures(page(WOMEN).replace('>Danubio</span>', '>Danubio Sub 20</span>'), source(WOMEN))

    def test_mismatched_professional_phase_number_rejected(self):
        with self.assertRaisesRegex(ValueError, "phases changed"):
            parse_fixtures(page(CUP).replace('Segunda Fase - FASE II', 'Segunda Fase - FASE III'), source(CUP))

    def test_windows_1252_live_encoding(self):
        self.assertEqual(parse_fixtures(page(CUP), source(CUP)),
                         parse_fixtures(page(CUP).encode('windows-1252'), source(CUP)))


if __name__ == "__main__":
    unittest.main()
