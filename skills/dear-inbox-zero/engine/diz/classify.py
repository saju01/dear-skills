"""Rules first: assign a bucket to each item and plan actions within autonomy and safety."""
import re
from . import CATEGORY, FORBIDDEN_ACTIONS
from .util import series_key, domain_of, parse_ts

INFERRED_THRESHOLD = 0.8
GUARD = re.compile(r"\b(security|password|compliance|verify|verification|sign-?in|mfa|2fa|fraud|"
                   r"invoice (is )?(due|overdue)|payment (due|failed)|account (locked|suspended)|device)\b", re.I)


def normalise(item):
    it = dict(item)
    it["sender"] = (it.get("sender") or it.get("organizer") or "").lower()
    it["sender_domain"] = (it.get("sender_domain") or domain_of(it["sender"])).lower()
    if not it.get("series"):
        it["series"] = series_key(it.get("subject", ""))
    it.setdefault("channel", "mail")
    return it


def _rules(facts, paused):
    rules = [f for f in facts if f.get("kind") == "rule"]
    for r in rules:
        r["_paused"] = r["id"] in paused
    return rules


def _match(rules, it, origin, buckets):
    """Series > exact sender > domain, among rules of one origin."""
    keys = (("series", it["series"]), ("sender", it["sender"]), ("domain", it["sender_domain"]))
    for scope, key in keys:
        if not key:
            continue
        for r in rules:
            if r.get("scope") == scope and r.get("key") == key and r.get("bucket") in buckets:
                if origin == "explicit" and r.get("origin") == "explicit":
                    return r
                if origin == "inferred" and r.get("origin") == "inferred" \
                        and float(r.get("confidence", 0)) >= INFERRED_THRESHOLD:
                    return r
    return None


def _people(facts, profile, flag):
    out = set(x.lower() for x in profile.get(flag, []))
    for f in facts:
        if f.get("kind") == "person" and f.get(flag):
            out.add(f.get("key", "").lower())
    return out


def assign(it, facts, profile, rules):
    """Return (bucket, reason, rule) for a mail or Teams item."""
    vip = _people(facts, profile, "vip")
    personal = set(x.lower() for x in profile.get("personal", []))
    for r in rules:
        if r.get("bucket") == "personal" and r.get("origin") == "explicit":
            personal.add(r.get("key", ""))
    if it["sender"] in personal or it["sender_domain"] in personal:
        return "personal", "personal_pin", None
    series_rule = _match(rules, it, "explicit", ("noise", "fyi"))
    if it["sender"] in vip and not (series_rule and series_rule.get("scope") == "series" and series_rule.get("beats_vip")):
        return "reply", "vip", None
    respond = _match(rules, it, "explicit", ("reply",))
    if respond:
        return "reply", "respond_rule", respond
    if it["channel"] == "teams":
        if series_rule:
            return "fyi", "teams_rule", series_rule
        return "reply", "teams_needs_response", None
    if it.get("to_me") and it.get("has_question"):
        return "reply", "direct_ask", None
    if it.get("deadline_hint") and it.get("to_me"):
        return "reply", "deadline", None
    guard = bool(GUARD.search(it.get("subject", "")))
    if series_rule:
        if guard and series_rule["bucket"] == "noise":
            return "fyi", "guard", series_rule
        return series_rule["bucket"], f"explicit_{series_rule['scope']}", series_rule
    inferred = _match(rules, it, "inferred", ("noise", "fyi", "reply"))
    if inferred:
        if guard and inferred["bucket"] == "noise":
            return "fyi", "guard", inferred
        return inferred["bucket"], f"inferred_{inferred['scope']}", inferred
    if guard:
        return "fyi", "guard", None
    return "unknown", "no_rule", None


def plan_actions(it, bucket, rule, levels, dry_run=False):
    if dry_run or bucket == "unknown":
        return []
    acts = []
    if it["channel"] == "mail":
        lvl = levels.get(bucket if bucket != "personal" else "fyi", 0)
        if lvl >= 1:
            acts.append({"op": "tag", "category": CATEGORY[bucket]})
        paused = bool(rule and rule.get("_paused"))
        if bucket == "noise" and lvl >= 2 and rule and rule.get("origin") == "explicit" and not paused:
            acts.append({"op": "mark_read"})
        if bucket == "fyi" and lvl >= 2 and not paused:
            acts.append({"op": "mark_read"})
        if bucket == "reply" and lvl >= 1:
            acts.append({"op": "draft"})
            if lvl >= 2 and not it.get("flagged"):
                acts.append({"op": "flag"})
    elif it["channel"] == "teams" and bucket == "reply":
        acts.append({"op": "suggest_reply"})
    for a in acts:
        assert a["op"] not in FORBIDDEN_ACTIONS
    return acts


