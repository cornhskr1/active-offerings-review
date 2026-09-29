import unittest

from scripts.romania_liga_i_fixture_adapter import parse_round


SOURCE = {
    "id": "uefa-soccer-romania-liga-i-men",
    "sport": "Soccer",
    "league": "Liga I | Men",
    "region": "Romania",
    "catalog_terms": ["Liga I | Men"],
    "endpoint": "https://lpf.ro/noutati/superliga-programul-etapei-a-11-a/6766",
}


def page():
    matches = [
        "Ora 18.00 Corvinul Hunedoara - FC Voluntari",
        "Ora 21.00 Sepsi OSK Sf. Gheorghe - Dinamo",
        "Ora 17.15 FC Botoșani - UTA Arad",
        "Ora 21.30 FCSB - Oțelul Galați",
        "Ora 18.00 FK Csikszereda Miercurea Ciuc - Universitatea Craiova",
        "Ora 21.00 Farul Constanța - Petrolul Ploiești",
        "Ora 18.00 FC Argeș - CFR 1907 Cluj",
        "Ora 21.00 Universitatea Cluj - FC Rapid",
    ]
    return ("<h1>SUPERLIGA – Programul etapei a 11-a</h1>"
            "<p>Comunicat de presă | 17.09.2026</p>"
            "<p>Partidele vor fi transmise în direct de PRIMA Sport și DIGI Sport.</p>"
            + "".join(f"<p>{x}</p>" for x in matches)).encode()


class RomaniaLigaIAdapterTests(unittest.TestCase):
    def test_exact_round_is_scoped_and_timed(self):
        events = parse_round(page(), SOURCE)
        self.assertEqual(8, len(events))
        self.assertEqual("FC Voluntari at Corvinul Hunedoara", events[0]["name"])
        self.assertEqual("2026-10-09T15:00:00Z", events[0]["start_time"])

    def test_changed_pairing_fails_closed(self):
        changed = page().replace(b"Corvinul Hunedoara - FC Voluntari",
                                 b"Corvinul Hunedoara - FCSB")
        with self.assertRaisesRegex(ValueError, "fixture changed"):
            parse_round(changed, SOURCE)

    def test_wrong_catalog_scope_fails_closed(self):
        bad = dict(SOURCE, league="Cupa României | Men")
        with self.assertRaisesRegex(ValueError, "catalog scope"):
            parse_round(page(), bad)


if __name__ == "__main__":
    unittest.main()
