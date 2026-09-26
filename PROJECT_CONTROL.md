# Project Control Ledger

**Deadline:** October 1, 2026  
**Last reconciled:** September 26, 2026
**Active priority:** **Priority 2 — Complete season and schedule coverage linked to Review Today**
**Current task:** **NCAA Tennis coverage — verify separate Division I men's and women's calendars and source scope**
**Scope-switch status:** **Priority 1 gate passed September 24; Priority 2 is active and remains frozen until its gate passes**

This file is the project source of truth. A merged pull request, passing test, or completed sport does not change project status unless this ledger is updated against the applicable completion gate.

## Fixed priority order

1. **Separate competition identities.**
   Retain the exact catalog line as the legal approval parent while giving every distinct men’s, women’s, level, discipline, age, or event competition its own operational identity.

2. **Complete season and schedule coverage linked to Review Today.**
   Attach season windows and official schedule sources to the correct operational identity. Schedule evidence may validate activity but never creates catalog approval.

3. **Normalize Kambi, IGT, and Caesars aliases.**
   Map only verified operator labels to exact operational identities. Ambiguous labels remain in review.

4. **Complete the catalog-change workflow.**
   Detect additions, changes, and removals; hold new or changed entries out of Review Today until explicitly mapped and approved.

5. **Run systemwide regression testing.**
   Validate catalog parsing, identity resolution, schedule linkage, operator reports, restrictions, Review Today, portal findings, and audit-log outputs together.

6. **Document ongoing maintenance.**
   Publish the refresh, exception, review, ownership, and recovery procedures needed to operate the system after release.

## Current project status

| Priority | Status | Current evidence | Exit condition |
|---|---|---|---|
| 1. Competition identities | **COMPLETE** | 74/74 resolved; 72 split legal parents yield 144 unique children, with two evidence-backed single mixed competitions; public and private portal gate checks passed | 74/74 resolved; no false combined schedulable identities |
| 2. Season/schedule coverage | **IN PROGRESS** | Inventory covers 722 catalog operational identities and 144 split children; 13 reported gap areas contain 303 labels, which are not a distinct-identity count | Every operational identity has a supported season/schedule state or a documented fail-closed coverage state |
| 3. Operator aliases | **PROVISIONAL** | Extensive alias and portal work merged before Priority 1 was finished | Revalidate every alias against final child identities; unresolved ambiguity remains queued |
| 4. Catalog-change workflow | **PARTIAL** | Fail-closed queue and refresh workflow exist | Controlled add/change/remove test passes end to end |
| 5. Systemwide regression | **PARTIAL** | Many component tests exist | One cross-repository release suite passes against final data |
| 6. Maintenance documentation | **INCOMPLETE** | General README material exists; no complete operating runbook | Staff-ready runbook and recovery procedure approved |

## Priority 1 recovery queue

The legal catalog parent remains unchanged. Each item below requires separate operational child identities.

| Order | Section | Remaining combined approvals | Status |
|---:|---|---:|---|
| 1 | Rugby | 5 | **Complete** |
| 2 | Surfing | 3 | **Complete** |
| 3 | Table Tennis | 2 | **Complete** |
| 4 | Tennis | 8 | **Complete** |
| 5 | Volleyball | 9 | **Complete** |
| 6 | NCAA Golf | 1 | **Complete** |
| 7 | NCAA Ice Hockey | 1 | **Complete** |
| 8 | NCAA Lacrosse | 1 | **Complete** |
| 9 | NCAA Soccer | 1 | **Complete** |
| 10 | NCAA Swimming | 1 | **Complete** |
| 11 | NCAA Tennis | 1 | **Complete** |
| 12 | NCAA Track and Field | 2 | **Complete** |
| 13 | NCAA Water Polo | 1 | **Complete** |
|  | **Remaining** | **0** |  |

Already resolved: Soccer 22, Basketball 13, NCAA Basketball 3, Rugby 5, Surfing 3, Table Tennis 2, Tennis 8, Volleyball 9, NCAA Golf 1, NCAA Ice Hockey 1, NCAA Lacrosse 1, NCAA Soccer 1, NCAA Swimming 1, NCAA Tennis 1, NCAA Track and Field 2, and NCAA Water Polo 1. Table Tennis includes one evidence-backed single mixed-gender MLTT competition; Tennis includes one evidence-backed single mixed-team United Cup competition. The NCAA titles its separate men's and women's water polo championships National Collegiate; the Division I wording remains the exact catalog approval, and the championship source scope needs explicit verification before schedule linkage.

## Priority 1 completion gate

Priority 1 is complete only when all of the following are true:

- All 74 combined catalog approvals are resolved according to their actual competition structure.
- Separate men’s and women’s competitions are represented by distinct operational children.
- A combined catalog line remains one operational identity only when official evidence establishes a single mixed-gender or coed competition.
- The original catalog wording remains preserved as the legal parent.
- Every child has a stable unique key and explicit division or competition identity.
- No combined parent is treated as schedulable merely because the catalog line says Men and Women.
- Schedule sources attach only to the appropriate child identity.
- Aliases attach only to verified child identities.
- Shared, bare, or conflicting labels fail closed into review.
- Nonexistent or unverified divisions remain documented holds; no approval is invented.
- Registry validation reports zero duplicate identity keys and zero cross-division collisions.
- Active Offerings and the private portal consume the same published identity model.
- The full relevant test suite passes.
- This ledger is updated in the same work cycle.

