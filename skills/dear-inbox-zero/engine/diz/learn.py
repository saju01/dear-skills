"""Learning loop: signals -> proposals -> confirmed rules; expiry; autonomy ladder."""
from datetime import timedelta
from . import AUTONOMY_BUCKETS, MAX_LEVEL, PRESETS, DEFAULT_PRESET
from .util import parse_ts, iso, now_utc, sha256

WINDOW_DAYS = 7
PROPOSAL_DAYS = 14
RETIRE_DAYS = 30
BLOCK_DAYS = 60
MIN_SIGNALS = 2

# signal -> direction (target bucket / calendar outcome); None = no direction
DIRECTION = {
    "tag_removed": "fyi", "marked_unread": "fyi", "flag_removed": "fyi", "draft_binned": "fyi",
    "ignored": "fyi", "replied": "reply", "replied_not_proposed": "reply", "flag_added": "reply",
    "flag_completed": "reply", "draft_edited_heavily": None, "left_unanswered": None,
    "clash_resolved": None,
}
WRONG = {"marked_unread", "draft_binned"}


def direction_of(sig):
    s = sig.get("signal") or ""
    if s.startswith("tag_changed:"):
        return s.split(":", 1)[1]
    if s in ("answered_differently", "answered_after_ask"):
        return "accept" if (sig.get("response") or "").lower() == "accepted" else "ask"
    return DIRECTION.get(s)


def decided_bucket(dec):
    if dec.get("channel") == "invite":
        return "accept" if dec.get("recommendation") == "accept" else "ask"
    return dec.get("bucket")


def autonomy_bucket(dec):
    if dec.get("channel") == "invite":
        return "calendar"
    b = dec.get("bucket")
    return b if b in AUTONOMY_BUCKETS else None


def observe(state, signals, now=None):
    """Attach this run's signals to the 7-day window; score the last run per autonomy bucket."""
    now = now or now_utc()
    head = state["head"]
    last = {d["id"]: d for d in ((head.get("last_run") or {}).get("decisions") or [])}
    enriched = []
    for sig in signals or []:
        dec = last.get(sig.get("id"))
        if dec is None:
            if sig.get("channel") != "teams" or sig.get("signal") != "replied_not_proposed":
                continue  # only decided items, plus own Teams replies to unsurfaced threads
            d = direction_of(sig)
            enriched.append({**sig, "at": sig.get("at") or iso(now), "series": sig.get("series"),
                             "sender": sig.get("sender"), "decided": None, "direction": d,
                             "by_series": False, "outcome": "override", "rule_id": None,
                             "abucket": None, "wrong": False})
            continue
        d = direction_of(sig)
        decided = decided_bucket(dec)
        outcome = None if d is None else ("agree" if d == decided else "override")
        enriched.append({**sig, "at": sig.get("at") or iso(now), "series": dec.get("series"), "sender": dec.get("sender"),
                         "decided": decided, "direction": d, "by_series": (dec.get("reason") or "").endswith("_series"), "outcome": outcome, "rule_id": dec.get("rule_id"),
                         "abucket": autonomy_bucket(dec), "wrong": sig.get("signal") in WRONG
                         or (sig.get("signal") == "answered_differently" and dec.get("recommendation") == "accept")})
    cutoff = now - timedelta(days=WINDOW_DAYS)
    window = [s for s in head.get("signals", []) if (parse_ts(s.get("at")) or now) >= cutoff]
    seen = {(s.get("id"), s.get("signal")) for s in window}
    window += [s for s in enriched if (s.get("id"), s.get("signal")) not in seen]
    head["signals"] = window
    # support for inferred rules
    for s in enriched:
        if s["outcome"] == "agree" and s.get("rule_id"):
            head.setdefault("rule_support", {})[s["rule_id"]] = iso(now)
    # score the last run
    stats = {}
    for dec in last.values():
        b = autonomy_bucket(dec)
        if b:
            stats.setdefault(b, {"decisions": 0, "overrides": 0, "wrong": 0})["decisions"] += 1
    for s in enriched:
        b = s.get("abucket")
        if b and b in stats:
            if s["outcome"] == "override":
                stats[b]["overrides"] += 1
            if s["wrong"]:
                stats[b]["wrong"] += 1
    head["_run_stats"] = stats
    return {"signals": len(enriched), "stats": stats}


