# API preflight repair and Event Overview checkpoint

Review date: November 2, 2026. **Draft; not merged or deployed.** This patch fixes missing failure diagnostics and one request-budget edge case. It does not claim that live schedule access is repaired or increase usable coverage.

## Verified starting point

- App: `cornhskr1/active-offerings-review`, main `daebbc1a589d642c15f0199fab571e6ccd855529`.
- Separate layout draft: [PR 371](https://github.com/cornhskr1/active-offerings-review/pull/371), head `03ff4f192f2ab6b8fc9302c913ba3ed19377832c`. This API patch branches directly from main and does not include that layout.
- Shared data: `cornhskr1/active-offerings-data`, inspected current snapshot at `2e912d1a0f3f7d91212dede28bbd4f5fa16cd643`.
- Compliance portal: `cornhskr1/wagering-compliance-portal`, unchanged main `a0561305279b1ad2c26db1dded9e0849bdcda79c`.
- Open PRs inspected before editing: layout PR 371 and the existing held basketball-discovery PR 249; no competing API repair found. Neither was overwritten.

The normal global collector run `41396673081` used app main and saved its attempts at `2026-11-02T05:54:26.884719+00:00` (November 1, 11:54 p.m. Central). Its published schedule blob is `9dce763d38c8a620cf3c1d1c1aac36e0d7eae2af`. The run has no retained workflow artifacts from which to recover a more specific response failure.

| Source | Actual saved result | Still unknown |
| --- | --- | --- |
| API-SPORTS NBA | One request, HTTP 200; rejected by the daily free-quota header check; zero events | Whether required headers were absent, malformed, inconsistent, or outside the free range; current-season response contents were not accepted |
| SharpAPI | Two requests, final HTTP 200; free-account validation passed; minute quota 12 with 10 remaining; event processing failed; zero events | Whether JSON, pagination, freshness, event identities, participants, phases or another validation caused the rejection |

These are observed integration blocks, not proof that either provider cannot supply current schedules. Successful HTTP and league matching are not fixture coverage or publication permission.

## Changes

- Record a small, fixed failure code and stage instead of collapsing all failures into a generic error. Distinguish transport, HTTP, JSON, account checks, daily/minute quota checks, pagination, update time, event identity, participant, phase and start-time validation.
- Preserve that failure through the existing rolling 24-hour wait, including clock rollback. Previously the next run replaced the failure text with a generic pending message.
- Preserve the two known legacy live failures as explicitly **legacy/unspecified**; do not invent their underlying causes. Unrecognized previous error strings and diagnostic fields are not copied.
- Distinguish empty responses from malformed responses, without declaring a season over or accepting fixtures.
- Stop SharpAPI before its event request when the account response reports zero requests remaining. It previously attempted the second request in that case.
- Retain only fixed messages and codes. Do not persist raw headers, bodies, provider error text, account identifiers, exception strings or keys. Existing accepted schedule evidence is unchanged.

No catalog, source configuration, mappings, UI, workflow, portal, authentication or shared decision code is modified. No adapter is activated. ESPN and publisher holds remain intact. NBA remains bounded to one request and SharpAPI to at most two, each per rolling 24 hours; no pagination, retries, redirects or paid-plan fallback is added. Publication and age review remain required.

The provider documentation distinguishes API-SPORTS daily headers (`x-ratelimit-requests-*`) from minute headers (`X-RateLimit-*`); minute headers are not substituted for missing daily evidence. SharpAPI documents its event envelope, pagination and optional phase information; validation is not loosened to guess a different schema.

- [API-SPORTS rate-limit documentation](https://www.api-football.com/news/post/how-ratelimit-works)
- [SharpAPI event documentation](https://docs.sharpapi.io/en/api-reference/events/)

## Testing

- Targeted provider and diagnostic suite: **31 tests passed**. Cases include secret-bearing exceptions and headers, rejected event fields, malformed JSON, paid quotas, zero allowance, unknown teams, empty results, cooldown, clock rollback and legacy receipts.
- Full app suite: **1,366 tests run; OK, one existing skip**. Existing permission, age, alias, mapping, provider and missing-data tests remain passing.
- Direct old/new collector comparison: **14 representative inputs identical** for emitted events, acceptance flags, completeness, review requirement, request counts, accepted evidence and observation dates. The intentionally tightened zero-remaining SharpAPI case has its own test and emits no fixtures before or after.
- Unchanged compliance portal: **726 passed, one existing skip**; **21/21 gold cases passed**, including aliases, protected participants, restrictions, college scope and unknown identities.
- Rechecked existing layout against the original app with the same saved inputs: identical digest `1e618ddc2d1606520f0066b3ddc0cc9d64d89ce35433e8574e7918a318451f1f`, covering 337 review events, 104 age records, 48 restriction entries and 661 season-progress values.
- `git diff --check` passed. App data, source configuration, frontend and workflow paths have no changes in this patch. The private portal and data repositories are not modified.

All new execution tests are local and use synthetic or retained inputs. **No authenticated provider request was made for this repair.** CI results are attached to the PR. No new production behavior or provider root cause has been verified.

## Event Overview checkpoint

An offline audit at `2026-11-02T11:41:35Z` used the latest retained global schedule, identity registry and coverage inventory from the pinned shared-data snapshot. Their Git blob hashes were verified. Existing app mapping and saved odds inputs were held fixed; no paid refresh was performed. This is a data audit, not a live UI test or a complete new deployment snapshot.

For the Central-date window November 2–9:

| Measure | Previous snapshot, same window and clock | Latest retained snapshot |
| --- | ---: | ---: |
| Operational catalog identities | 733 | 733 |
| Active mapped routes | 192 | 192 |
| Identities with fresh fixtures | 64 | 66 |
| Fresh distinct fixtures | 315 | 318 |
| Identities without fresh fixtures | 669 | 667 |
| Usable competitions added by this patch / either new API | 0 | 0 |

Normal existing-feed refreshes restored observations for Belgium's Challenger Pro League and Malaysia FA Cup. That two-competition gain is not credited to this code change. The earlier layout baseline of 69 covered identities used the November 1–8 window; it is not a same-window comparison.

The draft Event Overview retains existing events and review controls, but its usefulness is still limited by coverage. All catalog entries remain accessible in Sports & Leagues. Known U18 information remains integrated under sports, the duplicate tab is removed in the separate draft, and the Nebraska view remains separate. This patch does not finalize the layout or claim that saved ESPN mappings are current schedule coverage.

## Approval, next evidence and rollback

Owner approval is required before merging this isolated API patch. Merging app main invokes the existing deployment workflow and makes the code available to the existing collector; it does **not** merge layout PR 371 or authorize a source.

The saved rolling receipt prevents another preflight before `2026-11-03T05:54:26.884719Z` (November 2, 11:54 p.m. Central). Allow the next eligible normal collector run to record the specific cause; do not force an extra run or bypass the receipt. If a valid response is obtained, review exact competition/phase identities, freshness and intended-use permission before proposing any fixture adapter. Reassess Event Overview by additional competitions with usable data, not successful requests or commits.

Until that run, the precise live failure cannot be recovered from the saved catch-all error. This patch removes that observability block but cannot honestly be called a completed schedule-coverage repair.

Rollback: revert only this API patch on current main through the existing reviewed deployment process. Leave current data, attempt timestamps, accepted evidence, catalog, mappings, U18 records and unrelated newer changes intact. The older collector ignores the optional diagnostic field and still honors `api_attempted_at`; do not delete receipts to obtain another request. No portal or shared-data rollback is needed.
