# Official school calendar package

## Bounded scope
Six Nebraska programs (football, men's basketball, women's basketball, volleyball, baseball, softball), and the other five programs at Creighton and Omaha. Neither Creighton nor Omaha is configured for football. This package uses the schools' offered calendar subscriptions, not roster collection or publisher APIs currently on hold.

The user is separately reviewing publisher reuse/permission questions. Offering a calendar is not represented as an unrestricted redistribution license. ESPN, NCAA.com, ITF, USTA, FIBA, FAW and UEFA holds remain unchanged.

## Dependability contract
- Exact school, sport and current-season identity must reconcile. SIDEARM current-season metadata is re-resolved from the official schedule page; a stale numeric season ID is not silently reused.
- Retain only calendar facts necessary for schedule review, source health and UID reconciliation. No logos, photographs, copied descriptions, articles or bulk rosters are added.
- Honor calendar refresh intervals, including Huskers' literal 60-hour interval. These intervals are not a publisher update guarantee or a promise of real-time cancellation detection.
- Preserve unknown kickoffs as unknown. UTC and named timezones are converted with daylight-saving rules. Floating or ambiguous times are not assigned a guessed zone.
- Failed, ambiguous or unparseable calendars retain last-good observations, clearly stale. Empty responses do not establish an offseason or absence of games.
- Cancellations and disappearance from a validated same-season snapshot are distinct. Removed UIDs are not silently revived by saved ESPN basketball supplements.
- Physical state evidence controls Nebraska location screening. An ambiguous venue name, a HOME label, or a bare city does not establish state. Calendar facts do not verify athlete age or market eligibility.

## Existing evidence
Unrelated saved school sports are retained with stale disclosure. The old HTML collectors remain in source control but are no longer invoked by the Nebraska refresh workflow. Existing basketball futures evidence is retained with its original observation timestamp and explicit stale labeling. A calendar subscription alone does not prove the first legitimate regular-season/postseason contest, and the first future calendar fixture is not used to invent a futures cutoff.

## Publication verification
Local tests and independent review precede publication. Completion requires the normal hosted workflow, sixteen source-health results, preservation/deduplication checks and live Nebraska Collegiate rendering. Local fixture parsing is not proof of deployed source health.


## Bounded historical result verification
The separate `historical_events` / `historical_sources` arrays verify only two
reviewed completed results: Nebraska football at Illinois on November 6, 2026
(official event 21839), and Nebraska volleyball at Oregon on November 7, 2026
(event 25154). They are not upcoming dashboard fixtures or general historical
archive coverage. Each must reconcile the exact original calendar source, UID,
school, program, date, opponent, and site/location. Original observations remain
unchanged, including Illinois's REMOVED/stale provenance and Oregon's earlier
CONFIRMED observation. Oregon remains eligible when the rolling calendar later
marks that same exact observation SCHEDULED or REMOVED. A completed original
needs no supplemental duplicate, so its historical cache is cleared. Canceled,
postponed, suspended, abandoned or contradictory original records never qualify.

The adapter checks the exact official 2026 schedule title, unique event identity,
completed result, date, teams, away label and reviewed location. Oregon's exact
published location includes Matthew Knight Arena; `official_result_location`
retains that full value, while `location` carries the independently matching
Eugene city/state component. Neither scores nor inferred kickoff times are
published. Each verification has its own source ID and observation timestamp,
a conservative 60-hour refresh interval and an explicit 90-day review expiry.
Failures retain last-good historical facts as stale without updating observation
timestamps. These records do not erase calendar removal, authorize markets, or
prove athlete age; consumer confirmation still requires exact event evidence.

Omaha's offered calendars now use the exact school label `Omaha`; the reviewed
configuration accepts that name and the earlier `University of Nebraska Omaha`,
while still requiring the exact program and match structure. The new fixtures
retain only factual event properties. No production data is rewritten by this
configuration change alone.

## Optional bounded scheduled-start evidence

The historical result remains date-only. An optional
`scheduled_start_evidence` object carries separately fetched, scheduled (never
actual) start provenance for those same two reviewed events. Its own 60-hour
TTL, source URL, response SHA-256, exact original calendar identity, program,
match date, teams, site and city/state binding survive into the portal audit.
The result and calendar observations are never rewritten to manufacture a time.
Timing failure, malformed timing cache, changed facts or unavailable PDF leaves
valid result/location evidence available with timing unknown. Retried failures
never update a last-good observation timestamp. The existing 90-day historical
scope, cancellation/conflict checks and source-health gates still apply.

Nebraska football at Illinois is scheduled for 7 p.m. CT on November 6, 2026
(UTC November 7 at 01:00). The official November 2 preview supplies the qualified
kickoff statement, but does not itself state November 6. Therefore the adapter
also requires the exact linked official game-notes PDF, whose inspected page 1
identifies the 2026 football schedule, both teams, Friday November 6, 7 p.m. CT,
Champaign and Memorial Stadium. Its reviewed SHA-256 is
`b64c9ed82e4985c013dc47fd48fc59086745cf60a3d3abef9ef14d91db21546e`.
Only identical PDF bytes qualify. A changed PDF needs a new human review, not
automatic repinning. No runtime PDF parser or new dependency is needed.

Nebraska women's volleyball at Oregon is scheduled for 9 p.m. CT on November 7,
2026 (UTC November 8 at 03:00). Its official November 5 preview also describes
Washington. The parser requires the exact Oregon heading and qualified first
serve in the same unique paragraph. Washington's time cannot fill an absent
Oregon time. Actual venue continues to come from the separately verified
completed result, including its exact Matthew Knight Arena evidence.

Sources:
- https://huskers.com/news/2026/11/2/nebraska-faces-illinois-in-friday-night-road-game
- https://storage.googleapis.com/huskers-com-prod/2026/11/02/7722pedpBrvn50mWdr6tzmNFeRWsDWa0MMNPbTGO.pdf
- https://huskers.com/news/2026/11/05/vb-preview-at-no-12-oregon-and-no-18-washington

The portal requires explicit staff confirmation and a verification note for each
historical group. It separately validates optional timing provenance and the
PDF pin, retains known-start conflicts and post-scheduled-start findings, and
states that scheduled time does not prove play began. These fixtures are not a
claim that all real wagers clear. Release requires a full executable-tree
companion manifest after the actual source merge, then a verified collector and
consumer publication. Preparing patches alone does not activate new evidence; a successful guarded
collector and verified consumer publication are required.
