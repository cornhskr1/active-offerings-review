/* UI-only bridge to existing published data, evidence renderers and review model. */
let CATALOG_BROWSER={sport:'All sports',entry:'all',event:null,status:'all',restricted:false,date:'all',mode:'events',attention:false,details:false,olympicEdition:null};

// Decorative, local SVGs: sport names remain the accessible labels.
function catalogSportIcon(sport){
 const ball='<circle cx="12" cy="12" r="9"/>';
 const icons={
  football:'<g transform="rotate(-35 12 12)"><path d="M2 12C5 3 19 3 22 12c-3 9-17 9-20 0Z"/><path d="M8 12h8M10 10v4m2-4v4m2-4v4M5 7.5v9m14-9v9"/></g>',
  basketball:ball+'<path d="M3 12h18M12 3v18M5.7 5.7c4 3.3 4 9.3 0 12.6M18.3 5.7c-4 3.3-4 9.3 0 12.6"/>',
  baseball:ball+'<path d="M6.5 4.9c5 4 5 10.2 0 14.2m11-14.2c-5 4-5 10.2 0 14.2M7.5 8l2-1m-1 5h2m-3 4 2 1m7-9-2-1m1 5h-2m3 4-2 1"/>',
  soccer:ball+'<path d="m12 7 4.8 3.5-1.8 5.6H9l-1.8-5.6Z" fill="currentColor" stroke-width=".5"/><path d="M12 7V3m4.8 7.5 3.8-1.3M15 16.1l2.3 3.2M9 16.1l-2.3 3.2M7.2 10.5 3.4 9.2"/>',
  tennis:ball+'<g transform="rotate(35 12 12)"><path d="M5.6 5.6c5.5 3.5 5.5 9.3 0 12.8M18.4 5.6c-5.5 3.5-5.5 9.3 0 12.8"/></g>',
  tabletennis:'<path d="M6 3c4-2 10 0 11 4 2 4-1 8-5 9l-2 5-3-1 1-5C2 13 1 7 6 3Z" fill="currentColor" fill-opacity=".12"/><path d="m4 12 10-8M8 15l4 1"/><circle cx="19" cy="19" r="3" fill="currentColor" stroke="none"/>',
  volleyball:ball+'<path d="m12 12 8-4m-8 4-1-9m1 9-7 6M6 5c0 6 2 10 6 14m6-14c-6 3-9 7-10 14m13-5c-7-1-12-4-14-8"/>',
  hockey:'<ellipse cx="12" cy="10" rx="9" ry="4"/><path d="M3 10v5c0 5 18 5 18 0v-5M6 13v4m4-3v4m4-4v4m4-5v4"/>',
  golf:'<path d="M6 20V3l12 4-12 4"/><ellipse cx="12" cy="20" rx="9" ry="2"/>',
  racing:'<path d="M4 22V3c6-4 10 4 16 0v11c-6 4-10-4-16 0"/><path d="M8 2v6l4 1V4m4 1v6l4-1M4 8l4-1v7m4-5v5l4 2v-5"/>',
  boxing:'<path d="M7 17c-2-1-4-3-4-6V8c0-2 3-2 3 0V5c0-4 12-4 12 1v4c3-1 4 3 1 6l-2 2v3H7Z"/><path d="M7 17h10M7 21h10"/>',
  cycling:'<circle cx="5" cy="16" r="4"/><circle cx="19" cy="16" r="4"/><path d="m5 16 5-9 9 9H5l8-5m-5-4h5m2-3h3l1 12"/>',
  swimming:'<circle cx="15" cy="6" r="2"/><path d="m4 12 5-6 5 5 6 1M2 16q3-3 6 0t6 0t8 0M2 21q3-3 6 0t6 0t8 0"/>',
  athletics:'<circle cx="15" cy="4" r="2"/><path d="m7 21 5-8 3 3 4 1M3 15l6-1 3-7 4 4 4-1M6 7l4-2 3 2"/>',
  esports:'<path d="M8 7h8c5 0 7 12 3 12l-4-4H9l-4 4C1 19 3 7 8 7Z"/><path d="M8 9v5m-2-2h4m6-2h.01M18 13h.01"/>',
  darts:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><path d="m12 12 8-8m-3 0 2-2 1 2 2 1-2 2"/>',
  trophy:'<path d="M7 3h10v6c0 7-10 7-10 0ZM7 5H3v3c0 4 4 4 5 4m9-7h4v3c0 4-4 4-5 4M12 14v6m-5 1h10"/>',
  bowling:'<circle cx="12" cy="12" r="9"/><circle cx="10" cy="7" r="1"/><circle cx="14" cy="8" r="1"/><circle cx="11" cy="11" r="1"/>',
  cricket:'<path d="m15 2-5 7m-2-1 5 4-7 9-5-4Z"/><circle cx="18" cy="17" r="4"/><path d="m16 14 4 6"/>',
  lacrosse:'<path d="m3 22 9-11M10 3c4-4 11-2 11 2 0 7-6 11-10 8-3-2-3-6-1-10Z"/><path d="m10 5 8 6m-8-2 9-5m-5-2 2 10"/>',
  surf:'<ellipse cx="12" cy="10" rx="4" ry="9" transform="rotate(35 12 10)"/><path d="M2 20q3-3 6 0t6 0t8 0"/>',
 };
 const name=String(sport).toLowerCase();
 const type=/basketball/.test(name)?'basketball':/baseball|softball/.test(name)?'baseball':/soccer/.test(name)?'soccer':/volleyball|water polo/.test(name)?'volleyball':/football|aussie|rugby/.test(name)?'football':/table tennis|ping.?pong/.test(name)?'tabletennis':/tennis/.test(name)?'tennis':/hockey/.test(name)?'hockey':/golf/.test(name)?'golf':/motorsport/.test(name)?'racing':/boxing|combat|wrestling/.test(name)?'boxing':/cycling/.test(name)?'cycling':/swim/.test(name)?'swimming':/track/.test(name)?'athletics':/esport/.test(name)?'esports':/dart/.test(name)?'darts':/bowling/.test(name)?'bowling':/cricket/.test(name)?'cricket':/lacrosse/.test(name)?'lacrosse':/surf/.test(name)?'surf':'trophy';
 return `<svg class="sport-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${icons[type]}</svg>`;
}
function catalogBoardDayOffset(offset){
 const day=new Date(todayKey()+'T12:00:00Z');day.setUTCDate(day.getUTCDate()+offset);return day.toISOString().slice(0,10);
}

