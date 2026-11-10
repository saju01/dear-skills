"""The user's private store: content-addressed heads, append-only facts, rebuilt index.

Layout (mirror of OneDrive/dear-inbox-zero/<account_key>/):
  head/memory-<sha>.json   {"format", "sha256", "payload"}; payload.parent links history
  store/<fact_id>.json     one fact per file, never rewritten
  store/sup-<fact_id>.json supersession {old_id, new_id, at}
  index.json               {"sha256", "facts": [live facts]}
"""
import os
from . import __version__, AUTONOMY_BUCKETS
from .util import sha256, canon, iso, now_utc, load, dump

HEAD_FORMAT = "dear-inbox-zero/head@1"
HEAD_BUDGET = 16 * 1024


class StoreError(Exception):
    pass


def new_payload(account, tz="UTC", channels=("mail", "calendar"), now=None):
    now = now or now_utc()
    return {
        "account": account, "engine": __version__, "created_at": iso(now), "parent": None,
        "profile": {"tz": tz, "channels": list(channels), "broadcast_threshold": 50,
                    "teams_reply_hours": 4, "vip": [], "personal": [], "internal_domains": [],
                    "invite_accept": False},
        "setup": {"stage": "s0_done"},
        "autonomy": {b: {"level": 0, "runs": [], "history": []} for b in AUTONOMY_BUCKETS},
        "ledger": [], "checkpoints": {}, "drafts": [], "last_run": None,
        "signals": [], "proposals": [], "paused_rules": [], "rule_support": {},
        "index_ref": None,
    }


def fact_id(fact):
    body = {k: v for k, v in fact.items() if k != "id"}
    return sha256(body)[:24]


def _write_new(path, obj):
    if os.path.exists(path):
        raise StoreError(f"refusing to overwrite {path}")
    dump(path, obj)


def init(store_dir, account, tz, channels, now=None):
    if os.path.isdir(os.path.join(store_dir, "head")) and os.listdir(os.path.join(store_dir, "head")):
        raise StoreError("store already has a head: use store-load (recovery, never re-initialise)")
    for sub in ("head", "store"):
        os.makedirs(os.path.join(store_dir, sub), exist_ok=True)
    payload = new_payload(account, tz, channels, now)
    return publish(store_dir, {"head": payload, "head_sha": None, "facts": [], "new_facts": [], "superseded": []}, now=now)


def _read_heads(store_dir):
    hdir = os.path.join(store_dir, "head")
    heads = {}
    for name in sorted(os.listdir(hdir)) if os.path.isdir(hdir) else []:
        if not (name.startswith("memory-") and name.endswith(".json")):
            continue
        doc = load(os.path.join(hdir, name))
        if doc.get("format") != HEAD_FORMAT:
            raise StoreError(f"{name}: unknown head format")
        if sha256(doc["payload"]) != doc.get("sha256") or name != f"memory-{doc['sha256']}.json":
            raise StoreError(f"{name}: hash mismatch")
        heads[doc["sha256"]] = doc["payload"]
    return heads


def tip(heads):
    parents = {p.get("parent") for p in heads.values()}
    tips = [h for h in heads if h not in parents]
    if len(tips) != 1:
        raise StoreError(f"expected one head tip, found {len(tips)}: history forked")
    return tips[0]


def read_facts(store_dir):
    sdir = os.path.join(store_dir, "store")
    facts, sups = {}, {}
    for name in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []:
        if not name.endswith(".json"):
            continue
        doc = load(os.path.join(sdir, name))
        if name.startswith("sup-"):
            sups[doc["old_id"]] = doc
        else:
            if fact_id(doc) != doc.get("id"):
                raise StoreError(f"{name}: fact id mismatch")
            facts[doc["id"]] = doc
    live = [f for fid, f in facts.items() if fid not in sups and not f.get("retired")]
    return sorted(live, key=lambda f: (f.get("created_at", ""), f["id"]))


def load_state(store_dir):
    heads = _read_heads(store_dir)
    if not heads:
        raise StoreError("no head: run setup first")
    h = tip(heads)
    payload = heads[h]
    idx_path = os.path.join(store_dir, "index.json")
    facts = None
    if os.path.exists(idx_path):
        idx = load(idx_path)
        if idx.get("sha256") == payload.get("index_ref") and sha256(idx["facts"]) == idx.get("sha256"):
            facts = idx["facts"]
    rebuilt = facts is None
    if rebuilt:
        facts = read_facts(store_dir)
    return {"head": payload, "head_sha": h, "facts": facts, "new_facts": [], "superseded": [],
            "index_rebuilt": rebuilt}


def trim(payload, now=None):
    now = now or now_utc()
    from .util import parse_ts
    for b in payload["autonomy"].values():
        b["runs"] = b["runs"][-30:]
        b["history"] = b["history"][-20:]
    cutoff = now.timestamp() - 30 * 86400
    payload["ledger"] = [l for l in payload["ledger"] if l.get("state") == "open"
                         or (parse_ts(l.get("closed_at") or l.get("last_reported")) or now).timestamp() > cutoff]
    payload["proposals"] = [p for p in payload["proposals"] if p.get("state") == "open"
                            or (parse_ts(p.get("closed_at") or p.get("created_at")) or now).timestamp() > cutoff]
    payload["drafts"] = payload["drafts"][-100:]
    return len(canon(payload).encode("utf-8"))


def publish(store_dir, state, now=None):
    """Write new facts, supersessions, index and a new head. Returns the new files (relative paths)."""
    now = now or now_utc()
    written = []
    sdir = os.path.join(store_dir, "store")
    os.makedirs(sdir, exist_ok=True)
    os.makedirs(os.path.join(store_dir, "head"), exist_ok=True)
    live = {f["id"]: f for f in state.get("facts", [])}
    for fact in state.get("new_facts", []):
        fact.setdefault("created_at", iso(now))
        fact["id"] = fact_id(fact)
        path = os.path.join(sdir, f"{fact['id']}.json")
        if not os.path.exists(path):
            _write_new(path, fact)
            written.append(f"store/{fact['id']}.json")
        live[fact["id"]] = fact
    for sup in state.get("superseded", []):
        rec = {"old_id": sup["old_id"], "new_id": sup.get("new_id"), "at": iso(now)}
        path = os.path.join(sdir, f"sup-{sup['old_id']}.json")
        if not os.path.exists(path):
            _write_new(path, rec)
            written.append(f"store/sup-{sup['old_id']}.json")
        live.pop(sup["old_id"], None)
    facts = sorted(live.values(), key=lambda f: (f.get("created_at", ""), f["id"]))
    idx = {"sha256": sha256(facts), "facts": facts}
    dump(os.path.join(store_dir, "index.json"), idx)
    written.append("index.json")
    payload = dict(state["head"])
    payload["parent"] = state.get("head_sha")
    payload["engine"] = __version__
    payload["published_at"] = iso(now)
    payload["index_ref"] = idx["sha256"]
    size = trim(payload, now)
    h = sha256(payload)
    _write_new(os.path.join(store_dir, "head", f"memory-{h}.json"),
               {"format": HEAD_FORMAT, "sha256": h, "payload": payload})
    written.append(f"head/memory-{h}.json")
    return {"head_sha": h, "files": written, "head_bytes": size, "over_budget": size > HEAD_BUDGET}
