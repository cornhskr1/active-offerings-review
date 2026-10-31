import unittest

from scripts.rfef_supercopa_fixture_adapter import parse_semifinals


SOURCE = {
    "id": "uefa-soccer-spain-supercopa-de-espa-a-men",
    "sport": "Soccer",
    "league": "Supercopa de España | Men",
    "region": "Spain",
    "catalog_terms": ["Supercopa de España | Men"],
    "endpoint": "https://rfef.es/es/noticias/definida-la-hoja-de-ruta-de-la-supercopa-2027-que-se-celebrara-en-estambul",
}


def page():
    from pathlib import Path
    return (Path(__file__).parent / 'fixtures/rfef_semifinals_table_2027.html').read_bytes()


class RfefSupercopaAdapterTests(unittest.TestCase):
    def test_exact_semifinals_are_scoped_and_timed(self):
        events = parse_semifinals(page(), SOURCE)
        self.assertEqual(2, len(events))
        self.assertEqual("Club Atlético de Madrid at FC Barcelona", events[0]["name"])
        self.assertEqual("2027-02-02T19:00:00Z", events[0]["start_time"])

    def test_changed_pairing_fails_closed(self):
        changed = page().replace(b"Club Atl\xc3\xa9tico de Madrid", b"Real Madrid CF", 1)
        with self.assertRaisesRegex(ValueError, "semifinal changed"):
            parse_semifinals(changed, SOURCE)

    def test_wrong_catalog_scope_fails_closed(self):
        bad = dict(SOURCE, league="Supercopa de España Femenina | Women")
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_semifinals(page(), bad)

    def test_each_table_date_time_zone_pairing_and_unknown_final_remain_bound(self):
        for old,new in [(b'02/02/2027',b'03/02/2027'),(b'20:00',b'21:00'),
                        ('peninsular español'.encode(),b'UTC'),(b'Por determinar',b'FC Barcelona')]:
            with self.subTest(change=new), self.assertRaises(ValueError):
                self.assertIn(old,page())
                parse_semifinals(page().replace(old,new,1),SOURCE)

    def test_missing_table_cannot_use_unrelated_prose_to_authorize_fixtures(self):
        with self.assertRaisesRegex(ValueError,'table'):
            parse_semifinals(b'<h1>Supercopa de Espa\xc3\xb1a 2027 en Estambul</h1>',SOURCE)


if __name__ == "__main__":
    unittest.main()
