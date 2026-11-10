"""Open loops: Reply items and invites waiting for the user, with working days elapsed."""
from .util import iso, now_utc, parse_ts, working_days_between

CLOSING = {"replied", "flag_completed", "answered_after_ask", "answered_differently", "tag_removed",
           "draft_binned", "flag_removed"}


def update(head, decisions, signals, now=None):
    now = now or now_utc()
    led = {l["id"]: l for l in head.get("ledger", [])}
    for d in decisions:
        open_loop = (d.get("bucket") == "reply") or (d.get("channel") == "invite" and d.get("recommendation") == "ask")
        if not open_loop:
            continue
        l = led.get(d["id"])
        if l is None:
            led[d["id"]] = {"id": d["id"], "channel": d.get("channel"), "who": d.get("sender_name") or d.get("sender"),
                            "subject": (d.get("subject") or "")[:120], "first_reported": iso(now),
                            "last_reported": iso(now), "received_at": d.get("received_at"), "state": "open"}
        elif l["state"] == "open":
            l["last_reported"] = iso(now)
    for s in signals or []:
        l = led.get(s.get("id"))
        if l and l["state"] == "open" and s.get("signal") in CLOSING:
            l["state"], l["closed_at"] = "closed", iso(now)
    head["ledger"] = list(led.values())
    return head["ledger"]


def aged(head, now=None, min_days=2):
    now = now or now_utc()
    out = []
    for l in head.get("ledger", []):
        if l.get("state") != "open":
            continue
        since = parse_ts(l.get("received_at") or l.get("first_reported")) or now
        days = working_days_between(since, now)
        if days >= min_days:
            out.append({**l, "working_days": days})
    return sorted(out, key=lambda x: -x["working_days"])
