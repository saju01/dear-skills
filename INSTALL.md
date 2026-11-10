# INSTALL.md — agent-led installation

**Audience: an AI agent installing on a user's behalf.** A human can follow the same steps.
**Trigger phrases:** "install dear-inbox-zero", "install https://github.com/saju01/dear-skills", "add the dear-inbox-zero skill".

The manifest [`install.json`](install.json) is the source of truth for files, hashes, host folders and adapters. This page explains how to use it.

---

## Step 1 — Read the manifest

Fetch `install.json` from the default branch:
`https://raw.githubusercontent.com/saju01/dear-skills/main/install.json`

Pick the skill the user asked for from `skills[]` (default: `dear-inbox-zero`). Note its `version`, `path`, `files[]` and `requires`.

## Step 2 — Identify the host (you)

Match yourself against `hosts[]` in this order:
1. **You already know your host.** Use that `id`.
2. **Detection hints.** Check each host's `detect` hints (an existing skills folder, an environment marker or an available tool name).
3. **Unknown.** Use `generic` and ask the user one question: "Which folder does your agent load skills from?"

## Step 3 — Choose the target folder

Use the first existing entry in the host's `skills_dirs`. Create `<skills_dir>/<skill name>/`.
- If the folder already exists and contains a `SKILL.md` with the same `name`, this is an **upgrade**: back up the folder to `<skills_dir>/_backups/<name>-<old version>/` first (never delete it), then continue.
- Never install into a folder that holds a user's memory store (`head/`, `store/`, `index.json`).

## Step 4 — Copy and verify the files

For each entry in `files[]`:
1. Download `https://raw.githubusercontent.com/saju01/dear-skills/main/<path>`.
2. Compute its sha256 and compare it with `sha256`. **On a mismatch, stop and report.** Don't write partial installs.
3. Write it to the target folder, keeping the relative path below the skill's `path`.

If you can only write text files, that's fine: every file in `files[]` is text (Markdown, JSON, Python source).

## Step 5 — Pick the adapter

Set the adapter in `<target>/config/host.json`:
```json
{ "host": "<host id>", "adapter": "hosts/<adapter file>" }
```
The adapter maps the skill's abstract operations (mail, calendar, Teams, OneDrive memory, ask) to your own tools. If no adapter exists for your host, use `hosts/_template.md`, fill in the mapping for your tools, and tell the user it's a new adapter.

## Step 6 — Check requirements

Confirm each item in `requires`:
- `capabilities`: you can call tools covering each listed operation group (mail, calendar, Teams, OneDrive files, ask the user).
- `python`: if you can run Python ≥ the stated version, the engine runs; if not, the skill runs in prose mode (slower, same rules).
- `forbidden`: make sure the adapter exposes **none** of these operations.

Then run the health check if you can run Python:
```bash
python <target>/engine/dear_engine.py doctor --skill-dir <target>
```

## Step 7 — Hand over to setup

Tell the user, in one short message:
- where it is installed, the version and the adapter,
- the `doctor` result,
- the next step: **"Say `dear-inbox-zero setup` to start. I'll ask your consent before reading anything, and your memory will live in your own OneDrive."**

Don't start setup yourself unless the user asks you to. Setup is where consent is given.

---

## Upgrade and uninstall

- **Upgrade:** same steps. The backup in step 3 keeps the previous version. The user's memory in OneDrive is untouched and is migrated by the new version's `doctor`, if needed.
- **Uninstall:** move `<skills_dir>/<name>/` to `<skills_dir>/_backups/`. Tell the user their memory stays in `OneDrive/dear-inbox-zero/` until they remove it themselves.

## Status

The repository is in **design stage (v0.1 in development)**. `install.json` currently lists the documentation only (`"installable": false`). Agents should report that the skill is not yet installable, rather than install partial files.
