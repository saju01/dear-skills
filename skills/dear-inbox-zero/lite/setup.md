# Lite setup (mail only, no Python)

Resumable: memory's `stage` records progress (`l0_done` … `live`); `setup resume` continues from it. Never write over an existing `lite.json` with a different `account`: show it to the user instead. Memory format and saving rules: `lite/run.md`.

## L0 — Consent (one prompt)

1. `me` → the user's address. Propose an `account_key` (a short slug such as `work`, never the address) and the timezone the host reports.
2. Ask once, everything visible in one prompt:
   - mode: **lite**, mail only; calendar and Teams need the pro install;
   - what will be read: inbox metadata for 30 days, Sent-box metadata for 90 days, and up to 10 of the user's own sent replies to learn their writing style (read in working memory, never stored);
   - what is stored: confirmed rules, addresses and domains, message ids, the writing-style summary; never message bodies;
   - where: `OneDrive/dear-inbox-zero/<account_key>/lite.json`, or the agent's own memory if this host has no OneDrive access;
   - the automation level: **Medium** (recommended) or Low (`policy/buckets.md`);
   - a daily run on weekdays and a weekly learn, if the host can schedule;
   - that nothing is ever sent: replies are drafts.
3. Write memory with `stage: "l0_done"`, `version: 1` and the answers.

## L1 — Quick study (metadata only)

- Sent box, 90 days (`mail.sent`): the people the user writes to most → VIP candidates (up to 10); the user's own domain → `own_domains`.
- Inbox, 30 days (`mail.list`): the senders and series with the most mail and no rule yet (up to 15).

Stage `l1_done`.

## L2 — Calibration (one question at a time)

First the VIP candidates ("Is <name> someone whose mail always needs you? yes / no"). Then each top sender or series: Noise · FYI · Reply · Personal · skip, with "skip the rest" always offered. Answers become `rules`, `vip` or `personal`. Stage `l2_done`.

## L3 — Voice

Read up to 10 of the user's sent replies with `mail.body` (working memory only). Write the `voice` summary: greeting, sign-off, typical length, language. Show it in one line: "Is this how you write? yes / adjust". Stage `l3_done`.

## L4 — Dry run, then live

Run the daily run (`lite/run.md`) without any mailbox write: no tags, read state, flags or drafts. Show the report: what it would tag, flag and draft. Ask "Go live on Medium?" (or the level chosen at L0). Yes → `stage: "live"`, set `checkpoint` to now, save. If the user ticked scheduling, create the daily and weekly jobs with `schedule` (list existing ones first; never duplicate). Without a scheduler, tell the user to say `dear-inbox-zero` each morning.
