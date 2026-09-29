import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from nzr_npc_fixture_adapter import _row, publisher_pdf_url


SOURCE = {
    "catalog_terms": ["National Provincial Championship (NPC) | Men"],
    "publisher_page": "https://www.provincial.rugby/npc/fixtures-and-results",
    "endpoint": "https://www.provincial.rugby/assets/NPC-SCHEDULE_Package-2026.pdf",
}


class NZRNPCFixtureAdapterTests(unittest.TestCase):
    def test_publisher_link_must_still_point_to_the_scoped_pdf(self):
        page = b'<a href="/assets/NPC-SCHEDULE_Package-2026.pdf">2026 schedule</a>'
        self.assertEqual(publisher_pdf_url(page, SOURCE), SOURCE["endpoint"])
        with self.assertRaisesRegex(ValueError, "link changed"):
            publisher_pdf_url(b'<a href="/assets/NPC-SCHEDULE_Package-2027.pdf">schedule</a>', SOURCE)

    def test_round_rejects_unexpected_club(self):
        marker = {"top": 500}
        words = [{"x0": 310, "top": 505, "text": "OTAGO"},
                 {"x0": 640, "top": 505, "text": "YOUTH"}]
        with self.assertRaisesRegex(ValueError, "unknown"):
            _row(words, marker)


if __name__ == "__main__":
    unittest.main()
