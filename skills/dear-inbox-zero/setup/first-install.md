# First install (setup)

Resumable: `state.setup.stage` records progress; `setup resume` continues from it. Never initialise over an existing head: a foreign or broken head is recovery, shown to the user.

## S0 — Consent (one prompt)

1. Get the user's address, timezone and working hours (`me`). Propose `account_key` (a short slug, e.g. `work`, never the address).
2. Ask once, as a multi-select: which channels (mail, calendar, Teams); what will be read (sent mail 12 months, inbox 30 days, calendar ±30 days, Teams chats 30 days); what is stored (rules, ids, short summaries; never bodies); where (`OneDrive/dear-inbox-zero/<account_key>/`); and that nothing is ever sent.
3. `python engine/dear_engine.py store-init --store <working>/store --account <account_key> --tz <tz> --channels mail,calendar,teams` → upload the store folder. Stage `s0_done`.

## S1 — Behaviour study (paged, resumable)

**Sent box first** (`learn/sent-box.md`): 12 months of sent metadata plus up to 40 reply bodies (working memory only) →
`python engine/dear_engine.py sent-study --state … --sent sent.json --bodies bodies.json`.
This learns whom the user answers and how fast, language per contact, working hours, their own domain and voice.

Then the rest of their behaviour, as aggregated observations (`schemas/observation.schema.json`):
- inbox (30 days): what they read without replying (`read_no_reply`), leave unread (`ignored`); Focused/Other overrides; existing mail rules;
- calendar (±30 days): organisers/series they accept or decline;
- Teams (30 days): chats and mentions they answer (`teams_replied`).

`python engine/dear_engine.py study --state … --observations obs.json` creates inferred rules and proposals. Stage `s1_done`.

## S2 — Voice check

`sent-study` already wrote the voice fact (greeting, sign-off, length, bullets, default language). Show it to the user in one line and ask: "Is this how you write? Yes / adjust". Adjustments become an explicit `voice` fact (`engine … add-facts`). Stage `s2_done`.

## S3 — Calibration (one question at a time)

`python engine/dear_engine.py calibrate --state … --out questions.json` lists the senders/series with the most volume and the least certainty (max 15). Ask each one: Noise · FYI · Reply · Personal · skip. Answers become explicit rules. Ask about VIPs and personal senders the same way. Stage `s3_done`.

## S4 — Dry run

Run the daily run with `--dry-run`: no writes. Show the report: what it would tag, flag, draft and recommend. Ask "Go live?". Yes → autonomy level 1 for every bucket, stage `live`. Offer to schedule a daily run.
