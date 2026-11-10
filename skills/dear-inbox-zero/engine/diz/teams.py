"""Teams response filtering and signals from the user's own posts."""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .util import iso, parse_ts, working_days_between


def _working_hours_between(start, end, profile):
    if end <= start:
        return 0.0
    try:
        zone = ZoneInfo(profile.get("tz") or "UTC")
    except (ValueError, KeyError):
        zone = timezone.utc
    hours = profile.get("working_hours") or [9, 17]
    try:
        day_start, day_end = float(hours[0]), float(hours[1])
        if not (0 <= day_start < day_end <= 24):
            raise ValueError
    except (TypeError, ValueError, IndexError):
        day_start, day_end = 9.0, 17.0
    local_start, local_end = start.astimezone(zone), end.astimezone(zone)
    total = 0.0
    current = local_start.date()
    while current <= local_end.date():
        if current.weekday() < 5:
            window_start = datetime.combine(current, time.min, zone) + timedelta(hours=day_start)
            window_end = datetime.combine(current, time.min, zone) + timedelta(hours=day_end)
            left = max(start.astimezone(timezone.utc), window_start.astimezone(timezone.utc))
            right = min(end.astimezone(timezone.utc), window_end.astimezone(timezone.utc))
            if right > left:
                total += (right - left).total_seconds() / 3600
        current += timedelta(days=1)
    return total


def _timestamp(message):
    return parse_ts(message.get("sent_at") or message.get("created_at") or message.get("received_at"))


def needs_response(chats, profile, user_id, now=None):
    """Return each chat's latest incoming message when it needs a response."""
    now = now or datetime.now(timezone.utc)
    threshold = float(profile.get("teams_reply_hours", 4))
    result = []
    for chat in chats:
        messages = [m for m in chat.get("messages", []) if _timestamp(m)]
        if not messages:
            continue
        latest = max(messages, key=_timestamp)
        sender_id = latest.get("sender_id") or latest.get("from_user_id")
        if latest.get("is_me") is True or (user_id and sender_id == user_id):
            continue
        sent_at = _timestamp(latest)
        direct = bool(chat.get("direct"))
        has_question = bool(latest.get("has_question"))
        mentions_me = bool(latest.get("mentions_me"))
        waited = direct and _working_hours_between(sent_at, now, profile) >= threshold
        if not (has_question or mentions_me or waited):
            continue
        result.append({
            "id": latest.get("id"),
            "channel": "teams",
            "thread_id": chat.get("thread_id") or chat.get("id"),
            "sender": latest.get("sender") or "",
            "sender_name": latest.get("sender_name") or "",
            "sender_domain": latest.get("sender_domain") or "",
            "subject": chat.get("subject") or chat.get("topic") or "",
            "mentions_me": mentions_me,
            "direct": direct,
            "has_question": has_question,
            "received_at": iso(sent_at),
            "preview": (latest.get("preview") or latest.get("text") or "")[:300],
        })
    return result


def signals(posts, state, user_id, now=None):
    """Derive Teams reply outcomes only from user-authored posts."""
    now = now or datetime.now(timezone.utc)
    head = state["head"]
    decisions = [d for d in (head.get("last_run") or {}).get("decisions", [])
                 if d.get("channel") == "teams" and d.get("thread_id")]
    by_thread = {}
    for decision in decisions:
        by_thread.setdefault(decision["thread_id"], []).append(decision)
    for loop in head.get("ledger", []):
        if loop.get("channel") == "teams" and loop.get("state") == "open" and loop.get("thread_id"):
            entries = by_thread.setdefault(loop["thread_id"], [])
            if not any(d.get("id") == loop.get("id") for d in entries):
                entries.append(loop)

    own_posts = []
    for post in posts:
        sender_id = post.get("sender_id") or post.get("from_user_id")
        if post.get("is_me") is True or (user_id and sender_id == user_id):
            at = _timestamp(post)
            if at:
                own_posts.append((post, at))

    result, replied = [], set()
    posts_by_thread = {}
    for post, at in own_posts:
        thread_id = post.get("thread_id") or post.get("conversation_id")
        if not thread_id:
            continue
        posts_by_thread.setdefault(thread_id, []).append((post, at))
        for decision in by_thread.get(thread_id, []):
            received = parse_ts(decision.get("received_at"))
            if received and at > received and decision.get("id") not in replied:
                result.append({"id": decision["id"], "signal": "replied", "thread_id": thread_id, "at": iso(at)})
                replied.add(decision["id"])
        if thread_id not in by_thread:
            result.append({
                "id": post.get("id") or thread_id,
                "signal": "replied_not_proposed",
                "channel": "teams",
                "thread_id": thread_id,
                "sender": post.get("reply_to_sender") or post.get("contact") or "",
                "at": iso(at),
            })

    for loop in head.get("ledger", []):
        if loop.get("channel") != "teams" or loop.get("state") != "open":
            continue
        since = parse_ts(loop.get("received_at") or loop.get("first_reported")) or now
        has_reply = any(at > since for _, at in posts_by_thread.get(loop.get("thread_id"), []))
        if not has_reply and working_days_between(since, now) >= 2:
            result.append({"id": loop["id"], "signal": "ignored", "thread_id": loop.get("thread_id"), "at": iso(now)})
    return result
