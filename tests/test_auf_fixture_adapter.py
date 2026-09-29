"""The AUF source must not mix women's levels or cup participant phases."""

import itertools
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from auf_fixture_adapter import SOURCES, parse_fixtures


WOMEN = "conmebol-soccer-uruguay-campeonato-femenino-women"
CUP = "conmebol-soccer-uruguay-copa-uruguay-men"


def source(key):
    return {"id": key, "league": SOURCES[key]["league"],
            "catalog_terms": [SOURCES[key]["league"]],
            "endpoint": "https://www.auf.org.uy/"}


def row(home, away, date="30/09/2026", score=""):
    return (f'<div class="row item-fixture"><div class="col"><a href="/{home}/">'
            f'<span class="hidden-xs">{home}</span></a></div>'
            f'<div class="resultado">{score}</div><div class="club2"><a href="/{away}/">'
            f'<span class="hidden-xs">{away}</span></a></div>'
            f'<div class="fecha_estadio"><strong>{date} - 16:00 h</strong>Estadio Uno</div></div>')


def page(key):
    scope = SOURCES[key]
    blocks = []
    for n, title in enumerate(scope["headings"]):
        if key == WOMEN:
            clubs = [f"Women {i}" for i in range(10)]
            pairs = list(itertools.combinations(clubs, 2))
            rows = [row(a, b, "20/09/2026", "1 - 0") for a, b in pairs]
        elif n == 6:
            rows = [row(f"Amateur {i}", f"Amateur {i+4}", "17/09/2026", "1 - 0") for i in range(4)]
        else:
            clubs = [f"Group {n} Club {i}" for i in range(4)]
            pairs = list(itertools.combinations(clubs, 2))
            rows = [row(a, b, score="" if n == 1 and i < 2 else "1 - 0")
                    for i, (a, b) in enumerate(pairs)]
        blocks.append(f'<div class="cont-fixture_campeonato"><h3>{title}</h3>{"".join(rows)}</div>')
    return f'<html><title>{scope["title"]}</title>{"".join(blocks)}</html>'


class AufFixtureAdapterTests(unittest.TestCase):
    def test_womens_a_first_phase_is_separate_from_cup(self):
        events, count, held = parse_fixtures(page(WOMEN), source(WOMEN))
        self.assertEqual((0, 90, 0), (len(events), count, held))
        with self.assertRaisesRegex(ValueError, "page identity"):
            parse_fixtures(page(CUP), source(WOMEN))

    def test_cup_professional_groups_hold_amateur_phase(self):
        events, count, held = parse_fixtures(page(CUP), source(CUP))
        self.assertEqual((2, 40, 4), (len(events), count, held))
        self.assertEqual("2026-09-30T19:00Z", events[0]["start_time"])
        self.assertTrue(all("Amateur" not in e["name"] for e in events))

    def test_phase_change_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "phases changed"):
            parse_fixtures(page(CUP).replace("GRUPO 3", "GRUPO 9"), source(CUP))


if __name__ == "__main__":
    unittest.main()
