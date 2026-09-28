"""The men's final must not become approval for similarly named Canadian cups."""

import json
import unittest
from pathlib import Path

from scripts.canada_championship_final import parse_final


DATA = Path(__file__).resolve().parents[1] / "data"
SOURCE = next(s for s in json.loads((DATA / "soccer-concacaf-domestic-sources.json").read_text())["sources"]
              if s["id"] == "concacaf-soccer-canada-canadian-championship-men")
PAGE = b'''<html><head><meta charset="utf-8"></head><body><main>2026 TELUS Canadian Championship. The Men\xe2\x80\x99s 2026 TELUS Canadian Championship.
<div id="match-6384" class="match-card upcoming-match">
 <div class="match-card-header"><a href="https://canadasoccer.com/match/6384/">Match Info</a></div>
 <p class="away-team"><span class="team-name">CF Montr\xc3\xa9al</span></p>
 <p class="visitor-team"><span class="team-name">Forge FC Hamilton</span></p>
 <p class="match-date">21 Oct 2026</p><p class="match-time">19:00 EDT</p>
 <div class="match-card-footer">Stade Saputo, Montr\xc3\xa9al, Qu\xc3\xa9bec FINAL / FINALE (Local 19h00)</div>
</div></main></body></html>'''


class CanadaChampionshipScopeTests(unittest.TestCase):
    def test_exact_final_and_competition_gate(self):
        event = parse_final(PAGE, SOURCE)
        self.assertEqual("2026-10-21T23:00:00Z", event["start_time"])
        self.assertEqual("Canadian Championship | Men", event["league"])
        for altered in (PAGE.replace(b"The Men\xe2\x80\x99s", b"The Women\xe2\x80\x99s"),
                        PAGE.replace(b"match/6384/", b"match/6385/")):
            with self.assertRaises(ValueError):
                parse_final(altered, SOURCE)

    def test_other_approved_labels_remain_held(self):
        rows = {r["identity_key"]: r for r in json.loads((DATA / "priority2-coverage-inventory.json").read_text())["identities"]}
        self.assertEqual("ADAPTER_CONFIGURED", rows["soccer-canada-canadian-championship-men"]["coverage_state"])
        for key in ("soccer-canada-canadian-cup-men", "soccer-canada-voyager-cup-women"):
            self.assertEqual("ADAPTER_GAP", rows[key]["coverage_state"])
            self.assertEqual("DOCUMENTED_HOLD", rows[key]["season_state"])


if __name__ == "__main__":
    unittest.main()
