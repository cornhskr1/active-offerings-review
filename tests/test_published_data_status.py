"""Loading a public file must not certify review completion or freshness."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


def source(name):
    start = HTML.index(f"function {name}(")
    if HTML[start - 6:start] == "async ":
        start -= 6
    end = HTML.find("\nfunction ", start + 1)
    async_end = HTML.find("\nasync function ", start + 1)
    ends = [value for value in (end, async_end) if value >= 0]
    return HTML[start:min(ends) if ends else None]


class PublishedDataStatusTests(unittest.TestCase):
    def test_retired_publisher_banner_is_removed(self):
        self.assertNotIn('id="publisherCollectionHold"', HTML)

    def run_js(self, setup, body, names):
        script = "const assert=require('node:assert/strict');\nconsole.warn=()=>{};\n" + setup
        script += "\n" + source("feedCollectionPaused") + "\n" + "\n".join(source(name) for name in names)
        script += "\n" + body
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_loaded_files_do_not_claim_every_feed_is_current(self):
        self.run_js("""
const DATA={global:{window_start:'2026-10-02',window_end:'2026-10-09'},
 basketball:{window_start:'2026-10-02',window_end:'2026-10-09'}};
DATA.college={...DATA.global};DATA.tennisReview={...DATA.global};
function todayKey(){return '2026-10-02'}
function addDays(){return '2026-10-09'}
""", """
const result=publishedLoadStatus([['global',true],['basketball',true],['known',true]]);
assert.match(result.text,/3[/]3 published files loaded/);
assert.match(result.text,/source and participant checks remain separate/);
assert.doesNotMatch(result.text,/loaded and current|review complete|cleared/i);
assert.notEqual(result.tone,'status-ok');
DATA.basketball.window_end='2026-10-05';
assert.equal(publishedLoadStatus([['global',true],['basketball',true]]).tone,'status-warn');
delete DATA.basketball.window_end;
assert.match(publishedLoadStatus([['global',true],['basketball',true]]).text,/need verification/);
""", ["scheduleWindowStatus", "reviewFeedWindows", "publishedLoadStatus"])

    def test_paused_sources_never_claim_fresh_collection(self):
        self.run_js("const DATA={global:{sources:[{collection_paused:true}]}};", """
const result=publishedLoadStatus([['global',true]]);
assert.equal(result.tone,'status-warn');
assert.match(result.text,/saved evidence needs verification/);
assert.equal(feedCollectionPaused({publisher_permission_holds:[{publisher:'ITF'}]}),true);
assert.equal(feedCollectionPaused({collection_paused:true}),true);
assert.equal(feedCollectionPaused({}),false);
""", ["publishedLoadStatus"])

    def test_schedule_windows_hold_missing_future_and_short_dates(self):
        self.run_js("", """
const check=feed=>scheduleWindowStatus(feed,'2026-10-02','2026-10-09');
assert.equal(check(undefined),'not reported');
assert.equal(check({window_start:'2026-10-02'}),'not reported');
assert.equal(check({window_start:'2026-10-02',window_end:'unknown'}),'not reported');
assert.equal(check({window_start:'2026-02-30',window_end:'2026-10-09'}),'not reported');
assert.equal(check({window_start:'2026-10-10',window_end:'2026-10-01'}),'not reported');
assert.equal(check({window_start:'2026-09-24',window_end:'2026-10-01'}),'ended before review dates');
assert.equal(check({window_start:'2026-10-10',window_end:'2026-10-17'}),'starts after review dates');
assert.equal(check({window_start:'2026-10-03',window_end:'2026-10-10'}),'incomplete');
assert.equal(check({window_start:'2026-10-02',window_end:'2026-10-08'}),'incomplete');
assert.equal(check({window_start:'2026-10-01',window_end:'2026-10-09'}),'covers review dates');
assert.equal(check({window_start:'2026-10-02',window_end:'2026-10-09'}),'covers review dates');
""", ["scheduleWindowStatus"])

    def test_missing_dates_are_inclusive_across_month_and_dst_boundaries(self):
        self.run_js("const CT='America/Chicago';", """
const check=feed=>scheduleWindowGaps(feed,'2026-10-26','2026-11-02');
const full=[['2026-10-26','2026-11-02']];
assert.deepEqual(check(undefined),full);
assert.deepEqual(check({window_start:'invalid',window_end:'2026-11-02'}),full);
assert.deepEqual(check({window_start:'2026-10-18',window_end:'2026-10-25'}),full);
assert.deepEqual(check({window_start:'2026-11-03',window_end:'2026-11-10'}),full);
assert.deepEqual(check({window_start:'2026-10-25',window_end:'2026-11-01'}),[['2026-11-02','2026-11-02']]);
assert.deepEqual(check({window_start:'2026-10-23',window_end:'2026-10-30'}),[['2026-10-31','2026-11-02']]);
assert.deepEqual(check({window_start:'2026-10-27',window_end:'2026-11-01'}),[['2026-10-26','2026-10-26'],['2026-11-02','2026-11-02']]);
assert.deepEqual(check({window_start:'2026-10-20',window_end:'2026-11-05'}),[]);
assert.deepEqual(scheduleWindowGaps({window_start:'2026-03-09',window_end:'2026-03-10'},'2026-03-07','2026-03-10'),[['2026-03-07','2026-03-08']]);
""", ["ctKey", "addDays", "scheduleWindowStatus", "scheduleWindowGaps"])

    def test_notice_distinguishes_expired_and_partial_evidence_and_clears_on_reload(self):
        self.run_js("""
