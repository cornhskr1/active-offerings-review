"""FSF's current senior men's MeistaraDeildin round, from its public COMET feed."""

import datetime


SOURCE_ID = "uefa-soccer-faroe-islands-faroe-islands-premier-league-men"
COMPETITION_ID = 6654857
COMPETITION_NAME = "Meistaradeildin menn 2026"
MATCH_URL = "https://www.fsf.fo/kappingar/dystur/?matchID="


def next_round(payload, source, now):
    if source["id"] != SOURCE_ID or source.get("catalog_terms") != [source["league"]]:
        raise ValueError("FSF catalog scope changed")
    if not isinstance(payload, list) or len(payload) != 135:
        raise ValueError("FSF 27-round senior league feed incomplete")
    if len({row.get("id") for row in payload}) != len(payload):
        raise ValueError("FSF match identifiers repeated")
    rounds = {}
    for row in payload:
        competition = row.get("competition") or {}
        if competition.get("id") != COMPETITION_ID or competition.get("name") != COMPETITION_NAME:
            raise ValueError("FSF senior league edition changed")
        try:
            number = int(row["round"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("FSF round changed") from None
        if not 1 <= number <= 27 or row.get("roundOrder") != number:
            raise ValueError("FSF round order changed")
        rounds.setdefault(number, []).append(row)
    if len(rounds) != 27 or any(len(rows) != 5 for rows in rounds.values()):
        raise ValueError("FSF five-match round structure changed")
    future = [row for row in payload if row.get("liveStatus") == "SCHEDULED"
              and isinstance(row.get("dateTimeUTC"), int)
              and datetime.datetime.fromtimestamp(row["dateTimeUTC"] / 1000, datetime.timezone.utc) > now]
    if not future:
        return [], len(payload)
    number = min(int(row["round"]) for row in future)
    selected = rounds[number]
    if len(future) < 5 or any(row not in future for row in selected):
        raise ValueError("FSF next round has unconfirmed fixtures")
    teams = []
    events = []
    for row in selected:
        home, away = row.get("homeTeam") or {}, row.get("awayTeam") or {}
        facility = row.get("facility") or {}
        if (not isinstance(row.get("id"), int) or not home.get("name") or not away.get("name")
                or not home.get("id") or not away.get("id") or not facility.get("name")
                or not facility.get("id") or row.get("homeTeamResult", {}).get("current") is not None
                or row.get("awayTeamResult", {}).get("current") is not None):
            raise ValueError("FSF next-round pairing, venue or unplayed status changed")
        teams.extend((home["id"], away["id"]))
        start = datetime.datetime.fromtimestamp(row["dateTimeUTC"] / 1000, datetime.timezone.utc)
        events.append({"id": f"fsf-meistaradeildin-{row['id']}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{away['name']} at {home['name']}",
            "start_time": start.isoformat().replace("+00:00", "Z"), "status": "UPCOMING",
            "status_detail": f"Official 2026 MeistaraDeildin round {number}",
            "season_stage": "REGULAR", "location": facility["name"],
            "source_endpoint": MATCH_URL + str(row["id"])})
    if len(set(teams)) != 10:
        raise ValueError("FSF next round has repeated team")
    return events, len(payload)
