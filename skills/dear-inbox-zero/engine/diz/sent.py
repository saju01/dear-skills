"""The Sent box: the strongest evidence of what matters to the user.

Used twice:
- setup (`sent-study`): 12 months of sent metadata (+ up to 40 bodies, in memory only) ->
  who the user answers and how fast, working hours, language per contact, voice.
- daily (`sent-signals`): sent items since the checkpoint -> `replied` / `replied_not_proposed`
  signals, closed open loops, and how much the user changed a run draft before sending it.

Bodies are read from working files and never stored: only counts, medians and short
greeting/sign-off patterns (with names replaced by {first_name}) reach memory.
"""
import re
from collections import Counter, defaultdict
from statistics import median
from .util import parse_ts, domain_of, iso, now_utc

QUOTE_START = re.compile(
    r"^\s*(>|-{2,}\s*original message|_{5,}|from:\s|van:\s|von:\s|de:\s|sent:\s|verzonden:\s|gesendet:\s"
    r"|on .{3,80} wrote:|op .{3,80} schreef|am .{3,80} schrieb|le .{3,80} a écrit)", re.I)
GREETING = re.compile(r"^(hi|hello|hey|dear|good (morning|afternoon)|hoi|hallo|beste|goedemorgen|goedemiddag|"
                      r"liebe|lieber|sehr geehrte|bonjour|hola)\b[^\n]{0,40}$", re.I)
SIGNOFF = re.compile(r"^(thanks|thank you|cheers|best|kind regards|regards|warm regards|many thanks|br|"
                     r"groet(en)?|met vriendelijke groet|hartelijke groet|dank( je)?( wel)?|"
                     r"viele grüße|mit freundlichen grüßen|cordialement|saludos)\b[^\n]{0,40}$", re.I)
STOP = {
    "en": {"the", "and", "you", "to", "is", "for", "with", "that", "this", "will", "have", "thanks"},
    "nl": {"de", "het", "een", "en", "je", "van", "voor", "met", "dat", "is", "niet", "ik", "graag", "bedankt"},
    "de": {"der", "die", "das", "und", "ich", "sie", "nicht", "mit", "für", "ist", "danke", "bitte"},
    "fr": {"le", "la", "les", "et", "vous", "pour", "avec", "est", "pas", "je", "merci"},
    "es": {"el", "la", "los", "y", "usted", "para", "con", "es", "no", "yo", "gracias"},
}


def strip_reply(body):
    """Keep only what the user wrote: drop quoted history and anything after a signature marker."""
    out = []
    for line in (body or "").replace("\r", "").split("\n"):
        if QUOTE_START.match(line):
            break
        if line.strip() in ("--", "-- "):
            break
        out.append(line.rstrip())
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out).strip()


def language(text):
    words = re.findall(r"[a-zà-ÿ]+", (text or "").lower())
    if len(words) < 3:
        return None
    scores = {lang: sum(1 for w in words if w in sw) for lang, sw in STOP.items()}
    lang, best = max(scores.items(), key=lambda kv: kv[1])
    return lang if best >= 2 else None


def _templ(line, names, greeting=True):
    t = line.strip()
    for n in names:
        if n and len(n) > 1:
            t = re.sub(rf"\b{re.escape(n)}\b", "{first_name}", t, flags=re.I)
    if greeting:  # the recipient's name after the greeting word; a sign-off keeps the user's own name
        t = re.sub(r"^(\S+(?:\s+(?:morning|afternoon|geehrte))?)\s+[A-Z][\w'-]{1,20}(?=[,!.]?$)", r"\1 {first_name}", t)
    return t[:40]


