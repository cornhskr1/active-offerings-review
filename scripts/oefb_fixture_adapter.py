"""Exact ÖFB senior competition fixtures from the federation's public round JSON."""

import datetime
import json
import re
from urllib.parse import quote, urlparse
from zoneinfo import ZoneInfo


VIENNA = ZoneInfo("Europe/Vienna")
PROXY_ORIGIN = "https://www.oefb.at"
COMPETITIONS = {
    "uefa-soccer-austria-austrian-frauen-bundesliga-women": ("232361", "ADMIRAL Frauen Bundesliga - Grunddurchgang", "Meisterschaft", "KM Frauen", {r: 5 for r in range(1, 19)}),
    "uefa-soccer-austria-austrian-cup-men": ("232362", "UNIQA ÖFB Cup", "Cup", "KM", {2: 16, 3: 8}),
    "uefa-soccer-austria-fb-frauen-cup-women": ("232363", "ÖFB Frauen Cup", "Cup", "KM Frauen", {1: 16, 2: 8}),
}


def current_and_next_rounds(page, source):
    """Read the selected round and its successor from the publisher page."""
    expected_id, title, _, _, _ = COMPETITIONS[source["id"]]
    for match in re.finditer(r"SG\.container\.appPreloads\['[^']+'\]=", page):
        try:
            value, _ = json.JSONDecoder().raw_decode(page[match.end():])
            item = value[0] if isinstance(value, list) and value else {}
        except (ValueError, TypeError, IndexError):
            continue
        if not isinstance(item, dict):
            continue
        if str(item.get("id")) != expected_id or item.get("title") != title or "runden" not in item:
            continue
        rounds = [x for x in item["runden"] if isinstance(x.get("runde"), int) and x["runde"] > 0]
        if not rounds or len({x["runde"] for x in rounds}) != len(rounds):
            raise ValueError("ÖFB round list is empty or duplicated")
        active = [x["runde"] for x in rounds if x.get("aktuell")]
        if not active:
            raise ValueError("ÖFB active round is unidentified")
        selected = max(active)
        available = {x["runde"] for x in rounds}
        return [r for r in (selected, selected + 1) if r in available]
    raise ValueError("ÖFB competition identity or round preload changed")


def round_url(source, round_number, page):
    competition_id = COMPETITIONS[source["id"]][0]
    match = re.search(r'SG\.container\.deliveryInfo\.project\s*=\s*\{[^}]*"oid":"(\d+)"', page)
    if not match:
        raise ValueError("ÖFB public proxy project identity missing")
    project_id = match.group(1)
    internal = ("http://portale-datenservice:8080/datenservice/rest/oefb/spielbetrieb/"
                f"spielplanBewerbByPublicUid/{competition_id};runde={round_number}")
    key = f"spielbetrieb_spielplan_{competition_id}_{round_number}.json"
    return (f"{PROXY_ORIGIN}/proxy/oefb3/{project_id}_{key}"
            f"?proxyUrl={quote(internal, safe='')}")


def parse_round(payload, source, round_number):
    competition_id, title, kind, team_type, round_sizes = COMPETITIONS[source["id"]]
    expected_count = round_sizes.get(round_number)
    if expected_count is None:
        raise ValueError("ÖFB round outside verified 2026–27 publication")
    if (str(payload.get("id")) != competition_id or payload.get("title") != title
            or source.get("catalog_terms") != [source["league"]]):
        raise ValueError("ÖFB competition or catalog scope changed")
    rows = (payload.get("spiele") or []) + (payload.get("ergebnisse") or [])
    if len(rows) != expected_count:
        raise ValueError(f"ÖFB round {round_number} has {len(rows)} fixtures; expected {expected_count}")
    fixtures, held, seen = [], 0, set()
    for row in rows:
        home, away = (str(row.get(k) or "").strip() for k in ("heimMannschaft", "gastMannschaft"))
        link = str(row.get("actionLink") or "")
        parsed = urlparse(link)
        identity = re.search(r"/Spiel/(?:Spielbericht/)?(\d+)/", parsed.path)
        if (row.get("runde") != round_number or row.get("bewerb") != title
                or row.get("spielart") != kind or row.get("teamType") != team_type
                or not home or not away or home == away
                or not row.get("heimMannschaftId") or not row.get("gastMannschaftId")
                or parsed.hostname != "www.oefb.at" or not identity or identity.group(1) in seen):
            raise ValueError("ÖFB round fixture identity, pairing, or senior scope changed")
        seen.add(identity.group(1))
        try:
            kickoff = datetime.datetime.fromtimestamp(int(row["anstoss"]) / 1000, datetime.timezone.utc)
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            raise ValueError("ÖFB kickoff timestamp changed") from exc
        if row.get("status") != "offen":
            continue
        # The federation uses local 00:00 for fixtures whose kickoff is TBD.
        if kickoff.astimezone(VIENNA).time() == datetime.time(0, 0):
            held += 1
            continue
        fixtures.append({
            "id": f"oefb-{competition_id}-{identity.group(1)}", "source_id": source["id"],
            "sport": source["sport"], "league": source["league"], "region": source["region"],
            "name": f"{away} at {home}", "start_time": kickoff.isoformat().replace("+00:00", "Z"),
            "status": "UPCOMING", "status_detail": "ÖFB official senior fixture",
            "season_stage": "REGULAR" if kind == "Meisterschaft" else "CUP",
            "location": row.get("spielortStadt") or None, "source_endpoint": link,
        })
    return fixtures, held, len(rows)
