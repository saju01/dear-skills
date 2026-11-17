"""Health check: files, token budget, adapter coverage and forbidden operations, store integrity."""
import json, os, re, sys

REQUIRED_OPS = ["me", "mail.list", "mail.meta", "mail.body", "mail.sent", "mail.tag", "mail.read", "mail.flag",
                "mail.reply_draft", "mail.categories", "cal.view", "cal.accept", "teams.needs_response",
                "teams.thread", "teams.my_replies", "store.list", "store.read", "store.write", "ask", "run_python", "schedule"]
# Lite mode (mail only, no Python) needs only these. An adapter marked <!-- adapter-mode: lite --> may leave the rest empty.
LITE_OPS = ["me", "mail.list", "mail.meta", "mail.body", "mail.sent", "mail.tag", "mail.read", "mail.flag",
            "mail.reply_draft", "store.read", "store.write", "ask"]
FORBIDDEN_OPS = ["mail.send", "mail.forward", "mail.delete", "mail.move", "cal.decline", "teams.post"]
FORBIDDEN_TOOL_WORDS = re.compile(
    r"(\bSend(Email\w*|Draft\w*|Mail\w*)\b|\bForward\w*|\bDelete(Message|Event)\w*|\bDecline\w*|\bTentatively\w*"
    r"|\bPost(Channel)?Message\b|\bReplyTo(Channel)?Message\b|\bReplyAllToMessage\b|\bMoveMessage\b"
    r"|/send\b|/forward\b|/createForward\b|/decline\b|/tentativelyAccept\b|/move\b|\bDELETE\s)")
REQUIRED_FILES = ["SKILL.md", "channels/mail.md", "channels/calendar.md", "channels/teams.md", "policy/buckets.md",
                  "policy/voice.md", "policy/safety.md", "setup/first-install.md", "setup/install.md", "learn/learning-loop.md", "learn/sent-box.md",
                  "hosts/_template.md", "config/host.json", "engine/dear_engine.py",
                  "lite/run.md", "lite/setup.md"]
BUDGET = {"SKILL.md": 6 * 1024, "per_run_guides": 15 * 1024, "lite_run_guides": 15 * 1024}
LITE_RUN_FILES = ["lite/run.md", "policy/buckets.md", "policy/safety.md", "policy/voice.md"]
MODES = ("auto", "lite", "pro")


def adapter_table(text):
    m = re.search(r"<!-- adapter-ops:begin -->(.*?)<!-- adapter-ops:end -->", text, re.S)
    if not m:
        return None
    rows = {}
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].startswith("`"):
            rows[cells[0].strip("`")] = cells[1]
    return rows


def is_lite_adapter(text):
    return "<!-- adapter-mode: lite -->" in text


def check_adapter(path, template=False):
    errs = []
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    rows = adapter_table(text)
    if rows is None:
        return [f"{os.path.basename(path)}: no adapter-ops table"]
    lite = is_lite_adapter(text)
    for op in REQUIRED_OPS:
        if lite and op not in LITE_OPS and not rows.get(op):
            continue
        if op not in rows:
            errs.append(f"{os.path.basename(path)}: missing operation {op}")
        elif not template and not rows[op]:
            errs.append(f"{os.path.basename(path)}: operation {op} not mapped")
    for op in FORBIDDEN_OPS:
        if op in rows:
            errs.append(f"{os.path.basename(path)}: forbidden operation {op} is mapped")
    for op, tool in rows.items():
        allowed = re.sub(r"never\s+`?[^`]*`?", "", tool, flags=re.I)
        if FORBIDDEN_TOOL_WORDS.search(allowed):
            errs.append(f"{os.path.basename(path)}: {op} maps to a forbidden tool ({tool})")
    return errs


def run(skill_dir, store_dir=None):
    errs, warns, info = [], [], {}
    for f in REQUIRED_FILES:
        if not os.path.exists(os.path.join(skill_dir, f)):
            errs.append(f"missing {f}")
    sk = os.path.join(skill_dir, "SKILL.md")
    if os.path.exists(sk):
        size = os.path.getsize(sk)
        info["SKILL.md_bytes"] = size
        if size > BUDGET["SKILL.md"]:
            errs.append(f"SKILL.md is {size} bytes (budget {BUDGET['SKILL.md']})")
        with open(sk, encoding="utf-8") as fh:
            head = fh.read().split("---")
        if len(head) < 3 or "name: dear-inbox-zero" not in head[1] or "description:" not in head[1]:
            errs.append("SKILL.md frontmatter needs name and description")
    run_files = ["channels/mail.md", "channels/calendar.md", "channels/teams.md", "policy/buckets.md", "policy/voice.md", "policy/safety.md"]
    total = sum(os.path.getsize(os.path.join(skill_dir, f)) for f in run_files if os.path.exists(os.path.join(skill_dir, f)))
    info["per_run_guides_bytes"] = total
    if total > BUDGET["per_run_guides"]:
        errs.append(f"guides loaded per run are {total} bytes (budget {BUDGET['per_run_guides']})")
    lite_total = sum(os.path.getsize(os.path.join(skill_dir, f)) for f in LITE_RUN_FILES if os.path.exists(os.path.join(skill_dir, f)))
    info["lite_run_guides_bytes"] = lite_total
    if lite_total > BUDGET["lite_run_guides"]:
        errs.append(f"guides loaded per lite run are {lite_total} bytes (budget {BUDGET['lite_run_guides']})")
    hdir = os.path.join(skill_dir, "hosts")
    for name in sorted(os.listdir(hdir)) if os.path.isdir(hdir) else []:
        if name.endswith(".md"):
            path = os.path.join(hdir, name)
            errs += check_adapter(path, template=name.startswith("_"))
            with open(path, encoding="utf-8") as fh:
                if is_lite_adapter(fh.read()):
                    warns.append(f"{name}: lite-only adapter (mail only; pro needs calendar, Teams and run_python mapped)")
    cfg = os.path.join(skill_dir, "config", "host.json")
    if os.path.exists(cfg):
        with open(cfg, encoding="utf-8") as fh:
            c = json.load(fh)
        info["host"] = c.get("host")
        info["mode"] = c.get("mode", "auto")
        if info["mode"] not in MODES:
            errs.append(f"config/host.json mode must be one of {', '.join(MODES)}")
        ad = os.path.join(skill_dir, c.get("adapter", ""))
        if not os.path.exists(ad):
            errs.append(f"config/host.json points to a missing adapter {c.get('adapter')}")
    info["python"] = sys.version.split()[0]
    if sys.version_info < (3, 10):
        errs.append("Python 3.10+ required for the engine (lite mode still works)")
    if store_dir:
        from . import store
        try:
            st = store.load_state(store_dir)
            info["store_head"] = st["head_sha"][:12]
            info["live_facts"] = len(st["facts"])
            if st.get("index_rebuilt"):
                warns.append("index.json was stale or missing: rebuilt from facts (publish to fix)")
            size = len(json.dumps(st["head"]).encode())
            if size > store.HEAD_BUDGET:
                warns.append(f"head is {size} bytes (budget {store.HEAD_BUDGET})")
        except Exception as e:  # report, never repair silently
            errs.append(f"store: {e}")
    return {"ok": not errs, "errors": errs, "warnings": warns, "info": info}
