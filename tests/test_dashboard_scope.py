from pathlib import Path
import subprocess
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
        self.assertIn("Schedule status, last checked time, and the official schedule appear inside the matching catalog entry", HTML)
        self.assertNotIn("catalog-health-list", HTML)
        self.assertNotIn('data-panel="coverage"', HTML)
        self.assertNotIn('<section class="panel" id="coverage">', HTML)

    def test_catalog_health_distinguishes_source_counts_from_identity_progress(self):
        self.assertIn("coverage:'data/priority2-coverage-inventory.json'", HTML)
        self.assertIn("Priority 2 identity coverage:", HTML)
        self.assertIn("Connected sources", HTML)
        self.assertIn("Sources need setup", HTML)
        self.assertIn("buttons count schedule source records", HTML)

    def test_catalog_coverage_uses_exact_source_identity(self):
        self.assertIn("if(ids.size)return ids.has(source.id);", HTML)
        self.assertIn("sourceTerms.some(term=>term===label)", HTML)
        self.assertNotIn("term.includes(label)||label.includes(term)", HTML)

    def test_staff_schedule_links_never_open_machine_endpoints(self):
        self.assertIn("source.official_schedule_url||source.public_url", HTML)
        self.assertNotIn("official||source.endpoint", HTML)

    def test_combined_catalog_approvals_render_separate_coverage_children(self):
        self.assertIn("function renderCoverageChildren(event,sport)", HTML)
        self.assertIn("Catalog approval — coverage tracked separately below", HTML)
        self.assertIn("event?.coverage_children", HTML)

    def test_ncaa_detail_tabs_are_not_visible(self):
        self.assertNotIn('data-panel="ncaa"', HTML)
        self.assertNotIn('data-panel="basketball"', HTML)
        self.assertNotIn('<section class="panel" id="ncaa">', HTML)
        self.assertNotIn('<section class="panel" id="basketball">', HTML)

    def test_nonwagered_ncaa_sports_are_filtered_before_rendering(self):
        start = HTML.index("function normCollegeSport(")
        end = HTML.index("\nfunction collegeAliases(", start)
        script = "const assert=require('node:assert/strict');\n" + HTML[start:end] + """
for(const sport of ['Baseball','Basketball','Football','Soccer','Softball','Volleyball','Wrestling']){
  assert.equal(isNonWageredNcaaSport({sport:`NCAA ${sport}`}),false,sport);
  assert.equal(isNonWageredNcaaSport({sport:`Women's ${sport}`,school:'Nebraska'}),false,sport);
}
for(const sport of ['Beach Volleyball','Field Hockey','Golf','Ice Hockey','Lacrosse','Swimming','Tennis','Track and Field','Water Polo']){
  assert.equal(isNonWageredNcaaSport({sport:`NCAA ${sport}`}),true,sport);
}
assert.equal(isNonWageredNcaaSport({sport:'Soccer',league:'NCAA Division I Soccer | Women'}),false);
assert.equal(isNonWageredNcaaSport({sport:'Tennis',league:'ATP Tour'}),false);
assert.equal(isNonWageredNcaaSport({sport:'Tennis',league:'NCAA Division I Tennis | Men'}),true);
"""
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)
        self.assertIn("const events=visibleCollegeEvents();", HTML)
        self.assertIn("!isNonWageredNcaaSport(e)", HTML)
        self.assertIn("!isNonWageredNcaaSport(c)", HTML)
        self.assertIn("if(isNonWageredNcaaSport(source))return false;", HTML)
        self.assertIn("!isNonWageredNcaaSport(gap)", HTML)

    def test_collegiate_filter_copy_names_sports_in_review(self):
        self.assertIn("men's and women's soccer, softball, volleyball, and wrestling", HTML)

    def test_nebraska_collegiate_events_are_grouped_by_date(self):
        self.assertIn('class="college-day"', HTML)
        self.assertIn("Object.entries(byDate)", HTML)
        self.assertIn("timeValue(a.time)-timeValue(b.time)", HTML)

    def test_restriction_watch_is_grouped_by_sport(self):
        self.assertIn('id="restrictionSummary"', HTML)
        self.assertIn('id="restrictionGroups"', HTML)
        self.assertIn('class="restriction-card ${c}"', HTML)
        self.assertIn("groups[x.sport||x.catalog_section||'Other']", HTML)
        self.assertNotIn('id="restrictionRows"', HTML)

    def test_known_u18_is_grouped_by_sport_and_league(self):
        self.assertIn('id="u18Groups"', HTML)
        self.assertIn('class="registry-league"', HTML)
        self.assertIn('class="registry-athlete"', HTML)
        self.assertIn("league=x.league||'League not specified'", HTML)
        self.assertNotIn('id="u18Rows"', HTML)


if __name__ == "__main__":
    unittest.main()
