# Project Control Ledger

**Deadline:** October 1, 2026  
**Last reconciled:** September 25, 2026
**Active priority:** **Priority 2 — Complete season and schedule coverage linked to Review Today**
**Current task:** **Basketball — first source-linkage batch classified; 38 identities without linked sources remain for source-scope review**
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

`data/priority2-coverage-inventory.json` lists all 722 mapped operational identities, including 144 split children, using the published 9.22.26 catalog, current registry, and global plus regional schedule configurations. It keeps the two schedule-only labels `NCAA Football` and `NCAA Volleyball` outside the mapped approval count; these labels cannot create independent catalog approval.

| Schedule linkage state | Identities | Meaning |
|---|---:|---|
| Adapter configured | 175 | Source configured; actual fixture coverage and refresh health still require verification |
| Adapter gap | 288 | Source is marked as a coverage gap, not an unattended fixture adapter |
| No linked source | 180 | No source ID attached to the operational identity |
| Official event window only | 6 | Window evidence exists; individual fixture coverage is not established |
| Source scope review | 73 | Attached ID is absent from the schedule configuration; some IDs are official-link references rather than fixture adapters |

The separate season audit finds 150 identities with pending dates, 24 with no season window, and one partial window. The partial men's FIBA World Cup state reflects that the 2027 finals dates do not cover its qualifiers. These categories overlap the schedule linkage states. The global feed's 303 reported gap **labels** across 13 areas must not be added to the 722 identity total or treated as proof that the remaining identities have complete schedules. The absence of an event in a seven-day feed is not proof of missing coverage or an out-of-season state.

| Order | Coverage section | First check |
|---:|---|---|
| 1 | Basketball | 89 identities; 26 split children, 62 without linked sources, 22 pending or partial dates, six reported adapter gaps |
| 2 | NCAA sports | Resolve child-specific calendars and source scope across all NCAA sections, including the heavily wagered Football, Basketball, Volleyball, Baseball, and Softball entries; schedule-only labels remain held |
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

**Current checkpoint:** Priority 2; Basketball first in the fixed coverage queue; Active Offerings PR #94 merged. The inventory contains 722 mapped operational identities and 144 split children; 303 feed gap labels are a separate measure. Basketball source batch 1 reduces the remaining no-source identities from 43 to 38 while adding a documented BBL Champions Cup hold; zero pending or partial date states remain. Expected after Basketball: all 89 identities have verified calendar/source evidence or a documented fail-closed hold. Do not advance to NCAA coverage until the remaining source-scope review is complete.
