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