### Gate verification — September 24, 2026

**Passed.** Public Active Offerings PR #86 completed the 74th combined-approval resolution. The 72 approvals requiring a split retain their legal parent wording and produce 144 operational children with unique keys. The other two resolved approvals are evidence-backed single mixed competitions. The generated registry contains 724 competition identities, no schedulable split parents, no missing children, no duplicate child keys, and no cross-child schedule-source assignments among the 50 child source attachments checked. The reviewed public alias crosswalk has 208 entries targeting catalog identities, with none targeting a split parent; 142 ambiguous or unsupported aliases remain queued for review. Unverified women's competition labels remain explicit holds.

Private portal PR #52 synchronized its bundled catalog and identity reference with the published 9.22.26 model; merged portal and public branches match on all 724 identities, 72 split parents, 144 children, and the 142-entry review queue. Private portal PR #53 holds the 11 existing operator aliases that still point to a combined legal parent until an exact child can be verified. These provisional alias rows do not establish operational approval. The public catalog child renderer was merged in PR #82.

The public suite passed 85 tests and the catalog identity validator reported zero ghost approvals and zero held split-parent events. The portal suite passed 127 tests locally with the current operator aliases; the PR #53 Portal Tests workflow passed. Calendar dates and missing schedule evidence remain Priority 2 work; unverified operator aliases remain Priority 3 work and continue to fail closed.

**Scope-switch decision:** With the Priority 1 completion gate verified on the merged public and private branches, Priority 2 is now the only active priority. Inventory all final child identities and their coverage states before filling the 13 reported gap areas and the additional pending division-specific calendars. Keep Priority 3 alias verification frozen until Priority 2 passes its gate.

## Priority 2 coverage baseline and fixed queue

`data/priority2-coverage-inventory.json` lists all 722 mapped operational identities, including 144 split children, using the published 9.22.26 catalog, current registry, and global plus regional schedule configurations. It keeps the schedule-only label `NCAA Football` outside the mapped approval count; this label cannot create independent catalog approval.

| Schedule linkage state | Identities | Meaning |
|---|---:|---|
| Adapter configured | 179 | Source configured; actual fixture coverage and refresh health still require verification |
| Adapter gap | 288 | Source is marked as a coverage gap, not an unattended fixture adapter |
| No linked source | 120 | No source ID attached to the operational identity |
| Official event window only | 65 | Window evidence exists; individual fixture coverage is not established |
| Source scope review | 70 | Attached ID is absent from the schedule configuration; some IDs are official-link references rather than fixture adapters |

The separate season audit finds 131 identities with pending dates, 24 with no season window, eight documented holds, and no partial windows. These categories overlap the schedule linkage states. The global feed's 303 reported gap **labels** across 13 areas must not be added to the 722 identity total or treated as proof that the remaining identities have complete schedules. The absence of an event in a seven-day feed is not proof of missing coverage or an out-of-season state.

| Order | Coverage section | First check |
|---:|---|---|
| 1 | Basketball | 89 identities; 26 split children; six documented no-source holds, zero pending dates, six documented holds; section exit passed |
| 2 | NCAA sports | 35 identities; 24 split children; resolve child-specific calendars and source scope across Football, Basketball, Volleyball, Baseball, and Softball; FBS remains under source-scope review |
| 3 | Volleyball | 26 identities; 18 split children without linked sources and eight adapter gaps |
| 4 | Rugby, Surfing, Table Tennis, Tennis | Finish split-child date and source states before proceeding to broad gaps |
| 5 | Soccer | 344 identities; 236 currently attached only to gap-type sources; verify division and country scope |
| 6 | Remaining sports and adapters | Reconcile every remaining inventory row, including Bowling, Esports, Lacrosse, Motorsports, Rodeo, and the Boxing/Olympics adapter holds |

Each section exits only when every identity has either verified, correctly scoped season and schedule evidence or a documented fail-closed state visible to Review Today. Record exceptions in the inventory and ledger; source availability alone never establishes approval.
**Basketball checkpoint, September 24:** FIBA lists qualifier windows before the men's 2027 World Cup finals. The catalog now labels the finals dates as a partial calendar, displays SEASON NOT MAPPED for that child, and keeps its missing fixture feed in Review Today for manual calendar and menu checks. The partial-window inventory guard and its Review Today test are active at function/class scope so the behavior is exercised rather than silently skipped. Official evidence: https://www.fiba.basketball/en/events/fiba-basketball-world-cup-2027/event-guide and https://about.fiba.basketball/en/our-sport/basketball/national-team-competition-systems/fiba-basketball-world-cup . Chile LNB official Liga Chery results include September 23, 2026, so the current March–December season indicator is not disproved by the earlier June finals; the missing unattended adapter remains a gap: https://lnbchile.com/liga/uno/match/con-vs-apv-2026-09-23 . Liga Nacional de Basquetbol de Chile and Copa Chile now have separate source IDs and separate Review Today gap warnings; one source may no longer stand in for both competitions. All six reported Basketball gap sources retain explicit competition-specific dates or fail-closed states and missing-adapter labels. All 89 identities still require section exit review; no NCAA work begins from this checkpoint.

