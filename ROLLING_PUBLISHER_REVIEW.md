# Cross-sport rolling-publisher repair

Verified locally on 2026-10-18. This is a six-feed reliability package, not a
claim that all six publishers were recovered or that any competition is cleared
for wagering. Generated schedule data is not changed by this patch.

## Fresh official evidence

- PFL MENA and Africa: official event cards and details verify MENA 12 on
  December 11 and Africa: Kigali on December 12. Both are outside the current
  October 18–25 review window. A same-day midnight end placeholder is accepted
  only with an agreeing visible date and timezone. Colon/whitespace title
  normalization still requires identical event wording, series and detail URL.
  These remain date-only events requiring bout authority and participant-age
  review, never inferred bout kickoffs.
- AUF women: 101 published pairings; four undated pairings held. The unplayed
  Wanderers at Danubio fixture is October 18 at 21:00 UTC.
- AUF cup: 56 published pairings; 12 amateur pairings held. Professional fixtures
  are Cerro Largo at Liverpool, October 21 at 19:00 UTC, and M.C. Torque at
  Peñarol, October 27 at 23:00 UTC. Only the first is inside the review window.
- Argentina LNB: the official date-query endpoint returned HTTP 403. No
  alternate access was attempted. Its parser is unchanged and recovery is not
  claimed.
- SuperLega: the official calendar returned HTTP 503 upstream connection failure
  on the initial attempt and one transient retry. The research reader also
  could not open it. No current raw calendar was available, so its parser is
  unchanged and recovery is not claimed.

Four of six sources were verified against fresh official responses. Two exact
fixtures are current-window candidates at the verification time; elapsed games
are excluded at refresh time. AUF remains explicitly partial and its undated
pairings are exposed as held diagnostics. New editions, unrecognized phases,
unknown club identities and ambiguous evidence fail closed.

Evidence excerpts and full-response SHA-256 provenance are retained under
`tests/fixtures/pfl_*20261018*` and `tests/fixtures/auf-*-20261018*`.

## Shared publication contract

All six feeds now stage a complete source batch before changing published
state. A later malformed fixture or failed event detail cannot leak earlier
cards from that same failed batch. Timed batches validate source identity,
explicit timezone, duplicate consistency and the Chicago review window. The
PFL date-only path remains separate. Existing catalog, market, Nebraska,
participant-age and amateur restrictions are not broadened.

The shared offline harness covers late failure, unavailable publishers,
next-window progression, duplicates, wrong source, missing timezone and PFL
review flags. Competition-specific tests cover current evidence and advancement.
Run `python3 -m unittest discover -s tests -q` after installing the parser
dependencies used by the standard CI workflow.
