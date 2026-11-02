/* UI-only bridge to existing published data, evidence renderers and review model. */
let CATALOG_BROWSER={sport:null,entry:'all',event:null,status:'all',restricted:false,date:'all'};
let CATALOG_BOARD_EVENTS=[];
let CATALOG_BROWSER_ROWS=[];
const catalogSeasonLabel=s=>({in:'In season',out:'Out of season',unknown:'Undetermined'}[s]||'Undetermined');
function catalogAliasLabel(alias){
 if(alias.operator||alias.operator_name)return alias.operator||alias.operator_name;
 if(alias.name_type==='operator'){
  try{const host=new URL(alias.evidence_url).hostname;if(host==='sportsbook.fanduel.com')return 'FanDuel';if(host==='www.ticketmaster.com')return 'Ticketmaster (ticketing)';}catch(_){}
  return 'Operator not recorded';
 }
 return alias.name_type==='source label'?'Source label':alias.name_type==='data-provider'?'Data provider':'Also called';
}
function catalogBrowserU18(){return combinedKnownU18Rows().rows.filter(x=>registryAgeSummary(x,todayKey()).status!=='VERIFIED 18+');}
function catalogBrowserAthlete(x){
 const age=registryAgeSummary(x,todayKey());const link=String(x.source_url||'');
 const title=/^https?:\/\//.test(link)?`<a href="${esc(link)}" target="_blank" rel="noopener noreferrer">${esc(x.athlete)}</a>`:esc(x.athlete);
 const evidence=x.age_evidence||{};
 return `<article class="registry-athlete"><b>${title}</b> ${pill(age.color,age.status)}<div class="row-meta">${esc(age.label)}${x.team?` · ${esc(x.team)}`:''}${x.league?`<br>Recorded context: ${esc(x.league)}`:''}${x.aliases?.length?`<br>Also recorded as: ${esc(x.aliases.join(', '))}`:''}<br>Evidence checked: ${esc(u18LastVerifiedLabel(evidence.checked_at))} · Last verified: ${esc(u18LastVerifiedLabel(x.last_verified))}</div><details><summary>Age evidence</summary>${evidence.status==='verified_dob'?`<p>Verified DOB: ${esc(evidence.dob)}</p>`:''}<p>${esc(x.evidence||evidence.review?.notes||'See the linked evidence. Exact age may be uncertain.')}</p>${(evidence.sources||[]).map(s=>`<p>${/^https?:\/\//.test(s.url||'')?`<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title||'Source')}</a>`:''} ${esc(s.evidence||'')}</p>`).join('')}${evidence.status==='conflicting_dob'?`<p>DOB conflict: ${esc(JSON.stringify(evidence.candidates||evidence.candidate_dobs||evidence))}</p>`:''}</details></article>`;
}
function catalogBrowserSportDetails(sport){
 const people=catalogBrowserU18().filter(x=>CatalogWorkspace.u18Placement(x,CATALOG_BROWSER_ROWS).sport===sport);
 const section=(DATA.catalog?.sections||[]).find(x=>x.sport===sport);
 const notes=catalogSportNotes(DATA.catalog||{}).filter(x=>x.sport===sport||(x.sport==='NCAA'&&sport.startsWith('NCAA ')));
 return `<div class="catalog-path">${esc(sport)}</div><h3>Known U18 &amp; age evidence</h3><p>${people.length} current record${people.length===1?'':'s'} · Unverified league relationships stay at sport level.</p>${people.map(catalogBrowserAthlete).join('')||'<p>No current verified U18 information is available here. This does not confirm that all participants are 18 or older.</p>'}${notes.map(n=>`<div class="catalog-detail-rules"><b>${esc(n.title)}</b>${(Array.isArray(n.content)?n.content:[n.content]).map(t=>`<p>${esc(t)}</p>`).join('')}</div>`).join('')}${section?`<details><summary>Original catalog wording · ${esc(sport)}</summary>${section.lines.map(x=>`<div>${esc(x)}</div>`).join('')}</details>`:''}`;
}
function catalogBrowserEvents(row){
 const model=TODAY_MODEL||buildTodayModel();
 const referenceSources=new Set((model.global.sources||[]).filter(x=>x.source_type==='official-event-window').map(x=>x.id));
 return model.events.filter(event=>!event.reference_only&&!referenceSources.has(event.source_id)&&CatalogWorkspace.matchEvent(row,event,mappedCatalogEventForScheduleEvent(event)));
}
function catalogBrowserDetail(row,{showEvents=true}={}){
 const event=row.event||{};const path=[row.sport,row.group.confederation,row.group.country,row.group.governing_body,event.category].filter(Boolean).join(' › ');
 const people=catalogBrowserU18();const linked=people.filter(x=>CatalogWorkspace.u18Placement(x,CATALOG_BROWSER_ROWS).leagueId===row.id);
 const sportPeople=people.filter(x=>CatalogWorkspace.u18Placement(x,CATALOG_BROWSER_ROWS).sport===row.sport);
 const events=catalogBrowserEvents(row);const children=event.coverage_children||[];
 const seasonBlock=e=>{
  const status=CatalogWorkspace.season(e,todayKey(),DATA.global?.sources||[]);
  const confirmed=e.season_start_date&&e.season_end_date;
  const description=confirmed?`${e.season_start_date} – ${e.season_end_date}`:e.season_window||e.season_basis||'Season dates not confirmed';
  const progress=seasonProgressHtml(e,mappedSeasonStatus(e));
  return `<div><span class="catalog-season-tag ${status}">${catalogSeasonLabel(status)}</span><p>${esc(description)}${!confirmed&&e.season_start?' · Recurring window; current season dates unconfirmed.':''}${priorEditionWindow(e)?' · Prior edition; current season unconfirmed.':''}</p>${progress}${progress?'<div class="row-meta">Elapsed time in the saved season window.</div>':''}</div>`;
 };
 const eventCards=events.map(e=>{const when=CatalogWorkspace.eventDate(e);const source=(TODAY_MODEL?.global?.sources||[]).find(x=>x.id===e.source_id)||{};const alerts=(TODAY_MODEL?.windowCards||[]).filter(c=>c.key==='event|'+e.id||(c.event===e.name&&c.start_time===e.start_time&&c.sport===e.sport));return `<li><b>${esc(e.name)}</b>${alerts.map(c=>`<div class="catalog-detail-rules"><b>${esc(c.type)}</b><p>${esc(c.reason)}</p></div>`).join('')}<time>${esc(when.date)} · ${e.schedule_time_conflict?'Time requires review':esc(when.time)}</time>${e.source_stale?'<span class="catalog-restriction-tag">Saved schedule · verify current details</span>':''}${!e.date_only&&/[ZT]/.test(e.start_time||'')&&Date.parse(e.start_time)<Date.now()?'<div class="row-meta">Scheduled start has passed; event status may need checking.</div>':''}${e.requires_bout_review?'<div>Bout and age review required</div>':''}${e.source_id==='jolpica-f1'?f1EventHtml(e):''}${oddsObservationHtml(e)}<details><summary>Event source</summary><div>${esc(e.source_id||'Source not recorded')} · Last observed: ${esc(e.observed_at||e.checked_at||source.checked_at||'Not recorded')}</div>${/^https?:\/\//.test(e.source_url||'')?`<a href="${esc(e.source_url)}" target="_blank" rel="noopener noreferrer">Source ↗</a>`:''}</details></li>`;});
 const section=(DATA.catalog?.sections||[]).find(x=>x.sport===row.sport);
 const olympics=row.kind==='olympic'?renderOlympicsCatalog(section,(DATA.seasonMap.sports||[]).find(x=>x.sport==='Olympics'),row.name.toLowerCase(),'all'):'';
 return `<div class="catalog-path">${esc(path)}</div><h3>${row.event?.key?catalogEventNameHtml(event):esc(row.name)}</h3>${row.aliases.map(x=>`<div class="catalog-alias"><b>${esc(catalogAliasLabel(x))}:</b> ${esc(x.name)}${x.scope?` · ${esc(x.scope)}`:''}</div>`).join('')}${row.restrictions.length?`<div class="catalog-detail-rules"><b>Restrictions &amp; special conditions</b>${row.restrictions.map(x=>`<p>${esc(x)}</p>`).join('')}</div>`:'<p class="row-meta">Catalog-wide restrictions still apply.</p>'}${row.notes.map(x=>`<p>${esc(x)}</p>`).join('')}<h4>Season</h4>${seasonBlock(event)}${children.map(child=>`<div><h4>${esc(child.label||child.catalog_event||child.key)}</h4>${seasonBlock(child)}</div>`).join('')}${showEvents?`<h4>Today &amp; upcoming events · Central time</h4>${events.length?`<ul class="catalog-detail-events">${eventCards.slice(0,5).join('')}</ul>${events.length>5?`<details><summary>Show ${events.length-5} more events</summary><ul class="catalog-detail-events">${eventCards.slice(5).join('')}</ul></details>`:''}`:'<p>No usable upcoming schedule is available in this review window. Season information above is separate.</p>'}`:''}${row.id==='motorsports-intl-f1'?f1SourceHtml():''}${tourCalendarHtml(event)}${olympics}<h4>Known U18</h4>${linked.map(catalogBrowserAthlete).join('')||'<p>No verified league-specific U18 information. This does not confirm there are no U18 participants.</p>'}<button type="button" class="catalog-plain-link" data-browser-u18="${esc(row.sport)}">View sport-level age evidence (${sportPeople.length})</button><details><summary>Sources &amp; last verified</summary><p>Season last verified: ${esc(u18LastVerifiedLabel(event.last_verified))}</p>${event.season_source_url&&/^https?:\/\//.test(event.season_source_url)?`<a href="${esc(event.season_source_url)}" target="_blank" rel="noopener noreferrer">Season source ↗</a>`:''}${row.aliases.map(x=>`<p>${esc(x.name)}${x.scope_note?` — ${esc(x.scope_note)}`:''}${/^https?:\/\//.test(x.evidence_url||'')?` · <a href="${esc(x.evidence_url)}" target="_blank" rel="noopener noreferrer">Alias evidence</a>`:''}</p>`).join('')}${catalogEntryHealthHtml(row.sport,[row.name,row.id],eventSourceIds(event))}</details><details><summary>Catalog-wide standards</summary>${catalogWideStandards(DATA.catalog||{}).general.map(x=>`<p>${esc(x)}</p>`).join('')}<button type="button" class="catalog-plain-link" data-browser-panel="restrictions">Open all restrictions &amp; integrity standards</button></details><details><summary>Original catalog wording · ${esc(row.sport)}</summary>${(section?.lines||[]).map(x=>`<div>${esc(x)}</div>`).join('')}</details>`;
}

function catalogBoardDate(event){
 if(event.date_only||/^\d{4}-\d{2}-\d{2}$/.test(event.start_time||''))return String(event.start_time).slice(0,10);
 if(!/(?:Z|[+-]\d{2}:\d{2})$/.test(event.start_time||'')||!Number.isFinite(Date.parse(event.start_time)))return '';
 return new Intl.DateTimeFormat('en-CA',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(event.start_time));
}
function catalogBoardRows(rows,date='all'){
 const model=TODAY_MODEL||buildTodayModel(),referenceSources=new Set((model.global.sources||[]).filter(x=>x.source_type==='official-event-window').map(x=>x.id));
 const result=[];
 for(const event of model.events){
  if(event.reference_only||referenceSources.has(event.source_id))continue;
  const day=catalogBoardDate(event);
  if(date==='today'&&day!==todayKey())continue;
  if(date==='upcoming'&&(!day||day<todayKey()||(day===todayKey()&&!event.date_only&&Number.isFinite(Date.parse(event.start_time))&&Date.parse(event.start_time)<Date.now())))continue;
  const mapped=mappedCatalogEventForScheduleEvent(event),matches=rows.filter(row=>CatalogWorkspace.matchEvent(row,event,mapped));
  // A board row requires exactly one catalog parent. Similar labels never establish approval.
  if(matches.length!==1)continue;
  result.push({event,row:matches[0]});
 }
 return result.sort((a,b)=>String(a.event.start_time||'9999').localeCompare(String(b.event.start_time||'9999'))||a.event.name.localeCompare(b.event.name));
}
function catalogBoardAlerts(event){
 return (TODAY_MODEL?.windowCards||[]).filter(c=>c.key==='event|'+event.id||(c.event===event.name&&c.start_time===event.start_time&&c.sport===event.sport));
}
function catalogBoardFlags(event,row){
 const alerts=catalogBoardAlerts(event),flags=[];
 alerts.forEach(c=>flags.push(`<span class="board-flag ${c.status==='RED'||c.color==='red'?'red':'amber'}">${esc(c.type||'Review required')}</span>`));
 if(event.source_stale)flags.push('<span class="board-flag amber">Saved schedule</span>');
 if(event.schedule_time_conflict)flags.push('<span class="board-flag amber">Verify time</span>');
 if(event.requires_bout_review)flags.push('<span class="board-flag amber">Bout &amp; age review</span>');
 if(row.restrictions.length)flags.push('<span class="board-flag amber">Restrictions</span>');
 return flags.join('')||'<span class="board-neutral">Check offerings</span>';
}
function renderCatalogBoard(selected){
 const state=CATALOG_BROWSER,rows=state.entry==='all'||state.entry==='u18'?selected:selected.filter(x=>x.id===state.entry);
 CATALOG_BOARD_EVENTS=catalogBoardRows(rows,state.date);
 const eventKey=e=>String(e.id||[e.source_id,e.name,e.start_time].join('|'));
 let picked=CATALOG_BOARD_EVENTS.find(x=>eventKey(x.event)===state.event);
 if(!picked)state.event=null;
 const selectedRow=selected.find(x=>x.id===state.entry);
 const title=state.entry==='all'||state.entry==='u18'?'All competitions':selectedRow?.name||'Selected competition';
 document.getElementById('catalogEvents').innerHTML=`<div class="catalog-event-summary"><b>${esc(title)}</b><span>${CATALOG_BOARD_EVENTS.length} published event${CATALOG_BOARD_EVENTS.length===1?'':'s'} · Central time</span></div>`+(CATALOG_BOARD_EVENTS.length?`<table class="catalog-event-table"><thead><tr><th>Start · Central</th><th>Event / competition</th><th>Review</th><th><span class="sr-only">Details</span></th></tr></thead><tbody>${CATALOG_BOARD_EVENTS.map(({event,row},i)=>{const when=CatalogWorkspace.eventDate(event),passed=!event.date_only&&/(?:Z|[+-]\d{2}:\d{2})$/.test(event.start_time||'')&&Date.parse(event.start_time)<Date.now();return `<tr class="${state.event===eventKey(event)?'selected':''}"><td><time>${esc(when.date)}<strong>${event.schedule_time_conflict?'Verify time':esc(when.time)}</strong></time>${passed?'<span class="board-neutral">Start passed</span>':''}</td><td><button class="catalog-event-name" type="button" data-browser-event="${i}" aria-label="Review ${esc(event.name)}">${esc(event.name)}</button><div class="board-competition">${esc(row.name)}</div></td><td>${catalogBoardFlags(event,row)}</td><td><button class="board-open" type="button" data-browser-event="${i}" aria-label="Open details for ${esc(event.name)}">›</button></td></tr>`;}).join('')}</tbody></table>`:`<div class="catalog-board-empty"><h3>No published events in this view</h3><p>${state.date==='today'?'No matching events are available for today. Try Review window.':'The selected competition has no usable event schedule in the loaded review window.'}</p><p>The approved catalog and its restrictions remain available in Review details. An empty schedule does not confirm that no events are taking place.</p></div>`);
 const parking=document.getElementById('catalogAgeParking');
 if(parking)['catalogFootballAge','catalogBasketballAge'].forEach(id=>{const panel=document.getElementById(id);if(panel)parking.append(panel);});
 const detail=document.getElementById('catalogDetail');
 if(state.entry==='u18'){
  detail.innerHTML=catalogBrowserSportDetails(state.sport);
  const panel=state.sport==='NCAA Football'?'catalogFootballAge':state.sport==='NCAA Basketball'?'catalogBasketballAge':null;
  if(panel&&document.getElementById(panel))detail.append(document.getElementById(panel));
 }else{
  const row=picked?.row||selectedRow;
  detail.innerHTML=(picked?`<div class="board-selected-event"><div class="eyebrow">Selected event</div><h3>${esc(picked.event.name)}</h3><p>${esc(CatalogWorkspace.eventDate(picked.event).date)} · ${picked.event.schedule_time_conflict?'Time requires review':esc(CatalogWorkspace.eventDate(picked.event).time)}</p>${catalogBoardFlags(picked.event,picked.row)}${catalogBoardAlerts(picked.event).map(c=>`<div class="catalog-detail-rules"><b>${esc(c.type)}</b><p>${esc(c.reason)}</p></div>`).join('')}<p class="row-meta">Source: ${esc(picked.event.source_id||'Not recorded')}<br>Last observed: ${esc(picked.event.observed_at||picked.event.checked_at||(TODAY_MODEL?.global?.sources||[]).find(x=>x.id===picked.event.source_id)?.checked_at||'Not recorded')}</p>${/^https?:\/\//.test(picked.event.source_url||'')?`<a href="${esc(picked.event.source_url)}" target="_blank" rel="noopener noreferrer">Open event source ↗</a>`:''}${picked.event.source_id==='jolpica-f1'?f1EventHtml(picked.event):''}${oddsObservationHtml(picked.event)}</div>`:'')+(row?catalogBrowserDetail(row,{showEvents:false}):`<div class="board-review-intro"><div class="eyebrow">${esc(state.sport)}</div><h3>Select an event or competition</h3><p>Its restrictions, season information, known U18 evidence and source details will appear here.</p><button type="button" class="catalog-plain-link" data-browser-u18="${esc(state.sport)}">Open sport notes &amp; known U18</button></div>`);
 }
}
function renderCatalogWorkspace(){
 if(typeof CatalogWorkspace==='undefined'||!document.getElementById('catalogBrowser'))return;
 CATALOG_BROWSER_ROWS=CatalogWorkspace.build({catalog:DATA.catalog,seasonMap:DATA.seasonMap,identities:DATA.identities,today:todayKey(),sources:DATA.global?.sources||[],notes:catalogSportNotes(DATA.catalog||{}),role:(line,sport,country)=>((DATA.seasonMap?.catalog_role_overrides||[]).find(x=>x.sport===sport&&x.line===String(line).trim()&&(!x.country||x.country===country))?.role||catalogLineRole(line))});
 const sportsNode=document.getElementById('catalogSports'),leaguesNode=document.getElementById('catalogLeagues'),sportScroll=sportsNode.scrollTop,leagueScroll=leaguesNode.scrollLeft;
 const state=CATALOG_BROWSER,query=document.getElementById('catalogSearch').value||'',base={query,restricted:state.restricted},counts=CatalogWorkspace.counts(CATALOG_BROWSER_ROWS,base);
 document.getElementById('catalogSeasonButtons').innerHTML=[['all','All'],['in','In season'],['unknown','Dates unconfirmed'],['out','Out of season']].map(([key,label])=>`<button type="button" data-browser-season="${key}" aria-pressed="${state.status===key}">${label} (${counts[key]})</button>`).join('');
 const visible=CatalogWorkspace.filter(CATALOG_BROWSER_ROWS,{...base,status:state.status}),known=catalogBrowserU18();
 const sports=[...new Set([...(DATA.catalog?.sections||[]).map(x=>x.sport),...known.map(x=>CatalogWorkspace.u18Placement(x,CATALOG_BROWSER_ROWS).sport)])];
 if(!state.sport||!sports.includes(state.sport))state.sport=sports.includes('Football')?'Football':sports[0];
 if(query&&visible.length&&!visible.some(x=>x.sport===state.sport)){state.sport=visible[0].sport;state.entry='all';state.event=null;}
 sportsNode.innerHTML=sports.map(s=>{const count=visible.filter(x=>x.sport===s).length;return `<button type="button" class="catalog-select" data-browser-sport="${esc(s)}" aria-pressed="${state.sport===s}"><span>${esc(s)}</span><small>${count}</small></button>`;}).join('');
 const selected=visible.filter(x=>x.sport===state.sport);
 if(!['all','u18'].includes(state.entry)&&!selected.some(x=>x.id===state.entry)){state.entry='all';state.event=null;}
 if(query&&selected.length===1&&state.entry==='all')state.entry=selected[0].id;
 document.getElementById('catalogResultCount').textContent=`${visible.length} of ${CATALOG_BROWSER_ROWS.length} catalog entries · Published schedules support review; verify actual sportsbook offerings.`;
 document.getElementById('catalogVersionBadge').textContent=`Catalog ${DATA.catalog?.menu_version||'version unavailable'}`;
 document.getElementById('catalogSportTitle').textContent=state.sport;
 // Search and the full dropdown expose every competition; tabs stay short even for large sports.
 const eventCounts=new Map();catalogBoardRows(selected).forEach(x=>eventCounts.set(x.row.id,(eventCounts.get(x.row.id)||0)+1));
 const ranked=[...selected].sort((a,b)=>(eventCounts.get(b.id)||0)-(eventCounts.get(a.id)||0));
 const tabs=ranked.slice(0,8);const current=selected.find(x=>x.id===state.entry);if(current&&!tabs.includes(current))tabs.push(current);
 leaguesNode.innerHTML=`<button type="button" class="catalog-select" data-browser-entry="all" aria-pressed="${state.entry==='all'}">All competitions</button>`+tabs.map(row=>`<button type="button" class="catalog-select" data-browser-entry="${esc(row.id)}" aria-pressed="${state.entry===row.id}" title="${esc(row.name)}">${esc(row.name)}</button>`).join('');
 const select=document.getElementById('catalogLeagueSelect');select.innerHTML='<option value="all">All competitions ('+selected.length+')</option>'+selected.map(row=>`<option value="${esc(row.id)}">${esc([row.group.country,row.name].filter(Boolean).join(' · '))}</option>`).join('');select.value=state.entry==='u18'?'all':state.entry;
 document.querySelectorAll('[data-browser-date]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.browserDate===state.date)));
 renderCatalogBoard(selected);
 document.getElementById('catalogRestrictionsOnly').checked=state.restricted;
 sportsNode.scrollTop=sportScroll;leaguesNode.scrollLeft=leagueScroll;
}
function installCatalogWorkspace(){
 document.getElementById('catalogBrowserControls').addEventListener('click',e=>{
  const button=e.target.closest('[data-browser-season]');if(button){CATALOG_BROWSER.status=button.dataset.browserSeason;renderCatalogWorkspace();}
  if(e.target.closest('#catalogReset')){Object.assign(CATALOG_BROWSER,{entry:'all',event:null,status:'all',restricted:false,date:'all'});document.getElementById('catalogSearch').value='';document.getElementById('catalogSeason').value='all';CATALOG_HEALTH_FILTER='all';renderCatalog();}
 });
 document.getElementById('catalogRestrictionsOnly').addEventListener('change',e=>{CATALOG_BROWSER.restricted=e.target.checked;renderCatalogWorkspace();});
 document.getElementById('catalogLeagueSelect').addEventListener('change',e=>{CATALOG_BROWSER.entry=e.target.value;CATALOG_BROWSER.event=null;renderCatalogWorkspace();});
 document.getElementById('catalogBrowser').addEventListener('click',e=>{
  const sport=e.target.closest('[data-browser-sport]'),entry=e.target.closest('[data-browser-entry]'),u18=e.target.closest('[data-browser-u18]'),panel=e.target.closest('[data-browser-panel]'),date=e.target.closest('[data-browser-date]'),event=e.target.closest('[data-browser-event]');
  if(panel){document.querySelector(`button[data-panel="${panel.dataset.browserPanel}"]`)?.click();return;}
  if(sport){CATALOG_BROWSER.sport=sport.dataset.browserSport;CATALOG_BROWSER.entry='all';CATALOG_BROWSER.event=null;}
  else if(entry){CATALOG_BROWSER.entry=entry.dataset.browserEntry;CATALOG_BROWSER.event=null;}
  else if(u18||e.target.closest('#catalogSportEvidence')){if(u18)CATALOG_BROWSER.sport=u18.dataset.browserU18;CATALOG_BROWSER.entry='u18';CATALOG_BROWSER.event=null;}
  else if(date)CATALOG_BROWSER.date=date.dataset.browserDate;
  else if(event){const item=CATALOG_BOARD_EVENTS[Number(event.dataset.browserEvent)];if(!item)return;CATALOG_BROWSER.event=String(item.event.id||[item.event.source_id,item.event.name,item.event.start_time].join('|'));if(CATALOG_BROWSER.entry==='u18')CATALOG_BROWSER.entry='all';}
  else return;
  renderCatalogWorkspace();document.getElementById('catalogDetail').scrollTop=0;
 });
}
