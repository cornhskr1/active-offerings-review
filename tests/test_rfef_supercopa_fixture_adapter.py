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
    return """<html><body>
    <h1>Supercopa de España 2027</h1>
    <p>Estambul acogerá la competición.</p>
    <p>FC Barcelona - Club Atlético de Madrid · 02/02/2027 · 20:00 · Chobani Stadium Fenerbahçe Şükrü Saracoğlu Sports Complex</p>
    <p>Real Sociedad de Fútbol - Real Madrid CF · 03/02/2027 · 20:00 · Tüpraş Stadium</p>
    <p>La final tendrá lugar el 6 de febrero de 2027.</p>
    </body></html>""".encode()


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


if __name__ == "__main__":
    unittest.main()
