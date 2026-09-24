import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IDENTITY_MODEL = "combined-approval-separate-competitions"


def soccer_combined_parents(season_map):
    soccer = next(sport for sport in season_map["sports"] if sport["sport"] == "Soccer")
    return [
        event
        for group in soccer.get("groups", [])
        for event in group.get("events", [])
        if "Men and Women" in event.get("catalog_event", "")
    ]


class CompetitionIdentityRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build from the current inputs without rewriting a tracked file in the
        # checkout. GitHub workflows must remain clean before their rebase.
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory)
            (isolated / "scripts").mkdir()
            (isolated / "data").mkdir()
            shutil.copy2(ROOT / "scripts" / "build_competition_identity_registry.py",
                         isolated / "scripts" / "build_competition_identity_registry.py")
            for name in ("global-schedule.json", "global-schedule-sources.json", "catalog-season-map.json", "catalog-live.json", "competition-alias-crosswalk.json"):
                shutil.copy2(ROOT / "data" / name, isolated / "data" / name)
            subprocess.run(
                [sys.executable, str(isolated / "scripts" / "build_competition_identity_registry.py"), "--audit"],
                check=True,
            )
            cls.registry = json.loads(
                (isolated / "data" / "competition-identity-registry.json").read_text(encoding="utf-8")
            )
            cls.alias_audit = json.loads(
                (isolated / "data" / "competition-alias-audit.json").read_text(encoding="utf-8")
            )
        cls.season_map = json.loads(
            (ROOT / "data" / "catalog-season-map.json").read_text(encoding="utf-8")
        )

    def test_registry_covers_catalog_mappings_and_observed_participants(self):
        expected = set()
        for sport in self.season_map["sports"]:
            for group in sport.get("groups", []):
                for event in group.get("events", []):
                    children = event.get("coverage_children") or []
                    if children:
                        expected.update((sport["sport"], child["label"]) for child in children)
                    elif event.get("catalog_event"):
                        expected.add((sport["sport"], event["catalog_event"]))
        actual = {(item["sport"], item["league"]) for item in self.registry["competitions"]}
        self.assertLessEqual(expected, actual)

        nfl = next(
            item
            for item in self.registry["competitions"]
            if item["sport"] == "Football" and item["league"] == "National Football League (NFL)"
        )
        self.assertIn("Buffalo Bills", nfl["participants"])
        self.assertIn("Las Vegas Raiders", nfl["participants"])
        self.assertTrue(self.registry["coverage_gaps"])

        afl = next(item for item in self.registry["competitions"] if item["sport"] == "Aussie Rules")
        self.assertEqual("Australian Football League (AFL)", afl["league"])
        self.assertIn({"name": "AFL", "source_id": "afl"}, afl["source_labels"])
        self.assertEqual(1, len([item for item in self.registry["competitions"] if item["sport"] == "Aussie Rules"]))

        self.assertIn(("Soccer", "Serie A | Men"), actual)
        self.assertIn(("Soccer", "Serie A | Women"), actual)
        self.assertNotIn(("Soccer", "Serie A | Men and Women"), actual)

    def test_every_catalog_sport_has_a_source_identity_audit(self):
        self.assertEqual([block["sport"] for block in self.season_map["sports"]],
                         [block["sport"] for block in self.alias_audit["sports"]])
        by_sport = {block["sport"]: block for block in self.alias_audit["sports"]}
        self.assertEqual([], by_sport["Aussie Rules"]["schedule_only_labels"])
        self.assertEqual([], by_sport["Soccer"]["schedule_only_labels"])
        self.assertTrue(any(row["source_id"] == "rugby-rfl" and len(row["catalog_targets"]) > 1
                            for row in by_sport["Rugby"]["shared_sources_for_review"]))

    def test_every_combined_soccer_approval_has_isolated_operational_identities(self):
        parents = soccer_combined_parents(self.season_map)

        self.assertEqual(22, len(parents))
        child_keys = []
        child_source_ids = []
        for parent in parents:
            self.assertEqual(IDENTITY_MODEL, parent.get("identity_model"))
            self.assertNotIn("source_id", parent)
            self.assertNotIn("source_ids", parent)
            children = parent.get("coverage_children") or []
            self.assertEqual(2, len(children))
            base = parent["catalog_event"].replace(" | Men and Women", "")
            self.assertEqual(
                {f"{base} | Men", f"{base} | Women"},
                {child["label"] for child in children},
            )
            self.assertTrue(all(child.get("key") and child.get("source_id") for child in children))
            child_keys.extend(child["key"] for child in children)
            child_source_ids.extend(child["source_id"] for child in children)

        self.assertEqual(len(child_keys), len(set(child_keys)))
        self.assertEqual(len(child_source_ids), len(set(child_source_ids)))

    def test_combined_soccer_parents_are_not_schedulable_registry_entries(self):
        soccer_leagues = {
            item["league"] for item in self.registry["competitions"] if item["sport"] == "Soccer"
        }
        for parent in soccer_combined_parents(self.season_map):
            self.assertNotIn(parent["catalog_event"], soccer_leagues)
            self.assertLessEqual(
                {child["label"] for child in parent["coverage_children"]},
                soccer_leagues,
            )

    def test_combined_soccer_children_point_to_exact_source_identities(self):
        configured = {}
        source_paths = [
            ROOT / "data" / "global-schedule-sources.json",
            *sorted((ROOT / "data").glob("soccer-*-sources.json")),
        ]
        for path in source_paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            for source in payload.get("sources", []):
                self.assertNotIn(source["id"], configured)
                configured[source["id"]] = source

        for parent in soccer_combined_parents(self.season_map):
            for child in parent["coverage_children"]:
                source = configured[child["source_id"]]
                self.assertEqual("Soccer", source["sport"])
                self.assertEqual(child["label"], source["league"])
                self.assertIn(parent["catalog_event"], source.get("catalog_terms", []))

    def test_reviewed_aliases_resolve_only_to_catalog_identities(self):
        competitions = {
            (item["sport"], item.get("identity_key")): item
            for item in self.registry["competitions"] if item.get("identity_key")
        }
        crosswalk = json.loads((ROOT / "data" / "competition-alias-crosswalk.json").read_text(encoding="utf-8"))
        for row in crosswalk["reviewed_aliases"]:
            with self.subTest(alias=row["alias"]):
                identity = (competitions[(row["sport"], row["identity_key"])] if row.get("identity_key") else
                            next(item for item in self.registry["competitions"] if item["sport"] == row["sport"] and item["league"] == row["catalog_identity"]))
                self.assertIn(row["alias"], [alias["name"] for alias in identity["aliases"]])
                if row.get("identity_key"):
                    self.assertIn(" | ", identity["league"])
        self.assertEqual(crosswalk["review_queue"], self.registry["alias_review_queue"])
        self.assertFalse(any(alias["name"] == "AFC Women's Champions League"
                             for item in self.registry["competitions"]
                             for alias in item.get("aliases", [])))
        womens_series = "FIBA 3x3 Women’s Series"
        self.assertTrue(any(row.get("observed_official_name") == womens_series
                            and row["catalog_identity"] == "FIBA 3x3 World Tour | Women"
                            for row in self.registry["alias_review_queue"]))
        self.assertFalse(any(alias["name"] == womens_series
                             for item in self.registry["competitions"]
                             for alias in item.get("aliases", [])))

    def test_baseball_draft_alias_does_not_claim_major_league(self):
        baseball = {item["league"]: item for item in self.registry["competitions"]
                    if item["sport"] == "Baseball"}
        self.assertIn("MLB Draft", [alias["name"] for alias in baseball["Draft"]["aliases"]])
        self.assertNotIn("MLB Draft", [alias["name"] for alias in baseball["Major League Baseball (MLB)"]["aliases"]])
        self.assertEqual("MLB", baseball["Major League Baseball (MLB)"]["aliases"][0]["name"])

    def test_bowling_tour_alias_does_not_claim_strike_derby_or_other_tours(self):
        bowling = {item["league"]: item for item in self.registry["competitions"]
                   if item["sport"] == "Bowling"}
        self.assertEqual({"PBA National Tour", "PBA Strike Derby"}, set(bowling))
        self.assertEqual(["PBA Tour"], [alias["name"] for alias in bowling["PBA National Tour"]["aliases"]])
        self.assertFalse(bowling["PBA Strike Derby"].get("aliases"))

    def test_boxing_authority_aliases_do_not_claim_bout_approval(self):
        boxing = {item["league"]: item for item in self.registry["competitions"]
                  if item["sport"] == "Boxing"}
        self.assertEqual(7, sum(len(item.get("aliases", [])) for item in boxing.values()))
        self.assertFalse(boxing["Bout-Level Approval Test"].get("aliases"))
        self.assertFalse(boxing["State Athletic Commissions"].get("aliases"))
        self.assertFalse(boxing["Association of Boxing Commissions and Combative Sports (ABCCS)"].get("aliases"))
        self.assertTrue(all(not item["events"] for item in boxing.values()))
        self.assertTrue(any(row.get("observed_official_name") == "Association of Boxing Commissions (ABC)"
                            for row in self.registry["alias_review_queue"]))

    def test_combat_sports_aliases_preserve_event_series_boundaries(self):
        combat = {item["league"]: item for item in self.registry["competitions"]
                  if item["sport"] == "Combat Sports"}
        self.assertEqual(6, sum(len(item.get("aliases", [])) for item in combat.values()))
        self.assertIn("ONE Fight Night", [alias["name"] for alias in combat["ONE Championship"]["aliases"]])
        self.assertNotIn("ONE Friday Fights", [alias["name"] for alias in combat["ONE Championship"]["aliases"]])
        self.assertFalse(combat["PFL Professional Bouts"].get("aliases"))
        self.assertFalse(combat["Combat Sports Approval Test"].get("aliases"))
        self.assertTrue(any(row.get("observed_official_name") == "ONE Friday Fights"
                            for row in self.registry["alias_review_queue"]))

    def test_cricket_aliases_preserve_gender_and_county_division(self):
        cricket = {item["league"]: item for item in self.registry["competitions"]
                   if item["sport"] == "Cricket"}
        self.assertEqual(7, len(cricket))
        self.assertEqual(11, sum(len(item.get("aliases", [])) for item in cricket.values()))
        self.assertIn("WBBL", [alias["name"] for alias in cricket["Women’s Big Bash League (WBBL) | Women"]["aliases"]])
        self.assertNotIn("WBBL", [alias["name"] for alias in cricket["Big Bash League (BBL) | Men"].get("aliases", [])])
        self.assertIn("Rothesay County Championship Division Two", [alias["name"] for alias in cricket["Rothesay County Championship Division 2 | Men"]["aliases"]])
        self.assertFalse(any(alias["name"] in {"Women's Ashes", "ICC Women's T20 World Cup", "Rothesay County Championship"}
                             for item in cricket.values() for alias in item.get("aliases", [])))

    def test_cycling_aliases_do_not_erase_womens_road_race_boundaries(self):
        cycling = {item["league"]: item for item in self.registry["competitions"]
                   if item["sport"] == "Cycling"}
        self.assertEqual(29, len(cycling))
        self.assertIn("Milano-Sanremo", [alias["name"] for alias in cycling["Milan-San Remo"]["aliases"]])
        self.assertIn("La Vuelta Ciclista a España", [alias["name"] for alias in cycling["Vuelta a España / La Vuelta"]["aliases"]])
        held = {row.get("observed_official_name") for row in self.registry["alias_review_queue"]
                if row["sport"] == "Cycling"}
        self.assertIn("Tour de France Femmes avec Zwift", held)
        self.assertIn("Ronde van Vlaanderen", held)
        self.assertFalse(any(alias["name"] in held for item in cycling.values()
                             for alias in item.get("aliases", [])))

    def test_darts_series_aliases_do_not_claim_separate_finals_or_junior_tours(self):
        darts = {item["league"]: item for item in self.registry["competitions"]
                 if item["sport"] == "Darts"}
        self.assertEqual(5, len(darts))
        self.assertEqual(5, sum(len(item.get("aliases", [])) for item in darts.values()))
        self.assertIn("CDC Main Tour", [alias["name"] for alias in darts["Main Tour Events"]["aliases"]])
        self.assertIn("Players Championship", [alias["name"] for alias in darts["PDC Players Championship"]["aliases"]])
        held = {row.get("observed_official_name") for row in self.registry["alias_review_queue"]
                if row["sport"] == "Darts"}
        self.assertIn("Ladbrokes Players Championship Finals", held)
        self.assertIn("CDC Next Generation – Junior Tour", held)
        self.assertFalse(any(alias["name"] in held for item in darts.values()
                             for alias in item.get("aliases", [])))

    def test_esports_aliases_keep_game_and_tournament_boundaries(self):
        esports = {item["league"]: item for item in self.registry["competitions"]
                  if item["sport"] == "Esports"}
        self.assertEqual(31, len(esports))
        self.assertIn("Six Invitational", [a["name"] for a in esports["Global Championships"].get("aliases", [])])
        self.assertIn("LCS Lock-In Tournament", [a["name"] for a in esports["LCS Lock-In"].get("aliases", [])])
        held = {row.get("observed_official_name") for row in self.registry["alias_review_queue"]
                if row["sport"] == "Esports"}
        self.assertIn("Worlds", held)
        self.assertIn("Esports World Cup", held)
        self.assertIn("EAL", held)
        self.assertFalse(any(a["name"] in held for item in esports.values()
                             for a in item.get("aliases", [])))

    def test_football_preseason_alias_does_not_collapse_into_nfl(self):
        football = {item["league"]: item for item in self.registry["competitions"]
                    if item["sport"] == "Football"}
        self.assertEqual(8, len(football))
        self.assertIn("Hall of Fame Game", [a["name"] for a in football["NFL Preseason"].get("aliases", [])])
        self.assertNotIn("NFL", [a["name"] for a in football["National Football League (NFL)"].get("aliases", [])])
        held = {item.get("observed_official_name") for item in self.registry["alias_review_queue"]
                if item["sport"] == "Football"}
        self.assertIn("NFL", held)
        self.assertIn("NAIA Football", held)

    def test_golf_aliases_preserve_tour_event_and_division_boundaries(self):
        golf = {item["league"]: item for item in self.registry["competitions"]
                if item["sport"] == "Golf"}
        aliases = {league: {alias["name"] for alias in item.get("aliases", [])}
                   for league, item in golf.items()}
        self.assertEqual(19, len(golf))
        self.assertEqual(15, sum(map(len, aliases.values())))
        self.assertIn("PGA Tour", aliases["Professional Golfers’ Association Tour (PGA Tour)"])
        self.assertIn("PGA Tour Champions", aliases["Professional Golfers’ Association Tour Champions (PGA Tour Champions)"])
        self.assertIn("The Open", aliases["The Open Championship"])
        self.assertIn("Women’s British Open", aliases["AIG Women’s Open"])
        held = {row.get("observed_official_name") for row in self.registry["alias_review_queue"]
                if row["sport"] == "Golf"}
        self.assertTrue({"PGA", "British Open", "Epson Tour", "KPMG Women’s PGA Championship",
                         "DP World Tour Championship"} <= held)
        self.assertFalse(any(alias in held for names in aliases.values() for alias in names))

    def test_ice_hockey_aliases_preserve_league_and_special_event_boundaries(self):
        hockey = {item["league"]: item for item in self.registry["competitions"]
                  if item["sport"] == "Ice Hockey"}
        aliases = {league: {alias["name"] for alias in item.get("aliases", [])}
                   for league, item in hockey.items()}
        self.assertEqual(14, len(hockey))
        self.assertEqual(10, sum(map(len, aliases.values())))
        self.assertIn("4 Nations Face-Off", aliases["Four Nations Face-Off"])
        self.assertIn("NHL All-Star Skills", aliases["NHL All-Star Skills Challenge"])
        self.assertIn("Honda NHL All-Star Game", aliases["NHL All-Star Game"])
        self.assertIn("NHL Entry Draft", aliases["NHL Draft"])
        self.assertFalse(aliases["National Hockey League (NHL)"])
        held = {row.get("observed_official_name") for row in self.registry["alias_review_queue"]
                if row["sport"] == "Ice Hockey"}
        self.assertTrue({"CHL", "NHL", "Extraliga", "NHL All-Star Weekend",
                         "American Hockey League (AHL)", "IIHF World Junior Championship"} <= held)
        self.assertFalse(any(alias in held for names in aliases.values() for alias in names))

    def test_lacrosse_aliases_preserve_field_box_and_championship_series_boundaries(self):
        lacrosse = {item["league"]: item for item in self.registry["competitions"]
                    if item["sport"] == "Lacrosse"}
        aliases = {league: {alias["name"] for alias in item.get("aliases", [])}
                   for league, item in lacrosse.items()}
        self.assertEqual(3, len(lacrosse))
        self.assertEqual(7, sum(map(len, aliases.values())))
        self.assertIn("Premier Lacrosse League", aliases["Premier Lacrosse League (PLL)"])
        self.assertIn("PLL Championship Series",
                      aliases["Premier Lacrosse League (PLL) Championship Series"])
        self.assertIn("Lexus PLL Championship Series",
                      aliases["Premier Lacrosse League (PLL) Championship Series"])
        self.assertIn("NLL", aliases["National Lacrosse League (NLL)"])
        held = {row.get("observed_official_name") for row in self.registry["alias_review_queue"]
                if row["sport"] == "Lacrosse"}
        self.assertTrue({"PLL", "PLL Championship", "Championship Series",
                         "Women’s Lacrosse League (WLL)", "WLL Championship Series",
                         "World Lacrosse Sixes Championships", "NLL Finals"} <= held)
        self.assertFalse(any(alias in held for names in aliases.values() for alias in names))

    def test_motorsports_aliases_preserve_series_race_and_class_boundaries(self):
        motorsports = {item["league"]: item for item in self.registry["competitions"]
                       if item["sport"] == "Motorsports"}
        aliases = {league: {alias["name"] for alias in item.get("aliases", [])}
                   for league, item in motorsports.items()}
        self.assertEqual(12, len(motorsports))
        self.assertEqual(22, sum(map(len, aliases.values())))
        self.assertIn("F1", aliases["Formula One (F1)"])
        self.assertIn("NTT INDYCAR SERIES", aliases["IndyCar Series"])
        self.assertIn("NASCAR Xfinity Series", aliases["NASCAR O’Reilly Auto Parts Series"])
        self.assertIn("V8 Supercars Championship", aliases["Repco Supercars Championship"])
        self.assertIn("Nitro Rallycross", aliases["Nitrocross - Formerly Nitro Rallycross / Nitro RX"])
        held = {row.get("observed_official_name") for row in self.registry["alias_review_queue"]
                if row["sport"] == "Motorsports"}
        self.assertTrue({"SRX", "INDYCAR", "Formula 1 Grand Prix", "E-Prix",
                         "Indianapolis 500", "Moto2", "Moto3", "Daytona 500",
                         "NHRA Pro Mod Drag Racing Series", "SCORE Baja 1000",
                         "Dunlop Super2 Series", "Nitro RX NEXT", "SCORE International"} <= held)
        self.assertFalse(any(alias in held for names in aliases.values() for alias in names))

    def test_ncaa_priority_aliases_preserve_division_and_gender_boundaries(self):
        ncaa_basketball = next(sport for sport in self.season_map["sports"]
                               if sport["sport"] == "NCAA Basketball")
        combined = [event for group in ncaa_basketball["groups"] for event in group["events"]
                    if event["catalog_event"].endswith(" | Men and Women")]
        self.assertEqual(3, len(combined))
        self.assertTrue(all(event.get("identity_model") == IDENTITY_MODEL for event in combined))
        self.assertTrue(all("source_id" not in event and "source_ids" not in event for event in combined))
        self.assertTrue(all({child["label"].rsplit(" | ", 1)[1]
                             for child in event["coverage_children"]} == {"Men", "Women"}
                            for event in combined))

        basketball = {item["identity_key"]: item for item in self.registry["competitions"]
                      if item["sport"] == "NCAA Basketball" and item.get("identity_key")}
        mens_aliases = {alias["name"] for alias in basketball["ncaa-basketball-di-men"].get("aliases", [])}
        womens_aliases = {alias["name"] for alias in basketball["ncaa-basketball-di-women"].get("aliases", [])}
        self.assertTrue({"NCAAB", "NCAAM", "NCAAMB", "NCAA Men’s Basketball"} <= mens_aliases)
        self.assertTrue({"NCAAW", "NCAAWB", "NCAA Women’s Basketball"} <= womens_aliases)
        self.assertTrue(mens_aliases.isdisjoint(womens_aliases))
        self.assertTrue(all(alias.get("scope_note") for alias in basketball["ncaa-basketball-di-men"]["aliases"]
                            if alias["name_type"] != "official"))

        football = {item["league"]: {alias["name"] for alias in item.get("aliases", [])}
                    for item in self.registry["competitions"] if item["sport"] == "NCAA Football"}
        self.assertIn("NCAA FBS", football["Division I Football Bowl Subdivision (FBS)"])
        self.assertIn("NCAA FCS", football["Division I Football Championship Subdivision (FCS)"])
        self.assertIn("NCAA Division II Football", football["Division II Football"])

        held = {row.get("observed_official_name") for row in self.registry["alias_review_queue"]
                if row["sport"].startswith("NCAA")}
        self.assertTrue({"NCAAF", "NCAAFB", "College Football", "College Basketball",
                         "NCAA Basketball", "NCAABB", "College Baseball", "Volleyball",
                         "College Volleyball", "Softball", "College Softball"} <= held)
        self.assertFalse(any(alias["name"] in held for item in self.registry["competitions"]
                             if item["sport"].startswith("NCAA")
                             for alias in item.get("aliases", [])))

    def test_rodeo_aliases_preserve_series_organizer_and_final_boundaries(self):
        rodeo = {item["league"]: {alias["name"] for alias in item.get("aliases", [])}
                 for item in self.registry["competitions"] if item["sport"] == "Rodeo"}
        self.assertEqual(5, len(rodeo))
        self.assertEqual(11, sum(map(len, rodeo.values())))
        self.assertIn("PBR Unleash The Beast", rodeo["Unleash The Beast Series"])
        self.assertIn("PRCA Pro Rodeo Tour", rodeo["Pro Rodeo Tour"])
        self.assertIn("NFR Open", rodeo["National Circuit Finals Rodeo"])
        self.assertIn("PRCA Xtreme Broncs Finals", rodeo["Xtreme Broncs Finals"])
        self.assertIn("Pendleton Whisky Xtreme Bulls Tour Finale", rodeo["Xtreme Bulls Finale"])
        held = {row.get("observed_official_name") for row in self.registry["alias_review_queue"]
                if row["sport"] == "Rodeo"}
        self.assertTrue({"PBR", "Professional Bull Riders", "UTB", "PBR World Finals",
                         "PBR Team Series", "PBR Ram Challenger Series",
                         "Monster Energy Team Challenge", "PRCA", "PRORODEO",
                         "ProRodeo Playoff Series", "NFR", "National Finals Rodeo",
                         "Xtreme Broncs", "Xtreme Bulls", "International Finals Rodeo (IFR)",
                         "Women’s Rodeo World Championship", "The American Rodeo"} <= held)
        self.assertFalse(any(alias in held for aliases in rodeo.values() for alias in aliases))

    def test_alias_collision_with_other_division_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory)
            (isolated / "scripts").mkdir()
            (isolated / "data").mkdir()
            shutil.copy2(ROOT / "scripts" / "build_competition_identity_registry.py",
                         isolated / "scripts" / "build_competition_identity_registry.py")
            for name in ("global-schedule.json", "global-schedule-sources.json", "catalog-season-map.json", "catalog-live.json"):
                shutil.copy2(ROOT / "data" / name, isolated / "data" / name)
            crosswalk = json.loads((ROOT / "data" / "competition-alias-crosswalk.json").read_text(encoding="utf-8"))
            crosswalk["reviewed_aliases"][0]["alias"] = "AFC Asian Cup | Men"
            (isolated / "data" / "competition-alias-crosswalk.json").write_text(json.dumps(crosswalk))
            result = subprocess.run(
                [sys.executable, str(isolated / "scripts" / "build_competition_identity_registry.py")],
                capture_output=True, text=True,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("Alias collides with another competition", result.stderr)


if __name__ == "__main__":
    unittest.main()