function catalogObservation(event){
 const source=(TODAY_MODEL?.global?.sources||[]).find(x=>x.id===event.source_id)||{};
 const checked=event.observed_at||event.checked_at||source.checked_at;
 return checked&&Number.isFinite(Date.parse(checked))?checked:null;
}
function catalogObservationLabel(event){
 const checked=catalogObservation(event);
 return checked?`Observed ${esc(fmtDateTime(checked))}`:'Observation date unavailable';
}
function catalogReliabilityHtml(rows){
 // Use the full review window, independently of date/attention display filters.
 const entries=CATALOG_BROWSER.entry;
 const scope=entries==='all'||entries==='u18'?rows:rows.filter(row=>row.id===entries);
 const events=catalogBoardRows(scope);
 const covered=new Set(events.map(x=>x.row.id)).size;
 const saved=events.filter(x=>x.event.source_stale||x.event.collection_paused||!catalogObservation(x.event)).length;
 const held=DATA.oddsEvents?.collector_state?.halted===true||DATA.oddsEvents?.coverage?.collection_halted===true;
 return `<div><b>Schedule coverage</b><span>${covered} of ${scope.length} catalog entries have events in the loaded review window</span></div><div><b>${saved?'Verify saved observations':'Coverage is limited'}</b><span>${saved?`${saved} event${saved===1?'':'s'} flagged as saved, paused, or missing an observation date. `:''}${held?'A schedule provider is paused. ':''}Unlisted events may still be taking place.</span></div><button type="button" class="catalog-plain-link" id="hubEvidenceButton">View evidence &amp; gaps ↓</button>`;
}

function catalogBoardNeedsAttention(event,row){
 return Boolean(catalogBoardAlerts(event).length||event.source_stale||event.schedule_time_conflict||event.requires_bout_review||row.restrictions.length);
}
function catalogSetDetails(visible){
 CATALOG_BROWSER.details=visible;
 document.getElementById('catalogBrowser').classList.toggle('details-hidden',!visible);
 document.getElementById('catalogReviewColumn').hidden=!visible;
 const toggle=document.getElementById('catalogDetailToggle');toggle.textContent=visible?'Hide details':'Show details';toggle.setAttribute('aria-expanded',String(visible));
}

