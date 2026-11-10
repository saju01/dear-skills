#!/usr/bin/env python3
"""Build dist/dear-inbox-zero-v<version>.zip for manual upload (Cowork or any agent).

The zip holds one folder, dear-inbox-zero/, with config/host.json set to Cowork and a SHA256SUMS file.
"""
import hashlib, io, json, os, re, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "dear-inbox-zero")
FIXED = (2026, 1, 1, 0, 0, 0)  # reproducible zips


def version():
    with open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8") as fh:
        return re.search(r'version:\s*"([^"]+)"', fh.read()).group(1)


def build(host="cowork", adapter="hosts/cowork.md"):
    v = version()
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", f"dear-inbox-zero-v{v}.zip")
    sums = []
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirs, files in os.walk(SKILL):
            dirs[:] = sorted(d for d in dirs if d != "__pycache__")
            for name in sorted(files):
                if name.endswith(".pyc"):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, SKILL).replace(os.sep, "/")
                with open(full, "rb") as fh:
                    data = fh.read()
                if rel == "config/host.json":
                    data = (json.dumps({"host": host, "adapter": adapter, "mode": "auto"}) + "\n").encode()
                info = zipfile.ZipInfo(f"dear-inbox-zero/{rel}", FIXED)
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
                sums.append(f"{hashlib.sha256(data).hexdigest()}  dear-inbox-zero/{rel}")
        info = zipfile.ZipInfo("dear-inbox-zero/SHA256SUMS", FIXED)
        z.writestr(info, "\n".join(sums) + "\n")
    with open(out, "wb") as fh:
        fh.write(buf.getvalue())
    digest = hashlib.sha256(buf.getvalue()).hexdigest()
    return out, digest, len(sums)


if __name__ == "__main__":
    path, digest, n = build()
    print(json.dumps({"zip": os.path.relpath(path, ROOT), "files": n, "sha256": digest}))