def features(body, recipient_first_names=()):
    """Voice features of one sent reply. Returns no text beyond short templated greeting/sign-off."""
    own = strip_reply(body)
    lines = [l.strip() for l in own.split("\n") if l.strip()]
    greet = next((l for l in lines[:2] if GREETING.match(l)), None)
    sign = next((l for l in reversed(lines[-4:]) if SIGNOFF.match(l)), None)
    words = len(re.findall(r"\w+", own))
    return {"greeting": _templ(greet, recipient_first_names) if greet else None,
            "sign_off": _templ(sign, recipient_first_names, greeting=False) if sign else None,
            "words": words, "language": language(own), "bullets": sum(1 for l in lines if l[:1] in "-*•")}


def edit_ratio(draft, sent):
    """Share of words changed between a run draft and what the user actually sent (0..1)."""
    a, b = re.findall(r"\w+", strip_reply(draft).lower()), re.findall(r"\w+", strip_reply(sent).lower())
    if not a and not b:
        return 0.0
    ca, cb = Counter(a), Counter(b)
    common = sum((ca & cb).values())
    return round(1 - (2 * common) / (len(a) + len(b)), 3)


def study(sent_items, received_index=None, bodies=None, now=None):
    """sent_items: [{id, conversation_id, sent_at, to: [addr], cc: [addr], in_reply_to_received_at?,
    in_reply_to_sender?, recipient_names?: [first names]}] (metadata, 12 months).
    bodies: {id: body} for up to 40 recent replies (working memory only).
    Returns observations (for learn.study), person facts, voice facts and profile hints."""
    now = now or now_utc()
    per, hours, langs = defaultdict(lambda: {"replies": 0, "latency_h": [], "lang": Counter()}), Counter(), Counter()
    for s in sent_items or []:
        t = parse_ts(s.get("sent_at"))
        if t:
            hours[(t.weekday(), t.hour)] += 1
        target = (s.get("in_reply_to_sender") or (s.get("to") or [None])[0] or "").lower()
        if not target:
            continue
        p = per[target]
        p["replies"] += 1
        rt = parse_ts(s.get("in_reply_to_received_at"))
        if t and rt and t > rt:
            p["latency_h"].append((t - rt).total_seconds() / 3600)
    voice, vlang = [], Counter()
    by_id = {s["id"]: s for s in sent_items or []}
    for sid, body in (bodies or {}).items():
        meta = by_id.get(sid, {})
        f = features(body, meta.get("recipient_names") or [])
        voice.append(f)
        target = (meta.get("in_reply_to_sender") or (meta.get("to") or [""])[0] or "").lower()
        if f["language"]:
            vlang[f["language"]] += 1
            if target:
                per[target]["lang"][f["language"]] += 1
    obs, people = [], []
    dom = Counter()
    for addr, p in per.items():
        dom[domain_of(addr)] += p["replies"]
        if p["replies"] >= 3:
            obs.append({"kind": "replied_to", "scope": "sender", "key": addr, "count": p["replies"]})
        lat = median(p["latency_h"]) if p["latency_h"] else None
        fact = {"kind": "person", "key": addr, "replies_12m": p["replies"], "origin": "inferred", "confidence": 0.7}
        if lat is not None:
            fact["median_reply_hours"] = round(lat, 1)
        if p["lang"]:
            fact["language"] = p["lang"].most_common(1)[0][0]
        if p["replies"] >= 8 and lat is not None and lat <= 4:
            fact["vip"] = True  # answered often and fast: proposed as VIP, confirmed in calibration
            obs.append({"kind": "vip_hint", "scope": "sender", "key": addr, "count": 1})
        if p["replies"] >= 2:
            people.append(fact)
    voice_fact = None
    if voice:
        g = Counter(v["greeting"] for v in voice if v["greeting"])
        so = Counter(v["sign_off"] for v in voice if v["sign_off"])
        voice_fact = {"kind": "voice", "origin": "inferred", "samples": len(voice),
                      "greeting": g.most_common(1)[0][0] if g else None,
                      "sign_off": so.most_common(1)[0][0] if so else None,
                      "median_words": int(median(v["words"] for v in voice)),
                      "uses_bullets": sum(1 for v in voice if v["bullets"]) / len(voice) >= 0.3,
                      "language_default": vlang.most_common(1)[0][0] if vlang else None}
    # working hours: hours with >= 5% of sends, weekdays only
    total = sum(hours.values()) or 1
    by_hour = Counter()
    for (wd, h), n in hours.items():
        if wd < 5:
            by_hour[h] += n
    active = sorted(h for h, n in by_hour.items() if n / total >= 0.05)
    profile_hints = {"working_hours": [active[0], active[-1] + 1] if active else None,
                     "internal_domains_guess": [d for d, _ in dom.most_common(1)]}
    return {"observations": obs, "people": people, "voice": voice_fact, "profile_hints": profile_hints,
            "stats": {"sent": len(sent_items or []), "contacts": len(per), "voice_samples": len(voice)}}


