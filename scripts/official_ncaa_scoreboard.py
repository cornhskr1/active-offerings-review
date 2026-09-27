"""Extract exact Division I fixtures from NCAA's public scoreboard."""

import datetime
import json
import re


def scoreboard_query(page, sport_code):
    match = re.search(
        r'<script type="application/json" data-drupal-selector="drupal-settings-json">(.*?)</script>',
        page, re.S,
    )
    if not match:
        raise ValueError("NCAA scoreboard settings are missing")
    settings = json.loads(match.group(1))
    widget = (settings.get("scoreboardWidget") or {}).get("widgets") or []
    if (len(widget) != 1 or widget[0].get("sportCode") != sport_code
            or widget[0].get("division") != "d1"
            or not isinstance(widget[0].get("seasonYear"), int)):
        raise ValueError("NCAA scoreboard sport or Division I scope changed")
    url = (settings.get("scoreboard") or {}).get("contestsDataUrl")
    if not isinstance(url, str) or not url.startswith("https://sdataprod.ncaa.com?meta=GetContests_web&"):
        raise ValueError("NCAA contest endpoint changed")
    return url, widget[0]["seasonYear"]


def exact_contests(payloads, date):
    """Return DI games, holding IDs also present in DII/DIII or lacking time."""
    lists = []
    for division in (1, 2, 3):
        data = payloads[division]
        if data.get("errors") or not isinstance((data.get("data") or {}).get("contests"), list):
            raise ValueError("NCAA division contest response is incomplete")
        contests = data["data"]["contests"]
        ids = set()
        for contest in contests:
            if (not contest.get("contestId") or contest.get("startDate") != date.strftime("%m/%d/%Y")
                    or contest["contestId"] in ids):
                raise ValueError("NCAA contest identity or day changed")
            ids.add(contest["contestId"])
        lists.append(contests)
    other_ids = {contest["contestId"] for rows in lists[1:] for contest in rows}
    approved, crossover, untimed = [], [], []
    for contest in lists[0]:
        teams = contest.get("teams") or []
        if (len(teams) != 2 or {team.get("isHome") for team in teams} != {True, False}
                or not all(team.get("nameShort") for team in teams)):
            raise ValueError("NCAA Division I matchup has no exact named teams")
        if contest["contestId"] in other_ids:
            crossover.append(contest)
        elif (not contest.get("hasStartTime") or contest.get("tba")
              or not isinstance(contest.get("startTimeEpoch"), int)):
            untimed.append(contest)
        else:
            approved.append(contest)
    return approved, crossover, untimed


def event_from_contest(source, contest):
    home = next(team["nameShort"] for team in contest["teams"] if team["isHome"])
    away = next(team["nameShort"] for team in contest["teams"] if not team["isHome"])
    start = datetime.datetime.fromtimestamp(contest["startTimeEpoch"], datetime.timezone.utc)
    # NCAA's date is its own scoreboard date; the UTC epoch controls Review Today's CT day.
    status = {"P": "UPCOMING", "I": "LIVE", "F": "COMPLETED"}.get(contest.get("gameState"))
    if not status:
        raise ValueError("NCAA contest status changed")
    return {
        "id": str(contest["contestId"]), "source_id": source["id"],
        "sport": source["sport"], "league": source["league"],
        "region": source["region"], "name": f"{away} at {home}",
        "start_time": start.isoformat().replace("+00:00", "Z"),
        "status": status, "status_detail": contest.get("statusCodeDisplay") or "",
        "season_stage": "POSTSEASON" if contest.get("isChampionship") else None,
        "location": None, "source_endpoint": source["endpoint"],
    }