**Basketball checkpoint, September 25:** The men's FIBA 3x3 World Tour now has an official 2026 circuit window from the April 25 Utsunomiya Opener through the December 13 Rio de Janeiro Final and is classified as official-window-only, not as fixture-complete. FIBA calls the women's professional circuit the **FIBA 3x3 Women’s Series**, while the catalog child says **FIBA 3x3 World Tour | Women**. That child remains fail-closed with dates and source linkage pending; the Women's Series calendar is not imported as proof of World Tour approval. Review Today now exposes pending Basketball season mappings instead of hiding them merely because the system cannot classify them as in season. Official evidence: https://worldtour.fiba3x3.com/2026/calendar and https://about.fiba.basketball/en/our-sport/3x3-basketball/competition-structure .

**Basketball checkpoint, September 25 — AfroBasket:** FIBA's separate 2025 finals windows are now attached to the correct children: August 12–24 for the men's AfroBasket in Angola and July 26–August 3 for the Women's AfroBasket in Côte d'Ivoire. Both are classified as last-published official windows, not unattended fixture coverage; their next-edition dates remain pending. This reduces Basketball to 60 identities without linked sources and 20 pending or partial date states. The catalog health display now distinguishes source-record counts from the 722-identity Priority 2 inventory so source totals are not mistaken for a completion percentage. Official evidence: https://www.fiba.basketball/en/events/fiba-afrobasket-2025/news/2021-finals-loss-to-tunisia-fuelling-zouzoua-for-angola-2025 and https://www.fiba.basketball/en/events/fiba-womens-afrobasket-2025/news/one-month-to-go-to-cote-divoire-2025 .

**Basketball checkpoint, September 25 — FIBA continental and Oceania batch:** Twelve operational identities now have separate official windows: men's and women's AmeriCup, Asia Cup, EuroBasket, Melanesia Cup, Micronesia Cup, and Polynesian Cup. Current published future windows are used where FIBA has announced them: Women's AmeriCup 2027, Women's Asia Cup 2027, Women's EuroBasket 2027, and both 2026 Polynesian Cups. The other children retain their most recent official finals window with the next edition explicitly pending. All twelve are official-window-only and do not claim unattended fixture coverage. Pacific Games and the South American Championships remain tested fail-closed holds because current division-specific dates and source scope are not supported. This reduces Basketball to 48 identities without linked sources and 8 pending or partial date states. Official evidence includes https://www.fiba.basketball/en/events/fiba-womens-americup-2027 , https://www.fiba.basketball/en/events/fiba-womens-asiacup-2027 , https://www.fiba.basketball/en/events/fiba-womens-eurobasket-2027/event-guide , https://www.fiba.basketball/en/events/fiba-micronesian-cup-2026/news/fiba-micronesian-cups-set-to-tip-off-in-guam , and https://www.fiba.basketball/en/events?discipline=basketball .

**Basketball checkpoint, September 25 — date closeout:** All eight remaining pending or partial date states now have a supported disposition. The men's 2027 FIBA World Cup window includes all six published regional qualifier windows beginning November 24, 2025 and the finals ending September 12, 2027; its unattended fixture adapter remains an explicit gap. FIBA's separate 2023 Pacific Games history pages establish November 17–25 windows for both divisions. The latest published men's South American Championship remains June 26–July 2, 2016, while the women's 2026 championship ran August 3–9. TBT's official 2026 tournament ran July 18–August 2 and is linked only to the men's child. The catalog's **FIBA 3x3 World Tour | Women** and **The Basketball Tournament (TBT) | Women** children are now classified as documented holds because neither publisher establishes the corresponding women's competition identity; no adjacent women's product is treated as approval evidence. Basketball therefore has zero pending or partial date states, two documented scope holds, and 43 identities without linked sources. Official evidence: https://www.fiba.basketball/en/events/fiba-basketball-world-cup-2027/news/world-cup-2027-qualifiers-full-schedule-available , https://www.fiba.basketball/en/history/321-mens-pacificmicronesianpolynesianmelanesian-tournaments/208432 , https://www.fiba.basketball/en/history/353-womens-pacificmicronesianpolynesianmelanesian-tournaments/208433 , https://www.fiba.basketball/en/history/327-south-american-championship/9597 , https://www.fiba.basketball/en/events/fiba-south-american-womens-championship-2026 , and https://tbthoops.com/news/tbt-announces-two-year-extension-with-fox-sports-for-new-look-2-million-tournament/ .

