---
name: dear-inbox-zero
description: >
  Personal inbox-zero for Microsoft 365: mail, meeting invites and Teams messages that need the
  user. Tags mail Noise / FYI / Reply / Personal, drafts replies in the user's voice, recommends
  invite responses and helps answer Teams messages; learns only from the user's own actions and
  keeps its memory in the user's OneDrive. Never sends, forwards, posts, deletes or declines.
  Lite mode (mail only, no Python) or pro mode (adds invites and Teams; Python engine), picked
  from what the host can do. Use on "dear-inbox-zero",
  "dear-inbox-zero setup|learn|show|doctor", or when the user asks to install it. Not for
  one-off questions about a single message.
license: Apache-2.0
metadata:
  version: "0.1.0"
  repo: https://github.com/saju01/dear-skills
---

# dear-inbox-zero

Takes the mental load of everything that asks for the user's attention. This file is the router: load only the guide the current step needs.

## Mode: lite or pro (detect, don't ask)

Read `config/host.json`. `"mode": "lite"` or `"pro"` wins. Otherwise (`"auto"` or absent): **pro** if you can run Python 3.10+ (the adapter maps `run_python`) and `engine/dear_engine.py` is present; else **lite**. Don't ask the user. If the memory folder holds `lite.json` but no `head/`, stay in lite until the user runs pro setup. Name the mode in the first line of every report.

- **Lite**: mail only, no Python, Graph scopes `User.Read` + `Mail.ReadWrite` (plus `Files.ReadWrite` for OneDrive memory). Operations come from the adapter `config/host.json` names. Follow `lite/run.md` and `lite/setup.md`; the rest of this file is pro only, except the hard rules.
- **Pro**: mail, invites and Teams, with the engine. The rest of this file.

## Commands

| Command | Do | Pro loads | Lite loads |
|---|---|---|---|
| `dear-inbox-zero setup` (also `setup resume`) | first install for this user | `setup/first-install.md` | `lite/setup.md` |
| `dear-inbox-zero` | the daily run | this file + enabled `channels/*.md` | `lite/run.md` |
| `dear-inbox-zero learn` | weekly review of proposals and accuracy | `learn/learning-loop.md` | `lite/run.md` |
| `dear-inbox-zero show <bucket>` | list a bucket with reasons | engine `show` | `lite/run.md` |
| `dear-inbox-zero doctor` | health check | engine `doctor` | `lite/run.md` |

Install requests ("install dear-inbox-zero", an uploaded `dear-inbox-zero-v*.zip`) follow `setup/install.md`; after installing, setup starts right away with the consent prompt.

## Pro: before anything

1. Read `config/host.json` → open the adapter it names (`hosts/<file>.md`). Every operation below (`mail.*`, `cal.*`, `teams.*`, `store.*`, `ask`) is mapped there. If the file is missing, run `doctor`.
2. Load the store: `store.list` the user's memory folder (default `OneDrive/dear-inbox-zero/<account_key>/`), download `head/` into a working folder, then
   `python engine/dear_engine.py store-load --store <working>/store --out <working>/state.json`.
   No head → the user has not run setup: say so and offer `dear-inbox-zero setup`. A hash mismatch → stop and show the user; never initialise over it.

## Pro: the daily run

| Step | What | Engine |
|---|---|---|
| 1 Collect | per enabled channel, metadata only, in one batched read each (see channel guide) → `items.json` | — |
| 2 Observe | Sent box first (`learn/sent-box.md`), then tags changed, flags, binned drafts, invites answered, Teams replies → `signals.json` | `sent-signals`, `observe` |
| 3 Classify | rules decide; unknowns come back as a short list | `classify` |
| 4 Judge unknowns | only `unknown` items: read their metadata (body only if a reply is needed) and pick a bucket, or leave unknown and ask once in the report | — |
| 5 Act | do exactly the `actions[]` the engine planned (they already respect autonomy levels and safety) | — |
| 6 Draft | for Reply items: draft in the user's voice (`policy/voice.md`); Teams: suggested reply text in the report | — |
| 7 Learn | proposals from signals; expiry; autonomy update | `learn` |
| 7b Automation | first run after setup: create the daily run + weekly learn from `automation` (preset Auto · Medium unless the user chose otherwise) | `automation` |
| 8 Publish | new head + facts + index, uploaded to the store; re-list to confirm | `store-publish` |
| 9 Report | `report` output, shown to the user | `report` |

Commands: `python engine/dear_engine.py <cmd> --help`. All files are JSON in, JSON/Markdown out.

## Buckets

**Noise** (needs no human) · **FYI** (only needs knowing: digest line, then read) · **Reply** (needs the user: flag + draft) · **Personal** (private: counted only, never opened) · unknown (asked once). Details and precedence: `policy/buckets.md`.

## Hard rules (never relaxed by memory, rules or the user's past habits)

- Never send, forward, post, delete, move, or decline. Many hosts' "forward" sends immediately: never call it.
- Drafts are formatted HTML/Markdown files, never plain text that loses its line breaks; re-read every draft after writing.
- Never remove a category, flag or rule the user set.
- Personal items: never open, summarise, flag or learn from the body.
- Questions to the user: one item per question, clear options.
- Unattended runs: if the host refuses a write (e.g. a store upload), park the files and report it; never retry around a refusal.
- Ground every statement in the report in what was read this run.

## Scheduling

If the user asks for a daily run, use the host's scheduler with the prompt `dear-inbox-zero` (weekdays, a fixed time) and `dear-inbox-zero learn` weekly. Check for an existing schedule first, so it never runs twice.
