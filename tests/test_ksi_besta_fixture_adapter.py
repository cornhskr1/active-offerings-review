"""Both KSÍ final groups must provide the same complete upcoming round."""

import datetime
import unittest

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
