#!/usr/bin/env python3
"""dear-inbox-zero engine CLI. Run `python dear_engine.py <command> --help`."""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diz import __version__, store, classify as C, learn as L, ledger, report as R, doctor as D, sent as S  # noqa: E402
from diz.util import load, dump, parse_ts, iso, now_utc  # noqa: E402


def _now(a):
    return parse_ts(a.now) if getattr(a, "now", None) else now_utc()


def cmd_store_init(a):
    res = store.init(a.store, a.account, a.tz, a.channels.split(","), _now(a))
    print(json.dumps(res, indent=2))


def cmd_store_load(a):
    st = store.load_state(a.store)
    dump(a.out, st)
    print(json.dumps({"head": st["head_sha"][:12], "facts": len(st["facts"]), "stage": st["head"]["setup"]["stage"],
                      "index_rebuilt": st["index_rebuilt"]}))


def cmd_store_publish(a):
    st = load(a.state)
    res = store.publish(a.store, st, _now(a))
    print(json.dumps(res, indent=2))


def cmd_observe(a):
    st = load(a.state)
    res = L.observe(st, load(a.signals, []), _now(a))
    dump(a.state, st)
    print(json.dumps(res))


def cmd_classify(a):
    st = load(a.state)
    res = C.classify(st, load(a.items, []), load(a.calendar, []) if a.calendar else [], a.dry_run)
    dump(a.out, res)
    print(json.dumps({"decisions": len(res["decisions"]), "unknown": len(res["unknown"]), "dry_run": a.dry_run}))


def cmd_learn(a):
    now = _now(a)
    st = load(a.state)
    dec = load(a.decisions, {"decisions": []}) if a.decisions else {"decisions": []}
    sig = st["head"].get("signals", [])
    answered = L.apply_answers(st, load(a.answers, []) if a.answers else [], now)
    created = L.propose(st, now)
    exp = L.expire(st, now)
    changes = L.update_autonomy(st, now)
    ledger.update(st["head"], dec["decisions"], sig, now)
    if dec["decisions"] and not dec.get("dry_run"):
        st["head"]["last_run"] = {"at": iso(now), "decisions": [
            {k: d.get(k) for k in ("id", "channel", "bucket", "recommendation", "reason", "sender", "sender_name", "series", "rule_id", "thread_id", "received_at")}
            for d in dec["decisions"]]}
        for dr in (load(a.drafts, []) if a.drafts else []):
            st["head"]["drafts"].append({**dr, "created_at": iso(now), "state": "open"})
        for ch, ts in (load(a.checkpoints, {}) if a.checkpoints else {}).items():
            st["head"]["checkpoints"][ch] = ts
    dump(a.state, st)
    print(json.dumps({"answers": answered, "proposals": [p["id"] for p in created["created"]],
                      "inconsistent": created["inconsistent"], **exp, "autonomy_changes": changes}, indent=2))


def cmd_sent_study(a):
    now = _now(a)
    st = load(a.state)
    res = S.study(load(a.sent), bodies=load(a.bodies, {}) if a.bodies else None, now=now)
    made = L.study(st, res["observations"], now)
    st["new_facts"] += res["people"]
    if res["voice"]:
        st["new_facts"].append(res["voice"])
    prof = st["head"]["profile"]
    hints = res["profile_hints"]
    if hints.get("working_hours") and not prof.get("working_hours"):
        prof["working_hours"] = hints["working_hours"]
    for d in hints.get("internal_domains_guess") or []:
        if d and d not in prof["internal_domains"]:
            prof["internal_domains"].append(d)
    st["head"]["setup"]["stage"] = "s2_done" if res["voice"] else "s1_done"
    dump(a.state, st)
    print(json.dumps({**res["stats"], "rules_or_proposals": len(made), "people": len(res["people"]),
                      "voice": bool(res["voice"]), "profile_hints": hints}, indent=2))


def cmd_sent_signals(a):
    st = load(a.state)
    head = st["head"]
    sent_items = load(a.sent, [])
    bodies = load(a.bodies, {}) if a.bodies else {}
    res = S.daily_signals(sent_items, (head.get("last_run") or {}).get("decisions"), head.get("drafts"),
                          bodies, load(a.draft_bodies, {}) if a.draft_bodies else None)
    for out in res["drafts"]:
        for dr in head.get("drafts", []):
            if dr.get("draft_id") == out["draft_id"]:
                dr.update({"state": "sent", "edit_ratio": out["edit_ratio"]})
    feats = [S.features(b) for b in bodies.values()]
    voice = S.update_voice(st["facts"], feats)
    if voice:
        old = [f for f in st["facts"] if f.get("kind") == "voice"]
        st["superseded"] += [{"old_id": f["id"]} for f in old]
        st["new_facts"].append(voice)
    existing = load(a.out, []) if os.path.exists(a.out) else []
    dump(a.out, existing + res["signals"])
    dump(a.state, st)
    print(json.dumps({"signals": len(res["signals"]), "drafts_sent": len(res["drafts"]), "voice_updated": bool(voice)}))


