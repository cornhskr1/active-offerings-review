/* Pure identity-level schedule observations. This is not an approval or completeness model. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  if(root)root.CatalogHealthSummary=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const HOUR=3600000;
  const list=x=>Array.isArray(x)?x:[];
  const uniq=x=>[...new Set(x.filter(Boolean))];
  const time=x=>typeof x==='number'?x:Date.parse(x||'');
  const host=url=>{try{return new URL(url).hostname.toLowerCase().replace(/^www\./,'');}catch{return '';}};
  const retired=s=>s.retired===true||/(^|\.)espn\.com$/.test(host(s.endpoint||s.source_endpoint));
  const held=s=>s.collection_paused===true||s.collection_halted===true||s.permission_required===true||/permission|required|blocked|denied|paused|technical.only/.test(String(s.access_status||''));
  const reference=s=>['coverage-gap','official-event-window','tennis-intelligence'].includes(s.source_type)||/^(pending|missing|legacy-name|no-current-edition|no-next-edition|last-published-event-window|manual)/.test(s.coverage_status||'');
  const fixtureSource=s=>!!s&&s.approved_catalog!==false&&!retired(s)&&!held(s)&&!reference(s)&&!!host(s.endpoint||s.official_schedule_url);
  const family=s=>host(s.endpoint||s.official_schedule_url);
  function build(input){
    const {registry={},coverage={},global:globalData={},oddsMap={},oddsEvents={}}=input||{};
    const now=time(input&&input.now);
    // Explicit now is required for deterministic snapshots. Missing now fails closed.
    const start=input&&input.windowStart||globalData.window_start||coverage.schedule_window_start;
    const end=input&&input.windowEnd||globalData.window_end||coverage.schedule_window_end;
    const timezone=input&&input.windowTimezone||globalData.timezone||'America/Chicago';
    const dayFormat=new Intl.DateTimeFormat('en-CA',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit'});
    const dayKey=event=>{if(event.date_only||/^\d{4}-\d{2}-\d{2}$/.test(event.start_time||''))return String(event.start_time).slice(0,10);const stamp=time(event.start_time);if(!Number.isFinite(stamp))return '';const parts=Object.fromEntries(dayFormat.formatToParts(new Date(stamp)).map(p=>[p.type,p.value]));return parts.year+'-'+parts.month+'-'+parts.day;};
    const fresh=(stamp,ttl)=>Number.isFinite(now)&&Number.isFinite(time(stamp))&&time(stamp)<=now&&now-time(stamp)<=ttl;
    const covers=(data)=>!!data.window_start&&!!data.window_end&&String(data.window_start).slice(0,10)<=String(start).slice(0,10)&&String(data.window_end).slice(0,10)>=String(end).slice(0,10);
    const sourceTTL=Number.isFinite(input&&input.globalFreshnessHours)?input.globalFreshnessHours*HOUR:24*HOUR;
    const identities=list(coverage.identities).length?coverage.identities:list(registry.competitions);
    const rowsMap=new Map(),sourceMap=new Map(list(globalData.sources).map(s=>[s.id,s]));
    // Build once per snapshot, never across builds: scoped lookups must retain
    // exact domains, multiple candidates, and current source health flags.
    const scopedSources=new Map();
    for(const source of sourceMap.values()){
      if(!fixtureSource(source))continue;
      for(const scope of new Set(list(source.scope_source_ids))){
        if(!scopedSources.has(scope))scopedSources.set(scope,new Map());
        const domains=scopedSources.get(scope);
        for(const domain of new Set([host(source.endpoint),host(source.official_schedule_url)])){
          if(!domains.has(domain))domains.set(domain,[]);
          domains.get(domain).push(source);
        }
      }
    }
    const diagnostics={duplicate_identities:0,unknown_mapping_keys:[],unassigned_events:0,rejected_events:0,excluded_inactive_events:0,ambiguous_sources:[]};
    for(const identity of identities){
      const key=identity.identity_key;if(!key)continue;
      if(rowsMap.has(key)){diagnostics.duplicate_identities++;continue;}
      rowsMap.set(key,{identity_key:key,sport:identity.sport||'',league:identity.league||'',source_ids:uniq([...list(identity.source_ids),...list(identity.sources).map(s=>s.id)]),provider_keys:[],provider_families:[],mapped:false,state:'unmapped',fresh_event_count:0,stale_event_count:0,reference_event_count:0,date_only_event_count:0,healthy_source_count:0,_fresh:new Set(),_stale:new Set(),_reference:new Set(),_dateOnly:new Set(),_routes:[],_hasReference:false});
    }
    const sourceOwners=new Map();
    for(const row of rowsMap.values())for(const id of row.source_ids){if(!sourceOwners.has(id))sourceOwners.set(id,new Set());sourceOwners.get(id).add(row.identity_key);}
    // Scope IDs are explicit configured links, not permission to broadcast an event.
    for(const source of sourceMap.values())for(const scope of list(source.scope_source_ids))for(const key of sourceOwners.get(scope)||[]){
      const row=rowsMap.get(key);if(!row.source_ids.includes(source.id))row.source_ids.push(source.id);
    }
    sourceOwners.clear();
    for(const row of rowsMap.values())for(const id of row.source_ids){if(!sourceOwners.has(id))sourceOwners.set(id,new Set());sourceOwners.get(id).add(row.identity_key);}
    for(const [id,owners] of sourceOwners)if(owners.size>1)diagnostics.ambiguous_sources.push(id);
    const globalHealthy=s=>fixtureSource(s)&&s.ok===true&&!s.stale&&!s.source_stale&&fresh(s.checked_at,sourceTTL);
    const families=new Map();
    function route(row,name,id,healthy){
      row.mapped=true;row.provider_families=uniq([...row.provider_families,name]);
      if(healthy)row.healthy_source_count++;
      row._routes.push({name,id,healthy});
      if(!families.has(name))families.set(name,{name,source_ids:new Set(),identity_keys:new Set(),fresh_events:new Set(),healthy:false});
      if(healthy)families.get(name).healthy=true;
      families.get(name).source_ids.add(id);families.get(name).identity_keys.add(row.identity_key);
    }
    for(const row of rowsMap.values())for(const id of row.source_ids){
      const s=sourceMap.get(id);if(!s)continue;
      if(reference(s))row._hasReference=true;
      if(fixtureSource(s))route(row,family(s),id,globalHealthy(s)&&covers(s.source_type==='jolpica-race-schedule'?s:globalData));
    }
    const mappings=new Map(),providerOwners=new Map();
    for(const m of list(oddsMap.mappings)){
      if(!rowsMap.has(m.catalog_identity_key)){diagnostics.unknown_mapping_keys.push(m.catalog_identity_key);continue;}
      if(!m.provider_key)continue;
      if(!providerOwners.has(m.provider_key))providerOwners.set(m.provider_key,new Set());
      providerOwners.get(m.provider_key).add(m.catalog_identity_key);
      mappings.set(m.provider_key+'|'+m.catalog_identity_key,m);
    }
    const oddsSources=new Map(list(oddsEvents.sources).map(s=>[s.provider_key,s]));
    const oddsHealthy=s=>!!s&&s.status==='ok'&&!s.stale&&!s.source_stale&&!held(s)&&!held(oddsEvents.coverage||{})&&fresh(s.observed_at,3*HOUR);
    for(const m of mappings.values()){
      if(providerOwners.get(m.provider_key).size!==1)continue;
      const row=rowsMap.get(m.catalog_identity_key),s=oddsSources.get(m.provider_key);
      row.provider_keys=uniq([...row.provider_keys,m.provider_key]);
      if(!held(s||{})&&!held(oddsEvents.coverage||{}))route(row,'The Odds API','odds:'+m.provider_key,oddsHealthy(s)&&covers(oddsEvents));
    }
    const observations=[];
    function add(event,isOdds){
      const at=time(event.start_time),day=dayKey(event);if(!Number.isFinite(at)||!day||!start||!end||day<String(start).slice(0,10)||day>String(end).slice(0,10))return;
      if(/^(COMPLETED|COMPLETE|FINAL|CANCELLED|CANCELED|REMOVED|POSTPONED|FINISHED|STATUS_FINAL|STATUS_CANCELED)$/i.test(String(event.status||''))){diagnostics.excluded_inactive_events++;return;}
      if(!isOdds&&sourceMap.get(event.source_id)?.approved_catalog===false){diagnostics.rejected_events++;return;}
      if(event.catalog_approved===false||event.approved_catalog===false||event.catalog_rejected===true){diagnostics.rejected_events++;return;}
      let key=event.catalog_identity_key;
      if(isOdds){
        if(!key||!mappings.has(event.provider_key+'|'+key)||providerOwners.get(event.provider_key)?.size!==1){diagnostics.unassigned_events++;return;}
      }else{
        const owners=sourceOwners.get(event.source_id);
        // Explicit key must still be linked to this exact source.
        if(key&&(!owners||!owners.has(key))){diagnostics.unassigned_events++;return;}
        if(!key&&owners?.size===1)key=[...owners][0];
      }
      const row=rowsMap.get(key);if(!row){diagnostics.unassigned_events++;return;}
      let source=isOdds?oddsSources.get(event.provider_key):sourceMap.get(event.source_id);
      if(!isOdds&&!fixtureSource(source)){
        const scoped=scopedSources.get(event.source_id)?.get(host(event.source_endpoint))||[];
        if(scoped.length===1)source=scoped[0];
      }
      const token=key+'|'+(isOdds?'odds:'+event.provider_key:event.source_id)+'|'+(event.provider_event_id||event.id||[event.name,event.start_time].join('|'));
      const isReference=event.reference_only===true||(!isOdds&&reference(source||{}));
      if(isReference){row._reference.add(token);row._hasReference=true;return;}
      if(event.date_only)row._dateOnly.add(token);
      const current=!event.stale&&!event.source_stale&&!held(event)&&!retired(event)&&
        (isOdds?oddsHealthy(source)&&fresh(event.observed_at,3*HOUR):globalHealthy(source))&&
        (!event.observed_at||fresh(event.observed_at,isOdds?3*HOUR:sourceTTL));
      const label=String(event.name||'').trim().toLowerCase();
      let participants=uniq(list(event.participants).filter(p=>typeof p==='string').map(p=>p.trim().toLowerCase())).sort();
      // Global fixtures commonly carry only 'Away at Home', while Odds carries
      // participant arrays. Parse exactly one explicit two-party separator only:
      // no aliases, substrings, inferred teams, or multi-party names.
      if(!participants.length){const pair=label.split(/\s+(?:at|vs\.?)\s+/);if(pair.length===2&&pair.every(Boolean)&&pair[0]!==pair[1])participants=pair.sort();}
      const signature=key+'|'+new Date(at).toISOString()+'|'+(participants.length===2?'pair:'+JSON.stringify(participants):'name:'+label);
      observations.push({row,token,current,signature,origin:isOdds?'odds:'+event.provider_key:event.source_id,family:isOdds?'The Odds API':family(source||{})});
    }
    list(globalData.events).forEach(e=>add(e,false));list(oddsEvents.events).forEach(e=>add(e,true));
    // Merge only an exact identity/time/participants (or exact display-name) match
    // when each source contributes a single distinct event. Ambiguous doubleheaders
    // remain separate. Duplicate copies of an event retain their original ID.
    const signatures=new Map();
    for(const o of observations){if(!signatures.has(o.signature))signatures.set(o.signature,new Map());const origins=signatures.get(o.signature);if(!origins.has(o.origin))origins.set(o.origin,new Set());origins.get(o.origin).add(o.token);}
    for(const o of observations){const origins=signatures.get(o.signature);const exact=origins.size>1&&[...origins.values()].every(ids=>ids.size===1);const token=exact?'fixture:'+o.signature:o.token;
      if(o.current){o.row._fresh.add(token);const f=families.get(o.family);if(f)f.fresh_events.add(token);}else o.row._stale.add(token);
    }
    const workingFamilies=[...families.values()].filter(f=>f.healthy||f.fresh_events.size);
    const totals={identities:rowsMap.size,mapped:0,not_mapped:0,fresh:0,stale:0,healthy_empty:0,inactive_unknown:0,unmapped:0,reference_only:0,fresh_events:0,stale_events:0,reference_events:0,connected_provider_families:workingFamilies.length,configured_provider_families:families.size,date_only_events:0};
    const rows=[...rowsMap.values()].map(row=>{
      row.fresh_event_count=row._fresh.size;row.stale_event_count=[...row._stale].filter(k=>!row._fresh.has(k)).length;row.reference_event_count=row._reference.size;row.date_only_event_count=row._dateOnly.size;totals.date_only_events+=row.date_only_event_count;
      row.state=row.fresh_event_count?'fresh':row.stale_event_count?'stale':row.reference_event_count?'reference_only':row.healthy_source_count?'healthy_empty':row.mapped?'inactive_unknown':row._hasReference?'reference_only':'unmapped';
      totals[row.state]++;totals[row.mapped?'mapped':'not_mapped']++;totals.fresh_events+=row.fresh_event_count;totals.stale_events+=row.stale_event_count;totals.reference_events+=row.reference_event_count;
      delete row._fresh;delete row._stale;delete row._reference;delete row._dateOnly;delete row._routes;delete row._hasReference;return row;
    });
    // Compatibility API name: these are exact endpoint source domains, not a
    // count of corporate providers. The Odds API is the named API exception.
    const providerFamilies=workingFamilies.map(f=>({name:f.name,source_ids:[...f.source_ids].sort(),identity_keys:[...f.identity_keys].sort(),fresh_event_count:f.fresh_events.size})).sort((a,b)=>a.name.localeCompare(b.name));
    return {rows,totals,providerFamilies,provider_family_unit:'source domains (plus The Odds API)',diagnostics,window_start:start,window_end:end,window_timezone:timezone,global_freshness_hours:sourceTTL/HOUR,odds_freshness_hours:3,note:'Technical routing and saved schedule observations only; not event approval, complete coverage, or proof of no activity.'};
  }
  return {build};
});
