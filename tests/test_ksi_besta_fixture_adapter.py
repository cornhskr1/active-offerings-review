"""Both KSÍ final groups must provide the same complete upcoming round."""

import datetime
import unittest
from pathlib import Path
from lxml import html

from scripts.ksi_besta_fixture_adapter import next_round


SOURCE = {"id":"uefa-soccer-iceland-besta-deild-karla-rvalsdeild-men", "sport":"Soccer",
          "league":"Besta deild karla / Úrvalsdeild | Men", "region":"Iceland",
          "catalog_terms":["Besta deild karla / Úrvalsdeild | Men"]}


def pages():
    result = {}
    for cid, phase in (("7025527", "Efri hluti"), ("7025532", "Neðri hluti")):
        title = f"Besta deild karla 2026 - {phase}"
        cards = []
        for number in range(6):
            day = "10" if number < 3 else "17"
            cards.append(f'''<div class="grid-cols-[70%_auto]">
                <div><span class="body-5">Lau {day}. október 14:00</span>
                <span class="body-5">Stadium {number}</span><span class="body-5">{title}</span></div>
                <div class="grid-cols-[1fr_auto_1fr]">
                <a href="/oll-mot/mot/lid?id={number*2+1}&amp;competitionId={cid}">Home {number}</a>
                <a href="/oll-mot/mot/lid?id={number*2+2}&amp;competitionId={cid}">Away {number}</a>
                </div></div>''')
        header = f"<h1>{title}</h1>"
        result[cid] = (header + ''.join(cards),
                       header + '<button class="link-dropdown-trigger"><span>Umferð 3</span></button>'
                       + ''.join(cards[:3]))
    return result


class KsiBestaTests(unittest.TestCase):
    def completed_pages(self):
        root = Path(__file__).parent / "fixtures"
        return {cid: tuple((root / f"ksi_completed_{phase}{suffix}.html").read_text()
                           for suffix in ("", "-rounds"))
                for cid, phase in (("7025527", "upper"), ("7025532", "lower"))}

    def test_completed_final_groups_are_healthy_empty(self):
        self.assertEqual(([], 0, 0), next_round(self.completed_pages(), SOURCE, datetime.date(2026, 10, 31)))

    def test_completed_evidence_must_be_complete_and_consistent(self):
        changes = [
            (0, '2 - 2', 'TBC'),
            (0, '7100161', '9999999'),
            (0, 'competitionId=7025527', 'competitionId=youth'),
            (0, 'Víkingur R.', 'Unknown'),
            (0, '24. október', '25. október'),
            (1, 'Umferð 5', 'Umferð 4'),
            (1, '8 - 3', '8 - 2'),
        ]
        for view, old, new in changes:
            with self.subTest(change=(view, old, new)):
                both = self.completed_pages()
                pair = list(both['7025527'])
                self.assertIn(old, pair[view])
                pair[view] = pair[view].replace(old, new, 1)
                both['7025527'] = tuple(pair)
                with self.assertRaises(ValueError):
                    next_round(both, SOURCE, datetime.date(2026, 10, 31))
        both = self.completed_pages()
        both['7025532'] = pages()['7025532']
        with self.assertRaises(ValueError):
            next_round(both, SOURCE, datetime.date(2026, 10, 31))
        both = self.completed_pages()
        doc = html.fromstring(both['7025527'][0])
        cards = doc.xpath('//div[@class="grid-cols-[70%_auto]"]')
        cards[0].getparent().remove(cards[0])
        both['7025527'] = (html.tostring(doc, encoding='unicode'), both['7025527'][1])
        with self.assertRaises(ValueError):
            next_round(both, SOURCE, datetime.date(2026, 10, 31))
        with self.assertRaises(ValueError):
            next_round(self.completed_pages(), SOURCE, datetime.date(2026, 10, 24))

    def test_both_phases_cross_checked(self):
        fixtures, count, held = next_round(pages(), SOURCE, datetime.date(2026, 9, 28))
        self.assertEqual((len(fixtures), count, held), (6, 12, 6))
        self.assertEqual({f["start_time"] for f in fixtures}, {"2026-10-10T14:00:00Z"})
        self.assertEqual(len({f["id"] for f in fixtures}), 6)

    def test_missing_phase_and_youth_link_fail_closed(self):
        both = pages()
        cid = "7025532"
        both[cid] = (both[cid][0], both[cid][1].replace("Umferð 3", "Umferð 4"))
        with self.assertRaisesRegex(ValueError, "disagree"):
            next_round(both, SOURCE, datetime.date(2026, 9, 28))
        both = pages()
        both[cid] = (both[cid][0].replace("competitionId=7025532", "competitionId=youth", 1), both[cid][1])
        with self.assertRaisesRegex(ValueError, "team link"):
            next_round(both, SOURCE, datetime.date(2026, 9, 28))


if __name__ == "__main__":
    unittest.main()
