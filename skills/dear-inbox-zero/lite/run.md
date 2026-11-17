# Lite mode: the daily run (mail only, no Python)

Lite does for mail what pro does, with you (the agent) applying the rules straight from these guides. No engine, no Python, no calendar, no Teams. Load this file, `policy/buckets.md`, `policy/safety.md` and `policy/voice.md`; nothing else.

## Permissions

Lite uses these operations from the adapter: `me`, `mail.list`, `mail.meta`, `mail.body`, `mail.sent`, `mail.tag`, `mail.read`, `mail.flag`, `mail.reply_draft`, `store.read`, `store.write`, `ask`, and `schedule` if the host has one.

On Microsoft Graph that is two delegated scopes: `User.Read` and `Mail.ReadWrite`. Keeping memory in OneDrive adds `Files.ReadWrite`; without it, memory lives in the agent's own memory. Lite never needs `Mail.Send`, `MailboxSettings.*`, `Calendars.*`, `Chat.*` or `ChannelMessage.*`. So on Graph:
- `me` is `GET /me` only (the timezone is confirmed at setup, not read from mailbox settings);
- lite doesn't create the coloured DIZ category list (that needs mailbox settings). Tags still work; they show uncoloured until the user adds colours in Outlook.

## Memory: one small file

`OneDrive/dear-inbox-zero/<account_key>/lite.json`, or, on a host without OneDrive access, the same JSON kept in the agent's own memory as "dear-inbox-zero lite memory". Under 8 KB. Addresses, domains, series and message ids only: never bodies, previews, subjects of Personal mail or attachments.

```json
{
  "format": "dear-inbox-zero/lite@1",
  "version": 7,
  "account": "work",
  "tz": "UTC",
  "preset": "medium",
  "stage": "live",
  "checkpoint": "2026-03-02T07:55:00Z",
  "own_domains": ["example.com"],
  "vip": ["manager@example.com"],
  "personal": ["family.example.org"],
  "rules": [{"scope": "domain", "key": "newsletter.example.org", "bucket": "noise"}],
  "proposals": [{"scope": "sender", "key": "updates@example.net", "bucket": "fyi", "count": 2, "since": "2026-02-26"}],
  "paused": [],
  "voice": {"greeting": "Hi {first},", "sign_off": "Thanks, Alex", "length": "short", "language": "en"},
  "last_run": [{"id": "msg-1", "bucket": "noise", "acts": ["tag", "mark_read"]}]
}
```

`rules` are only ever what the user confirmed. `scope` is `series` (subject with dates, numbers and `RE:`/`FW:` removed), `sender` or `domain`; `bucket` is `noise`, `fyi`, `reply` or `personal`.

**Saving.** Re-read the file just before writing. If `version` changed since you loaded it, another run is writing: stop and report. Otherwise copy it to `lite.prev.json`, then write it with `version + 1`. `lite.json` is the only file lite ever overwrites (on Graph: `PUT …/lite.json:/content?@microsoft.graph.conflictBehavior=replace`). If the write is refused, report it; never retry around a refusal.

## The run

1. **Load** memory. None, or `stage` isn't `live` → say so and offer `dear-inbox-zero setup` (`lite/setup.md`).
2. **Collect** with one batched `mail.list` since `checkpoint` (first run: the last 2 days). Metadata only: sender, domain, subject, To/Cc, the ≤ 300-char preview, read, flag, categories, Focused/Other. Meeting invites are counted, not handled ("3 invites: answer them in Outlook").
3. **Observe** the items in `last_run` with one batched `mail.meta`, and the Sent box since `checkpoint` with `mail.sent`:
   - The user changed or removed a DIZ tag, or marked unread an item the run marked read → a **wrong action**: add the rule that caused it to `paused`, and add a proposal towards the bucket the user chose.
   - The user replied to an item that wasn't tagged Reply → a proposal: Reply for that sender.
   - Same direction again → `count + 1`. Opposite directions → drop the proposal.
4. **Classify** each new item with the precedence in `policy/buckets.md`: Personal (sender or domain in `personal`) → Reply (sender in `vip`, a `reply` rule, mail To the user with a direct question, or a deadline in subject/preview) → a confirmed rule, series before sender before domain (skip `paused` ones) → the guard (security, compliance, password, invoice-due and device alerts never go to Noise: lift to FYI) → unknown. Lite has no inferred rules: only confirmed ones act.
5. **Act** at the preset's level from `policy/buckets.md` (Low = 1, Medium = 2; lite has no High). Append the DIZ tag, never replace categories. Mark Noise read only under a confirmed, unpaused rule; FYI after its digest line; flag Reply at level 2. Personal: tag only, never opened. A bucket with a wrong action this week acts at level 1 until the weekly learn.
6. **Draft** each Reply item: read that one body (`mail.body`), write a reply draft with `policy/voice.md` and the `voice` memory, `mail.reply_draft`, re-read it.
7. **Propose**: a proposal with `count` ≥ 3 goes to the report as one question. Proposals older than 30 days are dropped.
8. **Save** memory: `checkpoint` = the newest received time collected; `last_run` = the items acted on this run; answers to last run's questions become `rules`.
9. **Report**, first line `dear-inbox-zero lite — <date>`: counts per bucket; **Needs you** (Reply items and draft status); one digest line per FYI item; **I noticed** (one question per proposal); **New senders** (one question each: Noise · FYI · Reply · Personal · skip); the Personal count; invites to answer in Outlook. Ground every line in what was read this run.

## Other commands

- `dear-inbox-zero learn` (weekly): wrong actions per bucket, each paused rule (resume or drop, one question each), open proposals. Resume a paused rule only on the user's yes.
- `dear-inbox-zero show <bucket>`: messages with that DIZ tag from the last 7 days, with the rule that matched.
- `dear-inbox-zero doctor`: memory loads, `format` is `dear-inbox-zero/lite@1`, size under 8 KB, and the adapter maps every operation listed under Permissions.
- `dear-inbox-zero automation --preset low|medium`: changes the preset in memory.
