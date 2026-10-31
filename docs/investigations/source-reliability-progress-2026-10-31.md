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
