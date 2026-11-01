# Source reliability progress — 2026-10-31

This is a follow-up to the immutable October 30 23:41 UTC triage snapshot. It records normal-publication evidence after the reviewed repair releases; it does not replace the original source register or change its observation timestamps.

## Normal publication checkpoint

- Generated: `2026-10-31T05:29:29.031696+00:00`
- Review window: October 31–November 7, 2026
- Source records: 650
- Published events: 2,606
- Healthy sources: 450
- Publisher permission holds: 178
- Access/TLS blockers: 5
- Other parser, identity or timing failures: 17

Permission holds remain permission holds. The access/TLS group remains the two PBA sources, ATP Challenger, Canadian Premier League and Swiss Cup. Do not retry them through alternate identities, disable TLS, use unapproved mirrors or treat a transport response as permission.

## Released-source production evidence

| Source | Normal status | Events | Validation retained |
| --- | --- | ---: | --- |
| Italian SuperLega men | healthy | 11 | Exact senior division, rounds, clubs and Rome-local kickoffs |
| Italian Serie A1 women | healthy | 10 | Exact A1 rows; A2 remains excluded |
| Swiss Challenge League men | healthy | 5 | October 23 PDF, 18 rounds / 90 pairings |
| Malaysia Super League men | healthy | 3 | October 21 PDF, 36 LS6–LS11 pairings; later phase excluded |
| Georgian Erovnuli Liga men | healthy | 8 | Nine linked candidates verified for the publication envelope |
| Canadian Championship men | healthy empty | 0 | Completed final validated; no invented upcoming match |
| Spain Supercopa men | healthy empty | 0 | Exact February semifinals are outside the window |

These counts are from normal scheduled publication, not captured-response replay. They confirm production recovery for the listed lanes only. They do not grant wagering approval or broaden catalog, age, phase, participant or geographic scope.

## NBB remains externally blocked

The NBB result-row repair remains valid against its reviewed response, but the current official schedule route (`https://lnb.com.br/nbb/tabela-de-jogos`) now returns an HTTP 200 fragment stating that the requested content was not found. The official NBB home page still links that same route. The fresh normal publication therefore correctly remains failed with `NBB schedule page changed` and zero events.

Do not replace the current table with its August first-turn PDF, an indexed copy, cached content or the home-page scoreboard without current completeness and revision evidence. Keep the parser fail closed until the publisher restores the schedule route or publishes a current authoritative replacement.

## Outstanding observation boundaries

- The tennis artifact is still generated at `2026-10-29T17:25:06.477580+00:00`; the merged tennis packaging fix still lacks fresh normal-publication confirmation.
- The Odds API persistent halt remains untouched; no recovery, paid request or cache reset is authorized.
- Source triage is complete, but the source-repair program is not. Seventeen non-access failure lanes remain; some need code, while others need new publisher evidence. They remain separate from the five access/TLS blockers and 178 permission holds.

## October 31 follow-up verification

App releases #329–#334 and their data companions #25–#29 are merged. The latest app merge is `7b9e741e754e2c51ff7cc2559ad15bf337a3e747`, reviewed tree `e6032f3f7b268981a9039ae05de9c936beab5ee8`; data #29 is `23802158afd5faa1f719b32b5c7b2f80f98d4a3b`. Deployment 41198551285 and post-merge boundary 41198566745 passed. The trusted manifest still contains 537 selected entries matching the reviewed app tree. Qatar Stars, Lithuania, Ireland, Bosnia and Azerbaijan still require normal-publication evidence at this checkpoint; UAE detail recovery also requires that observation.

### Portugal Allianz Cup: current evidence remains incomplete

The exact configured official page, https://www.ligaportugal.pt/competition/914/allianz-cup/round/20262027, was retrieved again on October 31. It identifies Allianz Cup and season 2026–2027, but renders `Não foram encontrados jogos.` Its embedded publisher state identifies competition 914 / season 20262027, with an empty rounds list and `hasMatches: false`.