**Basketball checkpoint, September 25 — source batch 1:** The first six no-source identities were reviewed in catalog order. BBL-Pokal has a published September 10, 2026–February 21, 2027 official cup window; BIG3 has a published June 20–August 9, 2026 season; and the latest published Caribbean/CBC, Central American/COCABA, and Centrobasket women's windows are attached only to their exact catalog identities. These five are official-window-only and do not claim unattended fixture coverage. BBL Champions Cup is no longer treated as an annual September event: the current BBL calendar publishes the league and Pokal but no Champions Cup, so that catalog identity remains an explicit fail-closed hold unless an official revival is published. Basketball now has zero pending or partial date states, three documented holds, and 38 identities without linked sources. Official evidence: https://easycredit-bbl.de/de/n/news/2026/august/easycredit-bbl-veroeffentlicht-vorlaeufigen-spielplan-fuer-saison-26-27-heimpartie-des-deutschen-meisters-alba-berlin-als-eroeffnung , https://big3.com/news/big3-schedule-released-as-ice-cube-hypes-2026-season-as-basketball-heaven-in-b-r-interview/ , https://www.fiba.basketball/en/events/fiba-cbc-womens-championship-2025 , https://www.fiba.basketball/en/events/fiba-cocaba-womens-championship-2025 , and https://www.fiba.basketball/en/events/fiba-centrobasket-womens-championship-2026 .

**Basketball checkpoint, September 25 — source batch 2:** The next six no-source identities were reviewed in catalog order. Exact official windows are now attached to the PBA Season 50 Commissioner's Cup, Brazil's 2026 Copa Super 8, Spain's 2026 Copa del Rey, Italy's 2026 Coppa Italia Final Eight, and the full 2026/27 EuroLeague calendar. These five remain official-window-only and do not claim unattended fixture coverage. The Danish Cup is fail-closed: DBBF confirms the January 24, 2026 men's final but does not expose the full cup schedule needed to treat a final-only page as complete competition coverage. Basketball remains at zero pending or partial date states, rises to four documented holds, and falls to 33 identities without linked sources. Official evidence: https://www.pba.ph/news/ross-40-puts-clamps-on-oftana-proves-defense-wins-titles , https://lnb.com.br/copa-super-8/copa-super-8-2025/ , https://eventos.acb.com/ , https://www.legabasket.it/landing/final-eight , https://basket.dk/pokalfinaledrama-39-aarige-darboe-dominerer-for-randers-i-overtidssejr/ , and https://www.euroleaguebasketball.net/euroleague/news/the-2026-27-euroleague-schedule-is-official/ .

**Basketball checkpoint, September 25 — source batch 3:** The next six actionable no-source identities were reviewed in catalog order after retaining the three earlier fail-closed holds. Exact official windows are now attached to EuroLeague Women 2026-27 (September 23, 2026–April 18, 2027), the last completed men's French Cup (September 12, 2025–April 25, 2026), the last completed men's Greek Cup (September 13, 2025–February 21, 2026), the 2026 Greek Super Cup (September 26–27), and the NBL27 Ignite Cup (September 30, 2026–February 21, 2027). The active 2026 PBA Governor's Cup is linked to the official schedule, which confirms a July 10 start and currently publishes games through October 18; because later rounds and the finals end date are not yet published, its season window remains descriptive rather than presenting October 18 as the competition end. All six are official-window-only and do not claim unattended fixture coverage. Basketball remains at zero pending or partial date states and four documented holds, while identities without linked sources fall from 33 to 27. Official evidence: https://www.fiba.basketball/en/events/euroleague-women-26-27/games , https://coupedefrance.ffbb.com/masculin/actualite/89215 , https://www.pba.ph/schedule , https://www.basket.gr/cup-men/kypello-andron-2025-2026/146128/ , https://www.esake.gr/el/810A565A , and https://www.nbl.com.au/news/the-hungry-jacks-nbl27-ignite-cup-schedule-tickets-rules-more .

**Basketball checkpoint, September 25 — source batch 4:** The next six no-source identities were reviewed in catalog order. LKL confirms the 2026-27 Citadele King Mindaugas Cup runs October 6, 2026–February 21, 2027, and the NBA confirms its completed 2026 Draft ran June 23–24. Israel's 2026 Winner Cup is linked to its official live schedule with a September 8 start and knockout games currently published through the October 4 semifinals; Argentina's 2026-27 Liga Nacional is linked to its official fixture page with a September 27 start. Those two season windows remain descriptive because their completion dates are not yet published. The KBL Cup is now a documented hold because the Korean Basketball League has not published a 2026 Cup schedule, and the NBA international-preseason child is a documented hold because the published 2026 preseason lists NBA-versus-NBA global games but no game against a non-NBA international club. Basketball remains at zero pending or partial date states, rises to six documented holds, and falls from 27 to 23 identities without linked sources. Official evidence: https://lkl.lt/straipsniai/8972/citadele-kmt-turnyre-varzysis-nkl-klubas , https://lkl.lt/karaliaus-mindaugo-taure/tvarkarastis , https://basket.co.il/news.asp?id=84532&lang=he , https://basket.co.il/news.asp?id=86616&lang=he , https://www.laliganacional.com.ar/laliga/noticia/52355/asamblea-general-ordinaria-se-confirmo-el-formato-de-competencia-de-la-temporada-2026-27 , https://www.laliganacional.com.ar/laliga/fixture , https://www.nba.com/news/nba-draft-2026-set-barclays-center-june-23-24 , https://www.nba.com/news/key-dates , and https://www.nba.com/schedule .

