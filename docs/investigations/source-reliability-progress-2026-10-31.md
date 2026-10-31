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