def cmd_report(a):
    st = load(a.state)
    md = R.render(st, load(a.decisions, {"decisions": []}), _now(a), a.note)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(md)
    print(md)


def cmd_review(a):
    print(R.review(load(a.state), _now(a)))


def cmd_show(a):
    dec = load(a.decisions)
    rows = [d for d in dec["decisions"] if (d.get("bucket") == a.bucket or (a.bucket == "invites" and d.get("channel") == "invite"))]
    for d in rows:
        print(f"- {d.get('sender_name') or d['sender']} — {d['subject']} · {d.get('reason')}")
    if not rows:
        print(f"Nothing in {a.bucket}.")


def cmd_study(a):
    st = load(a.state)
    made = L.study(st, load(a.observations), _now(a))
    st["head"]["setup"]["stage"] = "s1_done"
    dump(a.state, st)
    print(json.dumps({"made": len(made)}))


def cmd_add_facts(a):
    st = load(a.state)
    done = L.apply_answers(st, load(a.answers), _now(a))
    if a.stage:
        st["head"]["setup"]["stage"] = a.stage
    dump(a.state, st)
    print(json.dumps({"applied": done}))


def cmd_calibrate(a):
    st = load(a.state)
    qs = L.calibration_questions(st, load(a.volumes, []) if a.volumes else [], a.limit)
    dump(a.out, qs)
    print(json.dumps({"questions": len(qs)}))


def cmd_go_live(a):
    st = load(a.state)
    L.go_live(st, _now(a))
    dump(a.state, st)
    print(json.dumps({"stage": "live", "levels": {b: v["level"] for b, v in st["head"]["autonomy"].items()}}))


def cmd_doctor(a):
    res = D.run(a.skill_dir, a.store)
    res["engine"] = __version__
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["ok"] else 1)


def main(argv=None):
    p = argparse.ArgumentParser(prog="dear_engine", description=f"dear-inbox-zero engine {__version__}")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    def add(name, fn, *args):
        s = sub.add_parser(name)
        for spec in args:
            flag, kw = spec
            s.add_argument(flag, **kw)
        s.add_argument("--now", help="ISO time (tests, replays)")
        s.set_defaults(fn=fn)
    req = {"required": True}
    add("store-init", cmd_store_init, ("--store", req), ("--account", req), ("--tz", {"default": "UTC"}), ("--channels", {"default": "mail,calendar"}))
    add("store-load", cmd_store_load, ("--store", req), ("--out", req))
    add("store-publish", cmd_store_publish, ("--store", req), ("--state", req))
    add("observe", cmd_observe, ("--state", req), ("--signals", req))
    add("classify", cmd_classify, ("--state", req), ("--items", req), ("--calendar", {}), ("--out", req), ("--dry-run", {"action": "store_true"}))
    add("learn", cmd_learn, ("--state", req), ("--decisions", {}), ("--answers", {}), ("--checkpoints", {}), ("--drafts", {}))
    add("sent-study", cmd_sent_study, ("--state", req), ("--sent", req), ("--bodies", {}))
    add("sent-signals", cmd_sent_signals, ("--state", req), ("--sent", req), ("--bodies", {}), ("--draft-bodies", {}), ("--out", req))
    add("report", cmd_report, ("--state", req), ("--decisions", req), ("--out", {}), ("--note", {"action": "append"}))
    add("review", cmd_review, ("--state", req))
    add("show", cmd_show, ("--decisions", req), ("--bucket", req))
    add("study", cmd_study, ("--state", req), ("--observations", req))
    add("add-facts", cmd_add_facts, ("--state", req), ("--answers", req), ("--stage", {}))
    add("calibrate", cmd_calibrate, ("--state", req), ("--volumes", {}), ("--out", req), ("--limit", {"type": int, "default": 15}))
    add("go-live", cmd_go_live, ("--state", req))
    add("doctor", cmd_doctor, ("--skill-dir", {"default": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}), ("--store", {}))
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
