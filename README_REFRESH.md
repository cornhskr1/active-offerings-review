# Active Offerings Review System — Refresh Controls

This build adds the first two production controls requested:

## 1. Refresh Review
The `Refresh Review` button:
- calculates the current date in America/Chicago
- displays the Today + 7 window dynamically
- reloads `data/status.json` and `data/review-data.json` with cache bypass
- records the exact staff review timestamp in the browser
- shows the timestamp of the underlying published data separately

This prevents a staff review timestamp from being confused with the time external data was actually checked.

## 2. Background Data Refresh
`.github/workflows/refresh-data.yml` runs every 3 hours and can also be run manually from GitHub Actions.

It executes `scripts/refresh_public_data.py`, which:
- checks mapped official public sources
- records HTTP/source health and timestamps in `data/status.json`
- updates the background-check timestamp in `data/review-data.json`
- commits the refreshed status back to the repository
- triggers the normal GitHub Pages deployment

## Important coverage distinction
The background job is operational infrastructure. It does **not** yet claim that all 828+ catalog records have event-level schedule/roster adapters.

`data/review-data.json` is the contract that future league adapters will populate with:
- today's events
- U18 participant matches
- restriction triggers
- coverage alerts

The website can therefore grow league-by-league without redesigning the Refresh Review control.

## GitHub setup
Upload/replace these files in the existing Pages repository, preserving folders:
- `index.html`
- `data/`
- `scripts/`
- `.github/workflows/`

Then open **Actions → Refresh public data → Run workflow** once to test it.
