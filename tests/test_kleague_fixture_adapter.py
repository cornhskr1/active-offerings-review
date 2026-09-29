import unittest

from scripts.kleague_fixture_adapter import parse_next_fixture


K1 = {
    "id": "soccer-afc-korea-k-league-1-men",
    "sport": "Soccer",
    "league": "K League 1 | Men",
    "region": "Korea",
    "catalog_terms": ["K League 1 | Men"],
    "endpoint": "https://www.kleague.com/news_view.do?category=notice&orderBy=seq&page=1&seq=96195&viewOption=list",
}
K2 = {
    "id": "soccer-afc-korea-k-league-2-men",
    "sport": "Soccer",
    "league": "K League 2 | Men",
    "region": "Korea",
    "catalog_terms": ["K League 2 | Men"],
    "endpoint": "https://www.kleague.com/news_view.do?orderBy=seq&page=1&seq=96401&viewOption=album",
}


def k1_page():
    return """<html><body>
    하나은행 K 리그 1 2026
    기존 10 월 17 일(토) 오후 2 시 예정된 32 라운드 서울 대 김천 경기를
    10 월 18 일(일) 오후 4 시 30 분으로 변경했다.
    </body></html>""".encode()


def k2_page():
    return """<html><body>
    김포 FC는 10 월 9 일 오후 4 시 30 분, 서울이랜드 FC 를 홈으로 불러들여
    하나은행 K 리그 2 2026 28 라운드 경기를 치른다.
    </body></html>""".encode()


class KLeagueFixtureAdapterTests(unittest.TestCase):
    def test_k1_changed_fixture_is_exact_and_timed(self):
        events = parse_next_fixture(k1_page(), K1)
        self.assertEqual(1, len(events))
        self.assertEqual("Gimcheon Sangmu at FC Seoul", events[0]["name"])
        self.assertEqual("2026-10-18T07:30:00Z", events[0]["start_time"])
        self.assertEqual("ROUND 32", events[0]["season_stage"])

    def test_k2_next_fixture_is_exact_and_timed(self):
        events = parse_next_fixture(k2_page(), K2)
        self.assertEqual(1, len(events))
        self.assertEqual("Seoul E-Land FC at Gimpo FC", events[0]["name"])
        self.assertEqual("2026-10-09T07:30:00Z", events[0]["start_time"])
        self.assertEqual("ROUND 28", events[0]["season_stage"])

    def test_changed_publication_fails_closed(self):
        changed = k1_page().replace("오후 4 시 30 분".encode(), "오후 5 시".encode())
        with self.assertRaisesRegex(ValueError, "publication changed"):
            parse_next_fixture(changed, K1)

    def test_wrong_scope_fails_closed(self):
        bad = dict(K2, league="Korean FA Cup | Men")
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_next_fixture(k2_page(), bad)


if __name__ == "__main__":
    unittest.main()
