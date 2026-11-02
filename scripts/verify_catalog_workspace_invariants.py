"""Compare existing decisions before/after a UI change using one offline snapshot.

Usage: python scripts/verify_catalog_workspace_invariants.py BASE_REF SNAPSHOT_DIR ISO_TIME
No collection, Git writes, or changes to saved evidence.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base, snapshot, observed = sys.argv[1:]
snapshot = str(Path(snapshot).resolve())
baseline = subprocess.check_output(['git', 'show', f'{base}:index.html'], cwd=ROOT, text=True)
current = (ROOT / 'index.html').read_text()
bootstrap = """
const fs=require('node:fs'),path=require('node:path');
const OddsSession=require('./assets/odds-session.js');
const JolpicaF1=require('./assets/jolpica-f1.js');
const CatalogHealthSummary=require('./assets/catalog-health-summary.js');
const RealDate=Date;
""" + f"const fixed={json.dumps(observed)}, snapshot={json.dumps(snapshot)};\n" + """
global.Date=class extends RealDate{constructor(...args){super(...(args.length?args:[fixed]));}static now(){return RealDate.parse(fixed);}};
"""
probe = """
for(const [key,file] of Object.entries(FILES)){const p=path.join(snapshot,file);if(fs.existsSync(p))DATA[key]=JSON.parse(fs.readFileSync(p,'utf8'));}
// FILES gained a presentation-only registry. Give both versions identical input.
DATA.identities=JSON.parse(fs.readFileSync(path.join(snapshot,'data/competition-identity-registry.json'),'utf8'));
const input=JSON.stringify(DATA);
ODDS_SESSION=DATA.oddsEvents?OddsSession.validate(DATA.oddsEvents,DATA.oddsMap):null;
F1_SNAPSHOT=DATA.f1?JolpicaF1.project(DATA.f1,fixed):null;
const model=buildTodayModel();
const age=combinedKnownU18Rows().rows.map(row=>({row,assessment:registryAgeSummary(row,todayKey())}));
const progress=(DATA.seasonMap.sports||[]).flatMap(s=>(s.groups||[]).flatMap(g=>(g.events||[]).map(e=>({key:e.key,status:mappedSeasonStatus(e),html:seasonProgressHtml(e,mappedSeasonStatus(e))}))));
const result={model,age,eventMappings:model.events.map(e=>mappedCatalogEventForScheduleEvent(e)),restrictions:DATA.catalog.restrictions,wide:catalogWideStandards(DATA.catalog),sportNotes:catalogSportNotes(DATA.catalog),progress};
if(input!==JSON.stringify(DATA))throw new Error('Decision probe mutated published inputs');
process.stdout.write(JSON.stringify(result));
"""

def evaluate(html):
    inline = re.search(r'<script>([\s\S]*)</script>', html).group(1).split('// interactions')[0]
    result = subprocess.run(['node'], input=bootstrap + inline + probe, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(result.stderr)
    return json.loads(result.stdout)

before, after = evaluate(baseline), evaluate(current)
if before != after:
    raise SystemExit('FAIL: existing decisions changed; stop before merge/deployment')
digest = hashlib.sha256(json.dumps(after, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
print(json.dumps({'status':'identical','baseline':base,'observed_at':observed,'sha256':digest,
    'events':len(after['model']['events']),'age_records':len(after['age']),
    'restriction_entries':len(after['restrictions']),'season_progress_entries':len(after['progress']),
    'red':after['model']['red'],'amber':after['model']['amber']}, indent=2))