**Basketball checkpoint, September 25 — source batch 5:** The next six no-source identities were reviewed in catalog order. Liga Nacional de Basquete's official schedule confirms the 2026-27 NBB begins October 17 and currently publishes games through December 29; the PBA's official live schedule confirms the active Season 50 conference calendar and currently publishes games through October 21. Both windows remain descriptive because their completion dates are not yet published. Exact official windows are attached to the completed Season 50 Philippine Cup (October 5, 2025–February 1, 2026), the completed 2026 Polish Cup (February 19–22), the upcoming 2026 Polish Supercup (September 26–27), and the completed 39th Turkish Presidential Cup (September 22). All six are official-window-only and do not claim unattended fixture coverage. Basketball remains at zero pending or partial date states and six documented holds, while identities without linked sources fall from 23 to 17. Official evidence: https://lnb.com.br/nbb/tabela-de-jogos , https://www.pba.ph/schedule , https://www.pba.ph/news/tnt-itching-to-complete-an , https://www.youtube.com/watch?v=SeTL6CAKiGE , https://plk.pl/aktualnosci/puchar-polski , https://plk.pl/aktualnosci/27426/cztery-druzyny-powalcza-o-superpuchar-polski , https://www.tbf.org.tr/duyuru/39-cumhurbaskanligi-erkekler-basketbol-kupasi-hakemleri-belli-oldu-2026-09-17 , and https://tbf.org.tr/ligler/tbf/haber/39-cumhurbaskanligi-erkekler-basketbol-kupasi-nda-sampiyon-fenerbahce-tarfin-2026-09-22 .

**Basketball checkpoint, September 25 — source batch 6:** The next six actionable no-source identities were reviewed in catalog order after retaining the five earlier fail-closed holds. Exact official windows are now attached to the completed 2026 Radivoj Korac Cup (February 18–21), the upcoming 2027 men's SBL Cup Final Four (January 23–24), the completed 2025-26 Israel men's State Cup (January 31–February 19), the last published men's Copa Super 20 (March 3–4, 2025), the completed 2026 LBA Supercoppa (September 19–20), and the completed 2026 ACB Supercopa Endesa (September 19–20). All six are official-window-only and do not claim unattended fixture coverage. Basketball remains at zero pending or partial date states and six documented holds, while identities without linked sources fall from 17 to 11. Official evidence: https://kss.rs/pocinje-prodaja-kompleta-ulaznica-za-mocart-kup-radivoj-korac-2026/ , https://swiss.basketball/events/sbl-cup/swiss-basketball-league-cup-final-four-2018-1 , https://ibasketball.co.il/league/2025-900/ , https://ibasketball.co.il/news/2026/02/%D7%94%D7%94%D7%99%D7%A2%D7%A8%D7%9B%D7%95%D7%AA-%D7%9C%D7%92%D7%9E%D7%A8-%D7%92%D7%91%D7%99%D7%A2-%D7%94%D7%9E%D7%93%D7%99%D7%A0%D7%94/ , https://www.laliganacional.com.ar/laliga/page/noticias/id/46987/title/Se-present%C3%B3-la-Copa-S%C3%BAper-20-en-Rosario , https://www.legabasket.it/news/138922/supercoppa-2026 , and https://acb.com/es/supercopa .

**Basketball checkpoint, September 25 — source batch 7 and section closeout:** The final five actionable no-source identities were reviewed. Exact official windows are attached to the last completed men's Supercopa de La Liga (January 17, 2025), the full 2026-27 Swedish SBL plan (September 25–May 16), the 2026-27 Patrick Baumann Swiss Cup (September 14–April 10), and the completed 2026 men's Turkish Cup (February 17–22). Unrivaled's official announcement confirms its third season opens January 8, 2027 and runs through March; because the complete schedule and exact completion date are not yet published, its window remains descriptive. All five are official-window-only and do not claim unattended fixture coverage. Basketball finishes its section review with zero pending or partial date states and only the six documented fail-closed holds left without linked sources; all 89 identities therefore have verified calendar/source evidence or a documented hold. NCAA sports are next in the fixed Priority 2 queue. Official evidence: https://laliganacional.com.ar/ldd/page/noticias/id/46082/title/La-Supercopa-de-La-Liga-Nacional-se-jugara-en-Buenos-Aires , https://www.sblherr.se/spelordning , https://swiss.basketball/events/swiss-cup/resources , https://www.tbf.org.tr/ligler/etk/haber/ziraat-bankasi-turkiye-kupasi-2026-da-dortlu-final-in-adi-belli-oldu-2026-02-18 , and https://www.unrivaled.basketball/news/unrivaled-to-open-season-three-in-boston-on-january-8-6ic6iuiz7d5k .