let CATALOG_BOARD_EVENTS=[];
let CATALOG_BROWSER_ROWS=[];
const catalogSeasonLabel=s=>({in:'In season',out:'Out of season',unknown:'Undetermined'}[s]||'Undetermined');
function catalogCompetitionOptions(rows,sport){
 const groups=new Map();
 for(const row of rows){const key=sport==='All sports'?row.sport:(row.group.country||row.group.governing_body||sport);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}
 return `<option value="all">All competitions (${rows.length})</option>`+[...groups].map(([label,entries])=>`<optgroup label="${esc(label)}">${entries.map(row=>`<option value="${esc(row.id)}">${esc(row.name)}</option>`).join('')}</optgroup>`).join('');
}
function catalogAliasPreview(row){
 const names=[...new Set((row.aliases||[]).map(x=>x.name).filter(x=>x&&x!==row.name))];
 return names.length?`<span class="catalog-alias-preview">Also listed as ${names.slice(0,2).map(esc).join(' · ')}${names.length>2?` · +${names.length-2} more`:''}</span>`:'';
}
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
 return `<div class="catalog-path">${esc(path)}</div><h3>${row.event?.key?catalogEventNameHtml(event):esc(row.name)}</h3>${row.aliases.length?'<h4>Names &amp; aliases</h4>':''}${row.aliases.map(x=>`<div class="catalog-alias"><b>${esc(catalogAliasLabel(x))}:</b> ${esc(x.name)}${x.scope?` · ${esc(x.scope)}`:''}</div>`).join('')}${row.restrictions.length?`<div class="catalog-detail-rules"><b>Restrictions &amp; special conditions</b>${row.restrictions.map(x=>`<p>${esc(x)}</p>`).join('')}</div>`:'<p class="row-meta">Catalog-wide restrictions still apply.</p>'}${row.notes.length?`<details><summary>Catalog context</summary>${row.notes.map(x=>`<p>${esc(x)}</p>`).join('')}</details>`:''}<h4>Season</h4>${seasonBlock(event)}${children.map(child=>`<div><h4>${esc(child.label||child.catalog_event||child.key)}</h4>${seasonBlock(child)}</div>`).join('')}${showEvents?`<h4>Today &amp; upcoming events · Central time</h4>${events.length?`<ul class="catalog-detail-events">${eventCards.slice(0,5).join('')}</ul>${events.length>5?`<details><summary>Show ${events.length-5} more events</summary><ul class="catalog-detail-events">${eventCards.slice(5).join('')}</ul></details>`:''}`:'<p>No usable upcoming schedule is available in this review window. Season information above is separate.</p>'}`:''}${row.id==='motorsports-intl-f1'?f1SourceHtml():''}${tourCalendarHtml(event)}${olympics}<h4>Known U18</h4>${linked.map(catalogBrowserAthlete).join('')||'<p>No verified league-specific U18 information. This does not confirm there are no U18 participants.</p>'}<button type="button" class="catalog-plain-link" data-browser-u18="${esc(row.sport)}">View sport-level age evidence (${sportPeople.length})</button><details><summary>Sources &amp; last verified</summary><p>Season last verified: ${esc(u18LastVerifiedLabel(event.last_verified))}</p>${event.season_source_url&&/^https?:\/\//.test(event.season_source_url)?`<a href="${esc(event.season_source_url)}" target="_blank" rel="noopener noreferrer">Season source ↗</a>`:''}${row.aliases.map(x=>`<p>${esc(x.name)}${x.scope_note?` — ${esc(x.scope_note)}`:''}${/^https?:\/\//.test(x.evidence_url||'')?` · <a href="${esc(x.evidence_url)}" target="_blank" rel="noopener noreferrer">Alias evidence</a>`:''}</p>`).join('')}${catalogEntryHealthHtml(row.sport,[row.name,row.id],eventSourceIds(event))}</details><details><summary>Catalog-wide standards</summary>${catalogWideStandards(DATA.catalog||{}).general.map(x=>`<p>${esc(x)}</p>`).join('')}<button type="button" class="catalog-plain-link" data-browser-panel="restrictions">Open all restrictions &amp; integrity standards</button></details><details><summary>Original catalog wording · ${esc(row.sport)}</summary>${(section?.lines||[]).map(x=>`<div>${esc(x)}</div>`).join('')}</details>`;
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
  if(date==='tomorrow'&&day!==catalogBoardDayOffset(1))continue;
  if(date==='week'&&(!day||day<todayKey()||day>catalogBoardDayOffset(6)))continue;
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
 return flags.join('')||'<span class="board-neutral">Catalog linked</span>';
}

