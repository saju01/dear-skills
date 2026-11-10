"""Offline Microsoft Graph metadata collectors. No network calls or body text in output."""
import re
from collections import defaultdict
from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import quote
from zoneinfo import ZoneInfo

from .util import domain_of, iso, now_utc, parse_ts


ASK = re.compile(
    r"\b(can you|could you|would you|will you|please|let me know|"
    r"kun je|kun jij|kunt u|wil je|zou je|willen jullie|graag|laat .{0,15} weten|"
    r"kannst du|können sie|könnten sie|könnt ihr|bitte|"
    r"pouvez-vous|peux-tu|pourriez-vous|merci de|veuillez|"
    r"puedes|podrías|podéis|pueden|por favor|necesito que)\b", re.I)
DEADLINE = re.compile(
    r"\b(deadline|due|by (?:today|tomorrow|eod|cob|monday|tuesday|wednesday|thursday|friday)|"
    r"today|tomorrow|eod|cob|vandaag|morgen|uiterlijk|vóór|frist|fällig|heute|bis|"
    r"échéance|avant|aujourd'hui|demain|fecha límite|antes de|hasta|hoy|mañana|"
    r"\d{4}-\d{2}-\d{2})\b", re.I)


def rows(raw):
    """Accept a Graph value envelope, an object, or an array of objects/pages."""
    if isinstance(raw, list):
        return [row for part in raw for row in rows(part)]
    if not isinstance(raw, dict):
        raise ValueError("Expected a Graph object, value envelope, or array")
    if "error" in raw:
        raise ValueError("Graph error response; no metadata collected")
    if "value" in raw:
        if not isinstance(raw["value"], list):
            raise ValueError("Graph value must be an array")
        return rows(raw["value"])
    if not raw.get("id"):
        raise ValueError("Graph resource is missing id")
    return [raw]


def _address(recipient):
    return (((recipient or {}).get("emailAddress") or {}).get("address") or "").strip().lower()


def _addresses(recipients):
    return [address for r in recipients or [] if (address := _address(r))]


def _hints(text):
    match = DEADLINE.search(text or "")
    return {"has_question": bool("?" in (text or "") or ASK.search(text or "")),
            "deadline_hint": match.group(0).lower() if match else ""}


def mail(raw, me, profile=None):
    out = []
    me = me.strip().lower()
    for m in rows(raw):
        sender = _address(m.get("from") or m.get("sender"))
        to_me = me in _addresses(m.get("toRecipients"))
        out.append({
            "id": m["id"], "channel": "mail", "thread_id": m.get("conversationId", ""),
            "received_at": m.get("receivedDateTime", ""), "sender": sender,
            "sender_name": ((m.get("from") or m.get("sender") or {}).get("emailAddress") or {}).get("name", ""),
            "sender_domain": domain_of(sender), "subject": m.get("subject") or "",
            "to_me": to_me, "cc_only": not to_me and me in _addresses(m.get("ccRecipients")),
            **_hints(m.get("bodyPreview")),
            "is_read": bool(m.get("isRead")), "flagged": (m.get("flag") or {}).get("flagStatus") == "flagged",
            "categories": m.get("categories") or [], "importance": m.get("importance") or "normal",
            "other_tab": m.get("inferenceClassification") == "other",
            "is_invite": m.get("@odata.type", "").startswith("#microsoft.graph.eventMessage"),
        })
        if out[-1]["is_invite"] and m.get("event"):
            events = calendar(m["event"], profile or {})
            if events:
                # Retain the mail id for tag/read/flag; event id is only for RSVP.
                out[-1].update({k: events[0][k] for k in (
                    "event_id", "organizer", "start", "end", "invitees", "external", "is_series", "my_response")})
    return out


def sent(raw, received=None):
    """Match replies to the latest earlier received item in the same conversation."""
    by_thread = defaultdict(list)
    for item in received or []:
        if item.get("thread_id") and item.get("received_at"):
            by_thread[item["thread_id"]].append(item)
    out = []
    for m in rows(raw):
        item = {"id": m["id"], "conversation_id": m.get("conversationId", ""),
                "sent_at": m.get("sentDateTime", ""),
                "to": _addresses(m.get("toRecipients")), "cc": _addresses(m.get("ccRecipients")),
                "recipient_names": [r["emailAddress"]["name"].split()[0]
                                    for r in m.get("toRecipients") or []
                                    if (r.get("emailAddress") or {}).get("name", "").strip()],
                "is_meeting_response": m.get("@odata.type", "").startswith("#microsoft.graph.eventMessage")}
        t = parse_ts(item["sent_at"])
        candidates = [r for r in by_thread[item["conversation_id"]]
                      if t and parse_ts(r["received_at"]) < t
                      and r.get("sender") in item["to"] + item["cc"]]
        if candidates and not item["is_meeting_response"]:
            reply_to = max(candidates, key=lambda r: parse_ts(r["received_at"]))
            item.update({"in_reply_to_received_at": reply_to["received_at"],
                         "in_reply_to_sender": reply_to["sender"]})
        out.append(item)
    return out


