"""Keep unresolved opponent placeholders out of scheduled match cards."""

import re


OPPONENTS = re.compile(r"\s+(?:vs\.?|at|v)\s+", re.I)
PLACEHOLDER = re.compile(r"(?:TBD|TBA|To Be Determined|To Be Announced)", re.I)


def unresolved_matchup(event):
    opponents = OPPONENTS.split(str(event.get("name") or ""))
    return len(opponents) == 2 and any(PLACEHOLDER.fullmatch(name.strip()) for name in opponents)
