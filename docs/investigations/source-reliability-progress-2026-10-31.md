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
