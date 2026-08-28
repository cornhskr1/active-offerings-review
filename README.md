# Active Offerings Review System

This package is designed for **free static hosting** and requires no Python or local software for end users.

## What staff opens
`index.html`

Once hosted, staff only needs the site URL.

## Recommended free hosting
- Cloudflare Pages
- GitHub Pages

## Public-data boundary
This project is intentionally designed for public information only:
- NRGC sports wagering catalog
- official schedules
- official rosters / draws / entry lists
- official athlete/player profiles
- public DOB / age evidence
- catalog restrictions
- source coverage state

Do not place patron information, confidential operator materials, internal audit findings, or other non-public records in the hosted repository.

## Current architecture
The HTML is the user interface. Structured JSON files under `/data` define the source registry, coverage policy, and refresh strategy.

The next production step is attaching automated refresh jobs that retrieve public source data and write normalized JSON consumed by the site.

## Coverage principle
**Never Green by Absence:** zero known U18 athletes does not mean a league is cleared. Schedule, participant, age, and freshness coverage must be sufficient for the current review cycle.

## Deployment
### GitHub Pages
1. Create a free GitHub repository.
2. Upload the contents of this folder.
3. Push to `main`.
4. Open Repository Settings → Pages.
5. Select GitHub Actions as the source.
6. The included workflow deploys the site.

### Cloudflare Pages
1. Create a free Cloudflare account.
2. Create a Pages project.
3. Connect the repository or upload the site.
4. Use no build command.
5. Set output directory to `/` (repository root).

The site is static and does not require `app.py`, Flask, Docker, or a paid server.
