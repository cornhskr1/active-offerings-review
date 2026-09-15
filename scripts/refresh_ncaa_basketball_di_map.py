#!/usr/bin/env python3
from pathlib import Path
import datetime, json, re, requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
NOW = datetime.datetime.now(datetime.timezone.utc)

HEADERS = {
    "User-Agent":"Mozilla/5.0 (compatible; ActiveOfferingsReview/1.0; public compliance reference)"
}

SOURCES = [
    ("Men", "https://www.ncaa.com/standings/basketball-men/d1"),
    ("Women", "https://www.ncaa.com/standings/basketball-women/d1"),
]

def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()

def slug_from_href(href):
    if not href:
        return None
    m = re.search(r"/schools/([^/?#]+)", href)
    return m.group(1) if m else None

def parse_page(gender, url):
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    teams = []
    conf_nodes = soup.select(".standings-conference")
    if not conf_nodes:
        raise RuntimeError(f"{gender}: no conference headings found")

    for conf in conf_nodes:
        conference = clean(conf.get_text(" ", strip=True))
        table = conf.find_next("table")
        if not table:
            continue

        for tr in table.select("tbody tr"):
            cells = tr.find_all("td")
            if not cells:
                continue
            first = cells[0]
            team_name = clean(first.get_text(" ", strip=True))
            if not team_name:
                continue
            a = first.find("a")
            href = a.get("href") if a else None
            if href and href.startswith("/"):
                team_url = "https://www.ncaa.com" + href
            else:
                team_url = href
            teams.append({
                "gender": gender,
                "division": "Division I",
                "conference": conference,
                "team": team_name,
                "team_slug": slug_from_href(href),
                "team_url": team_url,
                "source_url": url,
                "roster_status": "ROSTER ADAPTER PENDING"
            })
    return teams

all_teams = []
errors = []
for gender, url in SOURCES:
    try:
        all_teams.extend(parse_page(gender, url))
    except Exception as exc:
        errors.append(f"{gender}: {exc}")

# Deduplicate conservatively by gender + conference + team.
dedup = {}
for x in all_teams:
    key = (x["gender"], x["conference"], x["team"])
    dedup[key] = x
teams = sorted(dedup.values(), key=lambda x:(x["gender"], x["conference"], x["team"]))

men = [x for x in teams if x["gender"]=="Men"]
women = [x for x in teams if x["gender"]=="Women"]
men_conf = sorted(set(x["conference"] for x in men))
women_conf = sorted(set(x["conference"] for x in women))

# Quality gate: official DI universe should be hundreds of teams, not dozens.
quality_passed = (
    not errors and
    len(men) >= 300 and len(women) >= 300 and
    len(men_conf) >= 20 and len(women_conf) >= 20
)

out = {
    "schema_version": 1,
    "generated_at": NOW.isoformat(),
    "source": "NCAA.com Division I basketball standings",
    "source_urls": {g:u for g,u in SOURCES},
    "quality": {
        "passed": quality_passed,
        "errors": errors,
        "requirements": {
            "min_men_teams": 300,
            "min_women_teams": 300,
            "min_men_conferences": 20,
            "min_women_conferences": 20
        }
    },
    "summary": {
        "men_teams": len(men),
        "women_teams": len(women),
        "men_conferences": len(men_conf),
        "women_conferences": len(women_conf)
    },
    "teams": teams
}

(DATA/"ncaa-basketball-di-map.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

print(json.dumps({
    "quality_gate": "passed" if quality_passed else "FAILED",
    "men_teams": len(men),
    "women_teams": len(women),
    "men_conferences": len(men_conf),
    "women_conferences": len(women_conf),
    "errors": errors
}))

if not quality_passed:
    raise SystemExit("NCAA Basketball DI map quality gate failed; refusing to publish incomplete map.")
