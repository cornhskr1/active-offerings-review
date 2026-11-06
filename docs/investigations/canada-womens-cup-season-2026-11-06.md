# Canada women's cup: confirmed identity, partial calendar

Exact key: `soccer-canada-voyager-cup-women`. Baseline main: `907c03993ca58ed8b5bb1277286dd08f7a2b091e`.

Nich explicitly confirmed on November 6, 2026 that **Voyager Cup | Women** covers the **W Canadian Championship**, whose trophy is the Voyageurs Shield. His reply, “That’s is correct,” answered the specific Canada women's identity question; it does not answer the separate Canadian Cup men, FIFA or Zambia questions.

The user-supplied interpretation was logged in the ledger before source review and marked consumed after checking. It resolves this identity conflict. The existing catalog key, label, source ID and endpoint are preserved.

## Calendar evidence

| Fact | Result | Direct official evidence |
| --- | --- | --- |
| Competition / edition | Inaugural senior women's W Canadian Championship, 2026/27 | [July 16 launch](https://news.canadasoccer.com/canada-soccer-launches-inaugural-w-canadian-championship) |
| First competition fixture | August 3, 2026, Halifax Tides–Ottawa Rapid | Launch identifies the competition opener; the [competition hub](https://canadasoccer.com/championship/womensCanadianChamp/2026/) and [October 4 report](https://news.canadasoccer.com/teams-qualified-for-the-quarterfinals-of-2026-27-w-canadian-championship) corroborate the played date. |
| Semifinals | April 2027; exact fixtures not published | October 4 report; draw to determine pairings and hosts. |
| Championship endpoint | May 2027, Victoria Day weekend; **exact day unverified** | October 4 report; [final match page](https://canadasoccer.com/match/6615/) still displays a year-0001 placeholder. |
| Full schedule export | No usable semifinal/final day | The linked [official spreadsheet](https://cs-data-production.azurewebsites.net/api/teamplayer/GetChampionshipScheduleByYear/?champCode=womensCanadianChamp&lang=en&year=2026) retains `01/01/0001 00:00:00` for both semifinals and the final. |

Checked November 6, 2026. The schedule export was 7,337 bytes; SHA256 `60cf845676876aa1abd9f7d47c68277917e9b0d23af90e4cff566bc03b5d520c`. The web reader could not parse the XLSX content type, so the explicitly linked file was read directly with the repository's publisher guards installed. No held publisher was requested. The workbook was read without modification; no fixture data was imported.

The launch puts all eight entrants directly into the quarterfinals. Earlier league qualification for entry is not an earlier round of this inaugural cup. Some quarterfinals also counted as NSL matches; resolving the calendar does not create duplicate fixture records. The export duplicates Calgary's quarterfinal with English/French venue labels, and the pressroom reports 5–0 where the hub/export report 4–0. No score is imported or used to establish the season window.

The pressroom article is dated October 4; the hub's news card says October 5. The direct article date is retained with that discrepancy noted. Search snippets were not used over the direct page.

## Result and remaining action

- Ledger: `scope-conflict` → `awaiting-published-dates`.
- Confirmed opening: `2026-08-03`; full closing date remains null.
- Remove only the now-resolved identity hold and its obsolete forced out-of-season flag. The presentation remains **Undetermined — Season dates are incomplete**.
- The source remains `coverage-gap` / `pending`, with the same ID, URL and catalog terms. No fixture collector is activated, and no participant-age, publisher, market or unrelated approval hold is relaxed.
- Next trigger: a new official draw or final-date publication. The announced early-2027 draw has no exact release date yet. Do not convert a holiday weekend or the year-0001 placeholder into a confirmed endpoint.

**Progress:** one user-triggered recheck, one identity conflict resolved, one partial opening established, zero newly complete calendars. All 735 remain reviewed and zero are first-pass pending. Current statuses: 317 complete, 253 awaiting dates, 47 manual, 48 access held, 28 scope conflicts, 28 nonseasonal, 10 not scheduled and four cancelled. Saved-source display remains **321 dated / 414 undetermined**.

Tests must verify that the men's ambiguous Canadian Cup stays held, the women's record stays partial, and its unattended fixture source remains a gap. Required checks and normal publication/live parity must pass before reporting this change live.