def _blocked(head, facts, scope, key, bucket, now):
    for f in facts:
        if f.get("kind") == "correction" and f.get("scope") == scope and f.get("key") == key \
                and f.get("bucket") == bucket:
            at = parse_ts(f.get("created_at")) or now
            if now - at < timedelta(days=BLOCK_DAYS):
                return True
    for f in facts:
        if f.get("kind") == "rule" and f.get("origin") == "explicit" and f.get("scope") == scope \
                and f.get("key") == key:
            return True  # never override an explicit rule by inference
    return False


def propose(state, now=None):
    now = now or now_utc()
    head, facts = state["head"], state["facts"]
    groups = {}
    for s in head.get("signals", []):
        if s.get("outcome") != "override" or not s.get("direction"):
            continue
        scope, key = ("series", s["series"]) if (s.get("by_series") and s.get("series")) else ("sender", s.get("sender"))
        if not key:
            continue
        groups.setdefault((scope, key), []).append(s)
    created, inconsistent = [], []
    open_keys = {(p["scope"], p["key"]) for p in head["proposals"] if p.get("state") == "open"}
    for (scope, key), sigs in groups.items():
        dirs = {s["direction"] for s in sigs}
        if len(dirs) > 1:
            inconsistent.append({"scope": scope, "key": key, "directions": sorted(dirs)})
            continue
        if len(sigs) < MIN_SIGNALS or (scope, key) in open_keys:
            continue
        bucket = dirs.pop()
        if _blocked(head, facts, scope, key, bucket, now):
            continue
        p = {"scope": scope, "key": key, "bucket": bucket, "evidence": sorted({s["id"] for s in sigs}),
             "created_at": iso(now), "expires_at": iso(now + timedelta(days=PROPOSAL_DAYS)), "state": "open"}
        p["id"] = "p-" + sha256([scope, key, bucket, p["created_at"]])[:12]
        head["proposals"].append(p)
        state["new_facts"].append({"kind": "rule", "scope": scope, "key": key, "bucket": bucket,
                                   "origin": "inferred", "confidence": 0.6, "evidence": p["evidence"],
                                   "proposal_id": p["id"]})
        created.append(p)
    return {"created": created, "inconsistent": inconsistent}


def apply_answers(state, answers, now=None):
    """answers: [{proposal_id, answer: confirm|reject}] or [{scope, key, bucket, answer: rule}] or
    [{person, vip|personal: true}] or [{fact: {...}}] (voice, preference)."""
    now = now or now_utc()
    head = state["head"]
    done = []
    by_id = {p["id"]: p for p in head["proposals"]}
    for a in answers or []:
        if a.get("proposal_id"):
            p = by_id.get(a["proposal_id"])
            if not p or p.get("state") != "open":
                continue
            p["state"] = "confirmed" if a.get("answer") == "confirm" else "rejected"
            p["closed_at"] = iso(now)
            for f in state["facts"]:
                if f.get("proposal_id") == p["id"] and f.get("origin") == "inferred":
                    state["superseded"].append({"old_id": f["id"]})
            state["new_facts"] = [f for f in state["new_facts"] if f.get("proposal_id") != p["id"]]
            if p["state"] == "confirmed":
                state["new_facts"].append({"kind": "rule", "scope": p["scope"], "key": p["key"], "bucket": p["bucket"],
                                           "origin": "explicit", "confidence": 1.0, "from_proposal": p["id"]})
            else:
                state["new_facts"].append({"kind": "correction", "scope": p["scope"], "key": p["key"],
                                           "bucket": p["bucket"], "from_proposal": p["id"]})
            done.append(p["id"])
        elif a.get("answer") == "rule":
            for f in state["facts"]:
                if f.get("kind") == "rule" and f.get("scope") == a["scope"] and f.get("key") == a["key"]:
                    state["superseded"].append({"old_id": f["id"]})
            rule = {"kind": "rule", "scope": a["scope"], "key": a["key"].lower(), "bucket": a["bucket"],
                    "origin": "explicit", "confidence": 1.0}
            for opt in ("beats_vip", "series_ok"):
                if a.get(opt):
                    rule[opt] = True
            state["new_facts"].append(rule)
            done.append(f"{a['scope']}:{a['key']}")
        elif a.get("person"):
            key = a["person"].lower()
            prof = head["profile"]
            if a.get("vip") and key not in prof["vip"]:
                prof["vip"].append(key)
            if a.get("personal") and key not in prof["personal"]:
                prof["personal"].append(key)
            done.append(key)
        elif a.get("fact"):
            state["new_facts"].append(dict(a["fact"]))
            done.append(a["fact"].get("kind", "fact"))
    return done


