# NHL special-event source linkage

Verified October 18, 2026. Four existing catalog identities gain exact source links; this does not create additional approvals or complete four fixture feeds.

## Bounded scope

- `hockey-usca-nhl-skills`: February 5, 2027, official-event-window only.
- `hockey-usca-nhl-all-star`: February 6, 2027, official-event-window only.
- `hockey-usca-four-nations`: completed 2025 edition; documented next-edition hold and coverage gap.
- `hockey-usca-nhl-draft`: completed 2026 edition; 2027 timing remains unverified, with a documented hold and coverage gap.

The two calendars use separate exact IDs and catalog labels. Neither reuses the ordinary NHL ESPN adapter. All-Star Weekend remains an ambiguous umbrella, not an approval alias. Four Nations cannot inherit the separate World Cup, Olympics or All-Star schedules. No annual or next-year recurrence is inferred.

## Evidence and timing

- [NHL's event-format announcement](https://www.nhl.com/news/topic/nhl-all-star/nhl-unveils-new-format-for-2027-all-star-weekend) establishes the two dates and UBS Arena venue.
- [NHL's later broadcast announcement](https://www.nhl.com/news/2026-2027-national-tv-schedule-announced) supplies Skills at 7 p.m. ET and the Game at 3 p.m. ET.
- [Official Four Nations schedule](https://www.nhl.com/news/4-nations-face-off-schedule-rosters-canada-united-states-sweden-finland-x9193) is historical 2025 evidence only.
- [Official 2026 Draft announcement](https://www.nhl.com/news/2026-nhl-draft-to-be-held-in-buffalo) is historical edition evidence, not a 2027 calendar.

The announced times are evidence metadata with America/New_York offsets and UTC conversions. The unchanged calendar helper still emits `date_only` markers; its placeholder timestamp must not be read as kickoff. Normal publisher health checks remain enabled. Reachability does not verify that pinned dates are still current.

Draft retains exactly `MARKETS CLOSE 1 HOUR PRIOR TO EVENT START`. There is no deadline calculation, assumed draft start time or opponent fixture. Actual event/session timing and market scope require review before any closing-time decision.

## Expected result and verification

The linkage changes four `NO_LINKED_SOURCE` rows into two `OFFICIAL_WINDOW_ONLY` rows and two `ADAPTER_GAP` rows. It adds no October 18–25 calendar cards or configured fixture adapters. Existing holds remain visible.

`tests/test_nhl_special_event_linkage.py` uses fixed offline fixtures and a fresh inventory build, not rolling generated inventory. It covers exact identity separation, published-time conversions, date-only output, expiry without rollover, publisher failure, draft restrictions and the four-row coverage delta. Generated data, collectors and UI are unchanged.
