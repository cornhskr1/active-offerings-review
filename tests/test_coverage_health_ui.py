"""Coverage summary uses exact identities and current saved evidence, not fixed counts."""
import re,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'index.html').read_text()
SCRIPT=re.search(r'<script>([\s\S]*)</script>',HTML).group(1).split('// interactions')[0]
class CoverageHealthUiTests(unittest.TestCase):
 def test_live_counts_and_filters_share_identity_rows(self):
  body=r'''
const assert=require('node:assert/strict');
const CatalogHealthSummary=require('./assets/catalog-health-summary.js');
const now=new Date().toISOString(),day=todayKey();
DATA.coverage={identities:[{identity_key:'a',sport:'Sport',league:'Alpha',sources:[]},{identity_key:'b',sport:'Sport',league:'Beta',sources:[]}]};
DATA.oddsMap={mappings:[{provider_key:'key_a',catalog_identity_key:'a',sport:'Sport',league:'Alpha'}]};
DATA.oddsEvents={events:[{id:'e1',catalog_identity_key:'a',provider_key:'key_a',source_id:'the-odds-api',name:'Away at Home',participants:['Away','Home'],start_time:day+'T18:00:00Z',observed_at:now,status:'UNKNOWN'}],sources:[{provider_key:'key_a',status:'ok',observed_at:now}],collector_state:{schema_version:1}};
DATA.global={sources:[],events:[]};
const host={innerHTML:''};global.document={getElementById:()=>host};
renderCatalogHealth();assert.match(host.innerHTML,/Coverage at a glance/);assert.match(host.innerHTML,/1 \/ 2/);assert.match(host.innerHTML,/Current fixtures: 1/);
CATALOG_HEALTH_FILTER='identity:fresh';assert.equal(catalogEntryMatchesHealth('Sport',['Alpha'],[]),true);assert.equal(catalogEntryMatchesHealth('Sport',['Beta'],[]),false);
DATA.oddsEvents.sources[0].stale=true;renderCatalogHealth();assert.match(host.innerHTML,/Current fixtures: 0/);assert.match(host.innerHTML,/Saved fixtures need checking: 1/);
assert.equal(catalogEntryMatchesHealth('Sport',['Alpha'],[]),false);
CATALOG_HEALTH_FILTER='identity:stale';assert.equal(catalogEntryMatchesHealth('Sport',['Alpha'],[]),true);
CATALOG_IDENTITY_HEALTH={rows:[{identity_key:'regular',sport:'Sport',league:'Regular',source_ids:['shared'],state:'fresh',mapped:true},{identity_key:'preseason',sport:'Sport',league:'Preseason',source_ids:['shared'],state:'stale',mapped:true}]};
CATALOG_HEALTH_FILTER='identity:fresh';assert.equal(catalogEntryMatchesHealth('Sport',['preseason'],['shared']),false);assert.equal(catalogEntryMatchesHealth('Sport',['regular'],['shared']),true);assert.equal(catalogEntryMatchesHealth('Sport',['Unknown'],['shared']),false);
assert.match(host.innerHTML,/<details[^>]*><summary>Sources and connection details/);
assert.doesNotMatch(host.innerHTML,/733 catalog identities/);
'''
  subprocess.run(['node'],input=SCRIPT+'\n'+body,text=True,cwd=ROOT,check=True)
 def test_module_is_loaded_before_application(self):
  self.assertLess(HTML.index('assets/catalog-health-summary.js'),HTML.index('const DATA={}'))
