import datetime
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import sfl_fixture_adapter as adapter


SOURCE = {
    "id": "uefa-soccer-switzerland-swiss-challenge-league-men",
    "sport": "Soccer",
    "league": "Swiss Challenge League | Men",
    "region": "Switzerland",
    "endpoint": (
        "https://origins-sportlab-payload-s3.origins-digital.com/sfl/images/"
        "dieci_Challenge_League_Spielplan-Calendrier_2026-29.pdf"
    ),
    "publisher_page": "https://sfl.ch/de/anspielzeiten",
    "catalog_terms": ["Swiss Challenge League | Men"],
}


class _Page:
    def __init__(self, raw, layout):
        self.raw = raw
        self.layout = layout

    def extract_text(self, extraction_mode=None):
        return self.layout if extraction_mode == "layout" else self.raw


class _Reader:
    def __init__(self, raw, layout):
        self.pages = [_Page(raw, layout)]


def _published_pdf(rounds=18, revision="23.10.2026", youth=False):
    raw = (
        f"SPIELPLAN/CALENDRIER / VERSION {revision}\n"
        "Spielplan / Calendrier, Saison 2026/27\n"
        "dieci Challenge League"
    )
    lines = []
    first = datetime.date(2026, 7, 24)
    for number in range(1, rounds + 1):
        day = first + datetime.timedelta(days=7 * (number - 1))
        for match in range(5):
            home = f"Club {2 * match + 1}"
            away = "U18 Academy" if youth and number == rounds and match == 4 else f"Club {2 * match + 2}"
            lines.append(
                f"{day:%d.%m.%Y} {day:%a} 19:30 {home} - {away}"
            )
    return _Reader(raw, "\n".join(lines))


class SFLFixtureAdapterTests(unittest.TestCase):
    def test_directory_must_uniquely_link_the_exact_current_pdf(self):
        page = f'<a href="{SOURCE["endpoint"]}">Spielplan dieci Challenge League 2026/27</a>'.encode()
        self.assertEqual(SOURCE["endpoint"], adapter.publisher_pdf_url(page, SOURCE))

        stale = page.replace(b"2026-29.pdf", b"2026-27")
        with self.assertRaisesRegex(ValueError, "current PDF link changed"):
            adapter.publisher_pdf_url(stale, SOURCE)

        competing = page + page.replace(b'2026-29.pdf"', b'2026-29.pdf?download=1"')
        with self.assertRaisesRegex(ValueError, "current PDF link changed"):
            adapter.publisher_pdf_url(competing, SOURCE)

    def test_revised_pdf_requires_all_eighteen_complete_rounds(self):
        with patch.object(adapter, "PdfReader", return_value=_published_pdf()):
            events, rounds, pairings = adapter.parse_pdf(
                b"%PDF-test",
                SOURCE,
                datetime.date(2026, 10, 30),
                datetime.date(2026, 11, 6),
            )

        self.assertEqual((18, 90), (rounds, pairings))
        self.assertEqual(10, len(events))
        self.assertEqual(
            {"SFL published 2026/27 round 15", "SFL published 2026/27 round 16"},
            {event["status_detail"] for event in events},
        )
        self.assertTrue(all(event["source_endpoint"] == SOURCE["publisher_page"] for event in events))

    def test_revision_round_count_and_senior_scope_fail_closed(self):
        cases = (
            (_published_pdf(revision="07.09.2026"), "edition or revision changed"),
            (_published_pdf(rounds=17), "fixture count changed"),
            (_published_pdf(youth=True), "clubs or eligibility changed"),
        )
        for reader, message in cases:
            with self.subTest(message=message), patch.object(adapter, "PdfReader", return_value=reader):
                with self.assertRaisesRegex(ValueError, message):
                    adapter.parse_pdf(
                        b"%PDF-test",
                        SOURCE,
                        datetime.date(2026, 10, 30),
                        datetime.date(2026, 11, 6),
                    )


if __name__ == "__main__":
    unittest.main()
