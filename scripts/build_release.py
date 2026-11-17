#!/usr/bin/env python3
"""Build the two release zips for manual upload (Cowork, claude.ai or any agent):

  dist/dear-inbox-zero-lite-v<version>.zip  mail only, no Python: the guides lite mode reads, no engine
  dist/dear-inbox-zero-pro-v<version>.zip   mail, invites and Teams, with the engine

Each zip holds one folder, dear-inbox-zero/, with SKILL.md at the top of it, config/host.json set to the
Cowork adapter and the zip's mode, and a SHA256SUMS file. Zips are reproducible (fixed timestamps, sorted).
Tests are not shipped. Prints JSON: {"version": ..., "zips": [{"edition", "zip", "files", "sha256"}, ...]}.
"""
import hashlib, io, json, os, re, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "dear-inbox-zero")
FOLDER = "dear-inbox-zero"
FIXED = (2026, 1, 1, 0, 0, 0)  # reproducible zips
HOST = {"host": "cowork", "adapter": "hosts/cowork.md"}

# Never shipped: tests and build leftovers.
SKIP_DIRS = {"__pycache__", "tests"}
# Lite reads only these (see SKILL.md "Mode", lite/run.md, lite/setup.md); everything else is pro.
LITE_KEEP = ("SKILL.md", "CHANGELOG.md", "config/", "hosts/", "lite/", "policy/", "setup/install.md", "setup/permissions.md")

EDITIONS = {
    "lite": {"mode": "lite", "keep": lambda rel: rel.startswith(LITE_KEEP)},
    # auto: pro wherever Python 3.10+ runs, lite otherwise (SKILL.md decides, the user isn't asked)
    "pro": {"mode": "auto", "keep": lambda rel: True},
}


def version():
    with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as fh:
        return re.search(r'version:\s*"([^"]+)"', fh.read()).group(1)


def files():
    for dirpath, dirs, names in os.walk(SKILL):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(names):
            if name.endswith(".pyc"):
                continue
            full = os.path.join(dirpath, name)
            yield os.path.relpath(full, SKILL).replace(os.sep, "/"), full


def build(edition, out_dir=None):
    spec = EDITIONS[edition]
    v = version()
    out_dir = out_dir or os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{FOLDER}-{edition}-v{v}.zip")
    sums = []
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, full in files():
            if not spec["keep"](rel):
                continue
            with open(full, "rb") as fh:
                data = fh.read()
            if rel == "config/host.json":
                data = (json.dumps(dict(HOST, mode=spec["mode"])) + "\n").encode()
            info = zipfile.ZipInfo(f"{FOLDER}/{rel}", FIXED)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
            sums.append(f"{hashlib.sha256(data).hexdigest()}  {FOLDER}/{rel}")
        info = zipfile.ZipInfo(f"{FOLDER}/SHA256SUMS", FIXED)
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, "\n".join(sums) + "\n")
    with open(out, "wb") as fh:
        fh.write(buf.getvalue())
    return {"edition": edition, "zip": out, "files": len(sums), "sha256": hashlib.sha256(buf.getvalue()).hexdigest()}


def build_all(out_dir=None):
    return {"version": version(), "zips": [build(e, out_dir) for e in EDITIONS]}


if __name__ == "__main__":
    res = build_all(sys.argv[1] if len(sys.argv) > 1 else None)
    for z in res["zips"]:
        z["zip"] = os.path.relpath(z["zip"], ROOT)
    print(json.dumps(res))
