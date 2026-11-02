/* Read-only presentation model. Never consumed by catalog approval or age screening. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.CatalogWorkspace=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const norm=v=>String(v||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[’']/g,'').replace(/[^a-z0-9]+/g,' ').trim();
const unique=a=>[...new Set(a.filter(Boolean))];
const validDate=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&Number.isFinite(Date.parse(v+'T12:00:00Z'))&&new Date(v+'T12:00:00Z').toISOString().slice(0,10)===v;
function season(event,today,sources=[]){
 if(!event||event.nonseasonal||event.season_hold||event.season_window_complete===false)return 'unknown';
 if(event.coverage_children?.length){const statuses=event.coverage_children.map(x=>season(x,today,sources));return statuses.every(x=>x===statuses[0])?statuses[0]:'unknown';}
 const ids=unique([event.source_id,...(event.source_ids||[])]);
 if(event.season_end_date<today&&sources.some(x=>ids.includes(x.id)&&x.coverage_status==='last-published-event-window'))return 'unknown';
 if(validDate(event.season_start_date)&&validDate(event.season_end_date)&&event.season_start_date<=event.season_end_date){
  // Prior-year dates describe their recorded edition, not this year's status.
  if(Number(event.season_end_date.slice(0,4))<Number(today.slice(0,4)))return 'unknown';
  return today>=event.season_start_date&&today<=event.season_end_date?'in':'out';
 }
 // Recurring month/day windows are retained as approximate context, not confirmed current dates.
 if(event.season_status_year===Number(today.slice(0,4))&&['in','out'].includes(event.season_status)&&event.last_verified)return event.season_status;
 return 'unknown';
}
function aliasRows(identities,key){
 const rows=identities.filter(x=>x.identity_key===key);
 const result=[];const seen=new Set();
 for(const row of rows){for(const item of [...(row.aliases||[]),...(row.source_labels||[]).map(x=>({...x,name_type:'source label'}))]){
  if(!item?.name)continue;
  const k=JSON.stringify([item.name,item.operator||item.operator_name||'',item.name_type||'']);if(seen.has(k))continue;seen.add(k);
  result.push({...item});
 }}return result;
}
function build({catalog={},seasonMap={},identities={},today,sources=[],role=()=> 'catalog-event',notes=[]}){
 const competitions=identities.competitions||[];const rows=[];
 for(const section of catalog.sections||[]){
  const mapping=(seasonMap.sports||[]).find(x=>x.sport===section.sport);const sportNotes=notes.filter(x=>x.sport===section.sport||(x.sport==='NCAA'&&section.sport.startsWith('NCAA ')));
  const common=sportNotes.flatMap(x=>Array.isArray(x.content)?x.content:[x.content]);
  for(const group of mapping?.groups||[]){for(const event of group.events||[]){
   const aliases=aliasRows(competitions,event.key);
   // Include child aliases without merging distinct catalog identities.
   for(const child of event.coverage_children||[])for(const alias of aliasRows(competitions,child.key))aliases.push({...alias,scope:child.label||child.catalog_event||child.key});
   const restrictions=unique([...(event.restrictions||[]),...common]);
   rows.push({id:event.key,sport:section.sport,name:event.catalog_event,event,group,aliases,restrictions,notes:event.notes||[],status:season(event,today,sources),kind:'mapped'});
  }}
  if(section.sport==='Olympics'){
   const seen=new Map();
   for(const edition of mapping?.editions||[]){for(const event of [...(edition.crosswalk||[]),...(edition.approved_not_scheduled||[])]){
    if(!event.catalog_event)continue;
    const k=edition.key+'|'+event.catalog_event;
    if(seen.has(k)){const row=seen.get(k);row.restrictions=unique([...row.restrictions,...(event.restrictions||[])]);continue;}
    const row={id:'olympics:'+k,sport:section.sport,name:event.catalog_event,event,edition,group:{country:edition.label,governing_body:event.governing_body},aliases:[],restrictions:unique([...(event.restrictions||[]),...common]),notes:[],status:'unknown',kind:'olympic'};seen.set(k,row);rows.push(row);
   }}
  }
  // Keep unmapped/new catalog entries visible; all original lines also have a lossless source view.
  const snapshot=new Map();for(const line of mapping?.catalog_snapshot_lines||[])snapshot.set(line,(snapshot.get(line)||0)+1);
  let country='',body='';
  for(let i=0;i<(section.lines||[]).length;i++){
   const line=section.lines[i];
   const groupCountry=(mapping?.groups||[]).some(g=>norm(g.country)===norm(line));
   const groupBody=(mapping?.groups||[]).some(g=>norm(g.governing_body)===norm(line)||norm(g.confederation)===norm(line));
   const r=groupCountry?'catalog-country':groupBody?'catalog-org':role(line,section.sport,country);
   if(r==='catalog-country'||r==='catalog-section'){country=line;continue;}
   if(r==='catalog-org'){body=line;continue;}
   if(mapping?.catalog_snapshot_lines?.length){const n=snapshot.get(line)||0;if(n){snapshot.set(line,n-1);continue;}}
   const name=norm(line).replace(/ (no |markets |wagers? |prohibited ).*$/,'');
   if(rows.some(x=>x.sport===section.sport&&(norm(x.name)===name||norm(x.name)===norm(line))))continue;
   if(r!=='catalog-event'||sportNotes.some(n=>n.rawLines?.includes(line)))continue;
   rows.push({id:'catalog-line:'+section.sport+':'+i,sport:section.sport,name:line,event:null,group:{country,governing_body:body},aliases:[],restrictions:unique([...common,...(/\b(NO |MARKETS |WAGERS? |ONLY|RESTRICT)/i.test(line)?[line]:[])]),notes:[],status:'unknown',kind:'unmapped'});
  }
 }
 for(const row of rows)row.search=norm([row.sport,row.name,row.group.country,row.group.confederation,row.group.governing_body,row.event?.category,...row.aliases.flatMap(x=>[x.name,x.operator,x.operator_name,x.scope]),...row.restrictions].join(' '));
 return rows;
}
function filter(rows,{query='',status='all',restricted=false,sport=null}={}){
 const q=norm(query);return rows.filter(x=>(!sport||x.sport===sport)&&(!q||x.search.includes(q))&&(!restricted||x.restrictions.length>0)&&(status==='all'||x.status===status));
}
function counts(rows,options={}){const a=filter(rows,{...options,status:'all'});return {all:a.length,in:a.filter(x=>x.status==='in').length,unknown:a.filter(x=>x.status==='unknown').length,out:a.filter(x=>x.status==='out').length};}
function u18Placement(record,rows){
 // Only an explicit evidenced catalog relationship can put someone into a specific competition.
 const link=record.league_mapping;
 const key=link?.status==='verified'&&(link.evidence_url||link.source_url)?link.catalog_identity_key:null;
 const match=key?rows.find(x=>x.id===key||(x.event?.coverage_children||[]).some(c=>c.key===key)):null;
 return {sport:match?.sport||record.sport||'Other',leagueId:match?.id||null};
}
function matchEvent(row,event,mapped){
 if(!mapped)return false;
 const keys=[row.id,...(row.event?.coverage_children||[]).map(x=>x.key)];
 if(event.catalog_identity_key)return keys.includes(event.catalog_identity_key);
 if(mapped.key)return keys.includes(mapped.key);
 return (mapped.parent_catalog_event===row.name&&mapped.sport===row.sport)||(mapped.catalog_event===row.name&&mapped.sport===row.sport&&(!mapped.country||mapped.country===row.group?.country));
}
function eventDate(event){
 const value=event.start_time;
 if(event.date_only||typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value))return validDate(String(value).slice(0,10))?{date:String(value).slice(0,10),time:'Time not published'}:{date:'Date not published',time:'Time not published'};
 if(typeof value!=='string'||!/(?:Z|[+-]\d{2}:\d{2})$/.test(value)||!Number.isFinite(Date.parse(value)))return {date:'Date not confirmed',time:'Time not published'};
 const date=new Date(value);return {date:new Intl.DateTimeFormat('en-US',{timeZone:'America/Chicago',month:'short',day:'numeric',year:'numeric'}).format(date),time:new Intl.DateTimeFormat('en-US',{timeZone:'America/Chicago',hour:'numeric',minute:'2-digit',timeZoneName:'short'}).format(date)};
}
return {norm,season,build,filter,counts,u18Placement,matchEvent,eventDate};
});
