"""Short Markdown report: counts plus what needs the user."""
from . import AUTONOMY_BUCKETS
from .ledger import aged
from .util import now_utc, parse_ts


LABEL = {"reply": "Reply", "invites": "Invites", "fyi": "FYI", "noise": "Noise", "personal": "Personal",
         "calendar": "Calendar", "unknown": "Unknown"}
_TZ = [None]


def _when(ts):
    dt = parse_ts(ts)
    if not dt:
        return ""
    if _TZ[0]:
        dt = dt.astimezone(_TZ[0])
    return dt.strftime("%a %d %b %H:%M")


def _set_tz(name):
    try:
        from zoneinfo import ZoneInfo
        _TZ[0] = ZoneInfo(name) if name else None
    except Exception:  # unknown zone or no tz database: show UTC
        _TZ[0] = None


def render(state, decisions, now=None, notes=None):
    now = now or now_utc()
    head = state["head"]
    _set_tz(head["profile"].get("tz"))
    decs = decisions.get("decisions", [])
    lines = [f"# dear-inbox-zero — {now.strftime('%a %d %b %Y')}" + (" (dry run: nothing changed)" if decisions.get("dry_run") else ""), ""]
    counts = {}
    for d in decs:
        k = d.get("bucket") if d.get("channel") != "invite" else "invites"
        counts[k] = counts.get(k, 0) + 1
    order = ["reply", "invites", "fyi", "noise", "personal", "calendar", "unknown"]
    lines += ["| " + " | ".join(LABEL[k] for k in order if k in counts) + " |",
              "|" + "---|" * len([k for k in order if k in counts]),
              "| " + " | ".join(str(counts[k]) for k in order if k in counts) + " |", ""] if counts else ["Nothing new since the last run.", ""]
    inv = [d for d in decs if d.get("channel") == "invite" and d.get("recommendation") in ("ask", "accept")]
    if inv:
        lines += ["## Decide today", ""]
        for d in inv:
            if d["recommendation"] == "accept":
                lines.append(f"- Accepted under your rule: **{d['subject']}** — {_when(d.get('start'))}")
            elif d.get("clashes"):
                c = "; ".join(f"{x['subject']} ({_when(x['start'])})" for x in d["clashes"])
                lines.append(f"- **{d['subject']}** — {_when(d.get('start'))} · clashes with {c} · flagged, not answered")
            else:
                lines.append(f"- **{d['subject']}** from {d.get('sender_name') or d['sender']} — {_when(d.get('start'))} · accept?")
        lines.append("")
    rep = [d for d in decs if d.get("bucket") == "reply"]
    if rep:
        lines += ["## Needs you", ""]
        for d in rep:
            how = "suggested reply below" if d["channel"] == "teams" else ("draft in Drafts" if any(a["op"] == "draft" for a in d.get("actions", [])) else "no draft (report-only level)")
            where = "Teams" if d["channel"] == "teams" else "Mail"
            lines.append(f"- {where} · **{d.get('sender_name') or d['sender']}** — {d['subject']} · {how}")
        lines.append("")
    old = aged(head, now)
    if old:
        lines += ["## Open loops", ""]
        for l in old[:15]:
            lines.append(f"- {l['who']} — {l['subject']} · {l['working_days']} working days")
        lines.append("")
    fyi = [d for d in decs if d.get("bucket") == "fyi"]
    if fyi:
        lines += ["## FYI", ""]
        for d in fyi[:30]:
            lines.append(f"- {d.get('sender_name') or d['sender']} — {d['subject']}")
        if len(fyi) > 30:
            lines.append(f"- …and {len(fyi) - 30} more")
        lines.append("")
    props = [p for p in head.get("proposals", []) if p.get("state") == "open"]
    if props:
        lines += ["## I noticed (confirm once)", ""]
        for p in props[:5]:
            what = {"noise": "Noise", "fyi": "FYI", "reply": "Reply", "accept": "always accept"}.get(p["bucket"], p["bucket"])
            lines.append(f"- {p['scope']} `{p['key']}` → **{what}**? (proposal {p['id']})")
        lines.append("")
    unk = [d for d in decs if d.get("bucket") == "unknown"]
    if unk:
        lines += ["## New senders (how should I treat them?)", ""]
        for d in unk[:10]:
            lines.append(f"- {d.get('sender_name') or d['sender']} — {d['subject']}")
        lines.append("")
    pers = counts.get("personal", 0)
    if pers:
        lines += [f"Personal: {pers} item(s), not opened.", ""]
    lvl = ", ".join(f"{b} L{head['autonomy'][b]['level']}" for b in AUTONOMY_BUCKETS)
    lines += [f"_Autonomy: {lvl}_"]
    for n in notes or []:
        lines.append(f"_Note: {n}_")
    return "\n".join(lines) + "\n"


def review(state, now=None):
    now = now or now_utc()
    head = state["head"]
    lines = [f"# dear-inbox-zero weekly review — {now.strftime('%d %b %Y')}", "", "| Bucket | Level | Runs (7) | Decisions | Override rate |", "|---|---|---|---|---|"]
    for b, a in head["autonomy"].items():
        runs = [r for r in a["runs"] if r.get("counted")][-7:]
        dec = sum(r["decisions"] for r in runs)
        ov = sum(r["overrides"] for r in runs)
        lines.append(f"| {b} | {a['level']} | {len(runs)} | {dec} | {(ov / dec * 100 if dec else 0):.1f}% |")
    rules = [f for f in state["facts"] if f.get("kind") == "rule"]
    lines += ["", f"Rules: {sum(1 for r in rules if r.get('origin') == 'explicit')} confirmed, "
              f"{sum(1 for r in rules if r.get('origin') == 'inferred')} inferred. "
              f"Open proposals: {sum(1 for p in head['proposals'] if p.get('state') == 'open')}."]
    return "\n".join(lines) + "\n"
