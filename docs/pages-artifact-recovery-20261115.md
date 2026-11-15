# Reviewed Pages artifact-expiry recovery

The one-day artifact retention expired during a deployment outage. The latest
successful publication, run **43585154329**, now has an empty artifact inventory.
The normal artifact restoration remains the default and has not been bypassed.

## Independent evidence

- Successful first-attempt job **132417942566** is independently validated by the
  existing exact workflow/job profile guard.
- Its authenticated GitHub log lists immutable complete snapshot
  `382917e1f67e6fd3cfa3bcf533462c00e6d920f4f3c5b18b12cbec93ce3f398d`.
- Its upload log records artifact14110765188 and ZIP SHA256
  `3c4d96826ec414be9771af563f338d8829aeef1a07975d2c632efa37d44a3c49`.
  The expired ZIP is unavailable; we do not claim to reproduce it.
- The current official Pages pointer matches the independently logged snapshot
  digest. All31 immutable public files,31,128,687 bytes, were downloaded and
  verified against the pinned manifest. Its publisher_run_id matches the
  successful run and app_commit matches that run's head.
- The current official Pages provider-control bytes were separately inspected:
  `collector_state.halted` is true, events is empty, observation time is
  `2026-11-14T10:26:55.982207Z`. Their SHA256 is
  `f6d036af056dc4c78f6a5634769ad522d90d89794a3e4811aab3422649dc6596`.
  The successful job log reports0 provider requests and persistent hold. The
  checkpoint pins these exact held bytes, never synthesizes control state.

## Recovery boundary

The checkpoint applies only to successful anchor43585154329 at its exact commit.
An absent/expired artifact may use this equivalent public snapshot only after
existing successful-publication verification. Wrong/ambiguous artifact evidence,
other anchors, changed live pointers, redirects, hash mismatches, unheld provider
state, unknown files, and incomplete manifests remain blocked.

Recovery skips the provider collector entirely, preserving held bytes and their
observation time. It is not a new source refresh or approval. The next successful
publication becomes the normal artifact-backed anchor; this checkpoint cannot
match it. New artifacts retain for30 days instead of1. The deployment history
interlock still requires a new reviewed dispatch to recover from a failed run.
