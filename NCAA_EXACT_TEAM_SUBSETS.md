# NCAA exact regular-season team subsets

Verified October 18, 2026. This package is **two partial identities / four reviewed games**, not complete team schedules, full division feeds, championship approval, athlete-age clearance, or authorization of individual markets. Preserve the existing National Collegiate championship holds and all catalog restrictions.

## Integration API

`scripts/official_ncaa_team_schedule.py` exports `parse_fixtures(page, source, start_day, end_day) -> (events, held_count)`. Dates are inclusive America/Chicago review dates. Fetch `source.endpoint`, check HTTP success, then call the pure parser. Source type: `official-ncaa-reviewed-team-fixtures`.

Sources must use the exact IDs, sports, leagues and endpoints below. Parser emits canonical collector dictionaries with stable source-prefixed publisher IDs, literal publisher UTC `start_time`, home/away name, status, location and source endpoint. Buffer all records before publishing. The collector owns any precise current-instant filtering. A `ValueError` is a failed source, never an empty healthy source.

A deliberately bounded verification window runs October 18–25, 2026 inclusive. Starting after October 25 fails closed until another batch is researched. Games moved outside the verified window are held; IDs survive reschedules within it. All reviewed games becoming completed/inactive/unconfirmed fails rather than reporting healthy offseason coverage. Do not extend expiry automatically.

The held count includes unique unapproved schedule-shaped game IDs elsewhere in the page, potentially including other sports in the site-wide upcoming panel. It is not a lower-division count or a full-season completeness metric.

## Exact sources and publisher records

### NCAA Water Polo: Division I Water Polo | Men

Identity `ncaa-water-polo-di-men`; host UC Irvine.

Official page: https://ucirvinesports.com/sports/mens-water-polo/schedule

- 14405, opponent ID 149 / UC San Diego, home H. October 23 at 6 P.M.; publisher UTC `2026-10-24T01:00:00Z`.
- 14406, opponent ID 115 / Air Force, home H. October 25 at noon; publisher UTC `2026-10-25T19:00:00Z`.
- Season title `2026 Men's Water Polo Schedule`; publisher sport ID 10, title `Men's Water Polo`, shortname `mwpolo`, gender `m`.

Sport-specific DI support, not an institution-wide assumption:

- UC San Diego explicitly identifies its 2026 men's water-polo squad as Division I: https://ucsdtritons.com/news/2026/9/10/mens-water-polo-tritons-set-for-two-games-at-cal-state-fullerton-tourney.aspx
- Connecticut College's current-season official game recap identifies Air Force as a Division I men's water-polo opponent: https://camelathletics.com/news/2026/8/30/mens-water-polo-falls-to-d1-liu-and-air-force-to-open-campaign.aspx
- UCI's sport-specific ACWPC Division I award announcement: https://ucirvinesports.com/news/2025/1/8/mens-water-polo-luka-krstic-garners-acwpc-all-america-nod.aspx?path=baseball . This evidence is from January 2025, corroborated by the active 2026 program schedule; it is not a fresh NCAA membership-directory certificate.
- Additional sport-specific DI evidence for Air Force and UCSD: https://collegiatewaterpolo.org/wp-content/uploads/2025/12/ACWPC2025MenDivisionIAllAmerica.pdf

### NCAA Ice Hockey: Division I Ice Hockey | Women

Identity `ncaa-ice-hockey-di-women`; host St. Cloud State.

Official page: https://scsuhuskies.com/sports/womens-ice-hockey/schedule

- 16677, opponent ID 16 / Bemidji State, home H. October 23 at 6 p.m.; publisher UTC `2026-10-23T23:00:00Z`.
- 16678, same opponent, home H. October 24 at 2 p.m.; publisher UTC `2026-10-24T19:00:00Z`.
- Season title `2026-27 Women's Hockey Schedule`; publisher sport ID 14, title `Women's Hockey`, shortname `whockey`, gender `f`.
- Independent human-readable current schedule corroboration: https://scsuhuskies.com/sports/womens-ice-hockey/schedule/text . It includes completed October 16–17 results, so this is not merely an unupdated preseason date announcement.

Sport-specific DI support:

- Bemidji's October 15, 2026 women's-hockey preview explicitly distinguishes its DI hockey programs from its 13 other DII programs: https://bsubeavers.com/news/2026/10/15/womens-ice-hockey-beavers-return-home-to-host-no-11-12-bulldogs.aspx
- St. Cloud's January 22, 2026 official women's-hockey preview identifies SCSU as an NCAA DI women's-hockey program in its coaching-staff discussion: https://scsuhuskies.com/news/2026/1/22/womens-hockey-no-15-14-st-cloud-state-womens-hockey-set-for-home-and-home-series-against-no-3-golden-gophers

## Structured extraction and safeguards

Both official pages returned HTTP 200 and contain `script#__NUXT_DATA__`, a devalue JSON reference array. Resolve references by index, but do not recursively interpret primitive numeric values as references. Reject malformed, out-of-range or cyclic references in candidate records. Do not pin array positions: they vary between fetches.

Schedule representations use `id`, `date`, `time`, `opponent`, `location_indicator`, `game_state_display`, `status`, and `tbd`. Upcoming-panel representations supply `start_date`, `start_date_utc`, `is_tdb` (publisher spelling), `is_all_day`, `sport`, `opponent`, `game_state_display`, and `status`. A camelCase representation can additionally supply `dateUtc`, `locationIndicator`, `gameStateDisplay`, and `allday`.

Compare all copies of each allowlisted game. Require matching date, state, time flags, location and UTC; preserve literal UTC and corroborate its local wall time using the host's zone. Reject a changed opponent, home/away assignment, sport/gender, edition, malformed UTC or missing approved game/UTC. Timed records must identify sport. Hold inactive/completed/TBD/all-day, tournament/exhibition/neutral or moved-outside-window records. Unknown IDs never become approved even if their opponent is on the list. This excludes mixed-division matchups, alumni and unresolved postseason slots.

The NCAA scoreboard route was not used for these feeds. Its robot-verification responses remain unresolved, and no challenge was bypassed.

## Validation

The compact synthetic fixture builder in `tests/test_official_ncaa_team_schedule.py` covers both identities, Central-day rollover, exact identity/gender/opponents, unrelated/alumni/placeholder exclusion, duplicates and conflicts, missing/contradictory UTC, missing games, changed season/endpoint, status and expiry holds, and reschedule ID stability. Live fetched official HTML produced exactly the four games above with the same parser. Normal collector publication after integration remains required; local parsing does not establish deployed source health.
