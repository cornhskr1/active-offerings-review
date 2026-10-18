# Shared provider coverage repair

## Scope and approval boundary

This package follows basketball PR #267 and changes the 27 remaining approved TheSportsDB-backed sources: 15 basketball, eight ice hockey and four baseball identities. It adds no catalog approval, source linkage, operator information or private data. The unapproved discovery-only Israeli duplicate remains unapproved and unchanged. The four new official basketball adapters are preserved.

All 27 sources remain **partial**. A configured adapter, HTTP 200 response or current fixture does not establish full-window, full-season, qualifier, playoff or participant-age coverage. The goal remains verified mapping of every approved catalog identity; blocked, calendar-only and missing entries remain unresolved.

## Supported provider configuration

Checked October 18, 2026:

- [Official API guide](https://www.thesportsdb.com/docs_api_guide.php) explicitly publishes 123 as the current free public API key and the www.thesportsdb.com v1 base URL. It is public vendor configuration, not a private credential or an alternate-key fallback.
- [API documentation](https://www.thesportsdb.com/documentation) specifies free limits of one next-league event and three day events, and permits a league-ID filter on the daily endpoint. The adapter uses those documented methods without pagination or requests designed to defeat result limits.
- No official statement proving the old /3/ route was deprecated was found. Historical /3/ HTTP 403s remain recorded failures, not a proven deprecation diagnosis. Updating to the explicitly supported public route does not establish why they failed.
- [Terms](https://www.thesportsdb.com/docs_terms_of_use.php) permit official API access and prohibit scraping the provider website. No provider website scraping, paid subscription, account, private key or denial workaround is introduced.
- [Vendor time guidance](https://www.thesportsdb.com/forum_topic.php?t=5297) identifies API times as UTC; explicit offsets are preserved and normalized. Local-time fields are not substituted. [Vendor status guidance](https://www.thesportsdb.com/docs_api_data.php) supplies status and special-round meanings. Vendor discussion also identifies midnight as a frequent unknown-time default; these records require independent verification rather than invented time.

## Guardrails

- Validate exact league ID, sport, publisher event identity, both named opponents, supported season format and fixture-year consistency.
- Hold missing, malformed, midnight/default and TBD kickoffs; cancelled/postponed/interrupted/in-play/unknown statuses; qualifiers and preseason; conflicting duplicate identities. No noon fallback.
- Filter actual future instants against the Chicago review window. Daily queries use the exact league and include every intersecting UTC day, including the last Chicago evening and daylight-saving transitions.
- Keep returned season metadata, but do not infer full season or phase coverage from the limited response. Historical or outside-window fixtures are not carried forward.
- HTTP access and fixture completeness are separate. Every successful response still carries partial coverage, the free result limit, expected/successful request counts and an explicit incomplete-coverage warning. Empty/null events do not prove offseason or absent wagering.
- A failed day or held invalid row cannot be hidden by another successful day's fixtures. Valid exact fixtures may remain visible with the unresolved source warning.
- Pace at less than 30 requests per minute. Retry only bounded transient transport/server errors and rate limits after their reset. Stop all public API requests for the run after access denial or exhausted/unsupported rate-limit waits. Do not follow redirects or try another host/key.

## Verification and publication

Synthetic regression tests cover identities, statuses, seasons, qualifier/preseason holds, date-only/default timestamps, explicit offsets, UTC spillovers, the 25-hour Chicago fall-back day, duplicates, partial/empty responses, request shape, permanent denials, redirects and run-wide rate-limit stops. The full existing suite must also pass.

Live evidence is recorded below after the scoped collection finishes. It is diagnostic evidence, not a replacement for normal publication. The normal post-merge workflow must regenerate global schedule, identity registry, coverage inventory and basketball acceptance together. Do not replace the shared schedule with a filtered diagnostic run.

## Next family work

Provider repairs must remain grouped. Follow this package with current official multi-competition families, prioritizing the unresolved FIBA windows and the volleyball federation families once their current payloads and exact approved divisions are verified. Known repeated transport/scope problems include VolleyballWorld (two timeouts), PFL (two series), Malaysia (two round-window horizons), QSL (two competitions), AUF (two changed phases), and RFEF (three access blocks). These are investigation candidates, not promised recoveries. Access-denied sources remain blocked until permitted publisher evidence changes.

## October 18 scoped live evidence

Collection started 2026-10-18T15:25:04.020848+00:00 for 2026-10-18–2026-10-25. All 27 approved sources returned valid API responses: 35 of 35 requests succeeded. 30 future, named, timed in-window fixtures passed the parser. One Mexican LNBP midnight/default fixture was held; that source remains an unresolved source warning despite its nine valid fixtures. The other 26 checks passed their scoped validation, not completeness. Five feeds returned no current fixtures; none is labeled offseason from that absence.

| Source | Timed fixtures | Held | Scoped check |
|---|---:|---:|---|
| [npb](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4591) | 0 | 0 | Passed; partial |
| [kbo](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4830) | 1 | 0 | Passed; partial |
| [lmb](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=5064) | 0 | 0 | Passed; partial |
| [lmp](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=5109) | 1 | 0 | Passed; partial |
| [cebl](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=5266) | 0 | 0 | Passed; partial |
| [mexican-lnbp](https://www.thesportsdb.com/api/v1/json/123/eventsday.php?d=2026-10-18&l=5119&s=Basketball) | 9 | 1 | Held kickoff; partial |
| [danish-basketligaen](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=5114) | 1 | 0 | Passed; partial |
| [lithuanian-lkl](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4478) | 1 | 0 | Passed; partial |
| [greek-basket-league](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4452) | 1 | 0 | Passed; partial |
| [serbian-kls](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=5121) | 1 | 0 | Passed; partial |
| [korean-kbl](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=5124) | 1 | 0 | Passed; partial |
| [france-lnb](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4423) | 1 | 0 | Passed; partial |
| [german-bbl](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4441) | 1 | 0 | Passed; partial |
| [italian-lba](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4433) | 1 | 0 | Passed; partial |
| [polish-plk](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4578) | 1 | 0 | Passed; partial |
| [spanish-acb](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4408) | 1 | 0 | Passed; partial |
| [swiss-sbl](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=5125) | 1 | 0 | Passed; partial |
| [turkish-bsl](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4475) | 1 | 0 | Passed; partial |
| [israeli-premier](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4474) | 1 | 0 | Passed; partial |
| [icehl](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4933) | 0 | 0 | Passed; partial |
| [czech-extraliga](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4923) | 1 | 0 | Passed; partial |
| [liiga](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4931) | 1 | 0 | Passed; partial |
| [del](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4925) | 1 | 0 | Passed; partial |
| [slovak-extraliga](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4932) | 1 | 0 | Passed; partial |
| [shl](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4419) | 1 | 0 | Passed; partial |
| [swiss-national](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=4934) | 1 | 0 | Passed; partial |
| [chl](https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id=5277) | 0 | 0 | Passed; partial |

Validation: 606 aggregate tests passed, including 16 focused provider cases. An independent reviewer accepted the current guardrails after retry/status corrections and separately verified DST boundaries. An isolated full-collector replay of the captured LKL response admitted one event through the explicit source-mapping gate and retained partial coverage, without network calls or shared-data publication. Normal GitHub-run publication remains a post-merge verification gate.