function catalogOlympicEditions(mapping){
 return (mapping?.editions||[]).map(edition=>{
  const games=(DATA[edition.program_data_key]||{}).games||{};
  return {edition,games,start:games.competition_start_date||games.games_start_date||'',end:games.competition_end_date||games.games_end_date||''};
 }).sort((a,b)=>{
  const past=x=>Boolean(x.end&&x.end<todayKey());
  return Number(past(a))-Number(past(b))||(a.start||'9999').localeCompare(b.start||'9999');
 });
}
function catalogOlympicsOverview(query=''){
 const section=(DATA.catalog?.sections||[]).find(x=>x.sport==='Olympics');
 const mapping=(DATA.seasonMap?.sports||[]).find(x=>x.sport==='Olympics');
 if(!section||!mapping)return '<div class="catalog-board-empty"><h3>Olympic program information unavailable</h3><p>Reload published data or consult the published catalog. Approval and scheduling cannot be confirmed from an empty program.</p></div>';
 const editions=catalogOlympicEditions(mapping);
 let selected=editions.find(x=>x.edition.key===CATALOG_BROWSER.olympicEdition)||editions[0];
 if(!selected)return '<div class="catalog-board-empty">No Olympic Games programs are available for review.</div>';
 CATALOG_BROWSER.olympicEdition=selected.edition.key;
 const next=editions.find(x=>x.start&&(!x.end||x.end>=todayKey()));
 const games=editions.map(x=>`<button type="button" class="olympic-games-choice" data-browser-olympics="${esc(x.edition.key)}" aria-pressed="${x===selected}"><span class="eyebrow">${x===next?(x.start<=todayKey()?'Current Games':'Next Games'):'Olympic Games'}</span><b>${esc(x.games.edition||x.edition.label)}</b><span>${esc(olympicDateLabel(x.start,x.end))}</span><small>${x.games.schedule_status==='detailed-schedule-pending'?'Discipline dates pending':x.start?'Published competition window':'Program mapping pending'}</small></button>`).join('');
 const program=renderOlympicsCatalog(section,mapping,query.trim().toLowerCase(),'all',{workspace:true,editionKey:selected.edition.key});
 return `<div class="olympic-workspace"><div class="olympic-workspace-intro"><div><div class="eyebrow">Olympic planning &amp; review</div><h3>Upcoming Games &amp; approval status</h3><p>Compare the official program with the NRGC catalog. Open a status group for discipline dates, restrictions, and review notes.</p></div><span class="olympic-verified">Catalog mapping last reviewed<br><b>${esc(selected.edition.last_verified||'Not recorded')}</b></span></div><div class="olympic-games-choices" role="group" aria-label="Choose Olympic Games">${games}</div>${program||'<div class="catalog-board-empty"><h3>No matching Olympic disciplines</h3><p>Try another Games edition or clear the search to see its complete program.</p></div>'}<details class="olympic-catalog-wording"><summary>Original Olympic catalog wording</summary>${section.lines.map(x=>`<div>${esc(x)}</div>`).join('')}</details></div>`;
}

