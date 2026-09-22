from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


class DashboardScopeTests(unittest.TestCase):
    def test_catalog_and_coverage_are_one_staff_view(self):
        self.assertIn("Approved Catalog &amp; Coverage", HTML)
        self.assertIn('id="catalogHealth"', HTML)
        self.assertIn("Data Health Summary", HTML)
        self.assertIn("catalogEntryHealthHtml", HTML)
        self.assertIn("Last checked", HTML)
        self.assertIn("Official schedule", HTML)
        self.assertIn("Schedule status, last checked time, and the official schedule now appear inside the matching catalog entry", HTML)
        self.assertNotIn("catalog-health-list", HTML)
        self.assertNotIn('data-panel="coverage"', HTML)
        self.assertNotIn('<section class="panel" id="coverage">', HTML)

    def test_ncaa_detail_tabs_are_not_visible(self):
        self.assertNotIn('data-panel="ncaa"', HTML)
        self.assertNotIn('data-panel="basketball"', HTML)
        self.assertNotIn('<section class="panel" id="ncaa">', HTML)
        self.assertNotIn('<section class="panel" id="basketball">', HTML)

    def test_nonwagered_ncaa_sports_are_filtered_before_rendering(self):
        self.assertIn("function isNonWageredNcaaSport(item)", HTML)
        self.assertIn("sport==='golf'", HTML)
        self.assertIn("sport==='soccer'", HTML)
        self.assertIn("const events=visibleCollegeEvents();", HTML)
        self.assertIn("!isNonWageredNcaaSport(e)", HTML)
        self.assertIn("!isNonWageredNcaaSport(c)", HTML)

    def test_professional_tennis_is_not_generically_suppressed(self):
        self.assertIn("Boolean(item?.school)", HTML)
        self.assertIn("\\bncaa\\b|\\bcollege\\b|\\bcollegiate\\b", HTML)

    def test_collegiate_filter_copy_names_all_hidden_sports(self):
        self.assertIn("Collegiate golf, soccer, tennis, and swimming/diving remain in the source data", HTML)

    def test_nebraska_collegiate_events_are_grouped_by_date(self):
        self.assertIn('class="college-day"', HTML)
        self.assertIn("Object.entries(byDate)", HTML)
        self.assertIn("timeValue(a.time)-timeValue(b.time)", HTML)


if __name__ == "__main__":
    unittest.main()
