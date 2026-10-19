/* Offline observation overlay. No network, storage, credentials, or approval decisions. */
(function(root){
'use strict';
const text=(v)=>typeof v==='string'&&v.length>0&&v.length<=300&&v===v.trim()&&!/[\x00-\x1f]/.test(v);
const participant=v=>text(v)&&! /\b(?:TBD|TBA|to be determined|to be announced|winner of|loser of)\b/i.test(v);
const timestamp=v=>{
 if(typeof v!=='string'||!/^\d{4}-\d\d-\d\dT\d\d:\d\d(?::\d\d(?:\.\d+)?)?(?:Z|[+-]\d\d:\d\d)$/.test(v)||!Number.isFinite(Date.parse(v)))return false;
 const [y,m,d]=v.slice(0,10).split('-').map(Number);return new Date(Date.UTC(y,m-1,d)).toISOString().slice(0,10)===v.slice(0,10)&&Number(v.slice(11,13))<24&&Number(v.slice(14,16))<60&&(v[16]!==':'||Number(v.slice(17,19))<60);
};
function validate(bundle,config){
 if(bundle?.schema_version!==1||bundle.provider!=='The Odds API'||!timestamp(bundle.observed_at)||!Array.isArray(bundle.events)||bundle.events.length>10000)throw Error('Invalid observation bundle.');
 if(Date.parse(bundle.observed_at)>Date.now())throw Error('Observation boundary is in the future.');
 const mappings=config?.mappings||[]; const seen=new Set(),matchups=new Set();
 const events=bundle.events.map(e=>{
  const m=mappings.find(m=>m.provider_key===e.provider_key&&m.catalog_identity_key===e.catalog_identity_key);
  if(!m||!text(e.id)||!text(e.provider_event_id)||!/^[A-Za-z0-9_-]{1,128}$/.test(e.provider_event_id)||!timestamp(e.start_time)||!timestamp(e.observed_at)||Date.parse(e.observed_at)>Date.parse(bundle.observed_at)||!Array.isArray(e.participants)||e.participants.length!==2||!e.participants.every(participant)||e.participants[0].toLowerCase()===e.participants[1].toLowerCase())throw Error('Unmapped identity or invalid event. No observations loaded.');
  const key=m.provider_key+'|'+e.provider_event_id;
  const matchup=m.catalog_identity_key+'|'+e.participants.map(x=>x.trim().toLowerCase()).sort().join('|')+'|'+new Date(e.start_time).toISOString();
  if(seen.has(key)||matchups.has(matchup))throw Error('Duplicate provider event or conflicting matchup. No observations loaded.');seen.add(key);matchups.add(matchup);
  return {id:'odds-api:'+m.provider_key+':'+e.provider_event_id,provider_event_id:e.provider_event_id,provider_key:m.provider_key,catalog_identity_key:m.catalog_identity_key,source_id:'odds-api:'+m.catalog_identity_key,provider:'The Odds API',sport:m.sport,league:m.league,region:m.region||'',name:e.participants.join(' vs '),participants:e.participants.slice(),start_time:new Date(e.start_time).toISOString(),observed_at:e.observed_at,status:'UNKNOWN',venue_status:'UNKNOWN',age_status:'UNKNOWN',phase_status:'UNKNOWN',coverage_complete:false,session_observation:true,source_stale:e.source_stale===true||Date.now()-Date.parse(e.observed_at)>3*60*60*1000};
 });
 return {schema_version:1,provider:'The Odds API',observed_at:bundle.observed_at,events};
}
const participantName=p=>typeof p==='string'?p:(p?.name||p?.displayName||'');
function key(e,identity){
 const raw=Array.isArray(e.participants)&&e.participants.length?e.participants:String(e.name||'').split(/ (?:at|vs\.?) /);
 const p=raw.map(participantName).map(x=>x.trim().toLowerCase()).sort();
 if(!identity||p.length!==2||p.some(x=>!x)||!timestamp(e.start_time))return null;
 return identity+'|'+p.join('|')+'|'+new Date(e.start_time).toISOString();
}
function merge(base,session,identityFor){
 const out=base.map(e=>({...e})), byKey=new Map();
 out.forEach((e,i)=>{const k=key(e,identityFor(e));if(k){if(!byKey.has(k))byKey.set(k,[]);byKey.get(k).push(i);}});
 for(const e of session?.events||[]){
  const k=key(e,e.catalog_identity_key),matches=byKey.get(k)||[];
  if(matches.length){for(const i of matches)out[i]={...out[i],odds_observation:{provider:'The Odds API',observed_at:e.observed_at,catalog_identity_key:e.catalog_identity_key,source_stale:e.source_stale===true}};}
  else {byKey.set(k,[out.length]);out.push({...e});}
 }
 return out;
}
const api={validate,merge,key};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.OddsSession=api;
})(typeof globalThis!=='undefined'?globalThis:this);
