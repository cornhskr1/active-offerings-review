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
    def run_js(self, setup, body, names):
        script = "const assert=require('node:assert/strict');\nconsole.warn=()=>{};\n" + setup
        script += "\n" + "\n".join(source(name) for name in names)
        script += "\n" + body
        subprocess.run(["node", "-e", script], check=True, cwd=ROOT)

    def test_loaded_files_do_not_claim_every_feed_is_current(self):
        self.run_js("""
const DATA={global:{window_start:'2026-10-02',window_end:'2026-10-09'},
 basketball:{window_start:'2026-10-02',window_end:'2026-10-09'}};
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
""", ["scheduleWindowStatus", "publishedLoadStatus"])

    def test_schedule_windows_hold_missing_future_and_short_dates(self):
        self.run_js("", """
const check=feed=>scheduleWindowStatus(feed,'2026-10-02','2026-10-09');
assert.equal(check(undefined),'not reported');
assert.equal(check({window_start:'2026-10-02'}),'not reported');
assert.equal(check({window_start:'2026-10-02',window_end:'unknown'}),'not reported');
assert.equal(check({window_start:'2026-02-30',window_end:'2026-10-09'}),'not reported');
assert.equal(check({window_start:'2026-10-03',window_end:'2026-10-10'}),'incomplete');
assert.equal(check({window_start:'2026-10-02',window_end:'2026-10-08'}),'incomplete');
assert.equal(check({window_start:'2026-10-01',window_end:'2026-10-09'}),'older publication');
assert.equal(check({window_start:'2026-10-02',window_end:'2026-10-09'}),'covers review dates');
""", ["scheduleWindowStatus"])

    def test_failed_file_and_display_errors_are_not_success(self):
        self.run_js("const DATA={};", """
assert.match(publishedLoadStatus([['global',true],['known',false]]).text,/1[/]2.*unavailable/);
assert.equal(publishedLoadStatus([['global',true],['known',false]]).tone,'status-warn');
const result=publishedLoadStatus([['global',true]],['Known U18']);
assert.match(result.text,/Display issue: Known U18/);
assert.equal(result.tone,'status-warn');
""", ["scheduleWindowStatus", "publishedLoadStatus"])

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
""", ["scheduleWindowStatus", "publishedLoadStatus", "loadAll"])


if __name__ == "__main__":
    unittest.main()