const CT='America/Chicago';
const host={innerHTML:'',visible:false,classList:{toggle:(_,value)=>host.visible=value}};
const document={getElementById:()=>host};
const esc=s=>String(s??'').replaceAll('<','&lt;').replaceAll('>','&gt;');
const DATA={
 global:{window_start:'2026-10-26',window_end:'2026-11-02'},
 college:{window_start:'2026-10-25',window_end:'2026-11-03'},
 basketball:{window_start:'2026-10-18',window_end:'2026-10-25',collection_paused:true},
 tennisReview:{window_start:'2026-10-23',window_end:'2026-10-30'},
 tennis:{publisher_permission_holds:[{publisher:'ITF'}]}
};
""", """
const before=JSON.stringify(DATA);
renderScheduleWarning('2026-10-26','2026-11-02');
assert.equal(host.visible,true);
assert.match(host.innerHTML,/NCAA basketball:<[/]b> Verify 2026-10-26 through 2026-11-02/);
assert.match(host.innerHTML,/ended before this review period/);
assert.match(host.innerHTML,/Automated collection is paused/);
assert.match(host.innerHTML,/Tennis review evidence:<[/]b> Verify 2026-10-31 through 2026-11-02/);
assert.match(host.innerHTML,/Some underlying sources are paused/);
assert.doesNotMatch(host.innerHTML,/Approved sports schedule|Nebraska collegiate schedules/);
assert.equal(JSON.stringify(DATA),before,'Rendering must not advance evidence dates');
DATA.basketball={...DATA.global};DATA.tennisReview={...DATA.global};
renderScheduleWarning('2026-10-26','2026-11-02');
assert.equal(host.visible,false);assert.equal(host.innerHTML,'');
// Source freshness remains separate even when all date windows cover the period.
assert.equal(publishedLoadStatus([['tennis',true]]).tone,'status-warn');
DATA.tennisReview={window_start:'<script>',window_end:'2026-11-02'};
renderScheduleWarning('2026-10-26','2026-11-02');
assert.equal(host.visible,true);assert.match(host.innerHTML,/missing or invalid/);
assert.doesNotMatch(host.innerHTML,/<script>/);
""", ["ctKey", "addDays", "scheduleWindowStatus", "scheduleWindowGaps", "reviewFeedWindows", "renderScheduleWarning", "publishedLoadStatus"])

    def test_failed_file_and_display_errors_are_not_success(self):
        self.run_js("const DATA={};", """
assert.match(publishedLoadStatus([['global',true],['known',false]]).text,/1[/]2.*unavailable/);
assert.equal(publishedLoadStatus([['global',true],['known',false]]).tone,'status-warn');
const result=publishedLoadStatus([['global',true]],['Known U18']);
assert.match(result.text,/Display issue: Known U18/);
assert.equal(result.tone,'status-warn');
""", ["scheduleWindowStatus", "reviewFeedWindows", "publishedLoadStatus"])

    def test_source_dates_distinguish_retained_and_missing_copies(self):
        self.run_js("""
const host={innerHTML:''};
const document={getElementById:()=>host};
const FILES={global:'g',known:'k',intake:'i',catalog:'c'};
const FEED_LABELS={global:'Schedule',known:'U18',intake:'Changes',catalog:'Catalog'};
const CT='America/Chicago';
const DATA={global:{generated_at:'2026-10-02T20:00:00Z',window_start:'2026-10-02',window_end:'2026-10-09'},
 known:{generated_at:'2026-09-16T20:00:00Z'},catalog:{generated_at:'invalid'}};
const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
""", """
renderPublishedDates([['global',true],['known',false],['intake',false],['catalog',true]]);
assert.match(host.innerHTML,/2026/);
assert.match(host.innerHTML,/Sep 16/);
assert.match(host.innerHTML,/previous loaded copy retained/);
assert.match(host.innerHTML,/Unavailable — no loaded copy/);
assert.match(host.innerHTML,/Publication date not reported/);
assert.match(host.innerHTML,/Schedule dates: 2026-10-02 through 2026-10-09/);
""", ["renderPublishedDates"])

    def test_reload_reenables_button_and_preserves_failed_previous_copy(self):
        self.run_js("""
const nodes=Object.fromEntries(['refreshBtn','refreshStatus','reviewTime','dataTime'].map(k=>[k,{}]));
const document={getElementById:id=>nodes[id]};
const FILES={global:'g',known:'k'};
const previous={generated_at:'2026-09-16T20:00:00Z'};
const DATA={known:previous};let LAST_LOAD_RESULTS=[];
async function fetchJson(url){if(url==='k')throw new Error('test unavailable');return {generated_at:'2026-10-02T20:00:00Z'}}
function fmtDateTime(value){return String(value)}
function renderPublishedDates(){}
function renderAll(){return ['Restriction Watch']}
""", """
(async()=>{
 await loadAll();
 assert.equal(nodes.refreshBtn.disabled,false);
 assert.match(nodes.refreshBtn.textContent,/Reload Published Data/);
 assert.equal(DATA.known,previous);
 assert.match(nodes.refreshStatus.textContent,/Display issue: Restriction Watch/);
 assert.equal(nodes.refreshStatus.className,'refresh-status status-warn');
 assert.equal(nodes.dataTime.textContent,'2026-10-02T20:00:00Z');
 assert.deepEqual(LAST_LOAD_RESULTS,[['global',true],['known',false]]);
})().catch(e=>{console.error(e);process.exitCode=1});
""", ["scheduleWindowStatus", "reviewFeedWindows", "publishedLoadStatus", "loadAll"])


if __name__ == "__main__":
    unittest.main()
