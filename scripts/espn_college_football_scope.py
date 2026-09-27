"""Keep FBS and FCS fixtures separate; hold cross-subdivision games."""

import re


def exclusive_events(payload, other_payload, group):
    expected = str(group)
    counterpart = "81" if expected == "80" else "80"
    if expected not in ("80", "81"):
        raise ValueError("Unrecognized college football subdivision")
    for data, group_id in ((payload, expected), (other_payload, counterpart)):
        if list(map(str, data.get("groups") or [])) != [group_id]:
            raise ValueError("ESPN college football group identity changed")
        rows = data.get("events")
        if not isinstance(rows, list) or len(rows) >= 500:
            raise ValueError("ESPN college football fixture list missing or truncated")
        for event in rows:
            competitors = (event.get("competitions") or [{}])[0].get("competitors") or []
            uid = str(event.get("uid") or "")
            if (not event.get("id") or not event.get("date")
                    or not re.search(r"(?:^|~)l:23(?:~|$)", uid)
                    or len(competitors) != 2
                    or not all((side.get("team") or {}).get("displayName") for side in competitors)):
                raise ValueError("ESPN college football fixture lacks exact teams or league identity")
    other_ids = {str(event["id"]) for event in other_payload["events"]}
    held = [event for event in payload["events"] if str(event["id"]) in other_ids]
    return [event for event in payload["events"] if str(event["id"]) not in other_ids], held
