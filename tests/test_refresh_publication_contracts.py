"""Offline writer regressions for the protected data publication boundary."""
import ast
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from scripts.snapshot_semantic_guards import validate_change
from scripts.tennis_publisher_holds import mark_permission_metadata, paused_snapshot

ROOT = Path(__file__).resolve().parents[1]
OLD = "2026-01-01T00:00:00+00:00"


def script_tree(name):
    tree = ast.parse((ROOT / "scripts" / name).read_text())
    # Browser collection is mocked; no Playwright installation or network needed.
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom) and node.module == "playwright.sync_api")]
    return tree


def execute(nodes, name, namespace):
    with patch.object(sys, "path", [str(ROOT / "scripts"), *sys.path]), redirect_stdout(io.StringIO()):
        exec(compile(ast.Module(body=nodes, type_ignores=[]), name, "exec"), namespace)


def run_writer(name, data):
    pw = MagicMock()
    pw.chromium.launch.return_value.new_page.return_value.goto.side_effect = AssertionError("Unexpected network request")
    manager = MagicMock()
    manager.__enter__.return_value = pw
    namespace = {"__file__": str(data.parent / "scripts" / name),
                 "sync_playwright": lambda: manager}
    try:
        execute(script_tree(name).body, name, namespace)
    except SystemExit as error:
        if error.code not in (0, None):
            raise
    pw.chromium.launch.return_value.new_page.return_value.goto.assert_not_called()


def run_intelligence_publication(data, *, invalid_field=False):
    """Replay saved collection results through the real assembly and write path."""
    name = "refresh_tennis_intelligence.py"
    tree = script_tree(name)
    split = next(i for i, node in enumerate(tree.body) if isinstance(node, ast.With))
    namespace = {"__file__": str(data.parent / "scripts" / name)}
    execute(tree.body[:split], name, namespace)
    saved = namespace["saved_intelligence"]
    tournaments = [deepcopy(row) for row in saved.get("tournaments", [])
                   if not row.get("collection_paused")]
    if invalid_field:
        tournaments.append({"id": "bad", "tour_id": "atp", "tour": "ATP Tour", "gender": "MEN",
                            "tournament": "Invalid field", "start_date": "2026-01-01",
                            "end_date": "2026-01-02", "status_color": "GREEN", "participant_count": 0})
    namespace.update(tournaments=tournaments, health=deepcopy(saved["source_health"]),
                     persistent_age_cache=namespace["load_age_cache"](),
                     durable_records=namespace["saved_records"], junior_candidates=namespace["saved_candidates"])
    execute(tree.body[split + 1:], name, namespace)


class RefreshPublicationContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "data"
        self.data.mkdir()

    def write(self, name, value):
        (self.data / name).write_text(json.dumps(value, indent=2) + "\n")

    def read(self, name):
        return json.loads((self.data / name).read_text())

    def tennis_inputs(self):
        held = mark_permission_metadata({}, OLD)["publisher_permission_holds"]
        held.append({"publisher": "USTA", "collection_paused": True, "hold_checked_at": OLD})
        docs = {
            "tennis-intelligence.json": {"schema_version": 6, "tournaments": [], "source_health": {
                "itf_men": {"permission_required": True, "error": "held"},
                "itf_women": {"permission_required": True, "error": "held"}, "itf_juniors": {}}},
            "tennis-schedule.json": {"schema_version": 1, "tournaments": []},
            "tennis-u18-registry.json": {"schema_version": 2, "records": [], "age_evidence_review": {"id": "review"}},
            "tennis-exceptions.json": {"schema_version": 1, "exceptions": []},
            "tennis-age-cache.json": {"schema_version": 1, "records": {
                "saved player": {"name": "Saved Player", "collection_paused": True, "last_verified": OLD}},
                "age_evidence_review": {"id": "review"}},
        }
        for name, doc in docs.items():
            doc.update(generated_at=OLD, publisher_permission_holds=deepcopy(held))
            self.write(name, doc)
        return docs

    def test_intelligence_outputs_preserve_all_holds_across_repeated_runs(self):
        originals = self.tennis_inputs()
        for _ in range(2):
            run_intelligence_publication(self.data)
            for name, old in originals.items():
                with self.subTest(output=name):
                    current = self.read(name)
                    self.assertEqual(current["publisher_permission_holds"], old["publisher_permission_holds"])
                    validate_change(old, current)
            self.assertEqual(self.read("tennis-age-cache.json")["records"], originals["tennis-age-cache.json"]["records"])

    def test_intelligence_quality_failure_does_not_publish(self):
        self.tennis_inputs()
        before = {p.name: p.read_bytes() for p in self.data.iterdir()}
        with self.assertRaises(SystemExit) as error:
            run_intelligence_publication(self.data, invalid_field=True)
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.data.iterdir()})

    def test_itf_calendar_hold_survives_month_rollover(self):
        name = "refresh_tennis_intelligence.py"
        loop = next(node for node in ast.walk(script_tree(name)) if isinstance(node, ast.For)
                    and isinstance(node.target, ast.Tuple)
                    and [getattr(item, "id", None) for item in node.target.elts] == ["url", "tid", "tour", "gender", "key"])
        urls = {key: f"https://www.itftennis.com/{key}?startdate=2026-01" for key in ("itf_men", "itf_women")}
        old = {key: paused_snapshot(url) for key, url in urls.items()}
        namespace = {"ITF_MEN": urls["itf_men"].replace("2026-01", "2026-02"),
                     "ITF_WOMEN": urls["itf_women"].replace("2026-01", "2026-02"),
                     "saved_intelligence": {"source_health": old}, "health": {},
                     "paused_snapshot": paused_snapshot}
        execute([loop], name, namespace)
        self.assertEqual(namespace["health"], old)
        validate_change(old, namespace["health"])
        namespace["health"]["itf_men"]["url"] = "changed"
        self.assertEqual(old["itf_men"]["url"], urls["itf_men"])

    def test_age_scan_keeps_dictionary_schema_and_saved_hold_evidence(self):
        old = self.tennis_inputs()["tennis-age-cache.json"]
        self.write("tennis-exceptions.json", {"exceptions": [
            {"name": "New Held Player", "tour": "ITF Men", "profile_url": "https://www.itftennis.com/en/players/fixture"}]})
        for _ in range(2):
            run_writer("refresh_tennis_age_scan.py", self.data)
            current = self.read("tennis-age-cache.json")
            self.assertEqual(current["schema_version"], 1)
            self.assertIsInstance(current["records"], dict)
            self.assertEqual(current["publisher_permission_holds"], old["publisher_permission_holds"])
            self.assertEqual(current["records"]["saved player"], old["records"]["saved player"])
            self.assertEqual(current["processed"], 0)
            self.assertEqual(current["permission_held"], 1)
            validate_change(old, current)
            old = current

    def test_basketball_preserves_paused_bytes_and_allows_derived_queue(self):
        old = {"schema_version": 1, "generated_at": OLD, "collection_paused": True,
               "records": [{"player_id": "saved-only", "athlete": "Saved Player", "team": "College",
                            "gender": "Men", "status": "UNRESOLVED", "last_seen": OLD}]}
        self.write("ncaa-basketball-age-cache.json", old)
        self.write("ncaa-basketball-rosters.json", {"teams": []})
        path = self.data / "ncaa-basketball-age-cache.json"
        before = path.read_bytes()
        run_writer("refresh_ncaa_basketball_age_cache.py", self.data)
        self.assertEqual(path.read_bytes(), before)
        validate_change(old, self.read(path.name))
        run_writer("build_ncaa_basketball_age_research_queue.py", self.data)
        self.assertEqual(self.read("ncaa-basketball-age-research-queue.json")["queue"][0]["player_id"], "saved-only")

    def test_hold_metadata_does_not_alias_or_clear_prior_records(self):
        old = mark_permission_metadata({}, OLD)
        expected = deepcopy(old)
        with patch("scripts.tennis_publisher_holds.permission_hold_reason", return_value=None):
            current = mark_permission_metadata({}, "2026-02-01", old)
        self.assertEqual(current, expected)
        current["publisher_permission_holds"][0]["tour_ids"].append("other")
        self.assertEqual(old, expected)


if __name__ == "__main__":
    unittest.main()