**NCAA checkpoint, September 25 — exact-scope adapter batch 1:** The men's and women's Division I basketball ESPN feeds are mapped to their separate NCAA Basketball children, and the women's Division I volleyball feed is mapped to its exact NCAA Volleyball child. This resolves three of four NCAA `SOURCE_SCOPE_REVIEW` identities; the fourth, FBS, remains held because the configured college-football feed does not yet demonstrate FBS-only scope. The NCAA section baseline is 35 identities, including 24 split children, 31 with no linked source, four in source-scope review, and 18 with pending dates. After batch 1, 31 identities still have no linked source and 18 have pending dates, while source-scope review falls to one. The NCAA section remains open. Source endpoints: https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard , https://site.api.espn.com/apis/site/v2/sports/basketball/womens-college-basketball/scoreboard , and https://site.api.espn.com/apis/site/v2/sports/volleyball/womens-college-volleyball/scoreboard .

**NCAA checkpoint, September 25 — baseball adapter batch:** The exact `Division I Baseball | Men` child now uses the NCAA Baseball schedule feed at https://site.api.espn.com/apis/site/v2/sports/baseball/college-baseball/scoreboard, with the NCAA Division I scoreboard at https://www.ncaa.com/scoreboard/baseball/d1 as the scope reference. Its recurring February–June window is retained. The September 25–October 2 refresh succeeded with zero events, consistent with the off-season; this is valid refresh health and does not establish missing coverage. The NCAA section now has four exact Division I adapters, 30 identities with no linked source, one FBS source-scope review, and 18 pending dates. FBS remains held until its feed demonstrates FBS-only scope. The NCAA section remains open.

**NCAA checkpoint, September 25 — postseason basketball batch:** The exact `College Basketball Crown (CBC) | Men` identity now has the complete April 1–5, 2026 official event window and FOX Sports schedule. It is official-window-only and does not claim unattended fixture coverage; 2027 dates remain pending. The official CBI site states that the 2026 tournament was canceled and that organizers intend to return, but it does not publish exact 2027 dates. `College Basketball Invitational (CBI) | Men` therefore remains without a linked source as a documented fail-closed hold. NCAA now has four exact adapters, one official event window, 29 identities without linked sources, one FBS source-scope review, one documented calendar hold, and 18 pending dates. The NCAA section remains open. Official evidence: https://www.foxsports.com/stories/presspass/college-basketball-crown-announces-ticket-sales-television-schedule-for-2026-tournament , https://www.foxsports.com/college-basketball/college-basketball-crown/schedule , and https://collegebasketballinvitational.com/ .

**NCAA checkpoint, September 25 — Division II and Division III basketball batch:** NCAA's four division- and gender-specific pages publish separate 2027 championship-site windows: Division II men March 23–27 in Fort Wayne, Division II women March 22–26 in Fort Wayne, Division III men March 18–20 in Pittsburgh, and Division III women March 18–20 in Cedar Rapids. Each window is attached only to its exact operational child and retains the recurring November–March season indicator. These are official-window-only records; the NCAA scoreboards remain staff references and are not presented as unattended regular-season fixture adapters. All eight NCAA Basketball identities now have an exact source disposition or documented hold. NCAA now has four exact adapters, five official event windows, 25 identities without linked sources, one FBS source-scope review, one documented calendar hold, and 18 pending dates. The NCAA section remains open; Beach Volleyball is next. Official evidence: https://www.ncaa.com/sports/basketball-men/d2 , https://www.ncaa.com/sports/basketball-women/d2 , https://www.ncaa.com/sports/basketball-men/d3 , and https://www.ncaa.com/sports/basketball-women/d3 .

**NCAA checkpoint, September 25 — Beach Volleyball scope review:** The catalog approves `Division I Beach Volleyball | Women`, and NCAA exposes a Division I scoreboard at https://www.ncaa.com/scoreboard/beach-volleyball/d1. NCAA's published May 7–9, 2027 championship, however, is officially the **National Collegiate Beach Volleyball Championship**, not a Division I-only championship. The broader championship window is therefore not attached as proof of the narrower catalog identity, and no unattended Division I-only source is claimed. This identity remains without a linked source as a documented fail-closed scope hold. NCAA remains at 25 identities without linked sources, rises to two documented calendar/scope holds, and retains one FBS source-scope review and 18 pending dates. Field Hockey is next. Official evidence: https://www.ncaa.org/championship/national-collegiate/beach-volleyball/ , https://www.ncaa.com/championships/beach-volleyball/nc/future-info , and https://www.ncaa.com/scoreboard/beach-volleyball/d1 .

**NCAA checkpoint, September 25 — Field Hockey:** NCAA's official Division I championship page establishes the exact approved women's competition scope and the Nov. 20–22, 2026 championship window at Trager Stadium in Louisville. The exact catalog child is now linked to an official-event-window source; this does not claim unattended regular-season fixture coverage. NCAA Field Hockey moves from NO_LINKED_SOURCE to OFFICIAL_WINDOW_ONLY, reducing the systemwide no-linked-source count from 120 to 119 and increasing official-window-only from 65 to 66. NCAA Football is next, with FBS remaining fail-closed until exact subdivision scope is established. Official evidence: https://www.ncaa.org/championship/division-i/field-hockey/ .

