#!/usr/bin/env python3
"""Fail if the repo contains personal data: real-looking addresses, phone numbers, secrets or denylisted names.

Allowed: example.com/.org/.net addresses, noreply-style placeholders in docs.
Optional denylist: DIZ_DENYLIST env var (comma-separated) or .privacy-denylist (git-ignored) for maintainers.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}
SKIP_FILES = {"LICENSE"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}")
ALLOWED_DOMAINS = re.compile(r"@([a-z0-9-]+\.)*example\.(com|org|net)$|@users\.noreply\.github\.com$", re.I)
PHONE = re.compile(r"(?<![\w/#.-])\+?\d[\d ()-]{8,}\d(?![\w/-])")
SECRET = re.compile(r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[bp]-[A-Za-z0-9-]{10,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
HEX_OK = re.compile(r"^[0-9a-f]{12,64}$")


def denylist():
    words = [w.strip() for w in os.environ.get("DIZ_DENYLIST", "").split(",") if w.strip()]
    p = os.path.join(ROOT, ".privacy-denylist")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            words += [l.strip() for l in fh if l.strip() and not l.startswith("#")]
    return [w.lower() for w in words]


def scan():
    hits, deny = [], denylist()
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name in SKIP_FILES or name.endswith((".png", ".jpg", ".pyc")) or name == ".privacy-denylist":
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT)
            try:
                text = open(path, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for m in EMAIL.finditer(line):
                    if not ALLOWED_DOMAINS.search(m.group(0)) and "{" not in m.group(0):
                        hits.append(f"{rel}:{i}: email address {m.group(0)}")
                for m in PHONE.finditer(line):
                    digits = re.sub(r"\D", "", m.group(0))
                    if len(digits) >= 9 and not HEX_OK.match(digits) and not re.search(r"\d{4}-\d{2}-\d{2}", m.group(0)):
                        hits.append(f"{rel}:{i}: phone-like number {m.group(0).strip()}")
                if SECRET.search(line):
                    hits.append(f"{rel}:{i}: secret-like token")
                low = line.lower()
                for w in deny:
                    if w in low:
                        hits.append(f"{rel}:{i}: denylisted term")
    return hits


if __name__ == "__main__":
    hits = scan()
    for h in hits:
        print(h)
    print(f"privacy scan: {len(hits)} finding(s)")
    sys.exit(1 if hits else 0)
