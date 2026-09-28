"""Publisher fixtures remain scoped to the exact NBB and Beach Pro Tour identities."""

import json
import sys
import unittest
from unittest.mock import Mock
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from publisher_basketball_beach import fetch_nbb_schedule, parse_beach_calendar, parse_nbb_fixtures  # noqa: E402


class PublisherScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sources = json.loads((ROOT / "data/global-schedule-sources.json").read_text())["sources"]
        cls.sources = {source["id"]: source for source in sources}

    def nbb_page(self, altered=""):
        rows = []
        for number in range(1, 21):
            rows.append(f'''<tr><td class="position_value" data-label="JOGO" data-real-id="{27100+number}">{number}</td>
              <td data-label="DATA"><span>17/10/2026</span><span>16:00</span></td>
              <td data-label="CASA">Home {number}</td><td data-label="VISITANTE">Away {number}</td>
              <td data-label="CAMPEONATO">2026/2027</td>
              <td><a href="https://lnb.com.br/partidas/nbb-2026-2027-match-{number}/">Details</a></td></tr>''')
        return "<title>Tabela de Jogos – Liga Nacional de Basquete</title><table>" + "".join(rows).replace("2026/2027", altered or "2026/2027", 1) + "</table>"

    def test_nbb_edition_pairing_and_brazil_kickoff(self):
        source = self.sources["basketball-br-nbb"]
        events = parse_nbb_fixtures(self.nbb_page(), source)
        self.assertEqual(20, len(events))
        self.assertEqual("Away 1 at Home 1", events[0]["name"])
        self.assertEqual("2026-10-17T19:00:00Z", events[0]["start_time"])
        with self.assertRaises(ValueError):
            parse_nbb_fixtures(self.nbb_page().replace("Away 1", "Home 1", 1), source)
        with self.assertRaises(ValueError):
            parse_nbb_fixtures(self.nbb_page().replace("2026/2027", "2025/2026"), source)
        with self.assertRaises(ValueError):
            parse_nbb_fixtures(self.nbb_page(), {**source, "catalog_terms": ["Philippine Basketball Association (PBA) | Men"]})

    def test_nbb_403_retries_browser_headers_but_persistent_block_fails(self):
        blocked = Mock(status_code=403)
        blocked.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        accepted = Mock(status_code=200, text=self.nbb_page())
        accepted.raise_for_status.return_value = None
        get = Mock(side_effect=[blocked, accepted])
        page = fetch_nbb_schedule(self.sources["basketball-br-nbb"]["endpoint"], get=get)
        self.assertEqual(len(parse_nbb_fixtures(page, self.sources["basketball-br-nbb"])), 20)
        self.assertIn("pt-BR", get.call_args.kwargs["headers"]["Accept-Language"])
        with self.assertRaises(requests.HTTPError):
            fetch_nbb_schedule(self.sources["basketball-br-nbb"]["endpoint"], get=Mock(return_value=blocked))

    def test_beach_calendar_uses_separate_gender_ids_and_event_windows(self):
        record = {"season": "2026", "discipline": "beach", "competitionFullName": "Futures - Alanya, TUR - 2026",
                  "startDate": "2026-10-15T07:00:00Z", "endDate": "2026-10-18T20:00:00Z",
                  "url": "/beachvolleyball/competitions/beach-pro-tour/2026/futures/alanya-tur/",
                  "menTournaments": "9151", "womenTournaments": "9152", "destination": "Alanya, Turkey (M/W)"}
        payload = {"competitions": [record]}
        men = parse_beach_calendar(payload, self.sources["volleyball-fivb-beach-pro-tour-men"], 2026, 10)
        women = parse_beach_calendar(payload, self.sources["volleyball-fivb-beach-pro-tour-women"], 2026, 10)
        self.assertEqual((["9151"], ["9152"]), ([x["id"] for x in men], [x["id"] for x in women]))
        self.assertEqual("2026-10-18", men[0]["end"].isoformat())
        with self.assertRaises(ValueError):
            parse_beach_calendar({"competitions": [{**record, "url": "https://other.example/event"}]},
                                 self.sources["volleyball-fivb-beach-pro-tour-men"], 2026, 10)
        with self.assertRaises(ValueError):
            parse_beach_calendar(payload, {**self.sources["volleyball-fivb-beach-pro-tour-men"],
                                           "catalog_terms": ["Beach Pro Tour | Women"]}, 2026, 10)


if __name__ == "__main__":
    unittest.main()
