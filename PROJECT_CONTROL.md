# Project Control Ledger

**Deadline:** October 1, 2026  
**Last reconciled:** September 24, 2026  
**Active priority:** **Priority 1 — Separate competition identities**  
**Current task:** **Table Tennis — split 2 combined Men-and-Women approvals**
**Scope-switch status:** **FROZEN — do not begin another priority until the active priority gate passes**

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
| 1. Competition identities | **IN PROGRESS** | 46 of 74 combined approvals modeled; 28 remain | 74/74 modeled; zero combined schedulable identities |
| 2. Season/schedule coverage | **INCOMPLETE** | Registry reports 13 gap areas, 302 named competition gaps, plus Boxing and Olympics adapters pending | Every operational identity has a supported season/schedule state or a documented fail-closed coverage state |
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
| 3 | Table Tennis | 2 | **NEXT** |
| 4 | Tennis | 8 | Pending |
| 5 | Volleyball | 9 | Pending |
| 6 | NCAA Golf | 1 | Pending |
| 7 | NCAA Ice Hockey | 1 | Pending |
| 8 | NCAA Lacrosse | 1 | Pending |
| 9 | NCAA Soccer | 1 | Pending |
| 10 | NCAA Swimming | 1 | Pending |
| 11 | NCAA Tennis | 1 | Pending |
| 12 | NCAA Track and Field | 2 | Pending |
| 13 | NCAA Water Polo | 1 | Pending |
|  | **Remaining** | **28** |  |

Already modeled: Soccer 22, Basketball 13, NCAA Basketball 3, Rugby 5, and Surfing 3.

## Priority 1 completion gate

Priority 1 is complete only when all of the following are true:

- All 74 combined catalog approvals are represented by distinct operational children.
- The original catalog wording remains preserved as the legal parent.
- Every child has a stable unique key and explicit division or competition identity.
- No combined parent is treated as a schedulable competition.
- Schedule sources attach only to the appropriate child identity.
- Aliases attach only to verified child identities.
- Shared, bare, or conflicting labels fail closed into review.
- Nonexistent or unverified divisions remain documented holds; no approval is invented.
- Registry validation reports zero duplicate identity keys and zero cross-division collisions.
- Active Offerings and the private portal consume the same published identity model.
- The full relevant test suite passes.
- This ledger is updated in the same work cycle.

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

**Current checkpoint:** Priority 1; Table Tennis; Rugby PR #73 prepared after Active Offerings PR #71 and portal PR #51; 46 of 74 combined approvals modeled; expected after Table Tennis: 48 of 74.
