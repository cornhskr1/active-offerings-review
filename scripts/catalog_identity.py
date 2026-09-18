#!/usr/bin/env python3
"""Strict identity helpers for catalog and event cross-references.

These helpers deliberately avoid substring and token-overlap matching.  A
display-name resemblance is never sufficient evidence that two competitions or
teams are the same entity.
"""

from __future__ import annotations

import re
import unicodedata


TEAM_ALIASES = {
    "union berlin": {"1 fc union berlin"},
    "rc lens": {"lens"},
    "ogc nice": {"nice"},
    "estac troyes": {"troyes"},
    "aj auxerre": {"auxerre"},
    "as roma": {"roma"},
    "ajax": {"ajax amsterdam"},
    "olympique lyonnais": {"lyon"},
    "royal antwerp": {"antwerp"},
    "new york red bulls": {"red bull new york"},
    "red bull new york": {"new york red bulls"},
    "usc": {"usc trojans"},
    "georgia state": {"georgia state panthers"},
    "miami": {"miami hurricanes"},
}


def normalize_identity(value: object) -> str:
    """Normalize punctuation and accents while retaining identity-bearing words."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def event_sides(event_name: object) -> tuple[str, ...]:
    """Return exact participant sides from a conventional matchup label."""
    value = str(event_name or "").strip()
    parts = re.split(r"\s+(?:at|vs\.?|v\.?)\s+", value, maxsplit=1, flags=re.I)
    if len(parts) != 2:
        return ()
    sides = tuple(normalize_identity(part) for part in parts)
    return sides if all(sides) else ()


def team_event_match(
    team: object,
    expected_league: object,
    event_name: object,
    event_league: object,
) -> tuple[bool, str | None]:
    """Require exact league identity plus an exact team side or reviewed alias."""
    team_id = normalize_identity(team)
    expected_league_id = normalize_identity(expected_league)
    event_league_id = normalize_identity(event_league)
    if not team_id or not expected_league_id or expected_league_id != event_league_id:
        return False, None

    sides = event_sides(event_name)
    if team_id in sides:
        return True, "EXACT TEAM + LEAGUE"
    if any(alias in sides for alias in TEAM_ALIASES.get(team_id, set())):
        return True, "APPROVED ALIAS + LEAGUE"
    return False, None


def exact_team_in_event(team: object, event_name: object) -> tuple[bool, str | None]:
    """Require an exact parsed side or a reviewed alias when league is fixed upstream."""
    team_id = normalize_identity(team)
    sides = event_sides(event_name)
    if team_id and team_id in sides:
        return True, "EXACT TEAM"
    if team_id and any(alias in sides for alias in TEAM_ALIASES.get(team_id, set())):
        return True, "APPROVED ALIAS"
    return False, None


def restriction_scope(text: object) -> str:
    """Extract the exact competition label preceding a restriction instruction."""
    value = str(text or "").strip()
    return re.split(
        r"\s+(?:-\s+|\|\s+)(?=(?:NO|MARKETS|WAGER|LIMIT|\$))",
        value,
        maxsplit=1,
        flags=re.I,
    )[0].strip()


def exact_league_match(event_league: object, restricted_league: object) -> bool:
    return bool(
        normalize_identity(event_league)
        and normalize_identity(event_league) == normalize_identity(restricted_league)
    )
