# Jolpica F1 schedule data

The isolated F1 dataset is refreshed daily by `refresh-jolpica-f1.yml`.
It is published through the existing protected Pages publisher, never a second
deployment path. The parser remains injectable; the production wrapper permits
only the documented no-auth HTTPS schedule endpoint.

## Data license and attribution

F1 schedule data: [Jolpica-F1](https://github.com/jolpica/jolpica-f1),
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
[API terms](https://github.com/jolpica/jolpica-f1/blob/main/TERMS.md).

The derived F1 dataset must remain separately identified under CC BY-NC-SA 4.0.
Changes: selected race schedule facts, normalized dates, and review-window filtering.
The provider supplies data without warranty and does not endorse this tool.
Retain any additional attribution or notices supplied in future source revisions.
The API's data license is separate from the provider repository's software license.
Do not apply this data license to unrelated provider data or claim ownership of it.

Qualifying noncommercial display is permitted under the license's conditions;
agency status alone does not establish that every possible use is noncommercial.
The intended free regulatory review use is not a license for monetized products,
operator-benefit feeds or commercial redistribution. Upstream row-level rights
are not independently guaranteed. No logos, photos, articles or entrant data are
copied by this adapter.

## Integration contract

`scripts/jolpica_f1_schedule.py` normalizes only the exact
`motorsports-intl-f1` identity. Race schedule facts do not approve wagers or
resolve entrants, age, cancellation status or other catalog restrictions.
Practice, qualifying and sprint fields are not emitted as additional events.
Dates without a supplied time remain date-only. Observed timestamps do not
pretend to be source-update timestamps. Missing events are not cancellations.

The production wrapper enforces the specified response byte limit while reading
and disables redirects. The module
accepts only its fixed documented endpoint, caches for at least 24 hours, honors
longer numeric retry delays and preserves a persistent halt after denial or a
redirect. No key, odds endpoint or paid access is required.

Keep the generated dataset separate, with the `license` metadata and a visible
source/license notice. Do not combine it into a differently licensed provider
cache or remove downstream license rights. Retained snapshots must keep original
observation times and stale flags. Actual source health depends on observed data, not configuration alone.
No additional wagering approval, driver eligibility or complete event coverage
is implied by this schedule feed.
