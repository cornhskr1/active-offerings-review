"""Offline synthetic browser-overlay contract; never contacts a publisher."""
import pathlib, subprocess, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class OddsSessionTests(unittest.TestCase):
 def test_offline_validation_and_additive_merge(self):
  script=r'''
const assert=require('node:assert/strict');const api=require('./assets/odds-session.js');
const m={provider_key:'synthetic',catalog_identity_key:'synthetic-id',sport:'Basketball',league:'Synthetic League'};
const e={id:'old-input',provider_event_id:'one',provider_key:m.provider_key,catalog_identity_key:m.catalog_identity_key,participants:['Away','Home'],start_time:'2026-10-20T18:00:00Z',observed_at:'2026-10-19T02:00:00Z',bookmakers:[{key:'must-not-survive'}],requires_age_review:false};
const b={schema_version:1,provider:'The Odds API',observed_at:e.observed_at,events:[e]},config={mappings:[m]};
const clean=api.validate(b,config);assert.equal(clean.events.length,1);assert(!JSON.stringify(clean).includes('bookmakers'));assert(!JSON.stringify(clean).includes('requires_age_review'));
assert.equal(clean.events[0].age_status,'UNKNOWN');assert.equal(clean.events[0].status,'UNKNOWN');
for(const bad of [{...e,provider_key:'conditional'},{...e,start_time:'2026-10-20'}, {...e,participants:['Home','Home']},{...e,provider_event_id:''},{...e,provider_event_id:'bad:id'},{...e,participants:['Home','home']},{...e,participants:[' ','Away']},{...e,participants:['Winner of Round','Away']},{...e,participants:['Home\n','Away']},{...e,start_time:'2026-02-30T18:00:00Z'},{...e,observed_at:'2026-10-19T03:00:00Z'}])assert.throws(()=>api.validate({...b,events:[bad]},config));
assert.throws(()=>api.validate({...b,events:[e,e]},config));
assert.throws(()=>api.validate({...b,events:[e,{...e,id:'other',provider_event_id:'other',participants:['Home','Away']}]},config));
const base={id:'canonical',catalog_identity_key:m.catalog_identity_key,participants:['Home','Away'],start_time:e.start_time,source_stale:true,requires_age_review:true,status_detail:'U18 evidence must remain',status:'CANCELLED'};
const before=JSON.stringify(base);const merged=api.merge([base],clean,x=>x.catalog_identity_key);
assert.equal(merged.length,1);assert.equal(merged[0].id,'canonical');assert.equal(merged[0].status,'CANCELLED');assert.equal(merged[0].requires_age_review,true);assert.equal(merged[0].status_detail,base.status_detail);assert.equal(merged[0].source_stale,true);assert.equal(JSON.stringify(base),before);assert.equal(merged[0].odds_observation.provider,'The Odds API');
const named={...base,name:'Away at Home'};delete named.participants;assert.equal(api.merge([named],clean,x=>x.catalog_identity_key).length,1);
const ambiguous={...named,name:'Away at Home at Other'};assert.equal(api.merge([ambiguous],clean,x=>x.catalog_identity_key).length,2);
const other={...base,catalog_identity_key:'different'};assert.equal(api.merge([other],clean,x=>x.catalog_identity_key).length,2);
assert.equal(api.merge([],clean,()=>null).length,1);
'''
  subprocess.run(['node','-e',script],cwd=ROOT,check=True)
 def test_no_network_storage_or_odds(self):
  helper=(ROOT/'assets/odds-session.js').read_text()
  for forbidden in ['fetch(', 'XMLHttpRequest', 'localStorage', 'sessionStorage', 'apiKey', 'reference_quotes']:
   self.assertNotIn(forbidden,helper)
  page=(ROOT/'index.html').read_text()
  self.assertNotIn('oddsSessionFile',page);self.assertIn("oddsEvents:'data/odds-api-events.json'",page);self.assertIn('oddsCatalogHealthHtml',page)
  self.assertIn('Existing restrictions still apply.',page)
  self.assertNotIn('Line A',page);self.assertNotIn('Line B',page)
