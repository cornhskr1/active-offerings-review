# Project Control Ledger

**Deadline:** October 1, 2026  
**Last reconciled:** September 24, 2026  
**Active priority:** **Priority 2 — Complete season and schedule coverage linked to Review Today**
**Current task:** **Basketball — reconcile 89 operational identities, starting with division calendars and five reported adapter gaps**
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
| 2. Season/schedule coverage | **IN PROGRESS** | Inventory covers 722 catalog operational identities and 144 split children; 13 reported gap areas contain 302 labels, which are not a distinct-identity count | Every operational identity has a supported season/schedule state or a documented fail-closed coverage state |
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
| Adapter gap | 287 | Source is marked as a coverage gap, not an unattended fixture adapter |
| No linked source | 184 | No source ID attached to the operational identity |
| Official event window only | 3 | Window evidence exists; individual fixture coverage is not established |
| Source scope review | 73 | Attached ID is absent from the schedule configuration; some IDs are official-link references rather than fixture adapters |

The separate season audit finds 153 identities with pending dates and 24 with no season window in the baseline. It now also flags the men's FIBA World Cup as a partial window: the 2027 finals dates do not cover its qualifiers. These categories overlap the schedule linkage states. The global feed's 302 reported gap **labels** across 13 areas must not be added to the 722 identity total or treated as proof that the remaining identities have complete schedules. The absence of an event in a seven-day feed is not proof of missing coverage or an out-of-season state.

| Order | Coverage section | First check |
|---:|---|---|
| 1 | Basketball | 89 identities; 26 split children, 64 without linked sources, 23 pending or partial dates, five reported adapter gaps |
| 2 | NCAA sports | Resolve child-specific calendars and source scope across all NCAA sections, including the heavily wagered Football, Basketball, Volleyball, Baseball, and Softball entries; schedule-only labels remain held |
| 3 | Volleyball | 26 identities; 18 split children without linked sources and eight adapter gaps |
| 4 | Rugby, Surfing, Table Tennis, Tennis | Finish split-child date and source states before proceeding to broad gaps |
| 5 | Soccer | 344 identities; 236 currently attached only to gap-type sources; verify division and country scope |
| 6 | Remaining sports and adapters | Reconcile every remaining inventory row, including Bowling, Esports, Lacrosse, Motorsports, Rodeo, and the Boxing/Olympics adapter holds |

Each section exits only when every identity has either verified, correctly scoped season and schedule evidence or a documented fail-closed state visible to Review Today. Record exceptions in the inventory and ledger; source availability alone never establishes approval.
**Basketball checkpoint, September 24:** FIBA lists qualifier windows before the men's 2027 World Cup finals. The catalog now labels the finals dates as a partial calendar, displays SEASON NOT MAPPED for that child, and keeps its missing fixture feed in Review Today for manual calendar and menu checks. Official evidence: https://www.fiba.basketball/en/events/fiba-basketball-world-cup-2027/event-guide and https://about.fiba.basketball/en/our-sport/basketball/national-team-competition-systems/fiba-basketball-world-cup . Chile LNB official Liga Chery results include September 23, 2026, so the current March–December season indicator is not disproved by the earlier June finals; the missing unattended adapter remains a gap: https://lnbchile.com/liga/uno/match/con-vs-apv-2026-09-23 . The other four reported Basketball gap sources retain division-specific dates and missing-adapter labels. All 89 identities still require section exit review; no NCAA work begins from this checkpoint.


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

**Current checkpoint:** Priority 2; Basketball first in the fixed coverage queue; Active Offerings PR #87 merged. The inventory baseline contains 722 mapped operational identities and 144 split children; 302 feed gap labels are a separate measure. Expected after Basketball: all 89 identities have a verified calendar/source state or a documented fail-closed hold. Do not advance to NCAA coverage until that section is reconciled.