This does not establish the quarterfinals' final results or a complete upcoming phase. The existing parser correctly rejects the missing quarterfinal identity. Do not remove that gate, reuse the previous hardcoded dates, or treat the empty shell as a healthy empty schedule. Before a code repair, require a current official schedule/results publication proving exact phase, match identities, senior pairings, completed status or explicit kickoffs. The January Final Four remains outside the reviewed adapter until exact pairings and times are published.

## Normal publication confirmed at 12:16 UTC

Normal scheduled [global refresh 41200368311](https://github.com/cornhskr1/active-offerings-data/actions/runs/41200368311) completed successfully. Its execution log checks out reviewed app commit `7b9e741e754e2c51ff7cc2559ad15bf337a3e747`; the family receipt records that same applied commit. The later target `faf12d0ceed74024dc0b62f50094bcc80cd11e5e` differs only in documentation, so its pending-configuration flag does not invalidate these executable observations.

The hosted global schedule was generated at `2026-10-31T12:16:52.079546+00:00`, for October 31–November 7. Its SHA-256 `67cec6218ea4d9f6ea3dbbda41ed4b5681a9daeaa53981c7e9e47438bd6cc046` matches the complete-snapshot manifest at data commit `c67e772f87eede0ab1dd91c8e81ede321bfb2793`; immutable schedule blob `89aeafcb94da09029cd842cd11a973b88e22aa16`. Deployment 41201239500 succeeded.

- 650 source records; 2,597 published events; 452 healthy sources.
- 178 permission holds, unchanged.
- 20 other failures: five original access/TLS blockers, one new Luxembourg HTTP 502, and 14 parser, identity, timing or evidence failures.

| Released source | Fresh normal status | Events |
| --- | --- | ---: |
| Qatar Stars League | healthy | 7 |
| Lithuania TOPLYGA | healthy | 3 |
| Bosnia Wwin League | healthy | 4 |
| Azerbaijan Misli Premier League | healthy | 3 |
| Ireland men's Premier Division regular season | healthy empty | 0 |

All five sources have empty error lists and source checks at the generation timestamp. Their 17 emitted events have exact IDs, named pairings and kickoffs, with no retained-stale marker. Counts differ from earlier replays because already-started matches are outside the upcoming publication slice; no missing match is inferred or backfilled. Round/phase boundaries and participant safeguards remain in force.

UAE is **not** recovered: the normal source still fails with `UAE fixture detail identity missing` and zero events. The earlier successful public replay did not establish a lasting publisher recovery. NBB remains failed with `NBB schedule page changed`. Tennis normal publication remains unconfirmed.

Compared with the 05:29 snapshot, exactly three previously healthy sources now fail: `rugby-usa` (unknown SA Rugby match status), `uefa-soccer-luxembourg-national-division-bgl-ligue-men` (HTTP 502 on exact detail 2942883), and `uefa-soccer-poland-ekstraklasa-men` (nine-match round changed). These join the remaining work; retain their explicit warnings and inspect exact permitted evidence before any repair. The Luxembourg response is a transient transport failure, not permission to bypass access controls. The LMP midnight-kickoff and Argentina LNB date-window warnings also remain open but predate this comparison.

## CONMEBOL women's evidence review — October 31

The exact configured official group-stage article is readable again at https://gol.conmebol.com/libertadores/es/news/asi-quedaron-los-grupos-de-la-conmebol-libertadores-femenina-2026. A fresh request using the existing collector/parser returned 18 named fixtures and six unidentified Colombian-representative fixtures held by the existing logic. All 24 published group fixtures fall on October 15–22, outside the current October 31–November 7 window. No code or source configuration change is needed to parse this response, and no new current fixture or production recovery is claimed. The latest hosted normal snapshot remains generated at 12:16 UTC and still records the earlier missing-section error.

Two current official linked announcements, [October 31 final preview](https://gol.conmebol.com/libertadores/es/news/corinthians-y-cruzeiro-se-enfrentan-por-el-titulo-de-la-conmebol-libertadores-femenina) and [October 28 finalist announcement](https://gol.conmebol.com/libertadores/es/news/corinthians-y-cruzeiro-protagonizaran-la-final-de-la-conmebol-libertadores-femenina), identify Corinthians–Cruzeiro, October 31, 2026 and Estadio Rodrigo Paz Delgado in Quito, Ecuador. Neither article's public text publishes an exact kickoff. The group article's exact linked official schedule PDF returned HTTP 403 during this review; that request was stopped without bypass, mirror substitution or altered identity.

Retain the six unidentified-participant holds and the knockout-phase boundary. Before adding final coverage, require an accessible permitted official publication with explicit kickoff and timezone, then verify exact final identity, pairing, date and venue. Do not reuse a group-stage clock or infer a final time from the tournament's October 15–31 date envelope. Normal publication must separately confirm any group-parser recovery. This lane has been reviewed; it remains limited by current official timing/access evidence rather than a demonstrated parser defect.

Iceland #337/#30 remains released but unconfirmed by a later normal global refresh at this checkpoint. The latest listed normal global run is still 41200368311; no manual collection was triggered.

## Sweden women's cup evidence review — October 31

The exact configured [SvFF cup overview](https://www.svenskfotboll.se/svenskacupen/) was retrieved on October 31. It identifies the women's 2026/27 cup and broad phase windows, but supplies no exact current match cards. Fresh replay with the existing parser fails closed with `SvFF women's cup current round has no exact fixtures`. The official overview's linked women's season/results route, `https://www.svenskfotboll.se/go-to/?ftid=137816`, returned HTTP 403 during this review. Stop at that block; do not use alternate identities, private endpoints or mirrors to obtain those results.

The official [September 22 round-three article](https://www.svenskfotboll.se/nyheter/cuper/2026/09/svc-dam-omgang-3/) describes 16 ties, three already won and thirteen then remaining. It states that the 2027 group-stage draw takes place in November after league play ends. The [phase-date page](https://www.svenskfotboll.se/serier-cuper/svenska-cupen/speldatum/) gives a September 22–October 1 window for round three and spring 2027 for group/knockout play, while the article describes its last two ties on October 8. Neither broad window is sufficient to prove all ties completed or the absence of rescheduled matches. The adapter's old October 22 boundary is not extended or used as proof of completion.

The article also explicitly includes opponents from Elitettan, division 1 and division 2 alongside Damallsvenskan. Competition branding alone cannot clear any participant, age or catalog restriction. Before a repair, require supported access to the exact women's edition/round results or fixture publication, complete match IDs, named clubs with applicable scope evidence, and explicit completed status or date/time/venue. Keep later group-stage pairings and kickoff times held pending publication; do not turn the overview into a healthy-empty sentinel.

No parser, source configuration, publisher hold, calendar date or catalog scope changed. This review establishes a concrete access/timing/scope evidence gate, not recovered coverage. Next provider work should use another unresolved permitted source rather than repeatedly probing the blocked season route.

## Tennis persistence repair — October 31

Normal tennis intelligence run [41217767424](https://github.com/cornhskr1/active-offerings-data/actions/runs/41217767424) collected and packaged a candidate, then failed during persistence with `retained identity missing or duplicated`. Its last verified publication was left unchanged. No failed candidate artifact was retained by that workflow, so no claim is made about a particular real athlete in that discarded candidate.

The executable stages expose a reproducible mismatch: data #17's packager uses the bounded reviewed birthday-rollover proof, while persistence reruns generic retention without that proof. A synthetic complete-snapshot regression reproduces the same error at persistence for both supported tennis families. Persistence now independently recomputes that same proof from the verified prior and candidate registry, using one aware validation clock; it does not trust packaging alone or change generic semantic guards. Durable identity/evidence, publisher holds and original observation timestamps remain protected.

Validation: 11 focused rollover tests and the full 115-test data suite pass. Nine tampered packaged candidates, with recomputed integrity hashes, are rejected before staging or commit: underage/durable identity loss, duplicate durable identity, changed DOB/review, held timestamp changes, hold clearing, stale proof and unowned output edits. Successful synthetic publication preserves the exact candidate bytes and expected parent. No provider was contacted, no collection was manually triggered, and no failed candidate was pushed.

This is a data-repository persistence fix. The app changes only this documentation; all 541 trusted application entries remain unchanged and match current executable code. Merge the documentation checkpoint first and the focused data-code PR second. Observe the next normal tennis publication before claiming operational recovery; the earlier packaging-only fix was insufficient at the persistence boundary.

## UAE league detail identity repair — October 31

Fresh retrieval of the exact configured ADNOC 2026/27 fixture directory and its public competition-filter response reproduces `UAE fixture detail identity missing`. The response adds a separate `Buy Tickets` button beside an otherwise valid official fixture-detail arrow. The previous parser counted both links as competing match identities. No ticket vendor was requested.

The adapter now excludes only the observed explicitly labelled HTTPS ticket buttons on the four published Platinumlist city hosts, with their exact ticket URL shape. Every timed upcoming card must still have exactly one canonical HTTPS publisher fixture UUID. Missing, duplicate, malformed, nonpublisher or disguised extra match links fail closed; unrecognised extra links are not discarded. Competition, edition, named teams, round, date and kickoff checks remain in force. TBC rows remain held, completed rows remain excluded, and cup/U23 identities cannot borrow league scope.

Captured-response replay validates 182 league rows: 42 completed, 98 untimed held and 42 timed fixtures in GW8–GW13. Exactly three fixtures fall in the October 31–November 7 Central-date review window: Kalba at Al Dhafra, Khorfakkan at Hatta and Shabab AlAhli at Sharjah on November 7. These are replay results, not production recovery. Five selected official row nodes and the full response digest support the focused regression fixture.

Validation: 11 focused UAE tests and the full app suite pass (1,257 tests, one existing skip). Negative cases cover missing/duplicate/disguised detail identities, wrong scheme/host/port/path/UUID/query/fragment, unrecognised extra links and cup/U23 scope. The exact executable tree requires its paired trusted-code manifest before normal collection can use it. All catalog, age, publisher, phase and zero-quota safeguards remain unchanged.

Normal publication is still pending for this release, Iceland and the tennis persistence repair. Global run [41225696234](https://github.com/cornhskr1/active-offerings-data/actions/runs/41225696234) collected and packaged but correctly rejected its push when the data parent moved; its candidate was not published. Do not rebase that stale snapshot or manually rerun collection. The last verified global publication remains the 12:16 UTC snapshot.

## Uruguay cup participant-scope review — October 31

The exact configured [Copa AUF Uruguay page](https://www.auf.org.uy/copaaufuruguay/) was retrieved on October 31 (response SHA-256 `f0eaaceae9387b339fc7563a08b6313e4da2ed71b8565f3a5027d599be66b138`). It now publishes eight `OCTAVOS DE FINAL` ties alongside the six original professional groups, two explicitly amateur brackets and the professional second-phase results. Current parser replay still rejects that unreviewed mixed phase with `AUF competition phases changed: OCTAVOS DE FINAL`; no parser defect permitting a scope-preserving fixture gain was demonstrated.

All eight new ties contain one of the exact clubs identified in the page's `Primera Fase - ELIMINATORIA EQUIPOS AMATEUR` bracket. Three ties are scored completed on October 28–29; the remaining five are explicitly timed but include amateur participants:

| Unplayed pairing, home–away | Official local kickoff (Montevideo) | Amateur club identity |
| --- | --- | --- |
| Club Atlético San Carlos–Boston River | November 4, 15:00 | `/club-atletico-san-carlos/` |
| Ferro Carril Fútbol Club–Nacional | November 4, 21:00 | `/ferro-carril-futbol-club/` |
| Lito–Wanderers | November 5, 16:00 | `/centro-atletico-lito/` |
| Gladiador (Salto)–Liverpool | November 5, 18:00 | `/gladiador-salto/` |
| Club Atlético Libertad–Montevideo City Torque | November 5, 21:00 | `/club-atletico-libertad/` |

Do not add these amateur club paths to `CUP_CLUBS`, accept the mixed heading as a professional elimination, or use the professional opponent's approval for the entire pairing. The completed amateur Club Nacional de Futbol path `/club-nacional-de-futbol/` is distinct from professional Nacional `/club-nacional-de-football/`; amateur Wanderers–Durazno `/wanderers-durazno/` is distinct from professional Montevideo Wanderers `/montevideo-wanderers-futbol-club/`. These exact identities matter even where display names resemble approved clubs.

Keep the current source failure and amateur/phase boundaries visible. Later rounds require newly published exact pairings and a separate participant-scope review; competition branding and explicit kickoff do not establish participant eligibility. No code, configuration, catalog, permission, age safeguard or observation timestamp changed. This is a documented scope blocker, not production recovery or completion of the repair program.

## Poland live-card round repair — October 31

The exact configured [official season URL](https://ekstraklasa.org/terminarz/2026-2027/) currently redirects to [2026–27 round 13](https://ekstraklasa.org/terminarz/2026-2027/kolejka-13/). Its nine senior match cards comprise five completed, one live and three upcoming matches. The prior adapter counted only `/przeglad/` and `/statystyki/` links, so the live GKS Katowice–Widzew Łódź `/relacja/` card caused a false eight-match round failure. Response SHA-256: `7912775480e38fd3217fa136e19d5cb9b9572ca42d9d42fa4729548281948025`.

The adapter now validates all match routes, including the explicit live card, while still requiring nine unique match UUIDs and eighteen distinct named clubs. A live card must have its exact pairing label, two distinct official club links, one `na żywo` label, a numeric score and the matching live route, with no completed-state contradiction. It is excluded before upcoming date handling: its absent date/clock is never inferred or emitted. Unknown routes or incomplete/contradictory evidence fail closed. Existing edition, upcoming kickoff, venue and state checks remain intact.

Fresh captured-response replay yields three upcoming November 2 fixtures: Korona Kielce at Zagłębie Lubin and Śląsk Wrocław at Radomiak Radom at 17:00 UTC, and Pogoń Szczecin at Raków Częstochowa at 19:30 UTC. All fall in the current review window; the live match and five completed matches emit nothing. These are replay results, not normal publication recovery. The regression fixture retains the exact live card's semantic fields and removes decorative SVG/images only.

Focused negative regressions reject absent live labels, unknown or contradictory routes, malformed scores, missing club links, completed/live contradictions, missing cards, duplicate UUIDs and duplicate clubs. This repair requires the paired exact trusted-code manifest and normal-publication verification. Catalog, age, publisher, phase, geographic and zero-quota safeguards remain unchanged; no scheduled collection was manually triggered.

## Normal global publication confirmed at 21:27 UTC

Normal scheduled [refresh 41243681140](https://github.com/cornhskr1/active-offerings-data/actions/runs/41243681140) succeeded using reviewed app `dd7e9839412ab5b8acf97570500c1e1bb8e7609e`. The execution log and complete-snapshot family receipt agree on that applied commit, with no pending global configuration. Immutable data commit `71f8771fbde29a8ea86adaedca876ca00ec5d94e` publishes schedule blob `6c6f39f54c14b88b1b360d4051eb59178fbb4bdd`; its manifest records schedule SHA-256 `42926626ed5662ef54175fbc2f04776e46e566de44c0fae043922f3fcb10fb6e`.

The schedule is generated at `2026-10-31T21:27:58.864331+00:00`, for October 31–November 7: 650 source records, 2,549 events, 452 healthy sources, 178 unchanged permission holds and 20 other failures. All 178 held records, including saved dates and errors, exactly match the earlier 12:16 snapshot. Seven UEFA holds lack the generic `collection_paused` flag, so that flag alone undercounts holds; their explicit permission errors remain unchanged.

| Source recovered since 12:16 | Fresh normal result | Events |
| --- | --- | ---: |
| Brazil NBB | healthy, official schedule available again | 17 |
| UAE ADNOC league | healthy | 3 |
| Poland Ekstraklasa | healthy | 3 |
| Iceland reviewed final groups | healthy empty | 0 |
| Rugby USA | healthy empty in this publication, partial coverage retained | 0 |
| Luxembourg BGL | healthy empty in this publication, partial coverage retained | 0 |

All six checks use the new generation timestamp and have empty errors. Their 23 emitted fixtures have unique IDs, named pairings, official source endpoints, upcoming starts after generation and Central dates inside the review window, with no stale markers. These normal observations supersede the earlier pending NBB/UAE/Poland/Iceland checkpoints. Rugby and Luxembourg recovered without a new code change; an empty partial source does not establish complete competition coverage or season completion. No fixture observation grants wagering or age eligibility approval.

Six previously healthy lanes now fail: Uzbekistan Super League (placeholder-only kickoff window), Uruguay women's A league (official request timeout), Bosnia Wwin League (round tabs changed), Estonia Premium Liiga (senior upcoming fields changed), Malta Premier League (no verified league fixtures on ticket page) and Slovenia PrvaLiga (senior fixture fields changed). They join the scoped evidence-review queue. Uruguay cup was already failed; its latest error is also an official request timeout, which does not clear its documented amateur/phase blocker. Retain explicit warnings and inspect permitted exact evidence before any repair; do not infer missing dates or widen participant/phase scope.

At the initial review, hosted global bytes still matched the older 12:16 snapshot, so this checkpoint distinguishes successful normal data publication from hosted delivery. Verify hosted SHA-256 after deployment before claiming delivery of the new snapshot. Tennis intelligence still lacks a normal run after its persistence repair and remains separately pending. No collection was manually dispatched, no caches were reset, and executable trust, quotas, catalog, age safeguards and publisher holds are unchanged.

## Bounded university water-polo renewal — October 31

The current permitted [UC Irvine schedule](https://ucirvinesports.com/sports/mens-water-polo/schedule) identifies game 14408 / opponent 27 as UC Irvine **away** at Long Beach State on November 6 at 19:00 Los Angeles time, with literal publisher UTC `2026-11-07T03:00:00Z`. All three schedule-shaped copies agree. The independent [Long Beach State schedule](https://longbeachstate.com/sports/mens-water-polo/schedule) confirms the reciprocal home fixture as game 10424 / opponent 344 UC Irvine, identical local/UTC time and Long Beach location, with Ken Lindgren Aquatics Center named in the visible schedule. This is November 6 at 21:00 Central, not a November 7 Central-date game.

The [UCI 2026–27 registrar catalogue](https://catalogue.uci.edu/informationforadmittedstudents/intercollegiateathletics/) explicitly lists men's water polo among its Division I men's teams. The [CSULB academic advising publication](https://www.csulb.edu/academic-advising-at-csulb/bickerstaff-academic-center-bac/prospective-student-athletes) likewise explicitly lists men's water polo among its Division I varsity sports. The [official October 9 conference announcement](https://bigwest.org/news/2026/10/9/the-2026-big-wests-mens-water-polo-conference-season-starts-today.aspx) identifies November 6 as their conference finale and distinguishes the later November 20–22 championship. No held NCAA, ESPN or other publisher route was collected. A separate UCI admissions URL returned HTTP 403 and was stopped; its indexed text is not used as evidence.

The renewal adds only this exact game, opponent, away orientation, local date, UTC and location for review starts October 31–November 6. It does not mechanically extend the historical October 18–25 whitelist. The old historical batches remain bounded, and women's hockey remains expired. All other current games, tournaments, exhibitions, neutral games and unreviewed opponents remain held. A changed side, identity, time, date or location fails closed, as do missing UTC and inconsistent duplicate records. Replays using the full current Irvine response yield one exact fixture and 33 held unreviewed schedule-shaped identities.

The current St. Cloud State page has no future reviewed home game in the October 31–November 7 window: the October 31 Wisconsin game has already started. Its next listed Minnesota games are November 13–14; one is away and publishes fractional UTC outside the existing literal format. Do not round that UTC, use an expired Bemidji whitelist, extend the hockey horizon or infer a healthy-empty season. It remains outside this code batch.

Evidence fixtures retain resolved semantic copies and full-response hashes for both university schedules. This one-game regular-season renewal requires its exact companion trusted manifest and later normal-publication confirmation. It does not establish whole-division, National Collegiate championship or athlete-age eligibility, and preserves all Nebraska, catalog, publisher and zero-quota safeguards. No scheduled collection was manually triggered.

## Bosnia round-12 results-tab transition

The current permitted [NS/FSBiH Wwin League page](https://www.nfsbih.ba/en/news/football-m/wwin-league-bh/) has removed the separate upcoming tab and moved the same complete round 12 into `Results round 12`. It retains two explicitly timed unscored fixtures on November 1 and three numeric October 31 results. The previous next-tab requirement correctly rejected the changed shape but hid those two remaining fixtures.

The new path accepts this exact results round only, requiring all five reviewed numeric match IDs, their exact senior pairings and Sarajevo-local kickoffs, and all ten clubs exactly once. Completed scores are excluded only after identity/date validation and must not be in the future relative to an aware observation clock. Unknown scores, partial/duplicate rounds, changed identities/dates, ambiguous targets or a nonempty footer fail closed. The presentation-only empty footer is validated before exclusion. Later results rounds and fixture rounds remain held; no cup or Super Cup scope is admitted.

Full current-response replay retains FK Sarajevo at BSK (November 1, 12:00 UTC) and FK Velež at FK Sloga Doboj (November 1, 14:00 UTC). Three scored matches emit nothing. These are replay observations, not production recovery. Exact official panel markup and response digest accompany the regression fixture. Tests cover missing/duplicate matches, changed IDs/clubs/kickoffs, malformed or future scores, later-round substitution and footer contamination. Catalog, age, publisher, Nebraska and zero-quota safeguards remain unchanged. Normal publication must separately confirm recovery; no collection was manually triggered.

## Pages timeout and reviewed-resume proof — October 31

Bosnia app #346 and companion data #35 remain merged with exact reviewed trees and a passing data boundary. Their application deployment [41250616031](https://github.com/cornhskr1/active-offerings-review/actions/runs/41250616031), job 124683189212, **failed** at 23:11:51 UTC: `actions/deploy-pages` timed out after ten minutes of `deployment_in_progress`, then cancelled its Pages deployment. Staging, validation and artifact upload passed. The bounded collector summary confirms persistent halt, zero requests and zero events with `persistent_hold_requires_explicit_recovery`. This is a hosting failure; it does not establish normal Bosnia publication or permit clearing any provider hold.

Offline inspection also demonstrates a separate recovery defect: the existing explicit `workflow_dispatch` / `resume_after_review=true` path passes reviewed-history admission but skips creation of `odds-recovery-proof.json`, which `restore_public_snapshot.stage_migration` requires unconditionally. A regression executed against the prior code reproduces that missing file. The focused repair supplies the proof on a reviewed first-attempt dispatch only after independently validating the exact latest successful publication and its pinned first-attempt job steps. It never selects the failed artifact or falls back to an older anchor when the latest success is invalid. Automatic triggers after the hosting failure and reruns remain blocked; concurrent/unknown history, unavailable jobs and damaged anchors cannot create a proof. Snapshot/control-state restoration, the persistent Odds API halt and the workflow's audited serialization lock remain unchanged.

Validation: 24 focused history/cache/serialization tests and the 1,270-test application suite pass (one existing skip). No collection or deployment recovery has been dispatched. The GitHub connector exposes reruns but no new workflow dispatch; rerunning the failed job would correctly be rejected by the first-attempt gate. The browser deployment controls require sign-in. Keep hosting recovery pending until an authenticated, explicitly reviewed new deployment can use the repaired path and its actual output is verified. Normal tennis, Bosnia and water-polo confirmations remain separate obligations; the wider provider backlog remains open.

## Hosting recovery and normal Bosnia/university confirmation — October 31 evening

The reviewed new deployment [41258169614](https://github.com/cornhskr1/active-offerings-review/actions/runs/41258169614) succeeded on app `40fe4b30376eec376ef71da0a19f789195b035f0`. Its job received `RESUME_AFTER_REVIEW=true`, validated the prior successful publication, restored original control state and preserved the persistent Odds API halt with zero requests and zero events. The earlier dispatch received false and safely stopped; that receipt does not establish what the operator clicked. Hosted global bytes after recovery still matched the previous 21:27 UTC publication, and tennis remained October 29. Hosting recovery alone did not establish new provider observations.

Normal global run [41259498550](https://github.com/cornhskr1/active-offerings-data/actions/runs/41259498550) subsequently succeeded with that exact reviewed app. Its log and the complete-snapshot family receipt agree; global `pending_configuration` is false. The immutable schedule blob `90db0902f7342cf66626f3d3706e5b30fe2b2e41` is generated `2026-11-01T01:04:59.694365+00:00` (October 31 evening Central), with SHA-256 `63df7ba2317fa7fa7b781c4519272abf96bff2e90eee14834b4a31efb8876f2f`. It contains 650 source records, 2,553 events, 456 healthy records, 178 permission holds and 16 nonpermission failures. All 178 original permission-held source records, including timestamps and errors, match the prior 21:27 snapshot exactly.

Production now confirms these three unique, future, nonstale fixtures, with fresh source checks and no source errors:

| Source | Exact published fixture | UTC kickoff | Central date |
|---|---|---|---|
| Bosnia Wwin League | FK Sarajevo at BSK, official ID 54152329 | November 1, 12:00 | November 1 |
| Bosnia Wwin League | FK Velež at FK Sloga Doboj, official ID 54152333 | November 1, 14:00 | November 1 |
| Reviewed university water polo | UC Irvine at Long Beach State, UCI game 14408 | November 7, 03:00 | November 6 |

The water-polo source still holds 33 unreviewed identities and is partial. Bosnia later rounds/cups remain outside the reviewed slice. Neither source grants athlete-age or wagering eligibility. These normal observations supersede the pending-publication status of #345/#34 and #346/#35; normal tennis intelligence remains separately pending, with its unchanged October 29 blob `bbf7a9194f39badf1dd5cb6170e094e5fd801603`.

Two PBA lanes now report healthy empty output and Uruguay women returns two fixtures without new code; this is normal publisher-side recovery, not permission to retry previously blocked routes manually or infer complete coverage. One new failure appeared: Italian women's Serie A1 rejects an incomplete round. Add that exact lane to the existing Estonia, Slovenia, Uzbekistan, Malta, LMP and Argentina evidence-review queue. The unchanged Sweden, Portugal, CONMEBOL, Uruguay cup and access/timing boundaries remain open.

This checkpoint establishes immutable normal data publication. Verify the hosted normal URL against both the blob SHA and SHA-256 after the next deployment before claiming delivery of the newer bytes. No scheduled collection was manually triggered, no cache reset, no provider hold cleared and no executable trust change occurred.
