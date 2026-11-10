# Durable school event observations

This package records exact public source facts across calendar rollovers. It does
not ingest operator reports, clear wagers, infer venues from HOME/AWAY, or infer
completion from elapsed time. The existing independent scheduled-start evidence
is unchanged. Completed result venue evidence and scheduled start time are
separate facts.

## Collection and persistence

Each `official-school-calendar-cache.json.sources[source_id]` now contains
`event_history` with contract `school-calendar-observations/v1`, and
`history_capture` with source_id, capture_status, reason, observation_count and
legacy_gap_count. Source observations are additive and never silently evicted.
Unknown old rows count as legacy gaps, not as newly verified observations.

A record contains observation_id, previous_observation_id, event_key,
observed_at, origin, kind, facts, changed_fields, venue_basis, and
actual_venue_verified=false. Per-event chains begin with null predecessor;
observation_id is SHA256 of sorted compact UTF-8 JSON of all other record fields.
Event key is SHA256 of the JSON array [source_id,school_id,sport_id,season_id,uid].
The full facts allowlist is in `scripts/school_event_history.py`. Hashes establish
internal integrity, not authenticity independent of the trusted published source.

Origins are legacy-cache, validated-calendar, and validated-official-result.
Kinds are published, removed, and season-no-longer-current. Removal means absent
from that validated same-season snapshot, never cancellation. Retiring a season
never refreshes the original published evidence timestamp. Normal
CONFIRMED/TENTATIVE to COMPLETED progression is not a conflict; cancellations,
contradictory locations/dates/opponents, and differing known times remain visible.
A missing time becoming known is not a conflicting known time.

Routine provider timestamp/sequence changes and supplementary link changes do
not create a new semantic version or refresh observed_at. Their first values
remain with the original observation; current polling metadata stays in the
ordinary source cache. Changes to event/result/date/location facts create versions.

## General Nebraska completed results

`official_school_results.py` polls the existing approved official schedule URLs
for configured Nebraska WMT programs. It verifies exact school/program/season
page title and exact event-block identity, date, opponent, explicit W/L/T result
and score, and literal location. It does not use a game whitelist. Seasons come
from explicit publisher titles, not the clock. Cross-year date bounds must be
explicitly configured or supported by validated exact-program calendar dates;
insufficient evidence holds that program. Polls and retries respect at least
216000 seconds. Existing narrow result adapters' cooldowns are inherited on
initialization and duplicate same-run page requests are shared.

Generic result fetch caches live at `official_results[source_id]` within the
same cache file. Result observations share the program's durable ledger. They
use origin validated-official-result, venue_basis
published-official-result-location, and facts.evidence_kind official-school-result.
Publisher entity ID forms uid official-result-ID. Result facts retain score,
result, publisher_event_id, source_links and calendar linkage. No actual start
is inferred. Missing location remains unresolved.

Exact unique source/school/sport/opponent/date linkage records
historical_calendar_uid, historical_calendar_source_id and calendar_location.
calendar_link_status is exact, unlinked, ambiguous or conflict. Literal same
location with optional appended venue detail is compatible; cancellation or
contradictory location is not. Original calendar rows remain intact. An exact
result may explain a removed calendar row but never silently override an
explicit cancellation or different event identity. Known parsing conflicts put
historical capture on a sticky integrity hold; network failure alone does not
rewrite historical observations.

## Public review contract

`nebraska-collegiate-live.json.event_history` uses
school-calendar-history-projection/v1 and contains window_start, window_end,
retention_note, sources and events. It selects events with any recorded event
date in the last 90 days, then emits their complete per-event chains, including
versions with changed dates outside the window. A projection row uses its latest
published facts, observation_id and original observed_at, plus
archive_event_key, archive_latest_kind, archive_conflict_fields and observations.
Retirement/removal records remain in the chain and never become a newer
published venue observation. Evidence kinds distinguish
recorded-official-calendar-result, recorded-official-calendar-schedule, and
recorded-official-school-result. Physical state classification reuses the strict
existing location classifier. No location is inferred from home/away labels.

Consumers must verify the complete chain and source status, exact program,
teams and event date, post-event observation, physical jurisdiction and conflicts.
They must not treat this descriptive archive as proof that every possible event
is present, or apply current forward-looking source TTL to original recorded
historical facts. It is not independent confirmation of actual play.

## Capacity and release

The existing private artifact limits remain unchanged at 5 MB. Each of sixteen
program ledgers has a 180000-byte pretty-JSON embedded budget (2.88 MB aggregate).
Overflow preserves all old records, marks capture degraded and stops new capture
for that attempt without blocking current schedule collection. Degraded status
is sticky; recovery requires review. This is bounded durable storage, not a
promise of unlimited retention. Per-season private storage is a separate future
contract change, not silently enabled here.

Initial saved-cache replay increased total cache from 585171 to 1450193 bytes;
90-day calendar projection was about 319 KB. Growth depends on meaningful event
revisions, not polling frequency. Generic result rows add further bounded facts.
Existing private validators accept additive keys, but every executable change
still requires the coordinated trusted-app-code manifest repin and actual
merged-tree verification specified by AGENTS.md. No new public files or private
permission changes are required. The two JSON test fixtures are synthetic
contract examples, never production source observations.

## Existing reviewed-cache migration and initial coverage

Exactly the already-reviewed Illinois and Oregon result observations may be
seeded with origin reviewed-result-cache, original_source_id and
original_event_id, preserving the original 2026-11-09T18:45:36.631287+00:00
observation timestamp. Each complete saved identity/location/status and healthy
cache deadline must match the existing reviewed spec. No score, result label,
source response hash, or new fetch timestamp is invented. The same event key
allows a later generic result observation to append without erasing the seed.
The consumer recognizes this specific provenance separately from generalized
parsed W/L/T results.

Their broad football/volleyball pages cannot be fetched again before
2026-11-12T06:45:36.631287+00:00 under the existing publisher cooldown. A normal
first run can therefore retain those two reviewed results immediately, but may
not claim all 36 results seen in the captured-page offline replay are published.
Other configured programs' first-run results depend on actual permitted fetches
and sufficient explicit season/date evidence. Saved full HTML remains an offline
verification input, not automatically backfilled production evidence.

Generic per-program result fetch caches are additionally capped at 100000 bytes
(600000 bytes across six configured programs). Oversize capture retains the prior
cache and places historical use on an integrity hold; it does not increase the
private 5 MB contract or block ordinary calendar collection.
