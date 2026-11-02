/* UI-only bridge to existing published data, evidence renderers and review model. */
let CATALOG_BROWSER={sport:null,entry:null,status:'all',restricted:false};
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
function catalogBrowserDetail(row){
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
 return `<div class="catalog-path">${esc(path)}</div><h3>${row.event?.key?catalogEventNameHtml(event):esc(row.name)}</h3>${row.aliases.map(x=>`<div class="catalog-alias"><b>${esc(catalogAliasLabel(x))}:</b> ${esc(x.name)}${x.scope?` · ${esc(x.scope)}`:''}</div>`).join('')}${row.restrictions.length?`<div class="catalog-detail-rules"><b>Restrictions &amp; special conditions</b>${row.restrictions.map(x=>`<p>${esc(x)}</p>`).join('')}</div>`:'<p class="row-meta">Catalog-wide restrictions still apply.</p>'}${row.notes.map(x=>`<p>${esc(x)}</p>`).join('')}<h4>Season</h4>${seasonBlock(event)}${children.map(child=>`<div><h4>${esc(child.label||child.catalog_event||child.key)}</h4>${seasonBlock(child)}</div>`).join('')}<h4>Today &amp; upcoming events · Central time</h4>${events.length?`<ul class="catalog-detail-events">${eventCards.slice(0,5).join('')}</ul>${events.length>5?`<details><summary>Show ${events.length-5} more events</summary><ul class="catalog-detail-events">${eventCards.slice(5).join('')}</ul></details>`:''}`:'<p>No usable upcoming schedule is available in this review window. Season information above is separate.</p>'}${row.id==='motorsports-intl-f1'?f1SourceHtml():''}${tourCalendarHtml(event)}${olympics}<h4>Known U18</h4>${linked.map(catalogBrowserAthlete).join('')||'<p>No verified league-specific U18 information. This does not confirm there are no U18 participants.</p>'}<button type="button" class="catalog-plain-link" data-browser-u18="${esc(row.sport)}">View sport-level age evidence (${sportPeople.length})</button><details><summary>Sources &amp; last verified</summary><p>Season last verified: ${esc(u18LastVerifiedLabel(event.last_verified))}</p>${event.season_source_url&&/^https?:\/\//.test(event.season_source_url)?`<a href="${esc(event.season_source_url)}" target="_blank" rel="noopener noreferrer">Season source ↗</a>`:''}${row.aliases.map(x=>`<p>${esc(x.name)}${x.scope_note?` — ${esc(x.scope_note)}`:''}${/^https?:\/\//.test(x.evidence_url||'')?` · <a href="${esc(x.evidence_url)}" target="_blank" rel="noopener noreferrer">Alias evidence</a>`:''}</p>`).join('')}${catalogEntryHealthHtml(row.sport,[row.name,row.id],eventSourceIds(event))}</details><details><summary>Catalog-wide standards</summary>${catalogWideStandards(DATA.catalog||{}).general.map(x=>`<p>${esc(x)}</p>`).join('')}<button type="button" class="catalog-plain-link" data-browser-panel="restrictions">Open all restrictions &amp; integrity standards</button></details><details><summary>Original catalog wording · ${esc(row.sport)}</summary>${(section?.lines||[]).map(x=>`<div>${esc(x)}</div>`).join('')}</details>`;
}
function renderCatalogWorkspace(){
 if(typeof CatalogWorkspace==='undefined'||!document.getElementById('catalogBrowser'))return;
 CATALOG_BROWSER_ROWS=CatalogWorkspace.build({catalog:DATA.catalog,seasonMap:DATA.seasonMap,identities:DATA.identities,today:todayKey(),sources:DATA.global?.sources||[],notes:catalogSportNotes(DATA.catalog||{}),role:(line,sport,country)=>((DATA.seasonMap?.catalog_role_overrides||[]).find(x=>x.sport===sport&&x.line===String(line).trim()&&(!x.country||x.country===country))?.role||catalogLineRole(line))});
 const sportScroll=document.getElementById('catalogSports').scrollTop,leagueScroll=document.getElementById('catalogLeagues').scrollTop;
 const state=CATALOG_BROWSER,query=document.getElementById('catalogSearch').value||'';
 const base={query,restricted:state.restricted};const counts=CatalogWorkspace.counts(CATALOG_BROWSER_ROWS,base);
 document.getElementById('catalogSeasonButtons').innerHTML=[['all','All'],['in','In season'],['unknown','Undetermined'],['out','Out of season']].map(([key,label])=>`<button type="button" data-browser-season="${key}" aria-pressed="${state.status===key}">${label} (${counts[key]})</button>`).join('');
 const visible=CatalogWorkspace.filter(CATALOG_BROWSER_ROWS,{...base,status:state.status});
 const known=catalogBrowserU18();
 const sports=[...new Set([...(DATA.catalog?.sections||[]).map(x=>x.sport),...known.map(x=>CatalogWorkspace.u18Placement(x,CATALOG_BROWSER_ROWS).sport)])];
 if(!state.sport||!sports.includes(state.sport))state.sport=sports[0];
 // A global search follows the first matching sport; empty filters keep sport evidence accessible.
 if(query&&visible.length&&!visible.some(x=>x.sport===state.sport))state.sport=visible[0].sport;
 document.getElementById('catalogSports').innerHTML=sports.map(s=>{const count=visible.filter(x=>x.sport===s).length;return `<button type="button" class="catalog-select" data-browser-sport="${esc(s)}" aria-pressed="${state.sport===s}">${esc(s)}<small>${count} catalog entr${count===1?'y':'ies'}</small></button>`;}).join('');
 const selected=visible.filter(x=>x.sport===state.sport);
 if(state.entry!=='u18'&&!selected.some(x=>x.id===state.entry))state.entry=selected[0]?.id||'u18';
 document.getElementById('catalogResultCount').textContent=`${visible.length} of ${CATALOG_BROWSER_ROWS.length} catalog entries · Season status is information, not wagering approval.`;
 let lastGroup='';
 document.getElementById('catalogLeagues').innerHTML=`<button type="button" class="catalog-select catalog-u18-button" data-browser-u18="${esc(state.sport)}" aria-pressed="${state.entry==='u18'}">Sport notes &amp; known U18<small>Always available · unaffected by filters</small></button>`+selected.map(row=>{
  const group=[row.group.confederation,row.group.country,row.group.governing_body,row.event?.category].filter(Boolean).join(' › ');const label=group!==lastGroup?`<div class="catalog-group-label">${esc(group)}</div>`:'';lastGroup=group;
  return label+`<button type="button" class="catalog-select" data-browser-entry="${esc(row.id)}" aria-pressed="${state.entry===row.id}">${esc(row.name)}<small><span class="catalog-season-tag ${row.status}">${catalogSeasonLabel(row.status)}</span>${row.restrictions.length?'<span class="catalog-restriction-tag">Has restrictions</span>':''}</small></button>`;
 }).join('')+(!selected.length?'<p class="empty">No leagues match these filters. Use Return to All to restore the catalog.</p>':'');
 const row=selected.find(x=>x.id===state.entry);
 document.getElementById('catalogDetail').innerHTML=row?catalogBrowserDetail(row):catalogBrowserSportDetails(state.sport);
 document.getElementById('catalogRestrictionsOnly').checked=state.restricted;
 document.getElementById('catalogSports').scrollTop=sportScroll;document.getElementById('catalogLeagues').scrollTop=leagueScroll;
}
function installCatalogWorkspace(){
 document.getElementById('catalogBrowserControls').addEventListener('click',e=>{
  const button=e.target.closest('[data-browser-season]');if(button){CATALOG_BROWSER.status=button.dataset.browserSeason;renderCatalogWorkspace();}
  if(e.target.closest('#catalogReset')){CATALOG_BROWSER.status='all';CATALOG_BROWSER.restricted=false;document.getElementById('catalogSearch').value='';document.getElementById('catalogSeason').value='all';CATALOG_HEALTH_FILTER='all';renderCatalog();}
 });
 document.getElementById('catalogRestrictionsOnly').addEventListener('change',e=>{CATALOG_BROWSER.restricted=e.target.checked;renderCatalogWorkspace();});
 document.getElementById('catalogBrowser').addEventListener('click',e=>{
  const sport=e.target.closest('[data-browser-sport]'),entry=e.target.closest('[data-browser-entry]'),u18=e.target.closest('[data-browser-u18]'),panel=e.target.closest('[data-browser-panel]');
  if(panel){document.querySelector(`button[data-panel="${panel.dataset.browserPanel}"]`)?.click();return;}
  if(sport){CATALOG_BROWSER.sport=sport.dataset.browserSport;CATALOG_BROWSER.entry=null;}
  else if(entry)CATALOG_BROWSER.entry=entry.dataset.browserEntry;
  else if(u18){CATALOG_BROWSER.sport=u18.dataset.browserU18;CATALOG_BROWSER.entry='u18';}
  else return;
  renderCatalogWorkspace();document.getElementById('catalogDetail').scrollTop=0;
 });
}