**NCAA checkpoint, September 25 — Football:** NCAA exposes distinct FBS, FCS, and Division II football views, so the broad schedule-only college-football feed is no longer used to establish any narrower catalog identity. FBS is linked to its exact NCAA scoreboard as an explicit adapter gap pending a dependable unattended fixture adapter. FCS is linked to its exact NCAA scoreboard and Jan. 11, 2027 NCAA Division I Football Championship window in Nashville. Division II is linked to its exact NCAA scoreboard and Dec. 19, 2026 championship window in McKinney. NCAA Football therefore has zero no-source identities; systemwide NO_LINKED_SOURCE falls from 119 to 117, OFFICIAL_WINDOW_ONLY rises from 66 to 68, ADAPTER_GAP rises by one, and SOURCE_SCOPE_REVIEW falls by one. The broad Football / NCAA Football feed remains schedule-only and cannot create catalog approval. Official evidence: https://www.ncaa.com/scoreboard/football/fbs , https://www.ncaa.com/scoreboard/football/fcs , https://www.ncaa.org/championship/division-i/football/ , and https://www.ncaa.org/championship/division-ii/football/ .

**NCAA checkpoint, September 25 — Golf:** NCAA's separate Division I championship pages publish the women's 2027 finals for May 21–26 and the men's for May 28–June 2, both at Omni La Costa in Carlsbad. The two split children now have their own official-window-only sources, while their recurring August–May and August–June indicators remain qualified: the championship pages do not establish a complete regular-season or regional fixture calendar. The original combined catalog wording remains the legal parent and is not schedulable. NCAA Golf moves from two pending/no-source children to zero; systemwide NO_LINKED_SOURCE falls from 117 to 115, OFFICIAL_WINDOW_ONLY rises from 68 to 70, and PENDING_DATES falls from 131 to 129. NCAA Ice Hockey is next. Official evidence: https://www.ncaa.org/championship/division-i/womens-golf/ and https://www.ncaa.org/championship/division-i/mens-golf/ .

**NCAA checkpoint, September 25 — Ice Hockey:** NCAA publishes exact Division I men's Frozen Four dates of April 8 and 10, 2027 at Capital One Arena. The men's child now has a two-date official-window-only source; this does not establish regional or regular-season fixtures. The NCAA separately titles the March 21 and 23, 2027 women's Frozen Four **National Collegiate**. That broader championship window is not attached to the catalog's narrower `Division I Ice Hockey | Women` child, which remains a visible documented scope hold with no linked source. NCAA Ice Hockey moves from two pending/no-source children to one official window and one hold. Systemwide NO_LINKED_SOURCE falls from 115 to 114, OFFICIAL_WINDOW_ONLY rises from 70 to 71, PENDING_DATES falls from 129 to 127, and documented holds rise from eight to nine. NCAA Lacrosse is next. Official evidence: https://www.ncaa.org/championship/division-i/mens-ice-hockey/ , https://www.ncaa.org/championship/national-collegiate/womens-ice-hockey/ , and https://www.ncaa.org/news/2027-womens-frozen-four-dates-changed/ .

**NCAA checkpoint, September 25 — Lacrosse:** The NCAA's separate Division I future-sites pages publish men's championship weekend May 29 and 31, 2027 at Lincoln Financial Field and women's May 28 and 30 at Subaru Park. Each split child now receives only its own two exact finals dates as official-window-only evidence; earlier rounds and regular-season fixtures remain unestablished. NCAA.org's women's event card names Johnny Unitas Stadium in Towson, which conflicts with NCAA.com's future-sites page, current women's sport page, NCAA tickets, and the published host selection identifying Subaru Park. The future-sites record and corroborating NCAA sources govern this mapping; the conflict is recorded in the women's source note for recheck. Systemwide NO_LINKED_SOURCE falls from 114 to 112, OFFICIAL_WINDOW_ONLY rises from 71 to 73, and PENDING_DATES falls from 127 to 125. NCAA Soccer is next. Official evidence: https://www.ncaa.com/championships/lacrosse-men/d1/future-info , https://www.ncaa.com/championships/lacrosse-women/d1/future-info , https://www.ncaa.com/sports/lacrosse-women/d1 , and https://www.ncaa.org/news/media-center-ncaa-announces-more-than-240-host-site-selections/ .


**NCAA checkpoint, September 26 — Soccer:** NCAA's separate Division I event pages publish the 2026 men's College Cup semifinal and final on December 11 and 14, and the women's on December 10 and 13, at WakeMed Soccer Park in Cary. Each approved split child links only to its own two exact finals dates as an official-window-only source. The recurring August–December indicator remains; these dates do not establish earlier championship rounds or unattended regular-season fixtures. Systemwide NO_LINKED_SOURCE falls from 112 to 110, OFFICIAL_WINDOW_ONLY rises from 73 to 75, and PENDING_DATES falls from 125 to 123. NCAA Softball is next; NCAA remains open. Official evidence: https://www.ncaa.org/championship/division-i/mens-soccer/ and https://www.ncaa.org/championship/division-i/womens-soccer/ .