def _event_time(value):
    dt = parse_ts(value["dateTime"])
    # Graph dateTimeTimeZone usually has a naive dateTime. Never silently treat
    # a non-UTC wall clock as UTC; adapters should request outlook.timezone="UTC".
    text = value["dateTime"]
    if not re.search(r"(Z|[+-]\d{2}:\d{2})$", text):
        dt = dt.replace(tzinfo=ZoneInfo(value.get("timeZone") or "UTC"))
    return iso(dt)


def calendar(raw, profile):
    internal = {d.lower() for d in profile.get("internal_domains", [])}
    out = []
    responses = {"notResponded": "none", "none": "none", "accepted": "accepted",
                 "tentativelyAccepted": "tentative", "declined": "declined", "organizer": "organizer"}
    for event in rows(raw):
        if event.get("isCancelled"):
            continue
        sender = _address(event.get("organizer"))
        out.append({
            "id": event["id"], "event_id": event["id"], "channel": "invite", "is_invite": True,
            "sender": sender, "organizer": sender, "sender_domain": domain_of(sender),
            "sender_name": (event.get("organizer", {}).get("emailAddress") or {}).get("name", ""),
            "subject": event.get("subject") or "", "start": _event_time(event["start"]),
            "end": _event_time(event["end"]), "invitees": len(event.get("attendees") or []),
            "external": any(domain_of(a) not in internal
                            for a in _addresses(event.get("attendees")) + ([sender] if sender else [])),
            "is_series": bool(event.get("seriesMasterId") or event.get("recurrence")
                              or event.get("type") == "seriesMaster"),
            "my_response": responses.get((event.get("responseStatus") or {}).get("response"), "none"),
        })
    return out


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def _working_hours(start, end, profile):
    zone = ZoneInfo(profile.get("tz") or "UTC")
    start, end = start.astimezone(zone), end.astimezone(zone)
    first, last = profile.get("working_hours") or [9, 17]
    hours, day = 0, start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day < end:
        if day.weekday() < 5:
            left, right = max(start, day + timedelta(hours=first)), min(end, day + timedelta(hours=last))
            hours += max(0, (right - left).total_seconds() / 3600)
        day += timedelta(days=1)
    return hours


def teams(raw, me_id, profile=None, chats=None, now=None):
    """Surface unanswered questions, mentions, and overdue one-to-one messages."""
    profile, now = profile or {}, now or now_utc()
    chat_index = {c["id"]: c for c in rows(chats or [])}
    threads = defaultdict(list)
    for m in rows(raw):
        if not m.get("chatId"):
            raise ValueError("Teams messages need chatId (add the fetched chat id when saving)")
        threads[m["chatId"]].append(m)
    out = []
    for thread, messages in sorted(threads.items()):
        latest = max(messages, key=lambda m: parse_ts(m.get("createdDateTime")))
        if latest.get("deletedDateTime") or latest.get("messageType", "message") != "message":
            continue
        user = (latest.get("from") or {}).get("user") or {}
        if not user or user.get("id") == me_id:
            continue
        chat = chat_index.get(thread, {})
        direct = chat.get("chatType") == "oneOnOne"
        mentions = any(((m.get("mentioned") or {}).get("user") or {}).get("id") == me_id
                       for m in latest.get("mentions") or [])
        body = latest.get("body") or {}
        text = body.get("content") or ""
        if body.get("contentType") == "html":
            parser = _Text()
            parser.feed(text)
            text = " ".join(parser.parts)
        hints = _hints(text)
        received = parse_ts(latest["createdDateTime"])
        overdue = direct and _working_hours(received, now, profile) >= profile.get("teams_reply_hours", 4)
        if not (mentions or hints["has_question"] or overdue):
            continue
        sender = (user.get("email") or user.get("userPrincipalName") or user.get("id") or "").lower()
        out.append({"id": quote(thread, safe="") + "/" + quote(latest["id"], safe=""),
                    "message_id": latest["id"], "channel": "teams", "thread_id": thread,
                    "received_at": latest["createdDateTime"], "sender": sender,
                    "sender_name": user.get("displayName") or "", "sender_domain": domain_of(sender),
                    "subject": chat.get("topic") or "", "mentions_me": mentions, "direct": direct,
                    "to_me": direct or mentions, "cc_only": False, **hints})
    return out