def expire(state, now=None):
    now = now or now_utc()
    head = state["head"]
    expired, retired = [], []
    for p in head["proposals"]:
        if p.get("state") == "open" and (parse_ts(p.get("expires_at")) or now) < now:
            p["state"], p["closed_at"] = "expired", iso(now)
            expired.append(p["id"])
            for f in state["facts"]:
                if f.get("proposal_id") == p["id"]:
                    state["superseded"].append({"old_id": f["id"]})
    open_ids = {p["id"] for p in head["proposals"] if p.get("state") == "open"}
    support = head.get("rule_support", {})
    for f in state["facts"]:
        if f.get("kind") == "rule" and f.get("origin") == "inferred" and f.get("proposal_id") not in open_ids:
            last = parse_ts(support.get(f["id"]) or f.get("created_at")) or now
            if now - last > timedelta(days=RETIRE_DAYS):
                state["superseded"].append({"old_id": f["id"]})
                retired.append(f["id"])
    return {"expired": expired, "retired": retired}


def update_autonomy(state, now=None):
    now = now or now_utc()
    head = state["head"]
    stats = head.pop("_run_stats", {}) or {}
    changes = []
    paused = set(head.get("paused_rules", []))
    for s in head.get("signals", []):
        if s.get("wrong") and s.get("rule_id"):
            paused.add(s["rule_id"])
    head["paused_rules"] = sorted(paused)
    for b, st in stats.items():
        a = head["autonomy"][b]
        rate = (st["overrides"] / st["decisions"]) if st["decisions"] else 0.0
        a["runs"].append({"at": iso(now), **st, "override_rate": round(rate, 4), "counted": st["decisions"] >= 3})
        if st["wrong"] and a["level"] > 1:
            a["history"].append({"at": iso(now), "from": a["level"], "to": a["level"] - 1, "reason": "wrong_action"})
            a["level"] -= 1
            changes.append((b, "down"))
            a["runs"].append({"at": iso(now), "decisions": 0, "overrides": 0, "wrong": 0, "override_rate": 0, "counted": False, "reset": True})
            continue
        streak = []
        for r in reversed(a["runs"]):
            if r.get("reset") or (r.get("counted") and r["override_rate"] >= 0.05):
                break
            if r.get("counted"):
                streak.append(r)
        cap = min(MAX_LEVEL[b], PRESETS.get(head["profile"].get("preset", DEFAULT_PRESET), PRESETS[DEFAULT_PRESET])["cap"][b])
        if len(streak) >= 5 and sum(r["decisions"] for r in streak) >= 30 and a["level"] < cap and a["level"] >= 1:
            a["history"].append({"at": iso(now), "from": a["level"], "to": a["level"] + 1, "reason": "accurate_streak"})
            a["level"] += 1
            changes.append((b, "up"))
            a["runs"].append({"at": iso(now), "decisions": 0, "overrides": 0, "wrong": 0, "override_rate": 0, "counted": False, "reset": True})
    return changes


def go_live(state, now=None, preset=None):
    """Go live with an automation preset (default: medium). Returns the levels set."""
    now = now or now_utc()
    head = state["head"]
    preset = preset or head["profile"].get("preset") or DEFAULT_PRESET
    if preset not in PRESETS:
        raise ValueError(f"unknown preset {preset}: use one of {', '.join(PRESETS)}")
    head["profile"]["preset"] = preset
    head["setup"]["stage"] = "live"
    for b, a in head["autonomy"].items():
        target = PRESETS[preset]["start"][b]
        if a["level"] != target:
            a["history"].append({"at": iso(now), "from": a["level"], "to": target, "reason": f"preset_{preset}"})
            a["level"] = target
    return {b: a["level"] for b, a in head["autonomy"].items()}


