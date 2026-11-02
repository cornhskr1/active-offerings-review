/* Offline audit only: no requests, collection, mutations, or approval decisions. */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const Health=require('../assets/catalog-health-summary.js');
const Catalog=require('../assets/catalog-workspace.js');
const root=path.resolve(__dirname,'..');
const snapshot=path.resolve(process.argv[2]||root);
const now=process.argv[3];
if(!now||!Number.isFinite(Date.parse(now)))throw new Error('Supply snapshot directory and an explicit ISO observation time');
const load=(dir,file)=>JSON.parse(fs.readFileSync(path.join(dir,'data',file),'utf8'));
const globalData=load(snapshot,'global-schedule.json'),coverage=load(snapshot,'priority2-coverage-inventory.json'),registry=load(snapshot,'competition-identity-registry.json');
const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(now)).map(x=>[x.type,x.value]));
const start=`${parts.year}-${parts.month}-${parts.day}`;
const end=new Date(Date.parse(start+'T12:00:00Z')+7*86400000).toISOString().slice(0,10);
let oddsEvents={};try{oddsEvents=load(snapshot,'odds-api-events.json');}catch{}
const report=Health.build({registry,coverage,global:globalData,oddsMap:load(root,'odds-api-catalog-mappings.json'),oddsEvents,now,windowStart:start,windowEnd:end});
const espn=new Set(globalData.sources.filter(s=>{try{return /(^|\.)espn\.com$/.test(new URL(s.endpoint||'').hostname);}catch{return false;}}).map(s=>s.id));
const paused=globalData.sources.filter(s=>s.collection_paused||s.permission_required||s.access_status==='permission_required');
const seasonMap=load(snapshot,'catalog-season-map.json'),mapped=new Map();
for(const sport of seasonMap.sports||[])for(const group of sport.groups||[])for(const event of group.events||[]){mapped.set(event.key,event);for(const child of event.coverage_children||[])mapped.set(child.key,child);}
const missing=report.rows.filter(x=>!x.fresh_event_count).map(row=>{
 const season=mapped.get(row.identity_key),sources=globalData.sources.filter(s=>(row.source_ids||[]).includes(s.id));
 return {...row,season_status:Catalog.season(season,start,globalData.sources),season_start_date:season?.season_start_date||null,season_end_date:season?.season_end_date||null,season_last_verified:season?.last_verified||null,
   permission_hold:sources.some(s=>s.collection_paused||s.permission_required||s.access_status==='permission_required'),
   source_observations:sources.map(s=>({id:s.id,checked_at:s.checked_at||null,coverage_status:s.coverage_status||null,errors:s.errors||[]}))};
}).sort((a,b)=>({in:0,unknown:1,out:2}[a.season_status]-{in:0,unknown:1,out:2}[b.season_status])||a.sport.localeCompare(b.sport)||a.league.localeCompare(b.league));
const retained=coverage.identities.filter(x=>[...(x.source_ids||[]),...(x.sources||[]).map(s=>s.id)].some(id=>espn.has(id)));
console.log(JSON.stringify({as_of:now,window:[start,end],schedule_published:globalData.generated_at,totals:report.totals,retained_espn_source_records:espn.size,retained_espn_identity_routes:retained.length,publisher_hold_records:paused.length,preflights:globalData.sources.filter(x=>/sharp-api|api-sports|api-football/.test(x.id)),additional_competitions_with_new_usable_data:0,missing_competitions:missing,source_evidence:globalData.sources.map(s=>({id:s.id,league:s.league,sport:s.sport,checked_at:s.checked_at,access_status:s.access_status,collection_paused:s.collection_paused,coverage_status:s.coverage_status,errors:s.errors}))},null,2));
