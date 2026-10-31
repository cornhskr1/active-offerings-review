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