def automation_plan(profile, preset=None):
    """The recommended daily automation for this user: when to run and what the prompts are."""
    preset = preset or profile.get("preset") or DEFAULT_PRESET
    start = (profile.get("working_hours") or [8, 17])[0]
    hh, mm = (start, 30) if start <= 9 else (start, 0)
    tz = profile.get("tz") or "UTC"
    return {
        "preset": preset,
        "invite_accept": bool(profile.get("invite_accept", False)),
        "timezone": tz,
        "jobs": [
            {"name": "dear-inbox-zero daily", "when": f"weekdays {hh:02d}:{mm:02d}", "cron": f"{mm} {hh} * * 1-5",
             "prompt": "dear-inbox-zero"},
            {"name": "dear-inbox-zero weekly learn", "when": f"Mondays {hh + 1:02d}:{mm:02d}", "cron": f"{mm} {hh + 1} * * 1",
             "prompt": "dear-inbox-zero learn"},
        ],
        "notes": "Check existing schedules first so runs never double up. Unattended runs keep every safety rule; "
                 "anything that needs the user waits in the report. Invite accepts are "
                 + ("on: confirmed rules accept invites, which sends the organiser a response."
                    if profile.get("invite_accept") else "off: the report asks about every invite; nothing is sent."),
    }


def study(state, observations, now=None):
    """Turn setup observations into inferred facts. observations: [{kind, scope, key, count}].
    kinds: replied_to, read_no_reply, ignored, accepted, declined, teams_replied, vip_hint."""
    agg = {}
    for o in observations or []:
        k = (o["kind"], o.get("scope", "sender"), (o.get("key") or "").lower())
        agg[k] = agg.get(k, 0) + int(o.get("count", 1))
    made = []
    def rule(scope, key, bucket, conf, why):
        state["new_facts"].append({"kind": "rule", "scope": scope, "key": key, "bucket": bucket,
                                   "origin": "inferred", "confidence": conf, "why": why})
        made.append((scope, key, bucket))
    for (kind, scope, key), n in sorted(agg.items()):
        if not key:
            continue
        if kind in ("replied_to", "teams_replied") and n >= 3:
            rule(scope, key, "reply", 0.8 if n >= 6 else 0.7, f"{kind} x{n}")
        elif kind == "ignored" and n >= 5:
            rule(scope, key, "noise", 0.8 if n >= 10 else 0.7, f"ignored x{n}")
        elif kind == "read_no_reply" and n >= 5:
            rule(scope, key, "fyi", 0.8 if n >= 10 else 0.7, f"read without reply x{n}")
        elif kind == "accepted" and n >= 3 and agg.get(("declined", scope, key), 0) == 0:
            p = {"scope": scope, "key": key, "bucket": "accept", "evidence": [], "created_at": iso(now or now_utc()),
                 "expires_at": iso((now or now_utc()) + timedelta(days=PROPOSAL_DAYS)), "state": "open", "why": f"accepted x{n}"}
            p["id"] = "p-" + sha256([scope, key, "accept", p["created_at"]])[:12]
            state["head"]["proposals"].append(p)
            made.append((scope, key, "accept?"))
        elif kind == "vip_hint" and n >= 1:
            state["new_facts"].append({"kind": "person", "key": key, "vip": True, "origin": "inferred", "confidence": 0.7})
            made.append(("person", key, "vip?"))
    return made


def calibration_questions(state, volumes=None, limit=15):
    """Uncertain senders/series with the most volume -> one question each."""
    vol = {(v.get("scope", "sender"), v["key"].lower()): int(v.get("count", 0)) for v in (volumes or [])}
    rules = {(f["scope"], f["key"]): f for f in state["facts"] if f.get("kind") == "rule"}
    cands = []
    for k, n in vol.items():
        r = rules.get(k)
        if r and r.get("origin") == "explicit":
            continue
        conf = float(r.get("confidence", 0)) if r else 0.0
        cands.append((-(n * (1 - conf)), k, r))
    for k, r in rules.items():
        if r.get("origin") == "inferred" and k not in vol:
            cands.append((-(1 - float(r.get("confidence", 0))), k, r))
    cands.sort()
    qs = []
    for _, (scope, key), r in cands[:limit]:
        qs.append({"scope": scope, "key": key, "current_guess": r.get("bucket") if r else None,
                   "question": f"How should I treat {'mail from' if scope != 'series' else 'the series'} {key}?",
                   "options": ["Noise", "FYI", "Reply", "Personal", "Skip"]})
    return qs