**NCAA checkpoint, September 26 — Softball:** NCAA publishes the Division I Women’s College World Series at Devon Park in Oklahoma City from June 3–11, 2027, with the June 11 championship-series game if necessary. The exact approved 'Division I Softball | Women' identity now links to this official-window-only source and retains its February–June recurring indicator. This finals-site window does not establish regionals, super regionals, or unattended regular-season fixtures. Systemwide NO_LINKED_SOURCE falls from 110 to 109 and OFFICIAL_WINDOW_ONLY rises from 75 to 76; PENDING_DATES remains 123. NCAA Swimming is next; the NCAA section remains open. Official evidence: https://www.ncaa.com/championships/softball/d1/future-info and https://www.ncaa.org/championship/division-i/softball/ .

**NCAA checkpoint, September 26 — Swimming:** NCAA publishes separate 2027 Division I Swimming and Diving Championships in Austin: women March 17–20 and men March 24–27. The catalog approves Swimming only, and the combined championship page does not establish a swimming-only fixture source. Both operational children now record their own dates as documented fail-closed scope holds, with no source linkage or inferred diving approval. The source-state total remains 109 NO_LINKED_SOURCE and 76 OFFICIAL_WINDOW_ONLY; PENDING_DATES falls from 123 to 121 and DOCUMENTED_HOLD rises from nine to 11. NCAA Tennis is next; the NCAA section remains open. Official evidence: https://www.ncaa.org/championship/division-i/swimming-and-diving/ .

## Recovered work from September 23–24

Forty pull requests were merged during the reconstruction window: 26 in Active Offerings and 14 in the private portal.

- **Priority 1:** Active Offerings PRs #46 and #47 established the Soccer and Basketball split-identity model.
- **Priority 2:** Active Offerings PRs #49 and #50 added division schedule evidence; PR #68 expanded Golf calendars.
- **Priority 3:** The subsequent sport-by-sport alias scrub and portal parent-resolution work produced useful verified aliases and fail-closed safeguards, but it advanced before Priority 1 was complete.
- **Priority 5:** Portal boundary tests and review-queue protections are retained as regression assets.

Nothing is rolled back solely because it was completed out of order. Alias and resolver work that targets an unsplit parent is marked provisional and must be revalidated after the corresponding Priority 1 split.

## Locked project decisions

- The published Nebraska catalog is the legal approval authority.
- A schedule, provider feed, prior offering, similar name, or approved sport never creates approval.
- A combined catalog line may remain the legal parent but may not serve as one schedulable identity when distinct competitions exist.
- Men’s and women’s competitions do not inherit each other’s schedules or aliases.
- Unknown, ambiguous, youth, division-conflicting, or unsupported identities fail closed.
- Review holds remain visible until evidence resolves them.
- A sport is not “complete” merely because aliases were added or tests passed.

## Change-control rules

1. Only one priority may be active at a time.
2. Work within the active priority follows the queue above without skipping.
3. Every PR must identify its priority in the title or description.
4. Every PR must state which completion-gate item it advances.
5. No sport or priority may be called complete without objective gate evidence.
6. New issues discovered outside the active priority are logged, not pursued.
7. Scope may change only through an explicit decision recorded in this ledger.
8. The ledger must be read at the beginning of every new chat or work session.
9. Cross-repository changes must reference their paired Active Offerings or portal PR.
10. Passing CI is necessary but not sufficient for completion.

## Deadline plan

| Date | Required milestone |
|---|---|
| September 24 | Establish control ledger; complete Rugby and Surfing identity splits |
| September 25 | Complete Table Tennis, Tennis, and Volleyball identity splits |
| September 26 | Complete remaining NCAA identity splits and pass the Priority 1 gate |
| September 27–28 | Complete Priority 2 coverage work against final child identities |
| September 29 | Revalidate and finish Priority 3 operator aliases |
| September 30 | Complete Priorities 4–6 and run the release regression |
| October 1 | Final verification, deployment check, and contingency buffer |

## Session start checkpoint

Before beginning work, record:

- Active priority
- Current queue item
- Last merged PR
- Gate total before work
- Expected gate total after work
- Any blocker or deliberate hold

**Current checkpoint:** Priority 2; Active Offerings PR #113 merged. The inventory contains 722 mapped operational identities and 144 split children. NCAA Swimming begins with two pending/no-source children; this candidate records separate 2027 dates as swimming-only scope holds, without linking the combined swimming-and-diving source. Expected systemwide totals are 109 NO_LINKED_SOURCE, 76 OFFICIAL_WINDOW_ONLY, 121 PENDING_DATES, 11 DOCUMENTED_HOLD, 289 ADAPTER_GAP, and 69 SOURCE_SCOPE_REVIEW. NCAA remains open; NCAA Tennis is next. The FBS source-scope hold remains unresolved.
