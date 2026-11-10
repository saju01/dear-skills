# Install (agent-led)

Use when the user asks to install dear-inbox-zero: from an uploaded zip, a folder, or the repo (`INSTALL.md` at the repo root covers repo installs and checksums).

## From the release zip in Cowork

1. **Find the upload:** a zip in the user's uploads named `dear-inbox-zero-v*.zip`. Unzip it to a working folder. It holds one folder, `dear-inbox-zero/`, with `SKILL.md` at its top.
2. **Check before installing:** `python dear-inbox-zero/engine/dear_engine.py doctor --skill-dir dear-inbox-zero` must return `"ok": true`. If not, stop and show the errors.
3. **Back up an existing install:** if `Documents/Cowork/skills/dear-inbox-zero/` exists, copy it to `Documents/Cowork/_backups/dear-inbox-zero-<old version>/` first. Never delete it.
4. **Copy** every file to `Documents/Cowork/skills/dear-inbox-zero/`, keeping relative paths, in one batched script. Re-list the folder and compare the file count.
5. **Adapter:** `config/host.json` is already `{"host": "cowork", "adapter": "hosts/cowork.md"}` in the Cowork zip.
6. **Start setup straight away**, unless the user said "install only". Tell the user it's installed, then begin `setup/first-install.md` at S0. The consent prompt is the first thing they see. Learning starts as soon as they consent: the Sent-box study, then calibration questions one at a time, a dry run, and live runs that keep learning.

## From any other agent

Follow `INSTALL.md` in the repo: read `install.json`, copy and verify every file's sha256, set `config/host.json` for your agent, run `doctor`, then start setup as in step 6.