function renderCatalogBoard(selected){
 const state=CATALOG_BROWSER;
 if(state.sport==='Olympics'){
  CATALOG_BOARD_EVENTS=[];state.event=null;
  document.getElementById('catalogEvents').innerHTML=catalogOlympicsOverview(document.getElementById('catalogSearch').value);
  document.getElementById('catalogDetail').innerHTML=state.entry==='u18'?catalogBrowserSportDetails('Olympics'):'';
  catalogSetDetails(state.entry==='u18');
  document.getElementById('catalogDetailToggle').hidden=state.entry!=='u18';
  return;
 }
 const rows=state.entry==='all'||state.entry==='u18'?selected:selected.filter(x=>x.id===state.entry);
 CATALOG_BOARD_EVENTS=catalogBoardRows(rows,state.date).filter(x=>!state.attention||catalogBoardNeedsAttention(x.event,x.row));
 const eventKey=e=>String(e.id||[e.source_id,e.name,e.start_time].join('|'));
 let picked=CATALOG_BOARD_EVENTS.find(x=>eventKey(x.event)===state.event);
 if(!picked)state.event=null;
 const selectedRow=selected.find(x=>x.id===state.entry);
 const title=state.entry==='all'||state.entry==='u18'?(state.sport==='All sports'?'Across all sports':'All '+state.sport+' competitions'):selectedRow?.name||'Selected competition';
 document.getElementById('catalogEvents').innerHTML=`<div class="catalog-event-summary"><b>${esc(title)}</b><span>${CATALOG_BOARD_EVENTS.length} published event${CATALOG_BOARD_EVENTS.length===1?'':'s'} · Central time</span></div>`+(CATALOG_BOARD_EVENTS.length?`<table class="catalog-event-table"><thead><tr><th>Start · Central</th><th>Event / competition</th><th>Review</th><th><span class="sr-only">Details</span></th></tr></thead><tbody>${CATALOG_BOARD_EVENTS.map(({event,row},i)=>{const when=CatalogWorkspace.eventDate(event),passed=!event.date_only&&/(?:Z|[+-]\d{2}:\d{2})$/.test(event.start_time||'')&&Date.parse(event.start_time)<Date.now();return `<tr data-browser-event="${i}" class="${state.event===eventKey(event)?'selected':''}"><td><time>${esc(when.date)}<strong>${event.schedule_time_conflict?'Verify time':esc(when.time)}</strong></time>${passed?'<span class="board-neutral">Start passed</span>':''}</td><td><button class="catalog-event-name" type="button" data-browser-event="${i}" aria-label="Review ${esc(event.name)}">${esc(event.name)}</button><div class="board-competition">${esc(row.sport)} · ${esc(row.name)}</div><div class="board-observed">${catalogObservationLabel(event)}</div></td><td>${catalogBoardFlags(event,row)}</td><td><button class="board-open" type="button" data-browser-event="${i}" aria-label="Open details for ${esc(event.name)}">›</button></td></tr>`;}).join('')}</tbody></table>`:`<div class="catalog-board-empty"><h3>No published events in this view</h3><p>${state.attention||state.date!=='all'?'No events match the date and review filters. Try Review window or clear Needs attention.':'The selected competition has no usable event schedule in the loaded review window.'}</p><p>Switch to Approved catalog to see entries and their restrictions. An empty schedule does not confirm that no events are taking place.</p></div>`);
 if(state.mode==='catalog'){
  document.getElementById('catalogEvents').innerHTML=`<div class="catalog-event-summary"><b>Approved catalog · ${esc(state.sport)}</b><span>${selected.length} entries</span></div><div class="catalog-entry-list">${selected.map(row=>`<button type="button" class="catalog-entry-card" data-browser-entry="${esc(row.id)}" aria-pressed="${state.entry===row.id}"><span><b>${esc(row.name)}</b>${catalogAliasPreview(row)}<small>${esc([state.sport==='All sports'?row.sport:'',row.group.country,row.group.governing_body].filter(Boolean).join(' · '))}</small>${row.restrictions.length?`<span class="board-flag amber">${row.restrictions.length} restriction${row.restrictions.length===1?'':'s'}</span>`:''}</span><span class="catalog-season-tag ${row.status}">${catalogSeasonLabel(row.status)}</span><span aria-hidden="true">›</span></button>`).join('')||'<div class="catalog-board-empty">No catalog entries match these filters. Clear filters to see the complete list.</div>'}</div>`;
 }
 const parking=document.getElementById('catalogAgeParking');
 if(parking)['catalogFootballAge','catalogBasketballAge'].forEach(id=>{const panel=document.getElementById(id);if(panel)parking.append(panel);});
 const detail=document.getElementById('catalogDetail');
 if(state.entry==='u18'){
  detail.innerHTML=catalogBrowserSportDetails(state.sport);
  const panel=state.sport==='NCAA Football'?'catalogFootballAge':state.sport==='NCAA Basketball'?'catalogBasketballAge':null;
  if(panel&&document.getElementById(panel))detail.append(document.getElementById(panel));
 }else{
  const row=picked?.row||selectedRow;
  detail.innerHTML=(picked?`<div class="board-selected-event"><div class="eyebrow">Selected event</div><h3>${esc(picked.event.name)}</h3><p>${esc(CatalogWorkspace.eventDate(picked.event).date)} · ${picked.event.schedule_time_conflict?'Time requires review':esc(CatalogWorkspace.eventDate(picked.event).time)}</p>${catalogBoardFlags(picked.event,picked.row)}${catalogBoardAlerts(picked.event).map(c=>`<div class="catalog-detail-rules"><b>${esc(c.type)}</b><p>${esc(c.reason)}</p></div>`).join('')}<details><summary>Event source &amp; observation date</summary><p class="row-meta">Source: ${esc(picked.event.source_id||'Not recorded')}<br>Last observed: ${esc(picked.event.observed_at||picked.event.checked_at||(TODAY_MODEL?.global?.sources||[]).find(x=>x.id===picked.event.source_id)?.checked_at||'Not recorded')}</p>${/^https?:\/\//.test(picked.event.source_url||'')?`<a href="${esc(picked.event.source_url)}" target="_blank" rel="noopener noreferrer">Open event source ↗</a>`:''}</details>${picked.event.source_id==='jolpica-f1'?f1EventHtml(picked.event):''}${oddsObservationHtml(picked.event)}</div>`:'')+(row?catalogBrowserDetail(row,{showEvents:false}):`<div class="board-review-intro"><div class="eyebrow">${esc(state.sport)}</div><h3>Select an event or competition</h3><p>Its restrictions, season information, known U18 evidence and source details will appear here.</p><button type="button" class="catalog-plain-link" data-browser-u18="${esc(state.sport)}">Open sport notes &amp; known U18</button></div>`);
 }
}
function renderCatalogWorkspace(){
 if(typeof CatalogWorkspace==='undefined'||!document.getElementById('catalogBrowser'))return;
 CATALOG_BROWSER_ROWS=CatalogWorkspace.build({catalog:DATA.catalog,seasonMap:DATA.seasonMap,identities:DATA.identities,today:todayKey(),sources:DATA.global?.sources||[],notes:catalogSportNotes(DATA.catalog||{}),role:(line,sport,country)=>((DATA.seasonMap?.catalog_role_overrides||[]).find(x=>x.sport===sport&&x.line===String(line).trim()&&(!x.country||x.country===country))?.role||catalogLineRole(line))});
 const sportsNode=document.getElementById('catalogSports'),leaguesNode=document.getElementById('catalogLeagues'),sportScroll=sportsNode.scrollTop,leagueScroll=leaguesNode.scrollLeft;
 const state=CATALOG_BROWSER,query=document.getElementById('catalogSearch').value||'',base={query:state.sport==='Olympics'?'':query,restricted:state.sport==='Olympics'?false:state.restricted},counts=CatalogWorkspace.counts(CATALOG_BROWSER_ROWS,base);
 document.getElementById('catalogSeasonButtons').innerHTML=[['all','All'],['in','In season'],['unknown','Dates unconfirmed'],['out','Out of season']].map(([key,label])=>`<button type="button" data-browser-season="${key}" aria-pressed="${state.status===key}">${label} (${counts[key]})</button>`).join('');
 const visible=CatalogWorkspace.filter(CATALOG_BROWSER_ROWS,{...base,status:state.sport!=='Olympics'&&state.mode==='catalog'?state.status:'all'}),known=catalogBrowserU18();
 const sports=[...new Set([...(DATA.catalog?.sections||[]).map(x=>x.sport),...known.map(x=>CatalogWorkspace.u18Placement(x,CATALOG_BROWSER_ROWS).sport)])];
 if(!state.sport||!['All sports',...sports].includes(state.sport))state.sport='All sports';
 if(!['All sports','Olympics'].includes(state.sport)&&query&&visible.length&&!visible.some(x=>x.sport===state.sport)){state.sport=visible[0].sport;state.entry='all';state.event=null;}
 const sportButton=s=>{const count=s==='All sports'?visible.length:visible.filter(x=>x.sport===s).length;return `<button type="button" class="catalog-select" data-browser-sport="${esc(s)}" aria-pressed="${state.sport===s}"><span class="catalog-sport-name">${catalogSportIcon(s)}<span>${esc(s)}</span></span><small title="Catalog entries">${count}</small></button>`;};
 const collegeOpen=sportsNode.querySelector('.catalog-college-group')?.open||state.sport.startsWith('NCAA');
 sportsNode.innerHTML=sportButton('All sports')+sports.filter(s=>!s.startsWith('NCAA')).map(sportButton).join('')+`<details class="catalog-college-group" ${collegeOpen?'open':''}><summary>College sports · NCAA</summary>${sports.filter(s=>s.startsWith('NCAA')).map(sportButton).join('')}</details>`;
 const selected=state.sport==='All sports'?visible:visible.filter(x=>x.sport===state.sport);
 if(!['all','u18'].includes(state.entry)&&!selected.some(x=>x.id===state.entry)){state.entry='all';state.event=null;}
 if(query&&selected.length===1&&state.entry==='all')state.entry=selected[0].id;
 document.getElementById('catalogResultCount').textContent=`${visible.length} of ${CATALOG_BROWSER_ROWS.length} catalog entries · Schedule information does not establish event or market approval.`;
 document.getElementById('catalogVersionBadge').textContent=`Catalog ${DATA.catalog?.menu_version||'version unavailable'}`;
 document.getElementById('catalogSportEvidence').hidden=state.sport==='All sports';
 document.getElementById('catalogSportTitle').innerHTML=catalogSportIcon(state.sport)+`<span>${esc(state.sport)}</span>`;
 document.getElementById('catalogSeasonButtons').hidden=state.mode!=='catalog';
 document.getElementById('catalogDateButtons').hidden=state.mode!=='events';
 document.getElementById('catalogEventFilters').hidden=state.mode!=='events';
 document.getElementById('catalogLeagues').hidden=state.mode!=='events';
 document.getElementById('catalogNeedsAttention').checked=state.attention;
 document.querySelectorAll('[data-browser-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.browserMode===state.mode)));
 const olympics=state.sport==='Olympics';
 document.getElementById('catalogReliability').hidden=olympics;
 document.getElementById('catalogReliability').innerHTML=olympics?'':catalogReliabilityHtml(selected);
 document.getElementById('catalogBrowser').classList.toggle('olympic-board',olympics);
 document.querySelector('#catalogBrowserControls .catalog-modes').hidden=olympics;
 document.querySelector('#catalogBrowserControls .catalog-restricted').hidden=olympics;
 document.getElementById('catalogDetailToggle').hidden=false;
 const search=document.getElementById('catalogSearch');
 search.placeholder=olympics?'Search Olympic disciplines or review notes…':'Find a sport, league, or sportsbook alias…';
 search.setAttribute('aria-label',olympics?'Search Olympic program':'Search approved catalog');
 if(olympics){
  document.getElementById('catalogSeasonButtons').hidden=true;
  document.getElementById('catalogResultCount').textContent='Official Games programs compared with the approved catalog. Schedule inclusion does not establish approval.';
 }
 catalogSetDetails(state.details);
 // Search and the full dropdown expose every competition; tabs stay short even for large sports.
 const eventCounts=new Map();catalogBoardRows(selected).forEach(x=>eventCounts.set(x.row.id,(eventCounts.get(x.row.id)||0)+1));
 const ranked=[...selected].sort((a,b)=>(eventCounts.get(b.id)||0)-(eventCounts.get(a.id)||0));
 const tabs=state.sport==='All sports'?[]:ranked.slice(0,3);const current=selected.find(x=>x.id===state.entry);if(current&&!tabs.includes(current))tabs.push(current);
 leaguesNode.innerHTML=`<button type="button" class="catalog-select" data-browser-entry="all" aria-pressed="${state.entry==='all'}">All competitions</button>`+tabs.map(row=>`<button type="button" class="catalog-select" data-browser-entry="${esc(row.id)}" aria-pressed="${state.entry===row.id}" title="${esc(row.name)}">${esc(row.name)}</button>`).join('');
 const select=document.getElementById('catalogLeagueSelect');select.innerHTML=catalogCompetitionOptions(selected,state.sport);select.value=state.entry==='u18'?'all':state.entry;
 document.querySelectorAll('[data-browser-date]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.browserDate===state.date)));
 renderCatalogBoard(selected);
 document.getElementById('catalogRestrictionsOnly').checked=state.restricted;
 sportsNode.scrollTop=sportScroll;leaguesNode.scrollLeft=leagueScroll;
}
function installCatalogWorkspace(){
 document.getElementById('catalogReliability').addEventListener('click',e=>{if(e.target.closest('#hubEvidenceButton')){const details=document.getElementById('hubEvidence');details.open=true;details.scrollIntoView({behavior:'instant',block:'start'});}});
 document.getElementById('catalogBrowserControls').addEventListener('click',e=>{
  const mode=e.target.closest('[data-browser-mode]');if(mode){CATALOG_BROWSER.mode=mode.dataset.browserMode;CATALOG_BROWSER.event=null;renderCatalogWorkspace();}
  const button=e.target.closest('[data-browser-season]');if(button){CATALOG_BROWSER.status=button.dataset.browserSeason;renderCatalogWorkspace();}
  if(e.target.closest('#catalogReset')){Object.assign(CATALOG_BROWSER,{olympicEdition:null,entry:'all',event:null,status:'all',restricted:false,date:'all',attention:false,details:false});document.getElementById('catalogSearch').value='';document.getElementById('catalogSeason').value='all';CATALOG_HEALTH_FILTER='all';renderCatalog();}
 });
 document.getElementById('catalogNeedsAttention').addEventListener('change',e=>{CATALOG_BROWSER.attention=e.target.checked;renderCatalogWorkspace();});
 document.getElementById('catalogDetailToggle').addEventListener('click',()=>catalogSetDetails(!CATALOG_BROWSER.details));
 document.getElementById('catalogRestrictionsOnly').addEventListener('change',e=>{CATALOG_BROWSER.restricted=e.target.checked;renderCatalogWorkspace();});
 document.getElementById('catalogLeagueSelect').addEventListener('change',e=>{CATALOG_BROWSER.entry=e.target.value;CATALOG_BROWSER.event=null;CATALOG_BROWSER.details=true;renderCatalogWorkspace();});
 document.getElementById('catalogBrowser').addEventListener('click',e=>{
  const sport=e.target.closest('[data-browser-sport]'),entry=e.target.closest('[data-browser-entry]'),u18=e.target.closest('[data-browser-u18]'),panel=e.target.closest('[data-browser-panel]'),date=e.target.closest('[data-browser-date]'),event=e.target.closest('[data-browser-event]');
  if(panel){document.querySelector(`button[data-panel="${panel.dataset.browserPanel}"]`)?.click();return;}
  const games=e.target.closest('[data-browser-olympics]');
  if(games){CATALOG_BROWSER.olympicEdition=games.dataset.browserOlympics;renderCatalogWorkspace();document.getElementById('catalogEvents').scrollTop=0;return;}
  if(sport){if(CATALOG_BROWSER.sport==='Olympics'||sport.dataset.browserSport==='Olympics')document.getElementById('catalogSearch').value='';CATALOG_BROWSER.sport=sport.dataset.browserSport;CATALOG_BROWSER.entry='all';CATALOG_BROWSER.event=null;CATALOG_BROWSER.details=false;}
  else if(entry){CATALOG_BROWSER.entry=entry.dataset.browserEntry;CATALOG_BROWSER.event=null;CATALOG_BROWSER.details=true;}
  else if(u18||e.target.closest('#catalogSportEvidence')){if(u18)CATALOG_BROWSER.sport=u18.dataset.browserU18;CATALOG_BROWSER.entry='u18';CATALOG_BROWSER.event=null;CATALOG_BROWSER.details=true;}
  else if(date)CATALOG_BROWSER.date=date.dataset.browserDate;
  else if(event){CATALOG_BROWSER.details=true;const item=CATALOG_BOARD_EVENTS[Number(event.dataset.browserEvent)];if(!item)return;CATALOG_BROWSER.event=String(item.event.id||[item.event.source_id,item.event.name,item.event.start_time].join('|'));if(CATALOG_BROWSER.entry==='u18')CATALOG_BROWSER.entry='all';}
  else return;
  renderCatalogWorkspace();document.getElementById('catalogDetail').scrollTop=0;
 });
}
