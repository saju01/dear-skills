#!/usr/bin/env python3
"""Regenerate install.json file lists and sha256 hashes. `--check` fails if install.json is out of date."""
import hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = ["README.md", "DESIGN.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "AGENTS.md", "INSTALL.md", "llms.txt"]
SKIP = {"__pycache__"}


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def skill_files(skill_path):
    base = os.path.join(ROOT, skill_path)
    out = []
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        for name in sorted(files):
            if name.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, name)
            out.append({"path": os.path.relpath(full, ROOT).replace(os.sep, "/"),
                        "target": os.path.relpath(full, base).replace(os.sep, "/"), "sha256": sha(full)})
    return out


def build():
    path = os.path.join(ROOT, "install.json")
    with open(path, encoding="utf-8") as fh:
        m = json.load(fh)
    for s in m["skills"]:
        s["files"] = skill_files(s["path"])
    m["docs"] = [{"path": d, "sha256": sha(os.path.join(ROOT, d))} for d in DOCS if os.path.exists(os.path.join(ROOT, d))]
    return path, json.dumps(m, indent=2) + "\n"


if __name__ == "__main__":
    path, text = build()
    with open(path, encoding="utf-8") as fh:
        current = fh.read()
    if "--check" in sys.argv:
        if current != text:
            print("install.json is out of date: run python scripts/build_manifest.py")
            sys.exit(1)
        print("install.json is up to date")
    else:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("install.json updated")