def _overlaps(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end


def recommend_invite(it, facts, profile, rules, calendar, levels, dry_run=False):
    personal = set(x.lower() for x in profile.get("personal", []))
    is_personal = it["sender"] in personal or it["sender_domain"] in personal
    start, end = parse_ts(it.get("start")), parse_ts(it.get("end"))
    clashes = []
    if start and end:
        for ev in calendar:
            if ev.get("event_id") == it.get("event_id"):
                continue
            if ev.get("my_response") not in ("accepted", "organizer") and not ev.get("external"):
                continue
            es, ee = parse_ts(ev.get("start")), parse_ts(ev.get("end"))
            if es and ee and _overlaps(start, end, es, ee):
                clashes.append({"subject": ev.get("subject", ""), "start": ev.get("start"), "end": ev.get("end")})
    accept_rule = None
    for scope, key in (("series", it["series"]), ("sender", it["sender"]), ("domain", it["sender_domain"])):
        for r in rules:
            if r.get("scope") == scope and r.get("key") == key and r.get("bucket") == "accept" \
                    and r.get("origin") == "explicit" and not r.get("_paused"):
                accept_rule = r
                break
        if accept_rule:
            break
    acts, rec, reason = [], "ask", "no_rule"
    threshold = int(profile.get("broadcast_threshold", 50))
    if it.get("my_response") in ("accepted", "organizer"):
        rec, reason = "done", "already_answered"
        acts = [{"op": "mark_read"}]
    elif clashes:
        rec, reason = "ask", "clash"
        acts = [{"op": "flag"}]
    elif int(it.get("invitees") or 0) >= threshold and not accept_rule:
        rec, reason = "fyi", "broadcast"
    elif accept_rule and (not it.get("event_id") or not start or not end):
        rec, reason = "ask", "incomplete_event"
    elif accept_rule and not profile.get("invite_accept", False):
        rec, reason = "ask", "accept_off"
    elif accept_rule and (levels.get("calendar", 0) >= 3 or (is_personal and levels.get("calendar", 0) >= 1)):
        rec, reason = "accept", "confirmed_rule"
        acts = [{"op": "accept", "occurrence_only": not accept_rule.get("series_ok", False)}, {"op": "mark_read"}]
    elif accept_rule:
        rec, reason = "ask", "rule_waiting_for_autonomy"
    if dry_run:
        acts = []
    return {"bucket": "personal" if is_personal else "calendar", "recommendation": rec, "reason": reason,
            "rule_id": accept_rule["id"] if accept_rule else None, "clashes": clashes, "actions": acts}


def classify(state, items, calendar=None, dry_run=False):
    head, facts = state["head"], state["facts"]
    profile = head["profile"]
    rules = _rules(facts, set(head.get("paused_rules", [])))
    levels = {b: v["level"] for b, v in head["autonomy"].items()}
    out = []
    for raw in items:
        it = normalise(raw)
        base = {"id": it["id"], "channel": it["channel"], "sender": it["sender"], "sender_name": it.get("sender_name", ""),
                "subject": it.get("subject", ""), "series": it["series"], "received_at": it.get("received_at"),
                "thread_id": it.get("thread_id")}
        if it["channel"] == "invite" or it.get("is_invite"):
            base["channel"] = "invite"
            r = recommend_invite(it, facts, profile, rules, calendar or [], levels, dry_run)
            base.update(r)
            base.update({"start": it.get("start"), "end": it.get("end"), "invitees": it.get("invitees")})
        else:
            bucket, reason, rule = assign(it, facts, profile, rules)
            base.update({"bucket": bucket, "reason": reason, "rule_id": rule["id"] if rule else None,
                         "actions": plan_actions(it, bucket, rule, levels, dry_run)})
        out.append(base)
    unknown = [d["id"] for d in out if d.get("bucket") == "unknown"]
    return {"dry_run": dry_run, "decisions": out, "unknown": unknown}