def daily_signals(sent_items, last_decisions, drafts=None, sent_bodies=None, draft_bodies=None):
    """sent_items since the checkpoint: [{id, conversation_id, sent_at, is_meeting_response?, draft_id?}].
    last_decisions: the previous run's decisions (with thread_id, received_at).
    drafts: head drafts registry [{draft_id, item_id, thread_id}].
    Returns signals plus draft outcomes (sent / edited heavily)."""
    by_thread = defaultdict(list)
    for d in last_decisions or []:
        if d.get("thread_id"):
            by_thread[d["thread_id"]].append(d)
    signals, seen, draft_out = [], set(), []
    reg = {d.get("thread_id"): d for d in (drafts or []) if d.get("state", "open") == "open"}
    for s in sent_items or []:
        if s.get("is_meeting_response"):
            continue
        sent_at = parse_ts(s.get("sent_at"))
        for d in by_thread.get(s.get("conversation_id"), []):
            rec = parse_ts(d.get("received_at"))
            if rec and sent_at and sent_at <= rec:
                continue  # replied before this item arrived
            sig = "replied" if d.get("bucket") == "reply" else "replied_not_proposed"
            if (d["id"], sig) not in seen:
                seen.add((d["id"], sig))
                signals.append({"id": d["id"], "signal": sig, "at": s.get("sent_at")})
        dr = reg.get(s.get("conversation_id"))
        if dr:
            ratio = None
            if draft_bodies and sent_bodies and dr["draft_id"] in draft_bodies and s["id"] in sent_bodies:
                ratio = edit_ratio(draft_bodies[dr["draft_id"]], sent_bodies[s["id"]])
            draft_out.append({"draft_id": dr["draft_id"], "state": "sent", "edit_ratio": ratio})
            if ratio is not None and ratio > 0.5 and dr.get("item_id"):
                signals.append({"id": dr["item_id"], "signal": "draft_edited_heavily", "at": s.get("sent_at")})
    return {"signals": signals, "drafts": draft_out}


def update_voice(facts, sent_features, min_samples=5):
    """Rolling voice update from replies the user actually sent (daily). Returns a new voice fact
    when the user's greeting/sign-off/length clearly moved away from the stored one, else None."""
    cur = next((f for f in facts if f.get("kind") == "voice"), None)
    if len(sent_features) < min_samples:
        return None
    g = Counter(v["greeting"] for v in sent_features if v.get("greeting"))
    so = Counter(v["sign_off"] for v in sent_features if v.get("sign_off"))
    new = {"kind": "voice", "origin": "inferred", "samples": len(sent_features),
           "greeting": g.most_common(1)[0][0] if g else (cur or {}).get("greeting"),
           "sign_off": so.most_common(1)[0][0] if so else (cur or {}).get("sign_off"),
           "median_words": int(median(v["words"] for v in sent_features)),
           "language_default": (cur or {}).get("language_default")}
    if cur and cur.get("greeting") == new["greeting"] and cur.get("sign_off") == new["sign_off"] \
            and abs(int(cur.get("median_words") or 0) - new["median_words"]) <= 15:
        return None
    return new
