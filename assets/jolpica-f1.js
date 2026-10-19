/* Presentation adapter only. Jolpica data stays in its separate licensed dataset. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.JolpicaF1=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const IDENTITY='motorsports-intl-f1',SOURCE='jolpica-f1',ENDPOINT='https://api.jolpi.ca/ergast/f1/current/races/';
 const LICENSE='CC-BY-NC-SA-4.0';
 const centralDay=value=>{const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(value)).map(p=>[p.type,p.value]));return `${parts.year}-${parts.month}-${parts.day}`;};
 const text=v=>typeof v==='string'&&v.length>0&&v.length<=500&&!/[\x00-\x1f]/.test(v);
 const stamp=v=>typeof v==='string'&&/T.*(?:Z|[+-]\d\d:\d\d)$/.test(v)&&Number.isFinite(Date.parse(v));
 function project(data,now){
  const at=Date.parse(now),fail=()=>{throw new Error('Invalid Jolpica F1 schedule snapshot');};
  if(!Number.isFinite(at)||!data||data.schema_version!==1||data.provider!=='Jolpica-F1'||data.source_id!==SOURCE||data.catalog_identity_key!==IDENTITY||data.dataset_scope!=='isolated_jolpica_f1_only'||!Array.isArray(data.events)||data.events.length>100)fail();
  if(!data.collector_state||typeof data.collector_state!=='object'||Array.isArray(data.collector_state)||typeof data.collector_state.halted!=='boolean')fail();
  const license=data.license;
  if(!license||license.id!==LICENSE||license.url!=='https://creativecommons.org/licenses/by-nc-sa/4.0/'||license.source_url!=='https://github.com/jolpica/jolpica-f1'||license.terms_url!=='https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md'||!['attribution','changes','notice'].every(k=>text(license[k])))fail();
  if(!stamp(data.window_start)||!stamp(data.window_end)||Date.parse(data.window_end)<=Date.parse(data.window_start)||!['partial','cached','stale','paused'].includes(data.source_health?.status))fail();
  if(data.observed_at!==null&&(!stamp(data.observed_at)||Date.parse(data.observed_at)>at))fail();
  const current=stamp(data.observed_at)&&at-Date.parse(data.observed_at)<=86400000&&['partial','cached'].includes(data.source_health.status)&&data.collector_state?.halted!==true;
  const seen=new Set();
  const events=data.events.map(e=>{
   if(!e||e.source_id!==SOURCE||e.catalog_identity_key!==IDENTITY||e.status!=='UNKNOWN'||e.coverage_complete!==false||e.license_id!==LICENSE||e.source_url!==ENDPOINT||!text(e.name)||!text(e.circuit)||!/^\d{4}-\d{2}-\d{2}$/.test(e.date)||new Date(e.date+'T00:00:00Z').toISOString().slice(0,10)!==e.date||!stamp(e.observed_at)||Date.parse(e.observed_at)>at||typeof e.source_stale!=='boolean'||typeof e.date_only!=='boolean')fail();
   if(!/^\d{4}$/.test(String(e.season))||!Number.isInteger(e.round)||e.round<1||!/^[A-Za-z0-9_-]+$/.test(e.circuit_id)||e.id!==`${SOURCE}:${e.season}:${e.round}:${e.circuit_id}`||seen.has(e.id)||e.date.slice(0,4)!==String(e.season))fail();
   if(e.date_only?e.start_time!==null:(!stamp(e.start_time)||new Date(e.start_time).toISOString().slice(0,10)!==e.date))fail();
   if(!stamp(data.observed_at)||Date.parse(e.observed_at)>Date.parse(data.observed_at))fail();
   if(e.date_only?(e.date<centralDay(data.window_start)||e.date>=centralDay(data.window_end)):(Date.parse(e.start_time)<Date.parse(data.window_start)||Date.parse(e.start_time)>=Date.parse(data.window_end)))fail();
   seen.add(e.id);
   // Whitelist schedule facts only. Never import entrants, ages, approval or season bounds.
   return {id:e.id,source_id:SOURCE,catalog_identity_key:IDENTITY,provider:'Jolpica-F1',sport:'Motorsports',league:'Formula One (F1)',name:e.name,circuit:e.circuit,locality:text(e.locality)?e.locality:'',country:text(e.country)?e.country:'',region:'International',start_time:e.date_only?e.date:e.start_time,date_only:e.date_only,status:'UNKNOWN',observed_at:e.observed_at,source_stale:!current||e.source_stale||at-Date.parse(e.observed_at)>86400000,source_endpoint:ENDPOINT,source_url:ENDPOINT,coverage_status:'partial',coverage_complete:false,license_id:LICENSE};
  });
  return {events,license:{...license},current:!!current,source:{id:SOURCE,sport:'Motorsports',league:'Formula One (F1)',catalog_terms:[IDENTITY],endpoint:ENDPOINT,source_type:'jolpica-race-schedule',window_start:centralDay(data.window_start),window_end:centralDay(Date.parse(data.window_end)-1),coverage_status:'partial',ok:!!current,stale:!current,collection_paused:data.collector_state?.halted===true||data.source_health.status==='paused',checked_at:data.observed_at,events:events.length,source_note:'Race schedule only. Entrants, ages and race status are unknown. Not a wagering approval.'}};
 }
 function coverage(base,snapshot){
  if(!snapshot)return base;
  return {...base,identities:(base?.identities||[]).map(row=>row.identity_key===IDENTITY?{...row,source_ids:[...new Set([...(row.source_ids||[]),SOURCE])]}:row)};
 }
 function global(base,snapshot){
  if(!snapshot)return base||{};
  return {...base,sources:[...(base?.sources||[]).filter(s=>s.id!==SOURCE),snapshot.source],events:[...(base?.events||[]).filter(e=>e.source_id!==SOURCE),...snapshot.events]};
 }
 return {IDENTITY,SOURCE,project,coverage,global};
});
